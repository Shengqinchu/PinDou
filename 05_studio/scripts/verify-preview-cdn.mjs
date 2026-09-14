import {chromium} from '@playwright/test';
import assert from 'node:assert/strict';
import fs from 'node:fs/promises';
import crypto from 'node:crypto';
const out=new URL('../../artifacts/image-delivery-20260914/',import.meta.url),rows=[];
const source='a1ab5db6b30ac5b033ec07daf3dfe3a1502d266917938a508c606e7aed8a820f.webp';
const browser=await chromium.launch();
try{
 for(let pass=1;pass<=2;pass++){
  const context=await browser.newContext(),page=await context.newPage();
  const response=await page.goto('https://pindoupuppy.com/studio-api/media/previews/v1/480/'+source);
  assert.equal(response.status(),200);const headers=await response.allHeaders();
  assert.equal(headers['content-type'],'image/webp');assert.ok(headers['cache-control'].includes('immutable'));
  const dimensions=await page.locator('img').evaluate(async image=>{await image.decode();return [image.naturalWidth,image.naturalHeight]});
  assert.deepEqual(dimensions,[480,480]);
  const body=await response.body();rows.push({pass,status:response.status(),bytes:body.length,sha256:crypto.createHash('sha256').update(body).digest('hex'),dimensions,type:headers['content-type'],cache:headers['cache-control'],cdnCache:headers['cf-cache-status']});
  await context.close();
 }
 assert.equal(rows[0].sha256,rows[1].sha256);
 assert.ok(rows.some(row=>row.cdnCache==='HIT'));
}finally{await browser.close();}
await fs.writeFile(new URL('cdn-verification.json',out),JSON.stringify(rows,null,2));console.log(JSON.stringify(rows));
