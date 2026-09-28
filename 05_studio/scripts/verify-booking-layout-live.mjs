// Public read-only acceptance for the owner's September 28 layout/hours request.
import {chromium,webkit,expect} from '@playwright/test';
import assert from 'node:assert/strict';
import fs from 'node:fs/promises';
import {fileURLToPath} from 'node:url';
const base='https://pindoupuppy.com',out=new URL('../../artifacts/booking-layout/live/',import.meta.url);
await fs.mkdir(out,{recursive:true});
const expected=JSON.parse(await fs.readFile(new URL('../dist/version.json',import.meta.url),'utf8')).build,results=[];
for(const [type,width,height,lang] of [[chromium,1366,768,'zh'],[webkit,390,844,'en']]){
 const browser=await type.launch(),ctx=await browser.newContext({viewport:{width,height},hasTouch:width<700,reducedMotion:null});
 const writes=[],blockedTelemetry=[],telemetryErrors=[],errors=[];
 await ctx.addInitScript(lang=>localStorage.setItem('puppy-studio-language',lang),lang);
 await ctx.route('**/*',route=>{if(['GET','HEAD','OPTIONS'].includes(route.request().method()))return route.continue();const url=route.request().url();if(new URL(url).pathname==='/cdn-cgi/rum'){blockedTelemetry.push(url);return route.fulfill({status:204,body:''});}writes.push(url);return route.abort();});
 const page=await ctx.newPage();page.setDefaultTimeout(25000);page.on('pageerror',e=>{
  // WebKit can surface an access-control error from the intercepted Cloudflare
  // beacon. Retain it separately; never hide application errors or allow writes.
  (/\/cdn-cgi\/rum\?.*access control checks/.test(e.message)?telemetryErrors:errors).push(e.message);
 });
 const shot=async name=>page.screenshot({path:fileURLToPath(new URL(lang+'-'+name+'.png',out)),fullPage:true,animations:'disabled'});
 try{
  const version=await (await ctx.request.get(base+'/version.json?verify=booking-layout')).json();assert.equal(version.build,expected);
  await page.goto(base+'/visit?step=1');await expect(page.locator('.visit-plans>label')).toHaveCount(3);
  await page.evaluate(()=>document.fonts.ready);await page.waitForTimeout(650);
  const layout=await page.evaluate(()=>({overflow:getComputedStyle(document.querySelector('.visit-scroll')).overflowY,bottom:document.querySelector('.visit-plans').getBoundingClientRect().bottom,actions:document.querySelector('.visit-actions').getBoundingClientRect().bottom,horizontal:document.documentElement.scrollWidth-innerWidth}));
  assert.equal(layout.overflow,'visible');assert(layout.horizontal<=1);if(width>=1280)assert(layout.bottom<height&&layout.actions<=height);
  await shot('choices');
  await page.locator('.visit-combined-offers .info-tip-trigger').first().click();await expect(page.getByRole('tooltip')).toBeVisible();await expect(page.getByRole('tooltip')).toContainText('10');
  await shot('offer-details');await page.locator('.visit-flow-heading').click();
  await page.locator('input[value=patch]').check();await page.locator('.visit-actions>.button').click();
  const cell=page.locator('button[data-date="2026-09-30"][data-time="20:00"]');await expect(cell).toBeEnabled();await cell.click();
  await expect(page.locator('.visit-time-selection')).toContainText('20:00–21:00');await expect(page.locator('.reservation-grid button.chosen')).toHaveCount(2);
  const calendar=await page.locator('.reservation-grid-scroll').evaluate(e=>({height:e.getBoundingClientRect().height,visible:visualViewport.height,row:document.querySelector('.reservation-grid tbody button').getBoundingClientRect().height}));
  if(width<700){assert(Math.abs(calendar.height-Math.max(260,calendar.visible-450))<2);assert(calendar.row>=44);}
  await shot('calendar');
  await page.goto(base+'/visit?step=1');await page.locator('input[value=hourly]').check();await page.locator('.visit-actions>.button').click();
  const pink=page.locator('button[data-date="2026-09-29"][data-time="10:00"]');await expect(pink).toHaveClass(/low-capacity/);await expect(pink).toBeEnabled();
  await expect(pink).toHaveAttribute('title',lang==='zh'?'已预约 2 组':'2 groups booked');await pink.scrollIntoViewIfNeeded();await shot('capacity');
  const response=await ctx.request.get(base+'/studio-api/reservation-calendar?guests=1'),data=await response.json();
  const wed=data.days.find(d=>d.date==='2026-09-30'),next=data.days.find(d=>d.date==='2026-10-07');
  assert.equal(wed.close,'22:00');assert.equal(next.close,'16:00');
  assert.deepEqual(writes,[]);assert.deepEqual(errors,[]);
  results.push({width,height,lang,build:version.build,policy:data.policy_version,layout,calendar,wednesday:wed.close,nextWednesday:next.close,writes,blockedTelemetry,telemetryErrors,errors});
 }catch(e){await shot('FAIL');throw e;}finally{await browser.close();}
}
await fs.writeFile(new URL('results.json',out),JSON.stringify(results,null,2));console.log(JSON.stringify(results));
