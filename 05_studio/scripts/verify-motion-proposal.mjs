import {chromium,expect} from '@playwright/test';
import fs from 'node:fs/promises';import assert from 'node:assert/strict';import {fileURLToPath} from 'node:url';
import AxeBuilder from '@axe-core/playwright';
const out=new URL(process.env.PINDOU_QA_OUTPUT||'../../artifacts/visit-flow/',import.meta.url),base='http://127.0.0.1:19678',prototype='http://127.0.0.1:19679/prototype.html';
await fs.mkdir(out,{recursive:true});
const browser=await chromium.launch({headless:true,ignoreDefaultArgs:['--hide-scrollbars']}),checks=[],errors=[];let page;
const capture=async(name)=>{if(page.url()===prototype)await expect.poll(()=>page.locator('.flow-stage').evaluate(e=>getComputedStyle(e).opacity)).toBe('1');return page.screenshot({path:fileURLToPath(new URL(name,out)),fullPage:true});};
try{
 const ctx=await browser.newContext({viewport:{width:1440,height:1000},locale:'zh-CN',reducedMotion:'no-preference'});page=await ctx.newPage();page.setDefaultTimeout(12000);page.on('pageerror',e=>errors.push(e.message));
 await page.goto(base+'/');await expect(page.locator('.vision-title')).toHaveAttribute('aria-label','属于你的 全新拼豆手作体验');
 await expect.poll(()=>page.locator('.vision-title>.lift-line').first().evaluate(e=>getComputedStyle(e).transform)).toBe('none');
 const hits=page.locator('.vision-title .lift-hit'),first=hits.first(),glyph=first.locator('.lift-glyph');const size=await page.locator('.vision-title').boundingBox();
 await first.hover();await expect.poll(()=>glyph.evaluate(e=>new DOMMatrix(getComputedStyle(e).transform).m42),{intervals:[25,25,25]}).toBeLessThan(-.3);
 assert.equal(await hits.nth(5).locator('.lift-glyph').evaluate(e=>new DOMMatrix(getComputedStyle(e).transform).m42),0);
 assert.equal((await page.locator('.vision-title').boundingBox()).height,size.height);await capture('title-lift.png');
 await expect.poll(()=>glyph.evaluate(e=>e.getAnimations().length)).toBe(0);
 for(let n=0;n<5;n++){await hits.nth(1).hover();await first.hover();}assert(await glyph.evaluate(e=>e.getAnimations().length)<=1);
 const copy=await page.locator('.vision-title').evaluate(e=>{const range=document.createRange();range.selectNodeContents(e);getSelection().removeAllRanges();getSelection().addRange(range);return getSelection().toString();});assert(copy.includes('属于你的')&&copy.includes('全新拼豆手作体验'));await page.mouse.move(0,0);
 await page.locator('.vision-header-actions .language-button').click();await expect(page.locator('.vision-title')).not.toHaveAttribute('aria-label',/属于/);assert((await page.locator('.vision-title').textContent()).includes('Make something lovely'));
 await page.locator('.vision-header-actions .language-button').click();
 checks.push('Independent letter lift, return, replace-on-reentry, unchanged heading box, copy and bilingual title');
 await page.goto(base+'/visit');await page.locator('.reservation-plans input[value=hourly]').check();
 const amounts=page.locator('.reservation-form .price-amount');await expect(amounts.first()).toHaveText('8.88 CAD');
 for(const item of await amounts.all()){const geo=await item.evaluate(e=>{const n=e.querySelector('.price-number'),c=e.querySelector('.price-currency'),nr=n.getBoundingClientRect(),cr=c.getBoundingClientRect();return {ns:parseFloat(getComputedStyle(n).fontSize),cs:parseFloat(getComputedStyle(c).fontSize),nx:nr.right,cx:cr.left,ny:nr.top,cy:cr.top};});assert(geo.cs<geo.ns*.6&&geo.cx>=geo.nx&&geo.cy>geo.ny);}
 await capture('price-cad.png');
 await page.goto(base+'/tools');await expect(page.locator('.mode-card')).toHaveCount(2);
 const standard=page.locator('.mode-card').last();await standard.hover();
 assert.equal(await standard.evaluate(e=>getComputedStyle(e).transitionDuration),'0.3s');
 await standard.click();assert(await standard.evaluate(e=>e.getAnimations().some(a=>a.id==='studio-press-feedback')));
 await expect(standard).toHaveAttribute('aria-pressed','true');await expect.poll(()=>standard.evaluate(e=>e.getAnimations().filter(a=>a.id==='studio-press-feedback').length)).toBe(0);
 await page.locator('.generator-allowance>button').click();await expect(page.locator('.sku-price .price-currency').first()).toHaveText('CNY');await capture('price-cny.png');await page.keyboard.press('Escape');
 await page.emulateMedia({reducedMotion:'reduce'});await expect(page.locator('html')).toHaveAttribute('data-motion','reduced');await standard.hover();assert.equal(await standard.evaluate(e=>getComputedStyle(e).transform),'none');
 await page.goto(base+'/');await page.locator('.vision-title .lift-hit').first().hover();assert.equal(await page.locator('.vision-title .lift-glyph').first().evaluate(e=>e.getAnimations().length),0);
 checks.push('CAD/CNY suffix geometry, generator 300ms feedback, immediate selection, reduced-motion cancellation');
 await page.emulateMedia({reducedMotion:'no-preference'});
 for(const width of [320,390,768,1024,1440,1920,2560]){
  await page.setViewportSize({width,height:900});for(const route of ['/','/visit','/tools']){await page.goto(base+route);await expect(page.locator('h1')).toBeVisible();assert(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth+1),`${route} overflow ${width}`);}
 }
 checks.push('Main headings, visit prices and generator at 7 widths including zoom reflow');
 await page.setViewportSize({width:1440,height:1000});await page.goto(prototype);await expect(page.locator('.flow-plans')).toBeVisible();await capture('prototype-step1.png');
 let bookingPosts=0;page.on('request',r=>{if(r.method()==='POST'&&r.url().includes('/reservations'))bookingPosts++;});
 await page.locator('.flow-plans input[value=hourly]').check();await page.locator('.flow-guests button').nth(1).click();
 await page.locator('.flow-actions .button').click();await expect(page.locator('.flow-dates')).toBeVisible();
 await page.locator('.flow-dates button:not(:disabled)').nth(1).click();await expect(page.locator('.flow-times button').first()).toBeVisible();await page.locator('.flow-times button').first().click();
 const selectedText=await page.locator('.flow-chosen').innerText();await capture('prototype-step2.png');
 await page.locator('.flow-actions .button').click();await expect(page.locator('.flow-contact')).toBeVisible();
 await page.locator('.flow-contact input').first().fill('Local guest');await page.locator('.flow-contact input').last().fill('local-wechat');await capture('prototype-step3.png');
 await page.locator('.flow-back').click();await expect(page.locator('.flow-chosen')).toHaveText(selectedText);await page.locator('.flow-actions .button').click();await expect(page.locator('.flow-contact input').first()).toHaveValue('Local guest');
 await page.locator('.flow-actions .button').click();await expect(page.locator('.flow-chosen')).toContainText('预览已走通');assert.equal(bookingPosts,0);
 await page.locator('.prototype-bar button').click();await expect(page.locator('h1')).toHaveText('Come make something');await expect(page.locator('.flow-contact input').first()).toHaveValue('Local guest');
 checks.push('Three-step prototype, progress, early validation, chosen time and contact survive Back/Next/language; submit is preview-only');
 await page.locator('.prototype-bar button').click();
 for(const width of [320,390,768,1440]){
  await page.setViewportSize({width,height:844});await page.locator('.flow-progress button').first().click();await expect(page.locator('.flow-plans')).toBeVisible();assert(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth+1));
  if(width===390)await capture('prototype-mobile-step1.png');await page.locator('.flow-progress button').nth(1).click();await expect(page.locator('.flow-times')).toBeVisible();assert(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth+1));if(width===390)await capture('prototype-mobile-step2.png');
 }
 await expect.poll(()=>page.locator('.flow-stage').evaluate(e=>getComputedStyle(e).opacity)).toBe('1');
 const axe=await new AxeBuilder({page}).include('.flow-shell').analyze();await fs.writeFile(new URL('prototype-accessibility.json',out),JSON.stringify(axe.violations.map(v=>({id:v.id,nodes:v.nodes.map(n=>({target:n.target,summary:n.failureSummary}))})),null,2));assert.deepEqual(axe.violations.map(v=>({id:v.id,nodes:v.nodes.length})),[]);
 checks.push('Prototype 4 widths, bilingual field retention and accessibility');assert.deepEqual(errors,[]);await ctx.close();
}catch(error){if(page)await capture('verification-error.png');throw error;}finally{await browser.close();await fs.writeFile(new URL('verification.json',out),JSON.stringify({checks,errors},null,2));}
console.log(JSON.stringify({checks,errors},null,2));
