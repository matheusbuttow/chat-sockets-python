from websocket_server import WebsocketServer
from websocket import on_new_client, on_client_left, on_message
import threading
import socket
import time
import os

# Configurações de portas e hosts
PRIMARY_HOST = os.environ.get('PRIMARY_HOST', 'localhost')
PRIMARY_PORT = int(os.environ.get('PRIMARY_PORT', 8765))
BACKUP_PORT = int(os.environ.get('PORT', 8766))

def is_primary_alive():
    try:
        with socket.create_connection((PRIMARY_HOST, PRIMARY_PORT), timeout=2):
            return True
    except OSError:
        return False

def monitor_primary():
    was_alive = True
    print(f"[MONITOR] Vigiando servidor principal em {PRIMARY_HOST}:{PRIMARY_PORT}")
    
    while True:
        alive = is_primary_alive()
        
        if was_alive and not alive:
            print(f"[MONITOR] *** Servidor principal caiu! Backup assumindo na porta {BACKUP_PORT} ***")
            
        if not was_alive and alive:
            print("[MONITOR] Servidor principal voltou ao ar.")
            
        was_alive = alive
        time.sleep(5)

def start_backup_server():
    server = WebsocketServer(host='0.0.0.0', port=BACKUP_PORT)
    server.set_fn_new_client(on_new_client)
    server.set_fn_client_left(on_client_left)
    server.set_fn_message_received(on_message)
    print(f"[BACKUP] Servidor reserva rodando na porta {BACKUP_PORT}")
    server.run_forever()

if __name__ == '__main__':
    monitor_thread = threading.Thread(target=monitor_primary, daemon=True)
    monitor_thread.start()

    start_backup_server()