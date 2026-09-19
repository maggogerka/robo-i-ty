const API_URL = import.meta.env.VITE_API_URL ?? "/api/v1";

export class ApiError extends Error {
  constructor(
    message: string,
    public status: number,
    public detail?: unknown,
  ) {
    super(message);
  }
}

export function getToken(): string | null {
  return localStorage.getItem("robo_token");
}

export function setToken(token: string): void {
  localStorage.setItem("robo_token", token);
}

export function clearToken(): void {
  localStorage.removeItem("robo_token");
}

export async function api<T>(path: string, init: RequestInit = {}): Promise<T> {
  const token = getToken();
  const response = await fetch(`${API_URL}${path}`, {
    ...init,
    headers: {
      "Content-Type": "application/json",
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
      ...init.headers,
    },
  });
  const body = await response.json().catch(() => null);
  if (!response.ok) {
    throw new ApiError(
      typeof body?.detail === "string" ? body.detail : "Ошибка запроса",
      response.status,
      body?.detail,
    );
  }
  return body as T;
}

