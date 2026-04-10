// popup.js — АвтоОтклик Chrome Extension popup logic
// Extracted from inline script to comply with Manifest V3 CSP (no inline scripts allowed)

const API_BASE = 'https://resumeai-bot.ru';

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

async function loadDashboard(token) {
  try {
    const resp = await fetch(`${API_BASE}/api/dashboard`, {
      headers: { 'Authorization': `Bearer ${token}` }
    });
    if (!resp.ok) throw new Error('auth_failed');
    const data = await resp.json();

    document.getElementById('userEmail').textContent    = data.email || '—';
    document.getElementById('statToday').textContent    = data.applications_today ?? 0;
    document.getElementById('statTotal').textContent    = data.applications_total ?? 0;
    document.getElementById('statCampaigns').textContent = data.active_campaigns ?? 0;
    setPlanBadge(data.plan);

    if (data.active_campaigns > 0) {
      setStatus(true, `Активна — ${data.active_campaigns} кампани${data.active_campaigns === 1 ? 'я' : 'и'}`);
    } else {
      setStatus(false, 'Нет активных кампаний');
    }

    // Cache for offline use
    await chrome.storage.local.set({ aa_plan: data.plan });

    showSection('dashboard');
  } catch (e) {
    if (e.message === 'auth_failed') {
      await chrome.storage.local.remove(['aa_token', 'aa_user_id']);
      showSection('login');
    } else {
      // Network error — show cached info
      const stored = await chrome.storage.local.get(['aa_plan', 'aa_email']);
      document.getElementById('userEmail').textContent = stored.aa_email || '—';
      setPlanBadge(stored.aa_plan || 'free');
      setStatus(false, 'Нет соединения с сервером');
      showSection('dashboard');
    }
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
    loginError.textContent    = 'Введите email и пароль';
    loginError.style.display  = 'block';
    return;
  }
  loginBtn.disabled    = true;
  loginBtn.textContent = 'Входим...';
  loginError.style.display = 'none';

  try {
    const resp = await fetch(`${API_BASE}/api/login`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ email, password })
    });
    const data = await resp.json();
    if (!resp.ok) {
      loginError.textContent   = data.detail || 'Неверный email или пароль';
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
    loginError.textContent   = 'Ошибка соединения. Проверьте интернет.';
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
  emailInput.value  = '';
  passwordInput.value = '';
});

init();
