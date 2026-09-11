import { computed, onMounted, onUnmounted, ref,watch } from 'vue';
import { onResize, onShow } from '@dcloudio/uni-app';
import miniappCopy from '../../../05_studio/src/content/miniapp.json';
import {useUserStore} from '../store/user';
import {setStudioCacheOwner} from './studio-cache';
import {studioPageShown} from './studio-navigation';

export type NativeLanguage = 'zh' | 'en';
export function useStudioNative() {
  const user=useUserStore();setStudioCacheOwner(user.token);
  watch(()=>user.token,setStudioCacheOwner,{flush:'sync'});
  const language = ref<NativeLanguage>(uni.getStorageSync('pd_studio_language') ||
    (/^en/i.test(uni.getSystemInfoSync().language || '') ? 'en' : 'zh'));
  const height = ref(uni.getSystemInfoSync().windowHeight);
  const width = ref(uni.getSystemInfoSync().windowWidth);
  const keyboardOpen = ref(false);
  const safeBottom=ref(Math.max(0,(uni.getSystemInfoSync().screenHeight||0)-(uni.getSystemInfoSync().safeArea?.bottom||uni.getSystemInfoSync().screenHeight||0)));
  const fullHeight=ref(height.value),keyboardHeight=ref(0);
  let resizeTimer:ReturnType<typeof setTimeout>|undefined;
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
  function keyboard(event: { height: number }) { keyboardHeight.value=Math.max(0,event.height);keyboardOpen.value = event.height > 0; }
  function syncSafeArea() {
    const info=uni.getSystemInfoSync();
    safeBottom.value=Math.max(0,(info.screenHeight||0)-(info.safeArea?.bottom||info.screenHeight||0));
  }
  onMounted(() => uni.onKeyboardHeightChange?.(keyboard));
  onUnmounted(() => {uni.offKeyboardHeightChange?.(keyboard);clearTimeout(resizeTimer);});
  onResize(event => { const rotated=width.value!==event.size.windowWidth;height.value = event.size.windowHeight; width.value = event.size.windowWidth;clearTimeout(resizeTimer);if(rotated){fullHeight.value=height.value;syncSafeArea();}else if(!keyboardOpen.value)resizeTimer=setTimeout(()=>{if(!keyboardOpen.value)fullHeight.value=height.value;},200); });
  onShow(()=>{syncLanguage();syncSafeArea();const info=uni.getSystemInfoSync();height.value=info.windowHeight;width.value=info.windowWidth;if(!keyboardOpen.value)fullHeight.value=height.value;studioPageShown(getCurrentPages().slice(-1)[0]?.route||'');});
  // iOS overlays its keyboard; Android may already have resized the window.
  const availableHeight=computed(()=>Math.max(180,keyboardOpen.value?Math.min(height.value,fullHeight.value-keyboardHeight.value):height.value));
  const shellStyle = computed(() => ({ '--studio-window-height': `${availableHeight.value}px`, '--studio-window-width':`${width.value}px`, '--studio-safe-bottom':`${keyboardOpen.value?0:safeBottom.value}px` }));
  function website() {
    uni.setClipboardData({ data: 'https://pindoupuppy.com/account?wechat_provider=miniapp',
      success: () => uni.showToast({ title: t('copied'), icon: 'none' }) });
  }
  return { language, width, keyboardOpen, shellStyle, say, t, changeLanguage, website };
}
