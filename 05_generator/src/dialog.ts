import type { ObjectDirective } from 'vue';
import { lockPageScroll } from '../../05_studio/src/browser';
const cleanups=new WeakMap<HTMLDialogElement,()=>void>();
export const vToolDialog:ObjectDirective<HTMLDialogElement,()=>void>={
 mounted(element,binding){
  const trigger=document.activeElement instanceof HTMLElement?document.activeElement:null;
  const unlock=lockPageScroll();
  const cancel=(event:Event)=>{event.preventDefault();binding.value();};
  const outside=(event:MouseEvent)=>{const b=element.getBoundingClientRect();if(event.target===element&&(event.clientX<b.left||event.clientX>b.right||event.clientY<b.top||event.clientY>b.bottom))binding.value();};
  element.classList.add('tool-native-dialog');element.addEventListener('cancel',cancel);element.addEventListener('click',outside);element.showModal();
  cleanups.set(element,()=>{element.close();unlock();element.removeEventListener('cancel',cancel);element.removeEventListener('click',outside);if(trigger?.isConnected)trigger.focus({preventScroll:true});});
 },beforeUnmount(element){cleanups.get(element)?.();cleanups.delete(element);}
};
