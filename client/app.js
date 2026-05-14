/* ============================================================
   ESTADO DA APLICAÇÃO
============================================================ */
const APP = {
  // Usuário autenticado
  user: null,              // { username, displayName }

  // Sala atual
  currentRoom: null,       // { id, name, icon, desc }

  // Conexão WebSocket
  ws: null,
  connected: false,
  reconnectTimer: null,
  reconnectAttempts: 0,

  // Estado do chat
  messages: {},            // roomId -> [{id, sender, text, ts, system}]
  members: {},             // roomId -> Set de usernames
  typingUsers: {},         // roomId -> Set de usernames
  typingTimer: null,

  // Último emissor de mensagem (para agrupamento visual)
  lastSender: null,

  // Salas disponíveis
  rooms: [],
};



/* ============================================================
   SALAS PADRÃO
============================================================ */
const DEFAULT_ROOMS = [
  { id: 'geral',      name: 'Geral',      icon: '💬', desc: 'Conversa geral para todos os membros', members: 0 },
  { id: 'tech',       name: 'Tech Talk',  icon: '💻', desc: 'Desenvolvimento, código e tecnologia',  members: 0 },
  { id: 'random',     name: 'Aleatório',  icon: '🎲', desc: 'Tópicos variados e off-topic',         members: 0 },
  { id: 'projetos',   name: 'Projetos',   icon: '🚀', desc: 'Discussão de projetos e tarefas',      members: 0 },
  { id: 'anuncios',   name: 'Anúncios',   icon: '📢', desc: 'Comunicados e novidades importantes',  members: 0 },
];

function loadRooms() {
  const stored = localStorage.getItem('nx_rooms');
  if (stored) {
    APP.rooms = JSON.parse(stored);
  } else {
    APP.rooms = [...DEFAULT_ROOMS];
    localStorage.setItem('nx_rooms', JSON.stringify(APP.rooms));
  }
}
function saveRooms() {
  localStorage.setItem('nx_rooms', JSON.stringify(APP.rooms));
}

/* ============================================================
   NAVEGAÇÃO ENTRE TELAS
============================================================ */
function showScreen(name) {
  ['login', 'lobby', 'chat'].forEach(s => {
    document.getElementById('screen-' + s).classList.add('hidden');
  });
  document.getElementById('screen-' + name).classList.remove('hidden');
}

/* ============================================================
   AUTENTICAÇÃO
============================================================ */
function switchTab(tab) {
  document.getElementById('form-login').classList.toggle('hidden', tab !== 'login');
  document.getElementById('form-register').classList.toggle('hidden', tab !== 'register');
  document.getElementById('tab-login').classList.toggle('active', tab === 'login');
  document.getElementById('tab-register').classList.toggle('active', tab === 'register');
}

function handleLogin() {
  const username = document.getElementById('login-username').value.trim().toLowerCase();
  const password = document.getElementById('login-password').value;
  const errEl    = document.getElementById('login-error');

  errEl.classList.add('hidden');

  if (!username || !password) {
    showError(errEl, 'Preencha usuário e senha.');
    return;
  }

  wsSend({
    type: 'login',
    username,
    password
  });
}

function handleRegister() {
  const username    = document.getElementById('reg-username').value.trim().toLowerCase();
  const displayName = document.getElementById('reg-display').value.trim();
  const password    = document.getElementById('reg-password').value;
  const confirm     = document.getElementById('reg-confirm').value;
  const errEl       = document.getElementById('reg-error');

  errEl.classList.add('hidden');

  if (!username || !displayName || !password) {
    showError(errEl, 'Todos os campos são obrigatórios.');
    return;
  }

  if (password !== confirm) {
    showError(errEl, 'As senhas não coincidem.');
    return;
  }

  wsSend({
    type: 'register',
    username,
    displayName,
    password
  });
}

function handleLogout() {
  if (APP.ws) {
    APP.ws.close();
    APP.ws = null;
  }
  APP.user = null;
  clearSession();
  showScreen('login');
}

/* ============================================================
   LOBBY
============================================================ */
function enterLobby() {
  loadRooms();

  // Atualiza UI do topbar
  document.getElementById('lobby-username').textContent = APP.user.displayName || APP.user.username;
  document.getElementById('lobby-avatar').textContent   = getInitials(APP.user.displayName || APP.user.username);

  renderRooms();
  showScreen('lobby');
  connectWebSocket();
}

function renderRooms() {
  const grid = document.getElementById('rooms-grid');
  grid.innerHTML = '';

  if (!APP.rooms.length) {
    grid.innerHTML = '<div class="room-empty-state">Nenhuma sala disponível. Crie a primeira!</div>';
    return;
  }

  APP.rooms.forEach((room, i) => {
    const card = document.createElement('div');
    card.className = 'room-card';
    card.style.animationDelay = (i * 0.06) + 's';
    card.innerHTML = `
      <div class="room-card-header">
        <div class="room-icon">${room.icon}</div>
        <div style="flex:1">
          <div class="room-name">${escHtml(room.name)}</div>
        </div>
        <span class="badge badge-online">
          <span class="dot"></span>${room.members || 0}
        </span>
      </div>
      <div class="room-desc">${escHtml(room.desc || 'Sala de bate-papo')}</div>
      <div class="room-meta">
        <span># ${room.id}</span>
        <span style="color:var(--accent);font-size:12px">Entrar →</span>
      </div>
    `;
    card.onclick = () => joinRoom(room);
    grid.appendChild(card);
  });
}

/* ============================================================
   MODAL CRIAR SALA
============================================================ */
const EMOJI_OPTIONS = ['💬','💻','🎮','🎲','🚀','📢','🎯','🔬','📚','🎵','🎨','🏆','🌍','⚡','🔥'];
let selectedEmoji = EMOJI_OPTIONS[0];

function openCreateModal() {
  selectedEmoji = EMOJI_OPTIONS[0];
  document.getElementById('modal-room-name').value = '';
  document.getElementById('modal-room-desc').value = '';
  document.getElementById('create-room-error').classList.add('hidden');

  const picker = document.getElementById('emoji-picker');
  picker.innerHTML = '';
  EMOJI_OPTIONS.forEach(e => {
    const opt = document.createElement('div');
    opt.className = 'emoji-opt' + (e === selectedEmoji ? ' selected' : '');
    opt.textContent = e;
    opt.onclick = () => {
      selectedEmoji = e;
      picker.querySelectorAll('.emoji-opt').forEach(el => el.classList.remove('selected'));
      opt.classList.add('selected');
    };
    picker.appendChild(opt);
  });

  document.getElementById('modal-create-room').classList.remove('hidden');
  setTimeout(() => document.getElementById('modal-room-name').focus(), 100);
}

function closeCreateModal() {
  document.getElementById('modal-create-room').classList.add('hidden');
}

function submitCreateRoom() {
  const name = document.getElementById('modal-room-name').value.trim();
  const desc = document.getElementById('modal-room-desc').value.trim();
  const errEl = document.getElementById('create-room-error');
  errEl.classList.add('hidden');

  if (!name) { showError(errEl, 'Dê um nome para a sala.'); return; }
  if (name.length < 2) { showError(errEl, 'Nome deve ter ao menos 2 caracteres.'); return; }

  const id = name.toLowerCase().replace(/\s+/g, '-').replace(/[^a-z0-9-]/g, '');
  if (APP.rooms.find(r => r.id === id)) {
    showError(errEl, 'Já existe uma sala com esse nome.'); return;
  }

  const room = { id, name, icon: selectedEmoji, desc, members: 0 };
  APP.rooms.push(room);
  saveRooms();
  renderRooms();
  closeCreateModal();
  showToast('Sala "' + name + '" criada!', 'success');

  // Transmite via WS para outros clientes (se conectado)
  wsSend({ type: 'room_created', room });
}

/* ============================================================
   CHAT — ENTRAR / SAIR DE SALA
============================================================ */
function joinRoom(room) {
  APP.currentRoom = room;
  APP.lastSender  = null;

  // Inicializa estruturas se necessário
  if (!APP.messages[room.id])    APP.messages[room.id]    = [];
  if (!APP.members[room.id])     APP.members[room.id]     = new Set();
  if (!APP.typingUsers[room.id]) APP.typingUsers[room.id] = new Set();

  // Atualiza header do chat
  document.getElementById('chat-room-icon').textContent = room.icon;
  document.getElementById('chat-room-name').textContent = room.name;
  document.getElementById('chat-username').textContent  = APP.user.displayName || APP.user.username;
  document.getElementById('chat-avatar').textContent    = getInitials(APP.user.displayName || APP.user.username);

  // Renderiza histórico existente
  renderMessages();
  renderMembers();

  showScreen('chat');

  // Avisa o servidor
  wsSend({ type: 'join_room', roomId: room.id, username: APP.user.username, displayName: APP.user.displayName || APP.user.username });

  // Foca no input
  setTimeout(() => document.getElementById('msg-input').focus(), 100);
}

function leaveRoom() {
  if (APP.currentRoom) {
    wsSend({ type: 'leave_room', roomId: APP.currentRoom.id, username: APP.user.username });
    APP.currentRoom = null;
  }
  showScreen('lobby');
  renderRooms();
}

/* ============================================================
   ENVIO E RECEPÇÃO DE MENSAGENS
============================================================ */
function sendMessage() {
  const input = document.getElementById('msg-input');
  const text  = input.value.trim();
  if (!text || !APP.currentRoom) return;

  const msg = {
    type: 'message',
    id:   Date.now() + '-' + Math.random().toString(36).slice(2),
    roomId:      APP.currentRoom.id,
    sender:      APP.user.username,
    displayName: APP.user.displayName || APP.user.username,
    text,
    ts: Date.now(),
  };

  // Exibe localmente de imediato
  appendMessage(msg);

  // Envia ao servidor
  wsSend(msg);

  input.value = '';
  autoResize(input);

  // Cancela indicador de digitação
  clearTypingIndicator();
}

function handleMsgKey(e) {
  // Enter envia; Shift+Enter quebra linha
  if (e.key === 'Enter' && !e.shiftKey) {
    e.preventDefault();
    sendMessage();
  }
}

function handleTyping() {
  if (!APP.currentRoom) return;
  wsSend({ type: 'typing', roomId: APP.currentRoom.id, username: APP.user.username });

  clearTimeout(APP.typingTimer);
  APP.typingTimer = setTimeout(clearTypingIndicator, 2000);
}

function clearTypingIndicator() {
  if (!APP.currentRoom) return;
  wsSend({ type: 'stop_typing', roomId: APP.currentRoom.id, username: APP.user.username });
}

/* ============================================================
   RENDERIZAÇÃO — MENSAGENS
============================================================ */
function appendMessage(msg) {
  const roomId = APP.currentRoom?.id;
  if (!roomId) return;

  if (!APP.messages[roomId]) APP.messages[roomId] = [];
  APP.messages[roomId].push(msg);
  renderMessage(msg);
}

function renderMessages() {
  const list = document.getElementById('messages-list');
  list.innerHTML = '';
  APP.lastSender = null;

  const roomId = APP.currentRoom?.id;
  if (!roomId || !APP.messages[roomId]) return;

  APP.messages[roomId].forEach(m => renderMessage(m));
}

function renderMessage(msg) {
  const list  = document.getElementById('messages-list');
  const isMine = msg.sender === APP.user.username;

  // Mensagem de sistema
  if (msg.system) {
    const el = document.createElement('div');
    el.className = 'msg-system';
    el.innerHTML = `<span>${escHtml(msg.text)}</span>`;
    list.appendChild(el);
    APP.lastSender = null;
    scrollBottom();
    return;
  }

  const isNewGroup = APP.lastSender !== msg.sender;
  APP.lastSender   = msg.sender;

  const wrap = document.createElement('div');
  wrap.className = 'msg ' + (isMine ? 'mine' : 'other') + (isNewGroup ? ' msg-group-start' : '');

  if (isNewGroup) {
    const senderEl = document.createElement('div');
    senderEl.className = 'msg-sender';
    senderEl.innerHTML = `
      <span class="name">${escHtml(msg.displayName || msg.sender)}</span>
      <span class="time">${formatTime(msg.ts)}</span>
    `;
    wrap.appendChild(senderEl);
  }

  const bubble = document.createElement('div');
  bubble.className = 'msg-bubble';
  bubble.textContent = msg.text;  // textContent evita XSS
  wrap.appendChild(bubble);

  list.appendChild(wrap);
  scrollBottom();
}

/* ============================================================
   RENDERIZAÇÃO — MEMBROS E TYPING
============================================================ */
function renderMembers() {
  const list   = document.getElementById('member-list');
  const countEl = document.getElementById('chat-member-count');
  list.innerHTML = '';

  const roomId  = APP.currentRoom?.id;
  const members = roomId ? (APP.members[roomId] || new Set()) : new Set();

  // Sempre inclui o próprio usuário
  const allMembers = new Set([APP.user.username, ...members]);
  countEl.textContent = allMembers.size;

  allMembers.forEach(u => {
        const item = document.createElement('div');
        const isMe = u === APP.user.username;
        item.className = 'member-item' + (isMe ? ' me' : '');

        const display = u; // Usamos a variável 'u' direto

        item.innerHTML = `
          <div class="user-avatar">${getInitials(display)}</div>
          <span>${escHtml(display)}${isMe ? ' <span style="color:var(--text-muted);font-size:10px">(você)</span>' : ''}</span>
        `;
        list.appendChild(item);
  });
}

function updateTypingIndicator() {
  const el     = document.getElementById('typing-indicator');
  const roomId = APP.currentRoom?.id;
  const typing = roomId
    ? [...(APP.typingUsers[roomId] || [])].filter(u => u !== APP.user.username)
    : [];

  if (!typing.length) {
    el.innerHTML = '';
    return;
  }

  const names = typing.slice(0, 3).join(', ');
  el.innerHTML = `
    <div class="typing-dots">
      <span></span><span></span><span></span>
    </div>
    <span>${escHtml(names)} está digitando...</span>
  `;
}

/* ============================================================
   WEBSOCKET — CONEXÃO E PROTOCOLO
============================================================ */

/**
 * Conecta ao servidor WebSocket principal.
 * Em caso de falha, tenta servidor secundário (tolerância a falhas).
 *
 * Substitua as URLs pelos endereços reais após o deploy.
 */
// URLs preenchidas dinamicamente via /api/config ao inicializar
let WS_PRIMARY   = 'ws://localhost:8765';
let WS_SECONDARY = 'ws://localhost:8766';

function connectWebSocket(useBackup = false) {
  const url = useBackup ? WS_SECONDARY : WS_PRIMARY;

  try {
    APP.ws = new WebSocket(url);
  } catch(e) {
    // WebSocket não disponível — modo offline
    setConnectionStatus('error');
    return;
  }

  APP.ws.onopen = () => {
    APP.connected = true;
    APP.reconnectAttempts = 0;
    setConnectionStatus('ok');

    // Re-entra na sala se estava em uma
    if (APP.currentRoom) {
      wsSend({ type: 'join_room', roomId: APP.currentRoom.id, username: APP.user.username });
    }
    if (APP.user) {
      wsSend({ type: 'auth', username: APP.user.username });
    }
  };

  APP.ws.onmessage = (event) => {
    try {
      const data = JSON.parse(event.data);
      handleServerMessage(data);
    } catch(e) {
      console.error('[WS] Mensagem inválida:', event.data);
    }
  };

  APP.ws.onclose = () => {
    APP.connected = false;
    setConnectionStatus('warning');

    // Tenta reconectar com backoff exponencial
    const delay = Math.min(1000 * Math.pow(2, APP.reconnectAttempts), 30000);
    APP.reconnectAttempts++;

    APP.reconnectTimer = setTimeout(() => {
      // Após 3 falhas, tenta servidor secundário
      const tryBackup = APP.reconnectAttempts >= 3;
      if (tryBackup) showToast('Tentando servidor de backup...', 'error');
      connectWebSocket(tryBackup);
    }, delay);
  };

  APP.ws.onerror = () => {
    setConnectionStatus('error');
  };
}

/**
 * Trata mensagens recebidas do servidor.
 * O servidor centraliza toda a lógica de roteamento.
 */
function handleServerMessage(data) {
  switch (data.type) {

    case 'message':
      // Apenas exibe se não for do próprio usuário (já renderizou local)
      if (data.sender !== APP.user.username && data.roomId === APP.currentRoom?.id) {
        appendMessage(data);
      }
      break;

    case 'user_joined':
      // Outro usuário entrou na sala
      if (data.roomId === APP.currentRoom?.id && data.username !== APP.user.username) {
        APP.members[data.roomId] = APP.members[data.roomId] || new Set();
        APP.members[data.roomId].add(data.username);
        appendMessage({ system: true, text: `${data.displayName} entrou na sala.`, ts: Date.now() });
        renderMembers();
      }
      break;

    case 'user_left':
      if (data.roomId === APP.currentRoom?.id) {
        APP.members[data.roomId]?.delete(data.username);
        appendMessage({ system: true, text: `${data.displayName} saiu da sala.`, ts: Date.now() });
        renderMembers();
      }
      break;

    case 'typing':
      if (data.roomId === APP.currentRoom?.id && data.username !== APP.user.username) {
        APP.typingUsers[data.roomId] = APP.typingUsers[data.roomId] || new Set();
        APP.typingUsers[data.roomId].add(data.username);
        updateTypingIndicator();
      }
      break;

    case 'stop_typing':
      if (data.roomId === APP.currentRoom?.id) {
        APP.typingUsers[data.roomId]?.delete(data.username);
        updateTypingIndicator();
      }
      break;

    case 'room_list':
      // Servidor envia lista atualizada de salas
      APP.rooms = data.rooms;
      saveRooms();
      renderRooms();
      break;

    case 'room_created':
      if (!APP.rooms.find(r => r.id === data.room.id)) {
        APP.rooms.push(data.room);
        saveRooms();
        renderRooms();
      }
      break;

    case 'member_count':
      // Atualiza contagem de membros por sala
      if (data.roomId === APP.currentRoom?.id) {
        document.getElementById('chat-member-count').textContent = data.count;
      }
      break;

    case 'history':
      // Histórico de mensagens ao entrar na sala
      if (data.roomId === APP.currentRoom?.id) {
        APP.messages[data.roomId] = data.messages;
        renderMessages();
      }
      break;

    case 'error':
      showToast(data.message || 'Erro do servidor.', 'error');
      break;
    
    case 'login_success':
        APP.user = {
            username: data.username,
            displayName: data.displayName
        };

        enterLobby();
        showToast('Login realizado!', 'success');
        break;

    case 'login_error':
        showError(
            document.getElementById('login-error'),
            data.message
        );
        break;

    case 'register_success':
        showToast('Conta criada com sucesso!', 'success');
        switchTab('login');
        break;

    case 'register_error':
        showError(
            document.getElementById('reg-error'),
            data.message
        );
        break;

    default:
      console.log('[WS] Evento desconhecido:', data.type);
  }
}

/** Envia um objeto JSON pelo WebSocket (se conectado) */
function wsSend(obj) {
  if (APP.ws && APP.ws.readyState === WebSocket.OPEN) {
    APP.ws.send(JSON.stringify(obj));
  }
}

/** Atualiza os indicadores visuais de status de conexão */
function setConnectionStatus(state) {
  const dots  = document.querySelectorAll('.conn-dot');
  const texts = ['lobby-conn-text', 'chat-conn-text'];
  const labels = { ok: 'Conectado', warning: 'Reconectando...', error: 'Sem conexão' };

  dots.forEach(d => {
    d.className = 'conn-dot ' + state;
  });
  texts.forEach(id => {
    const el = document.getElementById(id);
    if (el) el.textContent = labels[state] || state;
  });
}

/* ============================================================
   UTILITÁRIOS
============================================================ */
function escHtml(str) {
  return String(str)
    .replace(/&/g,'&amp;')
    .replace(/</g,'&lt;')
    .replace(/>/g,'&gt;')
    .replace(/"/g,'&quot;');
}

function getInitials(name) {
  return (name || '?')
    .split(/\s+/)
    .map(w => w[0])
    .join('')
    .toUpperCase()
    .slice(0, 2);
}

function formatTime(ts) {
  return new Date(ts).toLocaleTimeString('pt-BR', { hour:'2-digit', minute:'2-digit' });
}

function scrollBottom() {
  const list = document.getElementById('messages-list');
  if (list) list.scrollTop = list.scrollHeight;
}

function autoResize(el) {
  el.style.height = 'auto';
  el.style.height = Math.min(el.scrollHeight, 120) + 'px';
}

function showError(el, msg) {
  el.textContent = msg;
  el.classList.remove('hidden');
}

let toastTimer;
function showToast(msg, type = '') {
  const container = document.getElementById('toast-container');
  const toast = document.createElement('div');
  toast.className = 'toast ' + type;
  toast.textContent = msg;
  container.appendChild(toast);
  setTimeout(() => toast.remove(), 4000);
}

/* ============================================================
   INICIALIZAÇÃO
============================================================ */
(async function init() {
  // Fecha modal ao clicar fora
  document.getElementById('modal-create-room').addEventListener('click', function(e) {
    if (e.target === this) closeCreateModal();
  });

  // Tecla Escape fecha modal
  document.addEventListener('keydown', e => {
    if (e.key === 'Escape') closeCreateModal();
  });

  // Busca as URLs dos servidores WebSocket no backend Flask (/api/config).
  // Em produção (Render) isso retorna os endereços wss:// corretos;
  // localmente cai nos valores padrão definidos acima.
  try {
    const res = await fetch('/api/config');
    if (res.ok) {
      const cfg = await res.json();
      WS_PRIMARY   = cfg.ws_primary;
      WS_SECONDARY = cfg.ws_secondary;
    }
  } catch (_) {
    // Sem servidor HTTP (arquivo aberto direto) — mantém os defaults localhost
  }

  showScreen('login');
  connectWebSocket();
})();