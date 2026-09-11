import {useUserStore} from '../store/user';
export type SharedProfile={user_id:string;nickname:string;avatar:string;email?:string;[key:string]:any};
export class ProfileError extends Error{constructor(public code:string,public status=0){super(code);}}
export const normalizedName=(value:string)=>value.trim().replace(/\s+/gu,' ');
export const validName=(value:string)=>{const size=[...normalizedName(value)].length;return size>=1&&size<=20;};
export function assertProfileOwner(token:string,id:string){
 const user=useUserStore();
 if(!token||user.token!==token||(user.userInfo?.user_id&&user.userInfo.user_id!==id))throw new ProfileError('account_login_required',401);
}
function responseProfile(data:any,token:string,id:string){
 assertProfileOwner(token,id);
 if(data?.user_id!==id||typeof data.nickname!=='string'||(data.avatar!=null&&typeof data.avatar!=='string'))throw new ProfileError('save_error');
 const user=useUserStore();user.userInfo={...user.userInfo,...data};uni.setStorageSync('pd_user',JSON.stringify(user.userInfo));return data as SharedProfile;
}
export function saveNickname(token:string,id:string,nickname:string):Promise<SharedProfile>{
 assertProfileOwner(token,id);if(!validName(nickname))throw new ProfileError('name_invalid');
 return new Promise((resolve,reject)=>uni.request({url:'https://pindoupuppy.com/api/v1/user/profile',method:'PATCH',header:{Authorization:'Bearer '+token,'Content-Type':'application/json'},data:{nickname:normalizedName(nickname)},timeout:20000,
 success:r=>{if(r.statusCode!==200){reject(new ProfileError(r.statusCode===401?'account_login_required':r.statusCode===422?'name_rejected':'save_error',r.statusCode));return;}try{resolve(responseProfile(r.data,token,id));}catch(e){reject(e);}},fail:()=>reject(new ProfileError('save_error'))}));
}
export async function validateAvatar(path:string){
 let size=0,mimeType='';
 // #ifdef MP-WEIXIN
 size=await new Promise<number>((resolve,reject)=>uni.getFileInfo({filePath:path,success:r=>resolve(r.size),fail:()=>reject(new ProfileError('image_invalid'))}));
 // #endif
 // #ifdef H5
 const blob=await(await fetch(path)).blob();size=blob.size;mimeType=blob.type.replace(/^image\//,'');
 // #endif
 if(size>2*1024*1024)throw new ProfileError('image_large');
 const info=await new Promise<UniApp.GetImageInfoSuccessData>((resolve,reject)=>uni.getImageInfo({src:path,success:resolve,fail:()=>reject(new ProfileError('image_invalid'))}));
 if(!['jpg','jpeg','png','webp'].includes((mimeType||info.type||'').toLowerCase()))throw new ProfileError('image_invalid');
 return path;
}
export function saveAvatar(token:string,id:string,path:string):Promise<SharedProfile>{
 assertProfileOwner(token,id);
 return new Promise((resolve,reject)=>uni.uploadFile({url:'https://pindoupuppy.com/api/v1/user/avatar',filePath:path,name:'image',header:{Authorization:'Bearer '+token},timeout:20000,
 success:r=>{if(r.statusCode!==200){reject(new ProfileError(r.statusCode===401?'account_login_required':r.statusCode===413?'image_large':'avatar_error',r.statusCode));return;}try{resolve(responseProfile(JSON.parse(r.data).user,token,id));}catch(e){reject(e instanceof ProfileError?e:new ProfileError('avatar_error'));}},fail:()=>reject(new ProfileError('avatar_error'))}));
}
