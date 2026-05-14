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