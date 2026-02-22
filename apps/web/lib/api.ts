const API_BASE = '/api';

export interface LoginRequest {
  email: string;
  password: string;
}

export interface LoginResponse {
  access_token: string;
  token_type: string;
}

export interface AtlasChatRequest {
  message: string;
  session_id?: string;
}

export interface AtlasChatResponse {
  response: string;
  session_id: string;
  data?: unknown[];
  suggestions?: string[];
}

export async function login(data: LoginRequest): Promise<LoginResponse> {
  const res = await fetch(`${API_BASE}/auth/login`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(data),
  });

  if (!res.ok) {
    const error = await res.json().catch(() => ({ detail: 'Login failed' }));
    throw new Error(error.detail || 'Login failed');
  }

  return res.json();
}

export async function atlasChat(data: AtlasChatRequest): Promise<AtlasChatResponse> {
  const token = localStorage.getItem('token');

  const res = await fetch(`${API_BASE}/atlas/chat`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      ...(token && { Authorization: `Bearer ${token}` }),
    },
    body: JSON.stringify(data),
  });

  if (!res.ok) {
    const error = await res.json().catch(() => ({ detail: 'Chat failed' }));
    throw new Error(error.detail || 'Chat failed');
  }

  return res.json();
}
