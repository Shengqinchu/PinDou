// The crop, slow drift and tactile gesture each own a separate transform layer.
import { gsap } from 'gsap';
import { onMotionPreferenceChange,reducedMotion } from './motion-preference';
export function installMotif(root:HTMLElement) {
  const floating=root.querySelector<HTMLElement>('.motif-float')!,touch=root.querySelector<HTMLElement>('.motif-touch')!;
  let drift:gsap.core.Tween|undefined,gesture:gsap.core.Timeline|undefined,near=false,hovered=false;
  const reverse=root.classList.contains('bone');
  const update=()=>{
    if(reducedMotion()){drift?.kill();gesture?.kill();gsap.set([floating,touch],{clearProps:'transform'});drift=undefined;return;}
    if(!drift)drift=gsap.to(floating,{y:reverse?-4:-3,rotation:reverse?3:-4,duration:reverse?4.8:4.2,ease:'sine.inOut',repeat:-1,yoyo:true,paused:true});
    if(near&&document.visibilityState==='visible')drift.resume();else drift.pause();
  };
  const settle=()=>gsap.to(touch,{rotation:hovered?(reverse?-10:14):0,scaleX:1,scaleY:1,duration:.85,ease:'sine.inOut',overwrite:true});
  const enter=(event:PointerEvent)=>{if(event.pointerType==='touch'||reducedMotion())return;hovered=true;if(!gesture?.isActive())settle();};
  const leave=()=>{hovered=false;if(!reducedMotion()&&!gesture?.isActive())settle();};
  const pinch=()=>{
    if(reducedMotion())return;
    gesture?.kill();gsap.killTweensOf(touch);
    gesture=gsap.timeline().to(touch,{scaleX:1.16,scaleY:.78,rotation:reverse?-8:8,duration:.22,ease:'power2.out'})
      .to(touch,{scaleX:1,scaleY:1,rotation:hovered?(reverse?-10:14):0,duration:1.1,ease:'elastic.out(1,.55)'});
  };
  const observer=new IntersectionObserver(([entry])=>{near=entry.isIntersecting;update();},{rootMargin:'60px'});
  observer.observe(root);const stop=onMotionPreferenceChange(update);
  root.addEventListener('pointerenter',enter);root.addEventListener('pointerleave',leave);
  root.addEventListener('click',pinch);document.addEventListener('visibilitychange',update);
  update();
  return()=>{observer.disconnect();stop();drift?.kill();gesture?.kill();gsap.killTweensOf(touch);root.removeEventListener('pointerenter',enter);root.removeEventListener('pointerleave',leave);root.removeEventListener('click',pinch);document.removeEventListener('visibilitychange',update);};
}
