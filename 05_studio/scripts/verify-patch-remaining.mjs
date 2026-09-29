// All writes target the loopback-only disposable fixture, never production.
import {chromium,webkit,request,expect} from '@playwright/test';
import assert from 'node:assert/strict';
import fs from 'node:fs/promises';
import {fileURLToPath} from 'node:url';
import {randomUUID} from 'node:crypto';
const api='http://127.0.0.1:8137/studio-api',base=process.env.QUOTA_UI_BASE||'http://127.0.0.1:5337';
const out=new URL('../../artifacts/patch-quota/'+(base.startsWith('https:')?'live-browser/':'browser/'),import.meta.url);
await fs.mkdir(out,{recursive:true});
const staff={Authorization:'Bearer local-admin-visits'},fixture=await request.newContext();
async function call(path,method='GET',data,headers=staff){
 const r=await fixture.fetch(api+path,{method,headers,data});assert(r.ok(),path+': '+r.status()+' '+await r.text());return r.json();
}
async function setRemaining(remaining){const p=await call('/manage/patch-promotion');return call('/manage/patch-promotion','PUT',{quota:10,remaining,enabled:true,version:p.version});}
const results=[];
for(const [engine,type,width,height,lang] of [
 ['webkit',webkit,390,844,'zh'],['chromium',chromium,1440,900,'zh'],
 ['webkit',webkit,375,667,'en'],['chromium',chromium,320,568,'en'],
]){
 await setRemaining(10);
 const key=[engine,width,height,lang].join('-'),browser=await type.launch({headless:true});
 const ctx=await browser.newContext({viewport:{width,height},hasTouch:width<=700,reducedMotion:'reduce'});
 await ctx.addInitScript(({lang})=>{
  localStorage.setItem('puppy-studio-language',lang);
  localStorage.setItem('pd_web_token','qa-email-quota-viewer');localStorage.setItem('pd_token','qa-email-quota-viewer');
  sessionStorage.setItem('puppy-studio-admin','local-admin-visits');
 },{lang});
 await ctx.route('**/studio-api/**',async route=>{
  const req=route.request(),url=new URL(req.url()),headers={};
  for(const k of ['authorization','content-type','idempotency-key'])if(req.headers()[k])headers[k]=req.headers()[k];
  try{
   const r=await fixture.fetch('http://127.0.0.1:8137'+url.pathname+url.search,{method:req.method(),headers,data:req.postDataBuffer()||undefined});
   await route.fulfill({response:r});
  }catch(e){
   // SPA navigation cancels background calendar reads before the fixture responds.
   if(req.method()==='GET'&&(req.failure()||e.message.includes('Route is already handled!')))return;
   throw e;
  }
 });
 await ctx.route('**/api/v1/**',r=>r.fulfill({json:{}}));
 // WebKit can reject Cloudflare's RUM beacon in a routed browser context.
 // Record that telemetry failure separately; do not suppress application errors.
 const page=await ctx.newPage(),errors=[],telemetryErrors=[];
 page.on('pageerror',e=>(e.message.includes('/cdn-cgi/rum?')?telemetryErrors:errors).push(e.message));page.setDefaultTimeout(20000);
 try{
  await page.goto(base+'/manage?view=reservations');
  const settings=page.locator('.patch-promotion-settings:visible');
  await expect(settings).toContainText('10/10');
  await settings.locator('button.desk-button').click();
  const form=page.locator('#patch-promotion-form:visible'),dialog=page.locator('.studio-drawer[open]').filter({has:form});
  await expect(dialog).toHaveAttribute('data-phase','open');await page.evaluate(()=>document.fonts.ready);
  const total=form.locator('input[type=number]').nth(0),remaining=form.locator('input[type=number]').nth(1),save=dialog.locator('button[form=patch-promotion-form]');
  await expect(total).toHaveValue('10');await expect(remaining).toHaveValue('10');
  await remaining.fill('6');await expect(total).toHaveValue('10');
  await page.screenshot({path:fileURLToPath(new URL(key+'-edit.png',out)),animations:'disabled'});
  const layout=await dialog.evaluate(e=>{
   const h=e.querySelector('.drawer-top h2'),b=e.querySelector('.drawer-bottom'),box=h.getBoundingClientRect();
   return {wrap:getComputedStyle(h).textWrap,font:getComputedStyle(h).fontFamily,heading:{x:box.x,width:box.width,height:box.height},glyphs:[...h.querySelectorAll('.lift-glyph')].map(x=>({text:x.textContent,y:x.getBoundingClientRect().y})),footerBottom:b.getBoundingClientRect().bottom,overflow:document.documentElement.scrollWidth-innerWidth};
  });
  assert.equal(layout.wrap,'wrap');assert(layout.overflow<=1&&layout.footerBottom<=height+1);
  if(lang==='zh')assert.equal(layout.glyphs[0].y,layout.glyphs[1].y,'Chinese title must not orphan its first character');
  await save.click();await expect(form).not.toBeVisible();await expect(settings).toContainText('6/10');
  let p=await call('/manage/patch-promotion');assert.equal(p.quota,10);assert.equal(p.remaining,6);
  await page.reload();await expect(settings).toContainText('6/10');
  await settings.locator('button.desk-button').click();
  for(const bad of ['', '-1', '1.5']){
   await remaining.fill(bad);await save.click();await expect(form).toBeVisible();assert.equal((await call('/patch-promotion')).remaining,6);
  }
  await remaining.fill('4');
  // A concurrent change must preserve the draft and offer a deliberate reload.
  await setRemaining(5);await save.click();await expect(form.locator('[role=alert]')).toBeVisible();await expect(remaining).toHaveValue('4');
  await form.locator('[role=alert] button').click();await expect(remaining).toHaveValue('5');
  await remaining.fill('6');await save.click();await expect(form).not.toBeVisible();
  if(engine==='chromium'&&width===1440){
   const cal=await call('/reservation-calendar?guests=2&plan=patch');
   const day=cal.days.find((d,i)=>i>0&&d.slots.some(s=>s.start==='10:00'&&s.available));assert(day);
   const body={booking:{date:day.date,start:'10:00',end:'11:00',plan:'patch',guests:2},name:'Local quota QA',contact_method:'wechat',contact:'qa-local',consent:true};
   const booking=await call('/reservations','POST',body,{Authorization:'Bearer qa-email-quota-booking','Idempotency-Key':randomUUID()});
   assert.equal((await call('/patch-promotion')).remaining,4);
   await call('/manage/reservations/'+booking.id,'PATCH',{version:booking.version,status:'cancelled'});
   assert.equal((await call('/patch-promotion')).remaining,6);
  }
  await page.goto(base+'/visit?plan=patch');await expect(page.locator('.visit-patch-promotion')).toContainText('6/10');
  assert.deepEqual(errors,[]);results.push({key,layout,saveReload:true,invalidBlocked:true,conflictPreservesDraft:true,publicRemaining:true,telemetryErrors});
  await fs.writeFile(new URL('results.json',out),JSON.stringify(results,null,2));console.log(JSON.stringify({case:key,passed:true}));
 }finally{await ctx.unrouteAll({behavior:'ignoreErrors'});await ctx.close();await browser.close();}
}
await fixture.dispose();await fs.writeFile(new URL('results.json',out),JSON.stringify(results,null,2));console.log(JSON.stringify({passed:results.length,results:fileURLToPath(new URL('results.json',out))}));
