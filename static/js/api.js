const API_BASE = '/api';
const KEY = 'auth'

const savedAuth = JSON.parse(localStorage.getItem(KEY) || 'null');

const auth = Vue.reactive({
  token: savedAuth?.token ?? null,
  username: savedAuth?.username ?? '',
  expiresAt: savedAuth?.expiresAt ?? 0,

  onUnauthorized: () => {}, 
  onLogout: () => {},

  login(token, user, expiresAt) { 
    this.token = token;
    this.username = user;
    this.expiresAt = expiresAt;

    localStorage.setItem(KEY, JSON.stringify({token, username: user, expiresAt}));
    this.startTimer();
  },

  logout() {
    this.token = null;
    this.username = '';
    this.expiresAt = 0;
    localStorage.removeItem(KEY);
    clearTimeout(this._timer);
    this.onLogout();
  },

  startTimer() {
    clearTimeout(this._timer);
    if (!this.token) {return};
    const time = this.expiresAt - Date.now();
    this._timer = setTimeout(() => this.logout(), time);
  }
    
});

auth.startTimer();

class ApiError extends Error {
  constructor(status, problem) {
    super(problem?.detail || problem?.title || `Błąd ${status}`);
    this.name = 'ApiError';
    this.status = status;
    this.problem = problem;                 
    this.errors = problem?.errors ?? {};
  }
}

async function api(path, { method = 'GET', body, auth: useAuth = true } = {}) {
  const headers = { 'Content-Type': 'application/json' };
  if (useAuth && auth.token) headers['Authorization'] = `Bearer ${auth.token}`;

  const res = await fetch(API_BASE + path, {
    method,
    headers,
    body: body ? JSON.stringify(body) : undefined,
  });

  if (res.status === 401 && useAuth) {
    auth.logout();
    throw new Error('Session expired. Login required.');
  }
  if (!res.ok) {
    const data = await res.json().catch(() => null);
    throw new ApiError(res.status, data);
  }
  return res.status === 204 ? null : res.json();
}