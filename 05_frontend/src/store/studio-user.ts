import {defineStore} from 'pinia';
import {MiniappError} from '../utils/miniapp-client';
import {readStudioCached,setStudioCacheOwner} from '../utils/studio-cache';

// The shop shares login credentials with the website, not its generator runtime.
export type StudioUser={id?:string;user_id?:string;nickname?:string;email?:string;avatar?:string;is_admin?:boolean};
function storedUser():StudioUser|null{
 try{const value=uni.getStorageSync('pd_user');return typeof value==='string'?JSON.parse(value):null;}catch{return null;}
}
export const useUserStore=defineStore('studio-user',{
 state:()=>({token:uni.getStorageSync('pd_token')||'',userInfo:storedUser()}),
 getters:{isLoggedIn:state=>!!state.token},
 actions:{
  async fetchProfile(){
   const token=this.token;if(!token)return null;
   setStudioCacheOwner(token);
   try{
    const result=await readStudioCached<{user:StudioUser}>('/auth/me',token,30000);
    if(this.token!==token)return null;
    this.userInfo={...result.user,user_id:result.user.id||result.user.user_id};
    uni.setStorageSync('pd_user',JSON.stringify(this.userInfo));return this.userInfo;
   }catch(error){if(this.token===token&&error instanceof MiniappError&&error.status===401)this.logout();throw error;}
  },
  logout(){this.token='';this.userInfo=null;setStudioCacheOwner('');uni.removeStorageSync('pd_token');uni.removeStorageSync('pd_user');},
 },
});
