<script setup lang="ts">
import { ref,useId,watch } from 'vue';
import { PhArrowRight,PhGift,PhX } from '@phosphor-icons/vue';
import { useRouter } from 'vue-router';
import { useStudioModal } from '../modal';
import { usePatchPromotion,promotionCopy as copy } from '../patch-promotion';
import { readSession,saveSession } from '../reservations';
import { isContentPreview } from '../preview-context';
import { say,formatCopy } from '../state';
import LiftTitle from './LiftTitle.vue';
const {promotion}=usePatchPromotion(),dialog=ref<HTMLDialogElement>(),heading=useId();
const modal=useStudioModal(dialog,'photo'),open=ref(false),router=useRouter();
const seen=new Set<string>();
function dismiss(){if(promotion.value)saveSession('puppy-patch-promo:'+promotion.value.campaign,true);open.value=false;}
watch(open,value=>value?modal.open():modal.close());
watch(promotion,value=>{
  if(!value?.enabled){open.value=false;return;}
  if(isContentPreview()||seen.has(value.campaign)||readSession('puppy-patch-promo:'+value.campaign))return;
  // Do not stack over an account or other modal opened while the request loads.
  if(document.querySelector('dialog[open]'))return;
  seen.add(value.campaign);open.value=true;
});
function book(){dismiss();void router.push({path:'/visit',query:{experience:'patch',step:'1'}});}
</script>
<template>
 <Teleport to="body"><dialog ref="dialog" class="modal-shell patch-launch-dialog" :aria-labelledby="heading" @cancel.prevent="dismiss">
  <div class="modal-shade" aria-hidden="true" @click="dismiss"/>
  <section class="modal-panel patch-launch-panel">
   <button type="button" class="icon-button patch-launch-close" :aria-label="say(copy.close)" autofocus @click="dismiss"><PhX/></button>
   <span class="patch-launch-icon" aria-hidden="true"><PhGift :size="30" weight="light"/></span>
   <LiftTitle :id="heading" as="h2" :text="say(copy.title)"/>
   <template v-if="promotion">
    <p class="patch-launch-intro">{{promotion.remaining>0?formatCopy(copy.intro,{v0:promotion.quota}):say(copy.exhausted)}}</p>
    <p class="patch-launch-bonus">{{say(copy.bonus)}}</p>
    <p class="patch-launch-count">{{formatCopy(copy.remaining,{v0:promotion.remaining,v1:promotion.quota})}}</p>
   </template>
   <button type="button" class="button button-primary" @click="book">{{say(copy.book)}}<PhArrowRight/></button>
  </section>
 </dialog></Teleport>
</template>
<style>
.modal-shell.patch-launch-dialog{position:fixed;inset:var(--visible-top,0px) 0 auto;width:100%;height:var(--visible-height,100dvh);max-width:none;max-height:none;padding:20px 0;margin:0;border:0;background:transparent;overflow:hidden}
.patch-launch-panel{position:relative;margin:auto;width:min(480px,calc(100vw - 32px));max-height:calc(var(--visible-height,100dvh) - 40px);overflow:auto;padding:38px 32px 32px;text-align:center;border:1px solid #e2e8eb;border-radius:24px;background:#fff;box-shadow:0 20px 70px #3449571c;pointer-events:auto}
.patch-launch-dialog[open]{display:flex;align-items:center;justify-content:center}
.patch-launch-close{position:absolute;right:10px;top:10px;min-width:44px;min-height:44px}
.patch-launch-icon{display:inline-grid;place-items:center;width:64px;height:64px;border-radius:50%;background:#edf4f8;color:#526c7b;margin-bottom:18px}
.patch-launch-panel h2{font-size:clamp(25px,5vw,32px);line-height:1.5;margin:0 0 20px}
.patch-launch-intro{font-size:17px;line-height:1.7;margin:0 0 8px}
.patch-launch-bonus{font-size:15px;line-height:1.6;margin:0}
.patch-launch-count{font-size:13px;color:#62737c;margin:16px 0 24px;font-variant-numeric:tabular-nums}
.patch-launch-panel>.button{width:100%;justify-content:space-between}
@media(max-width:420px){.patch-launch-panel{padding:32px 22px 24px}.patch-launch-panel h2{font-size:25px}.patch-launch-intro{font-size:16px}}
</style>
