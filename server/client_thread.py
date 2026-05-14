from globals import *
from room import *
from user import (
    register_username,
    remove_username,
    get_online_users,
    register_user,
    authenticate_user,
    get_display_name
)

import threading
import queue
import json

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

        # username associado a essa conexão
        self.username = None

    def run(self):
        print(f"[THREAD] Iniciada para cliente {self.client['id']}")

        while self.running:
            try:
                # Aguarda próxima mensagem (timeout para checar self.running)
                data = self.message_queue.get(timeout=1)
                msg_type = data.get('type')

                if msg_type == 'register':
                    self._handle_register(data)

                elif msg_type == 'login':
                    self._handle_login(data)

                elif msg_type == 'message':
                    self._handle_message(data)

                elif msg_type == 'join_room':
                    self._handle_join(data)

                elif msg_type == 'leave_room':
                    self._handle_leave(data)

                elif msg_type == 'typing':
                    self._handle_typing(data, stop=False)

                elif msg_type == 'stop_typing':
                    self._handle_typing(data, stop=True)

                elif msg_type == 'room_created':
                    self._handle_room_created(data)

            except queue.Empty:
                continue

        print(f"[THREAD FINALIZADA] Cliente {self.client['id']}")

    # ---------------------------------------------------------- #
    # Handlers internos                                           #
    # ---------------------------------------------------------- #

    def _handle_room_created(self, data):
        # Transforma o dado de volta em texto JSON
        mensagem_str = json.dumps(data)
        
        # Pede pro servidor principal disparar para todos os clientes logados
        self.server.send_message_to_all(mensagem_str)
        print(f"[SALA CRIADA] Sala {data['room']['name']} anunciada no servidor")
    
    def _handle_room_created(self, data):
        from globals import registered_rooms, registered_rooms_lock
        
        nova_sala = data['room']
        
        # 1. O servidor anota a nova sala na memória dele
        with registered_rooms_lock:
            # Verifica se já não existe para evitar duplicata
            if not any(r['id'] == nova_sala['id'] for r in registered_rooms):
                registered_rooms.append(nova_sala)
        
        # 2. Avisa quem já está online agora
        self.server.send_message_to_all(json.dumps(data))

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
        """Registra o usuário na sala e envia o histórico."""

        username = data.get('username')
        displayName = data.get('displayName', username)
        room = data.get('roomId') or data.get('room')

        # PRIMEIRO JOIN da conexão
        if self.username is None:

            success = register_username(
                username,
                self.client['id']
            )

            if not success:

                send_to_client(
                    self.client,
                    self.server,
                    {
                        'type': 'error',
                        'message': 'Username já está em uso'
                    }
                )

                return

            self.username = username
            from websocket import broadcast_online_users
            # atualiza online users
            broadcast_online_users(self.server)

        # impede entrar 2x na mesma sala
        with rooms_lock:

            if room in rooms and self.client['id'] in rooms[room]:
                return

        join_room(self.client['id'], room)

        print(f"[JOIN] {username} entrou em '{room}'")

        # histórico
        with history_lock:
            history = list(room_history.get(room, []))

        send_to_client(
            self.client,
            self.server,
            {
                'type': 'history',
                'roomId': room,
                'messages': history
            }
        )

        # avisa sala
        send_to_room(
            room,
            self.server,
            json.dumps({
                'type': 'user_joined',
                'username': username,
                'displayName': displayName,
                'roomId': room
            })
        )

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

    def _handle_register(self, data):

        username = data.get('username')
        password = data.get('password')
        display_name = data.get('displayName', username)

        success = register_user(
            username,
            password,
            display_name
        )

        if success:

            send_to_client(
                self.client,
                self.server,
                {
                    'type': 'register_success'
                }
            )

            print(f"[REGISTER] {username}")

        else:

            send_to_client(
                self.client,
                self.server,
                {
                    'type': 'register_error',
                    'message': 'Usuário já existe'
                }
            )


    def _handle_login(self, data):

        username = data.get('username')
        password = data.get('password')

        success = authenticate_user(
            username,
            password
        )

        if success:
            self.username = username

            send_to_client(self.client, self.server, {
                'type': 'login_success',
                'username': username,
                'displayName': get_display_name(username)
            })
            
            # --- ADICIONAR ESTA PARTE ---
            # Manda a lista oficial de salas para o cara que acabou de entrar
            from globals import registered_rooms, registered_rooms_lock
            with registered_rooms_lock:
                lista_salas = list(registered_rooms)
                
            send_to_client(self.client, self.server, {
                'type': 'room_list',
                'rooms': lista_salas
            })
            # -----------------------------
            
            print(f"[LOGIN] {username}")
            
        else:

            send_to_client(
                self.client,
                self.server,
                {
                    'type': 'login_error',
                    'message': 'Login inválido'
                }
            )