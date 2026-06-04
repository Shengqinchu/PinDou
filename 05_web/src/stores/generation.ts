import { defineStore } from 'pinia';

import { generateAiPattern, generateScriptPattern, getArtworkDetail, getGenerationStatus, submitConsent } from '../api';
import type { Artwork, GenerationJobResponse, GenerateScriptResponse, PatternSheet, SizePreset, StylePreset } from '../api/types';
import styleCartoonIcon from '../assets/brand/style-cartoon.png';
import stylePetIcon from '../assets/brand/style-pet.png';
import stylePortraitIcon from '../assets/brand/style-portrait.png';

export const RESULT_SIZE_OPTIONS = ['26x26', '52x52', '78x78', '104x104'] as const;
export type FixedResultSizeOption = (typeof RESULT_SIZE_OPTIONS)[number];
export type ResultSizePreset = SizePreset;
export const DEFAULT_GENERATION_SIZE: ResultSizePreset = '52x52';
export const GENERATION_MODE_OPTIONS = ['ai', 'script'] as const;
export type GenerationMode = (typeof GENERATION_MODE_OPTIONS)[number];
export const DEFAULT_GENERATION_MODE: GenerationMode = 'ai';
export const GENERATION_MODE_DETAILS: Record<GenerationMode, { label: string; hint: string; badge?: string }> = {
  ai: { label: 'AI 模式', hint: 'Q版后转图纸', badge: '推荐' },
  script: { label: '普通模式', hint: '秒出原图量化' }
};

export const SIZE_OPTION_DETAILS: Record<FixedResultSizeOption, { label: string }> = {
  '26x26': { label: '26' },
  '52x52': { label: '52' },
  '78x78': { label: '78' },
  '104x104': { label: '104' }
};

export const STYLE_OPTIONS = ['q_pet', 'q_portrait', 'q_couple'] as const;
export type GenerationStylePreset = Extract<StylePreset, (typeof STYLE_OPTIONS)[number]>;
export const DEFAULT_STYLE_PRESET: GenerationStylePreset = 'q_portrait';
export const STYLE_OPTION_DETAILS: Record<GenerationStylePreset, { label: string; hint: string; iconSrc: string }> = {
  q_pet: { label: '萌宠特化', hint: '宠物轮廓更清楚', iconSrc: stylePetIcon },
  q_portrait: { label: '人像特化', hint: '适合真人和实物照', iconSrc: stylePortraitIcon },
  q_couple: { label: '卡通特化', hint: '适合卡通原图', iconSrc: styleCartoonIcon }
};

export type GenerationJobUpdateHandler = (job: GenerationJobResponse) => void;

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
    async generateCurrent(onJobUpdate?: GenerationJobUpdateHandler): Promise<GenerateScriptResponse> {
      if (!this.sourceFile) {
        throw new Error('请先选择一张照片。');
      }

      this.isGenerating = true;
      this.error = '';
      try {
        await submitConsent('sensitive');
        const result = this.generationMode === 'ai'
          ? await this.generateAiWithPolling(onJobUpdate)
          : await generateScriptPattern(this.sourceFile, this.selectedSize as SizePreset);
        this.currentResult = result;
        this.currentArtwork = null;
        return result;
      } catch (error) {
        const friendly = normalizeGenerationError(error);
        this.error = friendly.message;
        throw friendly;
      } finally {
        this.isGenerating = false;
      }
    },
    async generateAiWithPolling(onJobUpdate?: GenerationJobUpdateHandler): Promise<GenerateScriptResponse> {
      if (!this.sourceFile) {
        throw new Error('请先选择一张照片。');
      }
      const submitted = await generateAiPattern(this.sourceFile, this.selectedSize as SizePreset, this.selectedStyle);
      onJobUpdate?.(submitted);
      return await pollGenerationJob(submitted.job_id, onJobUpdate);
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
  if (typeof value !== 'string') {
    return false;
  }
  const match = /^([1-9]\d{1,2})x([1-9]\d{1,2})$/.exec(value);
  if (!match) {
    return false;
  }
  const width = Number(match[1]);
  const height = Number(match[2]);
  return width >= 1 && width <= 200 && height >= 1 && height <= 200;
}

export function isGenerationStylePreset(value: unknown): value is GenerationStylePreset {
  return STYLE_OPTIONS.includes(value as GenerationStylePreset);
}

export function resultSizeLabel(size: ResultSizePreset | string): string {
  const [width, height] = String(size).split('x');
  if (!width || !height || width === height) {
    return width || String(size);
  }
  return `${width} × ${height}`;
}

export function extractPatternImageUrl(pattern: PatternSheet | null, fallback = ''): string {
  const metadata = pattern?.metadata || {};
  const labeled = metadataString(metadata, 'labeled_image_url');
  const thumbnail = metadataString(metadata, 'thumbnail_url');
  return labeled || pattern?.image_url || thumbnail || fallback;
}

async function pollGenerationJob(
  jobId: string,
  onJobUpdate?: GenerationJobUpdateHandler
): Promise<GenerateScriptResponse> {
  const startedAt = Date.now();
  const timeoutMs = 12 * 60 * 1000;
  let delayMs = 1200;

  while (Date.now() - startedAt < timeoutMs) {
    await sleep(delayMs);
    const job = await getGenerationStatus(jobId);
    onJobUpdate?.(job);

    if (job.status === 'succeeded') {
      if (job.result) {
        return job.result;
      }
      throw new Error('生成完成但没有拿到结果，请到作品集刷新查看。');
    }

    if (job.status === 'failed') {
      throw new Error(job.error?.message_cn || job.message_cn || 'AI 生成暂时失败，请稍后重试或切换普通模式。');
    }

    delayMs = Math.min(2600, delayMs + 220);
  }

  throw new Error('AI 生成仍在处理中，请稍后到作品集查看，或重新提交一次。');
}

function sleep(ms: number): Promise<void> {
  return new Promise((resolve) => window.setTimeout(resolve, ms));
}

function normalizeGenerationError(error: unknown): Error {
  const rawMessage = error instanceof Error ? error.message : String(error || '');
  const status = typeof (error as { status?: unknown })?.status === 'number'
    ? (error as { status: number }).status
    : 0;
  if (status === 524 || rawMessage.includes('524') || /timeout|timed out/i.test(rawMessage)) {
    return new Error('AI 生成时间较长，请稍后重试；也可以切换普通模式先生成。');
  }
  if (rawMessage) {
    return new Error(rawMessage);
  }
  return new Error('图纸生成失败，请重新试一次。');
}

function metadataString(metadata: Record<string, unknown>, key: string): string {
  const value = metadata[key];
  return typeof value === 'string' ? value : '';
}
