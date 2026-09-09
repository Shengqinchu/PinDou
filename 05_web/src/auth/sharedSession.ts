/** Keep an already-open tool tab in sync with the Studio on this same origin. */
import { useAuthStore } from '../stores/auth';

export function installSharedSession(): () => void {
  const auth=useAuthStore();
  let generation=0;
  const sync=async()=>{
    const version=++generation;
    auth.syncFromStorage();
    if(!auth.token||document.hidden)return;
    try{await auth.refreshProfile();}catch(error){
      if(version!==generation)return;
      // Expiry is handled by the existing API client; network failures retain
      // the account instead of converting a temporary outage into a logout.
      auth.syncFromStorage();
    }
  };
  const storage=(event:StorageEvent)=>{if(event.key==='pd_web_user')auth.syncFromStorage();else if(event.key===null||event.key==='pd_web_token')void sync();};
  const visible=()=>{if(!document.hidden)void sync();};
  window.addEventListener('storage',storage);window.addEventListener('pageshow',visible);
  window.addEventListener('focus',visible);document.addEventListener('visibilitychange',visible);
  void sync();
  return()=>{generation++;window.removeEventListener('storage',storage);window.removeEventListener('pageshow',visible);window.removeEventListener('focus',visible);document.removeEventListener('visibilitychange',visible);};
}
