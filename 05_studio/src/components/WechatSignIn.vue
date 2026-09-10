<script setup lang="ts">
import { onMounted,ref } from 'vue';
import { useRoute } from 'vue-router';
import { PhWechatLogo } from '@phosphor-icons/vue';
import { commerceApi } from '../commerce';
import { wechatCopy as copy } from '../wechat';
import { profileCopy } from '../profile';
import { say } from '../state';
import InfoTip from './InfoTip.vue';
import SlideOver from './SlideOver.vue';
import WechatQr from './WechatQr.vue';
defineProps<{linking?:boolean;compact?:boolean}>();
const available=ref(false),linked=ref(false),open=ref(false);
const route=useRoute();
async function refresh(){try{const options=await commerceApi<{wechat:boolean;wechat_provider?:string;miniapp_available?:boolean}>('/auth/options');const native=options.miniapp_available&&(options.wechat_provider==='miniapp'||route.query.wechat_provider==='miniapp');available.value=options.wechat||!!native;if(available.value)linked.value=(await commerceApi<{linked:boolean}>(native?'/auth/wechat/miniapp/binding':'/auth/wechat/binding')).linked;}catch{available.value=false;}}
function done(){open.value=false;void refresh();}
onMounted(refresh);
</script>
<template>
 <div v-if="available" class="wechat-signin" :class="{'wechat-compact':compact}"><div v-if="linked" class="wechat-bound"><span><PhWechatLogo :size="18"/>{{say(copy.linked)}}</span><InfoTip :label="say(profileCopy.wechat_help)"><p>{{say(profileCopy.wechat_profile_help)}}</p></InfoTip></div><button v-else class="wechat-link text-link" type="button" @click="open=true"><PhWechatLogo :size="18"/>{{say(copy.link)}}</button></div>
 <SlideOver v-model="open" :title="say(copy.link)"><WechatQr v-if="open" linking @done="done"/></SlideOver>
</template>
