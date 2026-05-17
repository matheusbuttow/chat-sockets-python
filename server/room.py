from globals import rooms_lock, rooms, clients, clients_lock 
import json

def join_room(client_id, room_name):
    """Adiciona um cliente a uma sala, criando-a se não existir."""
    #codigo q coloca de fato o cliente na sala no dict
    with rooms_lock:
        rooms.setdefault(room_name, set()).add(client_id)
        print(f"[ROOM] Cliente {client_id} entrou em '{room_name}'")


def leave_room(client_id, room_name):
    """Remove um cliente de uma sala e apaga a sala se ficar vazia."""
    with rooms_lock:
        if room_name in rooms: #se a sala existir
            rooms[room_name].discard(client_id) #tira o cliente q saiu
            if not rooms[room_name]: #se sala vazia
                del rooms[room_name] #delete a sala
            print(f"[ROOM] Cliente {client_id} saiu de '{room_name}'")


def send_to_room(room_name, server, message):
    """Envia uma mensagem para todos os clientes de uma sala."""
    with rooms_lock:
        if room_name not in rooms:
            return #se n existir a sala
        room_clients = list(rooms[room_name]) #recebe os clientes

    with clients_lock:
        for client_id in room_clients:
            if client_id in clients:
                server.send_message(clients[client_id]['client'], message) #lista os clientes e manda a mensagem para cada

def send_to_client(client, server, data):
    """Envia um objeto Python (JSON) para um cliente específico."""
    server.send_message(client, json.dumps(data))