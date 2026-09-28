// All writes are confined to the disposable loopback fixture.
import {chromium,webkit,request,expect} from '@playwright/test';
import assert from 'node:assert/strict';
import fs from 'node:fs/promises';
import {fileURLToPath} from 'node:url';
const api='http://127.0.0.1:8127/studio-api',base='http://127.0.0.1:5287';
const out=new URL('../../artifacts/patch-launch/browser/',import.meta.url);
await fs.mkdir(out,{recursive:true});
const staff={Authorization:'Bearer local-admin-visits'},fixture=await request.newContext();
async function call(path,method='GET',data,headers=staff){
 const r=await fixture.fetch(api+path,{method,headers,data});assert(r.ok(),path+': '+r.status()+' '+await r.text());return r.json();
}
async function setOffer(quota,enabled=true){const p=await call('/manage/patch-promotion');return call('/manage/patch-promotion','PUT',{quota,enabled,version:p.version});}
await setOffer(10);
const results=[];
for(const [engine,type,width,height,lang,motion] of [
 ['chromium',chromium,1440,900,'zh','full'],['chromium',chromium,1366,768,'en','full'],
 ['chromium',chromium,1280,720,'zh','full'],['webkit',webkit,390,844,'zh','full'],
 ['webkit',webkit,375,667,'en','full'],['chromium',chromium,320,568,'en','reduced'],
 ['chromium',chromium,800,600,'zh','full'],['webkit',webkit,1440,900,'en','reduced'],
]){
 const key=[engine,width,height,lang,motion].join('-'),browser=await type.launch({headless:true,ignoreDefaultArgs:['--hide-scrollbars']});
 const ctx=await browser.newContext({viewport:{width,height},hasTouch:width<=700,reducedMotion:null});
 await ctx.addInitScript(({lang})=>{
  localStorage.setItem('puppy-studio-language',lang);
  localStorage.setItem('pd_web_token','qa-email-launch-viewer');localStorage.setItem('pd_token','qa-email-launch-viewer');
  sessionStorage.setItem('puppy-studio-admin','local-admin-visits');
 },{lang});
 await ctx.route('**/studio-api/**',async route=>{
  const req=route.request(),url=new URL(req.url()),headers={};
  for(const k of ['authorization','content-type','idempotency-key'])if(req.headers()[k])headers[k]=req.headers()[k];
  const r=await ctx.request.fetch('http://127.0.0.1:8127'+url.pathname+url.search,{method:req.method(),headers,data:req.postDataBuffer()||undefined});
  await route.fulfill({response:r});
 });
 await ctx.route('**/api/v1/**',r=>r.fulfill({json:{}}));
 const page=await ctx.newPage(),errors=[];page.on('pageerror',e=>errors.push(e.message));page.setDefaultTimeout(12000);
 const shot=async name=>page.screenshot({path:fileURLToPath(new URL(key+'-'+name+'.png',out)),fullPage:true,animations:'disabled'});
 try{
  await page.goto(base+'/?motion='+motion);
  const dialog=page.locator('.patch-launch-dialog'),panel=page.locator('.patch-launch-panel');
  await expect(dialog).toHaveAttribute('data-phase','open');
  await expect(panel).toContainText(lang==='zh'?'帆布带':'canvas strap');
  await expect(panel).toContainText('10/10');
  const geometry=await panel.boundingBox();
  assert(geometry.x>=0&&geometry.y>=0&&geometry.x+geometry.width<=width+1&&geometry.y+geometry.height<=height+1);
  assert(await page.evaluate(()=>document.activeElement.closest('.patch-launch-dialog')!==null));
  await page.keyboard.press('Tab');
  assert(await page.evaluate(()=>document.activeElement.closest('.patch-launch-dialog')!==null));
  await page.evaluate(()=>document.fonts.ready);await shot('popup');
  const cta=panel.locator('.button');
  if(width===1440&&lang==='zh'){
   await cta.hover();await page.waitForTimeout(330);
   const hover=await cta.evaluate(e=>({transform:getComputedStyle(e).transform,duration:getComputedStyle(e).transitionDuration}));
   await page.mouse.down();await page.waitForTimeout(160);
   const held=await cta.evaluate(e=>getComputedStyle(e).transform);
   assert.notEqual(hover.transform,held);assert(hover.duration.includes('0.3'));
   await page.mouse.move(2,2);await page.mouse.up();await page.waitForTimeout(330);
  }
  await cta.click();
  await expect(page).toHaveURL(/\/visit\?/);
  await expect(page.locator('input[value=patch]')).toBeChecked();
  await expect(page.locator('.visit-flow-page')).toHaveAttribute('data-step','1');
  await expect(page.locator('.visit-patch-promotion')).toContainText('10/10');
  await page.waitForTimeout(650);
  const layout=await page.evaluate(()=>({overflow:document.documentElement.scrollWidth-innerWidth,
   scroll:getComputedStyle(document.querySelector('.visit-scroll')).overflowY,
   bottom:document.querySelector('.visit-actions').getBoundingClientRect().bottom}));
  assert(layout.overflow<=1&&layout.scroll==='visible',JSON.stringify(layout));
  if(width>=1280)assert(layout.bottom<=height+3,JSON.stringify(layout));
  await shot('card');
  // Changing experience manually must survive refresh after the campaign link.
  await page.locator('input[value=hourly]').check();await page.reload();
  await expect(page.locator('input[value=hourly]')).toBeChecked();
  await page.goto(base+'/');
  await page.waitForTimeout(600);await expect(page.locator('.patch-launch-dialog')).not.toBeVisible();
  // A fresh browser session can dismiss with Escape, with scrolling restored.
  await page.evaluate(()=>sessionStorage.removeItem('puppy-patch-promo:patch-launch-20260928'));
  await page.reload();await expect(dialog).toHaveAttribute('data-phase','open');
  await page.keyboard.press('Escape');await expect(dialog).not.toBeVisible();
  assert.notEqual(await page.evaluate(()=>getComputedStyle(document.body).position),'fixed');
  if(width<=390&&lang==='zh'){
   await page.goto(base+'/manage?view=reservations');
   await page.locator('.patch-promotion-settings:visible button.desk-button').click();
   await expect(page.locator('#patch-promotion-form:visible')).toBeVisible();
   await shot('admin-mobile');
   await page.keyboard.press('Escape');
  }
  if(width===1440&&lang==='zh'){
   await page.goto(base+'/manage?view=reservations');
   const settings=page.locator('.patch-promotion-settings:visible');
   await expect(settings).toContainText('10/10');
   await settings.locator('button.desk-button').click();
   const form=page.locator('#patch-promotion-form:visible');
   await form.locator('input').fill('1');await page.locator('button[form=patch-promotion-form]:visible').click();
   await expect(form).not.toBeVisible();await expect(settings).toContainText('1/1');
   // Create a real local booking with two guests; a quota of one grants both.
   await call('/reservation-calendar');
   const cal=await call('/reservation-calendar?experience=patch');
   const day=cal.days.find((d,i)=>i>0&&d.slots.some(s=>s.start==='12:00'&&s.start_available));
   const row=await call('/reservations','POST',{booking:{date:day.date,start:'12:00',end:'13:00',guests:2,plan:'patch'},name:'Local launch QA',contact_method:'wechat',contact:'local-only',consent:true},{Authorization:'Bearer qa-email-launch-gift','Idempotency-Key':crypto.randomUUID()});
   await page.reload();await expect(settings).toContainText('0/1');await expect(settings).toContainText('2');
   const booking=page.locator('.reservation-desk-row').filter({hasText:row.id});
   await expect(booking.locator('.patch-gift-badge')).toContainText('2');
   await shot('admin-gift');
   await booking.click();await expect(page.locator('.studio-drawer[open] .patch-gift-badge')).toContainText('2');
   await page.keyboard.press('Escape');
   await page.goto(base+'/visit?experience=patch&step=1');await expect(page.locator('.visit-patch-promotion')).toContainText('已领完');
   await shot('exhausted');
   // Cancellation frees all allocated people but never manufactures extra quota.
   await call('/manage/reservations/'+row.id,'PATCH',{version:1,status:'cancelled'});
   assert.equal((await call('/patch-promotion')).remaining,1);
   await setOffer(10,false);
   await page.reload();await expect(page.locator('.visit-patch-promotion')).toHaveCount(0);
   await page.evaluate(()=>sessionStorage.removeItem('puppy-patch-promo:patch-launch-20260928'));
   await page.goto(base+'/');await page.waitForTimeout(600);await expect(dialog).not.toBeVisible();
   await setOffer(10,true);
  }
  assert.deepEqual(errors,[]);
  results.push({key,geometry,layout,errors});console.log('PASS '+key);
 }catch(error){await shot('FAILED');throw error;}
 finally{await browser.close();}
}
await fixture.dispose();await fs.writeFile(new URL('results.json',out),JSON.stringify(results,null,2));
console.log('Verified '+results.length+' launch views and local lifecycle.');
