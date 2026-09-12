import {reactive,ref} from 'vue';
import {commerceApi} from './commerce';
import {customerToken} from './account-storage';
export type NotificationPreferences={email:string;phone:string;email_enabled:boolean;sms_enabled:boolean;version:number};
const blank=():NotificationPreferences=>({email:'',phone:'',email_enabled:false,sms_enabled:false,version:0});
export const notificationDraft=reactive(blank()),notificationLoaded=ref(false);
let owner='',snapshot='',pending:Promise<void>|undefined;
export async function loadNotificationPreferences(){
 const token=customerToken();if(owner!==token){owner=token;notificationLoaded.value=false;Object.assign(notificationDraft,blank());snapshot='';pending=undefined;}
 if(!token||notificationLoaded.value)return;
 if(!pending)pending=commerceApi<NotificationPreferences>('/auth/notifications').then(data=>{if(token===owner){Object.assign(notificationDraft,data);snapshot=JSON.stringify(notificationDraft);notificationLoaded.value=true;}}).finally(()=>{if(token===owner)pending=undefined;});
 await pending;
}
export async function saveNotificationPreferences(){
 await loadNotificationPreferences();if(!notificationLoaded.value||(notificationDraft.version>0&&snapshot===JSON.stringify(notificationDraft)))return;
 const token=owner;const {email,phone,email_enabled,sms_enabled,version}=notificationDraft;
 const value=await commerceApi<NotificationPreferences>('/auth/notifications',{method:'PUT',body:JSON.stringify({email,phone,email_enabled,sms_enabled,version})});
 if(token===owner){Object.assign(notificationDraft,value);snapshot=JSON.stringify(notificationDraft);}
}
