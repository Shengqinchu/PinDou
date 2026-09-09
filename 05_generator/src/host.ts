import { accountUser,ensureCustomer,refreshAccount,openAccount,signOut } from '../../05_studio/src/account';
import { customerToken } from '../../05_studio/src/account-storage';
export const generatorSession=()=>customerToken();
export async function requestGeneratorLogin(){const ok=await ensureCustomer();return ok;}
export {openAccount,accountUser};
export async function expireGeneratorSession(expected:string){
  if(expected!==customerToken())return;
  const valid=await refreshAccount().catch(()=>true);
  if(!valid&&expected===customerToken())signOut();
  if(!valid&&!accountUser.value)openAccount();
}
