import {useUserStore} from '../store/studio-user';

type Snapshot={state:any;loadedAt:number;revision:number};
const views=new Map<string,Snapshot>(),revisions=new Map<string,number>();
let scope='',generation=0;
function currentScope(){
 const next=useUserStore().token||'current-wechat-session';
 if(next!==scope){scope=next;clearAdminViews();}
 return next;
}
export function clearAdminViews(){views.clear();revisions.clear();generation++;}
export function invalidateAdminViews(path:string){
 currentScope();
 const keys=path.startsWith('/manage/finance')?['home','finance']:
 path.startsWith('/manage/patch-promotion')?['reservations','calendar']:
 path.startsWith('/manage/reservations')?['home','reservations','calendar','finance','members']:
 path.startsWith('/manage/messages')||path.startsWith('/manage/site-messages')?['home','messages']:
 path.startsWith('/manage/members')?['home','members']:[];
 for(const key of keys)revisions.set(key,(revisions.get(key)||0)+1);
}
export function adminView<T>(key:string){
 const owner=currentScope(),epoch=generation,saved=views.get(key);
 let loadedAt=saved?.loadedAt||0,revision=saved?.revision??-1;
 const valid=()=>owner===currentScope()&&epoch===generation;
 return {
  snapshot:saved?JSON.parse(JSON.stringify(saved.state)) as T:undefined,
  valid,
  fresh:()=>valid()&&loadedAt>0&&Date.now()-loadedAt<30000&&revision===(revisions.get(key)||0),
  begin:()=>{loadedAt=0;return revisions.get(key)||0;},
  loaded:(readRevision:number)=>{loadedAt=Date.now();revision=readRevision;},
  expire:()=>{loadedAt=0;},
  save:(state:T)=>{
   if(!valid())return;
   views.delete(key);views.set(key,{state:JSON.parse(JSON.stringify(state)),loadedAt,revision});
   while(views.size>48)views.delete(views.keys().next().value!);
  },
 };
}
