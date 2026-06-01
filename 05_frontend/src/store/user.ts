import { defineStore } from 'pinia';
import { api, User } from '../api';
import { getOrCreateH5DeviceId, getPlatformLoginCode, getWxLoginCode } from '../utils/request';

export interface UiMetrics {
  statusBarHeight: number;
  menuButtonTop: number;
  menuButtonHeight: number;
  menuButtonWidth: number;
  menuButtonRight: number;
  topChromeHeight: number;
  capsuleReserveRight: number;
  safeAreaBottom: number;
  screenWidth: number;
  screenHeight: number;
  pixelRatio: number;
}

interface UserState {
  userInfo: User | null;
  token: string;
  uiMetrics: UiMetrics;
}

let activeLoginPromise: Promise<any> | null = null;

const defaultUiMetrics = (): UiMetrics => ({
  statusBarHeight: 20,
  menuButtonTop: 24,
  menuButtonHeight: 32,
  menuButtonWidth: 87,
  menuButtonRight: 8,
  topChromeHeight: 64,
  capsuleReserveRight: 107,
  safeAreaBottom: 0,
  screenWidth: 375,
  screenHeight: 667,
  pixelRatio: 2,
});

function isAuthExpiredError(error: unknown): boolean {
  const message = String((error as Error)?.message || error || '');
  return message.includes('登录已过期') || message.includes('请先登录');
}

function applyConsentToUser(user: User | null, type: 'privacy' | 'sensitive', consentAt: string) {
  if (!user) return;
  if (type === 'privacy') {
    user.privacy_consent_at = consentAt;
  } else {
    user.sensitive_consent_at = consentAt;
  }
  uni.setStorageSync('pd_user', JSON.stringify(user));
}

export const useUserStore = defineStore('user', {
  state: (): UserState => ({
    userInfo: null as User | null,
    token: uni.getStorageSync('pd_token') || '',
    uiMetrics: defaultUiMetrics(),
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
    initDeviceMetrics() {
      try {
        const systemInfo = uni.getSystemInfoSync();
        const screenWidth = systemInfo.screenWidth || systemInfo.windowWidth || 375;
        const screenHeight = systemInfo.screenHeight || systemInfo.windowHeight || 667;
        const statusBarHeight = systemInfo.statusBarHeight || 20;
        const pixelRatio = systemInfo.pixelRatio || 2;

        let menuButton = {
          top: statusBarHeight + 4,
          height: 32,
          width: 87,
          right: screenWidth - 8,
          bottom: statusBarHeight + 36,
        };

        try {
          const getMenuButton = (uni as any).getMenuButtonBoundingClientRect;
          const rect = typeof getMenuButton === 'function' ? getMenuButton() : null;
          if (rect && rect.height && rect.width) {
            menuButton = {
              top: rect.top,
              height: rect.height,
              width: rect.width,
              right: rect.right,
              bottom: rect.bottom,
            };
          }
        } catch (e) {
          console.warn('读取微信胶囊位置失败，使用默认导航尺寸:', e);
        }

        const safeAreaBottom = systemInfo.safeArea
          ? Math.max(0, screenHeight - systemInfo.safeArea.bottom)
          : ((systemInfo as any).safeAreaInsets?.bottom || 0);

        this.uiMetrics = {
          statusBarHeight,
          menuButtonTop: menuButton.top,
          menuButtonHeight: menuButton.height,
          menuButtonWidth: menuButton.width,
          menuButtonRight: Math.max(0, screenWidth - menuButton.right),
          topChromeHeight: Math.max(statusBarHeight + menuButton.height + 8, menuButton.bottom + 8),
          capsuleReserveRight: Math.max(screenWidth - (menuButton.right - menuButton.width) + 12, 104),
          safeAreaBottom,
          screenWidth,
          screenHeight,
          pixelRatio,
        };
      } catch (error) {
        console.warn('初始化设备安全区失败，使用默认导航尺寸:', error);
        this.uiMetrics = defaultUiMetrics();
      }
    },
    async login() {
      try {
        if (activeLoginPromise) {
          return activeLoginPromise;
        }
        activeLoginPromise = (async () => {
          let code = '';
          // #ifdef MP-WEIXIN
          code = await getWxLoginCode();
          // #endif
          // #ifdef H5
          code = getOrCreateH5DeviceId();
          // #endif
          if (!code) {
            code = await getPlatformLoginCode();
          }
          const data = await api.login(code);
          this.token = data.token;
          this.userInfo = data.user;
          uni.setStorageSync('pd_token', data.token);
          uni.setStorageSync('pd_user', JSON.stringify(data.user));
          return data;
        })();
        return await activeLoginPromise;
      } catch (error) {
        console.error('Login action error:', error);
        throw error;
      } finally {
        activeLoginPromise = null;
      }
    },
    async fetchProfile() {
      try {
        const user = await api.getProfile();
        this.userInfo = user;
        uni.setStorageSync('pd_user', JSON.stringify(user));
        return user;
      } catch (error) {
        if (isAuthExpiredError(error)) {
          this.logout();
          const data = await this.login();
          return data.user as User;
        }
        console.error('Fetch profile action error:', error);
        throw error;
      }
    },
    async giveConsent(type: 'privacy' | 'sensitive') {
      try {
        const res = await api.submitConsent(type);
        if (res.success) {
          applyConsentToUser(this.userInfo, type, res.consent_at);
        }
        return res;
      } catch (error) {
        if (isAuthExpiredError(error)) {
          this.logout();
          await this.login();
          const res = await api.submitConsent(type);
          if (res.success) {
            applyConsentToUser(this.userInfo, type, res.consent_at);
          }
          return res;
        }
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
