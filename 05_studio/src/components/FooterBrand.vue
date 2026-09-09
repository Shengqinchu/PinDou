<script setup lang="ts">
import { computed } from 'vue';
import { asset, contentModule } from '../content-store';
import { locale, say } from '../state';
import appDefaults from '../content/App.json';
import brandDefaults from '../content/components-BrandMark.json';
import BrandMark from './BrandMark.vue';
import CopyContact from './CopyContact.vue';

const words = contentModule('App', appDefaults);
const brandWords = contentModule('components-BrandMark', brandDefaults);
// Only the supplied contact artwork has a known, fixed WeChat line and hit area.
// Uploaded replacements remain normal home links; no invisible stale contact target.
const hasContactArtwork = computed(() => locale.value === 'en'
  && asset('brand-en-contact').src === '/studio-brand/english-contact-20260908.jpg');
</script>

<template>
  <div v-if="hasContactArtwork" class="footer-contact-artwork">
    <BrandMark contact />
    <RouterLink to="/" class="footer-contact-home" :aria-label="say(words.pindo_puppy_home_69051e)" />
    <CopyContact class="footer-contact-copy" :value="say(brandWords.artwork_wechat)" />
  </div>
  <RouterLink v-else to="/" :aria-label="say(words.pindo_puppy_home_69051e)"><BrandMark :contact="locale === 'en'" /></RouterLink>
</template>

<style scoped>
.footer-contact-artwork { position: relative; width: 310px; max-width: 100%; padding-bottom: 18px; }
.footer-contact-home { position: absolute; inset: 0 0 auto; height: 64%; border-radius: 8px; }
.footer-contact-artwork .footer-contact-copy {
  position: absolute; bottom: 0; left: 2%; width: 96%;
  padding: 0; background: transparent; transform: none;
}
.footer-contact-copy :deep(.copy-contact-button) {
  width: 100%; min-height: 44px; border-radius: 7px;
  transition: background-color 300ms cubic-bezier(.4,0,.2,1);
}
.footer-contact-copy :deep(.copy-contact-button > *) {
  position: absolute; width: 1px; height: 1px; padding: 0; margin: -1px;
  overflow: hidden; clip-path: inset(50%); white-space: nowrap;
}
.footer-contact-copy :deep(.copy-contact-manual) {
  position: absolute; top: calc(100% + 8px); z-index: 2;
  width: 100%; padding: 10px; background: var(--paper, white);
  border: 1px solid var(--line); border-radius: 8px; box-sizing: border-box;
}
.footer-contact-home:focus-visible,
.footer-contact-copy :deep(.copy-contact-button:focus-visible) { outline: 2px solid currentColor; outline-offset: 2px; }
@media (hover: hover) and (pointer: fine) {
  .footer-contact-copy :deep(.copy-contact-button:hover) { background: rgb(168 199 219 / 16%); }
}
</style>
