import { defineStore } from 'pinia';

import { ApiError, generateAiPattern, generateScriptPattern, getGenerationStatus, submitConsent } from '../api';
import type { Artwork, GenerationJobResponse, GenerateScriptResponse, PatternSheet, SizePreset, StylePreset } from '../api/types';
import { hasToken } from '../auth/tokenStorage';
import { generatorSession,accountUser } from '../host';
import { persistGeneratorDraft } from '../draft';
import styleCartoonIcon from '../assets/brand/style-cartoon.png';
import stylePetIcon from '../assets/brand/style-pet.png';
import stylePortraitIcon from '../assets/brand/style-portrait.png';
import { useSWRCacheStore } from './swrCache';

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
let pendingGeneration:{owner:string;epoch:number;task:Promise<GenerateScriptResponse>}|null=null;
let generationEpoch=0;

interface GenerationState {
  sourceFile: File | null;
  owner: string;
  jobId: string;
  submitted: boolean;
  completedId: string;
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
    owner: '',jobId: '',submitted: false,completedId: '',
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
    persistDraft(){return persistGeneratorDraft(this.sourceFile?{file:this.sourceFile,size:this.selectedSize,mode:this.generationMode,style:this.selectedStyle,owner:this.owner||accountUser.value?.id||'guest',saved:Date.now(),jobId:this.jobId,submitted:this.submitted,completedId:this.completedId}:null);},
    ensureOwner(){
      const owner=accountUser.value?.id||'guest';
      if(this.owner&&this.owner!==owner&&this.owner!=='guest'){generationEpoch++;this.$reset();useSWRCacheStore().clearAll();void persistGeneratorDraft(null);}
      this.owner=owner;
    },
    resetOwner(){generationEpoch++;this.$reset();this.owner=accountUser.value?.id||'guest';useSWRCacheStore().clearAll();void persistGeneratorDraft(null);},
    clearSourceFile(){this.sourceFile=null;this.persistDraft();},
    setSourceFile(file: File) {
      this.ensureOwner();
      if(!this.isGenerating){this.jobId='';this.submitted=false;this.completedId='';}
      this.sourceFile = file;
      this.error = '';
      this.currentResult = null;
      this.currentArtwork = null;
      this.persistDraft();
    },
    setSize(size: ResultSizePreset) {
      this.selectedSize = size;
      this.persistDraft();
    },
    setGenerationMode(mode: GenerationMode) {
      this.generationMode = mode;
      this.persistDraft();
    },
    setStyle(style: GenerationStylePreset) {
      this.selectedStyle = style;
      this.persistDraft();
    },
    async generateCurrent(onJobUpdate?: GenerationJobUpdateHandler): Promise<GenerateScriptResponse> {
      this.ensureOwner();
      const owner=generatorSession(),epoch=generationEpoch;
      const current=()=>owner===generatorSession()&&epoch===generationEpoch;
      if(pendingGeneration?.owner===owner&&pendingGeneration.epoch===epoch)return pendingGeneration.task;
      if(this.currentResult&&this.completedId===this.currentResult.artwork_id)return this.currentResult;
      if(this.completedId){await this.loadArtwork(this.completedId);return this.currentResult!;}
      if (!this.sourceFile) throw new Error('请先选择一张照片。');
      if(this.submitted&&!this.jobId)throw new Error('提交结果尚未确认，请先到我的作品查看。确认没有生成后，可回到制作图纸重新提交。');
      this.isGenerating = true;this.error = '';
      const file=this.sourceFile,size=this.selectedSize,style=this.selectedStyle,mode=this.generationMode;
      const task=(async()=>{
        try {
          if (hasToken()&&!this.jobId) await submitConsent('sensitive');
          if(!current())throw new Error('登录账号已变化，请重新打开此页面。');
          let result:GenerateScriptResponse;
          if(this.jobId){result=await pollGenerationJob(this.jobId,onJobUpdate,current);}
          else {
            this.submitted=true;await this.persistDraft();
            if(mode==='ai'){
              const job=await generateAiPattern(file,size,style);
              if(!current())throw new Error('登录账号已变化，请重新打开此页面。');
              this.jobId=job.job_id;await this.persistDraft();onJobUpdate?.(job);
              result=await pollGenerationJob(job.job_id,onJobUpdate,current);
            }else result=await generateScriptPattern(file,size);
          }
          if(!current())throw new Error('登录账号已变化，请重新打开此页面。');
          this.currentResult=result;this.currentArtwork=null;this.completedId=result.artwork_id;
          this.jobId='';this.submitted=false;this.persistDraft();
          useSWRCacheStore().invalidateGallery();return result;
        }catch(error){
          if(current()){
            // A definite rejection can be retried. Unknown POST outcomes and running jobs must not be resubmitted on refresh.
            if(error instanceof ApiError&&error.status>=400&&error.status<500&&error.code!=='SESSION_CHANGED'){this.submitted=false;this.jobId='';this.persistDraft();}
            const friendly=normalizeGenerationError(error);this.error=friendly.message;throw friendly;
          }
          throw error;
        }finally{if(current())this.isGenerating=false;}
      })();
      const pending={owner,epoch,task};pendingGeneration=pending;
      try{return await task;}finally{if(pendingGeneration===pending)pendingGeneration=null;}
    },
    async loadArtwork(artworkId: string): Promise<Artwork> {
      this.error = '';
      const artwork = await useSWRCacheStore().fetchArtwork(artworkId);
      this.applyArtwork(artwork);
      return artwork;
    },
    applyArtwork(artwork: Artwork): void {
      useSWRCacheStore().setArtwork(artwork);
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
  const match = /^([1-9]\d{0,2})x([1-9]\d{0,2})$/.exec(value);
  if (!match) {
    return false;
  }
  const width = Number(match[1]);
  const height = Number(match[2]);
  return width >= 20 && width <= 200 && height >= 20 && height <= 200 && width/height>=0.5 && width/height<=2;
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
  onJobUpdate?: GenerationJobUpdateHandler,
  current:()=>boolean=()=>true
): Promise<GenerateScriptResponse> {
  const startedAt = Date.now();
  const timeoutMs = 12 * 60 * 1000;
  let delayMs = 1200;

  while (Date.now() - startedAt < timeoutMs) {
    await sleep(delayMs);
    if(!current())throw new Error('登录账号已变化，请重新打开此页面。');
    const job = await getGenerationStatus(jobId);
    onJobUpdate?.(job);

    if (job.status === 'succeeded') {
      if (job.result) {
        return job.result;
      }
      throw new Error('生成完成但没有拿到结果，请到作品集刷新查看。');
    }

    if (job.status === 'failed') {
      throw new ApiError(422,{error:'GENERATION_FAILED',message_cn:job.error?.message_cn || 'AI 生成暂时失败，请稍后重试或切换普通模式。'});
    }

    delayMs = Math.min(2600, delayMs + 220);
  }

  throw new Error('AI 生成仍在处理中，请稍后到我的作品查看，或继续查询此任务。');
}

function sleep(ms: number): Promise<void> {
  return new Promise((resolve) => window.setTimeout(resolve, ms));
}

function normalizeGenerationError(error: unknown): Error {
  if (error instanceof ApiError && (error.status === 402 || error.code === 'QUOTA_EXCEEDED')) {
    return error;
  }
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
