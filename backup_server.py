"""
Servidor de Backup — NexusChat
Implementa o mecanismo de tolerância a falhas:
- Fica monitorando o servidor principal (porta 8765)
- Quando o principal cai, assume automaticamente na porta 8766
- Clientes tentam 8766 após 3 falhas de reconexão (ver frontend)
"""

from websocket_server import WebsocketServer
import threading
import queue
import socket
import time
import json
import os

# ------------------------------------------------------------------ #
# Estado compartilhado (espelhado do servidor principal)              #
# ------------------------------------------------------------------ #
clients = {}
clients_lock = threading.Lock()

rooms = {}
rooms_lock = threading.Lock()

room_history = {}
history_lock = threading.Lock()

usernames = {}
username_lock = threading.Lock()

# Endereço do servidor principal para monitoramento
# Em produção (Render), PRIMARY_HOST é o hostname do serviço principal
PRIMARY_HOST = os.environ.get('PRIMARY_HOST', 'localhost')
PRIMARY_PORT = int(os.environ.get('PRIMARY_PORT', 8765))

# Porta deste backup (Render injeta PORT; localmente usa 8766)
BACKUP_PORT = int(os.environ.get('PORT', 8766))


# ------------------------------------------------------------------ #
# Thread dedicada por cliente (mesma lógica do servidor principal)    #
# ------------------------------------------------------------------ #
class ClientThread(threading.Thread):

    def __init__(self, client, server):
        super().__init__(daemon=True)
        self.client = client
        self.server = server
        self.message_queue = queue.Queue()
        self.running = True

    def run(self):
        print(f"[BACKUP THREAD] Iniciada para cliente {self.client['id']}")

        while self.running:
            try:
                data = self.message_queue.get(timeout=1)
                msg_type = data.get('type')

                if msg_type == 'message':
                    _handle_message(self, data)

                elif msg_type == 'join_room':
                    _handle_join(self, data)

                elif msg_type == 'leave_room':
                    _handle_leave(self, data)

                elif msg_type == 'typing':
                    _handle_typing(self, data, stop=False)

                elif msg_type == 'stop_typing':
                    _handle_typing(self, data, stop=True)

            except queue.Empty:
                continue

        print(f"[BACKUP THREAD FINALIZADA] Cliente {self.client['id']}")

    def add_message(self, msg):
        self.message_queue.put(msg)

    def stop(self):
        self.running = False


# ------------------------------------------------------------------ #
# Handlers de protocolo                                               #
# ------------------------------------------------------------------ #
def _handle_message(thread, data):
    username = data.get('username')
    text     = data.get('text')
    room     = data.get('roomId') or data.get('room')

    response = {'type': 'message', 'sender': username, 'displayName': data.get('displayName', username),
                'roomId': room, 'text': text, 'ts': data.get('ts')}

    with history_lock:
        room_history.setdefault(room, []).append(response)
        if len(room_history[room]) > 50:
            room_history[room].pop(0)

    send_to_room(room, thread.server, json.dumps(response))


def _handle_join(thread, data):
    username    = data.get('username')
    displayName = data.get('displayName', username)
    room        = data.get('roomId') or data.get('room')

    with username_lock:
        if username in usernames:
            send_to_client(thread.client, thread.server,
                           {'type': 'error', 'message': 'Username já está em uso'})
            return
        usernames[username] = thread.client['id']

    join_room(thread.client['id'], room)

    # Envia histórico ao novo membro
    with history_lock:
        history = list(room_history.get(room, []))

    send_to_client(thread.client, thread.server,
                   {'type': 'history', 'roomId': room, 'messages': history})

    # Notifica os demais membros da sala
    send_to_room(room, thread.server,
                 json.dumps({'type': 'user_joined', 'username': username,
                             'displayName': displayName, 'roomId': room}))

    print(f"[BACKUP JOIN] {username} entrou em {room}")


def _handle_leave(thread, data):
    username    = data.get('username')
    displayName = data.get('displayName', username)
    room        = data.get('roomId') or data.get('room')

    leave_room(thread.client['id'], room)

    send_to_room(room, thread.server,
                 json.dumps({'type': 'user_left', 'username': username,
                             'displayName': displayName, 'roomId': room}))

    print(f"[BACKUP LEAVE] {username} saiu de {room}")


def _handle_typing(thread, data, stop):
    username = data.get('username')
    room     = data.get('roomId') or data.get('room')
    msg_type = 'stop_typing' if stop else 'typing'

    send_to_room(room, thread.server,
                 json.dumps({'type': msg_type, 'username': username, 'roomId': room}))


# ------------------------------------------------------------------ #
# Gerenciamento de salas                                              #
# ------------------------------------------------------------------ #
def join_room(client_id, room_name):
    with rooms_lock:
        rooms.setdefault(room_name, set()).add(client_id)


def leave_room(client_id, room_name):
    with rooms_lock:
        if room_name in rooms:
            rooms[room_name].discard(client_id)
            if not rooms[room_name]:
                del rooms[room_name]


def send_to_room(room_name, server, message):
    with rooms_lock:
        if room_name not in rooms:
            return
        room_clients = list(rooms[room_name])

    with clients_lock:
        for cid in room_clients:
            if cid in clients:
                server.send_message(clients[cid]['client'], message)


def send_to_client(client, server, data):
    server.send_message(client, json.dumps(data))


# ------------------------------------------------------------------ #
# Callbacks do WebsocketServer                                        #
# ------------------------------------------------------------------ #
def on_new_client(client, server):
    print(f"[BACKUP CONEXÃO] Cliente {client['id']}")
    thread = ClientThread(client, server)
    with clients_lock:
        clients[client['id']] = {'client': client, 'thread': thread}
    thread.start()


def on_client_left(client, server):
    print(f"[BACKUP DESCONEXÃO] Cliente {client['id']}")

    with clients_lock:
        if client['id'] in clients:
            clients[client['id']]['thread'].stop()
            del clients[client['id']]

    # Remove de todos os usernames e salas
    with username_lock:
        to_remove = next((u for u, cid in usernames.items() if cid == client['id']), None)
        if to_remove:
            del usernames[to_remove]

    with rooms_lock:
        for room in list(rooms.keys()):
            rooms[room].discard(client['id'])
            if not rooms[room]:
                del rooms[room]


def on_message(client, server, message):
    try:
        data = json.loads(message)
    except Exception:
        print("[BACKUP ERRO] JSON inválido")
        return

    with clients_lock:
        if client['id'] in clients:
            clients[client['id']]['thread'].add_message(data)


# ------------------------------------------------------------------ #
# Monitor do servidor principal                                        #
# ------------------------------------------------------------------ #
def is_primary_alive():
    """Tenta abrir uma conexão TCP na porta do servidor principal."""
    try:
        with socket.create_connection((PRIMARY_HOST, PRIMARY_PORT), timeout=2):
            return True
    except OSError:
        return False


def monitor_primary(backup_server_ref):
    """
    Loop de monitoramento: verifica o principal a cada 5 segundos.
    Quando detecta queda, imprime aviso (o servidor de backup já está ativo).
    """
    was_alive = True
    print(f"[MONITOR] Monitorando servidor principal em {PRIMARY_HOST}:{PRIMARY_PORT}")

    while True:
        alive = is_primary_alive()

        if was_alive and not alive:
            print("[MONITOR] *** Servidor principal caiu! Backup assumindo na porta", BACKUP_PORT, "***")

        if not was_alive and alive:
            print("[MONITOR] Servidor principal voltou ao ar.")

        was_alive = alive
        time.sleep(5)


# ------------------------------------------------------------------ #
# Ponto de entrada                                                    #
# ------------------------------------------------------------------ #
if __name__ == '__main__':
    # Inicia o servidor de backup na porta 8766
    server = WebsocketServer(host='0.0.0.0', port=BACKUP_PORT)
    server.set_fn_new_client(on_new_client)
    server.set_fn_client_left(on_client_left)
    server.set_fn_message_received(on_message)

    print(f"[BACKUP] Servidor de backup pronto na porta {BACKUP_PORT}")

    # Thread de monitoramento do principal (daemon — encerra com o processo)
    monitor_thread = threading.Thread(target=monitor_primary, args=(server,), daemon=True)
    monitor_thread.start()

    # Mantém o backup rodando indefinidamente
    server.run_forever()
