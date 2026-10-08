<script setup lang="ts">
import LiftTitle from '../components/LiftTitle.vue';
import { PhClock,PhSun,PhFlower } from '@phosphor-icons/vue';
import { patchCopy } from '../patch-reservations';
import { computed } from 'vue';
import { say,formatCopy } from '../state';
import { usePatchPromotion,promotionCopy } from '../patch-promotion';
import { copy,words,prices } from './copy';
import MoneyText from '../components/MoneyText.vue';
import InfoTip from '../components/InfoTip.vue';
import type { VisitFlow } from './useVisitFlow';
defineProps<{flow:VisitFlow}>();
const {promotion}=usePatchPromotion();
// Presentation only: the owner's copy stays whole for the mini program, which
// shows the same keys as plain lines.
function splitOffer(text:string){
 const at=text.includes(' · ')?text.indexOf(' · '):text.lastIndexOf(' ');
 return at>0?{name:text.slice(0,at),until:text.slice(at).replace(/^\s*·?\s*/,'')}:{name:text,until:''};
}
function splitPrice(text:string){
 const match=text.match(/^(.*?)[\s·]*((?:CAD|CNY)\s*\d[\d.,]*|\d[\d.,]*\s*(?:CAD|CNY))$/);
 return match?{label:match[1],price:match[2]}:{label:text,price:''};
}
function splitEmphasis(text:string){
 const at=text.search(/[，,:：]/);
 return at>0?{lead:text.slice(0,at+1)+(/[,:]/.test(text[at])?' ':''),strong:text.slice(at+1).trim()}:{lead:'',strong:text};
}
const offer=computed(()=>({...splitOffer(say(copy.holiday_offer_title)),board:splitPrice(say(copy.holiday_new_guests)),group:splitEmphasis(say(copy.holiday_bring_friends))}));
</script>
<template>
 <div class="visit-stage-title"><LiftTitle as="h2" :text="say(copy.experience)"/></div>
 <fieldset class="visit-plans"><legend class="sr-only">{{say(copy.experience)}}</legend>
  <label :class="{selected:flow.draft.booking.plan==='hourly'}"><input type="radio" name="visit-plan" value="hourly" :checked="flow.draft.booking.plan==='hourly'" @change="flow.choosePlan('hourly')"/><i class="visit-plan-dot" aria-hidden="true"/><PhClock/><strong>{{say(words.by_the_hour_5300b2)}}</strong><span>{{say(words.at_least_two_hours_9f144b)}}</span><div><MoneyText :text="'CAD '+prices.hourly"/><small>{{say(words.hour_person_7ea78f)}}</small></div></label>
  <label :class="{selected:flow.draft.booking.plan==='day'}"><input type="radio" name="visit-plan" value="day" :checked="flow.draft.booking.plan==='day'" @change="flow.choosePlan('day')"/><i class="visit-plan-dot" aria-hidden="true"/><PhSun/><strong>{{say(words.a_day_of_making_01d6e2)}}</strong><span>{{say(copy.day_until_close)}}</span><div><MoneyText :text="'CAD '+prices.day_one"/><small>{{say(words.one_guest_684bef)}}</small></div><dl class="visit-day-prices"><div><dt>{{say(copy.two)}}</dt><dd><MoneyText :text="'CAD '+prices.day_two"/></dd></div><div><dt>{{say(copy.three)}}</dt><dd><MoneyText :text="'CAD '+prices.day_three"/></dd></div></dl></label>
  <label :class="{selected:flow.draft.booking.plan==='patch'}"><input type="radio" name="visit-plan" value="patch" :checked="flow.draft.booking.plan==='patch'" @change="flow.choosePlan('patch')"/><i class="visit-plan-dot" aria-hidden="true"/><PhFlower/><strong>{{say(patchCopy.patch)}}</strong><span>{{say(patchCopy.description)}}</span><span v-if="promotion?.enabled" class="visit-patch-promotion"><b>{{say(promotionCopy.launch)}}</b><span>{{say(promotion.remaining>0?promotionCopy.card:promotionCopy.exhausted)}} <small>{{formatCopy(promotionCopy.remaining,{v0:promotion.remaining,v1:promotion.quota})}}</small></span><span>{{say(promotionCopy.bonus)}}</span></span></label>
 <div class="visit-promotions visit-combined-offers">
  <article class="visit-limited-offer" :aria-label="say(copy.limited_badge)+' · '+say(copy.holiday_offer_title)">
   <div class="visit-limited-top"><span class="visit-limited-badge"><i aria-hidden="true"/>{{say(copy.limited_badge)}}</span><span v-if="offer.until" class="visit-limited-until">{{offer.until}}</span></div>
   <h3 class="visit-limited-title" aria-hidden="true"><span v-for="(char,i) in Array.from(offer.name)" :key="i" :style="{'--hop':i}">{{char}}</span></h3>
   <p class="visit-limited-row"><span>{{offer.board.label}}</span><strong v-if="offer.board.price"><MoneyText :text="offer.board.price"/></strong></p>
   <p class="visit-limited-row visit-limited-group"><span>{{offer.group.lead}}<b>{{offer.group.strong}}</b></span></p>
  </article>
  <article class="visit-prepaid"><div class="visit-offer-heading"><h3>{{say(copy.prepaid_title)}}</h3><InfoTip :label="say(copy.prepaid_details)"><p>{{say(words.prepay_at_least_10_hours_and_at_8815bf)}}</p></InfoTip><strong><MoneyText :text="say(words.ca7_hour_c87a20)"/></strong></div></article>
 </div>
 </fieldset>
</template>
<style>
/* One informational offer card shares the same grid as the three choices. */
.visit-plans>.visit-combined-offers{display:flex;flex-direction:column;gap:0;margin:0;background:#f3f8fb;border:1px solid #c6d8e3;border-radius:14px;min-width:0;padding:14px 18px}
.visit-plans .visit-combined-offers>article{border:0;border-radius:0;padding:0;background:transparent}
.visit-plans .visit-combined-offers>article+article{border-top:1px solid #d9e6ee;margin-top:auto;padding-top:10px}
.visit-combined-offers h3{margin-bottom:6px}
.visit-combined-offers strong{font-size:22px}
.visit-offer-heading{display:flex;align-items:center;gap:3px;min-width:0}
.visit-offer-heading{flex-wrap:wrap}.visit-offer-heading h3{margin:0}.visit-offer-heading>strong{margin-left:auto;white-space:nowrap}
.visit-limited-offer{padding-bottom:10px!important}
.visit-limited-top{display:flex;align-items:center;justify-content:space-between;gap:10px}
.visit-limited-badge{display:inline-flex;align-items:center;gap:6px;padding:3px 10px 3px 8px;border-radius:999px;background:#e2eef6;color:#4b6a80;font-size:12px;font-weight:500;letter-spacing:.04em}
.visit-limited-badge i{position:relative;width:6px;height:6px;border-radius:50%;background:#688297}
.visit-limited-badge i:after{content:"";position:absolute;inset:0;border-radius:50%;background:#688297;animation:visit-limited-pulse 2.4s cubic-bezier(.4,0,.2,1) infinite}
.visit-limited-until{font-size:12px;color:#4b6a80;font-variant-numeric:tabular-nums;white-space:nowrap}
.visit-combined-offers h3.visit-limited-title{margin:8px 0 6px;font-family:var(--chinese-display);font-size:22px;font-weight:400;line-height:1.35;letter-spacing:.015em;color:var(--ink)}
.visit-limited-title span{display:inline-block;white-space:pre;animation:visit-limited-hop 4.2s cubic-bezier(.4,0,.2,1) infinite;animation-delay:calc(var(--hop) * 90ms)}
.visit-combined-offers .visit-limited-row{display:flex;align-items:baseline;justify-content:space-between;gap:12px;margin:4px 0 0;font-size:13px;line-height:1.55;color:var(--ink);overflow-wrap:break-word}
.visit-combined-offers .visit-limited-row strong{font-size:24px;font-weight:400;white-space:nowrap}
.visit-limited-group b{font-weight:600;color:#3f6680}
.visit-combined-offers .visit-prepaid h3{margin:0;font-size:12px;font-weight:400;line-height:1;color:var(--muted)}
.visit-combined-offers .visit-prepaid .visit-offer-heading{align-items:center}
.visit-combined-offers .visit-prepaid strong{font-size:18px}
@keyframes visit-limited-hop{0%,14%,100%{transform:translateY(0)}5%{transform:translateY(-4px)}9%{transform:translateY(0)}11%{transform:translateY(-1.5px)}}
@keyframes visit-limited-pulse{0%{transform:scale(1);opacity:.55}70%,100%{transform:scale(2.6);opacity:0}}
.visit-combined-offers .info-tip-trigger{min-width:36px;min-height:36px}
.visit-plans label>.visit-patch-promotion{display:flex;flex-direction:column;gap:2px;min-height:0;margin-top:7px;padding-top:9px;border-top:1px solid #dfe8ed;font-size:12px;line-height:1.5;color:#536b78}
.visit-patch-promotion b{font-weight:600}.visit-patch-promotion small{font-size:inherit;white-space:nowrap;font-variant-numeric:tabular-nums}
.visit-flow-page[data-step="1"]{height:auto;min-height:min(1100px,calc(var(--visible-height) - var(--visit-header-height,80px)))}
.visit-flow-page[data-step="1"] .visit-scroll{overflow:visible;overscroll-behavior:auto}
@media(min-width:701px){
 .visit-flow-page[data-step="1"]{gap:10px;padding-top:18px}
 .visit-flow-page[data-step="1"] .visit-stage-title{margin-bottom:10px}
 .visit-flow-page[data-step="1"] .visit-plans{gap:12px}
 .visit-flow-page[data-step="1"] .visit-plans>label{padding:14px 18px;gap:5px}
 .visit-flow-page[data-step="1"] .visit-plans label>div{font-size:28px}
 .visit-flow-page[data-step="1"] .visit-plans label>span{font-size:13px}
 .visit-flow-page[data-step="1"] .visit-plans strong{font-size:17px}
 .visit-flow-page[data-step="1"] .visit-combined-offers .visit-limited-row strong{font-size:26px}
 .visit-flow-page[data-step="1"] .visit-combined-offers .visit-prepaid strong{font-size:19px}
 .visit-flow-page[data-step="1"] .visit-combined-offers p{font-size:13px;line-height:1.5}
}
@media(min-width:1400px) and (min-height:850px){.visit-plans>.visit-combined-offers{border-radius:18px}}
@media(min-width:701px) and (max-height:730px){.visit-flow-page[data-step="1"]{padding-top:10px;gap:6px}.visit-flow-page[data-step="1"] .visit-plans>label{padding-block:11px}}
@media(max-width:700px){.visit-flow-page .visit-plans{grid-template-columns:1fr}.visit-flow-page .visit-plans>label{padding:16px}.visit-flow-page .visit-plans label>span{min-height:0;font-size:13px}.visit-plans>.visit-combined-offers{padding:16px}.visit-combined-offers p{font-size:12px}}
</style>
