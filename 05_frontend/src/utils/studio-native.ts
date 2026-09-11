import { computed, onMounted, onUnmounted, ref } from 'vue';
import { onResize, onShow } from '@dcloudio/uni-app';
import miniappCopy from '../../../05_studio/src/content/miniapp.json';

export type NativeLanguage = 'zh' | 'en';
export function useStudioNative() {
  const language = ref<NativeLanguage>(uni.getStorageSync('pd_studio_language') ||
    (/^en/i.test(uni.getSystemInfoSync().language || '') ? 'en' : 'zh'));
  const height = ref(uni.getSystemInfoSync().windowHeight);
  const width = ref(uni.getSystemInfoSync().windowWidth);
  const keyboardOpen = ref(false);
  const say = (text: string[]) => text[language.value === 'en' ? 1 : 0];
  const t = (key: keyof typeof miniappCopy) => say(miniappCopy[key]);
  function syncLanguage() {
    language.value = uni.getStorageSync('pd_studio_language') || language.value;
    uni.setNavigationBarTitle({ title: t('brand') });
  }
  function changeLanguage() {
    language.value = language.value === 'zh' ? 'en' : 'zh';
    uni.setStorageSync('pd_studio_language', language.value);
    syncLanguage();
  }
  function keyboard(event: { height: number }) { keyboardOpen.value = event.height > 0; }
  onMounted(() => uni.onKeyboardHeightChange?.(keyboard));
  onUnmounted(() => uni.offKeyboardHeightChange?.(keyboard));
  onResize(event => { height.value = event.size.windowHeight; width.value = event.size.windowWidth; });
  onShow(syncLanguage);
  const shellStyle = computed(() => ({ '--studio-window-height': `${height.value}px` }));
  function website() {
    uni.setClipboardData({ data: 'https://pindoupuppy.com/account?wechat_provider=miniapp',
      success: () => uni.showToast({ title: t('copied'), icon: 'none' }) });
  }
  return { language, width, keyboardOpen, shellStyle, say, t, changeLanguage, website };
}
