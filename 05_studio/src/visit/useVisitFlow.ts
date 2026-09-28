import { computed,onBeforeUnmount,onMounted,reactive,ref,watch } from 'vue';
import { useRoute,useRouter } from 'vue-router';
import { commerceApi,CommerceError } from '../commerce';
import { ensureCustomer,closeAccount,accountUser,accountCopy } from '../account';
import { customerToken } from '../account-storage';
import { bookingProfileCopy,loadBookingProfile,contactDetails,emptyContact,sameContact,validContact,type BookingProfile,type ContactDetails } from '../booking-profile';
import { isContentPreview } from '../preview-context';
import { locale,say } from '../state';
import { reservationDraft as draft,readSession,saveSession,validSelection,minutes,type Reservation,type ReservationPayload,type ReservationCalendar } from '../reservations';
import { copy,words } from './copy';
import {saveNotificationPreferences} from '../customer-notifications';
import { bookingExperience } from '../patch-reservations';

export function useVisitFlow(){
 const route=useRoute(),router=useRouter();
 const saved=readSession<{step:number}>('puppy-visit-flow-v1');
 const attempt=ref(readSession<{key:string;body:ReservationPayload;owner?:string}>('puppy-reservation-attempt-v1'));
 const step=ref(attempt.value?2:0),direction=ref(1);
 const calendar=ref<ReservationCalendar|null>(null),loading=ref(true),sending=ref(false),checkingAccount=ref(false),error=ref(''),loadError=ref('');
 const locked=computed(()=>sending.value||checkingAccount.value||!!attempt.value);
 const offer=computed(()=>calendar.value?.offers?.find(o=>o.id===draft.offer));
 const firstReady=computed(()=>['hourly','day','patch'].includes(draft.booking.plan));
 if(!attempt.value){delete draft.offer;delete draft.offer_revision;}
 const contactProfile=ref<BookingProfile>(),contactLoading=ref(!!customerToken()),contactError=ref('');
 const contactEditedKey='puppy-reservation-contact-edited-v1',contactOwnerKey='puppy-reservation-contact-owner-v1';
 const savedEditing=readSession<boolean>(contactEditedKey);
 let legacyContactDraft=savedEditing===null;
 const detailsEditing=ref(savedEditing??!!(draft.name||draft.contact));
 let contactOwner=readSession<string>(contactOwnerKey)||'',contactSequence=0;
 const savedDetails=computed(()=>!!contactProfile.value?.complete&&!detailsEditing.value);
 function editDetails(value:ContactDetails){Object.assign(draft,value);detailsEditing.value=true;saveSession(contactEditedKey,true);}
 function beginDetailsEdit(){detailsEditing.value=true;saveSession(contactEditedKey,true);}
 function useSavedDetails(){if(!contactProfile.value?.complete)return;Object.assign(draft,contactDetails(contactProfile.value));detailsEditing.value=false;saveSession(contactEditedKey,false);}
 async function loadContactContext(){
  const id=accountUser.value?.id,version=++contactSequence;if(!id){contactLoading.value=!!customerToken();return false;}
  contactLoading.value=true;contactError.value='';
  try{
   const result=await loadBookingProfile(id);
   if(!alive||version!==contactSequence||id!==accountUser.value?.id)return false;
   contactProfile.value=result;
   if(!attempt.value){
    if(result.complete&&(!detailsEditing.value||(legacyContactDraft&&sameContact(draft,result))))useSavedDetails();
    else if(!result.complete)detailsEditing.value=true;
    legacyContactDraft=false;
   }
   return true;
  }catch(e){if(alive&&version===contactSequence)contactError.value=(e as Error).message;return false;}
  finally{if(alive&&version===contactSequence)contactLoading.value=false;}
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
   const data=await commerceApi<ReservationCalendar>('/reservation-calendar?experience='+bookingExperience(draft.booking.plan)+'&guests='+(Number.isInteger(draft.booking.guests)&&draft.booking.guests>0?draft.booking.guests:1));
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
 function choosePlan(plan:'hourly'|'day'|'patch'){if(locked.value)return;delete draft.offer;delete draft.offer_revision;if(draft.booking.plan!==plan){draft.booking.plan=plan;clearTime();}error.value='';}
 function chooseGuests(value:number){if(locked.value||!Number.isInteger(value)||value<1||value>99)return;draft.booking.guests=value;error.value='';}
 function chooseInterval(value:{date:string;start:string;end:string}){if(locked.value)return;Object.assign(draft.booking,value);error.value='';}
 function back(){void navigate(step.value-1);}
 async function submit(){
  if(sending.value||checkingAccount.value||isContentPreview())return;
  if(step.value<2){await navigate(step.value+1);return;}
  if(!attempt.value&&!selected.value){error.value=say(copy.choose_available);return;}
  checkingAccount.value=true;
  try{
  if(!await ensureCustomer()||!alive)return;
  if(attempt.value?.owner&&attempt.value.owner!==accountUser.value?.id){error.value=say(accountCopy.account_login_required);return;}
  if(!attempt.value){
   if((!contactProfile.value||contactProfile.value.owner_id!==accountUser.value?.id)&&!await loadContactContext())return;
   if(!alive)return;
   if(!validContact(draft)){error.value=say(bookingProfileCopy.incomplete);detailsEditing.value=true;return;}
   if(!await load()||!alive||!selected.value){if(alive)step.value=firstReady.value?1:0;return;}
   const body:ReservationPayload={booking:{...draft.booking},name:draft.name.trim(),contact_method:draft.contact_method,contact:draft.contact.trim(),contact_profile_version:contactProfile.value!.version,notes:draft.notes,locale:locale.value,website:''};
   if(offer.value){body.offer=offer.value.id;body.offer_revision=offer.value.revision;}
   attempt.value={key:crypto.randomUUID(),body,owner:accountUser.value?.id};saveSession('puppy-reservation-attempt-v1',attempt.value);
  }
  }catch(e){error.value=(e as Error).message;return;}
  finally{checkingAccount.value=false;}
  const request=attempt.value;sending.value=true;error.value='';
  try{
   await saveNotificationPreferences();
   const receipt=await commerceApi<Reservation>('/reservations',{method:'POST',headers:{'Idempotency-Key':request.key},body:JSON.stringify(request.body)});
   if(request.owner&&request.owner!==accountUser.value?.id){error.value=say(accountCopy.account_login_required);return;}
   saveSession('puppy-reservation-attempt-v1',null);saveSession('puppy-last-reservation',receipt.id);saveSession('puppy-visit-flow-v1',null);
   saveSession(contactEditedKey,false);window.dispatchEvent(new Event('studio-booking-profile-change'));
   if(alive){attempt.value=null;clearTime();delete draft.offer;delete draft.offer_revision;await router.push('/reservation/'+receipt.id);}
  }catch(e){
   if(!alive)return;error.value=(e as Error).message;
   if(e instanceof CommerceError&&e.status>=400&&e.status<500&&!['reservation_request_changed','reservation_session_missing','account_login_required'].includes(e.code||'')){
    attempt.value=null;saveSession('puppy-reservation-attempt-v1',null);if(e.code==='booking_profile_changed')await loadContactContext();else if(e.status===409||e.code?.startsWith('reservation_offer'))await load();
   }
  }finally{if(alive)sending.value=false;}
 }
 function visible(){if(!document.hidden&&!locked.value&&!loading.value)void load();}
 watch(()=>[draft.booking.guests,bookingExperience(draft.booking.plan)],()=>{if(!locked.value)void load();});
 watch(()=>accountUser.value?.id,(id,previous)=>{
  contactProfile.value=undefined;
  if((contactOwner&&id&&contactOwner!==id)||(previous&&!id)||(contactOwner&&!id&&!customerToken())){
   Object.assign(draft,emptyContact());draft.notes='';detailsEditing.value=false;saveSession(contactEditedKey,false);
  }
  if(id||!customerToken()){contactOwner=id||'';saveSession(contactOwnerKey,contactOwner);}
  void loadContactContext();
 },{immediate:true,flush:'sync'});
 watch(step,value=>{if(value===2)void loadContactContext();});
 watch(()=>route.query.step,()=>{if(!restored||locked.value)return;const value=safeStep(requestedStep());direction.value=value>=step.value?1:-1;step.value=value;persist();});
 function refreshDetails(){if(!locked.value)void loadContactContext();}
 onMounted(()=>{void load();timer=setInterval(visible,60000);window.addEventListener('pageshow',visible);window.addEventListener('focus',visible);document.addEventListener('visibilitychange',visible);window.addEventListener('studio-booking-profile-change',refreshDetails);});
 onBeforeUnmount(()=>{alive=false;sequence++;contactSequence++;clearInterval(timer);window.removeEventListener('pageshow',visible);window.removeEventListener('focus',visible);document.removeEventListener('visibilitychange',visible);window.removeEventListener('studio-booking-profile-change',refreshDetails);closeAccount();});
 return reactive({draft,step,direction,calendar,loading,sending,checkingAccount,error,loadError,attempt,locked,offer,contactProfile,contactLoading,contactError,savedDetails,detailsEditing,loadContactContext,editDetails,beginDetailsEdit,useSavedDetails,firstReady,selected,load,navigate,choosePlan,chooseGuests,chooseInterval,back,submit});
}
export type VisitFlow=ReturnType<typeof useVisitFlow>;
