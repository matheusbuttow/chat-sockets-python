import threading

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

# Lista oficial de salas do servidor
registered_rooms = [
    {'id': 'geral', 'name': 'Geral', 'icon': '💬', 'desc': 'Conversa geral para todos os membros', 'members': 0},
    {'id': 'tech', 'name': 'Tech Talk', 'icon': '💻', 'desc': 'Desenvolvimento, código e tecnologia', 'members': 0},
    {'id': 'projetos', 'name': 'Projetos', 'icon': '🚀', 'desc': 'Discussão de projetos e tarefas', 'members': 0}
]
registered_rooms_lock = threading.Lock()