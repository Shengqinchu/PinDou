// Short-lived local File snapshots survive sign-in redirects without images in URLs.
const DB='pindou-generator-draft-v1';
export type Draft={file:File;size:string;mode:string;style:string;owner:string;saved:number;jobId?:string;submitted?:boolean;completedId?:string};
let pending=Promise.resolve();
function database():Promise<IDBDatabase>{return new Promise((resolve,reject)=>{
 const request=indexedDB.open(DB,1);request.onupgradeneeded=()=>request.result.createObjectStore('draft');
 request.onsuccess=()=>resolve(request.result);request.onerror=()=>reject(request.error);
});}
async function write(value:Draft|null){const db=await database();try{await new Promise<void>((resolve,reject)=>{
 const transaction=db.transaction('draft','readwrite');const store=transaction.objectStore('draft');
 if(value)store.put(value,'current');else store.delete('current');
 transaction.oncomplete=()=>resolve();transaction.onerror=()=>reject(transaction.error);
});}finally{db.close();}}
export function persistGeneratorDraft(value:Draft|null){pending=pending.then(()=>write(value)).catch(()=>{});return pending;}
export function flushGeneratorDraft(){return pending;}
export async function restoreGeneratorDraft(owner:string):Promise<Draft|null>{
 try{const db=await database();const value=await new Promise<Draft|undefined>((resolve,reject)=>{
   const request=db.transaction('draft').objectStore('draft').get('current');request.onsuccess=()=>resolve(request.result);request.onerror=()=>reject(request.error);
 });db.close();
 if(!value||!(value.file instanceof File)||value.file.size>12*1024*1024||Date.now()-value.saved>3600000||(value.owner!==owner&&value.owner!=='guest')){await persistGeneratorDraft(null);return null;}
 return value;
 }catch{return null;}
}
