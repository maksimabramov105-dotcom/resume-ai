'use client';

const BASE = '/api';

function getToken(): string | null {
  if (typeof window === 'undefined') return null;
  return localStorage.getItem('aa_token');
}

async function request<T>(
  endpoint: string,
  method: string,
  body?: unknown,
  customToken?: string
): Promise<T | null> {
  const token = customToken ?? getToken();
  const headers: Record<string, string> = { 'Content-Type': 'application/json' };
  if (token) headers['Authorization'] = `Bearer ${token}`;

  try {
    const res = await fetch(BASE + endpoint, {
      method,
      headers,
      body: body !== undefined ? JSON.stringify(body) : undefined,
    });

    if (res.status === 204) return null;

    const data = await res.json().catch(() => null);

    if (res.status === 401) {
      // Auth endpoints: return error data so caller can show "wrong password"
      if (endpoint === '/auth/login' || endpoint === '/auth/register') {
        return data as T;
      }
      // All other 401s: clear token and redirect to login
      localStorage.removeItem('aa_token');
      window.location.href = '/app/login';
      return null;
    }

    if (!res.ok) {
      return data as T;
    }

    return data as T;
  } catch (err) {
    console.error('[api]', endpoint, err);
    return null;
  }
}

export const api = {
  get: <T>(endpoint: string, token?: string) =>
    request<T>(endpoint, 'GET', undefined, token),
  post: <T>(endpoint: string, body: unknown, token?: string) =>
    request<T>(endpoint, 'POST', body, token),
  put: <T>(endpoint: string, body: unknown, token?: string) =>
    request<T>(endpoint, 'PUT', body, token),
  patch: <T>(endpoint: string, body: unknown, token?: string) =>
    request<T>(endpoint, 'PATCH', body, token),
  del: <T>(endpoint: string, token?: string) =>
    request<T>(endpoint, 'DELETE', undefined, token),
};

// Auth helpers
export async function login(email: string, password: string) {
  return api.post<{ access_token?: string; detail?: string }>(
    '/auth/login',
    { email, password }
  );
}

export async function register(email: string, password: string) {
  return api.post<{ access_token?: string; detail?: string }>(
    '/auth/register',
    { email, password }
  );
}

export async function getMe(token?: string) {
  return api.get<{
    id: number;
    email: string;
    plan: string;
    applications_count: number;
    applications_limit: number;
    created_at: string;
  }>('/auth/me', token);
}
