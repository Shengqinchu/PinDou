// Read-only shop showcase: the same public catalog as the website shop, without cart or ordering.
import {studioRead} from './miniapp-client';
const ORIGIN='https://pindoupuppy.com';
export type ShopVariant={id:string;zh:string;en:string;price_cents:number|null};
export type ShopProduct={id:string;zh:string;en:string;detailZh?:string;detailEn?:string;images:string[];shop_collection:'home'|'finished'|'services';shop_category_id:string|null;shop_visible?:boolean;code:string;sort:number;price_cents:number|null;variants?:ShopVariant[]};
export type ShopCategory={id:string;parent_id:string|null;zh:string;en:string;sort:number;visible?:boolean};
export type ShopCatalog={products:ShopProduct[];categories:ShopCategory[]};
let cached:ShopCatalog|undefined,cachedAt=0,pending:Promise<ShopCatalog>|undefined;
export function loadCatalog(force=false):Promise<ShopCatalog>{
 if(cached&&!force&&Date.now()-cachedAt<60000)return Promise.resolve(cached);
 if(pending)return pending;
 pending=studioRead<ShopCatalog>('/shop/catalog').then(data=>{
  cached={products:(data.products||[]).filter(p=>p.shop_visible!==false).sort((a,b)=>a.sort-b.sort),categories:(data.categories||[]).filter(c=>c.visible!==false).sort((a,b)=>a.sort-b.sort)};
  cachedAt=Date.now();return cached;
 }).finally(()=>{pending=undefined;});
 return pending;
}
export const cachedProduct=(id:string)=>cached?.products.find(p=>p.id===id);
// Uploaded originals have fixed-width previews (320/480/800) on the studio server.
export function imageUrl(src:string,width:320|480|800){
 const match=/^\/studio-api\/media\/([a-f0-9]{64}\.(?:jpg|png|webp))$/.exec(src);
 return ORIGIN+(match?`/studio-api/media/previews/v1/${width}/${match[1]}`:src);
}
// Same rules as the website: lowest variant price, "and up" when variants differ.
export const hasVariantPrices=(p:ShopProduct)=>!!p.variants?.some(v=>v.price_cents!=null);
export const minimumPrice=(p:ShopProduct)=>p.variants?.length?Math.min(...p.variants.map(v=>v.price_cents??p.price_cents??0)):p.price_cents??0;
export const amount=(cents:number)=>(cents/100).toFixed(2);
export function priceRange(p:ShopProduct){
 if(p.price_cents===null)return '';
 const prices=p.variants?.length?p.variants.map(v=>v.price_cents??p.price_cents!):[p.price_cents];
 const low=Math.min(...prices),high=Math.max(...prices);
 return low===high?amount(low):`${amount(low)}–${amount(high)}`;
}
export function intro(text:string){const line=(text||'').split(/\r?\n/).find(item=>item.trim())||'';return line.length>48?line.slice(0,48)+'…':line;}
