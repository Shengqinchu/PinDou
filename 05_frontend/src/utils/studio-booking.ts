// Protocol and interval rules shared with the existing reservation service.
// This module is platform-independent so calendar edge cases can be tested.
export type Plan='hourly'|'day'|'patch'|'';
export type Booking={date:string;start:string;end:string;plan:Plan;guests:number};
export type Slot={start:string;end:string;available:boolean;start_available?:boolean;reason:string|null;remaining_seats?:number|null;capacity_full?:boolean;buffered?:boolean;low_capacity?:boolean;booked_groups?:number};
export type Day={date:string;open:string;close:string;closed:boolean;slots:Slot[]};
export type Calendar={experience?:'beads'|'patch';today:string;timezone:string;minimum_minutes:number;max_guests_per_group:number;policy_version:number;days:Day[]};
export type Contact={name:string;contact_method:'wechat'|'phone'|'email'|'other';contact:string};
export type ContactProfile=Contact&{owner_id:string;version:number;complete:boolean;wechat_id?:string};
export type ContactContext={can_omit_details:boolean;profile:ContactProfile};
export type Payload=Contact&{booking:Booking;notes:string;locale:'zh'|'en';website:'';contact_profile_version:number};
export type Attempt={owner:string;key:string;body:Payload};
export type Receipt={id:string;status:'pending'|'confirmed'|'completed'|'cancelled';name:string;booking:Booking;can_cancel:boolean;can_edit?:boolean;previous_visit?:{booking:Booking;actual_minutes:number|null;actual_guests:number|null}|null;version:number;booked_minutes:number;actual_minutes:number|null;actual_guests:number|null;public_note:string};
export type CancelPolicy={limit:number;used:number;remaining:number;reset_date:string;month:string;timezone:string;eligible:boolean;reason:string|null;version:number};
export const emptyBooking=():Booking=>({date:'',start:'',end:'',plan:'',guests:1});
export const emptyContact=():Contact=>({name:'',contact_method:'wechat',contact:''});
export function minutes(time:string){if(!/^\d{2}:\d{2}$/.test(time))return NaN;const [h,m]=time.split(':').map(Number);return (h<=23&&[0,30].includes(m))||(h===24&&m===0)?h*60+m:NaN;}
export function experienceFor(plan:Plan){return plan==='patch'?'patch':'beads';}
export function calendarPath(booking:Booking){return '/reservation-calendar?guests='+booking.guests+'&experience='+experienceFor(booking.plan);}
export function clock(value:number){return String(Math.floor(value/60)).padStart(2,'0')+':'+String(value%60).padStart(2,'0');}
export function validBooking(calendar:Calendar|null,booking:Booking){
  const day=calendar?.days.find(d=>d.date===booking.date),start=minutes(booking.start),end=minutes(booking.end);
  if(!day||day.closed||!['hourly','day','patch'].includes(booking.plan)||(calendar!.experience||'beads')!==experienceFor(booking.plan)||!Number.isInteger(booking.guests)||booking.guests<1||booking.guests>calendar!.max_guests_per_group||!Number.isFinite(start)||!Number.isFinite(end)||(booking.plan==='patch'?end-start!==60:end-start<calendar!.minimum_minutes)||start<minutes(day.open)||end>minutes(day.close)||(booking.plan==='day'&&booking.end!==day.close))return false;
  const slots=day.slots.filter(s=>minutes(s.start)>=start&&minutes(s.start)<end);
  if(booking.plan==='patch'&&slots[0]?.start_available===false)return false;
  return slots.length===(end-start)/30&&slots.every((slot,index)=>slot.available&&minutes(slot.start)===start+index*30&&minutes(slot.end)===start+(index+1)*30);
}
export function chooseCell(calendar:Calendar,booking:Booking,day:Day,slot:Slot,choosingEnd:boolean){
  if(!slot.available||(booking.plan==='patch'&&slot.start_available===false))return null;
  const extend=booking.plan==='hourly'&&choosingEnd&&booking.date===day.date&&minutes(slot.end)-minutes(booking.start)>=calendar.minimum_minutes;
  const next:Booking=extend?{...booking,end:slot.end}:{...booking,date:day.date,start:slot.start,end:booking.plan==='day'?day.close:clock(minutes(slot.start)+(booking.plan==='patch'?60:calendar.minimum_minutes))};
  return validBooking(calendar,next)?{booking:next,choosingEnd:!extend&&booking.plan==='hourly'}:null;
}
export function validContact(contact:Contact,allowEmpty=false){
  const name=contact.name.trim(),value=contact.contact.trim();
  if(allowEmpty&&!name&&!value)return true;
  if(!name||name.length>80||value.length<3||value.length>180)return false;
  if(contact.contact_method==='email')return /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(value);
  if(contact.contact_method==='phone')return /^[+\d ()-]{7,30}$/.test(value)&&value.replace(/\D/g,'').length>=7;
  return ['wechat','other'].includes(contact.contact_method);
}
export function retryUnchanged(status:number,code:string){
  return status===0||status>=500||['reservation_request_changed','reservation_session_missing','account_login_required'].includes(code);
}
export function requestId(){
  // Uniqueness for idempotency, not an authentication credential.
  return 'xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx'.replace(/[xy]/g,c=>{const n=Math.floor(Math.random()*16);return (c==='x'?n:(n&3)|8).toString(16);});
}
export function shortDate(date:string,language:string){
  const value=new Date(date+'T12:00:00Z');
  if(!Number.isFinite(value.getTime()))return date;
  try{return new Intl.DateTimeFormat(language==='en'?'en-CA':'zh-CN',{month:'short',day:'numeric',timeZone:'UTC'}).format(value);}
  catch{return date.slice(5).replace('-','/');}
}
