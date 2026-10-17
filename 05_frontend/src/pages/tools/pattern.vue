<script setup lang="ts">
import {computed,ref} from 'vue';
import StudioShell from '../../components/StudioShell.vue';
import StudioGlyph from '../../components/StudioGlyph.vue';
import {useStudioNative} from '../../utils/studio-native';
import {studioWords} from '../../utils/studio-content';
import {compressPhoto,makePattern,PatternError,readPhotoBase64,savePatternImage,type PatternResult} from '../../utils/pattern-tool';
const {language,keyboardOpen,shellStyle,say,changeLanguage}=useStudioNative();
const words=(key:string)=>say(studioWords('miniapp',key));
const sizes=[26,52,78,104] as const;
const size=ref<number>(52),photo=ref(''),busy=ref(false),saving=ref(false),errorCode=ref(''),result=ref<PatternResult|null>(null),resetKey=ref(0);
const summary=computed(()=>result.value?words('pattern_total').replace('{v0}',String(result.value.total)).replace('{v1}',String(result.value.colors.length)):'');
function choose(){
 if(busy.value)return;
 const done=(path?:string)=>{if(path){photo.value=path;errorCode.value='';}};
 if(typeof uni.chooseMedia==='function')uni.chooseMedia({count:1,mediaType:['image'],sourceType:['album','camera'],sizeType:['compressed'],success:value=>done(value.tempFiles[0]?.tempFilePath)});
 else uni.chooseImage({count:1,sizeType:['compressed'],sourceType:['album','camera'],success:value=>done(value.tempFilePaths[0])});
}
async function generate(){
 if(busy.value||!photo.value)return;
 busy.value=true;errorCode.value='';
 try{
  const compressed=await compressPhoto(photo.value);
  const extension=(compressed.split('?')[0].split('.').pop()||'').toLowerCase();
  result.value=await makePattern(await readPhotoBase64(compressed),size.value,extension);
  resetKey.value++;
 }catch(error){errorCode.value=error instanceof PatternError?error.code:'pattern_error';}
 finally{busy.value=false;}
}
function zoom(){if(result.value)uni.previewImage({urls:[result.value.imageUrl],current:result.value.imageUrl});}
async function save(){
 if(!result.value||saving.value)return;saving.value=true;
 try{await savePatternImage(result.value);uni.showToast({title:words('pattern_saved'),icon:'success'});}
 catch(error){
  const denied=/auth|deny|denied/i.test(String((error as any)?.errMsg||''));
  if(denied)uni.showModal({content:words('pattern_save_denied'),confirmText:words('pattern_open_settings'),cancelText:words('cancel'),success:value=>{if(value.confirm)uni.openSetting({});}});
  else if(!/cancel/i.test(String((error as any)?.errMsg||'')))uni.showToast({title:words(error instanceof PatternError?error.code:'pattern_error'),icon:'none'});
 }finally{saving.value=false;}
}
function again(){result.value=null;photo.value='';errorCode.value='';resetKey.value++;}
function visit(){uni.navigateTo({url:'/pages/studio/visit'});}
</script>
<template>
 <StudioShell id="studio-pattern-shell" fitted :reset-key="resetKey" :language="language" :keyboard-open="keyboardOpen" :shell-style="shellStyle" @language="changeLanguage">
  <view class="studio-native-main studio-pattern">
   <view class="studio-native-section"><text class="studio-native-label">{{words('pattern_label')}}</text><text class="studio-native-title">{{words(result?'pattern_result':'pattern_title')}}</text><text v-if="!result" class="studio-native-body">{{words('pattern_intro')}}</text><text v-else class="studio-native-body">{{summary}}</text></view>
   <template v-if="!result">
    <button class="studio-pattern-photo" :class="{'studio-pattern-photo--filled':photo}" hover-class="studio-native-pressed" :hover-start-time="0" :hover-stay-time="180" :disabled="busy" @tap="choose">
     <image v-if="photo" :src="photo" mode="aspectFit" class="studio-pattern-photo-image"/>
     <view v-else class="studio-pattern-photo-empty"><StudioGlyph name="image" :size="30"/><text>{{words('pattern_pick')}}</text></view>
    </button>
    <button v-if="photo" class="studio-native-link studio-pattern-change" hover-class="studio-native-pressed" :disabled="busy" @tap="choose"><StudioGlyph name="refresh" :size="17"/><text>{{words('pattern_change')}}</text></button>
    <view class="studio-native-section">
     <text class="studio-native-subtitle">{{words('pattern_size')}}</text>
     <view class="studio-pattern-sizes"><button v-for="value in sizes" :key="value" class="studio-plan" :class="{'studio-plan--selected':size===value}" hover-class="studio-native-pressed" :hover-start-time="0" :hover-stay-time="180" :aria-pressed="size===value" :disabled="busy" @tap="size=value"><text class="studio-pattern-size">{{value}}</text><text class="studio-pattern-size-unit">× {{value}}</text></button></view>
     <text class="studio-native-body studio-native-small">{{words('pattern_size_hint')}}</text>
    </view>
    <text class="studio-native-body studio-native-small">{{words('pattern_photo_note')}}</text>
   </template>
   <template v-else>
    <image class="studio-pattern-result" :src="result.imageUrl" mode="widthFix" :aria-label="words('pattern_result')" @tap="zoom"/>
    <text class="studio-native-body studio-native-small">{{words('pattern_preview')}}</text>
    <view class="studio-native-section">
     <text class="studio-native-subtitle">{{words('pattern_colors')}}</text>
     <view class="studio-pattern-colors"><view v-for="color in result.colors" :key="color.code" class="studio-pattern-color"><view class="studio-pattern-swatch" :style="{background:color.hex}"/><text class="studio-pattern-code">{{color.code}}</text><text class="studio-pattern-count">{{color.count}}</text></view></view>
     <text class="studio-native-body studio-native-small">{{words('pattern_brand_note')}}</text>
    </view>
    <view class="studio-contact-shortcuts"><button class="studio-native-secondary" hover-class="studio-native-pressed" @tap="again"><StudioGlyph name="image" :size="18"/><text>{{words('pattern_again')}}</text></button><button class="studio-native-secondary" hover-class="studio-native-pressed" @tap="visit"><StudioGlyph name="calendar" :size="18"/><text>{{words('pattern_visit')}}</text></button></view>
   </template>
   <text v-if="errorCode" class="studio-native-error" role="alert">{{words(errorCode)}}</text>
  </view>
  <template #actions><view class="studio-visit-actions">
   <button v-if="!result" class="studio-native-primary" hover-class="studio-native-pressed" :disabled="busy||!photo" :loading="busy" @tap="generate"><StudioGlyph name="grid"/><text class="studio-native-primary-label">{{words(busy?'pattern_working':photo?'pattern_generate':'pattern_pick_first')}}</text></button>
   <button v-else class="studio-native-primary" hover-class="studio-native-pressed" :disabled="saving" :loading="saving" @tap="save"><StudioGlyph name="download"/><text class="studio-native-primary-label">{{words('pattern_save')}}</text></button>
  </view></template>
 </StudioShell>
</template>
<style>
.studio-pattern{gap:16px}
.studio-native .studio-pattern-photo{display:flex;align-items:center;justify-content:center;width:100%;height:220px;padding:0;background:#f6f9fb;border:1px dashed #c7d6e0;border-radius:18px;overflow:hidden}
.studio-native .studio-pattern-photo--filled{border-style:solid;border-color:#e0e9ef;background:#fff}
.studio-pattern-photo-image{width:100%;height:100%}
.studio-pattern-photo-empty{display:flex;flex-direction:column;align-items:center;gap:9px;color:#5a6f7d;font-size:14px}
.studio-native .studio-pattern-change{align-self:flex-start;gap:6px}
.studio-pattern-sizes{display:flex;gap:8px}
.studio-native .studio-pattern-sizes .studio-plan{min-height:0;align-items:center;gap:2px;padding:10px 4px;border-radius:14px}
.studio-pattern-size{font-size:20px;font-weight:600;color:#304d60;line-height:1.2}
.studio-pattern-size-unit{font-size:11px;color:#7c8f9b}
.studio-pattern-result{width:100%;border-radius:14px;border:1px solid #e0e9ef;background:#fff}
.studio-pattern-colors{display:flex;flex-wrap:wrap;gap:8px}
.studio-pattern-color{display:flex;align-items:center;gap:6px;padding:6px 10px 6px 6px;background:#f6f9fb;border:1px solid #e0e9ef;border-radius:12px}
.studio-pattern-swatch{width:20px;height:20px;border-radius:50%;border:1px solid #0000001f}
.studio-pattern-code{font-size:13px;font-weight:600;color:#344957}
.studio-pattern-count{font-size:12px;color:#6d808c}
</style>
