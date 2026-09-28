// Disposable loopback fixture only. Never point this mutation test at production.
import {chromium,webkit,expect,request} from '@playwright/test';
import assert from 'node:assert/strict';
import fs from 'node:fs/promises';
import {fileURLToPath} from 'node:url';
const base='http://127.0.0.1:5287',api='http://127.0.0.1:8127/studio-api';
const out=new URL('../../artifacts/booking-layout/browser/',import.meta.url);
await fs.mkdir(out,{recursive:true});
const staff={Authorization:'Bearer local-admin-visits'};
const fixture=await request.newContext();
async function call(path,method='GET',data,headers=staff){
 const response=await fixture.fetch(api+path,{method,headers,data});
 assert(response.ok(),path+': '+response.status()+' '+(!response.ok()?await response.text():''));return response.json();
}
await call('/reservation-calendar');
const before=await call('/manage/reservation-policy');
await call('/manage/reservation-policy','PUT',{version:before.version,max_guests_per_group:6,max_concurrent_groups:3,max_concurrent_guests:6,date_overrides:[{date:'2026-09-30',enabled:true,open:'10:00',close:'22:00'}]});
for(const [i,end] of ['12:00','22:00'].entries()){
 const row=await call('/reservations','POST',{booking:{date:'2026-09-29',start:'10:00',end,plan:'hourly',guests:1},name:'Local layout '+i,contact_method:'wechat',contact:'local-only',consent:true},{Authorization:'Bearer qa-email-layout-'+i,'Idempotency-Key':'41b0b000-0000-4000-8000-00000000000'+i});
 if(row.status!=='confirmed')await call('/manage/reservations/'+row.id,'PATCH',{version:row.version,status:'confirmed'});
}
const results=[];
for(const [engine,type,width,height,lang] of [
 ['chromium',chromium,1440,900,'zh'],['chromium',chromium,1366,768,'en'],
 ['chromium',chromium,1280,720,'zh'],['webkit',webkit,1440,900,'en'],
 ['chromium',chromium,390,844,'zh'],['webkit',webkit,390,844,'en'],
 ['chromium',chromium,320,568,'en'],['webkit',webkit,375,667,'zh'],
 ['chromium',chromium,800,600,'en'],
]){
 const key=[engine,width,height,lang].join('-'),browser=await type.launch({headless:true});
 const ctx=await browser.newContext({viewport:{width,height},hasTouch:width<=700,reducedMotion:null});
 await ctx.addInitScript(lang=>{
  localStorage.setItem('puppy-studio-language',lang);
  localStorage.setItem('pd_web_token','qa-email-layout-viewer');localStorage.setItem('pd_token','qa-email-layout-viewer');
  sessionStorage.setItem('puppy-studio-admin','local-admin-visits');
 },lang);
 await ctx.route('**/studio-api/**',async route=>{
  const req=route.request(),url=new URL(req.url()),headers={};
  for(const k of ['authorization','content-type','idempotency-key'])if(req.headers()[k])headers[k]=req.headers()[k];
  const r=await ctx.request.fetch('http://127.0.0.1:8127'+url.pathname+url.search,{method:req.method(),headers,data:req.postDataBuffer()||undefined});
  await route.fulfill({response:r});
 });
 await ctx.route('**/api/v1/**',route=>route.fulfill({json:{}}));
 const page=await ctx.newPage(),errors=[];page.on('pageerror',e=>errors.push(e.message));page.setDefaultTimeout(12000);
 const shot=async name=>page.screenshot({path:fileURLToPath(new URL(key+'-'+name+'.png',out)),fullPage:true,animations:'disabled'});
 try{
  await page.goto(base+'/visit?step=1');
  await expect(page.locator('.visit-plans>label')).toHaveCount(3);
  await page.evaluate(()=>document.fonts.ready);await page.waitForTimeout(700);
  const layout=await page.evaluate(()=>{
   const rect=s=>{const e=document.querySelector(s),r=e.getBoundingClientRect();return {x:r.x,y:r.y,width:r.width,height:r.height,bottom:r.bottom};};
   const scroll=document.querySelector('.visit-scroll');
   return {cards:rect('.visit-plans'),action:rect('.visit-actions'),overflow:getComputedStyle(scroll).overflowY,innerScroll:scroll.scrollHeight-scroll.clientHeight,pageOverflow:document.documentElement.scrollWidth-innerWidth,font:getComputedStyle(document.querySelector('.visit-plans>label>span')).fontFamily};
  });
  assert.equal(layout.overflow,'visible');assert(layout.pageOverflow<=1);
  if(width>=1280)assert(layout.cards.bottom<=height&&layout.action.bottom<=height+2,JSON.stringify(layout));
  await shot('choices');
  // Existing InfoTip behavior: keyboard, Escape, touch/click, outside dismissal.
  const tips=page.locator('.visit-combined-offers .info-tip-trigger');await expect(tips).toHaveCount(2);
  for(let i=0;i<2;i++){
   await page.keyboard.press('Tab');await tips.nth(i).focus();await expect(page.getByRole('tooltip')).toBeVisible();
   assert(await tips.nth(i).evaluate(e=>e.matches(':focus-visible')));
   await page.keyboard.press('Escape');await expect(page.getByRole('tooltip')).toHaveCount(0);
   await tips.nth(i).click();await expect(page.getByRole('tooltip')).toBeVisible();
   const box=await page.getByRole('tooltip').boundingBox();
   assert(box.x>=0&&box.x+box.width<=width+1&&box.y>=0&&box.y+box.height<=height+1);
   await shot('details-'+i);
   await page.locator('.visit-flow-heading').click();await expect(page.getByRole('tooltip')).toHaveCount(0);
  }
  await page.locator('input[value=patch]').check();
  await page.locator('.visit-actions>.button').click();
  await expect(page.locator('.reservation-grid')).toBeVisible();
  const calendar=await page.locator('.reservation-grid-scroll').evaluate(e=>({height:e.getBoundingClientRect().height,scrollHeight:e.scrollHeight,visible:visualViewport.height,row:document.querySelector('.reservation-grid tbody button').getBoundingClientRect().height}));
  if(width<=700){assert(Math.abs(calendar.height-Math.max(260,calendar.visible-450))<2,JSON.stringify(calendar));assert(calendar.row>=43);assert(calendar.scrollHeight>calendar.height);}
  const cell=page.locator('button[data-date="2026-09-30"][data-time="20:00"]');
  await expect(cell).toBeEnabled();await cell.click();
  await expect(page.locator('.visit-time-selection')).toContainText('20:00–21:00');
  await expect(page.locator('.reservation-grid button.chosen')).toHaveCount(2);
  await shot('calendar');
  // Fresh navigation and plan change exercise the independent beads capacity.
  await page.goto(base+'/visit?step=1');await page.locator('input[value=hourly]').check();
  await page.locator('.visit-actions>.button').click();
  const pink=page.locator('button[data-date="2026-09-29"][data-time="10:00"]');
  await expect(pink).toHaveClass(/low-capacity/);await expect(pink).toBeEnabled();
  await expect(pink).toHaveAttribute('title',lang==='zh'?'已预约 2 组':'2 groups booked');
  const color=await pink.evaluate(e=>getComputedStyle(e).backgroundColor);assert.equal(color,'rgb(255, 240, 244)');
  await shot('low-capacity');
  if(width>=1280){
   await page.goto(base+'/manage?view=reservations');await expect(page.locator('.timetable-scroll')).toHaveAttribute('aria-busy','false');
   const slot=page.locator('.timetable-slot[data-date="2026-09-29"][data-time="10:00"]');
   await expect(slot).toHaveClass(/low-capacity/);await expect(slot).toHaveAttribute('title',lang==='zh'?'已预约 2 组':'2 groups booked');
   await shot('admin-capacity');
  }
  if(key==='chromium-1440-900-zh'||key==='webkit-375-667-zh'){
   await page.goto(base+'/manage?view=reservations');
   await page.locator('.reservation-settings-entry:visible>.desk-button').click();
   const form=page.locator('.reservation-settings-form'),date=form.locator('.reservation-date-override');
   await expect(date.locator('input[type=date]')).toHaveValue('2026-09-30');
   await expect(date.locator('select').last()).toHaveValue('22:00');
   await date.scrollIntoViewIfNeeded();await shot('date-hours');
   const overflow=await form.evaluate(e=>e.scrollWidth-e.clientWidth);assert(overflow<=1);
   // Persist a no-op through the real admin form and ensure weekly hours survive.
   await form.locator('button:not([type])').click();
   await expect(form).not.toBeVisible();
   assert.deepEqual((await call('/manage/reservation-policy')).weekly_hours,before.weekly_hours);
  }
  assert.deepEqual(errors,[]);
  results.push({key,layout,calendar,color,errors});
  console.log(key+' PASS');
 }catch(e){await shot('FAIL');throw e;}
 finally{await browser.close();}
}
await fs.writeFile(new URL('results.json',out),JSON.stringify(results,null,2));
console.log('Booking layout checks: '+results.length+' states passed');
await fixture.dispose();
