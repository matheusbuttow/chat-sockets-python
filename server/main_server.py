from websocket_server import WebsocketServer
import threading
import queue
import time
import json

# clientes conectados
clients = {}
# lock para evitar race condition
clients_lock = threading.Lock()

#salas disponiveis
rooms = {}
# lock para evitar race condition
rooms_lock = threading.Lock()

#parte do historico
# historico das salas
room_history = {}
# lock do historico
history_lock = threading.Lock()

usernames = {}
username_lock = threading.Lock()



class ClientThread(threading.Thread):

    def __init__(self, client, server):
        super().__init__()

        self.client = client
        self.server = server

        # fila de mensagens do cliente
        self.message_queue = queue.Queue()

        self.running = True

    def run(self):

        print(f"[THREAD] Thread iniciada para cliente {self.client['id']}")

        while self.running:

            try:
                # espera mensagem da fila
                data = self.message_queue.get(timeout=1)
                msg_type = data.get('type')

                if msg_type == 'message':

                    username = data.get('username')
                    text = data.get('text')
                    room = data.get('room')

                    print(f"[CHAT] {username}: {text}")

                    response = {
                        'type': 'message',
                        'username': username,
                        'room': room,
                        'text': text
                    }

                    # salva no historico
                    with history_lock:

                        if room not in room_history:
                            room_history[room] = []

                        room_history[room].append(response)

                        # limita historico
                        if len(room_history[room]) > 50:
                            room_history[room].pop(0)

                    send_to_room(room, self.server, json.dumps(response))

                elif msg_type == "join_room":

                    username = data.get('username')
                    with username_lock:
                        if username in usernames:
                            error_response = {"type": "error", "message": "Username ja esta em uso"}
                            send_to_client(self.client,self.server,error_response)

                            continue
                        # registra username
                        usernames[username] = self.client['id']

                    room = data.get('room')

                    join_room(self.client['id'], room)

                    print(f'[JOIN] {username} entrou em {room}')

                    # envia historico da sala
                    with history_lock:

                        history = room_history.get(room, [])

                    history_response = {
                        "type": "history",
                        "room": room,
                        "messages": history
                    }

                    send_to_client(
                        self.client,
                        self.server,
                        history_response
                    )

                    response = {
                        'type': "user_joined",
                        'username': username,
                        "room": room
                    }

                    send_to_room(room, self.server, json.dumps(response))
                
            except queue.Empty:
                continue

        print(f"[THREAD FINALIZADA] Cliente {self.client['id']}")

    def add_message(self, message):
        self.message_queue.put(message)

    def stop(self):
        self.running = False


def join_room(client_id, room_name):

    with rooms_lock:

        if room_name not in rooms:
            rooms[room_name] = set()

        rooms[room_name].add(client_id)

        print(f"[ROOM] Cliente {client_id} entrou em {room_name}")

def leave_room(client_id, room_name):

    with rooms_lock:
        if room_name in rooms:
            rooms[room_name].discard(client_id)
        
            print(f"[ROOM] Cliente {client_id} saiu de {room_name}")

            # remove sala vazia
            if len(rooms[room_name]) == 0:
                del rooms[room_name]

def send_to_room(room_name, server, message):

    with rooms_lock:

        if room_name not in rooms:
            return

        room_clients = list(rooms[room_name])

    with clients_lock:

        for client_id in room_clients:

            if client_id in clients:

                client = clients[client_id]['client']
                server.send_message(client, message)

def send_to_client(client, server, data):

    server.send_message(
        client,
        json.dumps(data)
    )

def on_new_client(client, server):

    print(f"[NOVA CONEXÃO] Cliente {client['id']}")

    # cria thread do cliente
    client_thread = ClientThread(client, server)

    # salva thread
    with clients_lock:
        clients[client['id']] = {
            'client': client,
            'thread': client_thread
        }

    # inicia thread
    client_thread.start()

def on_client_left(client, server):

    print(f"[DESCONECTOU] Cliente {client['id']}")

    with clients_lock:

        if client['id'] in clients:

            # encerra thread
            clients[client['id']]['thread'].stop()

            # remove cliente
            del clients[client['id']]

            with username_lock:
                username_to_remove = None
                for username, cid in usernames.items():

                    if cid == client['id']:
                        username_to_remove = username
                        break

                if username_to_remove:
                    del usernames[username_to_remove]

                    print(f"[USERNAME REMOVIDO] {username_to_remove}")
    
    with rooms_lock:

        for room_name in list(rooms.keys()):

            rooms[room_name].discard(client['id'])

            if len(rooms[room_name]) == 0:
                del rooms[room_name]

def on_message(client, server, message):

    try:
        data = json.loads(message)
    except:
        print("[ERRO] JSON invalido")
        return
    
    msg_type = data.get("type")

    print(f"[EVENTO] {msg_type}")

    with clients_lock:

        if client['id'] in clients:

            # coloca mensagem na fila da thread
            clients[client['id']]['thread'].add_message(data)

def start_server():

    server = WebsocketServer(
        host='0.0.0.0',
        port=8765
    )

    server.set_fn_new_client(on_new_client)
    server.set_fn_client_left(on_client_left)
    server.set_fn_message_received(on_message)

    print("[SERVIDOR] Rodando na porta 8765")

    server.run_forever()

if __name__ == "__main__":

    server_thread = threading.Thread(target=start_server)

    server_thread.start()

    print("[MAIN] Servidor iniciado")