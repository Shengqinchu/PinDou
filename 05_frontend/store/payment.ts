import { defineStore } from 'pinia';
import { api, Order } from '../api';

export const usePaymentStore = defineStore('payment', {
  state: () => ({
    currentOrder: null as Order | null,
    customerServiceQR: null as { qr_url: string; wx_id: string; order_id: string } | null,
  }),
  actions: {
    async createPayOrder(sku: 'single_9.9' | 'monthly_28' | 'custom_99', artworkId?: string) {
      try {
        const order = await api.createOrder(sku, artworkId);
        this.currentOrder = order;
        // 创建订单后立马获取客服二维码
        const qrInfo = await api.getCustomerServiceQR(order.order_id);
        this.customerServiceQR = qrInfo;
        return { order, qrInfo };
      } catch (error) {
        console.error('Create payment order error:', error);
        throw error;
      }
    },
    async checkOrderStatus(orderId: string) {
      try {
        const res = await api.getOrderStatus(orderId);
        if (res.status === 'paid_confirmed' && this.currentOrder && this.currentOrder.order_id === orderId) {
          this.currentOrder.status = 'paid_confirmed';
        }
        return res;
      } catch (error) {
        console.error('Check order status error:', error);
        throw error;
      }
    }
  }
});
