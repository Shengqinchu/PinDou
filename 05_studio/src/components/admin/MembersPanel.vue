<script setup lang="ts">
import { computed,onBeforeUnmount,ref,watch } from 'vue';
import { useRoute } from 'vue-router';
import { PhArrowRight,PhArrowClockwise,PhWallet,PhCheck } from '@phosphor-icons/vue';
import { useDesk } from '../../admin';
import { CommerceError } from '../../commerce';
import { walletCopy as copy,duration,type WalletAccount,type WalletDetail,type WalletEntry,type WalletCategory } from '../../wallet';
import { say,formatCopy,hamiltonDate } from '../../state';
import { readSession,saveSession } from '../../reservations';
import SlideOver from '../SlideOver.vue';
import WalletBalances from '../WalletBalances.vue';
import WalletLedger from '../WalletLedger.vue';
import BookingContactFields from '../BookingContactFields.vue';
import { bookingProfileCopy as bookingCopy,contactDetails,emptyContact,contactMethodLabel,validContact,type BookingProfile } from '../../booking-profile';
const props=defineProps<{active:boolean}>();
const {request}=useDesk();const route=useRoute();
type Pending={owner:string;key:string;path:string;body:Record<string,unknown>};
const pending=ref<Pending|null>(readSession<Pending>('studio-wallet-pending-v1'));
const members=ref<WalletAccount[]>([]),total=ref(0),page=ref(1),search=ref(''),busy=ref(false),error=ref('');
const selected=ref(''),open=ref(false),data=ref<WalletDetail>(),ledgerPage=ref(1),category=ref<WalletCategory>('all');
const loading=ref(false),saving=ref(false),saveError=ref(''),saved=ref(false),showForm=ref(false);
const redemptionUse=ref<'visit'|'shop'>('visit'),noPromotion=ref(false);
const kind=ref('topup'),timeAmount=ref<number|''>(600),pointsAmount=ref<number|''>(0),redeemCad=ref<number|''>(1),bill=ref('');
const note=ref(''),effective=ref(hamiltonDate()),reservation=ref(''),privateNote=ref(''),noteVersion=ref(1),reverseEntry=ref<WalletEntry>();
const frozen=computed(()=>saving.value||!!pending.value);
const editingBooking=ref(false),bookingDraft=ref(emptyContact()),bookingVersion=ref(0);
function editBooking(){if(!data.value)return;bookingDraft.value=contactDetails(data.value.booking_profile);bookingVersion.value=data.value.booking_profile.version;editingBooking.value=true;}
async function saveBooking(){
 if(frozen.value||!data.value)return;
 if(!validContact(bookingDraft.value,true)){saveError.value=say(bookingCopy.incomplete);return;}
 const owner=selected.value;saving.value=true;saveError.value='';saved.value=false;
 try{const profile=await request<BookingProfile>(`/manage/members/${encodeURIComponent(owner)}/booking-profile`,{method:'PUT',body:JSON.stringify({...bookingDraft.value,version:bookingVersion.value})});if(owner===selected.value&&data.value){data.value.booking_profile=profile;editingBooking.value=false;saved.value=true;}await load();}
 catch(e){saveError.value=(e as Error).message;}finally{saving.value=false;}
}
let listSequence=0,detailSequence=0,debounce:ReturnType<typeof setTimeout>;
const kinds=['opening','topup','gift','usage','redeem','adjustment'];
const label=(value:string)=>say((copy as Record<string,string[]>)[value]);
async function load(){
  const seq=++listSequence;busy.value=true;error.value='';
  try{const result=await request<{items:WalletAccount[];total:number}>(`/manage/members?${new URLSearchParams({search:search.value,page:String(page.value)})}`);if(seq===listSequence){members.value=result.items;total.value=result.total;}}
  catch(e){if(seq===listSequence)error.value=(e as Error).message;}finally{if(seq===listSequence)busy.value=false;}
}
async function loadDetail(resetNote=false){
  if(!selected.value)return;
  const owner=selected.value,seq=++detailSequence;loading.value=true;
  try{const result=await request<WalletDetail>(`/manage/members/${encodeURIComponent(owner)}?page=${ledgerPage.value}&category=${category.value}`);if(seq!==detailSequence)return;data.value=result;if(resetNote){privateNote.value=result.account.staff_note||'';noteVersion.value=result.account.version;if(editingBooking.value){bookingDraft.value=contactDetails(result.booking_profile);bookingVersion.value=result.booking_profile.version;}}}
  catch(e){if(seq===detailSequence)saveError.value=(e as Error).message;}finally{if(seq===detailSequence)loading.value=false;}
}
async function inspect(owner:string){
  if(saving.value)return;
  if(pending.value)owner=pending.value.owner;
  selected.value=owner;data.value=undefined;ledgerPage.value=1;category.value='all';saved.value=false;saveError.value='';
  editingBooking.value=false;
  showForm.value=false;reverseEntry.value=undefined;note.value='';reservation.value=typeof route.query.booking==='string'?route.query.booking:'';effective.value=hamiltonDate();
  open.value=true;await loadDetail(true);
}
function setPending(value:Pending|null){pending.value=value;saveSession('studio-wallet-pending-v1',value);}
async function sendPending(){
  const action=pending.value;if(!action||saving.value)return;
  saving.value=true;saveError.value='';saved.value=false;
  try{
    const result=await request<WalletDetail>(action.path,{method:'POST',headers:{'Idempotency-Key':action.key},body:JSON.stringify(action.body)});
    setPending(null);data.value=result;ledgerPage.value=1;category.value='all';privateNote.value=result.account.staff_note||'';noteVersion.value=result.account.version;
    showForm.value=false;reverseEntry.value=undefined;note.value='';saved.value=true;await load();
  }catch(e){
    saveError.value=(e as Error).message;
    // A definite rejected request can be edited. An uncertain result retains its
    // exact key/body across a reload and can only be retried, never duplicated.
    if(e instanceof CommerceError&&e.status>=400&&e.status<500)setPending(null);
  }finally{saving.value=false;}
}
async function record(){
  if(frozen.value||!data.value)return;
  if(!reverseEntry.value&&kind.value==='redeem'&&!noPromotion.value){saveError.value=say(copy.wallet_promotion_confirmation_required);return;}
  const owner=data.value.account.owner_id;
  let path=`/manage/members/${encodeURIComponent(owner)}/transactions`;
  let body:Record<string,unknown>={version:data.value.account.version,note:note.value.trim()};
  if(reverseEntry.value){path=`/manage/members/${encodeURIComponent(owner)}/entries/${reverseEntry.value.id}/reverse`;}
  else{
    const m=Number(timeAmount.value||0),p=Number(pointsAmount.value||0);
    body={...body,kind:kind.value,minutes_delta:kind.value==='redeem'?0:kind.value==='usage'?-m:m,
      points_delta:kind.value==='redeem'?-Number(redeemCad.value)*100:['gift','opening','adjustment'].includes(kind.value)?p:0,
      effective_date:effective.value,reservation_id:reservation.value.trim(),
      ...(kind.value==='redeem'?{bill_cents:Math.round(Number(bill.value)*100),redemption_use:redemptionUse.value,no_promotion:noPromotion.value}:{})};
  }
  setPending({owner,key:crypto.randomUUID(),path,body});await sendPending();
}
async function saveNote(){
  if(frozen.value||!data.value)return;saving.value=true;saveError.value='';saved.value=false;
  try{const result=await request<WalletDetail>(`/manage/members/${encodeURIComponent(selected.value)}`,{method:'PATCH',body:JSON.stringify({version:noteVersion.value,staff_note:privateNote.value})});data.value=result;noteVersion.value=result.account.version;saved.value=true;await load();}
  catch(e){saveError.value=(e as Error).message;}finally{saving.value=false;}
}
function beginEntry(){showForm.value=true;noPromotion.value=false;redemptionUse.value='visit';reverseEntry.value=undefined;saved.value=false;saveError.value='';note.value='';}
function beginReverse(entry:WalletEntry){beginEntry();reverseEntry.value=entry;}
watch(kind,()=>{noPromotion.value=false;pointsAmount.value=0;timeAmount.value=['usage','adjustment','gift'].includes(kind.value)?0:600;});
watch(search,()=>{clearTimeout(debounce);debounce=setTimeout(()=>{page.value=1;void load();},300);});
watch([ledgerPage,category],()=>{if(open.value&&!saving.value)void loadDetail();});
watch(()=>[props.active,route.query.member],()=>{
  if(!props.active)return;void load();
  const target=pending.value?.owner||route.query.member;if(typeof target==='string')void inspect(target);
},{immediate:true});
onBeforeUnmount(()=>{listSequence++;detailSequence++;clearTimeout(debounce);});
defineExpose({refresh:load});
</script>
<template>
  <section class="member-desk">
    <header class="desk-page-heading"><div><h1>{{say(copy.members)}}</h1><p>{{say(copy.members_intro)}}</p></div><button class="desk-button secondary" :disabled="busy" @click="load"><PhArrowClockwise :class="{spinning:busy}"/>{{say(copy.refresh)}}</button></header>
    <p class="member-intro">{{say(copy.register_first)}}</p>
    <label class="desk-field member-search">{{say(copy.search)}}<input v-model.trim="search" type="search" maxlength="160"/></label>
    <p v-if="error" class="desk-error" role="alert">{{error}}</p>
    <p v-if="busy&&!members.length" role="status">{{say(copy.loading)}}</p><p v-else-if="!members.length" class="wallet-empty">{{say(copy.no_members)}}</p>
    <div class="member-list"><button v-for="member in members" :key="member.owner_id" class="member-row" @click="inspect(member.owner_id)"><PhWallet :size="24" weight="light"/><span><strong>{{member.booking_profile?.name||member.name}}</strong><small>{{member.email||member.owner_id}}</small><small v-if="member.booking_profile?.contact">{{contactMethodLabel(member.booking_profile.contact_method)}} · {{member.booking_profile.contact}}</small></span><span class="member-list-note">{{member.staff_note}}</span><span class="member-list-balance">{{duration(member.minutes)}}<small>{{formatCopy(copy.point_count,{v0:member.points})}}</small></span><PhArrowRight :size="18"/></button></div>
    <div v-if="total>30" class="wallet-pagination"><button :disabled="page===1||busy" @click="page--;load()">{{say(copy.previous)}}</button><span>{{formatCopy(copy.page,{v0:page,v1:total})}}</span><button :disabled="page*30>=total||busy" @click="page++;load()">{{say(copy.next)}}</button></div>
    <SlideOver v-model="open" :title="data?.account.name||say(copy.members)" :subtitle="data?.account.email||selected" :busy="saving">
      <p v-if="loading&&!data" role="status">{{say(copy.loading)}}</p>
      <p v-if="saveError" class="desk-error" role="alert">{{saveError}} <button class="desk-link" :disabled="frozen" @click="loadDetail(true)">{{say(copy.refresh)}}</button></p>
      <p v-if="saved" class="wallet-saved" role="status"><PhCheck/>{{say(copy.saved)}}</p>
      <template v-if="data">
        <section class="booking-profile-section"><h3>{{say(bookingCopy.title)}}</h3><div v-if="!editingBooking" class="booking-profile-summary"><div v-if="data.booking_profile.complete"><strong>{{data.booking_profile.name}}</strong><p>{{contactMethodLabel(data.booking_profile.contact_method)}} · {{data.booking_profile.contact}}</p></div><p v-else>{{say(bookingCopy.empty)}}</p><button type="button" class="text-link" :disabled="frozen" @click="editBooking">{{say(bookingCopy.edit)}}</button></div><form v-else @submit.prevent="saveBooking"><BookingContactFields v-model="bookingDraft" class="profile-contact" :required="false" :disabled="frozen"/><div class="booking-profile-actions"><button type="button" class="desk-button secondary" :disabled="frozen" @click="editingBooking=false">{{say(bookingCopy.cancel)}}</button><button class="desk-button primary" :disabled="frozen">{{say(bookingCopy.save)}}</button></div></form></section>
        <WalletBalances :account="data.account"/><p class="wallet-rule">{{say(copy.rules)}}</p>
        <p v-if="saving" role="status">{{say(copy.saving)}}</p>
        <div v-if="pending&&!saving" class="wallet-uncertain" role="alert"><p>{{say(copy.uncertain)}}</p><p>{{pending.body.note}}</p><button class="desk-button primary" :disabled="saving" @click="sendPending">{{say(copy.retry)}}</button></div>
        <button v-if="!showForm&&!pending" class="desk-button primary wallet-new" @click="beginEntry">{{say(copy.transaction)}}<PhArrowRight/></button>
        <form v-if="showForm&&!pending" class="wallet-form" @submit.prevent="record">
          <template v-if="reverseEntry"><h3>{{say(copy.reverse)}} · #{{reverseEntry.id}}</h3><p class="wallet-rule">{{say(copy.reverse_help)}}</p><WalletLedger :entries="[reverseEntry]"/></template>
          <template v-else>
            <label class="desk-field">{{say(copy.kind)}}<select v-model="kind" :disabled="frozen"><option v-for="key in kinds" :key="key" :value="key">{{label(key)}}</option></select></label>
            <div class="wallet-input-grid">
              <label v-if="kind!=='redeem'" class="desk-field">{{say(copy.time_amount)}}<input v-model.number="timeAmount" type="number" :min="kind==='adjustment'?-1000000:0" max="1000000" step="1" required :disabled="frozen"/></label>
              <label v-if="['opening','gift','adjustment'].includes(kind)" class="desk-field">{{say(copy.points_amount)}}<input v-model.number="pointsAmount" type="number" :min="kind==='adjustment'?-1000000:0" max="1000000" step="1" required :disabled="frozen"/></label>
              <template v-if="kind==='redeem'"><label class="desk-field">{{say(copy.redeem_cad)}}<input v-model.number="redeemCad" type="number" min="1" :max="data.account.redeemable_cad" step="1" required :disabled="frozen"/></label><label class="desk-field">{{say(copy.bill)}}<input v-model="bill" type="number" min="1" step="0.01" max="1000000" required :disabled="frozen"/></label></template>
            </div>
            <template v-if="kind==='redeem'"><label class="desk-field">{{say(copy.redemption_use)}}<select v-model="redemptionUse" :disabled="frozen"><option value="visit">{{say(copy.redeem_visit)}}</option><option value="shop">{{say(copy.redeem_shop)}}</option></select></label><label class="wallet-promotion-confirm"><input v-model="noPromotion" type="checkbox" required :disabled="frozen"/><span>{{say(copy.no_promotion)}}</span></label><p class="wallet-rule">{{say(copy.promotion_rule)}}</p></template>
            <p v-if="kind==='usage'" class="wallet-rule">{{say(copy.debit_help)}}</p><p v-if="kind==='adjustment'" class="wallet-rule">{{say(copy.adjust_help)}}</p>
            <label class="desk-field">{{say(copy.date)}}<input v-model="effective" type="date" :max="hamiltonDate()" required :disabled="frozen"/></label>
            <label class="desk-field">{{say(copy.reservation)}}<input v-model.trim="reservation" maxlength="64" :disabled="frozen"/></label>
          </template>
          <label class="desk-field">{{say(copy.reason)}}<textarea v-model="note" rows="3" minlength="1" maxlength="600" required :disabled="frozen"/></label>
          <div class="wallet-form-actions"><button type="button" class="desk-button secondary" :disabled="frozen" @click="showForm=false">{{say(copy.cancel)}}</button><button class="desk-button primary" :disabled="frozen">{{saving?say(copy.saving):say(copy.save)}}<PhCheck/></button></div>
        </form>
        <details class="member-private-note" open><summary>{{say(copy.private_note)}}</summary><form @submit.prevent="saveNote"><label class="desk-field">{{say(copy.private_note)}}<textarea v-model="privateNote" rows="3" maxlength="1500" :disabled="frozen"/></label><button class="desk-button secondary" :disabled="frozen">{{say(copy.save_note)}}</button></form></details>
        <div class="wallet-history-tabs" role="group" :aria-label="say(copy.all_history)"><button v-for="type in (['all','time','points'] as const)" :key="type" :aria-pressed="category===type" :disabled="loading" @click="ledgerPage=1;category=type">{{say(type==='all'?copy.all_history:type==='time'?copy.time_history:copy.point_history)}}</button></div>
        <WalletLedger :entries="data.entries" admin :busy="frozen" @reverse="beginReverse"/>
        <div v-if="data.total>30" class="wallet-pagination"><button :disabled="ledgerPage===1||loading" @click="ledgerPage--">{{say(copy.previous)}}</button><span>{{formatCopy(copy.page,{v0:ledgerPage,v1:data.total})}}</span><button :disabled="ledgerPage*30>=data.total||loading" @click="ledgerPage++">{{say(copy.next)}}</button></div>
      </template>
      <template #footer><button class="desk-button secondary" :disabled="saving" @click="open=false">{{say(copy.close)}}</button></template>
    </SlideOver>
  </section>
</template>
