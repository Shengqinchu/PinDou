// Public acceptance is read-only; real customer reservations are never fixtures.
import {chromium,webkit,expect} from '@playwright/test';
import assert from 'node:assert/strict';
import fs from 'node:fs/promises';
import {fileURLToPath} from 'node:url';
const base='https://pindoupuppy.com',out=new URL('../../artifacts/patch-launch/live/',import.meta.url);
await fs.mkdir(out,{recursive:true});
const expected=JSON.parse(await fs.readFile(new URL('../dist/version.json',import.meta.url),'utf8')).build,results=[];
for(const [type,width,height,lang] of [[chromium,1280,720,'zh'],[webkit,390,844,'en']]){
 const browser=await type.launch({ignoreDefaultArgs:['--hide-scrollbars']}),ctx=await browser.newContext({viewport:{width,height},hasTouch:width<700,reducedMotion:null});
 const writes=[],blockedTelemetry=[],telemetryErrors=[],errors=[];
 await ctx.addInitScript(lang=>localStorage.setItem('puppy-studio-language',lang),lang);
 await ctx.route('**/*',route=>{
  const req=route.request();if(['GET','HEAD','OPTIONS'].includes(req.method()))return route.continue();
  if(new URL(req.url()).pathname==='/cdn-cgi/rum'){blockedTelemetry.push(req.url());return route.fulfill({status:204,body:''});}
  writes.push(req.url());return route.abort();
 });
 const page=await ctx.newPage();page.setDefaultTimeout(30000);
 page.on('pageerror',e=>(/\/cdn-cgi\/rum\?.*access control checks/.test(e.message)?telemetryErrors:errors).push(e.message));
 const shot=async name=>page.screenshot({path:fileURLToPath(new URL(lang+'-'+name+'.png',out)),animations:'disabled'});
 try{
  const version=await (await ctx.request.get(base+'/version.json?verify=patch-launch')).json();assert.equal(version.build,expected);
  const response=await ctx.request.get(base+'/studio-api/patch-promotion'),promotion=await response.json();
  assert(response.ok());assert.match(response.headers()['cache-control'],/no-store/);
  assert.deepEqual(Object.keys(promotion).sort(),['campaign','enabled','quota','remaining']);
  assert.equal(promotion.campaign,'patch-launch-20260928');assert(promotion.enabled&&promotion.remaining>0);
  const protectedResponse=await ctx.request.get(base+'/studio-api/manage/patch-promotion');assert([401,403].includes(protectedResponse.status()));
  await page.goto(base+'/');
  const dialog=page.locator('.patch-launch-dialog');await expect(dialog).toHaveAttribute('data-phase','open');
  await expect(dialog).toContainText(lang==='zh'?'帆布带':'canvas strap');
  await expect(dialog).not.toContainText('帆布袋');await page.evaluate(()=>document.fonts.ready);
  const geometry=await page.locator('.patch-launch-panel').boundingBox();assert(geometry.x>=0&&geometry.y>=0&&geometry.x+geometry.width<=width+1&&geometry.y+geometry.height<=height+1);
  await shot('popup');
  await dialog.locator('button.button').click();
  await expect(page).toHaveURL(/\/visit\?/);await expect(page.locator('input[value=patch]')).toBeChecked();
  await expect(page.locator('.visit-flow-page')).toHaveAttribute('data-step','1');
  await expect(page.locator('.visit-patch-promotion')).toContainText(lang==='zh'?'帆布带':'canvas strap');
  await page.waitForTimeout(650);
  const layout=await page.evaluate(()=>({overflow:document.documentElement.scrollWidth-innerWidth,innerScroll:getComputedStyle(document.querySelector('.visit-scroll')).overflowY,actions:document.querySelector('.visit-actions').getBoundingClientRect().bottom}));
  assert(layout.overflow<=1&&layout.innerScroll==='visible');if(width>=1280)assert(layout.actions<=height+3);
  if(width<700)await page.locator('input[value=patch]').scrollIntoViewIfNeeded();await shot('card');
  await page.goto(base+'/');await page.waitForTimeout(650);await expect(dialog).not.toBeVisible();
  const calendar=await (await ctx.request.get(base+'/studio-api/reservation-calendar?guests=1')).json();
  assert.equal(calendar.policy_version,8);assert.equal(calendar.days.find(d=>d.date==='2026-09-30').close,'22:00');assert.equal(calendar.days.find(d=>d.date==='2026-10-07').close,'16:00');
  assert.deepEqual(writes,[]);assert.deepEqual(errors,[]);
  results.push({width,height,lang,build:version.build,promotion,geometry,layout,policy:calendar.policy_version,writes,blockedTelemetry,telemetryErrors,errors});console.log('PASS public '+lang+' '+width);
 }catch(e){await shot('FAILED');throw e;}finally{await browser.close();}
}
await fs.writeFile(new URL('results.json',out),JSON.stringify(results,null,2));
console.log('Verified '+results.length+' public views without business writes.');
