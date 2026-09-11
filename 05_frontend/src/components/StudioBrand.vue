<script setup lang="ts">
import motifCopy from '../../../05_studio/src/content/components-BrandMotif.json';
defineOptions({ options: { styleIsolation: 'shared' } });
defineProps<{ language: string; puppy?: boolean }>();
</script>
<template>
  <button :hover-start-time="0" class="studio-brand-touch" :class="{'studio-brand-touch--puppy':puppy}" hover-class="studio-brand-squeezed" :hover-stay-time="260" :aria-label="motifCopy.puppy[language==='en'?1:0]">
    <view v-if="puppy" class="studio-brand-puppy"><image src="/static/studio/puppy.png" mode="aspectFit" /></view>
    <view v-else class="studio-brand-window" :class="{'studio-brand-window--en':language==='en'}"><image :src="language==='en'?'/static/studio/logo-en.jpg':'/static/studio/logo-zh.jpg'" mode="widthFix" /></view>
  </button>
</template>
<style>
.studio-brand-touch{padding:0!important;width:144px;min-height:58px!important;background:transparent!important;overflow:visible!important;flex-shrink:0}
.studio-brand-window{position:relative;width:144px;height:54.34px;overflow:hidden;transition:transform .6s cubic-bezier(.22,1.5,.45,1)}
.studio-brand-window image{position:absolute;width:100%;left:0;top:-93%}
.studio-brand-window--en{height:56.81px}.studio-brand-window--en image{top:-90.1%}
.studio-brand-touch--puppy{width:104px;min-height:76px!important}
.studio-brand-puppy{width:90px;height:72px;transition:transform .6s cubic-bezier(.22,1.5,.45,1)}
.studio-brand-puppy image{width:100%;height:100%}
.studio-brand-squeezed .studio-brand-window,.studio-brand-squeezed .studio-brand-puppy{transform:scale(1.08,.88) rotate(-4deg);transition-duration:.18s}
</style>
