# NexusChat

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
python backup_server.py
```

O servidor de backup monitora o principal a cada 5 segundos. Se o principal cair, os clientes reconectam automaticamente no backup.

### Terminal 3 — Servidor HTTP (interface web, porta 5000)

```bash
python http_server.py
```

Acesse **http://localhost:5000** no navegador.

## Estrutura do projeto

```
├── server/
│   └── main_server.py   # Servidor WebSocket principal (porta 8765)
├── client/
│   └── index.html       # Interface web (SPA)
├── backup_server.py     # Servidor de backup (porta 8766)
├── http_server.py       # Servidor HTTP Flask (porta 5000)
├── requirements.txt
└── README.md
```

## Tolerância a falhas

- O frontend tenta reconectar no servidor principal com backoff exponencial (1s → 2s → 4s… até 30s).
- Após 3 tentativas falhas, conecta automaticamente no servidor de backup (porta 8766).
- O `backup_server.py` mantém o mesmo protocolo do principal e pode ser executado em paralelo.
