"""
Servidor HTTP — Chat Cangu
Serve a interface web (client/index.html) e expõe um endpoint de configuração
que informa ao frontend as URLs dos servidores WebSocket.

Localmente:  http://localhost:5000
No Render:   a URL pública gerada pelo Render

Variáveis de ambiente (configurar no painel do Render):
  PORT           - porta atribuída pelo Render (obrigatória em produção)
  WS_PRIMARY     - URL wss:// do servidor WebSocket principal
  WS_SECONDARY   - URL wss:// do servidor WebSocket de backup
"""

from flask import Flask, send_from_directory, jsonify
import os

app = Flask(__name__)

CLIENT_DIR = os.path.join(os.path.dirname(__file__), 'client')

# URLs dos servidores WebSocket — lidas de env vars com fallback para localhost
WS_PRIMARY   = os.environ.get('WS_PRIMARY',   'ws://localhost:8765')
WS_SECONDARY = os.environ.get('WS_SECONDARY', 'ws://localhost:8766')


@app.route('/')
def index():
    """Serve a página principal do chat."""
    return send_from_directory(CLIENT_DIR, 'index.html')


@app.route('/api/config')
def config():
    """
    Retorna as URLs dos servidores WebSocket em JSON.
    O frontend chama este endpoint ao inicializar para saber onde conectar.
    """
    return jsonify({
        'ws_primary':   WS_PRIMARY,
        'ws_secondary': WS_SECONDARY,
    })


@app.route('/<path:filename>')
def static_files(filename):
    """Serve arquivos estáticos da pasta client/."""
    return send_from_directory(CLIENT_DIR, filename)


if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    print(f"[HTTP] Servidor web rodando em http://localhost:{port}")
    print(f"[HTTP] WS primário : {WS_PRIMARY}")
    print(f"[HTTP] WS backup   : {WS_SECONDARY}")
    app.run(host='0.0.0.0', port=port, threaded=True)
