<template>
  <MiniProgramLayout title="出错了" backUrl="/pages/index/index" :scroll="true">
    <div class="error">
      <div class="error__art" aria-hidden="true">
        <svg width="120" height="120" viewBox="0 0 120 120" fill="none">
          <circle cx="60" cy="60" r="50" fill="#FFEDD5" />
          <path d="M48 50l24 24M72 50L48 74" stroke="#FF6B9D" stroke-width="3.5" stroke-linecap="round" />
        </svg>
      </div>
      <h2 class="error__title">{{ title }}</h2>
      <p class="error__desc">{{ desc }}</p>
      <button class="error__cta" @click="onRetry">{{ ctaText }}</button>
      <a class="error__help" href="javascript:void(0)" @click="onHelp">需要帮助？</a>
    </div>
  </MiniProgramLayout>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue';
import MiniProgramLayout from '../../components/MiniProgramLayout.vue';

type Variant = 'network' | 'fallback' | 'quota';

const variant = ref<Variant>('network');
const title = ref('网络有点慢');
const desc = ref('再试一次吧～');
const ctaText = ref('重试');

const variantMap: Record<Variant, { title: string; desc: string; cta: string }> = {
  network: { title: '网络有点慢', desc: '再试一次吧～', cta: '重试' },
  fallback: { title: 'AI 在偷懒', desc: '正在切换到快速生成…', cta: '我等等' },
  quota: { title: '今天的额度用完啦', desc: '看广告续 1 次，或购买月卡解锁更多', cta: '看广告续次' }
};

const applyVariant = (v: Variant) => {
  variant.value = v;
  title.value = variantMap[v].title;
  desc.value = variantMap[v].desc;
  ctaText.value = variantMap[v].cta;
};

onMounted(() => {
  const pages = getCurrentPages();
  const cur = pages[pages.length - 1] as any;
  const v = cur?.options?.variant as Variant;
  if (v && ['network', 'fallback', 'quota'].includes(v)) applyVariant(v);
});

const onRetry = () => { uni.navigateBack(); };
const onHelp = () => { uni.showToast({ title: '联系客服微信 pindou_help', icon: 'none', duration: 2500 }); };
</script>

<style lang="scss" scoped>
.error { padding: 64px 32px 32px; text-align: center; }
.error__art { margin: 0 auto 24px; width: 120px; height: 120px; }
.error__title { font-size: 22px; font-weight: 600; color: #2D1E1F; margin-bottom: 8px; }
.error__desc { font-size: 14px; color: #8C8C8C; margin-bottom: 32px; }
.error__cta { background: linear-gradient(135deg, #FF6B9D 0%, #FFA07A 100%); color: #fff; border: none; border-radius: 28px; padding: 14px 48px; font-size: 16px; font-weight: 600; }
.error__help { display: inline-block; margin-top: 24px; font-size: 13px; color: #FF6B9D; }
</style>
