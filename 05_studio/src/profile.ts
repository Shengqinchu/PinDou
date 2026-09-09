import { contentModule } from './content-store';
import defaults from './content/profile.json';
import { accountCopy,accountUser,applyAccountProfile } from './account';
import { customerToken } from './account-storage';
import { say } from './state';
export const profileCopy=contentModule('profile',defaults);
export const normalizeNickname=(value:string)=>value.trim().replace(/\s+/gu,' ');
export function imageError(file:File):string{
  if(!['image/jpeg','image/png','image/webp'].includes(file.type))return say(profileCopy.image_invalid);
  return file.size>2*1024*1024?say(profileCopy.image_large):'';
}
// Reuse the generator's authenticated profile endpoints and its existing image validation.
// Every request is tied to the account that opened the editor, including between two saves.
export async function saveProfilePart(token:string,id:string,part:{nickname:string}|File){
  if(!token||customerToken()!==token||accountUser.value?.id!==id)throw new Error(say(accountCopy.account_login_required));
  const avatar=part instanceof File;
  const body=avatar?new FormData():JSON.stringify(part);
  if(body instanceof FormData)body.append('image',part as File);
  let response:Response;
  try{
    response=await fetch(`/api/v1/user/${avatar?'avatar':'profile'}`,{
      method:avatar?'POST':'PATCH',headers:{Authorization:`Bearer ${token}`,...(!avatar?{'Content-Type':'application/json'}:{})},
      body,cache:'no-store',redirect:'error',
    });
  }catch{throw new Error(say(avatar?profileCopy.avatar_error:profileCopy.save_error));}
  const data=await response.json().catch(()=>null);
  if(!response.ok){
    const words=response.status===401?accountCopy.account_login_required:response.status===429?accountCopy.account_rate_limited:
      avatar?(response.status===413?profileCopy.image_large:profileCopy.avatar_error):response.status===422?profileCopy.name_rejected:profileCopy.save_error;
    throw new Error(say(words));
  }
  const profile=avatar?data?.user:data;
  if(!profile||profile.user_id!==id||typeof profile.email!=='string')throw new Error(say(profileCopy.save_error));
  if(!applyAccountProfile(profile,token))throw new Error(say(accountCopy.account_login_required));
  return profile;
}
