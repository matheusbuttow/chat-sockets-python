from websocket_server import WebsocketServer
from websocket import on_new_client, on_client_left, on_message
import os

def start_server():
    port = int(os.environ.get('PORT', 8765))
    
    server = WebsocketServer(host='0.0.0.0', port=port)
    
    server.set_fn_new_client(on_new_client)
    server.set_fn_client_left(on_client_left)
    server.set_fn_message_received(on_message)
    
    print(f"[SERVIDOR] WebSocket do Chat Cangu rodando na porta {port}")
    server.run_forever()

if __name__ == '__main__':
    start_server()