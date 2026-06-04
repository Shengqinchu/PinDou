export * from './client';
export * from './types';

import { apiRequest } from './client';
import type {
  Artwork,
  ArtworkListResponse,
  AvatarUploadResponse,
  ConsentResponse,
  GenerationJobResponse,
  GenerateScriptResponse,
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
}

export interface RegisterResponse extends AuthResponse {
  cdk?: {
    success: boolean;
    cdk_type?: string;
    value?: number;
    message_cn?: string;
  };
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
  patternJson: PatternSheet
): Promise<SaveArtworkPatternResponse> {
  return apiRequest<SaveArtworkPatternResponse>(`/artwork/${encodeURIComponent(artworkId)}/pattern`, {
    method: 'PUT',
    body: { pattern_json: patternJson }
  });
}

export function getPattern(artworkId: string): Promise<PatternSheet> {
  return apiRequest<PatternSheet>(`/pattern/${encodeURIComponent(artworkId)}`);
}

export function getPatternPartitions(artworkId: string): Promise<PartitionSheet> {
  return apiRequest<PartitionSheet>(`/pattern/${encodeURIComponent(artworkId)}/partitions`);
}
