import { ref } from "vue";
import { contentModule } from "./content-store";
import defaults from "./content/account.json";
import { commerceApi, CommerceError } from "./commerce";
import { customerToken,storeCustomer,clearCustomer } from "./account-storage";
export const accountCopy=contentModule("account",defaults);
export type Customer={id:string;email:string;nickname:string;avatar?:string;is_admin?:boolean;customer_code?:string};
export type SignInResult={token:string;user:Customer;shared_user:Record<string,unknown>};
export const accountUser=ref<Customer|null>(null);
export const accountOpen=ref(false);
export const accountForReservation=ref(false);
let resolveSignIn:((result:boolean)=>void)|undefined;
let sequence=0;

export async function refreshAccount():Promise<boolean> {
  const token=customerToken();const current=++sequence;
  if(!token){accountUser.value=null;return false;}
  try {
    const result=await commerceApi<{user:Customer}>("/auth/me");
    if(current!==sequence||token!==customerToken())return false;
    accountUser.value=result.user;return true;
  }catch(error){
    if(current===sequence&&token===customerToken()&&error instanceof CommerceError&&error.status===401){
      clearCustomer();accountUser.value=null;return false;
    }
    throw error;
  }
}
export function openAccount(){accountForReservation.value=false;accountOpen.value=true;}
export function closeAccount(){
  accountOpen.value=false;accountForReservation.value=false;
  const resolve=resolveSignIn;resolveSignIn=undefined;resolve?.(false);
}
export async function ensureCustomer():Promise<boolean>{
  if(await refreshAccount())return true;
  return new Promise(resolve=>{
    resolveSignIn?.(false);resolveSignIn=resolve;
    accountForReservation.value=true;accountOpen.value=true;
  });
}
export function completeSignIn(result:SignInResult){
  ++sequence;storeCustomer(result.token,result.shared_user);accountUser.value=result.user;
  const resolve=resolveSignIn;resolveSignIn=undefined;
  if(resolve){accountOpen.value=false;accountForReservation.value=false;resolve(true);}
}
export function signOut(){++sequence;clearCustomer();accountUser.value=null;closeAccount();}
export function applyAccountProfile(profile:Record<string,unknown>,token:string):boolean{
  if(token!==customerToken()||profile.user_id!==accountUser.value?.id)return false;
  ++sequence;storeCustomer(token,profile);
  accountUser.value={id:String(profile.user_id),email:String(profile.email||''),nickname:String(profile.nickname||''),avatar:typeof profile.avatar==='string'?profile.avatar:'',is_admin:accountUser.value?.is_admin};
  return true;
}
export function installAccount(){
  const refresh=()=>{if(!document.hidden)void refreshAccount().catch(()=>{});};
  const storage=(event:StorageEvent)=>{if(event.key===null||event.key==="pd_web_token"||event.key==="pd_web_user")refresh();};
  refresh();window.addEventListener("storage",storage);window.addEventListener("pageshow",refresh);
  window.addEventListener("focus",refresh);
  document.addEventListener("visibilitychange",refresh);
  return ()=>{window.removeEventListener("storage",storage);window.removeEventListener("pageshow",refresh);window.removeEventListener("focus",refresh);document.removeEventListener("visibilitychange",refresh);};
}
