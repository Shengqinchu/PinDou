import { contentModule } from './content-store';
import defaults from './content/booking-profile.json';
import { commerceApi } from './commerce';
import { accountUser,accountCopy } from './account';
import { customerToken } from './account-storage';
import { say } from './state';
import visitDefaults from './content/pages-Visit.json';
const visitCopy=contentModule('pages-Visit',visitDefaults);
export const bookingProfileCopy=contentModule('booking-profile',defaults);
export type ContactDetails={name:string;contact_method:'wechat'|'phone'|'email'|'other';contact:string};
export type BookingProfile=ContactDetails&{owner_id:string;version:number;complete:boolean;updated_at:string;source_reservation_id:string;wechat_id?:string;delivery_address?:string};
export const emptyContact=():ContactDetails=>({name:'',contact_method:'wechat',contact:''});
export const contactDetails=(data:ContactDetails):ContactDetails=>({name:data.name,contact_method:data.contact_method,contact:data.contact});
export const sameContact=(a:ContactDetails,b:ContactDetails)=>a.name===b.name&&a.contact_method===b.contact_method&&a.contact===b.contact;
export const contactMethodLabel=(method:ContactDetails['contact_method'])=>say(visitCopy[({wechat:'wechat_2941d2',phone:'phone_ac7a62',email:'email_b6d15f',other:'another_way_f489b4'} as const)[method]]);
export function validContact(data:ContactDetails,allowEmpty=false){
 const name=data.name.trim(),contact=data.contact.trim();
 if(allowEmpty&&!name&&!contact)return true;
 if(!name||name.length>80||contact.length<(data.contact_method==='wechat'?1:3)||contact.length>180)return false;
 if(data.contact_method==='email')return /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(contact);
 if(data.contact_method==='phone')return /^[+\d ()-]{7,30}$/.test(contact)&&contact.replace(/\D/g,'').length>=7;
 return true;
}
export async function loadBookingProfile(id:string,token=customerToken()){
 const result=await commerceApi<BookingProfile>('/auth/booking-profile',{headers:{Authorization:'Bearer '+token}});
 if(result.owner_id!==id||accountUser.value?.id!==id||customerToken()!==token)throw new Error(say(accountCopy.account_login_required));
 return result;
}
export async function saveBookingProfile(id:string,token:string,details:ContactDetails,version:number,wechatId?:string,deliveryAddress?:string){
 if(accountUser.value?.id!==id||customerToken()!==token)throw new Error(say(accountCopy.account_login_required));
 const result=await commerceApi<BookingProfile>('/auth/booking-profile',{method:'PUT',headers:{Authorization:'Bearer '+token},body:JSON.stringify({...contactDetails(details),version,...(wechatId===undefined?{}:{wechat_id:wechatId.trim()}),...(deliveryAddress===undefined?{}:{delivery_address:deliveryAddress.trim()})})});
 if(result.owner_id!==id||accountUser.value?.id!==id||customerToken()!==token)throw new Error(say(accountCopy.account_login_required));
 window.dispatchEvent(new Event('studio-booking-profile-change'));
 return result;
}
