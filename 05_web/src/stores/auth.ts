import { defineStore } from 'pinia';

import { clearToken, getToken, setToken } from '../auth/tokenStorage';

export const useAuthStore = defineStore('auth', {
  state: () => ({
    token: getToken()
  }),
  getters: {
    isLoggedIn: (state) => Boolean(state.token)
  },
  actions: {
    setToken(token: string) {
      this.token = token;
      setToken(token);
    },
    logout() {
      this.token = '';
      clearToken();
    }
  }
});

