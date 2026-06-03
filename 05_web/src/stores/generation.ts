import { defineStore } from 'pinia';

import { generateAiPattern, generateScriptPattern, getArtworkDetail, submitConsent } from '../api';
import type { Artwork, GenerateScriptResponse, PatternSheet, SizePreset, StylePreset } from '../api/types';

export const RESULT_SIZE_OPTIONS = ['26x26', '52x52', '78x78', '104x104'] as const;
export type ResultSizePreset = (typeof RESULT_SIZE_OPTIONS)[number];
export const DEFAULT_GENERATION_SIZE: ResultSizePreset = '52x52';
export const GENERATION_MODE_OPTIONS = ['ai', 'script'] as const;
export type GenerationMode = (typeof GENERATION_MODE_OPTIONS)[number];
export const DEFAULT_GENERATION_MODE: GenerationMode = 'ai';
export const GENERATION_MODE_DETAILS: Record<GenerationMode, { label: string; hint: string; badge?: string }> = {
  ai: { label: 'AI 精品', hint: 'Q版后转图纸', badge: '推荐' },
  script: { label: '脚本快速', hint: '秒出原图量化' }
};

export const SIZE_OPTION_DETAILS: Record<ResultSizePreset, { label: string; hint: string }> = {
  '26x26': { label: '26', hint: '简易·豆少' },
  '52x52': { label: '52', hint: '推荐' },
  '78x78': { label: '78', hint: '三板' },
  '104x104': { label: '104', hint: '精细·豆多' }
};

export const STYLE_OPTIONS = ['q_pet', 'q_couple', 'q_portrait'] as const;
export type GenerationStylePreset = Extract<StylePreset, (typeof STYLE_OPTIONS)[number]>;
export const DEFAULT_STYLE_PRESET: GenerationStylePreset = 'q_portrait';
export const STYLE_OPTION_DETAILS: Record<GenerationStylePreset, { label: string; hint: string; icon: string }> = {
  q_pet: { label: '宠萌宠', hint: '耳朵花纹更清楚', icon: '宠' },
  q_couple: { label: '心情侣', hint: '保留左右关系', icon: '心' },
  q_portrait: { label: '拍自拍', hint: '适合头像半身照', icon: '拍' }
};

interface GenerationState {
  sourceFile: File | null;
  selectedSize: ResultSizePreset;
  generationMode: GenerationMode;
  selectedStyle: GenerationStylePreset;
  currentResult: GenerateScriptResponse | null;
  currentArtwork: Artwork | null;
  isGenerating: boolean;
  error: string;
}

export const useGenerationStore = defineStore('generation', {
  state: (): GenerationState => ({
    sourceFile: null,
    selectedSize: DEFAULT_GENERATION_SIZE,
    generationMode: DEFAULT_GENERATION_MODE,
    selectedStyle: DEFAULT_STYLE_PRESET,
    currentResult: null,
    currentArtwork: null,
    isGenerating: false,
    error: ''
  }),
  getters: {
    currentArtworkId: (state) => state.currentResult?.artwork_id || state.currentArtwork?.artwork_id || '',
    currentPattern: (state): PatternSheet | null => state.currentResult?.pattern || state.currentArtwork?.pattern_data || null,
    patternImageUrl: (state): string => {
      const pattern = state.currentResult?.pattern || state.currentArtwork?.pattern_data || null;
      return extractPatternImageUrl(pattern, state.currentResult?.pattern_url || state.currentArtwork?.preview_url || '');
    }
  },
  actions: {
    setSourceFile(file: File) {
      this.sourceFile = file;
      this.error = '';
      this.currentResult = null;
      this.currentArtwork = null;
    },
    setSize(size: ResultSizePreset) {
      this.selectedSize = size;
    },
    setGenerationMode(mode: GenerationMode) {
      this.generationMode = mode;
    },
    setStyle(style: GenerationStylePreset) {
      this.selectedStyle = style;
    },
    async generateCurrent(): Promise<GenerateScriptResponse> {
      if (!this.sourceFile) {
        throw new Error('请先选择一张照片。');
      }

      this.isGenerating = true;
      this.error = '';
      try {
        await submitConsent('sensitive');
        const result = this.generationMode === 'ai'
          ? await generateAiPattern(this.sourceFile, this.selectedSize as SizePreset, this.selectedStyle)
          : await generateScriptPattern(this.sourceFile, this.selectedSize as SizePreset);
        this.currentResult = result;
        this.currentArtwork = null;
        return result;
      } catch (error) {
        this.error = error instanceof Error ? error.message : '图纸生成失败，请重新试一次。';
        throw error;
      } finally {
        this.isGenerating = false;
      }
    },
    async loadArtwork(artworkId: string): Promise<Artwork> {
      this.error = '';
      const artwork = await getArtworkDetail(artworkId);
      this.applyArtwork(artwork);
      return artwork;
    },
    applyArtwork(artwork: Artwork): void {
      this.currentArtwork = artwork;
      this.currentResult = {
        artwork_id: artwork.artwork_id,
        pattern_url: extractPatternImageUrl(artwork.pattern_data, artwork.preview_url || artwork.thumbnail_url || ''),
        pattern: artwork.pattern_data
      };
      if (isResultSizePreset(artwork.size_preset)) {
        this.selectedSize = artwork.size_preset;
      }
      if (isGenerationStylePreset(artwork.style_preset)) {
        this.selectedStyle = artwork.style_preset;
        this.generationMode = 'ai';
      } else if (artwork.style_preset === 'cartoon_fallback') {
        this.generationMode = 'script';
      }
    }
  }
});

export function isResultSizePreset(value: unknown): value is ResultSizePreset {
  return RESULT_SIZE_OPTIONS.includes(value as ResultSizePreset);
}

export function isGenerationStylePreset(value: unknown): value is GenerationStylePreset {
  return STYLE_OPTIONS.includes(value as GenerationStylePreset);
}

export function extractPatternImageUrl(pattern: PatternSheet | null, fallback = ''): string {
  const metadata = pattern?.metadata || {};
  const labeled = metadataString(metadata, 'labeled_image_url');
  const thumbnail = metadataString(metadata, 'thumbnail_url');
  return labeled || pattern?.image_url || thumbnail || fallback;
}

function metadataString(metadata: Record<string, unknown>, key: string): string {
  const value = metadata[key];
  return typeof value === 'string' ? value : '';
}
