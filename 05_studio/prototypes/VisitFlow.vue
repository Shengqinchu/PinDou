<script setup lang="ts">
import { computed,nextTick,onMounted,reactive,ref,watch } from 'vue';
import { PhArrowLeft,PhArrowRight,PhCheck,PhClock,PhSun,PhUser,PhPencilSimple } from '@phosphor-icons/vue';
import LiftTitle from '../src/components/LiftTitle.vue';
import MoneyText from '../src/components/MoneyText.vue';
import BrandMark from '../src/components/BrandMark.vue';
import { locale,say,prettyDate } from '../src/state';
import visit from '../src/content/pages-Visit.json';
import rates from '../src/content/experience-rates.json';
import { validSelection,minutes,clock,type ReservationCalendar } from '../src/reservations';
import './visit-flow.css';
const t=(zh:string,en:string)=>locale.value==='zh'?zh:en;
const step=ref(0),direction=ref(1),completed=ref(false),duration=ref(120),selectedDate=ref(''),calendar=ref<ReservationCalendar>(),loadError=ref(''),loading=ref(false),error=ref(''),stage=ref<HTMLElement>();
const data=reactive({booking:{plan:'' as ''|'hourly'|'day',guests:1,date:'',start:'',end:''},name:'',contact_method:'wechat',contact:'',notes:'',consent:false});
const steps=computed(()=>[t('体验与人数','Experience & guests'),t('日期与时间','Date & time'),t('联系与确认','Contact & review')]);
const customHours=computed({get:()=>duration.value/60,set:value=>{duration.value=Number(value)*60;}});
const selected=computed(()=>validSelection(calendar.value||null,data.booking));
const firstReady=computed(()=>!!data.booking.plan&&data.booking.guests>0&&data.booking.guests<=(calendar.value?.max_guests_per_group||4));
const day=computed(()=>calendar.value?.days.find(d=>d.date===selectedDate.value));
const starts=computed(()=>day.value?.slots.filter(s=>validSelection(calendar.value||null,{...data.booking,date:day.value!.date,start:s.start,end:data.booking.plan==='day'?day.value!.close:clock(minutes(s.start)+duration.value)}))||[]);
const summary=computed(()=>[data.booking.plan?t(data.booking.plan==='hourly'?'按时体验':'全天体验',data.booking.plan==='hourly'?'By the hour':'A day of making'):t('尚未选择体验','Choose an experience'),t(`${data.booking.guests} 人`,`${data.booking.guests} guest${data.booking.guests===1?'':'s'}`),selected.value?`${prettyDate(data.booking.date)} · ${data.booking.start}–${data.booking.end}`:t('尚未选择时间','Choose a time')]);
async function refresh(){
 loading.value=true;loadError.value='';
 try{const response=await fetch('/studio-api/reservation-calendar?guests='+data.booking.guests);if(!response.ok)throw Error();calendar.value=await response.json();if(!selected.value){data.booking.start='';data.booking.end='';}}
 catch{loadError.value=t('时段暂时没有加载出来，请重试。','Times could not be loaded. Try again.');}finally{loading.value=false;}
}
async function go(next:number){
 if(next>0&&!firstReady.value){error.value=t('先选择一种体验和人数。','Choose an experience and guest count first.');return;}
 if(next>1&&!selected.value){error.value=t('先选择可预约的日期和时间。','Choose an available date and time first.');return;}
 error.value='';direction.value=next>=step.value?1:-1;step.value=next;completed.value=false;
 await nextTick();stage.value?.focus({preventScroll:true});
 if(window.innerWidth<760)document.querySelector('.flow-progress')?.scrollIntoView({block:'start',behavior:'auto'});
}
function date(date:string){selectedDate.value=date;data.booking.date=date;data.booking.start='';data.booking.end='';error.value='';}
function time(start:string){data.booking.start=start;data.booking.date=selectedDate.value;data.booking.end=data.booking.plan==='day'?day.value!.close:clock(minutes(start)+duration.value);error.value='';}
function submit(){if(step.value<2){void go(step.value+1);return;}if(!selected.value||!data.consent)return;completed.value=true;}
watch(()=>data.booking.plan,()=>{data.booking.start='';data.booking.end='';completed.value=false;});
watch(()=>data.booking.guests,()=>{completed.value=false;void refresh();});
watch(duration,()=>{if(data.booking.start){data.booking.end=clock(minutes(data.booking.start)+duration.value);if(!selected.value){data.booking.start='';data.booking.end='';}}});
onMounted(refresh);
</script>
<template>
 <div class="prototype-bar"><span>{{t('交互方案预览 · 使用本地示例时段，不提交真实预约','Design preview · Local sample times; no real booking is submitted')}}</span><a href="?motion=full">{{t('完整动效预览','Preview full motion')}}</a><button @click="locale=locale==='zh'?'en':'zh'">{{locale==='zh'?'English':'中文'}}</button></div>
 <header class="flow-brand"><BrandMark compact/><span>{{t('慢慢选，期待见到你。','Take your time. We look forward to seeing you.')}}</span></header>
 <main class="flow-shell">
  <header class="flow-heading"><LiftTitle :text="say(visit.come_make_something_f834ec)"/><p>{{say(visit.choose_your_time_and_group_size_once_a1fdf7)}}</p></header>
  <nav class="flow-progress" :aria-label="t('预约进度','Booking progress')"><ol><li v-for="(label,i) in steps" :key="i"><button type="button" :aria-current="step===i?'step':undefined" :disabled="i>step&&(i===1?!firstReady:!selected)" :class="{current:step===i,done:step>i}" @click="go(i)"><span class="flow-step-number"><PhCheck v-if="step>i"/><template v-else>{{String(i+1).padStart(2,'0')}}</template></span><span>{{label}}</span></button></li></ol><div class="flow-progress-track" aria-hidden="true"><i :style="{transform:`scaleX(${step/2})`}"/></div></nav>
  <div class="flow-body">
   <form class="flow-form" @submit.prevent="submit">
    <div class="flow-window"><Transition name="flow-page" mode="out-in" @after-enter="stage?.focus({preventScroll:true})"><section :key="step" ref="stage" class="flow-stage" tabindex="-1" :style="{'--flow-direction':direction}">
     <template v-if="step===0">
      <div class="flow-stage-title"><span>01 / 03</span><h2>{{t('先选一种体验','Choose your experience')}}</h2></div>
      <fieldset class="flow-plans"><legend class="sr-only">{{steps[0]}}</legend>
       <label :class="{selected:data.booking.plan==='hourly'}"><input v-model="data.booking.plan" type="radio" value="hourly" required/><PhClock/><strong>{{say(visit.by_the_hour_5300b2)}}</strong><span>{{say(visit.at_least_two_hours_9f144b)}}</span><b><MoneyText :text="'CAD '+rates.hourly"/></b><small>{{say(visit.hour_person_7ea78f)}}</small></label>
       <label :class="{selected:data.booking.plan==='day'}"><input v-model="data.booking.plan" type="radio" value="day" required/><PhSun/><strong>{{say(visit.a_day_of_making_01d6e2)}}</strong><span>{{t('从你选的时间，拼到当天闭店。','Make from your chosen arrival until closing.')}}</span><b><MoneyText :text="'CAD '+rates.day_one"/></b><small>{{say(visit.one_guest_684bef)}}</small><details @click.stop><summary>{{t('查看多人价格','Prices for groups')}}</summary><p>{{t('两人','Two guests')}} <MoneyText :text="'CAD '+rates.day_two"/><br/>{{t('三人','Three guests')}} <MoneyText :text="'CAD '+rates.day_three"/><br/>{{t('更多人数由店主确认','The host confirms prices for larger groups')}}</p></details></label>
      </fieldset>
      <fieldset class="flow-guests"><legend>{{t('这次几个人一起来？','How many are coming?')}}</legend><div><button v-for="n in (calendar?.max_guests_per_group||4)" :key="n" type="button" :aria-pressed="data.booking.guests===n" @click="data.booking.guests=n"><PhUser/>{{t(`${n} 人`,`${n}`)}}</button></div></fieldset>
      <details class="flow-offers"><summary>{{t('查看储值与开学优惠','Prepaid hours & seasonal offers')}}</summary><div><article><strong><MoneyText :text="say(visit.ca7_hour_c87a20)"/></strong><p>{{say(visit.prepay_at_least_10_hours_and_at_8815bf)}}</p></article><article><strong><MoneyText :text="'CAD '+rates.school_two_four_hours"/></strong><p>{{say(visit.four_hours_of_making_for_two_8bb2b0)}}</p><strong><MoneyText :text="'CAD '+rates.school_card_holder"/></strong><p>{{say(visit.bead_cardholder_package_no_makingtime_limit_92105b)}}</p></article></div><small>{{say(visit.for_information_only_this_is_not_a_09a580)}}</small></details>
     </template>
     <template v-else-if="step===1">
      <div class="flow-stage-title"><span>02 / 03</span><h2>{{t('挑一个合适的时间','Find a time that suits you')}}</h2></div>
      <p class="flow-inline-summary">{{summary[0]}} · {{summary[1]}}<button type="button" @click="go(0)">{{t('修改','Edit')}}</button></p>
      <fieldset class="flow-dates"><legend>{{t('未来两周','The next two weeks')}}</legend><div><button v-for="d in calendar?.days" :key="d.date" type="button" :disabled="d.closed||loading" :aria-pressed="selectedDate===d.date" :aria-label="prettyDate(d.date)" @click="date(d.date)"><span>{{new Intl.DateTimeFormat(locale==='zh'?'zh-CN':'en-CA',{weekday:'short'}).format(new Date(d.date+'T12:00:00'))}}</span><strong>{{d.date.slice(8)}}</strong><small>{{d.closed?t('休息','Closed'):d.date.slice(5,7)+'/'+d.date.slice(8)}}</small></button></div></fieldset>
      <fieldset v-if="selectedDate&&data.booking.plan==='hourly'" class="flow-duration"><legend>{{t('想拼多久？','How long would you like?')}}</legend><div><button v-for="n in [120,150,180,210,240]" :key="n" type="button" :aria-pressed="duration===n" @click="duration=n">{{t(`${n/60} 小时`,`${n/60}h`)}}</button></div><details><summary>{{t('其他时长','Other duration')}}</summary><label>{{t('小时','Hours')}}<input v-model.number="customHours" type="number" min="2" max="24" step="0.5"/></label></details></fieldset>
      <fieldset v-if="selectedDate" class="flow-times"><legend>{{t('几点到店？','When will you arrive?')}}<small v-if="data.booking.plan==='day'">{{t('当天闭店时间','Closes at')}} {{day?.close}}</small></legend><div><button v-for="s in starts" :key="s.start" type="button" :aria-pressed="data.booking.start===s.start" @click="time(s.start)">{{s.start}}</button></div><p v-if="!starts.length&&!loading">{{t('这一天没有符合条件的时段，可以换一天或缩短时长。','No times fit this selection. Choose another day or a shorter visit.')}}</p></fieldset>
      <p v-if="selected" class="flow-chosen" role="status"><PhCheck/>{{summary[2]}}</p>
      <p v-if="loading" role="status">{{t('正在查看时段…','Checking available times…')}}</p><p v-if="loadError" role="alert">{{loadError}}<button type="button" @click="refresh">{{t('重试','Retry')}}</button></p>
     </template>
     <template v-else>
      <div class="flow-stage-title"><span>03 / 03</span><h2>{{t('留下联系方式，核对一下','Your contact details & a final check')}}</h2></div>
      <div class="flow-review"><div><small>{{steps[0]}}</small><strong>{{summary[0]}} · {{summary[1]}}</strong><button type="button" @click="go(0)"><PhPencilSimple/>{{t('修改','Edit')}}</button></div><div><small>{{steps[1]}}</small><strong>{{summary[2]}}</strong><button type="button" @click="go(1)"><PhPencilSimple/>{{t('修改','Edit')}}</button></div></div>
      <div class="flow-contact"><label>{{say(visit.guest_name_e468f6)}}<input v-model.trim="data.name" autocomplete="name" required maxlength="80"/></label><label>{{say(visit.contact_method_73d70a)}}<select v-model="data.contact_method"><option value="wechat">{{say(visit.wechat_2941d2)}}</option><option value="email">{{say(visit.email_b6d15f)}}</option><option value="phone">{{say(visit.phone_ac7a62)}}</option></select></label><label class="flow-contact-wide">{{data.contact_method==='wechat'?say(visit.wechat_id_7a6e86):data.contact_method==='email'?say(visit.email_address_a61e0e):say(visit.phone_number_15447d)}}<input v-model.trim="data.contact" :type="data.contact_method==='email'?'email':data.contact_method==='phone'?'tel':'text'" required minlength="3" maxlength="180"/></label></div>
      <details class="flow-notes"><summary>{{say(visit.anything_you_would_like_us_to_know_eef3ab)}}</summary><textarea v-model="data.notes" :aria-label="say(visit.anything_you_would_like_us_to_know_eef3ab)" rows="2"/></details>
      <label class="flow-consent"><input v-model="data.consent" type="checkbox" required/><span>{{say(visit.i_agree_to_use_these_details_to_5469c9)}}</span></label>
      <p v-if="completed" class="flow-chosen" role="status"><PhCheck/>{{t('预览已走通。正式提交后将等待店主确认。','Preview complete. A real request would wait for the host to confirm.')}}</p>
     </template>
     <p v-if="error" class="flow-error" role="alert">{{error}}</p>
    </section></Transition></div>
    <footer class="flow-actions"><button v-if="step" class="flow-back" type="button" @click="go(step-1)"><PhArrowLeft/>{{t('上一步','Back')}}</button><span v-else class="flow-hint">{{t('共 3 步，选择会保留','3 steps. Your choices stay with you.')}}</span><button class="button button-primary" :disabled="loading||(step===0&&!firstReady)||(step===1&&!selected)||completed">{{step===0?t('下一步：选时间','Next: date & time'):step===1?t('下一步：确认信息','Next: contact & review'):say(visit.request_this_visit_611e11)}}<PhArrowRight/></button></footer>
   </form>
   <aside class="flow-summary"><span>{{t('这一次小小的期待','Your little plan')}}</span><h2>{{t('你的选择','Your visit')}}</h2><p>{{summary[0]}}</p><p>{{summary[1]}}</p><p>{{summary[2]}}</p><hr/><small>{{say(visit.your_request_will_wait_for_the_hosts_cd36bf)}}</small></aside>
  </div>
 </main>
</template>
