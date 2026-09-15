import {reactive,ref} from 'vue';
import {miniSession,studioCall,MiniappError} from './miniapp-client';
import copy from '../../../05_studio/src/content/customer-notifications.json';
type Preferences={email:string;phone:string;email_enabled:boolean;sms_enabled:boolean;version:number};
type Permission={nonce:string;templates:{kind:string;template_id:string;title:string}[]};
export type WechatKind='confirmed'|'cancelled'|'reminder';
export type WechatChoice='accept'|'reject'|'ban'|'unavailable';
export const wechatKinds:WechatKind[]=['confirmed','cancelled','reminder'];
export const wechatChoices=reactive<Partial<Record<WechatKind,WechatChoice>>>({});
export const wechatPreparing=ref(false),wechatSubscribing=ref(false);
const lastBookingWechat=ref<{token:string;id:string;choices:Partial<Record<WechatKind,WechatChoice>>}|null>(null);
const blank=():Preferences=>({email:'',phone:'',email_enabled:false,sms_enabled:false,version:0});
export const notificationDraft=reactive(blank()),notificationsReady=ref(false),wechatReady=ref(false);
let owner='',snapshot='',permission:Permission|undefined,until=0,load:Promise<void>|undefined,warming:Promise<void>|undefined,epoch=0;
function clearChoices(){wechatReady.value=false;for(const kind of wechatKinds)delete wechatChoices[kind];}
function account(token:string){if(owner!==token){epoch++;owner=token;Object.assign(notificationDraft,blank());notificationsReady.value=false;clearChoices();wechatPreparing.value=false;wechatSubscribing.value=false;lastBookingWechat.value=null;snapshot='';permission=undefined;load=undefined;warming=undefined;until=0;}}
export function resetWechatChoices(token:string){account(token);clearChoices();}
export function skipWechatChoices(token:string){account(token);clearChoices();for(const kind of wechatKinds)wechatChoices[kind]='unavailable';}
export function wechatPermissionReady(token:string){return !!token&&token===owner&&!!permission?.templates.length&&Date.now()<until&&!wechatSubscribing.value;}
export function saveBookingWechatChoices(token:string,id:string){if(token===owner)lastBookingWechat.value={token,id,choices:{...wechatChoices}};}
export function bookingWechatChoices(token:string,id:string){const value=lastBookingWechat.value;return value?.token===token&&value.id===id?value.choices:null;}
export async function loadNotifications(token:string){account(token);if(!token||notificationsReady.value)return;if(!load)load=studioCall<Preferences>('/auth/notifications',{},'',token,'GET').then(value=>{if(token===owner){Object.assign(notificationDraft,value);snapshot=JSON.stringify(notificationDraft);notificationsReady.value=true;}}).finally(()=>{if(token===owner)load=undefined;});await load;}
export async function saveNotifications(token:string){await loadNotifications(token);if(!notificationsReady.value||(notificationDraft.version>0&&snapshot===JSON.stringify(notificationDraft)))return;const {email,phone,email_enabled,sms_enabled,version}=notificationDraft;const value=await studioCall<Preferences>('/auth/notifications',{email,phone,email_enabled,sms_enabled,version},'',token,'PUT');if(token===owner){Object.assign(notificationDraft,value);snapshot=JSON.stringify(notificationDraft);}}
export async function warmWechat(token:string,force=false){
 account(token);if(!token||wechatSubscribing.value||!force&&permission&&Date.now()<until)return;
 // #ifdef MP-WEIXIN
 if(!warming){
  const generation=epoch,started=Date.now();permission=undefined;until=0;wechatPreparing.value=true;
  const task=(async()=>{const proof=await miniSession();if(generation!==epoch||token!==owner)return;const value=await studioCall<Permission>('/auth/notifications/wechat/session',{},proof.ticket,token);if(generation===epoch&&token===owner){permission=value;until=started+Math.max(0,Math.min(240,proof.expires_in-30))*1000;}})();
  warming=task;
  void task.finally(()=>{if(generation===epoch&&warming===task){warming=undefined;wechatPreparing.value=false;}}).catch(()=>{});
 }
 await warming;
 // #endif
}
export async function subscribeWechat(token:string){
 // #ifdef MP-WEIXIN
 if(wechatSubscribing.value)return false;
 if(!wechatPermissionReady(token)){if(token===owner){clearChoices();for(const kind of wechatKinds)wechatChoices[kind]='unavailable';}return false;}
 const prompt=permission!,generation=epoch;permission=undefined;until=0;clearChoices();wechatSubscribing.value=true;
 try{
  // Keep this call in the actual tap stack. Refreshing an expired preparation
  // must happen before a new visible confirmation click, never before this API.
  const results=await new Promise<Record<string,string>>(resolve=>{
   let done=false;const finish=(value:Record<string,string>)=>{if(!done){done=true;resolve(value);}};
   try{uni.requestSubscribeMessage({tmplIds:prompt.templates.map(t=>t.template_id),success:value=>{const result:Record<string,string>={};for(const t of prompt.templates){const choice=(value as any)[t.template_id];if(['accept','reject','ban'].includes(choice))result[t.template_id]=choice;}finish(result);},fail:()=>finish({})});}catch{finish({});}
  });
  if(token!==owner||generation!==epoch)return false;
  if(Object.keys(results).length){
   const record=()=>studioCall('/auth/notifications/wechat/subscribe',{nonce:prompt.nonce,results},'',token);
   try{await record();}catch{if(token!==owner||generation!==epoch)return false;await record();}
  }
  if(token!==owner||generation!==epoch)return false;
  for(const template of prompt.templates){if(wechatKinds.includes(template.kind as WechatKind))wechatChoices[template.kind as WechatKind]=(results[template.template_id] as WechatChoice)||'unavailable';}
  // Cancellation/reminder permission does not authorize a confirmation notice.
  wechatReady.value=wechatChoices.confirmed==='accept';return wechatReady.value;
 }catch{
  if(token===owner&&generation===epoch){clearChoices();for(const kind of wechatKinds)wechatChoices[kind]='unavailable';}
  throw new MiniappError('notification_wechat_unavailable');
 }finally{if(token===owner&&generation===epoch){wechatSubscribing.value=false;void warmWechat(token).catch(()=>{});}}
 // #endif
 return false;
}

export async function askWechatNotifications(token:string,language:string){
 // #ifdef MP-WEIXIN
 try{await warmWechat(token);}catch{return false;}
 if(!permission?.templates.length)return false;
 const say=(value:string[])=>value[language==='en'?1:0];
 return await new Promise<boolean>(resolve=>uni.showModal({title:say(copy.prompt_title),content:say(copy.prompt_body),confirmText:say(copy.prompt_allow),cancelText:say(copy.prompt_later),
  success:choice=>{if(choice.confirm)void subscribeWechat(token).then(resolve).catch(()=>resolve(false));else resolve(false);},fail:()=>resolve(false)}));
 // #endif
 return false;
}
