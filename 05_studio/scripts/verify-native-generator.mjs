// Isolated APIs/DB only. Never exercise purchases or paid AI on production.
import {chromium,expect} from '@playwright/test';
import fs from 'node:fs/promises';import path from 'node:path';import {fileURLToPath} from 'node:url';import assert from 'node:assert/strict';
const root=fileURLToPath(new URL('../../',import.meta.url)),out=path.join(root,'artifacts/generator-integration'),base='http://127.0.0.1:19678';
const png=await fs.readFile(path.join(root,'01_research/tech/test_inputs/cartoon_synthetic.png'));
const browser=await chromium.launch({headless:true,ignoreDefaultArgs:['--hide-scrollbars']}),results=[],errors=[];let currentPage;
async function context(language='en',user='qa-owner'){
 const ctx=await browser.newContext({viewport:{width:1440,height:960},locale:language==='zh'?'zh-CN':'en-CA',acceptDownloads:true});
 await ctx.addInitScript(({language,user})=>{if(!localStorage.getItem('qa-init')){localStorage.setItem('qa-init','1');localStorage.setItem('puppy-studio-locale',language);if(user){localStorage.setItem('pd_web_token',user);localStorage.setItem('pd_web_user',JSON.stringify({user_id:user,nickname:'Local QA',email:user+'@example.test'}));}}},{language,user});
 const page=await ctx.newPage();currentPage=page;page.setDefaultTimeout(10000);page.on('pageerror',e=>errors.push(e.message));return {ctx,page};
}
async function controls(page,data){return page.request.post(base+'/qa/controls',{data});}
async function pick(page,mode='Standard mode',size='26'){
 await page.goto(base+'/tools');await expect(page.locator('.control-panel')).toBeVisible();
 await page.locator('input[type=file]').first().setInputFiles({name:'example.png',mimeType:'image/png',buffer:png});
 await page.getByRole('button',{name:new RegExp(mode)}).click();await page.getByRole('button',{name:size,exact:true}).click();
}
async function generate(page){await page.locator('.generate-cta').click();await page.getByRole('button',{name:'Confirm generation',exact:true}).click();}
async function checkLayout(page,route,width,language){
 const box=await page.evaluate(()=>({w:innerWidth,scroll:document.documentElement.scrollWidth,h:innerHeight,body:document.documentElement.scrollHeight}));
 assert(box.scroll<=box.w+1,`${language} ${route} overflow at ${width}: ${JSON.stringify(box)}`);
 if(route.includes('/editor/'))assert(box.body<=box.h+2,`Editor clipped below viewport at ${width}: ${JSON.stringify(box)}`);
 const text=await page.locator('.generator-workspace').first().innerText();assert(!text.includes('We could not complete this action'),`${route} untranslated fallback`);
 if(language==='en')assert(!/[\u3400-\u9fff]/.test(text),`${route} untranslated UI: ${text}`);
 results.push({test:'layout and language',route,width,language,...box});
}
try{
 const {ctx,page}=await context();await controls(page,{clear:true});await pick(page);await generate(page);
 await expect(page).toHaveURL(/\/tools\/result\//);const resultUrl=page.url(),id=resultUrl.split('/').pop();
 await page.getByRole('link',{name:'Edit pattern',exact:true}).click();await expect(page.locator('.pattern-editor__overlay')).toBeVisible();
 await page.getByRole('button',{name:'Eraser',exact:true}).click();const canvas=await page.locator('.pattern-editor__overlay').boundingBox();await page.mouse.click(canvas.x+canvas.width/2,canvas.y+canvas.height/2);
 await expect(page.getByRole('button',{name:'Undo',exact:true})).toBeEnabled();await page.getByRole('button',{name:'Undo',exact:true}).click();await page.getByRole('button',{name:'Redo',exact:true}).click();
 await page.getByRole('button',{name:'Save',exact:true}).click();await expect.poll(async()=>{const a=await page.request.get(base+'/api/v1/artwork/'+id,{headers:{Authorization:'Bearer qa-owner'}});return (await a.json()).pattern_data.grid.flat().filter(x=>x===null).length;}).toBe(1);
 const download=page.waitForEvent('download');await page.getByRole('button',{name:'Download',exact:true}).click();assert((await download).suggestedFilename().endsWith('.png'));
 await page.getByRole('button',{name:'All colours',exact:true}).click();await expect(page.locator('dialog[open]')).toBeVisible();
 for(let n=0;n<12;n++){await page.keyboard.press('Tab');assert(await page.evaluate(()=>!!document.activeElement?.closest('dialog[open]')));}
 await page.keyboard.press('Escape');await expect(page.locator('dialog[open]')).toHaveCount(0);
 results.push({test:'erase undo redo, saved grid, PNG download and modal focus/Escape',passed:true});
 await controls(page,{fail_save:true});await page.mouse.click(canvas.x+canvas.width/2+28,canvas.y+canvas.height/2);await page.getByRole('button',{name:'Save',exact:true}).click();await expect(page.locator('.editor-page')).toContainText('Saving failed');
 let guarded=false;page.once('dialog',dialog=>{guarded=true;void dialog.dismiss();});await page.getByRole('link',{name:'Home',exact:true}).first().click();assert(guarded);await expect(page).toHaveURL(/\/tools\/editor\//);
 await controls(page,{});await page.getByRole('button',{name:'Save',exact:true}).click();await expect(page.locator('.editor-page')).not.toContainText('Saving failed');results.push({test:'save failure retains edits and prevents unconfirmed navigation',passed:true});
 const routes=[['/tools','.control-panel'],['/tools/result/'+id,'.result-card'],['/tools/editor/'+id,'.pattern-editor__overlay'],['/tools/works','.works-page'],['/tools/tutorial','.tutorial-page']];
 for(const language of ['zh','en']){
  await page.evaluate(lang=>localStorage.setItem('puppy-studio-locale',lang),language);
  for(const width of [320,390,768,1440,2560])for(const [route,selector] of routes){
   await page.setViewportSize({width,height:900});await page.goto(base+route);await expect(page.locator(selector)).toBeVisible();await page.evaluate(()=>document.fonts.ready);await checkLayout(page,route,width,language);
   if(width===390||width===1440)await page.screenshot({path:path.join(out,`native-${language}-${width}-${route.split('/')[2]||'upload'}.png`)});
  }
 }
 await page.setViewportSize({width:1440,height:960});await page.goto(base+'/tools');await page.locator('.generator-allowance>button').click();await expect(page.locator('.pricing-modal[open]')).toBeVisible();await page.keyboard.press('Escape');await expect(page.locator('.pricing-modal[open]')).toHaveCount(0);
 await ctx.close();

 const late=await context();currentPage=late.page;await controls(late.page,{clear:true,delay:2});await pick(late.page);await generate(late.page);await expect(late.page).toHaveURL(/\/tools\/loading/);await late.page.locator('.generator-heading nav a[href="/tools/tutorial"]').click();await expect(late.page.locator('.generator-ready')).toBeVisible();await expect(late.page).toHaveURL(/\/tools\/tutorial/);results.push({test:'late completion does not steal navigation',passed:true});await late.ctx.close();

 const resume=await context();currentPage=resume.page;await controls(resume.page,{clear:true});await resume.page.route('**/api/v1/generate/status/*',async route=>{await new Promise(r=>setTimeout(r,2400));await route.continue().catch(()=>{});});
 await pick(resume.page,'AI mode');await generate(resume.page);
 await expect.poll(()=>resume.page.evaluate(()=>new Promise(resolve=>{const q=indexedDB.open('pindou-generator-draft-v1');q.onsuccess=()=>{const db=q.result,r=db.transaction('draft').objectStore('draft').get('current');r.onsuccess=()=>{resolve(r.result?.jobId||'');db.close();};};}))).toMatch(/^job-/);
 await resume.page.reload();await expect(resume.page).toHaveURL(/\/tools\/result\//,{timeout:15000});const writes=await (await resume.page.request.get(base+'/qa/requests')).json();assert.equal(writes.filter(r=>r.path==='generate/ai').length,1);results.push({test:'reload resumes original AI job with one submission',passed:true});await resume.ctx.close();

 const unknown=await context();currentPage=unknown.page;await controls(unknown.page,{clear:true,delay:3});await pick(unknown.page);await generate(unknown.page);await expect.poll(async()=>((await (await unknown.page.request.get(base+'/qa/requests')).json()).filter(r=>r.path==='generate/script').length)).toBe(1);await unknown.page.reload();await expect(unknown.page.locator('.loading-error')).toContainText('could not confirm');assert.equal((await (await unknown.page.request.get(base+'/qa/requests')).json()).filter(r=>r.path==='generate/script').length,1);results.push({test:'unknown POST outcome does not resubmit on refresh',passed:true});await unknown.ctx.close();

 const accounts=await context();currentPage=accounts.page;await controls(accounts.page,{});await pick(accounts.page);const second=await accounts.ctx.newPage();await second.goto(base+'/account');await second.evaluate(()=>{localStorage.setItem('pd_web_token','qa-other');localStorage.setItem('pd_web_user',JSON.stringify({user_id:'qa-other',nickname:'Other QA'}));});await accounts.page.bringToFront();await expect(accounts.page.locator('.file-strip')).toHaveCount(0);await accounts.page.reload();await expect(accounts.page.locator('.file-strip')).toHaveCount(0);results.push({test:'cross-tab account switch clears previous private draft',passed:true});
 for(const minutes of [0,30,90]){
  await accounts.page.route('**/studio-api/auth/wallet?*',async route=>{const response=await route.fetch();const data=await response.json();data.account.minutes=minutes;await route.fulfill({response,json:data});});
  await accounts.page.goto(base+'/account');await expect(accounts.page.locator('.wallet-balance.time strong')).toHaveText((minutes/60)+'h');await accounts.page.unroute('**/studio-api/auth/wallet?*');
 }results.push({test:'wallet decimal hours 0, 0.5, 1.5',passed:true});await accounts.ctx.close();

 const admin=await context('zh');currentPage=admin.page;const seed=await (await admin.page.request.post(base+'/qa/timetable-seed')).json();await admin.page.addInitScript(()=>sessionStorage.setItem('puppy-studio-admin','qa-admin'));await admin.page.goto(base+'/manage');await admin.page.getByRole('button',{name:'预约管理',exact:true}).click();await expect(admin.page.locator('.timetable-grid')).toBeVisible();
 const slot=admin.page.locator('.timetable-slot').filter({hasText:'待确认 2'}).first();await expect(slot).toContainText('1');await expect(slot).toContainText('3');await slot.click();await expect(admin.page.locator('input[type=date]').first()).toHaveValue(seed.date);await admin.page.screenshot({path:path.join(out,'admin-timetable.png'),fullPage:true});
 for(const width of [390,768,1440]){await admin.page.setViewportSize({width,height:950});const metrics=await admin.page.evaluate(()=>({width:innerWidth,scroll:document.documentElement.scrollWidth}));assert(metrics.scroll<=metrics.width+1);}
 results.push({test:'admin occupancy states, click filters date and responsive timetable',passed:true});await admin.ctx.close();
 assert.deepEqual(errors,[]);
}catch(error){await currentPage?.screenshot({path:path.join(out,'native-error.png'),fullPage:true}).catch(()=>{});await fs.writeFile(path.join(out,'native-error.txt'),String(error));throw error;}
finally{await fs.writeFile(path.join(out,'native-verification.json'),JSON.stringify({fixture:'isolated loopback, synthetic AI, no production writes',results,errors},null,2));await browser.close();}
console.log(JSON.stringify({passed:results.length,errors},null,2));
