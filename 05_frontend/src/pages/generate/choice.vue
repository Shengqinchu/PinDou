<template>
  <MiniProgramLayout title="选择生成方式" backUrl="/pages/upload/upload" :scroll="true">
    <div class="choice">
      <p class="choice__hint">选一种生成方式</p>

      <div class="choice__size" aria-label="选择拼豆板尺寸">
        <button
          v-for="option in SIZE_OPTIONS"
          :key="option.value"
          class="choice__size-option"
          :class="{ 'choice__size-option--active': !isCustomSize && selectedPresetSize === option.value }"
          type="button"
          @click.stop="selectPreset(option.value)"
        >
          <span class="choice__size-title">{{ option.label }}</span>
          <span class="choice__size-sub">{{ option.sub }}</span>
        </button>
        <button
          class="choice__size-option"
          :class="{ 'choice__size-option--active': isCustomSize }"
          type="button"
          @click.stop="isCustomSize = true"
        >
          <span class="choice__size-title">自定义</span>
          <span class="choice__size-sub">{{ customSizeLabel }}</span>
        </button>
      </div>

      <div v-if="isCustomSize" class="choice__custom-size">
        <label class="choice__custom-field">
          <span>宽</span>
          <input v-model="customWidth" type="number" maxlength="3" inputmode="numeric" />
        </label>
        <span class="choice__custom-times">×</span>
        <label class="choice__custom-field">
          <span>高</span>
          <input v-model="customHeight" type="number" maxlength="3" inputmode="numeric" />
        </label>
        <p class="choice__custom-hint" :class="`choice__custom-hint--${customSizeHint.tone}`">
          {{ customSizeHint.text }}
        </p>
      </div>

      <!-- ===== Card A — Quick (free, basic quality) ===== -->
      <div class="card choice__card" @click="handleSelect('quick')">
        <div class="choice__head">
          <h2 class="choice__title">快速生成</h2>
          <span class="tag">基础质量</span>
        </div>

        <div class="choice__preview">
          <!-- 展示用户真实选择的图片 -->
          <div class="choice__thumb choice__thumb--original" aria-hidden="true">
            <image class="choice__thumb-real-img" :src="rawImage" mode="aspectFill" />
            <span class="choice__thumb-label">原图</span>
          </div>
          <span class="choice__arrow choice__arrow--basic" aria-hidden="true">
            <span class="choice__arrow-symbol">›</span>
          </span>
          <!-- 拼豆图纸样张 -->
          <div class="choice__thumb choice__thumb--basic" aria-hidden="true">
            <image class="choice__thumb-real-img" src="/static/assets/bead-bunny.svg" mode="aspectFit" />
          </div>
        </div>

        <ul class="choice__bullets" role="list">
          <li class="choice__bullet">
            <span class="choice__check choice__check--basic" aria-hidden="true">✓</span>
            直接量化原图，最快 5 秒出图
          </li>
          <li class="choice__bullet">
            <span class="choice__check choice__check--basic" aria-hidden="true">✓</span>
            保留照片本来的样子
          </li>
        </ul>

        <div class="choice__footer">
          <div class="choice__price">
            <span class="choice__price-major">免费</span>
            <span class="choice__price-minor">每日 3 次 · 看广告可加次</span>
          </div>
          <button class="btn btn--ghost btn--sm choice__action" @click.stop="handleSelect('quick')">选这个</button>
        </div>
      </div>

      <!-- ===== Card B — Premium (recommended, paid) ===== -->
      <div class="card card--recommended choice__card choice__card--recommended choice__card--last" @click="handleSelect('premium')">
        <span class="tag tag--recommended choice__badge" aria-label="推荐">
          <span class="choice__badge-star" aria-hidden="true">*</span>
          推荐
        </span>

        <div class="choice__head">
          <h2 class="choice__title">AI 精品生成</h2>
          <span class="tag tag--warm">限时体验</span>
        </div>

        <div class="choice__preview">
          <!-- 展示用户真实选择的图片 -->
          <div class="choice__thumb choice__thumb--original" aria-hidden="true">
            <image class="choice__thumb-real-img" :src="rawImage" mode="aspectFill" />
            <span class="choice__thumb-label">原图</span>
          </div>
          <span class="choice__arrow choice__arrow--premium" aria-hidden="true">
            <span class="choice__arrow-symbol">›</span>
          </span>
          <!-- Q版萌宠/自拍 SVG 样张 -->
          <div class="choice__thumb choice__thumb--premium" aria-hidden="true">
            <image class="choice__thumb-real-img" src="/static/assets/bead-cat.svg" mode="aspectFit" />
          </div>
        </div>

        <ul class="choice__bullets" role="list">
          <li class="choice__bullet">
            <span class="choice__check choice__check--premium" aria-hidden="true">✓</span>
            AI 重绘 Q 版形象，更可爱
          </li>
          <li class="choice__bullet">
            <span class="choice__check choice__check--premium" aria-hidden="true">✓</span>
            智能配色，限定调色板更精致
          </li>
          <li class="choice__bullet">
            <span class="choice__check choice__check--premium" aria-hidden="true">✓</span>
            推荐拼豆板尺寸，也可自定义格数
          </li>
        </ul>

        <div class="choice__footer">
          <div class="choice__price">
            <span class="choice__price-major text-grad">首次免费</span>
            <span class="choice__price-minor">
              下次 <s class="choice__price-strike">¥19.9</s>
              <strong class="choice__price-now">¥9.9 起</strong>
            </span>
          </div>
          <button class="btn btn--primary btn--sm choice__action" @click.stop="handleSelect('premium')">
            选这个
            <span class="choice__button-arrow" aria-hidden="true">›</span>
          </button>
        </div>
      </div>

      <div class="help-link choice__help" @click="handleHelp">
        <span class="choice__help-icon" aria-hidden="true">?</span>
        <span class="help-link__label">这两种有什么区别？</span>
      </div>

      <div v-if="showConfirmSheet" class="choice__confirm" @click.self="closeConfirm">
        <section class="choice__confirm-sheet" role="dialog" aria-label="确认生成">
          <div class="choice__confirm-handle" aria-hidden="true"></div>
          <h2 class="choice__confirm-title">确认生成？</h2>
          <p class="choice__confirm-summary">{{ confirmSummary }}</p>

          <div class="choice__confirm-stats">
            <div class="choice__confirm-stat">
              <span class="choice__confirm-num">{{ estimatedBeads }}</span>
              <span class="choice__confirm-label">预计颗数</span>
            </div>
            <div class="choice__confirm-stat">
              <span class="choice__confirm-num">{{ estimatedColors }}</span>
              <span class="choice__confirm-label">预计色号</span>
            </div>
            <div class="choice__confirm-stat">
              <span class="choice__confirm-num">{{ estimatedDuration }}</span>
              <span class="choice__confirm-label">预计时长</span>
            </div>
          </div>

          <div class="choice__consume-card">
            <span class="choice__consume-label">消耗说明</span>
            <span class="choice__consume-text">{{ consumeText }}</span>
          </div>

          <button
            v-if="pendingTier === 'premium' && !isPremiumUser"
            type="button"
            class="choice__cdk-link"
            @click="goCdk"
          >
            我有 CDK 兑换码
          </button>

          <div class="choice__confirm-actions">
            <button type="button" class="btn btn--secondary btn--md choice__confirm-cancel" @click="closeConfirm">
              取消
            </button>
            <button type="button" class="btn btn--primary btn--md choice__confirm-ok" @click="confirmGeneration">
              ✓ 确认生成
            </button>
          </div>
        </section>
      </div>
    </div>
  </MiniProgramLayout>
</template>

<script setup lang="ts">
import { computed, ref } from 'vue';
import { onLoad } from '@dcloudio/uni-app';
import MiniProgramLayout from '../../components/MiniProgramLayout.vue';
import { SizePreset } from '../../api';
import { useUserStore } from '../../store/user';

const userStore = useUserStore();
const rawImage = ref('');
const stylePreset = ref('cartoon_fallback');
const selectedPresetSize = ref<SizePreset>('26x26');
const isCustomSize = ref(false);
const customWidth = ref('30');
const customHeight = ref('30');
const showConfirmSheet = ref(false);
const pendingTier = ref<'quick' | 'premium' | null>(null);
const SKIP_CONFIRM_FOR_PREMIUM = true;
const SIZE_OPTIONS: Array<{ value: SizePreset; label: string; sub: string }> = [
  { value: '26x26', label: '单板', sub: '26格' },
  { value: '52x52', label: '双板', sub: '52格' },
  { value: '78x78', label: '三板', sub: '78格' },
  { value: '104x104', label: '四板', sub: '104格' }
];

const selectedSize = computed<SizePreset>(() => {
  if (!isCustomSize.value) return selectedPresetSize.value;
  return `${Number(customWidth.value || 0)}x${Number(customHeight.value || 0)}` as SizePreset;
});

const sizeNumbers = computed(() => parseSize(selectedSize.value));

const isPremiumUser = computed(() => userStore.isMonthlyMember || userStore.credits >= 9999);

const selectedSizeLabel = computed(() => {
  const [width, height] = sizeNumbers.value;
  const presetLabel: Record<string, string> = {
    '26x26': '单板',
    '52x52': '双板',
    '78x78': '三板',
    '104x104': '四板'
  };
  return `${width}×${height} ${presetLabel[selectedSize.value] || '自定义'}`;
});

const confirmSummary = computed(() => {
  const prefix = pendingTier.value === 'premium' ? '✨ AI 精品' : '⚡ 快速生成';
  return `${prefix} · ${selectedSizeLabel.value}`;
});

const estimatedBeads = computed(() => {
  const [width, height] = sizeNumbers.value;
  return Math.round(width * height * (pendingTier.value === 'premium' ? 0.72 : 0.82));
});

const estimatedColors = computed(() => pendingTier.value === 'premium' ? '5-8' : '8-16');
const estimatedDuration = computed(() => pendingTier.value === 'premium' ? '30-60秒' : '5-10秒');

const consumeText = computed(() => {
  const freeCredits = userStore.userInfo?.free_credits_remaining || 0;
  const paidCredits = userStore.userInfo?.paid_credits || 0;
  const totalCredits = freeCredits + paidCredits;
  if (isPremiumUser.value) return '月卡 / 测试额度已生效，本次不额外提示消耗。';
  if (pendingTier.value === 'quick') {
    return freeCredits > 0 ? `今日剩 ${Math.min(freeCredits, 3)}/3 次` : '今日免费次数已用完，需要看 1 次广告续次';
  }
  if (totalCredits > 0) return `可用 AI 额度 ${totalCredits} 次`;
  return 'AI 首次体验免费；已体验后可选 9.9 元 / 月卡 / CDK 兑换';
});

const customSizeLabel = computed(() => {
  const width = Number(customWidth.value || 0);
  const height = Number(customHeight.value || 0);
  return width && height ? `${width}×${height}` : '输入';
});

const customSizeHint = computed(() => {
  const validation = validateSize(Number(customWidth.value), Number(customHeight.value));
  if (!validation.valid) {
    return { tone: 'bad', text: validation.message };
  }
  const width = Number(customWidth.value);
  const height = Number(customHeight.value);
  if (width % 26 === 0 && height % 26 === 0) {
    return { tone: 'good', text: `对齐 26 格拼豆板：${width / 26}×${height / 26} 块板` };
  }
  const boardsW = Math.ceil(width / 26);
  const boardsH = Math.ceil(height / 26);
  return { tone: 'warn', text: `不对齐拼豆板：约需 ${boardsW}×${boardsH} 块板，边缘需裁切` };
});

onLoad((options: any) => {
  if (options.image) {
    rawImage.value = decodeURIComponent(options.image);
  }
  if (options.style) {
    stylePreset.value = options.style;
  }
});

const handleSelect = (tier: 'quick' | 'premium') => {
  if (!ensureValidSize()) return;
  if (SKIP_CONFIRM_FOR_PREMIUM && isPremiumUser.value) {
    startGeneration(tier);
    return;
  }
  pendingTier.value = tier;
  showConfirmSheet.value = true;
};

const confirmGeneration = () => {
  if (!pendingTier.value) return;
  const tier = pendingTier.value;
  closeConfirm();
  startGeneration(tier);
};

const closeConfirm = () => {
  showConfirmSheet.value = false;
  pendingTier.value = null;
};

const startGeneration = (tier: 'quick' | 'premium') => {
  uni.navigateTo({
    url: `/pages/preview/loading?tier=${tier}&style=${stylePreset.value}&size=${selectedSize.value}&image=${encodeURIComponent(rawImage.value)}`
  });
};

const ensureValidSize = () => {
  if (!isCustomSize.value) return true;
  const validation = validateSize(Number(customWidth.value), Number(customHeight.value));
  if (!validation.valid) {
    uni.showToast({ title: validation.message, icon: 'none' });
    return false;
  }
  return true;
};

const selectPreset = (value: SizePreset) => {
  selectedPresetSize.value = value;
  isCustomSize.value = false;
};

const validateSize = (width: number, height: number): { valid: boolean; message: string } => {
  if (!Number.isInteger(width) || !Number.isInteger(height)) {
    return { valid: false, message: '尺寸必须是整数' };
  }
  if (width < 20 || height < 20) {
    return { valid: false, message: '最小 20×20 格' };
  }
  if (width > 200 || height > 200) {
    return { valid: false, message: '最大 200×200 格' };
  }
  const ratio = width / height;
  if (ratio < 0.5 || ratio > 2) {
    return { valid: false, message: '长宽比需在 0.5-2 之间' };
  }
  return { valid: true, message: '' };
};

const parseSize = (size: SizePreset): [number, number] => {
  const match = String(size).match(/^(\d+)x(\d+)$/);
  if (!match) return [26, 26];
  return [Number(match[1]), Number(match[2])];
};

const goCdk = () => {
  uni.navigateTo({ url: '/pages/cdk/redeem' });
};

const handleHelp = () => {
  uni.showModal({
    title: '区别说明',
    content: '【快速生成】直接根据您的照片色彩，利用智能匹配算法在5秒内导出制作色卡与简易网格。\n\n【AI精品生成】先利用AI重塑具有Q版人像/宠物特征的精致插画，去除杂乱噪点，再输出拥有柔和色调的高清级拼豆图纸，成品效果明显更可爱。',
    showCancel: false,
    confirmText: '我知道了',
    confirmColor: '#FF6B9D'
  });
};
</script>

<style scoped lang="scss">
.choice {
  padding: 8px 20px 24px;
}

.choice__hint {
  text-align: center;
  font-size: 12px;
  color: var(--pd-fg-2);
  margin: 0 0 16px;
}

.choice__size {
  display: grid;
  grid-template-columns: repeat(5, minmax(0, 1fr));
  gap: 8px;
  margin: 0 0 16px;
}

.choice__size-option {
  min-width: 0;
  border: 1px solid var(--pd-divider);
  border-radius: 8px;
  padding: 8px 4px 7px;
  background: rgba(255, 255, 255, 0.78);
  color: var(--pd-fg-2);
  text-align: center;
  line-height: 1.15;
}

.choice__size-option--active {
  border-color: var(--pd-pink);
  background: #FFE4EE;
  color: var(--pd-pink-deep);
}

.choice__size-title {
  display: block;
  font-size: 12px;
  font-weight: 800;
}

.choice__size-sub {
  display: block;
  margin-top: 3px;
  font-size: 10px;
  font-weight: 600;
}

.choice__custom-size {
  display: grid;
  grid-template-columns: 1fr auto 1fr;
  align-items: center;
  gap: 8px;
  margin: -6px 0 16px;
  padding: 12px;
  border-radius: 8px;
  background: rgba(255, 255, 255, 0.74);
  border: 1px solid var(--pd-divider);
}

.choice__custom-field {
  display: flex;
  align-items: center;
  gap: 6px;
  min-width: 0;
  font-size: 12px;
  color: var(--pd-fg-2);
}

.choice__custom-field input {
  width: 100%;
  height: 34px;
  padding: 0 8px;
  border: 1px solid var(--pd-divider);
  border-radius: 8px;
  background: #fff;
  color: var(--pd-fg-1);
  font-size: 16px;
  font-weight: 700;
  text-align: center;
}

.choice__custom-times {
  color: var(--pd-fg-3);
  font-weight: 800;
}

.choice__custom-hint {
  grid-column: 1 / -1;
  margin: 2px 0 0;
  font-size: 11px;
  line-height: 1.45;
}

.choice__custom-hint--good { color: #2E8B57; }
.choice__custom-hint--warn { color: #B7791F; }
.choice__custom-hint--bad { color: var(--pd-danger); }

/* ===== Card layout (used by both quick + premium) ===== */
.choice__card {
  display: block;
  padding: 18px 18px 16px;
  text-decoration: none;
  color: var(--pd-fg-1);
  margin-bottom: 16px;
  position: relative;
  transition: transform 180ms var(--pd-ease-out);
  cursor: pointer;
  
  &:active { 
    transform: scale(0.99); 
  }
}
.choice__card--last { 
  margin-bottom: 0; 
}

.choice__card--recommended { 
  padding-top: 22px; 
}

/* recommended badge — peeks above the top edge */
.choice__badge {
  position: absolute;
  top: -10px;
  right: 16px;
  z-index: 2;
}
.choice__badge-star {
  margin-right: 2px;
  font-size: 11px;
  line-height: 1;
}

.choice__head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 14px;
}

.choice__title {
  font-size: 17px;
  font-weight: 700;
  margin: 0;
}

/* ===== Preview row (original → bead-pattern) ===== */
.choice__preview {
  display: flex;
  align-items: center;
  gap: 12px;
  margin-bottom: 14px;
}

.choice__thumb {
  width: 88px;
  height: 88px;
  border-radius: var(--pd-r-img);
  overflow: hidden;
  flex-shrink: 0;
  display: flex;
  align-items: center;
  justify-content: center;
  position: relative;
}

.choice__thumb-real-img {
  width: 100%;
  height: 100%;
}

.choice__thumb--original {
  background:
    radial-gradient(circle at 40% 35%, #FFCDA6 0%, #FF8E53 60%, transparent 90%),
    radial-gradient(circle at 50% 50%, #FFE4EE 0%, #FFCDA6 60%, #FFB088 100%);
}

.choice__thumb-label {
  position: absolute;
  top: 6px;
  left: 6px;
  padding: 2px 6px;
  border-radius: 999px;
  background: rgba(255, 255, 255, 0.85);
  font-size: 9px;
  font-weight: 600;
  color: var(--pd-fg-2);
  z-index: 1;
}

.choice__thumb--basic { 
  background: #F4EFE9; 
}

.choice__thumb--premium {
  background: linear-gradient(135deg, #FFF1E8 0%, #FFE4EE 100%);
}

.choice__arrow {
  width: 22px;
  height: 22px;
  border-radius: 999px;
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
  color: #fff;
}

.choice__arrow--basic { 
  background: #E8E1D8; 
}

.choice__arrow--premium { 
  background: var(--pd-gradient-warm); 
}
.choice__arrow-symbol {
  font-size: 14px;
  font-weight: 800;
  line-height: 1;
}

/* ===== Bullets ===== */
.choice__bullets {
  list-style: none;
  margin: 0;
  padding: 0;
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.choice__bullet {
  display: flex;
  align-items: flex-start;
  gap: 8px;
  font-size: 12.5px;
  line-height: 1.5;
  color: var(--pd-fg-1);
}

.choice__check {
  width: 14px;
  height: 14px;
  flex-shrink: 0;
  margin-top: 3px;
  border-radius: 999px;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  font-size: 10px;
  font-weight: 800;
}
.choice__check--basic {
  background: #F4EFE9;
  color: var(--pd-fg-2);
}
.choice__check--premium {
  background: #FFE4EE;
  color: var(--pd-pink);
}

/* ===== Footer (price + CTA) ===== */
.choice__footer {
  display: flex;
  align-items: flex-end;
  justify-content: space-between;
  margin-top: 14px;
  padding-top: 12px;
  border-top: 1px dashed var(--pd-divider);
}

.choice__price-major {
  display: block;
  font-size: 20px;
  font-weight: 800;
  color: var(--pd-fg-1);
  line-height: 1;
}

.choice__price-minor {
  display: block;
  font-size: 11px;
  color: var(--pd-fg-2);
  margin-top: 4px;
}

.choice__price-strike { 
  color: var(--pd-fg-3); 
}

.choice__price-now {
  color: var(--pd-pink-deep);
  font-weight: 700;
}
.choice__button-arrow {
  margin-left: 2px;
  font-size: 14px;
  font-weight: 800;
}

/* ===== Help link ===== */
.choice__help {
  display: flex;
  align-items: center;
  gap: 6px;
  justify-content: center;
  margin-top: 20px;
  cursor: pointer;
}
.choice__help-icon {
  width: 16px;
  height: 16px;
  border-radius: 999px;
  border: 1.5px solid currentColor;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  font-size: 11px;
  font-weight: 700;
}

.choice__confirm {
  position: fixed;
  top: 0;
  right: 0;
  bottom: 0;
  left: 0;
  z-index: 998;
  background: rgba(45, 45, 45, 0.38);
  backdrop-filter: blur(4px);
}

.choice__confirm-sheet {
  position: fixed;
  right: 0;
  bottom: 0;
  left: 0;
  z-index: 999;
  margin: 0;
  padding: 10px 20px calc(22px + env(safe-area-inset-bottom));
  border-radius: 24px 24px 0 0;
  background: var(--pd-card);
  box-shadow: 0 -12px 40px rgba(45, 45, 45, 0.18);
  box-sizing: border-box;
  animation: choice-confirm-up 220ms var(--pd-ease-soft);
}

.choice__confirm-handle {
  width: 36px;
  height: 4px;
  margin: 2px auto 14px;
  border-radius: 999px;
  background: var(--pd-divider);
}

.choice__confirm-title {
  margin: 0 0 6px;
  text-align: center;
  font-family: var(--pd-font-display);
  font-size: 20px;
  font-weight: 800;
  color: var(--pd-fg-1);
}

.choice__confirm-summary {
  margin: 0 0 14px;
  text-align: center;
  font-size: 13px;
  color: var(--pd-fg-2);
}

.choice__confirm-stats {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 8px;
  margin-bottom: 12px;
}

.choice__confirm-stat {
  min-width: 0;
  padding: 12px 6px;
  border-radius: 12px;
  background: var(--pd-bg-warm);
  text-align: center;
}

.choice__confirm-num {
  display: block;
  font-family: var(--pd-font-display);
  font-size: 18px;
  font-weight: 800;
  color: var(--pd-fg-1);
  white-space: nowrap;
}

.choice__confirm-label {
  display: block;
  margin-top: 4px;
  font-size: 10px;
  color: var(--pd-fg-2);
  white-space: nowrap;
}

.choice__consume-card {
  display: flex;
  flex-direction: column;
  gap: 4px;
  padding: 12px 14px;
  margin-bottom: 10px;
  border-radius: 14px;
  background: #FFF7F2;
  border: 1px solid rgba(255, 176, 136, 0.32);
}

.choice__consume-label {
  font-size: 11px;
  color: var(--pd-fg-3);
}

.choice__consume-text {
  font-size: 13px;
  font-weight: 700;
  color: var(--pd-fg-1);
  line-height: 1.45;
}

.choice__cdk-link {
  display: block;
  width: fit-content;
  margin: 0 auto 12px;
  padding: 4px 10px;
  border: 0;
  background: transparent;
  color: var(--pd-pink-deep);
  font-size: 13px;
  font-weight: 700;
}

.choice__confirm-actions {
  display: grid;
  grid-template-columns: 0.78fr 1.22fr;
  gap: 10px;
}

.choice__confirm-cancel,
.choice__confirm-ok {
  min-width: 0;
}

@keyframes choice-confirm-up {
  from { transform: translateY(100%); }
  to { transform: translateY(0); }
}

@media (max-width: 360px) {
  .choice__confirm-sheet {
    padding-left: 16px;
    padding-right: 16px;
  }

  .choice__confirm-num {
    font-size: 16px;
  }
}
</style>
