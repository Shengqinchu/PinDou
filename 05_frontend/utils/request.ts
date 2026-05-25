// PinDou 统一请求库封装 (uni.request)

const BASE_URL = 'http://127.0.0.1:8000/api/v1'; // 联调时指向真后端，线上预留则见 process.env

interface RequestOptions {
  url: string;
  method?: 'GET' | 'POST' | 'PUT' | 'DELETE';
  data?: any;
  headers?: Record<string, string>;
  hideErrorToast?: boolean;
}

export function request<T = any>(options: RequestOptions): Promise<T> {
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
          if (!options.hideErrorToast) {
            uni.showToast({
              title: friendlyMessage,
              icon: 'none',
              duration: 3000
            });
          }
          reject(new Error(friendlyMessage));
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
