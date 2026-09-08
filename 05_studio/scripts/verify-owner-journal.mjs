import {chromium,expect} from '@playwright/test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import crypto from 'node:crypto';
const data=JSON.parse(fs.readFileSync('src/content/journal-posts.json','utf8'));
const out='../artifacts/studio-vision2/owner-journal-qa';fs.mkdirSync(out,{recursive:true});
const posts=data.posts.filter(p=>p.body_sha256),results=[],errors=[];
assert.equal(posts.length,8);assert.equal(posts.reduce((sum,p)=>sum+p.images.length,0),80);
for(const p of posts){
 assert.equal(crypto.createHash('sha256').update(p.body).digest('hex'),p.body_sha256);
 for(const img of p.images)assert.equal(crypto.createHash('sha256').update(fs.readFileSync('public/'+img.src)).digest('hex'),img.sha256);
}
const b=await chromium.launch({headless:true});
for(const width of [390,1440]){
 const c=await b.newContext({viewport:{width,height:900},reducedMotion:'reduce'}),p=await c.newPage();
 p.on('pageerror',e=>errors.push(e.message));
 for(const post of posts){
  await p.goto('http://127.0.0.1:5184/studio/journal/'+post.id);await p.evaluate(()=>document.fonts.ready);
  await expect(p.locator('.journal-entry-photos img')).toHaveCount(post.images.length);
  const body=post.body.replace(/\[话题\]#/g,'').replace(/\[([^\]]+)R\]/g,'（$1）');
  assert.equal(await p.locator('.journal-original').textContent(),body);
  assert(await p.evaluate(()=>document.documentElement.scrollWidth<=innerWidth+1));
  const picture=p.locator('.journal-image-button').first();await picture.click();
  await expect(p.locator('.photo-dialog[open]')).toHaveCount(1);
  assert(await p.locator('.photo-dialog[open] .photo-current img').evaluate(e=>e.complete&&e.naturalWidth>0));
  await p.keyboard.press('Escape');await expect(p.locator('.photo-dialog[open]')).toHaveCount(0);
  if(post===posts[0]){await p.evaluate(()=>window.scrollTo(0,0));await p.screenshot({path:`${out}/article-${width}.png`});}
  results.push({id:post.id,width,bodyUnchanged:true,images:post.images.length,viewer:true});
 }
 await c.close();
}
await b.close();fs.writeFileSync(out+'/results.json',JSON.stringify({results,errors},null,2));console.log(JSON.stringify({articles:posts.length,images:80,checks:results.length,errors}));assert.deepEqual(errors,[]);
