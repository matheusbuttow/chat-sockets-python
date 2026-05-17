from globals import username_lock, usernames
import json
import os

USERS_FILE = 'users.json'

def get_online_users():
    """Retorna lista de usuários online."""
    with username_lock: #entra no lock
        return list(usernames.keys())

def register_username(username, client_id):
    #registra usuario novo se n tiver
    with username_lock:
        if username in usernames:
            return False #se ja tiver 
        usernames[username] = client_id
        return True

def remove_username(client_id): #procura id do usuario para pegar o nome e eai deletar do dict
    with username_lock:
        to_remove = next((u for u, cid in usernames.items() if cid == client_id), None)
        if to_remove:
            del usernames[to_remove]
            return to_remove
    return None

# Usuários REGISTRADOS (persistência)
def load_users():
    #pega o json
    if not os.path.exists(USERS_FILE):
        with open(USERS_FILE, 'w') as f:
            json.dump({}, f)
        return {}

    with open(USERS_FILE, 'r') as f:
        return json.load(f)

def save_users(users): #salva no arquivo os users
    with open(USERS_FILE, 'w') as f:
        json.dump(users, f, indent=4)

def register_user(username, password, display_name):
    with username_lock:
        users = load_users()#carrega do json
        if username in users:
            return False #se ja tiver retorna False

        users[username] = { 'password': password, 'displayName': display_name}
        save_users(users)
        return True

def authenticate_user(username, password):
    with username_lock:
        users = load_users() #CARREGA  usuarios do json
        if username not in users:
            return False #para registrar primeiro
        return users[username]['password'] == password #return true ou false 

def get_display_name(username):
    users = load_users()
    if username not in users:
        return username
    return users[username].get('displayName', username)