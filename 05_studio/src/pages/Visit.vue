<script setup lang="ts">
import { computed,nextTick,onBeforeUnmount,onMounted,ref,watch } from 'vue';
import { PhArrowLeft,PhArrowRight,PhArrowClockwise,PhCheck } from '@phosphor-icons/vue';
import LiftTitle from '../components/LiftTitle.vue';
import { accountCopy } from '../account';
import { say,formatCopy } from '../state';
import { copy,words,guestCount } from '../visit/copy';
import { useVisitFlow } from '../visit/useVisitFlow';
import StepExperience from '../visit/StepExperience.vue';
import StepTime from '../visit/StepTime.vue';
import StepContact from '../visit/StepContact.vue';
import '../visit/visit.css';
const flow=useVisitFlow(),page=ref<HTMLElement>(),scroller=ref<HTMLElement>(),stage=ref<HTMLElement>();
const steps=computed(()=>[say(copy.step_experience),say(copy.step_time),say(copy.step_contact)]);
let observer:ResizeObserver|undefined;
function measure(){const height=document.querySelector('.vision-header')?.getBoundingClientRect().height||0;page.value?.style.setProperty('--visit-header-height',height+'px');}
function focusStage(){if(scroller.value)scroller.value.scrollTop=0;stage.value?.focus({preventScroll:true});}
watch(()=>flow.step,async()=>{await nextTick();if(scroller.value)scroller.value.scrollTop=0;});
onMounted(()=>{measure();observer=new ResizeObserver(measure);const header=document.querySelector('.vision-header');if(header)observer.observe(header);});
onBeforeUnmount(()=>observer?.disconnect());
</script>
<template>
 <section ref="page" class="visit-flow-page" :data-step="flow.step+1">
  <header class="visit-flow-heading"><LiftTitle :text="say(words.come_make_something_f834ec)"/></header>
  <nav class="visit-progress" :aria-label="say(copy.progress)"><ol><li v-for="(label,i) in steps" :key="i"><button type="button" :disabled="flow.locked||(i>flow.step&&(i===1?!flow.firstReady:!flow.selected))" :aria-current="flow.step===i?'step':undefined" :class="{current:flow.step===i,done:flow.step>i}" @click="flow.navigate(i)"><span><PhCheck v-if="flow.step>i"/><template v-else>{{String(i+1).padStart(2,'0')}}</template></span>{{label}}</button></li></ol><div aria-hidden="true"><i :style="{transform:`scaleX(${flow.step/2})`}"/></div></nav>
  <form class="visit-flow-form" @submit.prevent="flow.submit">

   <div ref="scroller" class="visit-scroll"><fieldset class="visit-fields" :disabled="flow.locked"><Transition name="visit-step" mode="out-in" @before-leave="el=>(el as HTMLElement).inert=true" @after-enter="focusStage"><section :key="flow.step" ref="stage" class="visit-stage" tabindex="-1" :style="{'--visit-direction':flow.direction}"><StepExperience v-if="flow.step===0" :flow="flow"/><StepTime v-else-if="flow.step===1" :flow="flow"/><StepContact v-else :flow="flow"/></section></Transition></fieldset></div>
   <div class="visit-feedback" aria-live="polite"><p v-if="flow.loadError" role="alert">{{flow.loadError}}<button type="button" @click="flow.load">{{say(copy.retry)}}</button></p><p v-else-if="flow.error" role="alert">{{flow.error}}</p><p v-else-if="flow.attempt&&!flow.sending">{{say(words.your_submission_is_saved_recover_its_result_8504a5)}}</p><p v-else-if="flow.loading&&!flow.calendar">{{say(copy.checking)}}</p></div>
   <footer class="visit-actions"><button v-if="flow.step" type="button" class="visit-back" :disabled="flow.locked" @click="flow.back"><PhArrowLeft/>{{say(copy.back)}}</button><span v-else aria-hidden="true"/><button class="button button-primary" :disabled="flow.sending||flow.checkingAccount||(!flow.attempt&&(flow.loading||(flow.step===2&&flow.contactLoading)||(flow.step===0&&!flow.firstReady)||(flow.step>0&&!flow.selected)))">{{flow.checkingAccount?say(accountCopy.checking):flow.sending?say(words.sending_c40370):flow.attempt?say(words.recover_reservation_12c189):flow.step===0?say(copy.next_time):flow.step===1?say(copy.next_contact):say(words.request_this_visit_611e11)}}<PhArrowRight/></button></footer>
  </form>
 </section>
</template>
