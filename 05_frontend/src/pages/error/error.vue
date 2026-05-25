<template>
  <MiniProgramLayout title="出错了" backUrl="/pages/index/index" :scroll="true">
    <div class="error">
      <div class="error__art" aria-hidden="true">
        <span class="error__art-x error__art-x--a"></span>
        <span class="error__art-x error__art-x--b"></span>
      </div>
      <h2 class="error__title">{{ title }}</h2>
      <p class="error__desc">{{ desc }}</p>
      <button class="error__cta" @click="onRetry">{{ ctaText }}</button>
      <view class="error__help" @click="onHelp">需要帮助？</view>
    </div>
  </MiniProgramLayout>
</template>

<script setup lang="ts">
import { ref } from 'vue';
import { onLoad } from '@dcloudio/uni-app';
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

onLoad((options: any = {}) => {
  const v = options?.variant as Variant;
  if (v && ['network', 'fallback', 'quota'].includes(v)) applyVariant(v);
  if (options?.title) title.value = decodeURIComponent(options.title);
  if (options?.message) desc.value = decodeURIComponent(options.message);
});

const onRetry = () => { uni.navigateBack(); };
const onHelp = () => { uni.showToast({ title: '联系客服微信 pindou_help', icon: 'none', duration: 2500 }); };
</script>

<style lang="scss" scoped>
.error { padding: 64px 32px 32px; text-align: center; }
.error__art {
  margin: 0 auto 24px;
  width: 120px;
  height: 120px;
  border-radius: 999px;
  background: #FFEDD5;
  position: relative;
}
.error__art-x {
  position: absolute;
  left: 40px;
  top: 58px;
  width: 40px;
  height: 4px;
  border-radius: 999px;
  background: #FF6B9D;
}
.error__art-x--a { transform: rotate(45deg); }
.error__art-x--b { transform: rotate(-45deg); }
.error__title { font-size: 22px; font-weight: 600; color: #2D1E1F; margin-bottom: 8px; }
.error__desc { font-size: 14px; color: #8C8C8C; margin-bottom: 32px; }
.error__cta { background: linear-gradient(135deg, #FF6B9D 0%, #FFA07A 100%); color: #fff; border: none; border-radius: 28px; padding: 14px 48px; font-size: 16px; font-weight: 600; }
.error__help { display: inline-block; margin-top: 24px; font-size: 13px; color: #FF6B9D; }
</style>
