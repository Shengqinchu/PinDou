<script setup lang="ts">
import { computed,onBeforeUnmount,onMounted,ref,watch } from 'vue';
import { PhCaretDown,PhPencilSimple,PhUserCircle } from '@phosphor-icons/vue';
import { RouterLink,useRoute,useRouter } from 'vue-router';
import {defaultDisplayName} from '../identity-model';
import {accountReturn} from '../wechat';
import { accountCopy,accountUser,closeAccount } from '../account';
import { customerToken } from '../account-storage';
import { profileCopy as copy,normalizeNickname,imageError,saveProfilePart } from '../profile';
import { say } from '../state';
import { notify } from '../ui';
import { CommerceError } from '../commerce';
import SlideOver from './SlideOver.vue';
import InfoTip from './InfoTip.vue';
import WechatSignIn from './WechatSignIn.vue';
import BookingContactFields from './BookingContactFields.vue';
import { bookingProfileCopy as bookingCopy,emptyContact,contactDetails,sameContact,validContact,loadBookingProfile,saveBookingProfile,type BookingProfile } from '../booking-profile';
const props=defineProps<{emailOnly?:boolean;linkToCenter?:boolean}>();
const route=useRoute(),router=useRouter(),address=ref('');
const setupNeeded=computed(()=>!!accountUser.value?.id.startsWith('wechat_authing_')&&(defaultDisplayName(accountUser.value.nickname)||!accountUser.value.avatar));
const editing=ref(false),busy=ref(false),nickname=ref(''),error=ref(''),file=ref<File>(),preview=ref(''),failed=ref(false);
const input=ref<HTMLInputElement>(),owner=ref(''),token=ref(''),original=ref('');
const booking=ref<BookingProfile>(),bookingDraft=ref(emptyContact()),bookingLoading=ref(false),bookingError=ref('');let bookingSequence=0;
const bookingConflict=ref(false);
const name=computed(()=>normalizeNickname(nickname.value));
const valid=computed(()=>name.value===original.value||([...name.value].length>=1&&[...name.value].length<=20));
const bookingChanged=computed(()=>!!booking.value&&(!sameContact(bookingDraft.value,booking.value)||address.value!==(booking.value.delivery_address||'')));
const changed=computed(()=>name.value!==original.value||!!file.value||bookingChanged.value);
const avatar=computed(()=>preview.value||accountUser.value?.avatar||'');
function releasePreview(){if(preview.value)URL.revokeObjectURL(preview.value);preview.value='';}
function openEditor(){
  if(!accountUser.value)return;
  owner.value=accountUser.value.id;token.value=customerToken();
  original.value=normalizeNickname(accountUser.value.nickname||'');nickname.value=original.value;
  file.value=undefined;error.value='';address.value='';releasePreview();editing.value=true;
  booking.value=undefined;bookingConflict.value=false;bookingDraft.value=emptyContact();void loadBooking();
}
async function loadBooking(){
 const seq=++bookingSequence,id=owner.value;bookingLoading.value=true;bookingError.value='';
 try{const value=await loadBookingProfile(id,token.value);if(seq===bookingSequence&&editing.value){booking.value=value;bookingDraft.value=contactDetails(value);address.value=value.delivery_address||'';}}
 catch(e){if(seq===bookingSequence)bookingError.value=(e as Error).message;}
 finally{if(seq===bookingSequence)bookingLoading.value=false;}
}
function closeEditor(){if(!busy.value){editing.value=false;file.value=undefined;releasePreview();if(route.query.setup==='1'&&route.query.next)void router.replace(accountReturn(route.query.next,'/'));}}
async function useLatestBooking(){await loadBooking();if(!bookingError.value){bookingConflict.value=false;error.value='';}}
function choose(event:Event){
  const selected=(event.target as HTMLInputElement).files?.[0];(event.target as HTMLInputElement).value='';
  if(!selected)return;
  error.value=imageError(selected);if(error.value)return;
  releasePreview();file.value=selected;preview.value=URL.createObjectURL(selected);
}
async function save(){
  if(busy.value||bookingLoading.value||!changed.value)return;
  if(!valid.value){error.value=say(copy.name_invalid);return;}
  if(bookingChanged.value&&!validContact(bookingDraft.value,true)){error.value=say(bookingCopy.incomplete);return;}
  busy.value=true;error.value='';let savedAny=false;
  try{
    if(name.value!==original.value){
      await saveProfilePart(token.value,owner.value,{nickname:name.value});
      original.value=name.value;savedAny=true;
    }
    if(bookingChanged.value){booking.value=await saveBookingProfile(owner.value,token.value,bookingDraft.value,booking.value!.version,undefined,address.value);bookingDraft.value=contactDetails(booking.value);savedAny=true;}
    if(file.value)await saveProfilePart(token.value,owner.value,file.value);
    busy.value=false;closeEditor();notify(copy.saved[0],copy.saved[1],'success');
  }catch(e){bookingConflict.value=e instanceof CommerceError&&e.code==='booking_profile_changed';error.value=(savedAny?say(bookingCopy.partial)+' ':'')+(e as Error).message;}
  finally{busy.value=false;}
}
watch(()=>accountUser.value?.id,()=>{bookingSequence++;editing.value=false;file.value=undefined;booking.value=undefined;bookingDraft.value=emptyContact();releasePreview();});
watch(()=>accountUser.value?.avatar,()=>failed.value=false);
onBeforeUnmount(releasePreview);
onMounted(()=>{if(!props.emailOnly&&route.query.setup==='1')openEditor();});
watch(()=>route.query.setup,value=>{if(value==='1'&&!props.emailOnly&&!editing.value)openEditor();});
</script>
<template>
  <p v-if="setupNeeded&&!emailOnly" class="profile-setup-notice">{{say(copy.setup_help)}} <button class="text-link" @click="openEditor">{{say(copy.setup_title)}}</button></p>
  <p v-if="accountUser?.customer_code&&!emailOnly" class="fine-print">{{say(copy.customer_code)}} · {{accountUser.customer_code}}</p>
  <div v-if="accountUser" class="account-identity">
    <component :is="linkToCenter?RouterLink:'span'" class="account-avatar-link" v-bind="linkToCenter?{to:'/account','aria-label':say(accountCopy.account_center)}:{}" @click="linkToCenter&&closeAccount()"><img v-if="accountUser.avatar&&!failed" class="account-portrait" :src="accountUser.avatar" alt="" referrerpolicy="no-referrer" @error="failed=true"/><PhUserCircle v-else class="account-portrait" :size="56" weight="light"/></component>
     <div class="account-identity-text"><component :is="linkToCenter?RouterLink:'span'" class="account-name-link" v-bind="linkToCenter?{to:'/account'}:{}" @click="linkToCenter&&closeAccount()"><strong>{{accountUser.nickname||accountUser.email||say(accountCopy.default_name)}}</strong></component><p v-if="emailOnly">{{accountUser.email}}</p></div>
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
      <label class="field"><span class="profile-field-label">{{say(copy.nickname)}}<InfoTip :label="say(copy.nickname_help)"><p>{{say(copy.nickname_help)}}</p></InfoTip></span><input v-model="nickname" autocomplete="nickname" :required="name!==original" :disabled="busy" :aria-invalid="nickname.length>0&&!valid||undefined"/></label>
      <WechatSignIn :key="'editor-'+accountUser?.id" linking/>
       <details class="booking-profile-section"><summary>{{say(bookingCopy.title)}}<span class="booking-profile-toggle"><PhCaretDown :size="16"/></span></summary><p class="booking-profile-help">{{say(bookingCopy.helper)}}</p><p v-if="bookingLoading" role="status">{{say(bookingCopy.loading)}}</p><p v-else-if="bookingError" class="profile-contact-error" role="alert">{{bookingError}} <button type="button" class="text-link" @click="loadBooking">{{say(bookingCopy.retry)}}</button></p><template v-else><BookingContactFields class="profile-contact" v-model="bookingDraft" :name-label="say(bookingCopy.profile_name)" :required="false" :disabled="busy"/><label class="field">{{say(bookingCopy.delivery_address)}}<input v-model="address" autocomplete="street-address" maxlength="500" :disabled="busy"/></label></template></details>
      <p v-if="error" class="form-error" role="alert">{{error}} <button v-if="bookingConflict" class="text-link" type="button" :disabled="busy||bookingLoading" @click="useLatestBooking">{{say(bookingCopy.use_latest)}}</button></p>
      <div class="profile-actions"><button type="button" class="button button-secondary" :disabled="busy" @click="closeEditor">{{say(copy.cancel)}}</button><button class="button button-primary" :disabled="busy||bookingLoading||!changed||!valid">{{say(busy?copy.saving:copy.save)}}</button></div>
    </form>
  </SlideOver>
</template>
