// PinDou 统一请求库封装 (微信云托管 callContainer + 传统 HTTP fallback)

declare const process: {
  env?: {
    NODE_ENV?: string;
    VITE_PINDOU_DEV_API?: string;
    VITE_PINDOU_PROD_API?: string;
    VITE_USE_WX_CLOUD?: string;
    VITE_WX_CLOUD_ENV?: string;
    VITE_WX_CLOUD_SERVICE?: string;
    VITE_WX_CLOUD_API_PREFIX?: string;
  };
};

declare const wx: any;

const viteEnv = (import.meta as any).env || {};
const runtimeEnv = {
  ...viteEnv,
  ...(typeof process !== 'undefined' && process.env ? process.env : {})
};
const DEV_API = runtimeEnv.VITE_PINDOU_DEV_API || 'http://192.168.2.40:8000/api/v1';
const PROD_API = runtimeEnv.VITE_PINDOU_PROD_API || 'https://api.pindou.cn/api/v1';
const isDev = runtimeEnv.NODE_ENV !== 'production';
const storageWxCloudFlag = uni.getStorageSync('pd_use_wx_cloud');

export const BASE_URL = normalizeBaseUrl(
  uni.getStorageSync('pd_api_base_url') || (isDev ? DEV_API : PROD_API)
);
export const USE_WX_CLOUD = storageWxCloudFlag
  ? storageWxCloudFlag !== 'false'
  : runtimeEnv.VITE_USE_WX_CLOUD !== 'false';
export const WX_CLOUD_ENV = runtimeEnv.VITE_WX_CLOUD_ENV || 'prod-01';
export const WX_CLOUD_SERVICE = runtimeEnv.VITE_WX_CLOUD_SERVICE || 'pindou-backend';
const WX_CLOUD_API_PREFIX = normalizeApiPrefix(runtimeEnv.VITE_WX_CLOUD_API_PREFIX || '/api/v1');

interface RequestOptions {
  url: string;
  method?: 'GET' | 'POST' | 'PUT' | 'DELETE';
  data?: any;
  headers?: Record<string, string>;
  hideErrorToast?: boolean;
  _retried?: boolean;
  _skipAuthRefresh?: boolean;
}

type LoginResponse = {
  token: string;
  user: any;
};

class RequestError extends Error {
  statusCode: number;
  data: any;

  constructor(message: string, statusCode: number, data: any) {
    super(message);
    this.name = 'RequestError';
    this.statusCode = statusCode;
    this.data = data;
  }
}

let authRefreshPromise: Promise<void> | null = null;

export async function request<T = any>(options: RequestOptions): Promise<T> {
  try {
    return await sendRequest<T>(options);
  } catch (error) {
    if (!shouldRefreshAuth(error, options)) {
      throw error;
    }

    await refreshAuthOnce();
    return sendRequest<T>({
      ...options,
      _retried: true
    });
  }
}

function sendRequest<T = any>(options: RequestOptions): Promise<T> {
  if (USE_WX_CLOUD && canUseWxCloud()) {
    return wxCloudRequest<T>(options);
  }
  return legacyHttpRequest<T>(options);
}

function legacyHttpRequest<T = any>(options: RequestOptions): Promise<T> {
  const token = uni.getStorageSync('pd_token') || '';

  // 组装完整 URL
  const fullUrl = options.url.startsWith('http')
    ? options.url
    : `${BASE_URL}${options.url.startsWith('/') ? '' : '/'}${options.url}`;

  const header = {
    'Content-Type': 'application/json',
    'Authorization': token ? `Bearer ${token}` : '',
    ...options.headers,
  };

  return new Promise((resolve, reject) => {
    uni.request({
      url: fullUrl,
      method: options.method || 'GET',
      data: options.data,
      header,
      success: (res) => {
        if (res.statusCode >= 200 && res.statusCode < 300) {
          resolve(res.data as T);
        } else {
          // 处理 4xx/500 等 HTTP 错误
          const friendlyMessage = translateError(res.data, res.statusCode);
          if (shouldShowErrorToast(options, res.statusCode)) {
            uni.showToast({
              title: friendlyMessage,
              icon: 'none',
              duration: 3000
            });
          }
          reject(new RequestError(friendlyMessage, res.statusCode, res.data));
        }
      },
      fail: (err) => {
        // 网络不通、超时等底层错误
        const friendlyMessage = '网络有点不给力，请稍后再试哦~';
        if (!options.hideErrorToast) {
          uni.showToast({
            title: friendlyMessage,
            icon: 'none',
            duration: 3000
          });
        }
        reject(err);
      }
    });
  });
}

function wxCloudRequest<T = any>(options: RequestOptions): Promise<T> {
  const token = uni.getStorageSync('pd_token') || '';
  const requestPath = cloudPath(options.url);
  const header = {
    'Content-Type': 'application/json',
    'Authorization': token ? `Bearer ${token}` : '',
    'X-WX-SERVICE': WX_CLOUD_SERVICE,
    ...options.headers,
  };

  return new Promise((resolve, reject) => {
    wx.cloud.callContainer({
      config: { env: WX_CLOUD_ENV },
      path: requestPath,
      method: options.method || 'GET',
      header,
      data: options.data,
      success: (res: any) => {
        const statusCode = Number(res?.statusCode || 0);
        if (statusCode >= 200 && statusCode < 300) {
          resolve(res.data as T);
          return;
        }
        const friendlyMessage = translateError(res?.data, statusCode);
        if (shouldShowErrorToast(options, statusCode)) {
          uni.showToast({
            title: friendlyMessage,
            icon: 'none',
            duration: 3000
          });
        }
        reject(new RequestError(friendlyMessage, statusCode, res?.data));
      },
      fail: (err: any) => {
        if (shouldFallbackToLegacyHttp(err)) {
          console.warn('wx.cloud.callContainer failed, fallback to HTTPS API', {
            errCode: err?.errCode || err?.code,
            errMsg: err?.errMsg || err?.message,
            env: WX_CLOUD_ENV,
            service: WX_CLOUD_SERVICE,
            path: requestPath,
            baseUrl: BASE_URL,
          });
          legacyHttpRequest<T>(options).then(resolve).catch(reject);
          return;
        }

        const friendlyMessage = '网络有点不给力，请稍后再试哦~';
        if (!options.hideErrorToast) {
          uni.showToast({
            title: friendlyMessage,
            icon: 'none',
            duration: 3000
          });
        }
        reject(err);
      }
    });
  });
}

function shouldShowErrorToast(options: RequestOptions, statusCode: number): boolean {
  return !options.hideErrorToast && !(statusCode === 401 && canRefreshAuth(options));
}

function canRefreshAuth(options: RequestOptions): boolean {
  return !options._retried && !options._skipAuthRefresh && !isLoginRequest(options.url);
}

function shouldRefreshAuth(error: unknown, options: RequestOptions): boolean {
  if (!canRefreshAuth(options)) {
    return false;
  }
  return isUnauthorizedError(error);
}

function isUnauthorizedError(error: unknown): boolean {
  const statusCode = Number((error as any)?.statusCode || 0);
  if (statusCode === 401) {
    return true;
  }

  const message = String((error as Error)?.message || error || '');
  return message.includes('登录已过期') || message.includes('请先登录');
}

function isLoginRequest(url: string): boolean {
  return cloudPath(url).includes('/user/login');
}

function refreshAuthOnce(): Promise<void> {
  if (!authRefreshPromise) {
    authRefreshPromise = performWxLogin().finally(() => {
      authRefreshPromise = null;
    });
  }
  return authRefreshPromise;
}

async function performWxLogin(): Promise<void> {
  clearStoredAuth();
  const code = await getWxLoginCode();
  const data = await sendRequest<LoginResponse>({
    url: '/user/login',
    method: 'POST',
    data: { code },
    hideErrorToast: true,
    _retried: true,
    _skipAuthRefresh: true
  });

  uni.setStorageSync('pd_token', data.token);
  uni.setStorageSync('pd_user', JSON.stringify(data.user));
  await syncUserStore(data);
}

function clearStoredAuth() {
  uni.removeStorageSync('pd_token');
  uni.removeStorageSync('pd_user');
}

function getWxLoginCode(): Promise<string> {
  return new Promise((resolve, reject) => {
    uni.login({
      provider: 'weixin',
      success: (loginRes) => {
        if (loginRes.code) {
          resolve(loginRes.code);
        } else {
          reject(new Error('微信登录失败：未获取到 code'));
        }
      },
      fail: reject
    });
  });
}

async function syncUserStore(data: LoginResponse): Promise<void> {
  try {
    const userModule = await import('../store/user');
    const userStore = userModule.useUserStore();
    userStore.token = data.token;
    userStore.userInfo = data.user;
  } catch (error) {
    console.warn('同步登录态到 userStore 失败，已写入本地缓存:', error);
  }
}

/**
 * 依据 PRD §7.2 规范：过滤英文及技术底层细节，统一友好中文提示
 */
function translateError(errorData: any, statusCode: number): string {
  if (statusCode === 401) {
    return '登录已过期，请重新登录哦~';
  }
  if (statusCode === 403) {
    return '您还没有此项操作的权限呢~';
  }
  if (statusCode === 404) {
    return '抱歉，没有找到相关资源~';
  }
  if (statusCode === 429) {
    return '您点击得太快啦，休息一下再试试吧~';
  }

  // 从后端返回数据中尝试查找 message (优先读取 PRD §6 指定的 message_cn)
  const msg = typeof errorData === 'string'
    ? errorData
    : (errorData?.message_cn || errorData?.message || errorData?.error || '');

  if (msg) {
    // 处理特定业务字段的翻译，不把原始英文暴露给用户
    const msgLower = msg.toLowerCase();
    if (msgLower.includes('timeout') || msgLower.includes('gateway')) {
      return '网络有点慢，请重新再试一次吧~';
    }
    if (msgLower.includes('invalid cdk') || msgLower.includes('cdk not found')) {
      return '兑换码不正确，请检查输入是否正确哦~';
    }
    if (msgLower.includes('cdk redeemed')) {
      return '该兑换码已经被兑换过了哦~';
    }
    if (msgLower.includes('insufficient credits') || msgLower.includes('no credit')) {
      return '您的 AI 额度不足，去充值或兑换一些额度吧~';
    }
    if (msgLower.includes('file too large')) {
      return '上传的照片太大了，请上传小于 10MB 的照片哦~';
    }
    if (msgLower.includes('format') || msgLower.includes('extension')) {
      return '不支持这种格式的照片，请上传 jpg, png 或 webp 格式哦~';
    }
  }

  return '系统开了一会儿小差，请重新再试一次哦~';
}

function normalizeBaseUrl(url: string): string {
  return url.replace(/\/+$/, '');
}

function normalizeApiPrefix(prefix: string): string {
  const normalized = prefix.trim() || '/api/v1';
  return normalized.startsWith('/') ? normalized.replace(/\/+$/, '') : `/${normalized.replace(/\/+$/, '')}`;
}

function cloudPath(url: string): string {
  if (url.startsWith('http')) {
    return url;
  }
  const path = url.startsWith('/') ? url : `/${url}`;
  if (path.startsWith(WX_CLOUD_API_PREFIX + '/') || path === WX_CLOUD_API_PREFIX) {
    return path;
  }
  return `${WX_CLOUD_API_PREFIX}${path}`;
}

function shouldFallbackToLegacyHttp(err: any): boolean {
  if (!BASE_URL.startsWith('https://')) {
    return false;
  }

  const errCode = String(err?.errCode || err?.code || '');
  const errMsg = String(err?.errMsg || err?.message || '');
  return errCode === '102002'
    || errCode === '-606001'
    || errMsg.includes('102002')
    || errMsg.includes('-606001')
    || errMsg.includes('cloud.callContainer:fail system error');
}

function canUseWxCloud(): boolean {
  return typeof wx !== 'undefined' && !!wx.cloud && typeof wx.cloud.callContainer === 'function';
}
