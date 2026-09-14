// Public reads only in --live mode; failure injection and upload use loopback.
import {chromium, webkit, expect} from '@playwright/test';
import assert from 'node:assert/strict';
import fs from 'node:fs/promises';
import {fileURLToPath} from 'node:url';
const live=process.argv.includes('--live'),base=live?'https://pindoupuppy.com':'http://127.0.0.1:4184';
const out=new URL('../../artifacts/image-delivery-20260914/',import.meta.url);
await fs.mkdir(out,{recursive:true});
const results=[];
async function visibleReady(page){
 await expect.poll(()=>page.locator('.shop-card-preview img').evaluateAll(images=>{
  const visible=images.filter(img=>{const r=img.getBoundingClientRect();return r.top<innerHeight&&r.bottom>0;});
  return visible.length>0&&visible.every(img=>img.complete&&img.naturalWidth>0&&getComputedStyle(img).opacity==='1');
 }),{timeout:30000}).toBe(true);
}
async function setup(context){
 await context.addInitScript(()=>{
  localStorage.setItem('puppy-studio-locale','zh');
  window.__entrance=[];
  function sample(){
   const line=document.querySelector('#main h1.lift-title > .lift-line');
   if(line){const s=getComputedStyle(line);window.__entrance.push({path:location.pathname,opacity:+s.opacity,y:new DOMMatrix(s.transform).m42});if(window.__entrance.length>1000)window.__entrance.shift();}
   requestAnimationFrame(sample);
  }requestAnimationFrame(sample);
 });
 return context.newPage();
}
for(const [name,engine] of [['chromium',chromium],['webkit',webkit]]){
 const browser=await engine.launch();
 try{
  const context=await browser.newContext({viewport:{width:1440,height:900},reducedMotion:null});
  const aborted=[],errors=[],writes=[];
  await context.exposeBinding('__recordPreviewAbort',(_source,url)=>aborted.push({url,time:Date.now(),source:'signal'}));
  await context.addInitScript(()=>{
   const native=window.fetch;
   window.fetch=function(input,init){
    const url=new URL(typeof input==='string'?input:input instanceof URL?input.href:input.url,location.href).href;
    if(url.includes('/studio-api/media/previews/')&&init?.signal){
     const record=()=>window.__recordPreviewAbort(url).catch(()=>{});
     if(init.signal.aborted)record();else init.signal.addEventListener('abort',record,{once:true});
    }
    return native.call(this,input,init);
   };
  });
  const page=await setup(context);
  page.on('requestfailed',request=>{
   if(request.url().includes('/studio-api/media/previews/')&&/cancel|abort/i.test(request.failure()?.errorText||''))
    aborted.push({url:request.url(),time:Date.now(),source:'cancelled-network-request'});
  });
  page.on('pageerror',error=>{if(!error.message.includes('/cdn-cgi/rum'))errors.push({message:error.message,time:Date.now()})});
  page.on('request',req=>{if(req.url().includes('/studio-api/')&&!['GET','HEAD','OPTIONS'].includes(req.method()))writes.push({method:req.method(),path:new URL(req.url()).pathname})});
  const animationChecks=[];
  for(const path of ['/','/shop','/visit','/journal','/details','/tools']){
   await page.goto(base+path,{waitUntil:'domcontentloaded'});
   await page.locator('#main h1.lift-title').waitFor({timeout:30000});
   await page.waitForTimeout(1250);
   const samples=await page.evaluate(()=>window.__entrance);
   assert.ok(samples.some(s=>s.opacity<.8&&s.y>1),`${name} ${path}: actual entrance intermediates`);
   await expect(page.locator('#main h1.lift-title > .lift-line').first()).toHaveCSS('opacity','1');
   animationChecks.push({path,minOpacity:Math.min(...samples.map(s=>s.opacity)),maxY:Math.max(...samples.map(s=>s.y))});
  }
  // In-app navigation enters, query changes leave the same form/grid mounted.
  await page.locator('.vision-header a[href="/shop"]').first().click();
  await page.locator('.shop-page').waitFor();
  await page.waitForTimeout(1100);await visibleReady(page);
  assert.ok((await page.evaluate(()=>window.__entrance.filter(s=>s.path==='/shop'))).some(s=>s.opacity<.8&&s.y>1),'Navigation shares the direct-entry animation');
  const loaded=await page.locator('.shop-card-preview img').evaluateAll(images=>images.filter(img=>img.getAttribute('src')).length);
  const total=await page.locator('.shop-card-preview img').count();
  assert.ok(loaded<total,`Only nearby images requested: ${loaded}/${total}`);
  if(!live){
   // Reproduce WebKit's error event for a lazy placeholder before it has src.
   const deferred=page.locator('.shop-card-preview img').last();
   assert.equal(await deferred.getAttribute('src'),null);
   await deferred.evaluate(image=>image.dispatchEvent(new Event('error')));
   await deferred.scrollIntoViewIfNeeded();
   await expect.poll(()=>deferred.getAttribute('src')).toContain('/previews/v1/');
   await expect.poll(()=>deferred.evaluate(i=>i.complete&&i.naturalWidth>0)).toBe(true);
   await page.evaluate(()=>scrollTo(0,0));
  }
  await page.locator('.shop-children button').filter({hasText:'B系列'}).click();
  await visibleReady(page);
  const search=page.locator('.shop-search input');await search.fill('B1');
  await page.evaluate(()=>{window.__savedSearch=document.querySelector('.shop-search input');window.__entrance=[]});
  await page.locator('.shop-action').first().click();
  await page.locator('dialog[data-phase="open"]').waitFor();
  await page.keyboard.press('Escape');
  await expect(page.locator('dialog[open]')).toHaveCount(0);
  await expect(search).toHaveValue('B1');
  assert.ok(await page.evaluate(()=>window.__savedSearch===document.querySelector('.shop-search input')));
  assert.ok((await page.evaluate(()=>window.__entrance)).every(s=>s.opacity===1));
  await search.fill('');await expect(page.locator('.shop-card')).toHaveCount(33);await visibleReady(page);
  const first=page.locator('.shop-card').filter({has:page.locator('.shop-name',{hasText:/^B1$/})}).first();
  const thumbnail=await first.locator('img').getAttribute('src');
  assert.ok(thumbnail.includes('/previews/v1/320/'));
  await first.locator('.shop-card-preview').click();
  const full=page.locator('dialog[data-phase="open"] .shop-detail-image');await full.evaluate(img=>img.decode());
  assert.ok(!(await full.getAttribute('src')).includes('/previews/'));
  await page.keyboard.press('Escape');
  await expect(page.locator('dialog[open]')).toHaveCount(0);
  await page.evaluate(()=>scrollTo(0,0));await visibleReady(page);
  // Revisit uses the browser HTTP/memory cache with no query-based cache buster.
  const previouslyVisible=await page.locator('.shop-card-preview img').evaluateAll(images=>images.filter(i=>{const r=i.getBoundingClientRect();return r.top<innerHeight&&r.bottom>0}).map(i=>i.currentSrc));
  await page.locator('.shop-children button').filter({hasText:'A系列'}).click();await visibleReady(page);
  await page.evaluate(()=>performance.clearResourceTimings());
  await page.locator('.shop-children button').filter({hasText:'B系列'}).click();await expect(page.locator('.shop-card')).toHaveCount(33);await page.evaluate(()=>scrollTo(0,0));await visibleReady(page);
  const allRepeat=await page.evaluate(()=>performance.getEntriesByType('resource').filter(r=>r.name.includes('/previews/')).map(r=>({name:r.name,type:r.initiatorType,transfer:r.transferSize,bytes:r.encodedBodySize,duration:r.duration})));
  await fs.writeFile(new URL(`${live?'live':'local'}-${name}-cache.json`,out),JSON.stringify({previouslyVisible,allRepeat},null,2));
  const repeat=allRepeat.filter(r=>r.type==='img'&&previouslyVisible.includes(r.name));
  assert.ok(repeat.every(r=>r.transfer===0),`${name}: cached revisit`);
  const rendering=await page.locator('.shop-card-preview img').evaluateAll(images=>images.filter(i=>{const r=i.getBoundingClientRect();return r.top<innerHeight&&r.bottom>0}).map(i=>({url:i.currentSrc,cached:i.dataset.cached,transition:getComputedStyle(i).transitionDuration})));
  await fs.writeFile(new URL(`${live?'live':'local'}-${name}-cache-rendering.json`,out),JSON.stringify({previouslyVisible,rendering},null,2));
  const cachedRendering=rendering.filter(i=>previouslyVisible.includes(i.url));
  assert.ok(cachedRendering.length>0&&cachedRendering.every(i=>i.cached==='true'&&i.transition==='0s'),'Cached images paint without another fade');
  await page.screenshot({path:fileURLToPath(new URL(`${live?'live':'local'}-${name}-shop.png`,out))});
  // Selecting reduced motion interrupts an entrance and restores readable styles.
  await page.locator('.vision-header a[href="/visit"]').first().evaluate(a=>a.click());
  await page.locator('.visit-flow-heading h1').waitFor();
  await page.evaluate(()=>{localStorage.setItem('puppy-studio-motion','reduced');dispatchEvent(new StorageEvent('storage',{key:'puppy-studio-motion'}))});
  await expect(page.locator('.visit-flow-heading h1 > .lift-line').first()).toHaveCSS('opacity','1');
  await page.goto(base+'/shop?motion=reduced');await visibleReady(page);
  assert.ok((await page.evaluate(()=>window.__entrance)).every(s=>s.opacity===1&&s.y===0));
  // WebKit can report a cancelled fetch through its access-control error stream.
  // Only accept errors matched to an observed abort/cancellation for that exact public
  // image within two seconds. A real CORS failure without cancellation still fails.
  const intentionalCancellations=errors.filter(error=>aborted.some(item=>error.message.includes(new URL(item.url).pathname)&&Math.abs(item.time-error.time)<2000));
  const unexpected=errors.filter(error=>!intentionalCancellations.includes(error));
  await fs.writeFile(new URL(`${live?'live':'local'}-${name}-network-cancellation.json`,out),JSON.stringify({errors,aborted,intentionalCancellations,unexpected},null,2));
  assert.deepEqual(unexpected,[]);assert.deepEqual(writes,[]);
  // True 3x density selects a larger preview; no horizontal overflow at 320px.
  const mobile=await browser.newContext({viewport:{width:390,height:844},deviceScaleFactor:3,isMobile:true,hasTouch:true});
  const phone=await setup(mobile);await phone.goto(base+'/shop');await visibleReady(phone);
  for(const width of [320,390]){await phone.setViewportSize({width,height:844});assert.ok(await phone.evaluate(()=>document.documentElement.scrollWidth<=innerWidth));}
  await phone.waitForTimeout(1100);
  await phone.screenshot({path:fileURLToPath(new URL(`${live?'live':'local'}-${name}-mobile.png`,out))});
  await phone.setViewportSize({width:600,height:900});
  await expect.poll(()=>phone.locator('.shop-card-preview img').first().getAttribute('src')).toContain('/800/');
  await visibleReady(phone);
  const density=await phone.locator('.shop-card-preview img').first().getAttribute('src');
  await mobile.close();
  if(!live){
   // A broken preview falls back to the preserved original once.
   const failure=await browser.newContext({viewport:{width:1440,height:900}});
   await failure.route('**/studio-api/media/previews/**',route=>route.fulfill({status:503,body:'preview unavailable'}));
   const failed=await setup(failure);await failed.goto(base+'/shop');await visibleReady(failed);
   assert.ok(!(await failed.locator('.shop-card-preview img').first().getAttribute('src')).includes('/previews/'));
   await failure.close();
   // Data Saver forbids background fetch preloads while visible pictures work.
   const limited=await browser.newContext();
   await limited.addInitScript(()=>Object.defineProperty(navigator,'connection',{value:{saveData:true,effectiveType:'4g'},configurable:true}));
   const saved=await setup(limited);await saved.goto(base+'/shop');await visibleReady(saved);await saved.waitForTimeout(1400);
   assert.equal(await saved.evaluate(()=>performance.getEntriesByType('resource').filter(r=>r.name.includes('/previews/')&&r.initiatorType==='fetch').length),0);
   await limited.close();
  }
  results.push({engine:name,passed:true,build:await page.evaluate(()=>document.documentElement.dataset.studioBuild),animationChecks,nearbyRequested:loaded,totalImages:total,cachedRevisit:repeat.length,densitySource:density,errors:unexpected,intentionalCancellations,writes});
  console.log(`${name}: image delivery and all main entrances passed`);
  await context.close();
 }finally{await browser.close();}
}
await fs.writeFile(new URL(`${live?'live':'local'}-browser.json`,out),JSON.stringify(results,null,2));
