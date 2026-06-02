const TOKEN_KEY = 'pd_web_token';

export function getToken(): string {
  return window.localStorage.getItem(TOKEN_KEY) || '';
}

export function setToken(token: string): void {
  window.localStorage.setItem(TOKEN_KEY, token);
}

export function clearToken(): void {
  window.localStorage.removeItem(TOKEN_KEY);
}

export function hasToken(): boolean {
  return Boolean(getToken());
}

