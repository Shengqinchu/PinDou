export type StylePreset = 'q_portrait' | 'q_pet' | 'q_couple' | 'cartoon_fallback';
export type SizePreset = '26x26' | '52x52' | '78x78' | '104x104' | `${number}x${number}`;
export type CDKType = 'points' | 'membership' | 'single_use' | 'monthly_card' | 'credit_pack_5' | 'credit_pack_10';
export type PaymentSkuCategory = 'points' | 'membership';
export type PaymentSkuId =
  | 'points_trial_099'
  | 'points_standard_990'
  | 'points_value_2990'
  | 'membership_week_990'
  | 'membership_month_1990'
  | 'membership_season_4990'
  | string;

export interface User {
  user_id: string;
  openid?: string | null;
  email?: string | null;
  nickname?: string;
  avatar?: string;
  created_at?: string;
  free_credits_remaining?: number;
  normal_trial_remaining?: number;
  paid_credits?: number;
  ai_points_balance?: number;
  ai_points_paid?: number;
  ai_points_gift?: number;
  ai_points_reserved?: number;
  ai_generation_cost_points?: number;
  register_gift_points?: number;
  register_gift_days?: number;
  is_unlimited_account?: boolean;
  membership_expires_at?: string | null;
  monthly_card_expires_at?: string | null;
  privacy_consent_at?: string | null;
  sensitive_consent_at?: string | null;
}

export interface AvatarUploadResponse {
  avatar_url: string;
  user: User;
}

export interface ColorRef {
  brand: string;
  code: string;
  name_cn: string;
  name_en?: string | null;
  hex: string;
  rgb: [number, number, number];
  bead_diameter_mm?: number;
}

export interface PatternSheet {
  grid: (ColorRef | null)[][];
  color_counts: Record<string, number>;
  bead_total: number;
  coords?: Array<{ row: number; col: number; code: string | null } | [number, number, string | null]>;
  no_bead_mask?: boolean[][];
  palette_used: ColorRef[];
  estimated_cost_cny?: number;
  suggested_buffer_pct?: number;
  brand?: string;
  bead_diameter_mm?: number;
  metadata?: Record<string, unknown>;
  image_url?: string;
}

export interface PartitionItem {
  index: number;
  key?: string;
  label: string;
  row_start: number;
  row_end: number;
  col_start: number;
  col_end: number;
  grid_offset?: { row: number; col: number };
  rows: number;
  cols: number;
  url: string;
}

export interface PartitionSheet {
  artwork_id: string;
  partition_size: number;
  partition_layout?: string;
  rows: number;
  cols: number;
  total: number;
  items: PartitionItem[];
}

export interface PreviewResult {
  preview_id: string;
  image_url: string;
  style_preset: StylePreset;
  size_preset: SizePreset;
  seed?: number | null;
  metadata?: Record<string, unknown>;
}

export interface Artwork {
  artwork_id: string;
  user_id: string;
  title?: string | null;
  original_path?: string | null;
  original_image_url?: string | null;
  original_image_deleted_at?: string | null;
  preview_path?: string | null;
  preview_url?: string | null;
  thumbnail_url?: string | null;
  pattern_data: PatternSheet;
  style_preset: StylePreset | string;
  size_preset: SizePreset | string;
  is_paid_unlocked?: boolean;
  created_at?: string;
  updated_at?: string;
}

export interface ArtworkListItem {
  artwork_id: string;
  title?: string | null;
  thumbnail_url?: string | null;
  preview_url?: string | null;
  size_preset: SizePreset | string;
  bead_count: number;
  color_count: number;
  style_preset?: StylePreset | string;
  created_at?: string;
}

export interface ArtworkListResponse {
  items: ArtworkListItem[];
  total: number;
  page: number;
  size: number;
  has_more: boolean;
}

export interface GenerateScriptResponse {
  artwork_id: string;
  pattern_url: string;
  pattern: PatternSheet;
}

export type GenerationJobStatus = 'queued' | 'running' | 'succeeded' | 'failed' | string;

export interface GenerationJobResponse {
  job_id: string;
  status: GenerationJobStatus;
  mode: 'ai' | 'script' | string;
  progress: number;
  stage: string;
  message_cn: string;
  created_at?: string;
  updated_at?: string;
  completed_at?: string | null;
  result?: GenerateScriptResponse & {
    preview_url?: string;
    preview?: PreviewResult;
    preview_path?: string;
  };
  error?: {
    code: string;
    message_cn: string;
  };
}

export interface SaveArtworkPatternResponse {
  success: boolean;
  pattern_url: string;
  pattern: PatternSheet;
  artwork: Artwork;
}

export interface ConsentResponse {
  success: boolean;
  consent_at: string;
}

export interface CDKRedeemResult {
  success: boolean;
  cdk_type?: CDKType;
  value?: number;
  expires_at?: string | null;
  message?: string;
}

export interface PaymentSku {
  sku: PaymentSkuId;
  sku_id: PaymentSkuId;
  category: PaymentSkuCategory;
  title: string;
  amount_cny: string;
  badge?: string | null;
  subtitle?: string | null;
  points?: number;
  days?: number;
  gift_points?: number;
}

export interface PaymentSkuCatalog {
  ai_generation_cost_points: number;
  items: PaymentSku[];
}

export interface Order {
  order_id: string;
  order_no?: string;
  user_id?: string;
  sku?: PaymentSkuId | 'single_9.9' | 'monthly_28' | 'custom_99' | string;
  amount_cny?: string | number;
  status: string;
  qr_code_url?: string | null;
  payment_provider?: string | null;
  is_mock_payment?: boolean;
  expires_at?: string | null;
  created_at?: string;
  updated_at?: string;
}

export interface OrderStatusResponse {
  status: string;
}
