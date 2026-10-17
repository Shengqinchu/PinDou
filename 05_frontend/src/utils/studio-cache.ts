import {MiniappError,studioRead} from './miniapp-client';
import {readPublic,writePublic} from './public-store';

// Session-only snapshots: never persist balances or contact details to disk.
type Entry={json:string;at:number};
const values=new Map<string,Entry>(),pending=new Map<string,{generation:number;request:Promise<any>}>();
let ownerToken='',generation=0;
const key=(path:string,token:string)=>(token?'private:':'public:')+path;
const allowed=(token:string)=>!token||token===ownerToken;
// Only anonymous public reads may outlive the session; they are shown while a fresh copy loads.
const persistable=(path:string,token:string)=>!token&&/^\/(reservation-calendar\?|patch-promotion$)/.test(path);
const DISK_AGE=86400000;
export function setStudioCacheOwner(token:string){if(token!==ownerToken){ownerToken=token;generation++;values.clear();pending.clear();}}
export function invalidateStudioSnapshots(token:string){if(token!==ownerToken)return;generation++;values.clear();pending.clear();}
export function rememberStudioSnapshot<T>(path:string,token:string,data:T){
 if(!allowed(token))return;
 const id=key(path,token);values.delete(id);values.set(id,{json:JSON.stringify(data),at:Date.now()});
 while(values.size>32)values.delete(values.keys().next().value!);
 if(persistable(path,token))writePublic(path,data);
}
export function peekStudioSnapshot<T>(path:string,token:string,maxAge=300000):{data:T;age:number}|undefined{
 if(!allowed(token))return;
 const id=key(path,token);let value=values.get(id);
 if(!value&&persistable(path,token)){const stored=readPublic<T>(path,DISK_AGE);if(stored){value={json:JSON.stringify(stored.data),at:stored.at};values.set(id,value);maxAge=Math.max(maxAge,DISK_AGE);}}
 if(!value)return;
 const age=Date.now()-value.at;if(age<0||age>maxAge){values.delete(id);return;}
 return {data:JSON.parse(value.json),age};
}
export async function readStudioCached<T>(path:string,token='',freshFor=15000,force=false):Promise<T>{
 if(!allowed(token))throw new MiniappError('account_login_required',401);
 const saved=peekStudioSnapshot<T>(path,token);if(!force&&saved&&saved.age<freshFor)return saved.data;
 const id=key(path,token),current=pending.get(id);if(current?.generation===generation)return current.request;
 const version=generation;
 const request=studioRead<T>(path,token).then(value=>{
  if(!allowed(token))throw new MiniappError('account_login_required',401);
  // A successful edit/cancellation invalidates even reads already in flight.
  if(version!==generation)return readStudioCached<T>(path,token,freshFor,true);
  rememberStudioSnapshot(path,token,value);return value;
 }).finally(()=>{if(pending.get(id)?.request===request)pending.delete(id);});
 pending.set(id,{generation:version,request});return request;
}
