import { computed,onBeforeUnmount,onMounted,reactive,ref,watch } from 'vue';
import { useRoute,useRouter } from 'vue-router';
import { commerceApi,CommerceError } from '../commerce';
import { ensureCustomer,closeAccount,accountUser } from '../account';
import { isContentPreview } from '../preview-context';
import { locale,say } from '../state';
import { reservationDraft as draft,readSession,saveSession,validSelection,minutes,type Reservation,type ReservationPayload,type ReservationCalendar } from '../reservations';
import { copy,words } from './copy';

export function useVisitFlow(){
 const route=useRoute(),router=useRouter();
 const saved=readSession<{step:number}>('puppy-visit-flow-v1');
 const attempt=ref(readSession<{key:string;body:ReservationPayload}>('puppy-reservation-attempt-v1'));
 const step=ref(attempt.value?2:0),direction=ref(1);
 const calendar=ref<ReservationCalendar|null>(null),loading=ref(true),sending=ref(false),checkingAccount=ref(false),error=ref(''),loadError=ref('');
 const locked=computed(()=>sending.value||checkingAccount.value||!!attempt.value);
 const offer=computed(()=>calendar.value?.offers?.find(o=>o.id===draft.offer));
 const firstReady=computed(()=>draft.booking.plan==='hourly'||draft.booking.plan==='day');
 if(!attempt.value){delete draft.offer;delete draft.offer_revision;}
 const canOmitDetails=ref(false);let contactSequence=0;
 async function loadContactContext(){
  const id=accountUser.value?.id,version=++contactSequence;if(!id){canOmitDetails.value=false;return;}
  try{const result=await commerceApi<{can_omit_details:boolean}>('/auth/reservation-context');if(alive&&version===contactSequence&&id===accountUser.value?.id)canOmitDetails.value=result.can_omit_details;}catch{/* The server rechecks eligibility at submission. */}
 }
 const selected=computed(()=>!loading.value&&!loadError.value&&validSelection(calendar.value,draft.booking)&&(!draft.offer||(!!offer.value&&draft.offer_revision===offer.value.revision&&draft.booking.guests===offer.value.guests&&minutes(draft.booking.end)-minutes(draft.booking.start)===offer.value.minutes&&draft.booking.date<=offer.value.until)));
 let sequence=0,alive=true,restored=false,timer:ReturnType<typeof setInterval>;
 const requestedStep=()=>{const value=Number(route.query.step);return value>=1&&value<=3?value-1:saved?.step||0;};
 function persist(){saveSession('puppy-visit-flow-v1',{step:step.value});}
 function safeStep(value:number){return attempt.value?2:!firstReady.value?0:value>=2&&!selected.value?1:Math.min(2,Math.max(0,value));}
 async function navigate(value:number,replace=false){
  if(locked.value)return;
  if(value>0&&!firstReady.value){error.value=say(copy.choose_first);return;}
  if(value>1&&!selected.value){error.value=say(copy.choose_available);return;}
  direction.value=value>=step.value?1:-1;step.value=value;persist();
  if(!isContentPreview())await router[replace?'replace':'push']({query:{...route.query,step:String(value+1)}});
 }
 async function load(){
  const revision=++sequence;loading.value=true;loadError.value='';
  try{
   const data=await commerceApi<ReservationCalendar>('/reservation-calendar?guests='+(Number.isInteger(draft.booking.guests)&&draft.booking.guests>0?draft.booking.guests:1));
   if(!alive||revision!==sequence)return false;calendar.value=data;loading.value=false;
   if(!attempt.value){
    if(draft.offer&&(!offer.value||offer.value.revision!==draft.offer_revision)){
     delete draft.offer;delete draft.offer_revision;draft.booking.plan='';draft.booking.start='';draft.booking.end='';error.value=say(copy.offer_changed);step.value=0;
    }else if(draft.booking.start&&!selected.value){draft.booking.start='';draft.booking.end='';error.value=say(words.your_previous_time_is_no_longer_available_9b5681);if(step.value===2)step.value=1;}
   }
   if(!restored){restored=true;step.value=safeStep(requestedStep());}
   persist();return true;
  }catch(e){if(alive&&revision===sequence)loadError.value=say(copy.calendar_error);return false;}
  finally{if(alive&&revision===sequence)loading.value=false;}
 }
 function clearTime(){draft.booking.start='';draft.booking.end='';}
 function choosePlan(plan:'hourly'|'day'){if(locked.value)return;delete draft.offer;delete draft.offer_revision;if(draft.booking.plan!==plan){draft.booking.plan=plan;clearTime();}error.value='';}
 function chooseGuests(value:number){if(locked.value||!Number.isInteger(value)||value<1||value>99)return;draft.booking.guests=value;error.value='';}
 function chooseInterval(value:{date:string;start:string;end:string}){if(locked.value)return;Object.assign(draft.booking,value);error.value='';}
 function back(){void navigate(step.value-1);}
 async function submit(){
  if(sending.value||checkingAccount.value||isContentPreview())return;
  if(step.value<2){await navigate(step.value+1);return;}
  if(!attempt.value&&!selected.value){error.value=say(copy.choose_available);return;}
  checkingAccount.value=true;
  try{if(!await ensureCustomer()||!alive)return;}
  catch(e){error.value=(e as Error).message;return;}
  finally{checkingAccount.value=false;}
  if(!attempt.value){
   if(!await load()||!alive||!selected.value){if(alive)step.value=firstReady.value?1:0;return;}
   const body:ReservationPayload={booking:{...draft.booking},name:draft.name,contact_method:draft.contact_method,contact:draft.contact,notes:draft.notes,locale:locale.value,website:''};
   if(offer.value){body.offer=offer.value.id;body.offer_revision=offer.value.revision;}
   attempt.value={key:crypto.randomUUID(),body};saveSession('puppy-reservation-attempt-v1',attempt.value);
  }
  const request=attempt.value;sending.value=true;error.value='';
  try{
   const receipt=await commerceApi<Reservation>('/reservations',{method:'POST',headers:{'Idempotency-Key':request.key},body:JSON.stringify(request.body)});
   saveSession('puppy-reservation-attempt-v1',null);saveSession('puppy-last-reservation',receipt.id);saveSession('puppy-visit-flow-v1',null);
   if(alive){attempt.value=null;clearTime();delete draft.offer;delete draft.offer_revision;await router.push('/reservation/'+receipt.id);}
  }catch(e){
   if(!alive)return;error.value=(e as Error).message;
   if(e instanceof CommerceError&&e.status>=400&&e.status<500&&!['reservation_request_changed','reservation_session_missing','account_login_required'].includes(e.code||'')){
    attempt.value=null;saveSession('puppy-reservation-attempt-v1',null);if(e.status===409||e.code?.startsWith('reservation_offer'))await load();
   }
  }finally{if(alive)sending.value=false;}
 }
 function visible(){if(!document.hidden&&!locked.value&&!loading.value)void load();}
 watch(()=>draft.booking.guests,()=>{if(!locked.value)void load();});
 watch(()=>accountUser.value?.id,()=>{canOmitDetails.value=false;void loadContactContext();},{immediate:true});
 watch(step,value=>{if(value===2)void loadContactContext();});
 watch(()=>route.query.step,()=>{if(!restored||locked.value)return;const value=safeStep(requestedStep());direction.value=value>=step.value?1:-1;step.value=value;persist();});
 onMounted(()=>{void load();timer=setInterval(visible,60000);window.addEventListener('pageshow',visible);window.addEventListener('focus',visible);document.addEventListener('visibilitychange',visible);});
 onBeforeUnmount(()=>{alive=false;sequence++;clearInterval(timer);window.removeEventListener('pageshow',visible);window.removeEventListener('focus',visible);document.removeEventListener('visibilitychange',visible);closeAccount();});
 return reactive({draft,step,direction,calendar,loading,sending,checkingAccount,error,loadError,attempt,locked,offer,canOmitDetails,firstReady,selected,load,navigate,choosePlan,chooseGuests,chooseInterval,back,submit});
}
export type VisitFlow=ReturnType<typeof useVisitFlow>;
