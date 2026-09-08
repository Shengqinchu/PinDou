// Imported by both Vue Router and intent prefetch: one module request per route.
export const routeLoaders = {
  visit: () => import("./pages/Visit.vue"),
  details: () => import("./pages/Details.vue"),
  shop: () => import("./pages/Shop.vue"),
  journal: () => import("./pages/Journal.vue"),
};
export function installRoutePrefetch() {
  const connection = (navigator as Navigator & {connection?:{saveData?:boolean;effectiveType?:string}}).connection;
  const limited=()=>connection?.saveData || /(^|-)2g$/.test(connection?.effectiveType || '');
  const prefetched=new Set<string>();
  const prefetch=(name:string)=>{
    if(limited() || prefetched.has(name) || !(name in routeLoaders))return;
    prefetched.add(name);
    void routeLoaders[name as keyof typeof routeLoaders]().catch(()=>prefetched.delete(name));
  };
  let intent:ReturnType<typeof setTimeout>|undefined;
  const hover=(event:Event)=>{
    const anchor=(event.target as Element).closest<HTMLAnchorElement>('a[href]');
    if(!anchor || anchor.origin!==location.origin || event.type==='pointerover' && (event as PointerEvent).pointerType==='touch')return;
    const name=anchor.pathname.split('/').filter(Boolean)[0] || '';
    clearTimeout(intent);intent=setTimeout(()=>prefetch(name),event.type==='focusin'?0:100);
  };
  const cancel=()=>clearTimeout(intent);
  document.addEventListener('pointerover',hover);document.addEventListener('focusin',hover);
  document.addEventListener('pointerout',cancel);
  // Only warm the next likely action, after initial load/idle. Never fetch personal
  // reservation/order pages, payment endpoints or admin resources speculatively.
  let idle:number|undefined;
  const load=()=>{
    if(location.pathname!=='/' || limited())return;
    if('requestIdleCallback' in window)idle=window.requestIdleCallback(()=>prefetch('visit'),{timeout:5000});
  };
  window.addEventListener('load',load,{once:true});
  return ()=>{clearTimeout(intent);if(idle!==undefined)window.cancelIdleCallback?.(idle);window.removeEventListener('load',load);document.removeEventListener('pointerover',hover);document.removeEventListener('focusin',hover);document.removeEventListener('pointerout',cancel);};
}
