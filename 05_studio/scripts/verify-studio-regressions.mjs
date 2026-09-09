// Isolated loopback QA only: start a fresh 06_studio/qa_server.py and a built preview on port 4184.
import {chromium,webkit,expect} from '@playwright/test';
import fs from 'node:fs/promises';
import assert from 'node:assert/strict';
const base='http://127.0.0.1:4184',out=new URL('../../artifacts/studio-regression-20260909/',import.meta.url),results=[];
await fs.mkdir(out,{recursive:true});
async function motion(engine,name,options,args=[]){
 const browser=await engine.launch({headless:true,args,ignoreDefaultArgs:['--hide-scrollbars']});
 try{
  const context=await browser.newContext({viewport:{width:1440,height:1000},...options});
  const page=await context.newPage();page.setDefaultTimeout(10000);
  await page.goto(base+'/?motion=full',{waitUntil:'networkidle'});
  const area=page.locator('.vision-carousel-window'),buttons=page.locator('.vision-carousel-controls button');
  await area.scrollIntoViewIfNeeded();await page.waitForTimeout(100);
  const before=await area.evaluate(e=>({width:e.clientWidth,left:e.scrollLeft,system:matchMedia('(prefers-reduced-motion:reduce)').matches}));
  await page.evaluate(()=>{window.samples=[];let start=performance.now();function sample(t){window.samples.push({t:t-start,left:document.querySelector('.vision-carousel-window').scrollLeft});if(t-start<950)requestAnimationFrame(sample)}requestAnimationFrame(sample)});
  await buttons.last().click();await page.waitForTimeout(1000);
  const samples=await page.evaluate(()=>window.samples),intermediates=samples.filter(s=>s.left>1&&s.left<before.width-1);
  assert(intermediates.length>5,`${name} missing animated frames`);
  assert(Math.abs(await area.evaluate(e=>e.scrollLeft)-before.width)<2);
  await buttons.last().click();await page.waitForTimeout(80);await buttons.first().click();await page.waitForTimeout(950);
  assert(Math.abs(await area.evaluate(e=>e.scrollLeft)-before.width)<2,`${name} interrupted reverse`);
  for(let i=0;i<3;i++){await buttons.last().click();await page.waitForTimeout(60)}await page.waitForTimeout(950);
  assert(Math.abs(await area.evaluate(e=>e.scrollLeft)-4*before.width)<2,`${name} quick queue`);
  await buttons.last().click();await page.waitForTimeout(100);await page.setViewportSize({width:600,height:820});await page.waitForTimeout(300);
  assert(Math.abs(await area.evaluate(e=>e.scrollLeft/e.clientWidth)-5)<.01,`${name} resize`);
  await page.locator('.vision-header').scrollIntoViewIfNeeded();await page.locator('.vision-header-actions>.icon-button').last().click();
  await page.locator('.motion-settings button').getByText('减少动效',{exact:true}).click();
  assert.equal(await page.locator('html').getAttribute('data-motion'),'reduced');await page.keyboard.press('Escape');
  await area.scrollIntoViewIfNeeded();await buttons.last().click();await page.waitForTimeout(40);
  assert(Math.abs(await area.evaluate(e=>e.scrollLeft/e.clientWidth)-6)<.01,`${name} reduced`);
  await page.reload({waitUntil:'networkidle'});assert.equal(await page.locator('html').getAttribute('data-motion'),'reduced');
  results.push({kind:'motion',name,systemReduced:before.system,intermediateFrames:intermediates.length,firstMovement:intermediates[0]?.t,lastMovement:intermediates.at(-1)?.t,reverse:true,rapid:true,resize:true,preference:true});
  await fs.writeFile(new URL(`motion-${name}.json`,out),JSON.stringify(samples));
 }finally{await browser.close()}
}
await motion(chromium,'windows-native',{reducedMotion:null});
await motion(chromium,'chrome-smooth-disabled',{reducedMotion:'no-preference'},['--disable-smooth-scrolling']);
await motion(webkit,'webkit-reduced-override',{reducedMotion:'reduce'});

const browser=await chromium.launch({headless:true});
try{
 const context=await browser.newContext({viewport:{width:1500,height:1000},reducedMotion:'reduce'});
 await context.addInitScript(()=>sessionStorage.setItem('puppy-studio-admin','local-qa'));
 const page=await context.newPage();page.setDefaultTimeout(10000);const errors=[];page.on('pageerror',e=>errors.push(e.message));
 await page.goto(base+'/manage?view=content',{waitUntil:'networkidle'});
 await page.locator('.editor-commandbar select').selectOption('pages-Visit');
 const key='make_from_your_chosen_arrival_until_37196a';
 const field=page.locator(`[data-content-key="${key}"] textarea`).first();
 await expect(field).toHaveValue('从所选时间开始，可拼到当天 {v0}。');
 await expect(page.locator('.editor-preview-state')).toHaveAttribute('data-state','synced');
 await field.fill('店主修改后的说明，结束于 {v0}。');
 await expect(page.locator('.editor-preview-state')).toHaveAttribute('data-state','synced');
 const preview=()=>page.frameLocator('.editor-preview-canvas iframe');
 await expect(preview().getByText('店主修改后的说明，结束于 22:00。',{exact:true})).toBeVisible();
 const frameSrc=await page.locator('.editor-preview-canvas iframe').getAttribute('src');assert(frameSrc.startsWith('/studio-api/site?'));
 await page.reload({waitUntil:'networkidle'});await page.locator('.editor-commandbar select').selectOption('pages-Visit');
 await expect(field).toHaveValue('店主修改后的说明，结束于 {v0}。');
 await expect(preview().getByText('店主修改后的说明，结束于 22:00。',{exact:true})).toBeVisible();
 // Deliberately lose the child receiver, then reconnect the preview only.
 await page.locator('.editor-preview-canvas iframe').evaluate(e=>e.src='about:blank');
 await field.fill('断线之后仍保留，结束于 {v0}。');
 await expect(page.locator('.editor-preview-state')).toHaveAttribute('data-state','error',{timeout:6500});
 await page.getByRole('button',{name:'重新连接预览',exact:true}).click();
 await expect(preview().getByText('断线之后仍保留，结束于 22:00。',{exact:true})).toBeVisible();
 await expect(page.locator('.editor-preview-state')).toHaveAttribute('data-state','synced');
 // One failed publication must retain all text, then retry succeeds.
 await page.route('**/studio-api/manage/content/pages-Visit',async route=>{
  if(route.request().method()==='PUT')await route.fulfill({status:503,contentType:'application/json',body:JSON.stringify({detail:'server_error'})});else await route.continue();
 });
 await page.getByRole('button',{name:'发布此页',exact:true}).click();await expect(page.locator('.desk-error')).toBeVisible();
 await expect(field).toHaveValue('断线之后仍保留，结束于 {v0}。');await page.unroute('**/studio-api/manage/content/pages-Visit');
 await page.getByRole('button',{name:'发布此页',exact:true}).click();await expect(page.locator('.editor-state')).toContainText('已发布');
 const published=(await (await page.request.get(base+'/studio-api/content')).json()).modules['pages-Visit'][key];assert.equal(published[0],'断线之后仍保留，结束于 {v0}。');
 const visitor=await context.newPage();await visitor.goto(base+'/visit',{waitUntil:'networkidle'});await expect(visitor.getByText('断线之后仍保留，结束于 22:00。',{exact:true})).toBeVisible();
 for(const [width,height] of [[320,740],[390,844],[768,1024],[1280,720],[1920,1080]]){await page.setViewportSize({width,height});await page.waitForTimeout(60);assert(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth+1));results.push({kind:'editor-layout',width,height});}
 assert.deepEqual(errors,[]);results.push({kind:'preview',sameOriginEndpoint:true,editing:true,refreshRecovery:true,reconnect:true,failedSaveRetained:true,publish:true,errors});
 await context.close();
}finally{await browser.close()}
await fs.writeFile(new URL('verification.json',out),JSON.stringify(results,null,2));console.log(JSON.stringify(results,null,2));
