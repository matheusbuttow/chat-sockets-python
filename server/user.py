from globals import username_lock, usernames

import json
import os

USERS_FILE = 'users.json'


# ---------------------------------------------------------- #
# Usuários ONLINE
# ---------------------------------------------------------- #

def get_online_users():
    """Retorna lista de usuários online."""

    with username_lock:
        return list(usernames.keys())


def register_username(username, client_id):

    with username_lock:

        if username in usernames:
            return False

        usernames[username] = client_id
        return True


def remove_username(client_id):

    with username_lock:

        to_remove = next(
            (u for u, cid in usernames.items() if cid == client_id),
            None
        )

        if to_remove:
            del usernames[to_remove]
            return to_remove

    return None


# ---------------------------------------------------------- #
# Usuários REGISTRADOS (persistência)
# ---------------------------------------------------------- #

def load_users():

    if not os.path.exists(USERS_FILE):

        with open(USERS_FILE, 'w') as f:
            json.dump({}, f)

        return {}

    with open(USERS_FILE, 'r') as f:
        return json.load(f)


def save_users(users):

    with open(USERS_FILE, 'w') as f:
        json.dump(users, f, indent=4)


def register_user(username, password, display_name):

    with username_lock:

        users = load_users()

        if username in users:
            return False

        users[username] = {
            'password': password,
            'displayName': display_name
        }

        save_users(users)

        return True


def authenticate_user(username, password):

    with username_lock:

        users = load_users()

        if username not in users:
            return False

        return users[username]['password'] == password


def get_display_name(username):

    users = load_users()

    if username not in users:
        return username

    return users[username].get('displayName', username)