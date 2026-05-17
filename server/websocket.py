import json
from client_thread import ClientThread
from user import (get_online_users,remove_username)
from globals import *


def broadcast_online_users(server):
    """Envia lista de usuários online para todos."""
    response = {"type": "online_users","users": get_online_users()}

    #server manda a msg
    server.send_message_to_all(json.dumps(response))

def on_new_client(client, server):
    """
    Chamado quando um novo cliente se conecta.
    Cria e inicia a thread dedicada ao cliente.
    """
    print(f"[CONEXÃO] Cliente {client['id']}")

    thread = ClientThread(client, server)
    with clients_lock:
        #adiciona thread do client ao dict dos clientes
        clients[client['id']] = {'client': client,'thread': thread}

    thread.start()

def on_client_left(client, server):
    """
    Chamado quando um cliente desconecta.
    Remove o cliente do sistema e encerra sua thread.
    """
    print(f"[DESCONEXÃO] Cliente {client['id']}")

    # encerra thread e remove cliente
    with clients_lock:
        if client['id'] in clients:
            clients[client['id']]['thread'].stop()
            del clients[client['id']]

    # remove username
    removed_username = remove_username(client['id'])
    if removed_username:
        print(f"[USERNAME REMOVIDO] {removed_username}")
        broadcast_online_users(server)

    # remove cliente de todas as salas
    with rooms_lock:
        for room in list(rooms.keys()):
            rooms[room].discard(client['id'])
            if not rooms[room]:
                del rooms[room]

def on_message(client, server, message):
    """
    Chamado quando uma mensagem é recebida.
    Faz parse do JSON e envia para a thread do cliente.
    """
    try:

        data = json.loads(message)

    except json.JSONDecodeError:

        print("[ERRO] JSON inválido recebido")
        return

    print(f"[EVENTO] tipo={data.get('type')} cliente={client['id']}")
    with clients_lock:

        if client['id'] in clients:
            clients[client['id']]['thread'].add_message(data)