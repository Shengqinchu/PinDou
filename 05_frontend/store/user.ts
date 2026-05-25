import { defineStore } from 'pinia';
import { api, User } from '../api';

export const useUserStore = defineStore('user', {
  state: () => ({
    userInfo: null as User | null,
    token: uni.getStorageSync('pd_token') || '',
  }),
  getters: {
    isLoggedIn: (state): boolean => !!state.token,
    hasPrivacyConsent: (state): boolean => !!state.userInfo?.privacy_consent_at,
    hasSensitiveConsent: (state): boolean => !!state.userInfo?.sensitive_consent_at,
    credits: (state): number => (state.userInfo?.free_credits_remaining || 0) + (state.userInfo?.paid_credits || 0),
    isMonthlyMember: (state): boolean => {
      if (!state.userInfo?.monthly_card_expires_at) return false;
      const expire = new Date(state.userInfo.monthly_card_expires_at).getTime();
      return expire > Date.now();
    }
  },
  actions: {
    async login() {
      try {
        // 小程序获取 code
        return new Promise<any>((resolve, reject) => {
          uni.login({
            provider: 'weixin',
            success: async (loginRes) => {
              if (loginRes.code) {
                try {
                  const data = await api.login(loginRes.code);
                  this.token = data.token;
                  this.userInfo = data.user;
                  uni.setStorageSync('pd_token', data.token);
                  uni.setStorageSync('pd_user', JSON.stringify(data.user));
                  resolve(data);
                } catch (err) {
                  reject(err);
                }
              } else {
                reject(new Error('微信登录失败：未获取到code'));
              }
            },
            fail: (err) => reject(err)
          });
        });
      } catch (error) {
        console.error('Login action error:', error);
        throw error;
      }
    },
    async fetchProfile() {
      try {
        const user = await api.getProfile();
        this.userInfo = user;
        uni.setStorageSync('pd_user', JSON.stringify(user));
        return user;
      } catch (error) {
        console.error('Fetch profile action error:', error);
        throw error;
      }
    },
    async giveConsent(type: 'privacy' | 'sensitive') {
      try {
        const res = await api.submitConsent(type);
        if (res.success && this.userInfo) {
          if (type === 'privacy') {
            this.userInfo.privacy_consent_at = res.consent_at;
          } else {
            this.userInfo.sensitive_consent_at = res.consent_at;
          }
          uni.setStorageSync('pd_user', JSON.stringify(this.userInfo));
        }
        return res;
      } catch (error) {
        console.error('Give consent action error:', error);
        throw error;
      }
    },
    logout() {
      this.token = '';
      this.userInfo = null;
      uni.removeStorageSync('pd_token');
      uni.removeStorageSync('pd_user');
    }
  }
});
