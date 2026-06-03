import { defineStore } from 'pinia';

import { generateScriptPattern, getArtworkDetail, submitConsent } from '../api';
import type { Artwork, GenerateScriptResponse, PatternSheet, SizePreset } from '../api/types';

export const RESULT_SIZE_OPTIONS = ['26x26', '52x52', '78x78', '104x104'] as const;
export type ResultSizePreset = (typeof RESULT_SIZE_OPTIONS)[number];
export const DEFAULT_GENERATION_SIZE: ResultSizePreset = '52x52';

export const SIZE_OPTION_DETAILS: Record<ResultSizePreset, { label: string; hint: string }> = {
  '26x26': { label: '26', hint: '简易·豆少' },
  '52x52': { label: '52', hint: '推荐' },
  '78x78': { label: '78', hint: '三板' },
  '104x104': { label: '104', hint: '精细·豆多' }
};

interface GenerationState {
  sourceFile: File | null;
  selectedSize: ResultSizePreset;
  currentResult: GenerateScriptResponse | null;
  currentArtwork: Artwork | null;
  isGenerating: boolean;
  error: string;
}

export const useGenerationStore = defineStore('generation', {
  state: (): GenerationState => ({
    sourceFile: null,
    selectedSize: DEFAULT_GENERATION_SIZE,
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
    async generateCurrent(): Promise<GenerateScriptResponse> {
      if (!this.sourceFile) {
        throw new Error('请先选择一张照片。');
      }

      this.isGenerating = true;
      this.error = '';
      try {
        await submitConsent('sensitive');
        const result = await generateScriptPattern(this.sourceFile, this.selectedSize as SizePreset);
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
    }
  }
});

export function isResultSizePreset(value: unknown): value is ResultSizePreset {
  return RESULT_SIZE_OPTIONS.includes(value as ResultSizePreset);
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
