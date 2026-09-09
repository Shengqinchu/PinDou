import { locale } from '../../05_studio/src/state';
import { contentModule } from '../../05_studio/src/content-store';
import defaults from '../../05_studio/src/content/generator.json';
const copy=contentModule('generator',defaults) as Record<string,string[]>;
const exact=new Map(Object.entries(defaults).map(([key,pair])=>[pair[0].trim(),key]));
const escape=(s:string)=>s.replace(/[.*+?^${}()|[\]\\]/g,'\\$&');
const dynamic=Object.entries(defaults).filter(([,pair])=>/\{v\d+\}/.test(pair[0])).map(([key,pair])=>({key,
  slots:[...pair[0].matchAll(/\{(v\d+)\}/g)].map(m=>m[1]),
  re:new RegExp('^'+pair[0].split(/\{v\d+\}/).map(escape).join('(.+?)')+'$'),length:pair[0].length,
})).sort((a,b)=>b.length-a.length);
export function gt(value:unknown,depth=0):string{
 if(value==null)return '';const original=String(value),text=original.trim();
 const key=exact.get(text);if(key)return copy[key][locale.value==='zh'?0:1];
 if(locale.value==='zh'||!/[\u3400-\u9fff]/.test(text))return original;
 if(depth<5)for(const pattern of dynamic){const match=text.match(pattern.re);if(match){
  let result=copy[pattern.key][1];pattern.slots.forEach((slot,i)=>{result=result.replaceAll('{'+slot+'}',gt(match[i+1],depth+1));});return result;
 }}
 // Unknown provider messages remain actionable in English; no untranslated server prose.
 return 'We could not complete this action. Please try again.';
}
export const generatorLocale=locale;
