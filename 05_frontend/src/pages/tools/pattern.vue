<script setup lang="ts">
import {pressTo} from '../../utils/press';
import {computed,ref} from 'vue';
import {onShow,onUnload} from '@dcloudio/uni-app';
import StudioShell from '../../components/StudioShell.vue';
import StudioGlyph from '../../components/StudioGlyph.vue';
import {useStudioNative} from '../../utils/studio-native';
import {studioWords} from '../../utils/studio-content';
import {compressPhoto,makePattern,patternState,PatternError,readPhotoBase64,savePatternImage,type PatternResult} from '../../utils/pattern-tool';
const {language,keyboardOpen,shellStyle,say,changeLanguage}=useStudioNative();
const words=(key:string)=>say(studioWords('miniapp',key));
const sizes=[26,52,78,104] as const;
// The same three stages the website shows for standard generation.
const stages=['pattern_stage_photo','pattern_stage_colors','pattern_stage_render'];
const size=ref<number>(52),photo=ref(''),busy=ref(false),saving=ref(false),errorCode=ref(''),result=ref<PatternResult|null>(null),resetKey=ref(0),progress=ref(0);
const stage=computed(()=>progress.value<30?0:progress.value<70?1:2);
const summary=computed(()=>result.value?words('pattern_total').replace('{v0}',String(result.value.total)).replace('{v1}',String(result.value.colors.length)):'');
let timer:ReturnType<typeof setInterval>|undefined;
function startProgress(){progress.value=8;clearInterval(timer);timer=setInterval(()=>{progress.value=Math.min(88,progress.value+Math.max(1,Math.round((88-progress.value)/9)));},260);}
function stopProgress(done:boolean){clearInterval(timer);timer=undefined;progress.value=done?100:0;}
onUnload(()=>clearInterval(timer));
// Returning from the editor shows the saved version.
onShow(()=>{const latest=patternState.get();if(result.value&&latest&&latest.artworkId===result.value.artworkId&&latest!==result.value){result.value=latest;resetKey.value++;}});
function choose(){
 if(busy.value)return;
 const done=(path?:string)=>{if(path){photo.value=path;errorCode.value='';}};
 if(typeof uni.chooseMedia==='function')uni.chooseMedia({count:1,mediaType:['image'],sourceType:['album','camera'],sizeType:['compressed'],success:value=>done(value.tempFiles[0]?.tempFilePath)});
 else uni.chooseImage({count:1,sizeType:['compressed'],sourceType:['album','camera'],success:value=>done(value.tempFilePaths[0])});
}
async function generate(){
 if(busy.value||!photo.value)return;
 busy.value=true;errorCode.value='';startProgress();
 try{
  const compressed=await compressPhoto(photo.value);
  const extension=(compressed.split('?')[0].split('.').pop()||'').toLowerCase();
  const made=await makePattern(await readPhotoBase64(compressed),size.value,extension);
  stopProgress(true);result.value=made;patternState.set(made);resetKey.value++;
 }catch(error){stopProgress(false);errorCode.value=error instanceof PatternError?error.code:'pattern_error';}
 finally{busy.value=false;}
}
function zoom(){if(result.value)uni.previewImage({urls:[result.value.imageUrl],current:result.value.imageUrl});}
function edit(){if(result.value){patternState.set(result.value);pressTo('/pages/tools/edit');}}
async function save(){
 if(!result.value||saving.value)return;saving.value=true;
 try{await savePatternImage(result.value);uni.showToast({title:words('pattern_saved'),icon:'success'});}
 catch(error){
  const denied=/auth|deny|denied/i.test(String((error as any)?.errMsg||''));
  if(denied)uni.showModal({content:words('pattern_save_denied'),confirmText:words('pattern_open_settings'),cancelText:words('cancel'),success:value=>{if(value.confirm)uni.openSetting({});}});
  else if(!/cancel/i.test(String((error as any)?.errMsg||'')))uni.showToast({title:words(error instanceof PatternError?error.code:'pattern_error'),icon:'none'});
 }finally{saving.value=false;}
}
function again(){result.value=null;photo.value='';errorCode.value='';progress.value=0;resetKey.value++;}
function visit(){pressTo('/pages/studio/visit');}
</script>
<template>
 <StudioShell id="studio-pattern-shell" fitted :reset-key="resetKey" :language="language" :keyboard-open="keyboardOpen" :shell-style="shellStyle" @language="changeLanguage">
  <view class="studio-native-main studio-pattern">
   <view class="studio-native-section"><text class="studio-native-title">{{words(result?'pattern_result':'pattern_title')}}</text><text class="studio-native-body">{{result?summary:words('pattern_intro')}}</text></view>
   <template v-if="!result">
    <button class="studio-pattern-photo" :class="{'studio-pattern-photo--filled':photo}" hover-class="studio-native-pressed" :hover-start-time="0" :hover-stay-time="180" :disabled="busy" @tap="choose">
     <image v-if="photo" :src="photo" mode="aspectFit" class="studio-pattern-photo-image" :class="{'studio-pattern-photo-image--busy':busy}"/>
     <view v-else class="studio-pattern-photo-empty"><StudioGlyph name="image" :size="30"/><text>{{words('pattern_pick')}}</text></view>
    </button>
    <view v-if="busy" class="studio-pattern-progress" role="progressbar" :aria-valuenow="progress" aria-valuemin="0" aria-valuemax="100">
     <view class="studio-pattern-progress-head"><image class="studio-pattern-puppy" src="/static/studio/puppy.png" mode="aspectFit"/><text class="studio-pattern-progress-stage">{{words(stages[stage])}}</text><text class="studio-pattern-progress-value">{{progress}}%</text></view>
     <view class="studio-pattern-progress-track"><view class="studio-pattern-progress-fill" :style="{width:progress+'%'}"/></view>
     <view class="studio-pattern-stages"><text v-for="(key,index) in stages" :key="key" :class="{'studio-pattern-stage--done':index<stage,'studio-pattern-stage--active':index===stage}">{{index+1}} {{words(key)}}</text></view>
    </view>
    <template v-else>
     <button v-if="photo" class="studio-native-link studio-pattern-change" hover-class="studio-native-pressed" :hover-stay-time="180" :hover-start-time="0" @tap="choose"><StudioGlyph name="refresh" :size="17"/><text>{{words('pattern_change')}}</text></button>
     <view class="studio-pattern-sizes"><button v-for="value in sizes" :key="value" class="studio-plan" :class="{'studio-plan--selected':size===value}" hover-class="studio-native-pressed" :hover-start-time="0" :hover-stay-time="180" :aria-pressed="size===value" @tap="size=value"><text class="studio-pattern-size">{{value}}</text><text class="studio-pattern-size-unit">× {{value}}</text></button></view>
     <text class="studio-native-body studio-native-small">{{words('pattern_photo_note')}}</text>
    </template>
   </template>
   <template v-else>
    <image class="studio-pattern-result" :src="result.imageUrl" mode="widthFix" :aria-label="words('pattern_result')" @tap="zoom"/>
    <view class="studio-pattern-colors"><view v-for="color in result.colors" :key="color.code" class="studio-pattern-color"><view class="studio-pattern-swatch" :style="{background:color.hex}"/><text class="studio-pattern-code">{{color.code}}</text><text class="studio-pattern-count">{{color.count}}</text></view></view>
    <text class="studio-native-body studio-native-small">{{words('pattern_brand_note')}}</text>
    <view class="studio-pattern-actions"><button class="studio-native-secondary" hover-class="studio-native-pressed" :hover-stay-time="180" :hover-start-time="0" @tap="edit"><StudioGlyph name="brush" :size="18"/><text>{{words('pattern_edit')}}</text></button><button class="studio-native-secondary" hover-class="studio-native-pressed" :hover-stay-time="180" :hover-start-time="0" @tap="again"><StudioGlyph name="image" :size="18"/><text>{{words('pattern_again')}}</text></button><button class="studio-native-secondary" hover-class="studio-native-pressed" :hover-stay-time="180" :hover-start-time="0" @tap="visit"><StudioGlyph name="calendar" :size="18"/><text>{{words('pattern_visit')}}</text></button></view>
   </template>
   <text v-if="errorCode" class="studio-native-error" role="alert">{{words(errorCode)}}</text>
  </view>
  <template #actions><view class="studio-visit-actions">
   <button v-if="!result" class="studio-native-primary" hover-class="studio-native-pressed" :hover-stay-time="180" :hover-start-time="0" :disabled="busy||!photo" @tap="generate"><StudioGlyph name="grid"/><text class="studio-native-primary-label">{{words(busy?'pattern_working':photo?'pattern_generate':'pattern_pick_first')}}</text></button>
   <button v-else class="studio-native-primary" hover-class="studio-native-pressed" :hover-stay-time="180" :hover-start-time="0" :disabled="saving" :loading="saving" @tap="save"><StudioGlyph name="download"/><text class="studio-native-primary-label">{{words('pattern_save')}}</text></button>
  </view></template>
 </StudioShell>
</template>
