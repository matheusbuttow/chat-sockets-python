# Chat Cangu

Chat em tempo real com WebSockets, múltiplos usuários e tolerância a falhas.

## Requisitos

- Python 3.8+
- Dependências listadas em `requirements.txt`

## Instalação

```bash
pip install -r requirements.txt
```

## Como executar

O sistema possui três processos independentes. Abra **três terminais**:

### Terminal 1 — Servidor WebSocket principal (porta 8765)

```bash
python server/main_server.py
```

### Terminal 2 — Servidor de backup (porta 8766)

```bash
python server/backup_server.py
```

O servidor de backup monitora o principal a cada 5 segundos. Se o principal cair, os clientes reconectam automaticamente no backup.

### Terminal 3 — Servidor HTTP (interface web, porta 5000)

```bash
python http_server.py
```

Acesse **http://localhost:5000** no navegador.


(Dica: pressione Ctrl + D na interface do chat para abrir o terminal oculto de debug de rede).

## Estrutura do projeto
  
├── http_server.py       # Servidor HTTP Flask (porta 5000)
├── requirements.txt
├── render.yaml          # Configuração para deploy na nuvem
├── README.md
├── server/
|   ├── backup_server.py # Servidor de backup (porta 8766)
│   ├── main_server.py   # Servidor WebSocket principal (porta 8765)
│   ├── client_thread.py # Lógica de threads independentes por cliente
│   ├── globals.py       # Memória compartilhada e Locks de sincronização
│   ├── room.py          # Gerenciamento das salas do chat
│   ├── user.py          # Autenticação e persistência
│   ├── websocket.py     # Lógica central e eventos do WebSocket
│   └── users.json       # Banco de dados local gerado dinamicamente
└── client/
    ├── index.html       # Interface web (SPA)
    ├── style.css        # Estilos visuais
    ├── app.js           # Lógica do frontend e concorrência (Event Loop)
    └── fundo-cangucu.jpg # Imagem customizada de fundo
```

## Tolerância a falhas

- O frontend tenta reconectar no servidor principal com backoff exponencial (1s → 2s → 4s… até 30s).
- Após 3 tentativas falhas, conecta automaticamente no servidor de backup (porta 8766).
- O `backup_server.py` mantém o mesmo protocolo do principal e pode ser executado em paralelo.
