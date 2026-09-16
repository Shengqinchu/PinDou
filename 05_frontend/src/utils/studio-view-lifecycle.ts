import {computed,inject,onBeforeUnmount,provide,watch,type ComputedRef,type InjectionKey} from 'vue';
import {onShow,onHide,onUnload,onLoad} from '@dcloudio/uni-app';
type ViewContext={active:ComputedRef<boolean>;query:ComputedRef<Record<string,string>>};
const key:InjectionKey<ViewContext>=Symbol('studio-visible-view');
export function provideView(active:()=>boolean,query:()=>Record<string,string>){provide(key,{active:computed(active),query:computed(query)});}
export function useViewActive(){return inject(key,undefined)?.active;}
export function onViewShow(callback:()=>void){const view=inject(key,undefined);if(view)watch(view.active,active=>{if(active)callback();},{immediate:true,flush:'post'});else onShow(callback);}
export function onViewHide(callback:()=>void){const view=inject(key,undefined);if(view)watch(view.active,(active,was)=>{if(was&&!active)callback();},{flush:'sync'});else onHide(callback);}
export function onViewUnload(callback:()=>void){if(inject(key,undefined))onBeforeUnmount(callback);else onUnload(callback);}
export function onViewLoad(callback:(query:Record<string,string>)=>void){
 const view=inject(key,undefined);
 if(view)watch(()=>view.active.value?view.query.value:undefined,query=>{if(query)callback(query);},{immediate:true,flush:'sync'});
 else onLoad(query=>callback((query||{}) as Record<string,string>));
}
