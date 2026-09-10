import copy from '../../../05_studio/src/content/miniapp.json';

const origin='https://pindoupuppy.com/studio-api';
export const miniappPrefix='/auth/wechat/miniapp';
export type MiniSession={ticket:string;linked:boolean;expires_in:number};
export type SharedSession={token:string;user:{id:string;nickname:string;email:string};shared_user:any};
export class MiniappError extends Error {
  constructor(public code:string,public status=0){super((copy as Record<string,string[]>)[code]?.[0]||copy.generic_error[0]);}
}
export function studioCall<T>(path:string,data:unknown={},ticket='',token=''):Promise<T>{
  return new Promise((resolve,reject)=>uni.request({
    url:origin+path,method:'POST',data,
    header:{'Content-Type':'application/json',...(ticket?{'X-Pindou-Miniapp':ticket}:{}),...(token?{Authorization:'Bearer '+token}:{})},
    timeout:20000,
    success:(response)=>{const body=response.data as any;if(response.statusCode>=200&&response.statusCode<300)resolve(body);else reject(new MiniappError(typeof body?.detail==='string'?body.detail:'generic_error',response.statusCode));},
    fail:()=>reject(new MiniappError('miniapp_provider_unavailable')),
  }));
}
export function wxCode():Promise<string>{
  return new Promise((resolve,reject)=>uni.login({provider:'weixin',success:result=>result.code?resolve(result.code):reject(new MiniappError('miniapp_code_expired')),fail:()=>reject(new MiniappError('miniapp_code_expired'))}));
}
export async function miniSession(code?:string){return studioCall<MiniSession>(miniappPrefix+'/session',{code:code||await wxCode()});}
let navigating=false;
export function openMiniappLogin(){
  const pages=getCurrentPages();
  if(navigating||pages[pages.length-1]?.route==='pages/auth/studio-login')return;
  navigating=true;uni.navigateTo({url:'/pages/auth/studio-login',complete:()=>{navigating=false;}});
}
export async function loginWithMiniappCode(code:string):Promise<{token:string;user:any}>{
  const proof=await miniSession(code);
  if(!proof.linked){openMiniappLogin();throw new MiniappError('miniapp_account_required',401);}
  const result=await studioCall<SharedSession>(miniappPrefix+'/native/sign-in',{},proof.ticket);
  return {token:result.token,user:result.shared_user};
}
