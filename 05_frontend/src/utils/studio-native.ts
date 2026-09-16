import {computed,inject,onUnmounted,provide,ref,watch,type Ref,type ComputedRef,type InjectionKey} from 'vue';
import {onResize,onShow,onHide} from '@dcloudio/uni-app';
import miniappCopy from '../../../05_studio/src/content/miniapp.json';
import {useUserStore} from '../store/user';
import {setStudioCacheOwner} from './studio-cache';
import {studioPageShown} from './studio-navigation';
export type NativeLanguage='zh'|'en';
type NativeContext={language:Ref<NativeLanguage>;width:Ref<number>;keyboardOpen:Ref<boolean>;shellStyle:ComputedRef<Record<string,string>>;say:(text:string[])=>string;t:(key:keyof typeof miniappCopy)=>string;changeLanguage:()=>void;website:()=>void};
const nativeKey:InjectionKey<NativeContext>=Symbol('studio-native-window');
export function provideStudioNative(value:NativeContext){provide(nativeKey,value);}
type WindowInfo={windowHeight:number;windowWidth:number;screenHeight:number;safeArea?:{bottom:number};language?:string};
let windowInfo:WindowInfo|undefined,readAt=0;
function readWindow(force=false){
 if(!force&&windowInfo&&Date.now()-readAt<100)return windowInfo;
 windowInfo=typeof uni.getWindowInfo==='function'?uni.getWindowInfo():uni.getSystemInfoSync();readAt=Date.now();return windowInfo;
}
export function useStudioNative():NativeContext{
 const inherited=inject(nativeKey,undefined);if(inherited)return inherited;
 const user=useUserStore();setStudioCacheOwner(user.token);watch(()=>user.token,setStudioCacheOwner,{flush:'sync'});
 const info=readWindow(),stored=uni.getStorageSync('pd_studio_language');
 const systemLanguage=stored?'':info.language||(typeof uni.getAppBaseInfo==='function'?uni.getAppBaseInfo().language:'zh');
 const language=ref<NativeLanguage>(stored||(/^en/i.test(systemLanguage||'')?'en':'zh'));
 const height=ref(info.windowHeight),width=ref(info.windowWidth),keyboardOpen=ref(false),keyboardHeight=ref(0),fullHeight=ref(info.windowHeight);
 const inset=(value:WindowInfo)=>Math.max(0,(value.screenHeight||0)-(value.safeArea?.bottom||value.screenHeight||0));
 const safeBottom=ref(inset(info));let resizeTimer:ReturnType<typeof setTimeout>|undefined,listening=false,lastTitle='';
 const say=(text:string[])=>text[language.value==='en'?1:0],t=(key:keyof typeof miniappCopy)=>say(miniappCopy[key]);
 function syncLanguage(){language.value=uni.getStorageSync('pd_studio_language')||language.value;const title=t('brand');if(title!==lastTitle){uni.setNavigationBarTitle({title});lastTitle=title;}}
 function changeLanguage(){language.value=language.value==='zh'?'en':'zh';uni.setStorageSync('pd_studio_language',language.value);syncLanguage();}
 function keyboard(event:{height:number}){keyboardHeight.value=Math.max(0,event.height);keyboardOpen.value=event.height>0;}
 function stop(){if(listening)uni.offKeyboardHeightChange?.(keyboard);listening=false;clearTimeout(resizeTimer);keyboardOpen.value=false;keyboardHeight.value=0;}
 onHide(stop);onUnmounted(stop);
 onResize(event=>{if(!event.size)return;const rotated=width.value!==event.size.windowWidth;height.value=event.size.windowHeight;width.value=event.size.windowWidth;clearTimeout(resizeTimer);if(rotated){fullHeight.value=height.value;safeBottom.value=inset(readWindow(true));}else if(!keyboardOpen.value)resizeTimer=setTimeout(()=>{if(!keyboardOpen.value)fullHeight.value=height.value;},200);});
 onShow(()=>{
  syncLanguage();const current=readWindow();height.value=current.windowHeight;width.value=current.windowWidth;safeBottom.value=inset(current);if(!keyboardOpen.value)fullHeight.value=height.value;
  if(!listening){uni.onKeyboardHeightChange?.(keyboard);listening=true;}
  studioPageShown(getCurrentPages().slice(-1)[0]?.route||'');
 });
 const availableHeight=computed(()=>Math.max(180,keyboardOpen.value?Math.min(height.value,fullHeight.value-keyboardHeight.value):height.value));
 const shellStyle=computed(()=>({'--studio-window-height':`${availableHeight.value}px`,'--studio-window-width':`${width.value}px`,'--studio-safe-bottom':`${keyboardOpen.value?0:safeBottom.value}px`}));
 function website(){uni.setClipboardData({data:'https://pindoupuppy.com/account?wechat_provider=miniapp',success:()=>uni.showToast({title:t('copied'),icon:'none'})});}
 return {language,width,keyboardOpen,shellStyle,say,t,changeLanguage,website};
}
