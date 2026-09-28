import {ref} from 'vue';
import {onViewShow,onViewHide,onViewUnload} from './studio-view-lifecycle';
import {studioRead} from './miniapp-client';

export type PatchPromotion={campaign:string;enabled:boolean;quota:number;remaining:number};
const dismissed=new Set<string>();
export function usePatchPromotion(popup=false){
 const offer=ref<PatchPromotion|null>(null),open=ref(false);
 let alive=true,visible=false,sequence=0,timer:ReturnType<typeof setInterval>|undefined;
 function dismiss(){if(offer.value)dismissed.add(offer.value.campaign);open.value=false;}
 async function refresh(){
  const n=++sequence;
  try{
   const value=await studioRead<PatchPromotion>('/patch-promotion');
   if(!alive||!visible||n!==sequence)return;
   if(!value.campaign||typeof value.enabled!=='boolean'||!Number.isInteger(value.quota)||value.quota<0||!Number.isInteger(value.remaining)||value.remaining<0)throw new Error('invalid_offer');
   offer.value=value;
   open.value=popup&&value.enabled&&!dismissed.has(value.campaign);
  }catch{if(alive&&n===sequence){offer.value=null;open.value=false;}}
 }
 onViewShow(()=>{visible=true;void refresh();clearInterval(timer);timer=setInterval(()=>void refresh(),30000);});
 onViewHide(()=>{visible=false;sequence++;open.value=false;clearInterval(timer);});
 onViewUnload(()=>{alive=false;sequence++;clearInterval(timer);});
 return {offer,open,dismiss,refresh};
}
