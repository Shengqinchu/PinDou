import { computed, reactive, ref, shallowRef,watch } from 'vue';
import { onShow, onHide, onUnload } from '@dcloudio/uni-app';
import { useUserStore } from '../store/user';
import { MiniappError, studioCall } from './miniapp-client';
import {peekStudioSnapshot,readStudioCached,invalidateStudioSnapshots,rememberStudioSnapshot} from './studio-cache';
import { refreshStudioContent } from './studio-content';
import { emptyBooking, emptyContact, validBooking, validContact, requestId, retryUnchanged, type Booking, type ContactContext, type Calendar, type Attempt, type Receipt,type Payload } from './studio-booking';

export function useStudioVisit(language:{value:string}){
  const user=useUserStore(),booking=reactive(emptyBooking()),contact=reactive(emptyContact());
  const notes=ref(''),step=ref(0),calendar=ref<Calendar|null>(null),loading=ref(false),sending=ref(false),errorCode=ref(''),calendarError=ref(false);
  const context=ref<ContactContext>(),contactLoading=ref(false),contactError=ref(false),editing=ref(false),profileConflict=ref(false),attempt=ref<Attempt|null>(null);
  const confirmation=shallowRef<Payload|null>(null);
  let alive=true,visible=true,calendarSeq=0,contactSeq=0,owner='',ownerToken='',timer:ReturnType<typeof setInterval>|undefined,restoring=false,resolveConfirmation:((value:boolean)=>void)|undefined;
  function settleConfirmation(value:boolean){const resolve=resolveConfirmation;resolveConfirmation=undefined;confirmation.value=null;resolve?.(value);}
  function dismissSubmission(){settleConfirmation(false);}
  function confirmSubmission(){settleConfirmation(true);}
  function review(body:Payload){return new Promise<boolean>(resolve=>{if(!alive||!visible){resolve(false);return;}resolveConfirmation=resolve;confirmation.value=body;});}
  const locked=computed(()=>sending.value||!!attempt.value);
  const selected=computed(()=>!loading.value&&!calendarError.value&&validBooking(calendar.value,booking));
  const savedContact=computed(()=>context.value?.profile.complete&&!editing.value);
  const attemptKey=(id:string)=>'pd_studio_booking_attempt:'+id;
  const draftKey=(id:string)=>'pd_studio_booking_draft:'+id;
  function saveDraft(){
    if(!owner||restoring||attempt.value)return;
    try{uni.setStorageSync(draftKey(owner),{booking:{...booking},contact:{...contact},notes:notes.value,step:step.value,editing:editing.value,profileVersion:context.value?.profile.version});}catch{}
  }
  function clearTime(){booking.start='';booking.end='';}
  function choosePlan(plan:'hourly'|'day'){if(locked.value)return;if(booking.plan!==plan){booking.plan=plan;clearTime();}errorCode.value='';}
  async function chooseGuests(count:number){
    if(locked.value||!Number.isInteger(count)||count<1||count>(calendar.value?.max_guests_per_group||6))return;
    if(booking.guests===count)return;booking.guests=count;errorCode.value='';await loadCalendar();
  }
  function select(value:Booking){if(locked.value)return;Object.assign(booking,value);errorCode.value='';}
  function navigate(value:number){
    if(locked.value)return;
    if(value>0&&!booking.plan){errorCode.value='choose_first';return;}
    if(value>1&&!selected.value){errorCode.value='choose_available';return;}
    step.value=value;errorCode.value='';uni.pageScrollTo({scrollTop:0,duration:180});
  }
  async function loadCalendar(force=false){
    const seq=++calendarSeq,path='/reservation-calendar?guests='+booking.guests,saved=peekStudioSnapshot<Calendar>(path,'');calendarError.value=false;
    if(saved&&!calendar.value)calendar.value=saved.data;
    loading.value=force||!saved||saved.age>=15000;
    try{
      const value=await readStudioCached<Calendar>(path,'',15000,force);
      if(!alive||seq!==calendarSeq)return false;
      calendar.value=value;
      if(!attempt.value&&booking.start&&!validBooking(value,booking)){clearTime();errorCode.value='reservation_interval_unavailable';if(step.value===2)step.value=1;}
      return true;
    }catch{if(alive&&seq===calendarSeq)calendarError.value=true;return false;}
    finally{if(alive&&seq===calendarSeq)loading.value=false;}
  }
  function useSaved(){
    if(locked.value)return;applySavedContact();
  }
  function applySavedContact(){
    if(!context.value)return;
    const value=context.value.profile;
    Object.assign(contact,{name:value.name,contact_method:value.contact_method,contact:value.contact});
    editing.value=!value.complete;profileConflict.value=false;errorCode.value='';
  }
  async function loadContact(force=false){
    const seq=++contactSeq,token=user.token;
    if(!token){context.value=undefined;contactLoading.value=false;return false;}
    contactLoading.value=true;contactError.value=false;
    try{
      const result=await readStudioCached<ContactContext>('/auth/reservation-context',token,30000,force);
      if(!alive||seq!==contactSeq||token!==user.token)return false;
      const id=result.profile.owner_id;
      if(!id)throw new MiniappError('account_login_required',401);
      if(owner!==id){
        restoring=true;owner=id;ownerToken=token;Object.assign(contact,emptyContact());notes.value='';editing.value=false;profileConflict.value=false;
        let pending:Attempt|null=null,saved:any=null;
        try{pending=uni.getStorageSync(attemptKey(id))||null;saved=uni.getStorageSync(draftKey(id))||null;}catch{}
        attempt.value=pending?.owner===id&&pending.key&&pending.body?pending:null;
        if(attempt.value){const body=attempt.value.body;Object.assign(booking,body.booking);Object.assign(contact,{name:body.name,contact_method:body.contact_method,contact:body.contact});notes.value=body.notes;step.value=2;}
        else if(saved?.booking&&saved?.contact){Object.assign(booking,saved.booking);Object.assign(contact,saved.contact);notes.value=String(saved.notes||'');step.value=Math.max(0,Math.min(2,saved.step||0));editing.value=!!saved.editing;profileConflict.value=editing.value&&saved.profileVersion!==result.profile.version;}
        restoring=false;
      }
      if(context.value&&context.value.profile.owner_id===id&&context.value.profile.version!==result.profile.version&&editing.value&&!attempt.value)profileConflict.value=true;
      context.value=result;ownerToken=token;
      if(!attempt.value&&!editing.value)applySavedContact();
      return true;
    }catch(e){
      if(alive&&seq===contactSeq){contactError.value=true;if(e instanceof MiniappError&&e.status===401){user.logout();context.value=undefined;}}
      return false;
    }finally{if(alive&&seq===contactSeq)contactLoading.value=false;}
  }
  async function submit(){
    if(sending.value)return;
    if(!user.token){uni.navigateTo({url:'/pages/auth/studio-login'});return;}
    if(!attempt.value&&(!selected.value||step.value!==2)){errorCode.value='choose_available';return;}
    sending.value=true;errorCode.value='';uni.hideKeyboard();
    const token=user.token;
    try{
      if(!attempt.value||!context.value||ownerToken!==token){if(!await loadContact(true))return;}
      if(!alive||token!==user.token)return;
      if(attempt.value?.owner&&attempt.value.owner!==owner)throw new MiniappError('account_login_required',401);
      if(!attempt.value){
        if(profileConflict.value){errorCode.value='booking_profile_changed';return;}
        if(!validContact(contact,context.value!.can_omit_details)){editing.value=true;errorCode.value=!contact.name&&!contact.contact?'reservation_contact_required':'booking_contact_invalid';return;}
        if(!await loadCalendar(true)||!alive||!validBooking(calendar.value,booking)){if(alive)step.value=1;return;}
        if(token!==user.token||!visible)return;
        const body:Payload={booking:{...booking},name:contact.name.trim(),contact_method:contact.contact_method,contact:contact.contact.trim(),notes:notes.value,locale:language.value==='en'?'en':'zh',website:'',contact_profile_version:context.value!.profile.version};
        const reviewedOwner=owner;
        if(!await review(body)||!alive||token!==user.token||owner!==reviewedOwner)return;
        const next={owner:reviewedOwner,key:requestId(),body};
        // Never send before the exact request has been retained for recovery.
        uni.setStorageSync(attemptKey(owner),next);
        attempt.value=next;
      }else if(!await loadCalendar(true))return;
      if(!alive||token!==user.token)return;
      const request=attempt.value!;
      const result=await studioCall<Receipt>('/reservations',request.body,'',token,'POST',{'Idempotency-Key':request.key});
      if(token!==user.token)return;
      invalidateStudioSnapshots(token);rememberStudioSnapshot('/reservations/'+result.id,token,result);
      uni.removeStorageSync(attemptKey(request.owner));uni.removeStorageSync(draftKey(request.owner));
      if(alive){restoring=true;attempt.value=null;clearTime();notes.value='';step.value=0;restoring=false;uni.redirectTo({url:'/pages/studio/reservation?id='+encodeURIComponent(result.id)});}
    }catch(e){
      if(!alive||token!==user.token)return;
      const failure=e instanceof MiniappError?e:new MiniappError('generic_error');errorCode.value=failure.code;
      if(failure.status===401){user.logout();return;}
      if(attempt.value&&!retryUnchanged(failure.status,failure.code)){
        uni.removeStorageSync(attemptKey(owner));attempt.value=null;
        if(failure.code==='booking_profile_changed'){await loadContact(true);profileConflict.value=true;}
        else if(failure.status===409||failure.status===422){await loadCalendar(true);if(!validBooking(calendar.value,booking))step.value=1;}
      }
    }finally{if(alive)sending.value=false;}
  }
  watch([booking,contact,notes,step,editing],saveDraft,{deep:true});
  watch(()=>user.token,(token,previous)=>{
    if(token===previous)return;
    dismissSubmission();
    contactSeq++;ownerToken='';context.value=undefined;Object.assign(contact,emptyContact());notes.value='';owner='';attempt.value=null;editing.value=false;
  });
  async function resume(){
    clearInterval(timer);void refreshStudioContent();
    if(!locked.value){await loadContact();if(alive)await loadCalendar();}
    if(alive)timer=setInterval(()=>{if(!locked.value&&!loading.value)void loadCalendar();},60000);
  }
  onShow(()=>{visible=true;void resume();});onHide(()=>{visible=false;clearInterval(timer);dismissSubmission();});onUnload(()=>{alive=false;visible=false;dismissSubmission();calendarSeq++;contactSeq++;clearInterval(timer);});
  return {booking,contact,notes,step,calendar,loading,sending,errorCode,calendarError,context,contactLoading,contactError,editing,profileConflict,attempt,confirmation,confirmSubmission,dismissSubmission,locked,selected,savedContact,choosePlan,chooseGuests,select,navigate,loadCalendar,loadContact,useSaved,submit};
}
