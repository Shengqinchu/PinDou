import { customerToken } from '../../../05_studio/src/account-storage';
import type { User } from '../api/types';

const TOKEN_KEY = 'pd_web_token';
const USER_KEY = 'pd_web_user';
const DEVICE_TOKEN_KEY = 'pd_device_token';

export function getToken(): string {
  return customerToken();
}

export function setToken(token: string): void {
  try{window.localStorage.setItem(TOKEN_KEY, token);}catch{/* Storage is optional for this session. */}
}

export function clearToken(): void {
  try{window.localStorage.removeItem(TOKEN_KEY);}catch{/* Storage is optional for this session. */}
}

export function hasToken(): boolean {
  return Boolean(getToken());
}

export function getStoredUser(): User | null {
  let raw:string|null=null;try{raw=window.localStorage.getItem(USER_KEY);}catch{return null;}
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
  try{window.localStorage.setItem(USER_KEY, JSON.stringify(user));}catch{/* Storage is optional for this session. */}
}

export function clearStoredUser(): void {
  try{window.localStorage.removeItem(USER_KEY);}catch{/* Storage is optional for this session. */}
}

export function getDeviceToken(): string {
  try{return window.localStorage.getItem(DEVICE_TOKEN_KEY)||'';}catch{return '';}
}

export function setDeviceToken(token: string): void {
  try{window.localStorage.setItem(DEVICE_TOKEN_KEY, token);}catch{/* Storage is optional for this session. */}
}

export function clearDeviceToken(): void {
  try{window.localStorage.removeItem(DEVICE_TOKEN_KEY);}catch{/* Storage is optional for this session. */}
}
