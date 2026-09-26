import { chromium, webkit, expect } from '@playwright/test';
import fs from 'node:fs/promises';
import path from 'node:path';
import assert from 'node:assert/strict';
import { fileURLToPath } from 'node:url';

const base=process.env.PINDOU_QA_ORIGIN||'http://127.0.0.1:4184';
const live=new URL(base).hostname==='pindoupuppy.com';
assert(live||new URL(base).hostname==='127.0.0.1');
const out=fileURLToPath(new URL('../../artifacts/booking-mobile-20260912/',import.meta.url));
await fs.mkdir(out,{recursive:true});
const results=[];
const expectedBuild=JSON.parse(await fs.readFile(new URL('../dist/version.json',import.meta.url),'utf8')).build;
async function settle(page){
 await expect(page.locator('.visit-step-enter-active,.visit-step-leave-active')).toHaveCount(0);
 await page.evaluate(()=>document.fonts.ready);
}
async function openTime(page){
 await page.goto(base+'/visit?step=1');
 await page.locator('.visit-plans input[value=hourly]').check();
 await expect(page.locator('.visit-actions .button-primary')).toBeEnabled();
 await page.locator('.visit-actions .button-primary').click();
 await expect(page.locator('.reservation-grid')).toBeVisible();await settle(page);
}
const time=value=>{const [h,m]=value.split(':').map(Number);return h*60+m;};
const clock=value=>String(Math.floor(value/60)).padStart(2,'0')+':'+String(value%60).padStart(2,'0');

for(const [name,type] of [['chromium',chromium],['webkit',webkit]]){
 const browser=await type.launch({headless:true,ignoreDefaultArgs:['--hide-scrollbars']});
 const result={name,live,passed:false,states:[],errors:[],telemetryErrors:[]};results.push(result);
 const recordError=error=>{
  // WebKit can reject Cloudflare's RUM beacon in the automated browser.
  // Retain this exact third-party diagnostic separately; application errors fail.
  const bucket=live&&error.message==='/pindoupuppy.com/cdn-cgi/rum? due to access control checks.'?result.telemetryErrors:result.errors;
  bucket.push(error.message);
 };
 let page;
 try{
  for(const [width,height,language,minimum] of [[390,700,'zh',500],[390,844,'en',736],[320,568,'zh',500],[430,932,'zh',912],[1440,900,'zh',250],[844,390,'en',100]]){
   const context=await browser.newContext({viewport:{width,height},locale:language==='zh'?'zh-CN':'en-CA',hasTouch:width<=700,reducedMotion:'reduce'});
   await context.addInitScript(lang=>localStorage.setItem('puppy-studio-language',lang),language);
   page=await context.newPage();page.setDefaultTimeout(15000);page.on('pageerror',recordError);
   if(live)await page.route('**/studio-api/reservations',route=>{throw new Error('Live booking submission is forbidden in this check');});
   await openTime(page);
   const first=page.locator('.reservation-grid button:not(:disabled)').first();
   const day=await first.getAttribute('data-date'),start=await first.getAttribute('data-time');
   await first.click();
   await expect(page.locator('.visit-time-selection')).toContainText(start+'–'+clock(time(start)+120));
   await expect(page.locator('.reservation-legend i.chosen')).toHaveCSS('background-color','rgb(232, 227, 244)');
   await expect(page.locator('.reservation-grid button.chosen:not(.start)').first()).toHaveCSS('background-color','rgb(232, 227, 244)');
   await expect(page.locator('.reservation-minimum-note')).toHaveText(language==='zh'?'预约时长至少 2 小时':'Minimum booking: 2 hours.');
   const metrics=await page.evaluate(()=>{
    const grid=document.querySelector('.reservation-grid-scroll'),footer=document.querySelector('.visit-actions');
    return {width:innerWidth,height:innerHeight,pageWidth:document.documentElement.scrollWidth,pageHeight:document.documentElement.scrollHeight,
     grid:grid.getBoundingClientRect().height,gridWidth:grid.clientWidth,gridScrollWidth:grid.scrollWidth,footerBottom:footer.getBoundingClientRect().bottom,
     build:document.querySelector('meta[name=studio-build]')?.content};
   });
   assert(metrics.grid>=minimum,JSON.stringify(metrics));
   assert.equal(metrics.build,expectedBuild);
   assert(metrics.pageWidth<=width+1&&metrics.gridScrollWidth<=metrics.gridWidth+1,JSON.stringify(metrics));
   assert(metrics.footerBottom<=height+1,JSON.stringify(metrics));
   if(width>700)assert(metrics.pageHeight<=height+1);
   if(width===390&&height===700){
    await page.screenshot({path:path.join(out,`${live?'live-':''}${name}-mobile-page.png`),fullPage:true});
    await page.evaluate(()=>{const grid=document.querySelector('.reservation-grid-scroll');window.scrollTo(0,window.scrollY+grid.getBoundingClientRect().top-20);});
    await page.screenshot({path:path.join(out,`${live?'live-':''}${name}-mobile-table.png`)});
   }
   // Extend the same day after scrolling and retain that range across steps.
   const later=page.locator(`.reservation-grid button[data-date="${day}"][data-time="${clock(time(start)+120)}"]`);
   await later.click();
   const selection=await page.locator('.visit-time-selection').innerText();
   assert(selection.includes(start+'–'+clock(time(start)+150)));
   await page.locator('.reservation-minimum-note').scrollIntoViewIfNeeded();
   await expect(page.locator('.reservation-minimum-note')).toBeInViewport();
   await page.locator('.visit-actions .button-primary').click();
   await expect(page.locator('.visit-contact-value input')).toBeVisible();await settle(page);
   const input=page.locator('.visit-contact-value input');
   await page.locator('.contact-method-picker input[value=wechat]').check();
   await expect(input).toHaveAttribute('minlength','1');await input.fill('猫');
   assert(await input.evaluate(el=>el.checkValidity()));
   await page.locator('.contact-method-picker input[value=email]').check();
   await expect(input).toHaveAttribute('type','email');await expect(input).toHaveAttribute('minlength','3');
   assert(!await input.evaluate(el=>el.checkValidity()));
   await page.locator('.contact-method-picker input[value=wechat]').check();
   await page.locator('.visit-back').click();await settle(page);
   await expect(page.locator('.visit-time-selection')).toHaveText(selection);
   await page.locator('.visit-actions .button-primary').click();await settle(page);
   await expect(input).toHaveValue('猫');
   await page.reload();await expect(input).toHaveValue('猫');
   result.states.push({language,...metrics});await context.close();
  }
  if(!live){
   const context=await browser.newContext({viewport:{width:390,height:700},locale:'zh-CN',reducedMotion:'reduce'});
   await context.addInitScript(()=>localStorage.setItem('puppy-studio-language','zh'));
   page=await context.newPage();page.on('pageerror',recordError);
   // Each browser uses a fresh fake customer on the isolated QA service.
   const email=`mobile-${name}-${Date.now()}@example.test`;
   const login=await page.request.post(base+'/studio-api/auth/password-login',{data:{email,password:'local-password'}});
   assert(login.ok(),await login.text());const auth=await login.json();
   await context.addInitScript(token=>localStorage.setItem('pd_web_token',token),auth.token);
   await openTime(page);await page.locator('.reservation-grid button:not(:disabled)').first().click();
   await page.locator('.visit-actions .button-primary').click();await settle(page);
   await page.locator('.visit-contact input[autocomplete=name]').fill('Local mobile guest');
   await page.locator('.contact-method-picker input[value=wechat]').check();
   await page.locator('.visit-contact-value input').fill('猫');
   const request=page.waitForRequest(r=>r.method()==='POST'&&r.url().endsWith('/studio-api/reservations'));
   const response=page.waitForResponse(r=>r.request().method()==='POST'&&r.url().endsWith('/studio-api/reservations'));
   await page.locator('.visit-actions .button-primary').click();
   const sent=await request,received=await response;
   assert.equal(sent.postDataJSON().contact,'猫');assert.equal(received.status(),201,await received.text());
   await expect(page).toHaveURL(/\/reservation\/VIS-/);
   const profile=await page.request.get(base+'/studio-api/auth/booking-profile',{headers:{Authorization:'Bearer '+auth.token}});
   assert(profile.ok());const saved=await profile.json();assert(saved.complete&&saved.contact==='猫');
   const replay=await page.request.post(base+'/studio-api/reservations',{headers:{Authorization:'Bearer '+auth.token,'Idempotency-Key':sent.headers()['idempotency-key']},data:sent.postDataJSON()});
   assert.equal(replay.status(),201,await replay.text());assert.equal((await replay.json()).id,(await received.json()).id);
   result.submittedAndRetried=true;await context.close();
  }
  assert.deepEqual(result.errors,[]);result.passed=true;
 }catch(error){
  result.failure=String(error);if(page&&!page.isClosed())await page.screenshot({path:path.join(out,`${name}-failure.png`),fullPage:true});throw error;
 }finally{
  await browser.close();await fs.writeFile(path.join(out,live?'live-verification.json':'browser-verification.json'),JSON.stringify(results,null,2));
 }
}
console.log(JSON.stringify(results));
