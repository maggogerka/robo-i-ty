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

export async function apiDownload(path: string): Promise<{ blob: Blob; filename: string }> {
  const token = getToken();
  const response = await fetch(`${API_URL}${path}`, {
    headers: token ? { Authorization: `Bearer ${token}` } : {},
  });
  if (!response.ok) {
    const body = await response.json().catch(() => null);
    throw new ApiError(
      typeof body?.detail === "string" ? body.detail : "Ошибка выгрузки",
      response.status,
      body?.detail,
    );
  }
  const disposition = response.headers.get("Content-Disposition") ?? "";
  const match = disposition.match(/filename="?([^";]+)"?/i);
  return {
    blob: await response.blob(),
    filename: match?.[1] ?? "export.bin",
  };
}

export async function apiUpload<T>(path: string, file: File): Promise<T> {
  const token = getToken();
  const form = new FormData();
  form.append("file", file);
  const response = await fetch(`${API_URL}${path}`, {
    method: "POST",
    headers: token ? { Authorization: `Bearer ${token}` } : {},
    body: form,
  });
  const body = await response.json().catch(() => null);
  if (!response.ok) {
    throw new ApiError(
      typeof body?.detail === "string" ? body.detail : "Ошибка загрузки файла",
      response.status,
      body?.detail,
    );
  }
  return body as T;
}
