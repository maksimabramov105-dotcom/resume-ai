// popup.js — АвтоОтклик Chrome Extension popup logic
// Extracted from inline script to comply with Manifest V3 CSP (no inline scripts allowed)

const API_BASE = 'https://resumeai-bot.ru';
const TIMEOUT_MS = 10000;

const loadingSection   = document.getElementById('loadingSection');
const loginSection     = document.getElementById('loginSection');
const dashboardSection = document.getElementById('dashboardSection');
const loginBtn         = document.getElementById('loginBtn');
const loginError       = document.getElementById('loginError');
const logoutBtn        = document.getElementById('logoutBtn');
const emailInput       = document.getElementById('emailInput');
const passwordInput    = document.getElementById('passwordInput');

function showSection(name) {
  loadingSection.classList.add('hidden');
  loginSection.classList.add('hidden');
  dashboardSection.classList.add('hidden');
  if (name === 'loading')   loadingSection.classList.remove('hidden');
  if (name === 'login')     loginSection.classList.remove('hidden');
  if (name === 'dashboard') dashboardSection.classList.remove('hidden');
}

function setPlanBadge(plan) {
  const el = document.getElementById('planBadge');
  el.textContent = plan || 'free';
  el.className = 'plan-badge plan-' + (plan || 'free');
}

function setStatus(active, label) {
  const dot  = document.getElementById('statusDot');
  const text = document.getElementById('statusText');
  dot.className    = 'status-dot ' + (active ? 'active' : 'inactive');
  text.textContent = label;
}

// Fetch with timeout — avoids hanging indefinitely
async function fetchWithTimeout(url, options = {}) {
  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), TIMEOUT_MS);
  try {
    const resp = await fetch(url, { ...options, signal: controller.signal });
    return resp;
  } finally {
    clearTimeout(timer);
  }
}

// Safe JSON parse — returns null instead of throwing
async function safeJson(resp) {
  try {
    return await resp.json();
  } catch {
    return null;
  }
}

async function loadDashboard(token) {
  try {
    const resp = await fetchWithTimeout(`${API_BASE}/api/dashboard`, {
      headers: { 'Authorization': `Bearer ${token}` }
    });

    if (resp.status === 401) {
      await chrome.storage.local.remove(['aa_token', 'aa_user_id']);
      showSection('login');
      return;
    }

    if (!resp.ok) {
      const data = await safeJson(resp);
      console.error('[АвтоОтклик] dashboard error', resp.status, data);
      setStatus(false, `Ошибка сервера ${resp.status}`);
      showSection('dashboard');
      return;
    }

    const data = await resp.json();
    document.getElementById('userEmail').textContent     = data.email || '—';
    document.getElementById('statToday').textContent     = data.applications_today ?? 0;
    document.getElementById('statTotal').textContent     = data.applications_total ?? 0;
    document.getElementById('statCampaigns').textContent = data.active_campaigns ?? 0;
    setPlanBadge(data.plan);

    if (data.active_campaigns > 0) {
      setStatus(true, `Активна — ${data.active_campaigns} кампани${data.active_campaigns === 1 ? 'я' : 'и'}`);
    } else {
      setStatus(false, 'Нет активных кампаний');
    }

    await chrome.storage.local.set({ aa_plan: data.plan, aa_email: data.email });
    showSection('dashboard');

  } catch (e) {
    console.error('[АвтоОтклик] loadDashboard exception:', e);
    // Show cached data when offline
    const stored = await chrome.storage.local.get(['aa_plan', 'aa_email']);
    document.getElementById('userEmail').textContent = stored.aa_email || '—';
    setPlanBadge(stored.aa_plan || 'free');
    setStatus(false, e.name === 'AbortError' ? 'Сервер не отвечает (таймаут)' : 'Нет соединения');
    showSection('dashboard');
  }
}

async function init() {
  showSection('loading');
  const stored = await chrome.storage.local.get(['aa_token', 'aa_user_id']);
  if (stored.aa_token) {
    await loadDashboard(stored.aa_token);
  } else {
    showSection('login');
  }
}

loginBtn.addEventListener('click', async () => {
  const email    = emailInput.value.trim();
  const password = passwordInput.value;

  if (!email || !password) {
    loginError.textContent   = 'Введите email и пароль';
    loginError.style.display = 'block';
    return;
  }

  loginBtn.disabled    = true;
  loginBtn.textContent = 'Входим...';
  loginError.style.display = 'none';

  try {
    const resp = await fetchWithTimeout(`${API_BASE}/api/login`, {
      method:  'POST',
      headers: { 'Content-Type': 'application/json' },
      body:    JSON.stringify({ email, password })
    });

    const data = await safeJson(resp);

    if (!resp.ok) {
      const msg = data?.detail || (resp.status === 401 ? 'Неверный email или пароль' : `Ошибка сервера (${resp.status})`);
      loginError.textContent   = msg;
      loginError.style.display = 'block';
      return;
    }

    if (!data?.token) {
      loginError.textContent   = 'Неверный ответ сервера';
      loginError.style.display = 'block';
      return;
    }

    await chrome.storage.local.set({
      aa_token:   data.token,
      aa_user_id: data.user_id,
      aa_email:   email
    });
    await loadDashboard(data.token);

  } catch (e) {
    console.error('[АвтоОтклик] login exception:', e);
    const msg = e.name === 'AbortError'
      ? 'Сервер не отвечает. Попробуйте позже.'
      : 'Не удалось подключиться к серверу.';
    loginError.textContent   = msg;
    loginError.style.display = 'block';
  } finally {
    loginBtn.disabled    = false;
    loginBtn.textContent = 'Войти';
  }
});

passwordInput.addEventListener('keydown', (e) => {
  if (e.key === 'Enter') loginBtn.click();
});

logoutBtn.addEventListener('click', async () => {
  await chrome.storage.local.remove(['aa_token', 'aa_user_id', 'aa_email', 'aa_plan']);
  showSection('login');
  emailInput.value    = '';
  passwordInput.value = '';
});

init();
