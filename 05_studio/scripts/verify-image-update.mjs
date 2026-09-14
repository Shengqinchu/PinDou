// Disposable loopback catalogue only. No production credentials or writes.
import {chromium,expect} from '@playwright/test';
import assert from 'node:assert/strict';
import fs from 'node:fs/promises';
const base='http://127.0.0.1:4184',out=new URL('../../artifacts/image-delivery-20260914/',import.meta.url);
const browser=await chromium.launch();
try{
 const context=await browser.newContext({viewport:{width:1440,height:900}});
 await context.addInitScript(()=>{localStorage.setItem('puppy-studio-locale','zh');localStorage.setItem('puppy-studio-motion','reduced')});
 const page=await context.newPage();await page.goto(base+'/shop');
 await page.locator('.shop-children button').first().waitFor();
 await page.locator('.shop-children button').filter({hasText:'B系列'}).click();
 const image=page.locator('.shop-card').filter({has:page.locator('.shop-name',{hasText:/^B1$/})}).locator('img');
 await expect.poll(()=>image.evaluate(i=>i.complete&&i.naturalWidth>0)).toBe(true);
 const previous=await image.getAttribute('src');
 const catalog=await (await context.request.get(base+'/studio-api/manage/commerce')).json();
 const original=catalog.products.find(p=>p.code==='B1');assert.ok(original);
 const bytes=await page.evaluate(()=>{const c=document.createElement('canvas');c.width=720;c.height=960;const p=c.getContext('2d');p.fillStyle='#4a89c2';p.fillRect(0,0,720,960);p.fillStyle='#fff';p.fillRect(80,80,560,200);return c.toDataURL('image/png').split(',')[1]});
 const upload=await context.request.post(base+'/studio-api/manage/media?original=true',{data:Buffer.from(bytes,'base64'),headers:{'Content-Type':'image/png'}});assert.equal(upload.status(),200);
 const photo=await upload.json();
 let updated;
 try{
  const response=await context.request.put(base+'/studio-api/manage/products/'+original.id,{data:{...original,images:[photo.src]}});assert.equal(response.status(),200);updated=await response.json();
  await page.evaluate(()=>dispatchEvent(new Event('focus')));
  await expect.poll(()=>image.getAttribute('src')).toContain(photo.sha256);
  await expect.poll(()=>image.evaluate(i=>i.complete&&i.naturalWidth>0)).toBe(true);
  const current=await image.getAttribute('src');assert.notEqual(previous,current);
  const oldResponse=await context.request.get(base+previous);assert.equal(oldResponse.status(),200);
  await fs.writeFile(new URL('owner-image-update.json',out),JSON.stringify({passed:true,oldCacheStillReadable:true,newImageRendered:true,sourcePreserved:Buffer.compare(await (await context.request.get(base+photo.src)).body(),Buffer.from(bytes,'base64'))===0},null,2));
 }finally{
  if(updated){const restored=await context.request.put(base+'/studio-api/manage/products/'+original.id,{data:{...original,version:updated.version}});assert.equal(restored.status(),200);}
 }
 console.log('Owner upload, published replacement and cache invalidation passed');
}finally{await browser.close();}
