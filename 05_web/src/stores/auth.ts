import { defineStore } from 'pinia';

import { emailPasswordLogin, getProfile, registerWebAccount, sendEmailCode, verifyEmailCode } from '../api';
import type { EmailCodeResponse, RegisterResponse } from '../api';
import type { User } from '../api/types';
import {
  clearStoredUser,
  clearToken,
  getStoredUser,
  getToken,
  setStoredUser,
  setToken
} from '../auth/tokenStorage';

export const useAuthStore = defineStore('auth', {
  state: () => ({
    token: getToken(),
    user: getStoredUser() as User | null
  }),
  getters: {
    isLoggedIn: (state) => Boolean(state.token),
    displayName: (state) => state.user?.email || state.user?.nickname || 'PinDou 用户'
  },
  actions: {
    setSession(token: string, user: User) {
      this.token = token;
      this.user = user;
      setToken(token);
      setStoredUser(user);
    },
    async sendEmailCode(email: string): Promise<EmailCodeResponse> {
      return sendEmailCode(email);
    },
    async loginWithEmail(email: string, code: string): Promise<User> {
      const payload = await verifyEmailCode(email, code);
      this.setSession(payload.token, payload.user);
      return payload.user;
    },
    async registerWithPassword(payload: {
      email: string;
      code: string;
      password: string;
      cdk?: string;
    }): Promise<RegisterResponse> {
      const response = await registerWebAccount(payload);
      this.setSession(response.token, response.user);
      return response;
    },
    async loginWithPassword(email: string, password: string): Promise<User> {
      const payload = await emailPasswordLogin(email, password);
      this.setSession(payload.token, payload.user);
      return payload.user;
    },
    async refreshProfile(): Promise<User> {
      const user = await getProfile();
      this.user = user;
      setStoredUser(user);
      return user;
    },
    setToken(token: string) {
      this.token = token;
      setToken(token);
    },
    logout() {
      this.token = '';
      this.user = null;
      clearToken();
      clearStoredUser();
    }
  }
});
