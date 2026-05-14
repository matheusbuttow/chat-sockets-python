from globals import rooms_lock, rooms, clients, clients_lock 
import json

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