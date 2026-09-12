import type { ShopProduct } from './shop';

export function matchProductImage(filename:string,products:Pick<ShopProduct,'id'|'code'>[]):string {
  const stem=filename.replace(/\.[^.]+$/,'').trim().toUpperCase();
  const exact=products.filter(p=>p.id.toUpperCase()===stem||(p.code&&p.code.toUpperCase()===stem));
  if(exact.length)return exact.length===1?exact[0].id:'';
  const withoutIndex=stem.replace(/[-_ ]\d+$/,'');
  if(withoutIndex===stem)return '';
  const indexed=products.filter(p=>p.id.toUpperCase()===withoutIndex||(p.code&&p.code.toUpperCase()===withoutIndex));
  return indexed.length===1?indexed[0].id:'';
}

export function centsFromInput(value:string):number|null {
  const text=value.trim();
  if(!text)return null;
  if(!/^\d{1,5}(\.\d{1,2})?$/.test(text))throw new Error('invalid_price');
  const [whole,fraction='']=text.split('.');
  const cents=Number(whole)*100+Number(fraction.padEnd(2,'0'));
  if(cents<1||cents>1000000)throw new Error('invalid_price');
  return cents;
}
