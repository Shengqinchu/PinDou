import { defineStore } from 'pinia';
import { api, Artwork, ColorRef, SizePreset, StylePreset, PatternSheet, PreviewResult } from '../api';

const CURRENT_PATTERN_KEY = 'pd_current_pattern';
const CURRENT_PREVIEW_KEY = 'pd_current_preview';
const COMPACT_PATTERN_VERSION = 1;

type CompactPatternSnapshot = {
  __compact_pattern__: number;
  grid_codes: (string | null)[][];
  color_counts: Record<string, number>;
  bead_total: number;
  palette_used: ColorRef[];
  estimated_cost_cny: number;
  suggested_buffer_pct: number;
  brand: string;
  bead_diameter_mm: number;
  metadata?: Record<string, any>;
  image_url?: string;
};

const fallbackColor = (code: string, snapshot: CompactPatternSnapshot): ColorRef => ({
  brand: snapshot.brand || 'MARD',
  code,
  name_cn: '',
  name_en: null,
  hex: '#D9D9D9',
  rgb: [217, 217, 217],
  bead_diameter_mm: Number(snapshot.bead_diameter_mm || 5)
});

const compactPatternForStorage = (sheet: PatternSheet): CompactPatternSnapshot => ({
  __compact_pattern__: COMPACT_PATTERN_VERSION,
  grid_codes: sheet.grid.map(row => row.map(color => color?.code || null)),
  color_counts: sheet.color_counts || {},
  bead_total: sheet.bead_total || 0,
  palette_used: sheet.palette_used || [],
  estimated_cost_cny: sheet.estimated_cost_cny || 0,
  suggested_buffer_pct: sheet.suggested_buffer_pct || 10,
  brand: sheet.brand || 'MARD',
  bead_diameter_mm: Number(sheet.bead_diameter_mm || 5),
  metadata: sheet.metadata || {},
  image_url: sheet.image_url
});

const expandCompactPattern = (snapshot: CompactPatternSnapshot): PatternSheet => {
  const paletteByCode = new Map((snapshot.palette_used || []).map(color => [color.code, color]));
  const grid = (snapshot.grid_codes || []).map(row =>
    row.map(code => {
      if (!code) return null;
      return paletteByCode.get(code) || fallbackColor(code, snapshot);
    })
  );

  return {
    grid,
    color_counts: snapshot.color_counts || {},
    bead_total: snapshot.bead_total || 0,
    coords: [],
    no_bead_mask: grid.map(row => row.map(color => !color)),
    palette_used: snapshot.palette_used || [],
    estimated_cost_cny: snapshot.estimated_cost_cny || 0,
    suggested_buffer_pct: snapshot.suggested_buffer_pct || 10,
    brand: snapshot.brand || 'MARD',
    bead_diameter_mm: Number(snapshot.bead_diameter_mm || 5),
    metadata: snapshot.metadata || {},
    image_url: snapshot.image_url
  };
};

export const readStoredPattern = (): PatternSheet | null => {
  const stored = uni.getStorageSync(CURRENT_PATTERN_KEY);
  if (!stored) return null;
  if (stored.__compact_pattern__ === COMPACT_PATTERN_VERSION) {
    return expandCompactPattern(stored as CompactPatternSnapshot);
  }
  return stored as PatternSheet;
};

const savePatternSnapshot = (sheet: PatternSheet) => {
  try {
    uni.setStorageSync(CURRENT_PATTERN_KEY, compactPatternForStorage(sheet));
  } catch (error) {
    console.warn('图纸快照缓存失败，已跳过本地兜底缓存:', error);
    try {
      uni.removeStorageSync(CURRENT_PATTERN_KEY);
    } catch (_removeError) {
      // Ignore cleanup failures; Pinia still holds the current in-memory sheet.
    }
  }
};

export const useArtworkStore = defineStore('artwork', {
  state: () => ({
    artworks: [] as Artwork[],
    currentArtwork: null as Artwork | null,
    currentPreview: null as PreviewResult | null,
    currentPattern: null as PatternSheet | null,
  }),
  actions: {
    async fetchArtworks() {
      try {
        const list = await api.getArtworks();
        this.artworks = list;
        return list;
      } catch (error) {
        console.error('Fetch artworks error:', error);
        throw error;
      }
    },
    async fetchArtworkDetail(id: string) {
      try {
        const detail = await api.getArtworkDetail(id);
        this.currentArtwork = detail;
        this.currentPattern = detail.pattern_data;
        savePatternSnapshot(detail.pattern_data);
        return detail;
      } catch (error) {
        console.error('Fetch artwork detail error:', error);
        throw error;
      }
    },
    async generateAIPreview(filePath: string, style: StylePreset, size: SizePreset) {
      try {
        const preview = await api.generatePreview(filePath, style, size);
        this.currentPreview = preview;
        uni.setStorageSync(CURRENT_PREVIEW_KEY, preview);
        return preview;
      } catch (error) {
        console.error('Generate AI preview error:', error);
        throw error;
      }
    },
    async buildPatternSheet(params: {
      size: SizePreset;
      preview_id?: string;
      rawImageFilePath?: string;
      mode: 'auto' | 'script' | 'ai';
    }) {
      try {
        const sheet = await api.buildPattern(params);
        this.currentPattern = sheet;
        savePatternSnapshot(sheet);
        return sheet;
      } catch (error) {
        console.error('Build pattern sheet error:', error);
        throw error;
      }
    },
    async deleteArtwork(id: string) {
      try {
        const res = await api.deleteArtwork(id);
        if (res.success) {
          this.artworks = this.artworks.filter(art => art.artwork_id !== id);
        }
        return res;
      } catch (error) {
        console.error('Delete artwork error:', error);
        throw error;
      }
    }
  }
});
