import { defineStore } from 'pinia';
import { api, Order } from '../api';
import { BASE_URL } from '../utils/request';

const QR_PLACEHOLDER = '/static/assets/qr-placeholder.svg';

function resolveQrUrl(url?: string | null): string {
  if (!url) return QR_PLACEHOLDER;
  if (url.startsWith('/payment/')) return `${BASE_URL}${url}`;
  if (url.startsWith('/api/')) return `${BASE_URL.replace(/\/api\/v\d+$/, '')}${url}`;
  return url;
}

function resolveHupijiaoQrUrl(order: Order): string {
  if (order.payment_provider === 'hupijiao' && order.order_no) {
    return `${BASE_URL}/payment/order/${order.order_no}/qr.png`;
  }
  return resolveQrUrl(order.qr_code_url);
}

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
        const qrInfo = {
          qr_url: resolveHupijiaoQrUrl(order),
          wx_id: '',
          order_id: order.order_id
        };
        return { order, qrInfo };
      } catch (error) {
        console.error('Create payment order error:', error);
        throw error;
      }
    },
    async createCustomerServiceOrder(sku: 'single_9.9' | 'monthly_28' | 'custom_99', artworkId?: string) {
      try {
        const order = await api.createCustomerServiceOrder(sku, artworkId);
        this.currentOrder = order;
        const qrInfo = await api.getCustomerServiceQR(order.order_id);
        this.customerServiceQR = qrInfo;
        return { order, qrInfo };
      } catch (error) {
        console.error('Create customer service payment order error:', error);
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
