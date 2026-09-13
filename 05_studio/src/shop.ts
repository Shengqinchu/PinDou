import { ref } from 'vue';
import { contentModule } from './content-store';
import defaults from './content/shop.json';
import { commerceApi, type Product, orderKey } from './commerce';
import { media } from './state';
export const shopWords=contentModule('shop',defaults);
export const productTextLimits={name:200,description:10000} as const;
export const productTextLength=(text:string)=>Array.from(text).length;
export function productIntro(text:string){
  const lines=text.split(/\r?\n/),characters=Array.from(lines.slice(0,3).join('\n'));
  const shortened=lines.length>3||characters.length>180;
  return {text:shortened?characters.slice(0,180).join('').trimEnd()+'…':text,shortened};
}
export type ShopCategory={id:string;parent_id:string|null;zh:string;en:string;sort:number;visible:boolean;version:number};
export type ShopProduct=Product & {images:string[];shop_collection:'home'|'finished'|'services';shop_category_id:string|null;shop_visible:boolean;code:string;sort:number};
export type ShopCatalog={products:ShopProduct[];categories:ShopCategory[];checkout_ready:boolean;manual_ordering_ready?:boolean;sources?:Record<string,{platform:string;title:string;source_min_fen:number;source_currency:string;captured_at:string}>};
export const shopCatalog=ref<ShopCatalog>();
let pending:Promise<void>|undefined;
export function loadShop(force=false):Promise<void>{
  if(pending)return pending;
  if(shopCatalog.value&&!force)return Promise.resolve();
  pending=commerceApi<ShopCatalog>('/shop/catalog').then(d=>{shopCatalog.value=d}).finally(()=>{pending=undefined});
  return pending;
}
export const shopImage=(src:string)=>src.startsWith('/')?src:src?media(src):'';
export function savedShopOrders():string[]{
  try {return Object.keys(JSON.parse(localStorage.getItem('puppy-order-access-v2')||'{}')).filter(id=>/^PS[A-F0-9]{24}$/.test(id)&&orderKey(id)).reverse();}catch{return [];}
}
