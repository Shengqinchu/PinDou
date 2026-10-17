export * from './client';
export * from './types';

import { apiRequest } from './client';
import type {
  Artwork,
  ArtworkListResponse,
  AvatarUploadResponse,
  ConsentResponse,
  CDKRedeemResult,
  GenerationJobResponse,
  GenerateScriptResponse,
  Order,
  OrderStatusResponse,
  PaymentSkuCatalog,
  PaymentSkuId,
  PartitionSheet,
  PatternSheet,
  SaveArtworkPatternResponse,
  SizePreset,
  StylePreset,
  User
} from './types';

export interface EmailCodeResponse {
  success: boolean;
  message?: string;
  expires_in_seconds?: number;
  cooldown_seconds?: number;
}

export interface AuthResponse {
  token: string;
  user: User;
  device_token?: string | null;
  device_id?: string | null;
  device_migration?: DeviceMigrationResult | null;
}

export interface RegisterResponse extends AuthResponse {
  cdk?: {
    success: boolean;
    cdk_type?: string;
    value?: number;
    message_cn?: string;
  };
}

export interface DeviceMigrationResult {
  status: string;
  device_id: string;
  user_id: string;
  migrated: boolean;
  moved_points?: number;
  moved_credit_grants?: number;
  moved_credit_transactions?: number;
  moved_memberships?: number;
  moved_artworks?: number;
  moved_jobs?: number;
  moved_cdks?: number;
  claimed_by_user_id?: string | null;
}

export function sendEmailCode(email: string): Promise<EmailCodeResponse> {
  return apiRequest<EmailCodeResponse>('/user/email/send-code', {
    method: 'POST',
    auth: false,
    body: { email }
  });
}

export function verifyEmailCode(email: string, code: string): Promise<AuthResponse> {
  return apiRequest<AuthResponse>('/user/email/verify', {
    method: 'POST',
    auth: false,
    body: { email, code }
  });
}

export function registerWebAccount(payload: {
  email: string;
  code: string;
  password: string;
  cdk?: string;
}): Promise<RegisterResponse> {
  return apiRequest<RegisterResponse>('/user/register', {
    method: 'POST',
    auth: false,
    body: payload
  });
}

export function emailPasswordLogin(email: string, password: string): Promise<AuthResponse> {
  return apiRequest<AuthResponse>('/user/email-login', {
    method: 'POST',
    auth: false,
    body: { email, password }
  });
}

export function getProfile(): Promise<User> {
  return apiRequest<User>('/user/profile');
}

export function getWalletProfile(): Promise<User> {
  return apiRequest<User>('/wallet/profile', {
    auth: false
  });
}

export function updateProfile(payload: { nickname?: string; avatar_url?: string }): Promise<User> {
  return apiRequest<User>('/user/profile', {
    method: 'PATCH',
    body: payload
  });
}

export function uploadAvatar(file: File): Promise<AvatarUploadResponse> {
  const form = new FormData();
  form.set('image', file);
  return apiRequest<AvatarUploadResponse>('/user/avatar', {
    method: 'POST',
    body: form
  });
}

export function getSkus(): Promise<PaymentSkuCatalog> {
  return apiRequest<PaymentSkuCatalog>('/payment/skus', {
    auth: false
  });
}

export function createOrder(payload: { sku_id: PaymentSkuId; artwork_id?: string | null }): Promise<Order> {
  return apiRequest<Order>('/payment/order/create', {
    method: 'POST',
    body: payload
  });
}

export function getOrder(orderRef: string): Promise<OrderStatusResponse> {
  return apiRequest<OrderStatusResponse>(`/payment/order/${encodeURIComponent(orderRef)}`);
}

export function redeemCdk(cdk_code: string, options: { auth?: boolean } = {}): Promise<CDKRedeemResult> {
  return apiRequest<CDKRedeemResult>('/cdk/redeem', {
    method: 'POST',
    auth: options.auth ?? true,
    body: { cdk_code }
  });
}

export function submitConsent(type: 'privacy' | 'sensitive'): Promise<ConsentResponse> {
  return apiRequest<ConsentResponse>('/user/consent', {
    method: 'POST',
    body: { type }
  });
}

export function generateScriptPattern(file: File, size: SizePreset = '26x26'): Promise<GenerateScriptResponse> {
  const form = new FormData();
  form.set('raw_image', file);
  form.set('size', size);
  form.set('size_preset', size);
  form.set('brand', 'MARD');
  form.set('mode', 'script');
  form.set('auto_remove_white_bg', 'true');

  return apiRequest<GenerateScriptResponse>('/generate/script', {
    method: 'POST',
    body: form
  });
}

export function generateAiPattern(
  file: File,
  size: SizePreset = '52x52',
  style: StylePreset = 'q_portrait'
): Promise<GenerationJobResponse> {
  const form = new FormData();
  form.set('image', file);
  form.set('size', size);
  form.set('size_preset', size);
  form.set('style', style);
  form.set('style_preset', style);
  form.set('brand', 'MARD');

  return apiRequest<GenerationJobResponse>('/generate/ai', {
    method: 'POST',
    body: form
  });
}

export function getGenerationStatus(jobId: string): Promise<GenerationJobResponse> {
  return apiRequest<GenerationJobResponse>(`/generate/status/${encodeURIComponent(jobId)}`);
}

export function getArtworkDetail(artworkId: string): Promise<Artwork> {
  return apiRequest<Artwork>(`/artwork/${encodeURIComponent(artworkId)}`);
}

export function getArtworkGallery(page = 1, size = 12): Promise<ArtworkListResponse> {
  const params = new URLSearchParams({ page: String(page), size: String(size) });
  return apiRequest<ArtworkListResponse>(`/artwork/gallery?${params.toString()}`);
}

export function saveArtworkPattern(
  artworkId: string,
  patternJson: PatternSheet,
  options: { renderPreview?: boolean } = {}
): Promise<SaveArtworkPatternResponse> {
  return apiRequest<SaveArtworkPatternResponse>(`/artwork/${encodeURIComponent(artworkId)}/pattern`, {
    method: 'PUT',
    body: {
      pattern_json: patternJson,
      render_preview: options.renderPreview ?? true
    }
  });
}

export function getPattern(artworkId: string): Promise<PatternSheet> {
  return apiRequest<PatternSheet>(`/pattern/${encodeURIComponent(artworkId)}`);
}

export function getPatternPartitions(artworkId: string): Promise<PartitionSheet> {
  return apiRequest<PartitionSheet>(`/pattern/${encodeURIComponent(artworkId)}/partitions`);
}
