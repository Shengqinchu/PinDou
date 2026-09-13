import { contentModule } from './content-store';
import defaults from './content/shop-ordering.json';
import { type CartLine, type Product, money } from './commerce';
import { formatCopy, tr } from './state';

export const orderWords=contentModule('shop-ordering',defaults);
export const manualStates=['manual_pending','manual_confirmed','manual_completed','manual_cancelled'] as const;
export const optionText=(p:Product|undefined,line:CartLine)=>{
 const variant=p?.variants?.find(x=>x.id===line.variant_id),choice=p?.choices?.find(x=>x.id===line.choice_id);
 return [variant?tr(variant.zh,variant.en):'',choice?tr(choice.zh,choice.en):''].filter(Boolean).join(' · ');
};
export const offerText=(p:Product)=>p.quantity_offer?formatCopy(orderWords.offer,{v0:p.quantity_offer.quantity,v1:money(p.quantity_offer.price_cents)}):'';
export const shopPayload=(lines:CartLine[])=>lines.map(l=>({product_id:l.product_id,quantity:l.quantity,variant_id:l.variant_id||'',choice_id:l.choice_id||''}));
export const orderable=(p:(Product&{shop_collection?:string})|undefined)=>!!p&&p.price_cents!==null&&(p.available_stock??p.stock)>0&&p.shop_collection!=='services';
export function previewTotal(lines:CartLine[],products:Product[]){
 const quantities=new Map<string,number>();for(const l of lines)quantities.set(l.product_id,(quantities.get(l.product_id)||0)+l.quantity);
 let total=0;for(const [id,q] of quantities){const p=products.find(x=>x.id===id);if(p?.price_cents==null)continue;
 const o=p.quantity_offer;total+=o?Math.floor(q/o.quantity)*o.price_cents+(q%o.quantity)*p.price_cents:q*p.price_cents;}
 return total;
}
