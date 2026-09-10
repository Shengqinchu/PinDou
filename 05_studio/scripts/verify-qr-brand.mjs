import {chromium,expect} from '@playwright/test';import assert from 'node:assert/strict';import fs from 'node:fs/promises';import {fileURLToPath} from 'node:url';
const out=new URL('../../artifacts/auth-tabs/',import.meta.url),base='http://127.0.0.1:19682';
const provider=JSON.parse(await fs.readFile(new URL('provider-brand.json',out),'utf8')).find(x=>!x.merged);
const browser=await chromium.launch({headless:true});
try{
 const page=await browser.newPage({viewport:{width:390,height:844},locale:'zh-CN'});let mode='brand';
 await page.route('**/studio-api/auth/options',r=>r.fulfill({json:{wechat:true,password:true,email:false,recovery:true}}));
 await page.route('**/studio-api/auth/wechat/qr/start',r=>r.fulfill({json:{state:'a'.repeat(43),image:provider.image,logo:mode==='brand'?provider.logo:base+'/missing-logo.png',expires_in:120}}));
 await page.route('**/studio-api/auth/wechat/qr/poll',r=>r.fulfill({json:{status:'qr_pending'}}));
 await page.route('**/missing-logo.png',r=>r.fulfill({status:404,body:''}));
 await page.goto(base+'/account');await page.getByRole('tab',{name:'微信登录',exact:true}).click();const image=page.locator('.wechat-qr-window img');await expect(image).toHaveAttribute('src',/^data:image\/png/);
 const pixels=await page.evaluate(async raw=>{
  const original=await new Promise((resolve,reject)=>{const img=new Image();img.crossOrigin='anonymous';img.onload=()=>resolve(img);img.onerror=reject;img.src=raw;});const composed=document.querySelector('.wechat-qr-window img');await composed.decode();
  const w=original.naturalWidth,h=original.naturalHeight;function data(img){const c=document.createElement('canvas');c.width=w;c.height=h;const ctx=c.getContext('2d');ctx.drawImage(img,0,0);return ctx.getImageData(0,0,w,h).data;}const a=data(original),b=data(composed),radius=Math.min(w,h)/4.8;let outerChanged=0,insideBlack=0,insideBlue=0;
  for(let y=0;y<h;y++)for(let x=0;x<w;x++){const i=(y*w+x)*4,d=Math.hypot(x-w/2,y-h/2);if(d>radius+2&&a.slice(i,i+4).some((n,j)=>n!==b[i+j]))outerChanged++;if(d<radius-3){if(b[i]<70&&b[i+1]<70&&b[i+2]<70)insideBlack++;if(b[i+2]>b[i]+35&&b[i+2]>b[i+1]+15)insideBlue++;}}
  return {width:w,height:h,outerChanged,insideBlack,insideBlue};
 },provider.image);
 assert.equal(pixels.outerChanged,0);assert(pixels.insideBlack>100);assert.equal(pixels.insideBlue,0);await page.screenshot({path:fileURLToPath(new URL('branded-qr-mobile.png',out))});
 await page.getByRole('tab',{name:'登录',exact:true}).click();mode='missing';await page.getByRole('tab',{name:'微信登录',exact:true}).click();await expect(image).toHaveAttribute('src',provider.image);
 await fs.writeFile(new URL('qr-brand.json',out),JSON.stringify({passed:true,pixels,missingLogoFallsBack:true,phoneScanNotTested:true},null,2));console.log(JSON.stringify({passed:true,pixels,missingLogoFallsBack:true}));
}finally{await browser.close();}
