import type { User } from '../api/types';

const TOKEN_KEY = 'pd_web_token';
const USER_KEY = 'pd_web_user';
const DEVICE_TOKEN_KEY = 'pd_device_token';

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

export function getStoredUser(): User | null {
  const raw = window.localStorage.getItem(USER_KEY);
  if (!raw) {
    return null;
  }

  try {
    return JSON.parse(raw) as User;
  } catch (_error) {
    window.localStorage.removeItem(USER_KEY);
    return null;
  }
}

export function setStoredUser(user: User): void {
  window.localStorage.setItem(USER_KEY, JSON.stringify(user));
}

export function clearStoredUser(): void {
  window.localStorage.removeItem(USER_KEY);
}

export function getDeviceToken(): string {
  return window.localStorage.getItem(DEVICE_TOKEN_KEY) || '';
}

export function setDeviceToken(token: string): void {
  window.localStorage.setItem(DEVICE_TOKEN_KEY, token);
}

export function clearDeviceToken(): void {
  window.localStorage.removeItem(DEVICE_TOKEN_KEY);
}
