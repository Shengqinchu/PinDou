import { getDeviceToken, getToken, setDeviceToken } from '../auth/tokenStorage';
import { expireGeneratorSession } from '../host';

export const API_BASE = '/api/v1';

export interface ApiErrorBody {
  error?: string;
  message?: string;
  message_cn?: string;
  detail?: unknown;
  details?: unknown;
}

export class ApiError extends Error {
  status: number;
  code: string;
  detail?: unknown;

  constructor(status: number, body: ApiErrorBody = {}) {
    super(body.message_cn || body.message || body.error || `请求失败 (${status})`);
    this.name = 'ApiError';
    this.status = status;
    this.code = body.error || String(status);
    this.detail = body.detail ?? body.details;
  }
}

export interface ApiRequestOptions extends Omit<RequestInit, 'body'> {
  body?: BodyInit | Record<string, unknown> | null;
  auth?: boolean;
}

export async function apiRequest<T>(path: string, options: ApiRequestOptions = {}): Promise<T> {
  const { body, auth = true, headers, ...rest } = options;
  const requestHeaders = new Headers(headers);
  const token = getToken();
  let requestBody: BodyInit | undefined;

  if (auth && token) {
    requestHeaders.set('Authorization', `Bearer ${token}`);
  } else {
    const deviceToken = getDeviceToken();
    if (deviceToken) {
      requestHeaders.set('X-PinDou-Device', deviceToken);
    }
  }

  if (body instanceof FormData || body instanceof Blob || body instanceof URLSearchParams) {
    requestBody = body;
  } else if (body != null) {
    requestHeaders.set('Content-Type', 'application/json');
    requestBody = JSON.stringify(body);
  }

  const response = await fetch(`${API_BASE}${path.startsWith('/') ? path : `/${path}`}`, {
    credentials: 'same-origin',
    ...rest,
    headers: requestHeaders,
    body: requestBody
  });

  if (response.status === 401) {
    const errorBody = await readErrorBody(response);
    if (auth) {
      void expireGeneratorSession(token);
    }
    throw new ApiError(401, errorBody);
  }

  if (!response.ok) {
    throw new ApiError(response.status, await readErrorBody(response));
  }

  if (response.status === 204) {
    return undefined as T;
  }

  const payload = await response.json();
  if(auth&&token!==getToken())throw new ApiError(409,{error:'SESSION_CHANGED',message_cn:'登录账号已变化，请重新打开此页面。'});
  persistDeviceToken(payload);
  return payload as T;
}

async function readErrorBody(response: Response): Promise<ApiErrorBody> {
  try {
    return (await response.json()) as ApiErrorBody;
  } catch (_error) {
    return { error: String(response.status), message: response.statusText };
  }
}

function persistDeviceToken(payload: unknown): void {
  if (!payload || typeof payload !== 'object') {
    return;
  }
  const token = (payload as { device_token?: unknown }).device_token;
  if (typeof token === 'string' && token) {
    setDeviceToken(token);
  }
}
