import {reactive,ref} from 'vue';
import {miniSession,studioCall} from './miniapp-client';
import copy from '../../../05_studio/src/content/customer-notifications.json';
type Preferences={email:string;phone:string;email_enabled:boolean;sms_enabled:boolean;version:number};
type Permission={nonce:string;templates:{kind:string;template_id:string;title:string}[]};
const blank=():Preferences=>({email:'',phone:'',email_enabled:false,sms_enabled:false,version:0});
export const notificationDraft=reactive(blank()),notificationsReady=ref(false),wechatReady=ref(false);
let owner='',snapshot='',permission:Permission|undefined,until=0,load:Promise<void>|undefined,warming:Promise<void>|undefined;
function account(token:string){if(owner!==token){owner=token;Object.assign(notificationDraft,blank());notificationsReady.value=false;wechatReady.value=false;snapshot='';permission=undefined;load=undefined;warming=undefined;until=0;}}
export async function loadNotifications(token:string){account(token);if(!token||notificationsReady.value)return;if(!load)load=studioCall<Preferences>('/auth/notifications',{},'',token,'GET').then(value=>{if(token===owner){Object.assign(notificationDraft,value);snapshot=JSON.stringify(notificationDraft);notificationsReady.value=true;}}).finally(()=>{if(token===owner)load=undefined;});await load;}
export async function saveNotifications(token:string){await loadNotifications(token);if(!notificationsReady.value||(notificationDraft.version>0&&snapshot===JSON.stringify(notificationDraft)))return;const {email,phone,email_enabled,sms_enabled,version}=notificationDraft;const value=await studioCall<Preferences>('/auth/notifications',{email,phone,email_enabled,sms_enabled,version},'',token,'PUT');if(token===owner){Object.assign(notificationDraft,value);snapshot=JSON.stringify(notificationDraft);}}
export async function warmWechat(token:string){
 account(token);if(permission&&Date.now()<until||!token)return;
 // #ifdef MP-WEIXIN
 if(!warming)warming=(async()=>{const proof=await miniSession();const value=await studioCall<Permission>('/auth/notifications/wechat/session',{},proof.ticket,token);if(token===owner){permission=value;until=Date.now()+240000;}})().finally(()=>{if(token===owner)warming=undefined;});await warming;
 // #endif
}
export async function subscribeWechat(token:string){
 // #ifdef MP-WEIXIN
 if(token!==owner||!permission||Date.now()>=until)return false;
 const prompt=permission;if(!prompt.templates.length)return false;permission=undefined;until=0;
 const results=await new Promise<Record<string,string>>(resolve=>uni.requestSubscribeMessage({tmplIds:prompt.templates.map(t=>t.template_id),success:value=>{const result:Record<string,string>={};for(const t of prompt.templates){const choice=(value as any)[t.template_id];if(['accept','reject','ban'].includes(choice))result[t.template_id]=choice;}resolve(result);},fail:()=>resolve({})}));
 if(token!==owner)return false;
 await studioCall('/auth/notifications/wechat/subscribe',{nonce:prompt.nonce,results},'',token);
 wechatReady.value=Object.values(results).includes('accept');void warmWechat(token).catch(()=>{});return wechatReady.value;
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
