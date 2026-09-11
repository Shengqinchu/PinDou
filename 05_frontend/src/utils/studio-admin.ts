import {miniSession,studioCall,MiniappError} from './miniapp-client';
import {useUserStore} from '../store/user';
import workbench from '../../../05_studio/src/content/workbench.json';
import business from '../../../05_studio/src/content/business.json';
import wallet from '../../../05_studio/src/content/wallet.json';
import commerce from '../../../05_studio/src/content/commerce.json';
import messaging from '../../../05_studio/src/content/messaging.json';
import {clearAdminViews,invalidateAdminViews} from './studio-admin-cache';
let ticket='',until=0,inFlight:ReturnType<typeof miniSession>|null=null;
async function proof(){
 if(ticket&&Date.now()<until)return ticket;
 if(!inFlight)inFlight=miniSession();
 try{const session=await inFlight;ticket=session.ticket;until=Date.now()+Math.max(10,session.expires_in-30)*1000;return ticket;}finally{inFlight=null;}
}
function clearRejectedAdmin(error:unknown){
 if(error instanceof MiniappError&&[401,403].includes(error.status))clearAdminViews();
}
export async function adminCall<T>(path:string,data:unknown={},method:'GET'|'POST'|'PUT'|'PATCH'|'DELETE'='GET',extra:Record<string,string>={}):Promise<T>{
 if(!path.startsWith('/manage/'))throw new Error('invalid_admin_path');
 // WeChat's portable request method set excludes PATCH; these aliases invoke
 // the same authenticated, version-checked server handlers as the website.
 const requestMethod=method==='PATCH'?'POST':method;
 if(method==='PATCH')path+='/update';
 // #ifdef MP-WEIXIN
 try{const result=await studioCall<T>(path,data,await proof(),'',requestMethod,extra);if(requestMethod!=='GET')invalidateAdminViews(path);return result;}
 catch(e){
  if(e instanceof MiniappError&&e.status===401){ticket='';try{const result=await studioCall<T>(path,data,await proof(),'',requestMethod,extra);if(requestMethod!=='GET')invalidateAdminViews(path);return result;}catch(retry){clearRejectedAdmin(retry);throw retry;}}
  clearRejectedAdmin(e);throw e;
 }
 // #endif
 // #ifndef MP-WEIXIN
 try{const result=await studioCall<T>(path,data,'',useUserStore().token,requestMethod,extra);if(requestMethod!=='GET')invalidateAdminViews(path);return result;}catch(e){clearRejectedAdmin(e);throw e;}
 // #endif
}
export function adminError(error:unknown,say:(s:string[])=>string){
 const key=error instanceof MiniappError?error.code:'generic_error';
 for(const source of [workbench,business,wallet,commerce,messaging]){const item=(source as Record<string,string[]>)[key];if(item)return say(item);}
 return say(workbench.generic_error);
}
export function today(){const d=new Date();return new Intl.DateTimeFormat('en-CA',{timeZone:'America/Toronto',year:'numeric',month:'2-digit',day:'2-digit'}).format(d);}
export function requestKey(){
 return 'xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx'.replace(/[xy]/g,c=>{const r=Math.floor(Math.random()*16);return(c==='x'?r:(r&3)|8).toString(16);});
}
export function goAdmin(page='',query=''){uni.navigateTo({url:'/pages/studio/manage'+page+(query?'?'+query:'')});}
export function confirmAdmin(title:string,content:string,confirmText:string,cancelText:string):Promise<boolean>{
 return new Promise(resolve=>uni.showModal({title,content,confirmText,cancelText,success:r=>resolve(r.confirm),fail:()=>resolve(false)}));
}
