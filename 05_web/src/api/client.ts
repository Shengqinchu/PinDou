import { getToken } from '../auth/tokenStorage';
import { expireAuthSession } from '../router';

export const API_BASE = '/api/v1';

export interface ApiErrorBody {
  error?: string;
  message?: string;
  message_cn?: string;
  detail?: unknown;
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
    this.detail = body.detail;
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
    expireAuthSession();
    throw new ApiError(401, await readErrorBody(response));
  }

  if (!response.ok) {
    throw new ApiError(response.status, await readErrorBody(response));
  }

  if (response.status === 204) {
    return undefined as T;
  }

  return (await response.json()) as T;
}

async function readErrorBody(response: Response): Promise<ApiErrorBody> {
  try {
    return (await response.json()) as ApiErrorBody;
  } catch (_error) {
    return { error: String(response.status), message: response.statusText };
  }
}
