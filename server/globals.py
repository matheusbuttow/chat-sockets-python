import threading

"""
Módulo de Variáveis Globais (Memória Compartilhada)
Funciona como o "banco de dados em memória" do servidor. 
Armazena o estado atual dos clientes, salas e mensagens.
"""

#Dicionário que mapeia o ID único da conexão ao objeto do cliente e sua Thread dedicada.
#Formato: { client_id: {'client': objeto_websocket, 'thread': objeto_ClientThread} }
clients = {} 
clients_lock = threading.Lock()

#Dicionário que mapeia o ID da sala para um conjunto (set) de IDs de clientes presentes nela.
#Formato: { 'geral': {'client_id_1', 'client_id_2'} }
rooms = {}
rooms_lock = threading.Lock()

#Dicionário que guarda o histórico das últimas 50 mensagens de cada sala.
#Formato: { 'geral': [ {msg1}, {msg2} ] }
room_history = {}
history_lock = threading.Lock()

#Dicionário que mapeia o nome de usuário escolhido para o ID da conexão.
#Garante que não existam dois usuários com o mesmo apelido simultaneamente.
#Formato: { 'luis_henrique': 'client_id_1' }
usernames = {}
username_lock = threading.Lock()

#Lista oficial de salas fixas disponíveis no servidor ao iniciar.
registered_rooms = [
    {'id': 'geral', 'name': 'Geral', 'icon': '💬', 'desc': 'Conversa geral para todos os membros', 'members': 0},
    {'id': 'tech', 'name': 'Tech Talk', 'icon': '💻', 'desc': 'Desenvolvimento, código e tecnologia', 'members': 0},
    {'id': 'projetos', 'name': 'Projetos', 'icon': '🚀', 'desc': 'Discussão de projetos e tarefas', 'members': 0}
]
registered_rooms_lock = threading.Lock()