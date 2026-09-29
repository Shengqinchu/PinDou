import { onBeforeUnmount, onMounted, ref } from 'vue';
import { commerceApi } from './commerce';
import { contentModule } from './content-store';
import defaults from './content/patch-promotion.json';
export const promotionCopy = contentModule('patch-promotion', defaults);
export type PatchPromotion = {campaign:string;enabled:boolean;quota:number;remaining:number};
export type ManagedPromotion = PatchPromotion & {allocated:number;remaining_adjustment:number;started_at:string;version:number};

// Refresh on navigation, focus and while visible. A failed refresh removes stale
// availability rather than continuing to advertise gifts which may be gone.
export function usePatchPromotion(){
  const promotion=ref<PatchPromotion>(),loading=ref(false);
  let alive=true,sequence=0,timer:ReturnType<typeof setInterval>;
  async function refresh(){
    const n=++sequence;loading.value=true;
    try{const data=await commerceApi<PatchPromotion>('/patch-promotion',{cache:'no-store'});if(alive&&n===sequence)promotion.value=data;}
    catch{if(alive&&n===sequence)promotion.value=undefined;}
    finally{if(alive&&n===sequence)loading.value=false;}
  }
  function visible(){if(!document.hidden)void refresh();}
  onMounted(()=>{void refresh();timer=setInterval(visible,30000);window.addEventListener('focus',visible);document.addEventListener('visibilitychange',visible);});
  onBeforeUnmount(()=>{alive=false;sequence++;clearInterval(timer);window.removeEventListener('focus',visible);document.removeEventListener('visibilitychange',visible);});
  return {promotion,loading,refresh};
}
