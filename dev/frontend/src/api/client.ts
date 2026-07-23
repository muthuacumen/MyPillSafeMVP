import axios from 'axios';

const client = axios.create({
  baseURL: import.meta.env.VITE_API_URL ?? '/api/v1',
  withCredentials: true,
  headers: { 'Content-Type': 'application/json' },
});

client.interceptors.request.use((config) => {
  const token = localStorage.getItem('access_token');
  if (token) config.headers.Authorization = `Bearer ${token}`;
  return config;
});

let refreshPromise: Promise<string> | null = null;

// Requests to these endpoints must never trigger the refresh-retry-and-redirect
// flow below: a failed /auth/login or /auth/register is a normal form-validation
// outcome the page needs to render inline (LoginPage renders `serverError` from
// the rejection), not a session expiry. A hard `window.location.href` redirect
// on a wrong-password attempt destroys the form's error state before the user
// ever sees it. /auth/refresh itself is excluded too, so a failed refresh can't
// try to refresh-and-retry itself.
const AUTH_ENDPOINTS = ['/auth/login', '/auth/register', '/auth/refresh'];

function isAuthEndpoint(url?: string): boolean {
  if (!url) return false;
  return AUTH_ENDPOINTS.some((path) => url.includes(path));
}

function refreshAccessToken(): Promise<string> {
  if (!refreshPromise) {
    const apiBase = import.meta.env.VITE_API_URL ?? '/api/v1';
    refreshPromise = axios
      .post(`${apiBase}/auth/refresh`, {}, { withCredentials: true })
      .then(({ data }) => {
        localStorage.setItem('access_token', data.access_token);
        return data.access_token as string;
      })
      .finally(() => {
        refreshPromise = null;
      });
  }
  return refreshPromise;
}

client.interceptors.response.use(
  (res) => res,
  async (error) => {
    const original = error.config;
    if (error.response?.status === 401 && !original._retry && !isAuthEndpoint(original?.url)) {
      original._retry = true;
      try {
        // Several requests can hit a just-expired token at once (e.g. the
        // dashboard, medications list, and dose-reminder poller all firing
        // together) — share one in-flight refresh instead of each request
        // racing its own /auth/refresh call.
        const accessToken = await refreshAccessToken();
        original.headers.Authorization = `Bearer ${accessToken}`;
        return client(original);
      } catch {
        localStorage.removeItem('access_token');
        window.location.href = '/login';
      }
    }
    return Promise.reject(error);
  },
);

export default client;
