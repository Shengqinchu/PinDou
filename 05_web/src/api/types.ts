export type StylePreset = 'q_portrait' | 'q_pet' | 'q_couple' | 'cartoon_fallback';
export type SizePreset = '26x26' | '52x52' | '78x78' | '104x104' | `${number}x${number}`;
export type CDKType = 'single_use' | 'monthly_card' | 'credit_pack_5' | 'credit_pack_10';

export interface User {
  user_id: string;
  openid?: string | null;
  email?: string | null;
  nickname?: string;
  avatar?: string;
  created_at?: string;
  free_credits_remaining?: number;
  paid_credits?: number;
  monthly_card_expires_at?: string | null;
  privacy_consent_at?: string | null;
  sensitive_consent_at?: string | null;
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
  coords?: Array<{ row: number; col: number; code: string | null }>;
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
  preview_path?: string | null;
  pattern_data: PatternSheet;
  style_preset: StylePreset | string;
  size_preset: SizePreset | string;
  is_paid_unlocked?: boolean;
  created_at?: string;
  updated_at?: string;
}

export interface CDKRedeemResult {
  success: boolean;
  cdk_type?: CDKType;
  value?: number;
  expires_at?: string | null;
  message?: string;
}

export interface Order {
  order_id: string;
  order_no?: string;
  user_id?: string;
  sku?: 'single_9.9' | 'monthly_28' | 'custom_99' | string;
  amount_cny?: string | number;
  status: string;
  qr_code_url?: string | null;
  payment_provider?: string | null;
  is_mock_payment?: boolean;
  expires_at?: string | null;
  created_at?: string;
  updated_at?: string;
}

