// Public, non-personal snapshots (published copy, open booking times, shop catalog) kept
// across launches so pages can paint at once and refresh in the background. Account,
// balance, booking and contact data never come through here.
const PREFIX='pd_public:';
type Stored<T>={at:number;data:T};
export function readPublic<T>(name:string,maxAge:number):Stored<T>|undefined{
 try{
  if(typeof uni==='undefined')return;
  const value=uni.getStorageSync(PREFIX+name) as Stored<T>|'';
  if(value&&typeof value.at==='number'&&Date.now()-value.at>=0&&Date.now()-value.at<=maxAge)return value;
 }catch{/* storage is an optimisation only */}
}
export function writePublic<T>(name:string,data:T){
 try{if(typeof uni!=='undefined')uni.setStorageSync(PREFIX+name,{at:Date.now(),data});}catch{/* full or unavailable storage just skips caching */}
}
