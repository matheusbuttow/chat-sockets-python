"""
Servidor WebSocket Principal — NexusChat (porta 8765)
Gerencia conexões de múltiplos clientes, salas de chat e histórico de mensagens.
Cada cliente recebe uma thread dedicada para processamento assíncrono de mensagens.
"""

from websocket_server import WebsocketServer
import threading
import queue
import json
import os

# ------------------------------------------------------------------ #
# Estado compartilhado entre threads                                  #
# Todos os dicionários abaixo são protegidos por Locks para evitar   #
# race conditions em acessos concorrentes.                           #
# ------------------------------------------------------------------ #

# { client_id -> {'client': ..., 'thread': ClientThread} }
clients = {}
clients_lock = threading.Lock()

# { room_name -> set(client_ids) }
rooms = {}
rooms_lock = threading.Lock()

# { room_name -> [lista das últimas 50 mensagens] }
room_history = {}
history_lock = threading.Lock()

# { username -> client_id }  — garante unicidade de nicknames
usernames = {}
username_lock = threading.Lock()


# ------------------------------------------------------------------ #
# Thread dedicada por cliente                                         #
# ------------------------------------------------------------------ #
class ClientThread(threading.Thread):
    """
    Thread criada para cada cliente conectado.
    Processa mensagens de uma fila (Queue) de forma independente,
    evitando que um cliente lento bloqueie os demais.
    """

    def __init__(self, client, server):
        super().__init__(daemon=True)
        self.client = client
        self.server = server
        # Fila de mensagens recebidas deste cliente
        self.message_queue = queue.Queue()
        self.running = True

    def run(self):
        print(f"[THREAD] Iniciada para cliente {self.client['id']}")

        while self.running:
            try:
                # Aguarda próxima mensagem (timeout para checar self.running)
                data = self.message_queue.get(timeout=1)
                msg_type = data.get('type')

                if msg_type == 'message':
                    self._handle_message(data)

                elif msg_type == 'join_room':
                    self._handle_join(data)

                elif msg_type == 'leave_room':
                    self._handle_leave(data)

                elif msg_type == 'typing':
                    self._handle_typing(data, stop=False)

                elif msg_type == 'stop_typing':
                    self._handle_typing(data, stop=True)

            except queue.Empty:
                continue

        print(f"[THREAD FINALIZADA] Cliente {self.client['id']}")

    # ---------------------------------------------------------- #
    # Handlers internos                                           #
    # ---------------------------------------------------------- #

    def _handle_message(self, data):
        """Processa e retransmite uma mensagem de chat para toda a sala."""
        username    = data.get('username') or data.get('sender')
        displayName = data.get('displayName', username)
        text        = data.get('text')
        room        = data.get('roomId') or data.get('room')

        print(f"[CHAT] [{room}] {username}: {text}")

        response = {
            'type':        'message',
            'sender':      username,
            'displayName': displayName,
            'roomId':      room,
            'text':        text,
            'ts':          data.get('ts'),
        }

        # Salva no histórico (máximo 50 mensagens por sala)
        with history_lock:
            room_history.setdefault(room, []).append(response)
            if len(room_history[room]) > 50:
                room_history[room].pop(0)

        send_to_room(room, self.server, json.dumps(response))

    def _handle_join(self, data):
        """Registra o usuário na sala e envia o histórico de mensagens."""
        username    = data.get('username')
        displayName = data.get('displayName', username)
        room        = data.get('roomId') or data.get('room')

        # Verifica unicidade do username
        with username_lock:
            if username in usernames:
                send_to_client(self.client, self.server,
                               {'type': 'error', 'message': 'Username já está em uso'})
                return
            usernames[username] = self.client['id']

        join_room(self.client['id'], room)
        print(f"[JOIN] {username} entrou em '{room}'")

        # Envia histórico ao usuário que acabou de entrar
        with history_lock:
            history = list(room_history.get(room, []))

        send_to_client(self.client, self.server,
                       {'type': 'history', 'roomId': room, 'messages': history})

        # Notifica os demais membros da sala
        send_to_room(room, self.server,
                     json.dumps({'type': 'user_joined', 'username': username,
                                 'displayName': displayName, 'roomId': room}))

    def _handle_leave(self, data):
        """Remove o usuário da sala e notifica os membros restantes."""
        username    = data.get('username')
        displayName = data.get('displayName', username)
        room        = data.get('roomId') or data.get('room')

        leave_room(self.client['id'], room)
        print(f"[LEAVE] {username} saiu de '{room}'")

        send_to_room(room, self.server,
                     json.dumps({'type': 'user_left', 'username': username,
                                 'displayName': displayName, 'roomId': room}))

    def _handle_typing(self, data, stop):
        """Repassa o indicador de digitação (ou parada) para os demais da sala."""
        username = data.get('username')
        room     = data.get('roomId') or data.get('room')
        msg_type = 'stop_typing' if stop else 'typing'

        send_to_room(room, self.server,
                     json.dumps({'type': msg_type, 'username': username, 'roomId': room}))

    def add_message(self, message):
        """Enfileira uma mensagem para processamento pela thread."""
        self.message_queue.put(message)

    def stop(self):
        """Sinaliza para a thread encerrar seu loop."""
        self.running = False


# ------------------------------------------------------------------ #
# Funções de gerenciamento de salas                                   #
# ------------------------------------------------------------------ #

def join_room(client_id, room_name):
    """Adiciona um cliente a uma sala, criando-a se não existir."""
    with rooms_lock:
        rooms.setdefault(room_name, set()).add(client_id)
        print(f"[ROOM] Cliente {client_id} entrou em '{room_name}'")


def leave_room(client_id, room_name):
    """Remove um cliente de uma sala e apaga a sala se ficar vazia."""
    with rooms_lock:
        if room_name in rooms:
            rooms[room_name].discard(client_id)
            if not rooms[room_name]:
                del rooms[room_name]
            print(f"[ROOM] Cliente {client_id} saiu de '{room_name}'")


def send_to_room(room_name, server, message):
    """Envia uma mensagem para todos os clientes de uma sala."""
    with rooms_lock:
        if room_name not in rooms:
            return
        room_clients = list(rooms[room_name])

    with clients_lock:
        for client_id in room_clients:
            if client_id in clients:
                server.send_message(clients[client_id]['client'], message)


def send_to_client(client, server, data):
    """Envia um objeto Python (serializado como JSON) para um cliente específico."""
    server.send_message(client, json.dumps(data))


# ------------------------------------------------------------------ #
# Callbacks do WebsocketServer                                        #
# ------------------------------------------------------------------ #

def on_new_client(client, server):
    """Chamado quando um novo cliente se conecta — cria e inicia sua thread."""
    print(f"[CONEXÃO] Cliente {client['id']}")
    thread = ClientThread(client, server)
    with clients_lock:
        clients[client['id']] = {'client': client, 'thread': thread}
    thread.start()


def on_client_left(client, server):
    """Chamado quando um cliente desconecta — encerra a thread e limpa o estado."""
    print(f"[DESCONEXÃO] Cliente {client['id']}")

    with clients_lock:
        if client['id'] in clients:
            clients[client['id']]['thread'].stop()
            del clients[client['id']]

    # Remove o username associado ao cliente
    with username_lock:
        to_remove = next((u for u, cid in usernames.items() if cid == client['id']), None)
        if to_remove:
            del usernames[to_remove]
            print(f"[USERNAME REMOVIDO] {to_remove}")

    # Remove o cliente de todas as salas em que estava
    with rooms_lock:
        for room in list(rooms.keys()):
            rooms[room].discard(client['id'])
            if not rooms[room]:
                del rooms[room]


def on_message(client, server, message):
    """Chamado a cada mensagem recebida — deserializa e enfileira na thread do cliente."""
    try:
        data = json.loads(message)
    except json.JSONDecodeError:
        print("[ERRO] JSON inválido recebido")
        return

    print(f"[EVENTO] tipo={data.get('type')} cliente={client['id']}")

    with clients_lock:
        if client['id'] in clients:
            clients[client['id']]['thread'].add_message(data)


# ------------------------------------------------------------------ #
# Ponto de entrada                                                    #
# ------------------------------------------------------------------ #

def start_server():
    """Inicializa e executa o servidor WebSocket.
    A porta é lida da variável de ambiente PORT (usada pelo Render)
    ou cai no padrão 8765 para execução local.
    """
    port = int(os.environ.get('PORT', 8765))
    server = WebsocketServer(host='0.0.0.0', port=port)
    server.set_fn_new_client(on_new_client)
    server.set_fn_client_left(on_client_left)
    server.set_fn_message_received(on_message)
    print(f"[SERVIDOR] WebSocket rodando na porta {port}")
    server.run_forever()


if __name__ == '__main__':
    # Roda o servidor em uma thread separada para permitir expansão futura
    server_thread = threading.Thread(target=start_server, daemon=True)
    server_thread.start()
    print("[MAIN] Servidor iniciado — pressione Ctrl+C para encerrar")
    server_thread.join()
