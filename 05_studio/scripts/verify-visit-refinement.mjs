import {chromium,expect} from '@playwright/test';
import AxeBuilder from '@axe-core/playwright';
import fs from 'node:fs/promises';
import assert from 'node:assert/strict';
import {fileURLToPath} from 'node:url';
const out=new URL('../../artifacts/visit-flow-v2/',import.meta.url),base='http://127.0.0.1:19678',prototype='http://127.0.0.1:19679/prototype.html';
await fs.mkdir(out,{recursive:true});
const browser=await chromium.launch({headless:true,ignoreDefaultArgs:['--hide-scrollbars']}),checks=[],errors=[],axeResults=[];
let page;const save=async name=>page.screenshot({path:fileURLToPath(new URL(name+'.png',out)),fullPage:true});
const settle=async()=>{await expect(page.locator('.flow-stage')).toHaveCSS('opacity','1');await expect(page.locator('.flow-page-enter-active,.flow-page-leave-active,.picker-swap-enter-active,.picker-swap-leave-active')).toHaveCount(0);};
const noOverflow=async label=>assert(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth+1),label);
const accessible=async selector=>{const results=await new AxeBuilder({page}).include(selector).analyze();axeResults.push({selector,url:page.url(),violations:results.violations.map(v=>({id:v.id,nodes:v.nodes.map(n=>({target:n.target,summary:n.failureSummary}))}))});assert.deepEqual(axeResults.at(-1).violations,[]);};
const y=locator=>locator.evaluate(e=>new DOMMatrix(getComputedStyle(e).transform).m42);
try{
 const ctx=await browser.newContext({viewport:{width:1440,height:1000},locale:'zh-CN',reducedMotion:'no-preference'});page=await ctx.newPage();page.setDefaultTimeout(15000);page.on('pageerror',e=>errors.push(e.message));
 await page.goto(base+'/');await expect(page.locator('.vision-title')).toBeVisible();
 await expect.poll(()=>page.locator('.vision-title>.lift-line').first().evaluate(e=>getComputedStyle(e).transform)).toBe('none');
 const hits=page.locator('.vision-title .lift-hit'),glyph=hits.first().locator('.lift-glyph');const headingBox=await page.locator('.vision-title').boundingBox();
 await hits.first().hover();await expect.poll(()=>y(glyph),{intervals:[30]}).toBeLessThan(-.1);
 assert.equal(await glyph.evaluate(e=>e.getAnimations()[0]?.effect.getTiming().duration),620);
 await expect.poll(()=>glyph.evaluate(e=>e.getAnimations().length)).toBe(0);const held=await y(glyph);assert(held< -4);
 await page.waitForTimeout(850);assert.equal(await y(glyph),held);assert.equal(await y(hits.nth(4).locator('.lift-glyph')),0);
 assert.equal((await page.locator('.vision-title').boundingBox()).height,headingBox.height);await save('title-held');
 await page.mouse.move(0,0);await expect.poll(()=>y(glyph)).toBe(0);
 for(let i=0;i<4;i++){await hits.nth(1).hover();await hits.first().hover();assert(await glyph.evaluate(e=>e.getAnimations().length)<=1);}
 await page.emulateMedia({reducedMotion:'reduce'});await expect(page.locator('html')).toHaveAttribute('data-motion','reduced');assert.equal(await y(glyph),0);assert.equal(await glyph.evaluate(e=>e.getAnimations().length),0);
 await page.emulateMedia({reducedMotion:'no-preference'});await hits.nth(1).hover();await hits.first().hover();await page.evaluate(()=>window.dispatchEvent(new Event('blur')));assert.equal(await y(glyph),0);
 await page.locator('.vision-header-actions .language-button').click();assert.equal(await page.locator('.lift-glyph[style*=transform]').count(),0);await page.locator('.vision-header-actions .language-button').click();
 checks.push('Title: 620 ms rise, held beyond 1 second, independent letters, 500 ms return, rapid re-entry, blur/language/reduced-motion cleanup, fixed heading size');
 let prototypePosts=0;page.on('request',r=>{if(r.method()==='POST'&&r.url().includes('/reservations')&&page.url().includes('19679'))prototypePosts++;});
 await page.goto(prototype+'?motion=full');await expect(page.locator('.flow-duo-offer')).toBeEnabled();
 await page.locator('.flow-prepaid-details>summary').click();await save('desktop-experience');
 assert(!await page.locator('.flow-shell').innerText().then(t=>t.includes('仅作优惠说明')||t.includes('这次几个人一起来')));
 await page.locator('.flow-duo-offer').click();await expect(page.locator('.flow-dates')).toBeVisible();await settle();
 await expect(page.locator('.flow-inline-summary')).toContainText('2 人');await expect(page.locator('.flow-inline-summary')).toContainText('4h');
 await save('desktop-dates');
 await page.evaluate(()=>{window.__pickerFrames=[];const started=performance.now();function frame(){const p=document.querySelector('.flow-picker-window');window.__pickerFrames.push({ms:performance.now()-started,height:p.getBoundingClientRect().height,panes:p.querySelectorAll('.flow-picker-pane').length,opacity:getComputedStyle(p.querySelector('.flow-picker-pane')||p).opacity,view:p.querySelector('.flow-picker-pane')?.dataset.pickerView,overflow:document.documentElement.scrollWidth>innerWidth+1});if(performance.now()-started<1400)requestAnimationFrame(frame);}requestAnimationFrame(frame);});
 await page.locator('.flow-dates button:not(:disabled)').first().click();await expect(page.locator('.flow-times')).toBeVisible();await settle();await page.waitForTimeout(500);
 const frames=await page.evaluate(()=>window.__pickerFrames);await fs.writeFile(new URL('picker-transition.json',out),JSON.stringify(frames,null,2));
 assert(frames.every(f=>f.panes<=1&&!f.overflow));assert(frames.some(f=>f.view==='date'&&Number(f.opacity)<.8));assert(frames.some(f=>f.view==='time'&&Number(f.opacity)<.8));assert(Math.min(...frames.map(f=>f.height))>=Math.min(frames[0].height,frames.at(-1).height)-5);
 await expect(page.locator('.flow-dates')).toHaveCount(0);await expect(page.locator('.flow-duration')).toHaveCount(0);await expect(page.locator('.flow-fixed-duration')).toContainText('4 小时');await expect(page.locator('.flow-picker-pane')).toBeFocused();
 const chosenDate=await page.locator('.flow-picked-date>strong').innerText();
 await page.locator('.flow-times button').first().click();await expect(page.locator('.flow-chosen')).toContainText(/\d\d:\d\d–\d\d:\d\d/);
 const selection=await page.locator('.flow-chosen').innerText(),times=selection.match(/(\d\d):(\d\d)–(\d\d):(\d\d)/);assert.equal((+times[3]*60+ +times[4])-(+times[1]*60+ +times[2]),240);await save('desktop-times');
 await page.locator('.flow-change-date').click();await expect(page.locator('.flow-dates')).toBeVisible();await settle();await page.locator('.flow-dates button[aria-pressed=true]').click();await settle();await expect(page.locator('.flow-chosen')).toHaveText(selection);
 await page.locator('.flow-actions .button').click();await expect(page.locator('.flow-contact')).toBeVisible();await settle();
 await expect(page.locator('.flow-contact select,input[type=checkbox]')).toHaveCount(0);
 await page.getByRole('textbox',{name:'怎么称呼您~',exact:true}).fill('本地体验客人');
 const methods=page.locator('.contact-method-picker input[type=radio]');await methods.first().focus();await page.keyboard.press('ArrowRight');await expect(methods.nth(1)).toBeChecked();
 await page.getByRole('textbox',{name:'电子邮箱地址',exact:true}).fill('local@example.test');
 await page.keyboard.press('Tab');await save('desktop-contact');await accessible('.flow-shell');
 await page.locator('.flow-back').click();await settle();await expect(page.locator('.flow-chosen')).toHaveText(selection);await page.locator('.flow-actions .button').click();await settle();await expect(page.getByRole('textbox',{name:'怎么称呼您~',exact:true})).toHaveValue('本地体验客人');
 await page.locator('.prototype-bar button').click();await expect(page.getByRole('textbox',{name:'What should we call you?',exact:true})).toHaveValue('本地体验客人');await expect(page.locator('.contact-method-picker input[value=email]')).toBeChecked();
 await page.locator('.flow-actions .button').click();await expect(page.locator('.flow-chosen')).toContainText('Preview complete');assert.equal(prototypePosts,0);await accessible('.flow-shell');
 checks.push('Duo offer selects 2 guests / fixed 4 hours and advances; date fades out before time floats in, no stacked panes or collapsed frame; Back/date edit/contact/language retain fields; preview sends no booking');
 for(const width of [320,390,768,1440]){
  await page.setViewportSize({width,height:844});await page.goto(prototype);await expect(page.locator('.flow-duo-offer')).toBeEnabled();await page.locator('.flow-prepaid-details>summary').click();await noOverflow('step1 '+width);if(width===390)await save('mobile-experience');
  await page.locator('.flow-duo-offer').click();await expect(page.locator('.flow-dates')).toBeVisible();await settle();await noOverflow('dates '+width);if(width===390)await save('mobile-dates');
  await page.locator('.flow-dates button:not(:disabled)').first().click();await expect(page.locator('.flow-times')).toBeVisible();await settle();await noOverflow('times '+width);if(width===390)await save('mobile-times');
  await page.locator('.flow-times button').first().click();await page.locator('.flow-actions .button').click();await settle();await noOverflow('contact '+width);if(width===390){await save('mobile-contact');await accessible('.flow-shell');}
 }
 checks.push('All four prototype panels in English at 320 / 390 / 768 / 1440 px, mobile contact and date selection accessible');
 await page.setViewportSize({width:1440,height:1000});await page.goto(prototype);await page.locator('.flow-duo-offer').click();await settle();await page.locator('.flow-back').click();await settle();await page.locator('.flow-plans input[value=hourly]').check();await page.locator('.flow-guests button').nth(2).click();await expect(page.locator('.flow-duo-offer')).toBeEnabled();await page.locator('.flow-actions .button').click();await settle();
 await page.locator('.flow-dates button:not(:disabled)').first().click();await settle();await expect(page.locator('.flow-duration')).toBeVisible();await expect(page.locator('.flow-fixed-duration')).toHaveCount(0);await expect(page.locator('.flow-duration button').first()).toHaveAttribute('aria-pressed','true');
 await page.locator('.flow-duration button').nth(1).click();await page.locator('.flow-times button').first().click();const normal=await page.locator('.flow-chosen').innerText();const nt=normal.match(/(\d\d):(\d\d)–(\d\d):(\d\d)/);assert.equal((+nt[3]*60+ +nt[4])-(+nt[1]*60+ +nt[2]),150);
 await page.locator('.flow-change-date').click();await page.waitForTimeout(120);await page.setViewportSize({width:390,height:844});await settle();await noOverflow('resize during swap');await page.locator('.flow-dates button:not(:disabled)').nth(1).click();await settle();await expect(page.locator('.flow-chosen')).toHaveCount(0);
 await page.goto(prototype+'?motion=system');await page.emulateMedia({reducedMotion:'reduce'});await expect(page.locator('html')).toHaveAttribute('data-motion','reduced');await page.locator('.flow-duo-offer').click();await settle();await page.locator('.flow-dates button:not(:disabled)').first().click();await settle();assert.equal(await page.locator('.flow-picker-window').evaluate(e=>e.style.height),'');await page.locator('.flow-back').click();await settle();await expect(page.locator('.flow-dates')).toBeVisible();
 checks.push('Offer can be replaced by hourly / 3 guests / 2.5 h; changed date clears only time; resize mid-swap and reduced-motion Back work');
 await page.emulateMedia({reducedMotion:'no-preference'});
 const calendar=await (await page.request.get(base+'/studio-api/reservation-calendar?guests=2')).json();const good=calendar.days.find(d=>!d.closed&&d.slots.some(s=>s.available));
 await page.route('**/studio-api/reservation-calendar?*',route=>route.fulfill({json:{...calendar,today:'2026-10-01',days:[{...good,date:'2026-10-01'},{...good,date:'2026-10-02'}]}}));
 await page.goto(prototype);await page.locator('.flow-duo-offer').click();await settle();await expect(page.locator('.flow-dates button').nth(1)).toBeDisabled();await expect(page.locator('.flow-dates button').first()).toBeEnabled();await page.unroute('**/studio-api/reservation-calendar?*');checks.push('Duo dates respect the existing October 1 offer end; later date disabled');
 await ctx.close();
 const customer=await browser.newContext({viewport:{width:1440,height:1000},locale:'zh-CN'});await customer.addInitScript(()=>localStorage.setItem('pd_web_token','qa-owner'));page=await customer.newPage();page.on('pageerror',e=>errors.push(e.message));
 await page.goto(base+'/visit');await page.locator('.reservation-plans input[value=hourly]').check();await page.locator('.reservation-grid button:not(:disabled)').first().click();await expect(page.locator('.reservation-selection strong')).toContainText('–');
 await expect(page.locator('.reservation-contact-fields select,.reservation-form input[type=checkbox]')).toHaveCount(0);await page.getByRole('textbox',{name:/怎么称呼您~/}).fill('Local refinement');
 for(const method of ['phone','other','email','wechat']){await page.locator('.contact-method-picker label').filter({has:page.locator('input[value='+method+']')}).click();await expect(page.locator('.contact-method-picker input[value='+method+']')).toBeChecked();}
 await page.getByRole('textbox',{name:'微信号',exact:true}).fill('local-qa-contact');
 for(const width of [320,390,768,1440]){await page.setViewportSize({width,height:844});await noOverflow('real form '+width);const radios=await page.locator('.contact-method-picker input').evaluateAll(es=>es.map(e=>({w:e.offsetWidth,h:e.offsetHeight})));assert(radios.every(e=>e.w<=1&&e.h<=1));}
 await page.locator('.reservation-contact-fields').scrollIntoViewIfNeeded();await save('existing-visit-contact');await accessible('.reservation-guest');
 const posted=page.waitForRequest(r=>r.method()==='POST'&&r.url().endsWith('/studio-api/reservations'));await page.locator('.reservation-submit .button-primary').click();const payload=(await posted).postDataJSON();assert(!Object.hasOwn(payload,'consent'));await expect(page).toHaveURL(/\/reservation\/VIS-/);await save('local-booking-confirmed');
 checks.push('Existing /visit: four styled contact channels, polite name label, 4 widths, keyboard radios; local authenticated booking succeeds with no consent field or checkbox');
 assert.deepEqual(errors,[]);await customer.close();
}catch(error){if(page&&!page.isClosed())await save('verification-error');throw error;}finally{await browser.close();await fs.writeFile(new URL('verification.json',out),JSON.stringify({checks,errors,axeResults},null,2));}
console.log(JSON.stringify({checks,errors,axeChecks:axeResults.length},null,2));
