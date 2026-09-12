import defaults from './content/wallet.json';
import { contentModule } from './content-store';
import { formatCopy,locale } from './state';
import type { BookingProfile } from './booking-profile';
export const walletCopy=contentModule('wallet',defaults);
export type WalletAccount={owner_id:string;name:string;email:string;avatar?:string;customer_code?:string;contacts?:{kind:'wechat'|'email'|'phone'|'other';value:string}[];minutes:number;points:number;version:number;redeemable_cad:number;points_per_cad:number;visit_reward:number;updated_at:string;staff_note?:string;booking_profile?:BookingProfile};
export type WalletEntry={id:number;kind:string;created_at:string;effective_date:string;minutes_delta:number;points_delta:number;minutes_balance:number;points_balance:number;note:string;reservation_id:string;reverses_id:number|null;reversed_by:number|null;bill_cents:number|null;redemption_use?:string;no_promotion?:boolean|null;actor?:string};
export type WalletDetail={account:WalletAccount;entries:WalletEntry[];total:number;page:number;booking_profile:BookingProfile};
export type WalletCategory='all'|'time'|'points';
export function duration(minutes:number){
  const hours=new Intl.NumberFormat(locale.value==='zh'?'zh-CN':'en-CA',{maximumFractionDigits:2}).format(Math.abs(minutes)/60);
  return formatCopy(walletCopy.whole_hours,{v0:hours});
}
