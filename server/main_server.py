"""
Servidor WebSocket Principal — NexusChat (porta 8765)
Gerencia conexões de múltiplos clientes, salas de chat e histórico de mensagens.
Cada cliente recebe uma thread dedicada para processamento assíncrono de mensagens.
"""

from websocket_server import WebsocketServer
from websocket import (
    on_new_client,
    on_client_left,
    on_message
)
import threading
import os


def start_server():
    """Inicializa e executa o servidor WebSocket.
    A porta é lida da variável de ambiente PORT (usada pelo Render)
    ou cai no padrão 8765 para execução local.
    """
    port = int(os.environ.get('PORT', 8765))
    server = WebsocketServer(host='0.0.0.0', port=port)
    server.set_fn_new_client(on_new_client)
    server.set_fn_client_left(on_client_left)
    server.set_fn_message_received(on_message)
    print(f"[SERVIDOR] WebSocket rodando na porta {port}")
    server.run_forever()


if __name__ == '__main__':
    # Roda o servidor em uma thread separada para permitir expansão futura
    server_thread = threading.Thread(target=start_server, daemon=True)
    server_thread.start()
    print("[MAIN] Servidor iniciado — pressione Ctrl+C para encerrar")
    server_thread.join()
