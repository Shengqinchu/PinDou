<script setup lang="ts">
import { gt } from './i18n';
import { computed,onBeforeUnmount,onMounted,ref,watch } from 'vue';
import { useRoute } from 'vue-router';
import { useAuthStore } from './stores/auth';
import { useGenerationStore,isResultSizePreset,isGenerationStylePreset } from './stores/generation';
import { getWalletProfile } from './api';
import type { User } from './api/types';
import { accountUser,refreshAccount } from '../../05_studio/src/account';
import { say,formatCopy } from '../../05_studio/src/state';
import { contentModule } from '../../05_studio/src/content-store';
import words from '../../05_studio/src/content/generator-shell.json';
import PricingModal from './components/PricingModal.vue';
import InfoTip from '../../05_studio/src/components/InfoTip.vue';
import { restoreGeneratorDraft,persistGeneratorDraft } from './draft';
import './styles/studio.css';
const copy=contentModule('generator-shell',words),auth=useAuthStore(),generation=useGenerationStore(),route=useRoute();
const ready=ref(false),wallet=ref<User>(),pricing=ref(false);let active=true,revision=0;
const editor=computed(()=>route.meta.toolEditor),balance=computed(()=>wallet.value||auth.user);
const points=computed(()=>balance.value?.is_unlimited_account?say(copy.unlimited):String(balance.value?.ai_points_balance??balance.value?.paid_credits??0));
const standard=computed(()=>{const p=balance.value;if(p?.is_unlimited_account||(p?.membership_expires_at&&Date.parse(p.membership_expires_at)>Date.now()))return say(copy.unlimited);return formatCopy(copy.units,{v0:p?.normal_trial_remaining??p?.free_credits_remaining??0});});
async function sync(){const n=++revision;auth.syncFromStorage();try{const result=await getWalletProfile();if(n===revision){wallet.value=result;if(auth.isLoggedIn)auth.applyUser(result);}}catch{}}
watch(accountUser,(user,old)=>{
 auth.syncFromStorage();if(old?.id&&old.id!==user?.id){wallet.value=undefined;generation.resetOwner();}
 void sync();
});
onMounted(async()=>{
 await refreshAccount().catch(()=>false);auth.syncFromStorage();
 generation.ensureOwner();
 const saved=await restoreGeneratorDraft(accountUser.value?.id||'guest');
 if(active&&saved&&!generation.sourceFile){generation.sourceFile=saved.file;generation.jobId=saved.jobId||'';generation.submitted=!!saved.submitted;generation.completedId=saved.completedId||'';if(isResultSizePreset(saved.size))generation.selectedSize=saved.size;generation.generationMode=saved.mode==='script'?'script':'ai';if(isGenerationStylePreset(saved.style))generation.selectedStyle=saved.style;}
 if(active){ready.value=true;void sync();window.addEventListener('focus',sync);}
});
watch(()=>generation.isGenerating,(busy,previous)=>{if(!busy&&previous)void sync();});
onBeforeUnmount(()=>{active=false;revision++;window.removeEventListener('focus',sync);});
</script>
<template>
 <section class="generator-workspace" :class="{'generator-editor-workspace':editor}">
  <div v-if="!editor" class="generator-heading"><div><h1>{{ gt(say(copy.title)) }}</h1><nav :aria-label="gt(say(copy.title))"><RouterLink to="/tools" :class="{selected:route.name==='tools-upload'||route.name==='tools-loading'||route.name==='tools-result'}">{{ gt(say(copy.create)) }}</RouterLink><RouterLink to="/tools/works">{{ gt(say(copy.works)) }}</RouterLink><RouterLink to="/tools/tutorial">{{ gt(say(copy.tutorial)) }}</RouterLink></nav></div><div class="generator-allowance"><button type="button" :aria-label="gt(say(copy.wallet))" @click="pricing=true"><span>{{ gt(say(copy.credits)) }} <strong>{{ gt(points) }}</strong></span><span>{{ gt(say(copy.passes)) }} <strong>{{ gt(standard) }}</strong></span></button><InfoTip :label="say(copy.wallet)"><p>{{ gt(say(copy.credit_help)) }}</p></InfoTip></div></div>
  <div v-if="generation.currentArtworkId&&!['tools-loading','tools-result','tools-editor'].includes(String(route.name))" class="generator-ready"><span>{{ gt(say(copy.ready)) }}</span><RouterLink :to="'/tools/result/'+generation.currentArtworkId">{{ gt(say(copy.view_result)) }}</RouterLink></div>
  <RouterView v-if="ready" v-slot="{Component}"><component :is="Component" :key="(accountUser?.id||'guest')+':'+String(route.name)+':'+String(route.params.id||'')"/></RouterView><p v-else role="status">{{ gt(say(copy.loading)) }}</p>
  <PricingModal :open="pricing" @close="pricing=false" @success="sync"/>
 </section>
</template>
