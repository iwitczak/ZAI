const API_BASE = '/api';
const TOKEN_KEY = 'auth_token';

const auth = Vue.reactive({
  token: localStorage.getItem(TOKEN_KEY),
  set(value) { 
    this.token = value
    value ? localStorage.setItem(TOKEN_KEY, value) : localStorage.removeItem(TOKEN_KEY); 
  },
    onUnauthorized: () => {}, 
});

async function api(path, { method = 'GET', body, auth: useAuth = true } = {}) {
  const headers = { 'Content-Type': 'application/json' };
  if (useAuth && auth.token) headers['Authorization'] = `Bearer ${auth.token}`;

  const res = await fetch(API_BASE + path, {
    method,
    headers,
    body: body ? JSON.stringify(body) : undefined,
  });

  if (res.status === 401 && useAuth) {
    auth.set(null);
    auth.onUnauthorized();
    throw new Error('Session expired. Login required.');
  }
  if (!res.ok) {
    const data = await res.json().catch(() => ({}));
    throw new Error(data.detail || `Error ${res.status}`);
  }
  return res.status === 204 ? null : res.json();
}