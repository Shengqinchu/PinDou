import { defineStore } from 'pinia';
import { api } from '../api';
import { useUserStore } from './user';

export const useCDKStore = defineStore('cdk', {
  actions: {
    async redeem(cdkCode: string) {
      try {
        const result = await api.redeemCDK(cdkCode);
        if (result.success) {
          // 兑换成功后更新用户信息中的会员状态或剩余额度
          const userStore = useUserStore();
          await userStore.fetchProfile();
        }
        return result;
      } catch (error) {
        console.error('CDK redeem error:', error);
        throw error;
      }
    }
  }
});
