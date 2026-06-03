export * from './client';
export * from './types';

import { apiRequest } from './client';
import type { User } from './types';

export interface EmailCodeResponse {
  success: boolean;
  message?: string;
  expires_in_seconds?: number;
  cooldown_seconds?: number;
}

export interface AuthResponse {
  token: string;
  user: User;
}

export interface RegisterResponse extends AuthResponse {
  cdk?: {
    success: boolean;
    cdk_type?: string;
    value?: number;
    message_cn?: string;
  };
}

export function sendEmailCode(email: string): Promise<EmailCodeResponse> {
  return apiRequest<EmailCodeResponse>('/user/email/send-code', {
    method: 'POST',
    auth: false,
    body: { email }
  });
}

export function verifyEmailCode(email: string, code: string): Promise<AuthResponse> {
  return apiRequest<AuthResponse>('/user/email/verify', {
    method: 'POST',
    auth: false,
    body: { email, code }
  });
}

export function registerWebAccount(payload: {
  email: string;
  code: string;
  password: string;
  cdk?: string;
}): Promise<RegisterResponse> {
  return apiRequest<RegisterResponse>('/user/register', {
    method: 'POST',
    auth: false,
    body: payload
  });
}

export function emailPasswordLogin(email: string, password: string): Promise<AuthResponse> {
  return apiRequest<AuthResponse>('/user/email-login', {
    method: 'POST',
    auth: false,
    body: { email, password }
  });
}

export function getProfile(): Promise<User> {
  return apiRequest<User>('/user/profile');
}
