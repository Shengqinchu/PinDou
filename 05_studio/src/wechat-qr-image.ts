/** Authing WXAPP_AUTH reserves its centre for the configured logo.
 * Use the SDK's 1 / 2.4 diameter; keep the surrounding code pixels unchanged.
 * One composed image also preserves the logo when the QR is saved on mobile.
 */
function load(source:string):Promise<HTMLImageElement>{
 return new Promise((resolve,reject)=>{const img=new Image();const timeout=setTimeout(()=>reject(new Error('QR image timeout')),5000);img.crossOrigin='anonymous';img.referrerPolicy='no-referrer';img.onload=()=>{clearTimeout(timeout);resolve(img);};img.onerror=()=>{clearTimeout(timeout);reject(new Error('QR image unavailable'));};img.src=source;});
}
export async function wechatQrImage(source:string,logo?:string):Promise<string>{
 if(!logo)return source;
 try{
  const [code,brand]=await Promise.all([load(source),load(logo)]);
  const canvas=document.createElement('canvas');canvas.width=code.naturalWidth;canvas.height=code.naturalHeight;
  const ctx=canvas.getContext('2d');if(!ctx)return source;
  ctx.drawImage(code,0,0);const diameter=Math.min(canvas.width,canvas.height)/2.4;
  const x=(canvas.width-diameter)/2,y=(canvas.height-diameter)/2;
  ctx.save();ctx.beginPath();ctx.arc(canvas.width/2,canvas.height/2,diameter/2,0,Math.PI*2);ctx.clip();
  ctx.fillStyle='white';ctx.fillRect(x,y,diameter,diameter);ctx.drawImage(brand,x,y,diameter,diameter);ctx.restore();
  return canvas.toDataURL('image/png');
 }catch{return source;}
}
