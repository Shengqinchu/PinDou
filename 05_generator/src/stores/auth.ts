import { defineStore } from 'pinia';
import { gt } from '../i18n';

import { emailPasswordLogin, getProfile, registerWebAccount, sendEmailCode, updateProfile, uploadAvatar, verifyEmailCode } from '../api';
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
import { useSWRCacheStore } from './swrCache';

export const useAuthStore = defineStore('auth', {
  state: () => ({
    token: getToken(),
    user: getStoredUser() as User | null
  }),
  getters: {
    isLoggedIn: (state) => Boolean(state.token),
    displayName: (state) => state.user?.nickname || state.user?.email || gt('Pindou Puppy 用户')
  },
  actions: {
    syncFromStorage() {
      const token=getToken();
      if(token!==this.token)useSWRCacheStore().clearAll();
      this.token=token;
      this.applyUser(token?getStoredUser():null,false);
    },
    setSession(token: string, user: User) {
      if (token !== this.token) {
        useSWRCacheStore().clearAll();
      }
      this.token = token;
      this.applyUser(user);
      setToken(token);
    },
    applyUser(user: User | null, persist = true) {
      this.user = user;
      if (!persist) {
        return;
      }
      if (user) {
        setStoredUser(user);
      } else {
        clearStoredUser();
      }
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
      const token=this.token;
      const user = await getProfile();
      if(token===this.token&&token===getToken())this.applyUser(user);
      return user;
    },
    async updateProfile(payload: { nickname?: string; avatar_url?: string }): Promise<User> {
      const user = await updateProfile(payload);
      this.applyUser(user);
      return user;
    },
    async uploadAvatar(file: File): Promise<User> {
      const response = await uploadAvatar(file);
      this.applyUser(response.user);
      return response.user;
    },
    rollbackUser(user: User | null) {
      this.applyUser(user);
      return user;
    },
    setToken(token: string) {
      this.token = token;
      setToken(token);
    },
    logout() {
      this.token = '';
      this.applyUser(null);
      useSWRCacheStore().clearAll();
      clearToken();
    }
  }
});
