import { contentModule } from './content-store';
import defaults from './content/wechat.json';
export const wechatCopy=contentModule('wechat',defaults);

// Restrict navigation to site pages, including generator paths. Never accept an
// external return URL from a login link or provider response.
export function accountReturn(value:unknown,fallback='/account'):string{
  if(typeof value!=='string'||value.length>600)return fallback;
  try{
    const parsed=new URL(value,location.origin);
    if(!value.startsWith('/')||value.startsWith('//')||parsed.origin!==location.origin||/[\\\x00-\x1f]/.test(decodeURIComponent(value)))return fallback;
    if(!/^\/(?:tools(?:\/(?:upload|tutorial|loading|works|(?:editor|result)\/[\w-]+))?|visit|upload|tutorial|loading|works|details|shop|journal(?:\/[\w-]+)?|account|(?:reservation|editor|result)\/[\w-]+)?$/.test(parsed.pathname))return fallback;
    return parsed.pathname+parsed.search+parsed.hash;
  }catch{return fallback;}
}
