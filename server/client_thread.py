from globals import *
from room import *
from user import register_username,register_user,authenticate_user,get_display_name
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
        '''
        Funcionamento principal do codigo, fica lendo fila de mensagens e direcionando para a funcao
        correta com base no type recebido no Json.
        '''
        print(f"[THREAD] Iniciada para cliente {self.client['id']}")

        while self.running:
            try:
                # Aguarda próxima mensagem (timeout para checar self.running)
                data = self.message_queue.get(timeout=1)

                msg_type = data.get('type') #pega o tipo da mensagem

                if msg_type == 'register': #manda mensagem para a funcao correta
                    self._handle_register(data)

                elif msg_type == 'login':
                    self._handle_login(data)

                elif msg_type == 'message':
                    self._handle_message(data)

                elif msg_type == 'join_room':
                    self._handle_join(data)

                elif msg_type == 'leave_room':
                    self._handle_leave(data)

                elif msg_type == 'typing': #se digitando recebe stop como false
                    self._handle_typing(data, stop=False)

                elif msg_type == 'stop_typing': #se parou de digitar stop recebe true
                    self._handle_typing(data, stop=True)

                elif msg_type == 'room_created':
                    self._handle_room_created(data)

                elif msg_type == 'auth':
                    self.username = data.get('username')

                    #registra o cara de volta na memória do servidor
                    register_username(self.username, self.client['id'])

            except queue.Empty: #para o codigo nao travar na escuta
                continue

        print(f"[THREAD FINALIZADA] Cliente {self.client['id']}")

    # funcoes internas que tratam oq cada tipo de mensagem faz
    def _handle_room_created(self, data):    
        nova_sala = data['room']
        
        # 1. O servidor anota a nova sala na memória dele
        #usar o with pois ele garante o acquire e o release seguro sem deadlock
        with registered_rooms_lock:
            # Verifica se já não existe para evitar duplicata
            if not any(r['id'] == nova_sala['id'] for r in registered_rooms):
                registered_rooms.append(nova_sala)
        
        # 2. Avisa quem já está online agora
        self.server.send_message_to_all(json.dumps(data))
        print(f"[SALA CRIADA] Sala {nova_sala['name']} anunciada no servidor")

    def _handle_message(self, data):
        """Processa e retransmite uma mensagem de chat para toda a sala."""
        #pega as informacoes da mensagem para transformar em um envelope para mandar para os clientes
        username = data.get('username') or data.get('sender')
        displayName = data.get('displayName', username)
        text = data.get('text')
        room= data.get('roomId') or data.get('room')

        print(f"[CHAT] [{room}] {username}: {text}")

        #cria o json q sera enviado para todos
        response = {'type': 'message','sender': username,'displayName': displayName,'roomId': room,'text':text,'ts':data.get('ts'),}

        # Salva no histórico (máximo 50 mensagens por sala)
        with history_lock:
            room_history.setdefault(room, []).append(response)
            if len(room_history[room]) > 50:
                room_history[room].pop(0) #tira se passar de 50

        send_to_room(room, self.server, json.dumps(response)) #manda mensagem para todos daquela sala

    def _handle_join(self, data):
        """Registra o usuário na sala e envia o histórico."""

        username = data.get('username')
        displayName = data.get('displayName', username)
        room = data.get('roomId') or data.get('room')

        # PRIMEIRO JOIN da conexão
        if self.username is None: 
            success = register_username( username, self.client['id'] ) #tenta registrar

            if not success: #se ja esta em uso retorna com erro para o front por na tela
                send_to_client(self.client,self.server,
                    {'type': 'error',
                    'message': 'Username já está em uso'})
                return

            self.username = username
            from websocket import broadcast_online_users
            # atualiza online users
            broadcast_online_users(self.server) #se conectou mostra a todos que conectou

        # impede entrar 2x na mesma sala
        with rooms_lock:
            if room in rooms and self.client['id'] in rooms[room]: #se o client ja estiver na sala return para impedir
                return

        join_room(self.client['id'], room) #se n tiver ele entra na sala

        print(f"[JOIN] {username} entrou em '{room}'")

        # histórico
        with history_lock: #carrega historico
            history = list(room_history.get(room, []))
        #manda historico pro novo client
        send_to_client( self.client, self.server,
            {'type': 'history',
            'roomId': room,
            'messages': history})

        # avisa sala que tem gente nova
        send_to_room( room, self.server,
            json.dumps({
                'type': 'user_joined',
                'username': username,
                'displayName': displayName,
                'roomId': room}) )

        # Descobre quem já está na sala para avisar o novato
        membros_nomes = []
        with rooms_lock:
            # Pega os IDs de quem está na sala
            membros_ids = list(rooms.get(room, []))
            
        with username_lock:
            # Transforma os IDs em Nomes de Usuário
            for cid in membros_ids:
                nome = next((u for u, c in usernames.items() if c == cid), None)
                if nome:
                    membros_nomes.append(nome)
                    
        # Manda a lista só pra quem acabou de entrar
        send_to_client(self.client, self.server, {
            'type': 'room_members',
            'roomId': room,
            'members': membros_nomes})

    def _handle_leave(self, data):
        """Remove o usuário da sala e notifica os membros restantes."""
        username = data.get('username')
        displayName = data.get('displayName', username)
        room = data.get('roomId') or data.get('room')

        leave_room(self.client['id'], room)
        print(f"[LEAVE] {username} saiu de '{room}'")

        #mandar pra sala que o client saiu
        send_to_room(room, self.server,
            json.dumps({'type': 'user_left', 'username': username,
                        'displayName': displayName, 'roomId': room}))

    def _handle_typing(self, data, stop):
        """Repassa o indicador de digitação (ou parada) para os demais da sala."""
        username = data.get('username')
        room = data.get('roomId') or data.get('room')
        msg_type = 'stop_typing' if stop else 'typing'

        #manda pra todos da sala se client esta digitando
        send_to_room(room, self.server,
                     json.dumps({'type': msg_type, 'username': username, 'roomId': room}))

    def add_message(self, message):
        """Enfileira uma mensagem para processamento pela thread."""
        self.message_queue.put(message)

    def stop(self):
        """Sinaliza para a thread encerrar seu loop."""
        self.running = False

    def _handle_register(self, data):
        """Cria uma conta nova salvando no arquivo users.json."""
        username = data.get('username')
        password = data.get('password')
        display_name = data.get('displayName', username)

        #tenta registrar novo cliente
        success = register_user(username,password,display_name)

        if success: #se conseguir
            send_to_client(self.client, self.server, {'type': 'register_success'}) #manda q conseguiu
            print(f"[REGISTER] {username}") 

        else: #se nao conseguir (ja tiver o nome registrado)
            send_to_client( self.client, self.server, {'type': 'register_error','message': 'Usuário já existe'})

    def _handle_login(self, data):
        """Valida as credenciais do usuário."""
        username = data.get('username')
        password = data.get('password')

        success = authenticate_user(username,password)

        if success: #se colocou o login certo
            self.username = username
            # Se deu bom, manda os dados dele de volta
            send_to_client(self.client, self.server, {'type': 'login_success','username': username,'displayName': get_display_name(username)})
            
            # Manda a lista oficial de salas para ele poder escolher onde entrar
            with registered_rooms_lock:
                lista_salas = list(registered_rooms)
                
            send_to_client(self.client, self.server, {'type': 'room_list', 'rooms': lista_salas})
            print(f"[LOGIN] {username}")
            
        else:
            send_to_client( self.client,self.server, {'type': 'login_error', 'message': 'Login inválido'})