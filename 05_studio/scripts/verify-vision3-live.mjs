// Public read-only UI checks. Customer/owner data submissions are blocked.
import {chromium,expect} from '@playwright/test';
import fs from 'node:fs';
import assert from 'node:assert/strict';
const base='https://pindoupuppy.com',build='2026-09-08T20:45:21.363Z';
const out='../artifacts/vision3/live';fs.mkdirSync(out,{recursive:true});
const results=[],errors=[];
const browser=await chromium.launch({headless:true,ignoreDefaultArgs:['--hide-scrollbars']});
try{
 const context=await browser.newContext({viewport:{width:1440,height:1000},reducedMotion:null});
 await context.route('**/studio-api/**',route=>['GET','HEAD'].includes(route.request().method())?route.continue():route.abort());
 const page=await context.newPage();page.on('pageerror',e=>errors.push(e.message));
 for(const path of ['/','/visit','/details','/journal','/journal/6a6d2925000000000e03c000','/shop','/manage']){
  const response=await page.goto(base+path,{waitUntil:'domcontentloaded'});assert.equal(response.status(),200);
  await page.evaluate(()=>document.fonts.ready);
  await expect(page.locator('meta[name="studio-build"]')).toHaveAttribute('content',build);
  assert.equal(await page.locator('#studio-published-content').count(),1);
  if(path==='/journal')await expect(page.locator('.journal-story')).toHaveCount(7);
  if(path.startsWith('/journal/'))await expect(page.locator('.journal-entry-photos figure')).toHaveCount(17);
  if(path==='/visit')await page.locator('.reservation-grid').waitFor();
  const state=await page.evaluate(()=>({url:location.href,overflow:document.documentElement.scrollWidth>innerWidth+1,mode:document.documentElement.dataset.motion,systemReduced:matchMedia('(prefers-reduced-motion:reduce)').matches,robots:document.querySelector('meta[name="robots"]')?.content}));
  assert.equal(state.overflow,false,path);results.push({path,...state});
 }
 await page.goto(base+'/visit?motion=full');await page.locator('.reservation-grid').waitFor();await expect(page.locator('html')).toHaveAttribute('data-motion','full');
 const card=page.locator('label').filter({has:page.locator('input[value="hourly"]')});
 await card.hover();await page.waitForTimeout(160);
 const intermediate=await card.evaluate(e=>({duration:getComputedStyle(e).transitionDuration,transform:getComputedStyle(e).transform}));assert(intermediate.duration.includes('0.3s'));
 await page.goto(base+'/visit');await expect(page.locator('html')).toHaveAttribute('data-motion','full');await page.reload();await expect(page.locator('html')).toHaveAttribute('data-motion','full');
 results.push({motionPreferencePersists:true,intermediate});
 await page.goto(base+'/');await page.evaluate(()=>document.fonts.ready);await page.waitForTimeout(1600);
 const pos=()=>page.locator('.vision-hero-photo').evaluate(e=>({x:e.getBoundingClientRect().x,width:e.getBoundingClientRect().width}));
 const before=await pos();await page.getByRole('button',{name:'网站菜单',exact:true}).click();await page.waitForTimeout(550);assert.deepEqual(await pos(),before);await page.getByRole('button',{name:'关闭菜单',exact:true}).click();await page.waitForTimeout(900);assert.deepEqual(await pos(),before);
 await page.screenshot({path:out+'/home-desktop.png'});results.push({menuShift:0,position:before});
 await page.setViewportSize({width:390,height:844});await page.waitForTimeout(150);await page.screenshot({path:out+'/home-mobile.png'});
 assert.equal(await page.evaluate(()=>document.documentElement.scrollWidth>innerWidth+1),false);
 const calendar=await (await page.request.get(base+'/studio-api/reservation-calendar')).json();assert.equal(calendar.minimum_minutes,120);assert.equal(calendar.weekly_hours[2].close,'16:00');assert.equal(calendar.weekly_hours[3].close,'18:00');results.push({hours:true,minimum:calendar.minimum_minutes});
 for(const url of ['https://www.pindoupuppy.com/','https://pindoupuppy.com/studio/visit','https://pindoupuppy.com/studio/#space','https://pindoupuppy.com/upload','https://www.pindoupuppy.com/upload','https://pindoupuppy.com/tutorial']){
  const response=await page.goto(url,{waitUntil:'domcontentloaded'});await page.waitForTimeout(200);
  const data=await page.evaluate(()=>({url:location.href,title:document.title,scripts:[...document.scripts].map(x=>x.src).filter(Boolean)}));assert.equal(response.status(),200);results.push({requested:url,status:response.status(),...data});
  if(url==='https://www.pindoupuppy.com/')assert.equal(new URL(data.url).hostname,'pindoupuppy.com');
  if(url.endsWith('/studio/visit'))assert.equal(new URL(data.url).pathname,'/visit');
  if(url.endsWith('/upload'))assert(data.scripts.some(x=>x.includes('/assets/index-D_x1Yq-W.js')));
 }
 await context.close();
}catch(e){errors.push(e.stack);}finally{await browser.close();}
fs.writeFileSync(out+'/verification.json',JSON.stringify({build,results,errors},null,2));console.log(JSON.stringify({checks:results.length,results,errors}));if(errors.length)process.exitCode=1;
