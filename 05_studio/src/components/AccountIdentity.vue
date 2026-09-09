<script setup lang="ts">
import { computed,onBeforeUnmount,ref,watch } from 'vue';
import { PhPencilSimple,PhUserCircle } from '@phosphor-icons/vue';
import { accountCopy,accountUser } from '../account';
import { customerToken } from '../account-storage';
import { profileCopy as copy,normalizeNickname,imageError,saveProfilePart } from '../profile';
import { say } from '../state';
import { notify } from '../ui';
import SlideOver from './SlideOver.vue';
import InfoTip from './InfoTip.vue';
import WechatSignIn from './WechatSignIn.vue';
defineProps<{emailOnly?:boolean}>();
const editing=ref(false),busy=ref(false),nickname=ref(''),error=ref(''),file=ref<File>(),preview=ref(''),failed=ref(false);
const input=ref<HTMLInputElement>(),owner=ref(''),token=ref(''),original=ref('');
const name=computed(()=>normalizeNickname(nickname.value));
const valid=computed(()=>[...name.value].length>=1&&[...name.value].length<=20);
const changed=computed(()=>name.value!==original.value||!!file.value);
const avatar=computed(()=>preview.value||accountUser.value?.avatar||'');
function releasePreview(){if(preview.value)URL.revokeObjectURL(preview.value);preview.value='';}
function openEditor(){
  if(!accountUser.value)return;
  owner.value=accountUser.value.id;token.value=customerToken();
  original.value=normalizeNickname(accountUser.value.nickname||'');nickname.value=original.value;
  file.value=undefined;error.value='';releasePreview();editing.value=true;
}
function closeEditor(){if(!busy.value){editing.value=false;file.value=undefined;releasePreview();}}
function choose(event:Event){
  const selected=(event.target as HTMLInputElement).files?.[0];(event.target as HTMLInputElement).value='';
  if(!selected)return;
  error.value=imageError(selected);if(error.value)return;
  releasePreview();file.value=selected;preview.value=URL.createObjectURL(selected);
}
async function save(){
  if(busy.value||!changed.value)return;
  if(!valid.value){error.value=say(copy.name_invalid);return;}
  busy.value=true;error.value='';let nameSaved=false;
  try{
    if(name.value!==original.value){
      await saveProfilePart(token.value,owner.value,{nickname:name.value});
      original.value=name.value;nameSaved=true;
    }
    if(file.value)await saveProfilePart(token.value,owner.value,file.value);
    busy.value=false;closeEditor();notify(copy.saved[0],copy.saved[1],'success');
  }catch(e){error.value=nameSaved&&file.value?say(copy.partial_save):(e as Error).message;}
  finally{busy.value=false;}
}
watch(()=>accountUser.value?.id,()=>{editing.value=false;file.value=undefined;releasePreview();});
watch(()=>accountUser.value?.avatar,()=>failed.value=false);
onBeforeUnmount(releasePreview);
</script>
<template>
  <div v-if="accountUser" class="account-identity">
    <img v-if="accountUser.avatar&&!failed" class="account-portrait" :src="accountUser.avatar" alt="" referrerpolicy="no-referrer" @error="failed=true"/>
    <PhUserCircle v-else class="account-portrait" :size="56" weight="light"/>
    <div class="account-identity-text"><strong>{{accountUser.nickname||accountUser.email}}</strong><WechatSignIn v-if="!emailOnly" :key="accountUser.id" linking compact/><p v-else>{{accountUser.email}}</p></div>
    <button v-if="!emailOnly" type="button" class="account-edit" @click="openEditor"><PhPencilSimple :size="18"/><span>{{say(copy.edit)}}</span></button>
  </div>
  <SlideOver v-if="!emailOnly" :model-value="editing" :title="say(copy.edit)" :busy="busy" @update:model-value="closeEditor">
    <form class="account-form profile-form" @submit.prevent="save">
      <div class="profile-avatar-editor">
        <img v-if="avatar" class="profile-preview" :src="avatar" :alt="say(copy.avatar)" referrerpolicy="no-referrer"/>
        <PhUserCircle v-else :size="80" weight="light"/>
        <div class="profile-upload-actions"><button class="text-link" type="button" :disabled="busy" @click="input?.click()">{{say(copy.upload)}}</button><InfoTip :label="say(copy.image_help)"><p>{{say(copy.image_help)}}</p></InfoTip></div>
        <input ref="input" type="file" accept="image/jpeg,image/png,image/webp" hidden :disabled="busy" :aria-label="say(copy.upload)" @change="choose"/>
      </div>
      <label class="field"><span class="profile-field-label">{{say(copy.nickname)}}<InfoTip :label="say(copy.nickname_help)"><p>{{say(copy.nickname_help)}}</p></InfoTip></span><input v-model="nickname" autocomplete="nickname" required :disabled="busy" :aria-invalid="nickname.length>0&&!valid||undefined"/></label>
      <div class="profile-email"><span>{{say(accountCopy.email)}}</span><p>{{accountUser?.email}}</p><InfoTip :label="say(copy.shared_help)"><p>{{say(copy.shared_help)}}</p></InfoTip></div>
      <p v-if="error" class="form-error" role="alert">{{error}}</p>
      <div class="profile-actions"><button type="button" class="button button-secondary" :disabled="busy" @click="closeEditor">{{say(copy.cancel)}}</button><button class="button button-primary" :disabled="busy||!changed||!valid">{{say(busy?copy.saving:copy.save)}}</button></div>
    </form>
  </SlideOver>
</template>
