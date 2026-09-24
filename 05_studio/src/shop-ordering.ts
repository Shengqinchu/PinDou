import { contentModule } from './content-store';
import defaults from './content/shop-ordering.json';
import { type CartLine, type Product, money } from './commerce';
import { formatCopy, say, tr } from './state';

export const orderWords=contentModule('shop-ordering',defaults);
export const manualStates=['manual_pending','manual_preparing','manual_ready','manual_completed','manual_cancelled'] as const;
export const manualStatus=(status:string,delivery?:string)=>say(status==='manual_ready'&&delivery==='courier'?orderWords.manual_shipped:orderWords[status as keyof typeof defaults]||[status,status]);
export const optionText=(p:Product|undefined,line:CartLine)=>{
 const variant=p?.variants?.find(x=>x.id===line.variant_id),choice=p?.choices?.find(x=>x.id===line.choice_id);
 return [variant?tr(variant.zh,variant.en):'',choice?tr(choice.zh,choice.en):''].filter(Boolean).join(' · ');
};
export const offerText=(p:Product)=>p.quantity_offer?formatCopy(orderWords.offer,{v0:p.quantity_offer.quantity,v1:money(p.quantity_offer.price_cents)}):'';
export const variantPrice=(p:Product|undefined,id?:string)=>p?.variants?.find(v=>v.id===id)?.price_cents??p?.price_cents??null;
export const hasVariantPrices=(p:Product)=>!!p.variants?.some(v=>v.price_cents!=null);
export const minimumPrice=(p:Product)=>p.variants?.length?Math.min(...p.variants.map(v=>v.price_cents??p.price_cents??0)):p.price_cents??0;
export function priceRange(p:Product){
 if(p.price_cents===null)return '';
 const prices=p.variants?.length?p.variants.map(v=>v.price_cents??p.price_cents!):[p.price_cents];
 const low=Math.min(...prices),high=Math.max(...prices);
 return low===high?(low/100).toFixed(2):`${(low/100).toFixed(2)}–${(high/100).toFixed(2)}`;
}
export const shopPayload=(lines:CartLine[])=>lines.map(l=>({product_id:l.product_id,quantity:l.quantity,variant_id:l.variant_id||'',choice_id:l.choice_id||''}));
export const orderable=(p:(Product&{shop_collection?:string})|undefined)=>!!p&&p.price_cents!==null&&(p.available_stock??p.stock)>0&&p.shop_collection!=='services';
export function previewTotal(lines:CartLine[],products:Product[]){
 const quantities=new Map<string,number>();let total=0;
 for(const l of lines){const p=products.find(x=>x.id===l.product_id);if(p?.price_cents==null)continue;
 const override=p.variants?.find(v=>v.id===l.variant_id)?.price_cents;
 if(override!=null)total+=override*l.quantity;else quantities.set(l.product_id,(quantities.get(l.product_id)||0)+l.quantity);}
 for(const [id,q] of quantities){const p=products.find(x=>x.id===id);if(p?.price_cents==null)continue;
 const o=p.quantity_offer;total+=o?Math.floor(q/o.quantity)*o.price_cents+(q%o.quantity)*p.price_cents:q*p.price_cents;}
 return total;
}
