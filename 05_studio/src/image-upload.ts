const CHUNK_BYTES=256*1024;
const PARALLEL_CHUNKS=4;

// Only the shop's explicit speed option calls this. Keep dimensions and use
// the original file unless a high-quality encode saves enough transfer time.
export async function optimizeProductImage(file:File):Promise<File>{
  if(file.size<=512*1024||!['image/jpeg','image/png'].includes(file.type)||typeof createImageBitmap!=='function')return file;
  let bitmap:ImageBitmap|undefined;
  try{
    bitmap=await createImageBitmap(file);
    if(bitmap.width*bitmap.height>24_000_000)return file;
    const canvas=document.createElement('canvas');
    canvas.width=bitmap.width;canvas.height=bitmap.height;
    const context=canvas.getContext('2d');
    if(!context)return file;
    context.drawImage(bitmap,0,0);
    const encoded=await new Promise<Blob|null>(resolve=>canvas.toBlob(resolve,'image/webp',0.95));
    if(!encoded||encoded.type!=='image/webp'||encoded.size>=file.size*0.7)return file;
    return new File([encoded],file.name.replace(/\.[^.]+$/,'')+'.webp',{type:'image/webp',lastModified:file.lastModified});
  }catch{return file}
  finally{bitmap?.close()}
}

export async function sendImageChunks<T>(file:File,uploadId:string,original:boolean,send:<R>(path:string,init:RequestInit,attempts?:number)=>Promise<R>):Promise<T>{
  const chunks=Math.ceil(file.size/CHUNK_BYTES);
  let next=0,failed:unknown;
  async function worker(){
    while(next<chunks&&failed===undefined){
      const index=next++;
      try{
        await send(`/manage/media/chunks/${uploadId}/${index}`,{method:'PUT',headers:{'Content-Type':'application/octet-stream'},body:file.slice(index*CHUNK_BYTES,(index+1)*CHUNK_BYTES)},3);
      }catch(error){failed ??=error;}
    }
  }
  await Promise.all(Array.from({length:Math.min(PARALLEL_CHUNKS,chunks)},()=>worker()));
  if(failed!==undefined)throw failed;
  return send<T>(`/manage/media/chunks/${uploadId}/complete?size=${file.size}&chunks=${chunks}&original=${original}`,{method:'POST'},3);
}
