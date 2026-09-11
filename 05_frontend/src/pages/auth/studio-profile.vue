<script setup lang="ts">
import {computed,reactive,ref,watch} from 'vue';
import {onLoad,onShow,onUnload} from '@dcloudio/uni-app';
import StudioShell from '../../components/StudioShell.vue';
import StudioGlyph from '../../components/StudioGlyph.vue';
import {useUserStore} from '../../store/user';
import {useStudioNative} from '../../utils/studio-native';
import {studioRead,studioCall,MiniappError} from '../../utils/miniapp-client';
import {studioWords,bookingError} from '../../utils/studio-content';
import profileWords from '../../../../05_studio/src/content/profile.json';
import {emptyContact,validContact,type ContactProfile} from '../../utils/studio-booking';
import {normalizedName,validName,validateAvatar,saveNickname,saveAvatar,assertProfileOwner,ProfileError} from '../../utils/studio-profile';
const user=useUserStore(),{language,keyboardOpen,shellStyle,say,changeLanguage}=useStudioNative();
const words=(key:keyof typeof profileWords)=>say(studioWords('profile',key));
const nickname=ref(''),originalName=ref(''),avatar=ref(''),selectedAvatar=ref(''),imageFailed=ref(false),loading=ref(true),busy=ref(false),choosing=ref(false),errorCode=ref(''),partial=ref(false),booking=ref<ContactProfile>();
const contact=reactive(emptyContact());let owner='',token='',alive=true,sequence=0;
const methods=[{value:'wechat',key:'wechat_2941d2',field:'wechat_id_7a6e86'},{value:'email',key:'email_b6d15f',field:'email_address_a61e0e'},{value:'phone',key:'phone_ac7a62',field:'phone_number_15447d'},{value:'other',key:'another_way_f489b4',field:'contact_details_3b7403'}] as const;
const contacts=computed(()=>methods.map(item=>({...item,label:say(studioWords('visit',item.key))})));
const contactIndex=computed(()=>Math.max(0,methods.findIndex(item=>item.value===contact.contact_method)));
const changedContact=computed(()=>!!booking.value&&['name','contact_method','contact'].some(key=>(contact as any)[key]!== (booking.value as any)[key]));
const changed=computed(()=>normalizedName(nickname.value)!==originalName.value||!!selectedAvatar.value||changedContact.value);
const preview=computed(()=>{const value=selectedAvatar.value||avatar.value;return value.startsWith('/')?'https://pindoupuppy.com'+value:value;});
const error=computed(()=>errorCode.value in profileWords?words(errorCode.value as keyof typeof profileWords):say(bookingError(errorCode.value)));
let nativeAvatar=false;
// #ifdef MP-WEIXIN
nativeAvatar=typeof uni.canIUse==='function'&&uni.canIUse('button.open-type.chooseAvatar');
// #endif
async function load(){
 if(!user.token){uni.redirectTo({url:'/pages/auth/studio-login'});return;}
 const seq=++sequence;token=user.token;loading.value=true;errorCode.value='';
 try{const [account,saved]=await Promise.all([studioRead<{user:{id:string;nickname:string;avatar:string}}>('/auth/me',token),studioRead<ContactProfile>('/auth/booking-profile',token)]);
  if(!alive||seq!==sequence||token!==user.token)return;
  if(saved.owner_id!==account.user.id)throw new ProfileError('account_login_required',401);
  owner=account.user.id;nickname.value=account.user.nickname;originalName.value=normalizedName(nickname.value);avatar.value=account.user.avatar||'';booking.value=saved;Object.assign(contact,{name:saved.name,contact_method:saved.contact_method,contact:saved.contact});
 }catch(e){if(alive&&seq===sequence)errorCode.value=e instanceof MiniappError||e instanceof ProfileError?e.code:'save_error';}
 finally{if(alive&&seq===sequence)loading.value=false;}
}
async function choosePath(path:string){
 if(!path||busy.value||choosing.value)return;choosing.value=true;errorCode.value='';const selectedToken=token;
 try{await validateAvatar(path);if(alive&&selectedToken===user.token){selectedAvatar.value=path;imageFailed.value=false;}}
 catch(e){if(alive)errorCode.value=e instanceof ProfileError?e.code:'image_invalid';}
 finally{if(alive)choosing.value=false;}
}
function chooseAvatar(event:{detail:{avatarUrl:string}}){void choosePath(event.detail.avatarUrl);}
function chooseFallback(){if(nativeAvatar||busy.value||choosing.value)return;uni.chooseImage({count:1,sizeType:['compressed'],sourceType:['album','camera'],success:r=>void choosePath(r.tempFilePaths[0])});}
function methodChange(event:{detail:{value:string}}){contact.contact_method=methods[Number(event.detail.value)].value;}
function close(){if(busy.value)return;if(getCurrentPages().length>1)uni.navigateBack();else uni.redirectTo({url:'/pages/auth/studio-account'});}
async function useLatest(){
 if(busy.value)return;loading.value=true;
 try{const value=await studioRead<ContactProfile>('/auth/booking-profile',token);assertProfileOwner(token,owner);if(value.owner_id!==owner)throw new ProfileError('account_login_required',401);if(alive){booking.value=value;Object.assign(contact,{name:value.name,contact_method:value.contact_method,contact:value.contact});errorCode.value='';}}
 catch(e){if(alive)errorCode.value=e instanceof MiniappError||e instanceof ProfileError?e.code:'save_error';}
 finally{if(alive)loading.value=false;}
}
async function save(){
 if(busy.value||loading.value||choosing.value||!changed.value||!booking.value)return;
 if(!validName(nickname.value)){errorCode.value='name_invalid';return;}
 if(changedContact.value&&!validContact(contact,true)){errorCode.value='booking_contact_invalid';return;}
 busy.value=true;errorCode.value='';partial.value=false;uni.hideKeyboard();
 try{
  assertProfileOwner(token,owner);
  if(normalizedName(nickname.value)!==originalName.value){const value=await saveNickname(token,owner,nickname.value);originalName.value=normalizedName(value.nickname);nickname.value=value.nickname;partial.value=true;}
  if(!alive)return;
  if(changedContact.value){assertProfileOwner(token,owner);const value=await studioCall<ContactProfile>('/auth/booking-profile',{...contact,version:booking.value.version},'',token,'PUT');assertProfileOwner(token,owner);if(value.owner_id!==owner)throw new ProfileError('account_login_required',401);booking.value=value;partial.value=true;}
  if(!alive)return;
  if(selectedAvatar.value){const value=await saveAvatar(token,owner,selectedAvatar.value);avatar.value=value.avatar;selectedAvatar.value='';partial.value=true;}
  if(alive){busy.value=false;uni.showToast({title:words('saved'),icon:'none'});close();}
 }catch(e){if(alive)errorCode.value=e instanceof ProfileError||e instanceof MiniappError?e.code:'save_error';}
 finally{if(alive)busy.value=false;}
}
watch(()=>user.token,()=>{sequence++;nickname.value='';avatar.value='';selectedAvatar.value='';booking.value=undefined;Object.assign(contact,emptyContact());owner='';token='';if(alive)uni.redirectTo({url:'/pages/auth/studio-login'});});
onLoad(()=>void load());onShow(()=>{if(token&&token!==user.token)close();});onUnload(()=>{alive=false;sequence++;selectedAvatar.value='';});
</script>
<template>
 <StudioShell id="studio-shell" fitted :language="language" :keyboard-open="keyboardOpen" :shell-style="shellStyle" @language="changeLanguage">
  <view class="studio-native-main studio-profile-form">
   <text class="studio-native-title">{{words('edit')}}</text>
   <view v-if="loading" class="studio-native-status"><view class="studio-native-progress"/><text>{{say(studioWords('booking','loading'))}}</text></view>
   <template v-else-if="owner">
    <view class="studio-profile-avatar-row"><button class="studio-avatar-edit" :open-type="nativeAvatar?'chooseAvatar':undefined" :disabled="busy||choosing" :aria-label="words('upload')" @chooseavatar="chooseAvatar" @tap="chooseFallback"><image v-if="preview&&!imageFailed" class="studio-native-avatar" :src="preview" mode="aspectFill" @error="imageFailed=true"/><view v-else class="studio-native-avatar"><StudioGlyph name="user" :size="30"/></view></button><view><text class="studio-plan-name">{{words('avatar')}}</text><button class="studio-native-link" :open-type="nativeAvatar?'chooseAvatar':undefined" :disabled="busy||choosing" @chooseavatar="chooseAvatar" @tap="chooseFallback"><view v-if="choosing" class="studio-native-progress"/>{{words('upload')}}</button></view></view>
    <label class="studio-native-field"><text>{{words('nickname')}}</text><view class="studio-native-input"><input v-model="nickname" type="nickname" :maxlength="40" :disabled="busy" :cursor-spacing="48" :aria-label="words('nickname')"/></view></label>
    <text class="studio-native-label">{{words('nickname_help')}}</text>
    <view class="studio-profile-booking"><text class="studio-native-subtitle">{{say(studioWords('booking','title'))}}</text><label class="studio-native-field"><text>{{say(studioWords('booking','name'))}}</text><view class="studio-native-input"><input v-model="contact.name" :maxlength="80" :disabled="busy" :cursor-spacing="48" :aria-label="say(studioWords('booking','name'))"/></view></label><view class="studio-profile-contact"><picker :range="contacts" range-key="label" :value="contactIndex" :disabled="busy" @change="methodChange"><view class="studio-contact-choice"><text>{{contacts[contactIndex].label}} ⌄</text></view></picker><view class="studio-native-input"><input v-model="contact.contact" :maxlength="180" :disabled="busy" :cursor-spacing="48" :aria-label="say(studioWords('visit',contacts[contactIndex].field))"/></view></view></view>
   </template>
   <text v-if="errorCode" class="studio-native-error" role="alert">{{partial?say(studioWords('booking','partial'))+' ':''}}{{error}}</text>
   <button v-if="errorCode==='booking_profile_changed'" class="studio-native-link" @tap="useLatest">{{say(studioWords('booking','use_latest'))}}</button><button v-if="errorCode&&!owner" class="studio-native-link" @tap="load">{{say(studioWords('booking','retry'))}}</button>
  </view>
  <template #actions><view class="studio-visit-actions"><button class="studio-native-link" :disabled="busy" @tap="close">{{words('cancel')}}</button><button class="studio-native-primary" :disabled="busy||loading||choosing||!changed||!booking" @tap="save"><view v-if="busy" class="studio-native-progress"/>{{words(busy?'saving':'save')}}</button></view></template>
 </StudioShell>
</template>
