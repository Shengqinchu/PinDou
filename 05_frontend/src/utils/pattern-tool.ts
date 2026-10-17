// Standard (colour-quantised) bead patterns, free for everyone. AI generation,
// credits and purchases stay on the website; this client never calls them.
const API='https://pindoupuppy.com/api/v1';
const ORIGIN='https://pindoupuppy.com';
const DEVICE_KEY='pd_pattern_device';

export type PatternColor={code:string;hex:string;count:number};
// `sheet` is the full PatternSheet the editor works on; `viaAccount` records which identity owns it.
export type PatternResult={artworkId:string;imageUrl:string;total:number;colors:PatternColor[];sheet:any;viaAccount:boolean};
export type PatternErrorCode='pattern_error_busy'|'pattern_error_large'|'pattern_error_network'|'pattern_error';
export class PatternError extends Error{constructor(public code:PatternErrorCode,public status=0){super(code);}}

type Reply={statusCode:number;data:any};
function call(path:string,method:'GET'|'POST'|'PUT',data:unknown,header:Record<string,string>):Promise<Reply>{
 return new Promise((resolve,reject)=>uni.request({
  url:API+path,method,data:data as UniApp.RequestOptions['data'],timeout:60000,
  header:{'Content-Type':'application/json',...header},
  success:response=>resolve({statusCode:response.statusCode,data:response.data}),
  fail:()=>reject(new PatternError('pattern_error_network')),
 }));
}

// Signed-in visitors generate into their shared account (visible under My works
// on the website); everyone else uses a signed device identity from the backend.
async function deviceHeader():Promise<Record<string,string>>{
 let token=uni.getStorageSync(DEVICE_KEY)||'';
 if(!token){
  const reply=await call('/wallet/profile','GET',undefined,{});
  token=typeof reply.data?.device_token==='string'?reply.data.device_token:'';
  if(token)uni.setStorageSync(DEVICE_KEY,token);
 }
 return token?{'X-PinDou-Device':token}:{};
}
async function identity(useAccount:boolean):Promise<Record<string,string>>{
 const token=useAccount?uni.getStorageSync('pd_token')||'':'';
 return token?{Authorization:'Bearer '+token}:deviceHeader();
}

export function readPhotoBase64(path:string):Promise<string>{
 // #ifdef H5
 return fetch(path).then(response=>response.blob()).then(blob=>new Promise<string>((resolve,reject)=>{const reader=new FileReader();reader.onload=()=>resolve(String(reader.result).split(',')[1]||'');reader.onerror=()=>reject(new PatternError('pattern_error'));reader.readAsDataURL(blob);}));
 // #endif
 // #ifndef H5
 return new Promise((resolve,reject)=>uni.getFileSystemManager().readFile({filePath:path,encoding:'base64',success:result=>resolve(String(result.data)),fail:()=>reject(new PatternError('pattern_error'))}));
 // #endif
}
export function compressPhoto(path:string):Promise<string>{
 if(typeof uni.compressImage!=='function')return Promise.resolve(path);
 return new Promise(resolve=>uni.compressImage({src:path,quality:80,compressedWidth:1280,success:result=>resolve(result.tempFilePath),fail:()=>resolve(path)} as UniApp.CompressImageOptions));
}

export function toResult(body:any,viaAccount=false,version=''):PatternResult{
 const pattern=body?.pattern||{},counts:Record<string,number>=pattern.color_counts||{};
 const hex=new Map<string,string>((pattern.palette_used||[]).map((item:any)=>[String(item.code),String(item.hex||'#ffffff')]));
 const colors=Object.entries(counts).map(([code,count])=>({code,hex:hex.get(code)||'#ffffff',count:Number(count)||0})).sort((a,b)=>b.count-a.count||a.code.localeCompare(b.code));
 const path=String(pattern.image_url||pattern.metadata?.labeled_image_url||'');
 // An edited pattern keeps its file name, so a version marker refreshes cached images.
 const url=(path.startsWith('/')?ORIGIN+path:path)+(version&&path?`?v=${version}`:'');
 return {artworkId:String(body?.artwork_id||pattern.metadata?.artwork_id||''),imageUrl:url,total:Number(pattern.bead_total)||colors.reduce((sum,item)=>sum+item.count,0),colors,sheet:pattern,viaAccount};
}

function failure(reply:Reply):PatternError{
 if(reply.statusCode===429)return new PatternError('pattern_error_busy',429);
 if(reply.statusCode===413||reply.data?.error==='IMAGE_TOO_LARGE')return new PatternError('pattern_error_large',reply.statusCode);
 return new PatternError('pattern_error',reply.statusCode);
}

export async function makePattern(photoBase64:string,size:number,extension:string):Promise<PatternResult>{
 const body={raw_image_base64:photoBase64,filename:'photo.'+(extension==='png'?'png':'jpg'),size:`${size}x${size}`,size_preset:`${size}x${size}`,brand:'MARD',auto_remove_white_bg:true};
 let useAccount=true,consented=false,renewedDevice=false;
 for(let attempt=0;attempt<3;attempt++){
  const header=await identity(useAccount);
  const reply=await call('/generate/script','POST',body,header);
  if(reply.statusCode>=200&&reply.statusCode<300)return toResult(reply.data,!!header.Authorization);
  // Tapping "make the pattern" under the photo note is the consent the website also records.
  if(reply.statusCode===403&&reply.data?.error==='CONSENT_REQUIRED'&&header.Authorization&&!consented){consented=true;await call('/user/consent','POST',{type:'sensitive'},header);continue;}
  if(reply.statusCode===401){
   // An expired account token should not block a free tool: continue as this device.
   if(header.Authorization){useAccount=false;continue;}
   // A rejected device identity is replaced once with a fresh one.
   uni.removeStorageSync(DEVICE_KEY);
   if(!renewedDevice){renewedDevice=true;continue;}
  }
  throw failure(reply);
 }
 throw new PatternError('pattern_error');
}

// The pattern page hands its latest result to the editor and back.
let current:PatternResult|null=null;
export const patternState={get:()=>current,set:(value:PatternResult|null)=>{current=value;}};

// Saves an edited sheet with the identity that generated it; the backend re-renders the labelled image.
export async function savePattern(result:PatternResult,sheet:unknown):Promise<PatternResult>{
 const header=result.viaAccount?{Authorization:'Bearer '+(uni.getStorageSync('pd_token')||'')}:await deviceHeader();
 const reply=await call(`/artwork/${encodeURIComponent(result.artworkId)}/pattern`,'PUT',{pattern_json:sheet,render_preview:true},header);
 if(reply.statusCode>=200&&reply.statusCode<300)return toResult({artwork_id:result.artworkId,pattern:reply.data?.pattern},result.viaAccount,String(Date.now()));
 throw failure(reply);
}

// Saving uses an ordinary HTTPS request so it relies on the existing request domain.
export function savePatternImage(result:PatternResult):Promise<void>{
 // #ifdef H5
 window.open(result.imageUrl,'_blank');return Promise.resolve();
 // #endif
 // #ifndef H5
 return new Promise((resolve,reject)=>uni.request({
  url:result.imageUrl,method:'GET',responseType:'arraybuffer',timeout:60000,
  success:response=>{
   if(response.statusCode!==200){reject(new PatternError('pattern_error_network'));return;}
   const filePath=`${(globalThis as any).wx?.env?.USER_DATA_PATH||''}/pattern-${result.artworkId||'image'}-${Date.now()}.png`;
   uni.getFileSystemManager().writeFile({filePath,data:response.data as ArrayBuffer,encoding:'binary',
    success:()=>uni.saveImageToPhotosAlbum({filePath,success:()=>resolve(),fail:error=>reject(error)}),
    fail:()=>reject(new PatternError('pattern_error'))});
  },
  fail:()=>reject(new PatternError('pattern_error_network')),
 }));
 // #endif
}
