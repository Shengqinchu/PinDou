<template>
  <MiniProgramLayout title="选择生成方式" backUrl="/pages/upload/upload" :scroll="true">
    <div class="choice">
      <p class="choice__hint">选一种生成方式</p>

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
            <span class="choice__arrow-symbol">&gt;</span>
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
          <button class="btn btn--ghost btn--sm choice__action">选这个</button>
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
            <span class="choice__arrow-symbol">&gt;</span>
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
            可调网格大小（60x80/80x100/100x120）
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
          <button class="btn btn--primary btn--sm choice__action">
            选这个
            <span class="choice__button-arrow" aria-hidden="true">&gt;</span>
          </button>
        </div>
      </div>

      <div class="help-link choice__help" @click="handleHelp">
        <span class="choice__help-icon" aria-hidden="true">?</span>
        <span class="help-link__label">这两种有什么区别？</span>
      </div>
    </div>
  </MiniProgramLayout>
</template>

<script setup lang="ts">
import { ref } from 'vue';
import { onLoad } from '@dcloudio/uni-app';
import MiniProgramLayout from '../../components/MiniProgramLayout.vue';

const rawImage = ref('');
const stylePreset = ref('cartoon_fallback');

onLoad((options: any) => {
  if (options.image) {
    rawImage.value = decodeURIComponent(options.image);
  }
  if (options.style) {
    stylePreset.value = options.style;
  }
});

const handleSelect = (tier: 'quick' | 'premium') => {
  uni.navigateTo({
    url: `/pages/preview/loading?tier=${tier}&style=${stylePreset.value}&image=${encodeURIComponent(rawImage.value)}`
  });
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
</style>
