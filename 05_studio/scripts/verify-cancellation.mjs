import {chromium,webkit,expect} from '@playwright/test';
import AxeBuilder from '@axe-core/playwright';
import fs from 'node:fs/promises';
import assert from 'node:assert/strict';
import {fileURLToPath} from 'node:url';
const base=process.env.PINDOU_QA_ORIGIN||'http://127.0.0.1:19687';
if(!/^http:\/\/127\.0\.0\.1:\d+$/.test(base))throw new Error('Isolated QA only');
const out=new URL('../../artifacts/cancellation/',import.meta.url);await fs.mkdir(out,{recursive:true});
const errors=[],measurements=[];let context,page;
const browser=await chromium.launch({headless:true,ignoreDefaultArgs:['--hide-scrollbars']});
async function start(engine,locale='zh',viewport={width:1706,height:1100}){
 context=await engine.newContext({viewport,locale:locale==='zh'?'zh-CN':'en-CA'});
 await context.addInitScript(locale=>{localStorage.setItem('pd_web_token','qa-owner');localStorage.setItem('puppy-studio-language',locale);sessionStorage.setItem('puppy-studio-admin','qa-admin');},locale);
 page=await context.newPage();page.on('pageerror',e=>errors.push(e.message));
}
async function shot(name){await page.screenshot({path:fileURLToPath(new URL(name+'.png',out))});}
async function api(path,method='GET',data){const response=await page.request.fetch(base+path,{method,headers:{Authorization:'Bearer qa-owner'},data});assert(response.ok(),await response.text());return response.json();}
async function measure(name){
 await page.evaluate(()=>document.fonts.ready);await page.evaluate(()=>new Promise(r=>requestAnimationFrame(()=>requestAnimationFrame(r))));
 const state=await page.evaluate(()=>({width:innerWidth,height:innerHeight,body:document.documentElement.scrollWidth,dialog:[...document.querySelectorAll('.cancellation-dialog[open] .cancellation-panel')].map(e=>{const r=e.getBoundingClientRect();return{x:r.x,y:r.y,right:r.right,bottom:r.bottom};})}));
 assert(state.body<=state.width+1,name+' horizontal overflow');for(const r of state.dialog)assert(r.x>=-1&&r.y>=-1&&r.right<=state.width+1&&r.bottom<=state.height+1,name+' clipped dialog');
 measurements.push({name,...state});
}
try{
 await start(browser);const seed=await api('/qa/cancellation-seed','POST');
 for(const locale of ['zh','en']){
  for(const width of [320,375,768,1280,1706,2560]){
   await context.close();await start(browser,locale,{width,height:width<600?812:1050});
   await page.goto(base+'/manage?view=reservations');await expect(page.locator('.reservation-timetable:visible')).toBeVisible();
   await expect(page.locator('.reservation-timetable:visible .timetable-scroll')).toBeVisible();
   // Narrow layouts show a single date; advance from today to the seeded day.
   if(width<720)await page.locator('.reservation-timetable:visible .timetable-navigation button').last().click();
   await expect(page.locator('.reservation-timetable:visible .timetable-booking').first()).toBeVisible();
   await page.locator('.reservation-timetable:visible').scrollIntoViewIfNeeded();await page.locator('.reservation-timetable:visible .timetable-scroll').evaluate(el=>el.scrollTop=220);await measure('timetable-'+locale+'-'+width);
   const overlaps=await page.locator('.reservation-timetable:visible .timetable-events').evaluateAll(columns=>columns.flatMap(column=>{
    const blocks=[...column.querySelectorAll('.timetable-booking')].map(e=>({id:e.getAttribute('aria-label'),r:e.getBoundingClientRect()}));const bad=[];
    for(let i=0;i<blocks.length;i++)for(let j=i+1;j<blocks.length;j++){const a=blocks[i].r,b=blocks[j].r;if(a.top<b.bottom-1&&b.top<a.bottom-1&&a.left<b.right-1&&b.left<a.right-1)bad.push([blocks[i].id,blocks[j].id]);}return bad;
   }));assert.deepEqual(overlaps,[]);
   if([375,1706].includes(width))await shot('timetable-'+locale+'-'+width);
   await page.locator('.reservation-timetable:visible .timetable-booking').first().click();await expect(page.locator('.studio-drawer[open]')).toBeVisible();
   await page.keyboard.press('Escape');await expect(page.locator('.studio-drawer[open]')).toHaveCount(0);
  }
 }
 await context.close();await start(browser);
 await page.goto(base+'/reservation/'+seed.ids[0]);await page.locator('.reservation-cancel-link').click();
 await expect(page.locator('.cancellation-dialog[open] .cancellation-count')).toContainText('0 / 3');await expect(page.locator('.cancellation-dialog[data-phase=open]')).toBeVisible();
 await shot('cancel-confirm-desktop');await measure('cancel-desktop');
 const axe=await new AxeBuilder({page}).include('.cancellation-dialog').analyze();await fs.writeFile(new URL('accessibility.json',out),JSON.stringify(axe.violations,null,2));assert.deepEqual(axe.violations,[]);
 await page.keyboard.press('Escape');await expect(page.locator('.cancellation-dialog[open]')).toHaveCount(0);
 assert.equal((await api('/studio-api/reservations/'+seed.ids[0]+'/cancellation')).used,0);
 await page.locator('.reservation-cancel-link').click();await expect(page.locator('.cancellation-dialog[open] .cancellation-confirm')).toBeEnabled();
 // Server commits, response is lost: retry the same version, count only once.
 let lose=true;await page.route('**/studio-api/reservations/*/cancel',async route=>{if(lose){lose=false;await route.fetch();await route.abort();}else await route.continue();});
 await page.locator('.cancellation-dialog[open] .cancellation-confirm').click();await expect(page.locator('.cancellation-dialog[open] .cancellation-panel [role=alert]')).toBeVisible();
 await page.locator('.cancellation-dialog[open] .cancellation-confirm').click();await expect(page.locator('.cancellation-dialog[open]')).toHaveCount(0);
 await expect(page.locator('h1')).toContainText('取消');assert.equal((await api('/studio-api/reservations/'+seed.ids[1]+'/cancellation')).used,1);
 await page.goto(base+'/account');await page.getByRole('button',{name:'我的预约',exact:true}).click();
 await expect(page.locator('.account-bookings')).not.toContainText('等待付款');
 await page.locator('.account-bookings .reservation-cancel-link').first().click();await expect(page.locator('.cancellation-dialog[open] .cancellation-count')).toContainText('1 / 3');
 await page.locator('.cancellation-dialog[open] .cancellation-confirm').click();await expect(page.locator('.cancellation-dialog[open]')).toHaveCount(0);
 const active=(await api('/studio-api/auth/reservations')).items.filter(x=>x.can_cancel);
 await api('/studio-api/reservations/'+active[0].id+'/cancel','POST',{version:active[0].version});
 await page.reload();await page.getByRole('button',{name:'我的预约',exact:true}).click();await page.locator('.account-bookings .reservation-cancel-link').first().click();
 await expect(page.locator('.cancellation-dialog[open] .cancellation-panel')).toContainText('本月已达到');await expect(page.locator('.cancellation-dialog[open] .cancellation-confirm')).toHaveCount(0);await shot('monthly-limit');
 const remaining=(await api('/studio-api/auth/reservations')).items.find(x=>x.can_cancel);
 for(const engineName of ['chromium','webkit']){
  const engine=engineName==='chromium'?browser:await webkit.launch({headless:true});
  for(const locale of ['zh','en'])for(const size of [{width:320,height:568},{width:390,height:844},{width:844,height:390}]){
   await context.close();await start(engine,locale,size);await page.goto(base+'/reservation/'+remaining.id);await page.locator('.reservation-cancel-link').click();await expect(page.locator('.cancellation-dialog[data-phase=open]')).toBeVisible();await expect(page.locator('.cancellation-dialog[open] .cancellation-panel .form-error')).toBeVisible();
   await measure(engineName+'-'+locale+'-'+size.width+'x'+size.height);if(size.width===390)await shot('limit-'+engineName+'-'+locale);
  }
  if(engineName==='webkit'){await context.close();await engine.close();}
 }
 assert.deepEqual(errors,[]);await fs.writeFile(new URL('verification.json',out),JSON.stringify({checks:['one block per group','no overlapping blocks','group opens details','both cancellation entry points','keep leaves quota unchanged','lost response replay','three per month limit','no payment wording','keyboard and dialog accessibility'],measurements,errors},null,2));
 console.log(JSON.stringify({passed:true,layouts:measurements.length,errors:errors.length}));
}finally{await context?.close().catch(()=>{});await browser.close();}
