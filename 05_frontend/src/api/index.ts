// PinDou API 封装 (符合 PRD §5 接口契约)
import { request, BASE_URL } from '../utils/request';

// 是否开启 Mock 模式 (联调前默认开启)
const USE_MOCK = false;
const UPLOAD_TIMEOUT_MS = 120000;

type ApiErrorBody = {
  error?: string;
  message_cn?: string;
  message?: string;
  details?: unknown;
};

export class PinDouApiError extends Error {
  statusCode?: number;
  code?: string;
  details?: unknown;

  constructor(message: string, options: { statusCode?: number; code?: string; details?: unknown } = {}) {
    super(message);
    this.name = 'PinDouApiError';
    this.statusCode = options.statusCode;
    this.code = options.code;
    this.details = options.details;
  }
}

function parseJsonBody(data: unknown): ApiErrorBody | null {
  if (!data) return null;
  if (typeof data === 'object') return data as ApiErrorBody;
  if (typeof data !== 'string') return null;
  try {
    return JSON.parse(data) as ApiErrorBody;
  } catch {
    return null;
  }
}

function uploadResponseError(res: UniApp.UploadFileSuccessCallbackResult, fallbackMessage: string): PinDouApiError {
  const body = parseJsonBody(res.data);
  const message = body?.message_cn || body?.message || fallbackMessage;
  return new PinDouApiError(message, {
    statusCode: res.statusCode,
    code: body?.error,
    details: body?.details
  });
}

function uploadFailError(err: any): PinDouApiError {
  const errMsg = String(err?.errMsg || '');
  if (errMsg.toLowerCase().includes('timeout')) {
    return new PinDouApiError('生成时间超过等待上限，请稍后重试。', {
      code: 'UPLOAD_TIMEOUT',
      details: err
    });
  }
  return new PinDouApiError('网络连接失败，请检查后重试。', {
    code: 'NETWORK_ERROR',
    details: err
  });
}

/* ==========================================
   类型定义 (符合 PRD §5 / §6)
   ========================================== */
export type StylePreset = 'q_portrait' | 'q_pet' | 'q_couple' | 'cartoon_fallback';
export type SizePreset = '40x40' | '60x80' | '80x100' | '100x120';
export type CDKType = 'single_use' | 'monthly_card' | 'credit_pack_5' | 'credit_pack_10';

export interface User {
  user_id: string;
  nickname: string;
  avatar: string;
  created_at: string;
  free_credits_remaining: number;
  paid_credits: number;
  monthly_card_expires_at: string | null;
  privacy_consent_at: string | null;
  sensitive_consent_at: string | null;
}

export interface ColorRef {
  brand: string;
  code: string;
  name_cn: string;
  name_en: string | null;
  hex: string;
  rgb: [number, number, number];
  bead_diameter_mm: number;
  china_market_status?: string;
  aliases_cn?: string[];
}

export interface PatternSheet {
  grid: (ColorRef | null)[][]; // 二维网格，null 表示 NoBead
  color_counts: Record<string, number>; // { "M01": 234 }
  bead_total: number;
  coords: [number, number, string][]; // [row, col, color_code]
  no_bead_mask: boolean[][];
  palette_used: ColorRef[];
  estimated_cost_cny: number;
  suggested_buffer_pct: number;
  brand: string;
  bead_diameter_mm: number;
}

export interface PreviewResult {
  preview_id: string;
  image_url: string; // PNG transparent bg
  target_color_count: number;
  provider_used: string;
  fallback_count: number;
  cost_estimate: number;
  latency_ms: number;
}

export interface Artwork {
  artwork_id: string;
  user_id: string;
  created_at: string;
  original_image_url: string | null;
  original_image_deleted_at: string | null;
  style_preset: StylePreset;
  size_preset: SizePreset;
  preview_url: string;
  pattern_data: PatternSheet;
  title: string | null;
  is_paid_unlocked: boolean;
}

export interface CDKRedeemResult {
  success: boolean;
  cdk_type: CDKType;
  value: number;
  expires_at: string | null;
}

export interface Order {
  order_id: string;
  user_id: string;
  created_at: string;
  sku: string; // 'single' | 'monthly' | 'custom'
  amount_cny: number;
  status: 'pending' | 'paid_confirmed' | 'failed';
  payment_method: 'wechat_qr_via_cs' | 'cdk_redemption';
  artwork_id: string | null;
}

/* ==========================================
   Mock 数据准备
   ========================================== */
const mockColorPalette: ColorRef[] = [
  { brand: 'MARD', code: 'M01', name_cn: '纯白', name_en: 'Pure White', hex: '#FFFFFF', rgb: [255, 255, 255], bead_diameter_mm: 5.0, aliases_cn: ['奶白', '糖霜白'] },
  { brand: 'MARD', code: 'M13', name_cn: '腮红粉', name_en: 'Blush Pink', hex: '#FFB6C1', rgb: [255, 182, 193], bead_diameter_mm: 5.0, aliases_cn: ['樱花粉'] },
  { brand: 'MARD', code: 'M05', name_cn: '珊瑚红', name_en: 'Coral Red', hex: '#FF8E8E', rgb: [255, 142, 142], bead_diameter_mm: 5.0, aliases_cn: ['蜜桃红'] },
  { brand: 'MARD', code: 'M22', name_cn: '奶油黄', name_en: 'Butter Yellow', hex: '#FFE5A0', rgb: [255, 229, 160], bead_diameter_mm: 5.0, aliases_cn: ['柠檬黄'] },
  { brand: 'MARD', code: 'M34', name_cn: '薄荷绿', name_en: 'Mint Green', hex: '#B8E6C9', rgb: [184, 230, 201], bead_diameter_mm: 5.0, aliases_cn: ['浅绿'] },
  { brand: 'MARD', code: 'M41', name_cn: '天空蓝', name_en: 'Sky Blue', hex: '#B6DCFB', rgb: [182, 220, 251], bead_diameter_mm: 5.0, aliases_cn: ['浅蓝'] },
  { brand: 'MARD', code: 'M90', name_cn: '可可褐', name_en: 'Cocoa Brown', hex: '#8C6A55', rgb: [140, 106, 85], bead_diameter_mm: 5.0, aliases_cn: ['咖啡色'] },
  { brand: 'MARD', code: 'M10', name_cn: '极光黑', name_en: 'Ink Black', hex: '#2D2D2D', rgb: [45, 45, 45], bead_diameter_mm: 5.0, aliases_cn: ['黑色'] }
];

function generateMockPatternSheet(size: SizePreset): PatternSheet {
  const [cols, rows] = size === '40x40' ? [40, 40] : size === '60x80' ? [60, 80] : size === '80x100' ? [80, 100] : [100, 120];
  const grid: (ColorRef | null)[][] = [];
  const color_counts: Record<string, number> = {};
  const coords: [number, number, string][] = [];
  const no_bead_mask: boolean[][] = [];
  let bead_total = 0;

  for (let r = 0; r < rows; r++) {
    const rowList: (ColorRef | null)[] = [];
    const maskRow: boolean[] = [];
    for (let c = 0; c < cols; c++) {
      // 随机给点空白区域 (不放豆子)，人脸/动物边缘识别
      const isNoBead = (r < 5 || r > rows - 5 || c < 5 || c > cols - 5) && Math.random() > 0.4;
      if (isNoBead) {
        rowList.push(null);
        maskRow.push(true);
      } else {
        // 随机分配一个色号
        const color = mockColorPalette[Math.floor(Math.random() * mockColorPalette.length)];
        rowList.push(color);
        maskRow.push(false);
        bead_total++;
        color_counts[color.code] = (color_counts[color.code] || 0) + 1;
        coords.push([r, c, color.code]);
      }
    }
    grid.push(rowList);
    no_bead_mask.push(maskRow);
  }

  return {
    grid,
    color_counts,
    bead_total,
    coords,
    no_bead_mask,
    palette_used: mockColorPalette.filter(color => !!color_counts[color.code]),
    estimated_cost_cny: Number((bead_total * 0.0065).toFixed(2)), // 1000 颗 6.5 元平均
    suggested_buffer_pct: 10,
    brand: 'MARD',
    bead_diameter_mm: 5.0
  };
}

/* ==========================================
   API 服务函数
   ========================================== */

export const api = {
  /* ----------------- 用户与账户 ----------------- */
  // 微信登录 / 注册
  login(code: string): Promise<{ token: string; user: User }> {
    if (USE_MOCK) {
      return Promise.resolve({
        token: 'mock_token_abcdef123456',
        user: {
          user_id: 'mock_openid_123',
          nickname: '拼豆资深玩家',
          avatar: '/static/assets/qr-placeholder.svg',
          created_at: '2026-05-24T12:00:00Z',
          free_credits_remaining: 3,
          paid_credits: 0,
          monthly_card_expires_at: null,
          privacy_consent_at: '2026-05-24T12:00:00Z',
          sensitive_consent_at: null
        }
      });
    }
    return request({ url: '/user/login', method: 'POST', data: { code } });
  },

  // 获取个人资料
  getProfile(): Promise<User> {
    if (USE_MOCK) {
      const stored = uni.getStorageSync('pd_user');
      return Promise.resolve(stored || {
        user_id: 'mock_openid_123',
        nickname: '拼豆资深玩家',
        avatar: '/static/assets/qr-placeholder.svg',
        created_at: '2026-05-24T12:00:00Z',
        free_credits_remaining: 3,
        paid_credits: 0,
        monthly_card_expires_at: null,
        privacy_consent_at: '2026-05-24T12:00:00Z',
        sensitive_consent_at: null
      });
    }
    return request({ url: '/user/profile', method: 'GET' });
  },

  // 记录合规协议同意留痕
  submitConsent(type: 'privacy' | 'sensitive'): Promise<{ success: boolean; consent_at: string }> {
    if (USE_MOCK) {
      return Promise.resolve({ success: true, consent_at: new Date().toISOString() });
    }
    return request({ url: '/user/consent', method: 'POST', data: { type } });
  },

  /* ----------------- AI Preview 生成器 ----------------- */
  // AI 路径：上传照片并生成 Q 版 Q 版预览 (PreviewProvider.generate)
  generatePreview(filePath: string, style: StylePreset, size: SizePreset, seed?: number): Promise<PreviewResult> {
    if (USE_MOCK) {
      return new Promise((resolve) => {
        // 模拟生成耗时
        setTimeout(() => {
          resolve({
            preview_id: 'preview_mock_' + Math.random().toString(36).substr(2, 9),
            // 使用 shared/assets 的假素材作为 placeholder
            image_url: '/static/assets/bead-cat.svg',
            target_color_count: 12 + Math.floor(Math.random() * 12),
            provider_used: 'xiaochi_gpt_image_2',
            fallback_count: 0,
            cost_estimate: 0,
            latency_ms: 22000
          });
        }, 3000); // Mock 耗时设为 3s (方便演示)
      });
    }

    // 真机上传使用 uni.uploadFile 包装
    return new Promise((resolve, reject) => {
      const token = uni.getStorageSync('pd_token') || '';
      uni.uploadFile({
        url: `${BASE_URL}/preview/generate`, // uni.uploadFile 必须完整 URL（不走 request 拦截器）
        filePath: filePath,
        name: 'image',
        timeout: UPLOAD_TIMEOUT_MS,
        formData: {
          style_preset: style,
          size_preset: size,
          seed: seed ? String(seed) : ''
        },
        header: {
          'Authorization': token ? `Bearer ${token}` : ''
        },
        success: (res) => {
          if (res.statusCode >= 200 && res.statusCode < 300) {
            resolve(JSON.parse(res.data) as PreviewResult);
          } else {
            reject(uploadResponseError(res, '上传失败'));
          }
        },
        fail: (err) => reject(uploadFailError(err))
      });
    });
  },

  /* ----------------- 图纸生成器 (PatternBuilder) ----------------- */
  // 生成拼豆图纸 (本地 CIEDE2000 / K-Means 类似算法服务端实现)
  buildPattern(params: {
    size: SizePreset;
    preview_id?: string; // AI 路径
    rawImageFilePath?: string; // 脚本路径专属
    brand?: string;
    bead_diameter_mm?: number;
    mode: 'auto' | 'script' | 'ai';
  }): Promise<PatternSheet> {
    if (USE_MOCK) {
      return new Promise((resolve) => {
        setTimeout(() => {
          resolve(generateMockPatternSheet(params.size));
        }, 1000);
      });
    }

    if (params.rawImageFilePath) {
      // 脚本路径，使用 uploadFile 上传原图直接生成
      return new Promise((resolve, reject) => {
        const token = uni.getStorageSync('pd_token') || '';
        uni.uploadFile({
          url: `${BASE_URL}/pattern/build`, // uni.uploadFile 必须完整 URL（不走 request 拦截器）
          filePath: params.rawImageFilePath!,
          name: 'raw_image',
          timeout: UPLOAD_TIMEOUT_MS,
          formData: {
            size: params.size,
            brand: params.brand || 'MARD',
            bead_diameter_mm: String(params.bead_diameter_mm || 5.0),
            mode: params.mode
          },
          header: { 'Authorization': token ? `Bearer ${token}` : '' },
          success: (res) => {
            if (res.statusCode >= 200 && res.statusCode < 300) {
              resolve(JSON.parse(res.data) as PatternSheet);
            } else {
              reject(uploadResponseError(res, '图纸生成失败'));
            }
          },
          fail: (err) => reject(uploadFailError(err))
        });
      });
    } else {
      // AI 路径，使用 preview_id 纯 JSON 呼叫
      return request({
        url: '/pattern/build',
        method: 'POST',
        data: {
          size: params.size,
          preview_id: params.preview_id,
          brand: params.brand || 'MARD',
          bead_diameter_mm: params.bead_diameter_mm || 5.0,
          mode: params.mode
        }
      });
    }
  },

  /* ----------------- 作品集 (Artwork) ----------------- */
  // 获取用户所有的作品
  getArtworks(): Promise<Artwork[]> {
    if (USE_MOCK) {
      return Promise.resolve([
        {
          artwork_id: 'art_101',
          user_id: 'mock_openid_123',
          created_at: '2026-05-24T10:15:00Z',
          original_image_url: null,
          original_image_deleted_at: '2026-05-24T10:15:00Z',
          style_preset: 'q_portrait',
          size_preset: '60x80',
          preview_url: '/static/assets/bead-cat.svg',
          pattern_data: generateMockPatternSheet('60x80'),
          title: '可爱小猫拼豆',
          is_paid_unlocked: false
        },
        {
          artwork_id: 'art_102',
          user_id: 'mock_openid_123',
          created_at: '2026-05-23T16:40:00Z',
          original_image_url: null,
          original_image_deleted_at: '2026-05-23T16:40:00Z',
          style_preset: 'q_couple',
          size_preset: '100x120',
          preview_url: '/static/assets/bead-heart.svg',
          pattern_data: generateMockPatternSheet('100x120'),
          title: '浪漫爱心拼豆',
          is_paid_unlocked: true // 已解锁高级
        }
      ]);
    }
    return request({ url: '/artwork/list', method: 'GET' });
  },

  // 获取单件作品详情
  getArtworkDetail(id: string): Promise<Artwork> {
    if (USE_MOCK) {
      return Promise.resolve({
        artwork_id: id,
        user_id: 'mock_openid_123',
        created_at: '2026-05-24T10:15:00Z',
        original_image_url: null,
        original_image_deleted_at: '2026-05-24T10:15:00Z',
        style_preset: 'q_portrait',
        size_preset: '80x100',
        preview_url: '/static/assets/bead-cat.svg',
        pattern_data: generateMockPatternSheet('80x100'),
        title: '我的精品拼豆图纸',
        is_paid_unlocked: id === 'art_102'
      });
    }
    return request({ url: `/artwork/${id}`, method: 'GET' });
  },

  // 删除作品 (PRD §4.10)
  deleteArtwork(id: string): Promise<{ success: boolean }> {
    if (USE_MOCK) {
      return Promise.resolve({ success: true });
    }
    return request({ url: `/artwork/${id}`, method: 'DELETE' });
  },

  /* ----------------- CDK 兑换 ----------------- */
  // 校验并兑换 18 位 CDK (PRD §4.9)
  redeemCDK(cdkCode: string): Promise<CDKRedeemResult> {
    if (USE_MOCK) {
      return new Promise((resolve, reject) => {
        setTimeout(() => {
          const codeClean = cdkCode.replace(/[\s-]/g, '').toUpperCase();
          if (codeClean.length !== 18) {
            reject(new Error('请输入18位卡密哦~'));
            return;
          }
          // 模拟成功/失败校验
          if (codeClean.startsWith('FAIL')) {
            reject(new Error('卡密不存在，请仔细检查哦~'));
          } else if (codeClean.startsWith('USED')) {
            reject(new Error('该卡密已经被兑换过了哦~'));
          } else if (codeClean.includes('EXP')) {
            reject(new Error('该卡密已过期了呢~'));
          } else {
            resolve({
              success: true,
              cdk_type: codeClean.startsWith('MON') ? 'monthly_card' : 'single_use',
              value: 1,
              expires_at: codeClean.startsWith('MON') ? new Date(Date.now() + 30 * 24 * 3600 * 1000).toISOString() : null
            });
          }
        }, 1200);
      });
    }
    return request({ url: '/cdk/redeem', method: 'POST', data: { cdk_code: cdkCode } });
  },

  /* ----------------- 支付与订单 ----------------- */
  // 创建订单 (PRD §4.8)
  createOrder(sku: 'single_9.9' | 'monthly_28' | 'custom_99', artworkId?: string): Promise<Order> {
    if (USE_MOCK) {
      return Promise.resolve({
        order_id: 'order_mock_' + Math.random().toString(36).substr(2, 9),
        user_id: 'mock_openid_123',
        created_at: new Date().toISOString(),
        sku: sku,
        amount_cny: sku === 'single_9.9' ? 9.9 : sku === 'monthly_28' ? 28.0 : 99.0,
        status: 'pending',
        payment_method: 'wechat_qr_via_cs',
        artwork_id: artworkId || null
      });
    }
    return request({ url: '/payment/order/create', method: 'POST', data: { sku_id: sku, artwork_id: artworkId } });
  },

  // 获取订单状态
  getOrderStatus(orderId: string): Promise<{ status: 'pending' | 'paid_confirmed' | 'failed' }> {
    if (USE_MOCK) {
      return Promise.resolve({ status: 'pending' });
    }
    return request({ url: `/payment/order/${orderId}`, method: 'GET' });
  },

  // 获取客服支付二维码 (PRD §4.8 客服扫码付机制)
  getCustomerServiceQR(orderId: string): Promise<{ qr_url: string; wx_id: string; order_id: string }> {
    if (USE_MOCK) {
      return Promise.resolve({
        qr_url: '/static/assets/qr-placeholder.svg',
        wx_id: 'pindou_cs_01',
        order_id: orderId
      });
    }
    return request({ url: `/payment/customer-service`, method: 'GET', data: { order_id: orderId } });
  }
};
