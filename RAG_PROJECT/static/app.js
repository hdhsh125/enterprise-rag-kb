/* ── State ─────────────────────────────────────────────────────────── */
const TOKEN_KEY = 'rag_token';
const USER_KEY  = 'rag_user';
const SESSION_KEY = 'rag_session_id';

let token    = localStorage.getItem(TOKEN_KEY);
let userInfo = JSON.parse(localStorage.getItem(USER_KEY) || 'null');
let sessionId = localStorage.getItem(SESSION_KEY);
let ragMode  = 'auto';
let sending  = false;
let authMode = 'login';
let currentAnswerEl = null;  // 当前流式回答的 DOM 元素

/* ── DOM refs ──────────────────────────────────────────────────────── */
const authOverlay  = document.getElementById('auth-overlay');
const appEl        = document.getElementById('app');
const messagesEl   = document.getElementById('messages');
const questionEl   = document.getElementById('question');
const sendBtn      = document.getElementById('send');
const adminSection = document.getElementById('admin-section');
const sourcesSection = document.getElementById('sources-section');
const sourcesList  = document.getElementById('sources-list');
const uploadMsg    = document.getElementById('upload-msg');
const miniDocList  = document.getElementById('mini-doc-list');
const uploadBtn    = document.getElementById('upload-btn');
const historyList  = document.getElementById('history-list');

/* ── Configure marked ──────────────────────────────────────────────── */
if (typeof marked !== 'undefined') {
  marked.setOptions({ breaks: true, gfm: true });
}

/* ── Init ──────────────────────────────────────────────────────────── */
(async function init() {
  if (token && userInfo) {
    try {
      const res = await apiFetch('/api/v1/auth/me');
      if (res.ok) {
        userInfo = await res.json();
        localStorage.setItem(USER_KEY, JSON.stringify(userInfo));
        showApp();
        await loadSessionList();
        // 如果有保存的会话ID，自动加载该会话的消息
        if (sessionId) {
          try {
            const msgRes = await apiFetch(`/api/v1/sessions/${sessionId}/messages`);
            if (msgRes.ok) {
              const data = await msgRes.json();
              renderMessages(data.messages || []);
            }
          } catch (_) {}
        }
        return;
      }
    } catch (_) {}
  }
  showAuthOverlay();
})();

/* ── Auth UI ───────────────────────────────────────────────────────── */
function showAuthOverlay() {
  authOverlay.classList.remove('hidden');
  appEl.classList.add('hidden');
  document.getElementById('auth-username').focus();
}

function showApp() {
  authOverlay.classList.add('hidden');
  appEl.classList.remove('hidden');
  document.getElementById('username-display').textContent = userInfo.username;
  const roleTag = document.getElementById('role-tag');
  roleTag.textContent = userInfo.role === 'admin' ? '管理员' : '普通用户';
  roleTag.className = 'role-tag ' + userInfo.role;

  if (userInfo.role === 'admin') {
    adminSection.style.display = '';
    loadDocList();
  } else {
    adminSection.style.display = 'none';
  }
  questionEl.focus();
}

function switchTab(mode) {
  authMode = mode;
  document.getElementById('tab-login').classList.toggle('active', mode === 'login');
  document.getElementById('tab-register').classList.toggle('active', mode === 'register');
  document.getElementById('auth-submit-btn').textContent = mode === 'login' ? '登录' : '注册';
  document.getElementById('auth-error').textContent = '';
  document.getElementById('auth-password').value = '';
}

async function submitAuth(e) {
  e.preventDefault();
  const username = document.getElementById('auth-username').value.trim();
  const password = document.getElementById('auth-password').value;
  const errEl = document.getElementById('auth-error');
  const btn = document.getElementById('auth-submit-btn');

  errEl.textContent = '';
  btn.disabled = true;

  const endpoint = authMode === 'login' ? '/api/v1/auth/login' : '/api/v1/auth/register';
  try {
    const res = await fetch(endpoint, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ username, password }),
    });
    const data = await res.json();
    if (!res.ok) {
      errEl.textContent = formatError(data.detail) || '操作失败';
      return;
    }
    token = data.access_token;
    userInfo = { username: data.username, role: data.role };
    localStorage.setItem(TOKEN_KEY, token);
    localStorage.setItem(USER_KEY, JSON.stringify(userInfo));
    showApp();
    await loadSessionList();
  } catch (err) {
    errEl.textContent = '网络错误: ' + err.message;
  } finally {
    btn.disabled = false;
  }
}

function logout() {
  localStorage.removeItem(TOKEN_KEY);
  localStorage.removeItem(USER_KEY);
  localStorage.removeItem(SESSION_KEY);
  token = null; userInfo = null; sessionId = null;
  messagesEl.innerHTML = '<div class="message assistant">你好！我是<strong>半导体知识库助手</strong>，专注于半导体材料、芯片制造、光刻技术等领域。</div>';
  resetWorkflow();
  showAuthOverlay();
}

/* ── RAG mode ──────────────────────────────────────────────────────── */
function setMode(mode) {
  ragMode = mode;
  document.querySelectorAll('.mode-btn').forEach(btn => {
    btn.classList.toggle('active', btn.dataset.mode === mode);
  });
}

/* ── Session History ──────────────────────────────────────────────── */
async function loadSessionList() {
  try {
    const res = await apiFetch('/api/v1/sessions');
    if (!res.ok) return;
    const data = await res.json();
    renderSessionList(data.sessions || []);
  } catch (_) {}
}

function renderSessionList(sessions) {
  historyList.innerHTML = '';
  if (!sessions.length) {
    historyList.innerHTML = '<div class="history-empty">暂无历史会话</div>';
    return;
  }
  sessions.forEach(s => {
    const item = document.createElement('div');
    item.className = 'history-item' + (s.session_id === sessionId ? ' active' : '');
    item.dataset.sessionId = s.session_id;
    const timeStr = formatTime(s.last_active);
    item.innerHTML = `
      <div class="hi-content" onclick="switchSession('${escHtml(s.session_id)}')">
        <div class="hi-title">${escHtml(s.title)}</div>
        <div class="hi-time">${timeStr}</div>
      </div>
      <button class="hi-del" onclick="event.stopPropagation();deleteSession('${escHtml(s.session_id)}')" title="删除会话">删除</button>
    `;
    historyList.appendChild(item);
  });
}

async function switchSession(sid) {
  if (sending) return;
  sessionId = sid;
  localStorage.setItem(SESSION_KEY, sessionId);

  // 高亮当前会话
  document.querySelectorAll('.history-item').forEach(el => {
    el.classList.toggle('active', el.dataset.sessionId === sid);
  });

  // 从服务端加载消息
  try {
    const res = await apiFetch(`/api/v1/sessions/${sid}/messages`);
    if (!res.ok) {
      messagesEl.innerHTML = '<div class="message assistant">加载历史消息失败</div>';
      return;
    }
    const data = await res.json();
    renderMessages(data.messages || []);
  } catch (_) {
    messagesEl.innerHTML = '<div class="message assistant">加载历史消息失败</div>';
  }
  resetWorkflow();
}

function renderMessages(messages) {
  messagesEl.innerHTML = '<div class="message assistant">你好！我是<strong>半导体知识库助手</strong>，专注于半导体材料、芯片制造、光刻技术等领域。</div>';
  messages.forEach(m => {
    if (m.role === 'user') {
      appendMessage('user', m.content);
    } else if (m.role === 'assistant') {
      appendMarkdownMessage('assistant', m.content);
    }
  });
  messagesEl.scrollTop = messagesEl.scrollHeight;
}

async function deleteSession(sid) {
  if (!confirm('确认删除此会话？此操作不可恢复。')) return;
  try {
    const res = await apiFetch(`/api/v1/sessions/${sid}`, { method: 'DELETE' });
    if (!res.ok) { toast('删除失败', 'error'); return; }
    // 如果删除的是当前会话，清空聊天区
    if (sid === sessionId) {
      sessionId = null;
      localStorage.removeItem(SESSION_KEY);
      messagesEl.innerHTML = '<div class="message assistant">新对话已开始。请输入你的问题。</div>';
      resetWorkflow();
    }
    await loadSessionList();
  } catch (err) {
    toast('网络错误: ' + err.message, 'error');
  }
}

function newChat() {
  localStorage.removeItem(SESSION_KEY);
  sessionId = null;
  messagesEl.innerHTML = '<div class="message assistant">新对话已开始。请输入你的问题。</div>';
  resetWorkflow();
  // 取消历史列表中的高亮
  document.querySelectorAll('.history-item').forEach(el => el.classList.remove('active'));
}

function formatTime(timestamp) {
  const d = new Date(timestamp * 1000);
  const now = new Date();
  const diffMs = now - d;
  const diffMin = Math.floor(diffMs / 60000);
  if (diffMin < 1) return '刚刚';
  if (diffMin < 60) return diffMin + '分钟前';
  const diffHour = Math.floor(diffMin / 60);
  if (diffHour < 24) return diffHour + '小时前';
  const diffDay = Math.floor(diffHour / 24);
  if (diffDay < 7) return diffDay + '天前';
  return d.toLocaleDateString('zh-CN');
}

/* ── Workflow visualization ────────────────────────────────────────── */
function resetWorkflow() {
  document.querySelectorAll('.wf-node').forEach(el => {
    el.classList.remove('active', 'done');
  });
  sourcesSection.style.display = 'none';
  sourcesList.innerHTML = '';
}

function highlightNode(nodeName) {
  // Mark previous active nodes as done
  document.querySelectorAll('.wf-node.active').forEach(el => {
    el.classList.remove('active');
    el.classList.add('done');
  });
  const node = document.querySelector(`.wf-node[data-node="${nodeName}"]`);
  if (node) {
    node.classList.add('active');
    node.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
  }
}

function allNodesDone() {
  document.querySelectorAll('.wf-node.active').forEach(el => {
    el.classList.remove('active');
    el.classList.add('done');
  });
}

/* ── SSE Streaming Chat ────────────────────────────────────────────── */
sendBtn.addEventListener('click', sendMessage);
questionEl.addEventListener('keydown', e => {
  if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); sendMessage(); }
});

async function sendMessage() {
  if (sending || !token) return;
  const q = questionEl.value.trim();
  if (!q) return;

  sending = true;
  sendBtn.disabled = true;
  questionEl.value = '';

  appendMessage('user', q);
  currentAnswerEl = appendMessage('assistant', '⏳ 思考中...', true);
  resetWorkflow();

  try {
    const res = await fetch('/api/v1/chat/stream', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': 'Bearer ' + token,
      },
      body: JSON.stringify({ question: q, session_id: sessionId, rag_mode: ragMode }),
    });

    if (res.status === 401) { logout(); return; }
    if (!res.ok) {
      const errText = await res.text();
      let errMsg = '请求失败';
      try { errMsg = JSON.parse(errText).detail || errMsg; } catch (_) {}
      currentAnswerEl.innerHTML = '<span style="color:#c62828">' + escHtml(errMsg) + '</span>';
      currentAnswerEl.classList.remove('thinking');
      allNodesDone();
      return;
    }

    const reader = res.body.getReader();
    const decoder = new TextDecoder();
    let buffer = '';
    let answerText = '';

    while (true) {
      const { done, value } = await reader.read();
      if (done) break;
      buffer += decoder.decode(value, { stream: true });

      // Parse SSE lines
      const lines = buffer.split('\n');
      buffer = lines.pop() || ''; // keep incomplete line in buffer

      let eventType = '';
      for (const line of lines) {
        if (line.startsWith('event: ')) {
          eventType = line.slice(7).trim();
        } else if (line.startsWith('data: ')) {
          const dataStr = line.slice(6);
          try {
            const data = JSON.parse(dataStr);
            handleSSEEvent(eventType, data);
            if (eventType === 'token') {
              answerText += data.token || '';
            }
            if (eventType === 'done' && data.answer) {
              answerText = data.answer;
            }
          } catch (_) {}
          eventType = '';
        }
      }
    }

    // Finalize
    if (currentAnswerEl) {
      currentAnswerEl.classList.remove('thinking');
      if (answerText) {
        currentAnswerEl.innerHTML = renderMarkdown(answerText);
      }
      allNodesDone();
    }

  } catch (err) {
    if (currentAnswerEl) {
      currentAnswerEl.innerHTML = '<span style="color:#c62828">网络错误: ' + escHtml(err.message) + '</span>';
      currentAnswerEl.classList.remove('thinking');
    }
    allNodesDone();
  } finally {
    sending = false;
    sendBtn.disabled = false;
    questionEl.focus();
    // 刷新历史会话列表
    await loadSessionList();
  }
}

function handleSSEEvent(event, data) {
  switch (event) {
    case 'node_start':
      highlightNode(data.node);
      // Update thinking text
      if (currentAnswerEl && currentAnswerEl.classList.contains('thinking')) {
        currentAnswerEl.textContent = data.label || '处理中...';
      }
      break;

    case 'node_complete':
      // Keep node highlighted until next one starts
      break;

    case 'token':
      if (currentAnswerEl) {
        if (currentAnswerEl.classList.contains('thinking')) {
          currentAnswerEl.classList.remove('thinking');
          currentAnswerEl.textContent = '';
        }
        currentAnswerEl.textContent += data.token || '';
        messagesEl.scrollTop = messagesEl.scrollHeight;
      }
      break;

    case 'sources':
      if (data.documents && data.documents.length > 0) {
        sourcesSection.style.display = '';
        sourcesList.innerHTML = data.documents.map(doc =>
          `<div class="source-card">
            <div class="src-title">${escHtml(doc.title || '未知来源')}</div>
            <div class="src-preview">${escHtml(doc.preview || '')}</div>
          </div>`
        ).join('');
      }
      break;

    case 'done':
      if (data.session_id) {
        sessionId = data.session_id;
        localStorage.setItem(SESSION_KEY, sessionId);
      }
      break;

    case 'error':
      if (currentAnswerEl) {
        currentAnswerEl.innerHTML = '<span style="color:#c62828">错误: ' + escHtml(data.message || '未知错误') + '</span>';
        currentAnswerEl.classList.remove('thinking');
      }
      allNodesDone();
      toast(data.message || '请求失败', 'error');
      break;
  }
}

/* ── Markdown rendering ────────────────────────────────────────────── */
function renderMarkdown(text) {
  if (typeof marked !== 'undefined') {
    try { return marked.parse(text); } catch (_) {}
  }
  return escHtml(text).replace(/\n/g, '<br>');
}

function appendMarkdownMessage(role, text) {
  const div = document.createElement('div');
  div.className = 'message ' + role;
  div.innerHTML = renderMarkdown(text);
  messagesEl.appendChild(div);
  return div;
}

function appendMessage(role, text, isThinking = false) {
  const div = document.createElement('div');
  div.className = 'message ' + role + (isThinking ? ' thinking' : '');
  div.textContent = text;
  messagesEl.appendChild(div);
  messagesEl.scrollTop = messagesEl.scrollHeight;
  return div;
}

/* ── Admin: document management ────────────────────────────────────── */
async function loadDocList() {
  try {
    const res = await apiFetch('/api/v1/documents');
    if (!res.ok) return;
    const docs = await res.json();
    renderMiniDocList(docs);
  } catch (_) {}
}

function renderMiniDocList(docs) {
  miniDocList.innerHTML = '';
  if (!docs.length) {
    miniDocList.innerHTML = '<div style="font-size:.78rem;color:#aaa;padding:4px 0">暂无文档</div>';
    return;
  }
  docs.forEach(doc => {
    const item = document.createElement('div');
    item.className = 'mini-doc-item';
    const date = new Date(doc.uploaded_at * 1000).toLocaleDateString('zh-CN');
    item.innerHTML = `
      <span title="${escHtml(doc.filename)}" style="overflow:hidden;text-overflow:ellipsis;white-space:nowrap;flex:1;min-width:0">${escHtml(doc.filename)}</span>
      <span style="color:#aaa;margin:0 8px;white-space:nowrap">${doc.chunk_count}块·${date}</span>
      <button class="del-btn" onclick="deleteDoc('${escHtml(doc.doc_id)}','${escHtml(doc.filename)}')">删除</button>
    `;
    miniDocList.appendChild(item);
  });
}

async function uploadDoc() {
  const fileInput = document.getElementById('doc-file-input');
  const file = fileInput.files[0];
  if (!file) { uploadMsg.textContent = '请先选择文件'; return; }

  uploadBtn.disabled = true;
  uploadMsg.textContent = '上传中...';

  const formData = new FormData();
  formData.append('file', file);

  try {
    const res = await fetch('/api/v1/documents', {
      method: 'POST',
      headers: { 'Authorization': 'Bearer ' + token },
      body: formData,
    });
    const data = await res.json();
    if (!res.ok) {
      uploadMsg.textContent = '上传失败: ' + (data.detail || res.statusText);
      return;
    }
    uploadMsg.textContent = `✓ ${data.filename} 上传成功，共 ${data.chunks_added} 个向量块`;
    fileInput.value = '';
    await loadDocList();
  } catch (err) {
    uploadMsg.textContent = '网络错误: ' + err.message;
  } finally {
    uploadBtn.disabled = false;
  }
}

async function deleteDoc(docId, filename) {
  if (!confirm(`确认删除文档「${filename}」？此操作将同时清除 Milvus 中的向量数据，不可恢复。`)) return;
  try {
    const res = await apiFetch(`/api/v1/documents/${docId}`, { method: 'DELETE' });
    const data = await res.json();
    if (!res.ok) { toast(data.detail || '删除失败', 'error'); return; }
    uploadMsg.textContent = data.message;
    await loadDocList();
  } catch (err) {
    toast('网络错误: ' + err.message, 'error');
  }
}

/* ── Helpers ───────────────────────────────────────────────────────── */
async function apiFetch(url, options = {}) {
  const res = await fetch(url, {
    ...options,
    headers: {
      'Content-Type': 'application/json',
      'Authorization': token ? 'Bearer ' + token : '',
      ...(options.headers || {}),
    },
  });
  // 统一处理 401 Token 过期
  if (res.status === 401) {
    logout();
    throw new Error('登录已过期，请重新登录');
  }
  return res;
}

function escHtml(str) {
  return String(str).replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;').replace(/"/g,'&quot;').replace(/'/g,'&#39;');
}

function formatError(detail) {
  if (!detail) return null;
  if (typeof detail === 'string') return detail;
  if (Array.isArray(detail)) return detail.map(d => d.msg || JSON.stringify(d)).join('; ');
  return detail.msg || JSON.stringify(detail);
}

function toast(msg, type = '') {
  const el = document.getElementById('toast');
  el.textContent = msg;
  el.className = 'toast show ' + type;
  clearTimeout(el._timeout);
  el._timeout = setTimeout(() => { el.classList.remove('show'); }, 3000);
}
