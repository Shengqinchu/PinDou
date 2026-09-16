import { shallowRef } from 'vue';
import { studioRead } from './miniapp-client';
import home from '../../../05_studio/src/content/pages-Home.json';
import visit from '../../../05_studio/src/content/pages-Visit.json';
import flow from '../../../05_studio/src/content/visit-flow.json';
import calendar from '../../../05_studio/src/content/components-ReservationCalendar.json';
import receipt from '../../../05_studio/src/content/pages-ReservationReceipt.json';
import cancellation from '../../../05_studio/src/content/reservation-cancellation.json';
import booking from '../../../05_studio/src/content/booking-profile.json';
import account from '../../../05_studio/src/content/account.json';
import wallet from '../../../05_studio/src/content/wallet.json';
import app from '../../../05_studio/src/content/App.json';
import details from '../../../05_studio/src/content/pages-Details.json';
import errors from '../../../05_studio/src/content/data-commerce-messages.json';
import generic from '../../../05_studio/src/content/commerce.json';
import miniapp from '../../../05_studio/src/content/miniapp.json';
import rates from '../../../05_studio/src/content/experience-rates.json';
import studio from '../../../05_studio/src/content/studio-profile.json';
import profile from '../../../05_studio/src/content/profile.json';
import notifications from '../../../05_studio/src/content/customer-notifications.json';
import process from '../../../05_studio/src/content/components-BeadingProcess.json';
import contacts from '../../../05_studio/src/content/contact-fields.json';
import media from '../../../05_studio/src/media-assets.json';

const defaults={home,visit,flow,calendar,receipt,cancellation,booking,account,wallet,app,details,errors,generic,miniapp,profile,process,contacts};
const names:Record<keyof typeof defaults,string>={home:'pages-Home',visit:'pages-Visit',flow:'visit-flow',calendar:'components-ReservationCalendar',receipt:'pages-ReservationReceipt',cancellation:'reservation-cancellation',booking:'booking-profile',account:'account',wallet:'wallet',app:'App',details:'pages-Details',errors:'data-commerce-messages',generic:'commerce',miniapp:'miniapp',profile:'profile',process:'components-BeadingProcess',contacts:'contact-fields'};
const published=shallowRef<Record<string,Record<string,unknown>>>({});
let pending:Promise<void>|undefined,updated=0;
export function refreshStudioContent(){
  if(pending)return pending;
  if(Date.now()-updated<60000)return Promise.resolve();
  pending=studioRead<{modules:Record<string,Record<string,unknown>>}>('/content').then(value=>{if(value.modules){published.value=value.modules;updated=Date.now();}}).catch(()=>{}).finally(()=>{pending=undefined;});
  return pending;
}
export function studioWords(module:keyof typeof defaults,key:string):string[]{
  const value=published.value[names[module]]?.[key];
  if(Array.isArray(value)&&value.length===2&&value.every(v=>typeof v==='string'))return value;
  return (defaults[module] as Record<string,string[]>)[key]||miniapp.generic_error;
}
export function studioRate(key:keyof typeof rates){
  const value=published.value['rate-fields']?.[key];
  return Array.isArray(value)&&typeof value[0]==='string'?value[0]:rates[key];
}
export function studioPhoto(){
  const value=(published.value.media?.['hero-illustration'] as {src?:string}|undefined)?.src;
  return value?.startsWith('/')&&!value.startsWith('//')?'https://pindoupuppy.com'+value:'/static/studio/hero.webp';
}
export const studioProfile=studio;
export type StudioMedia={src:string;width:number;height:number};
export function studioMedia(name:keyof typeof media):StudioMedia{
  const fallback=media[name],override=published.value.media?.[name] as Partial<StudioMedia>|undefined;
  const source=override?.src;
  const valid=typeof source==='string'&&((source.startsWith('/')&&!source.startsWith('//'))||source.startsWith('https://pindoupuppy.com/'));
  const src=valid?source!:fallback.src;
  const dimension=(value:unknown,original:number)=>typeof value==='number'&&Number.isFinite(value)&&value>0?value:original;
  return {src:src.startsWith('/')?'https://pindoupuppy.com'+src:src,width:dimension(valid?override?.width:undefined,fallback.width),height:dimension(valid?override?.height:undefined,fallback.height)};
}
export function bookingError(code:string):string[]{
  if(code in notifications)return (notifications as Record<string,string[]>)[code];
  if(code==='booking_profile_changed')return booking.changed;
  if(code==='booking_contact_invalid')return booking.incomplete;
  for(const group of ['errors','cancellation','account','miniapp'] as const)if(code in defaults[group])return studioWords(group,code);
  if(code==='reservation_rate_limit')return generic.too_many_requests_please_try_again_later_e30269;
  return miniapp.generic_error;
}
export function fillWords(words:string[],language:string,values:Record<string,string|number>){
  return words[language==='en'?1:0].replace(/\{(v\d+)\}/g,(match,key)=>values[key]===undefined?match:String(values[key]));
}
