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
  sessionId?: string;
}

interface AtlasBackendResponse {
  success: boolean;
  sessionId: string;
  response: {
    text: string;
    data?: unknown[];
    suggestions?: string[];
  };
  error?: string;
}

export interface AtlasChatResponse {
  text: string;
  sessionId: string;
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

  const result: AtlasBackendResponse = await res.json();

  if (!result.success) {
    throw new Error(result.error || 'Chat failed');
  }

  return {
    text: result.response.text,
    sessionId: result.sessionId,
    data: result.response.data,
    suggestions: result.response.suggestions,
  };
}
