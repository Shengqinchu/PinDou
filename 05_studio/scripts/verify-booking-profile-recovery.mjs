import {chromium,expect} from '@playwright/test';
import fs from 'node:fs/promises';import assert from 'node:assert/strict';
const base=process.env.PINDOU_QA_ORIGIN||'http://127.0.0.1:19686';
if(!base.startsWith('http://127.0.0.1:'))throw new Error('Local QA only');
const owner='qa-email-profile-recovery-'+Date.now(),checks=[],errors=[],writes=[];
const browser=await chromium.launch({headless:true});
try{
 const ctx=await browser.newContext({viewport:{width:390,height:844}});await ctx.addInitScript(owner=>localStorage.setItem('pd_web_token',owner),owner);
 const page=await ctx.newPage();page.on('pageerror',e=>errors.push(e.message));page.on('request',r=>{if(r.method()!=='GET')writes.push(r.url());});
 // A verified account without a nickname must still be able to save booking details.
 await page.route('**/studio-api/auth/me',r=>r.fulfill({json:{user:{id:owner,email:owner+'@example.test',nickname:'',avatar:''}}}));
 await page.goto(base+'/account');await page.locator('.account-edit').click();
 const form=page.locator('.profile-form'),name=form.locator('.profile-contact input[autocomplete=name]'),contact=form.locator('.profile-contact .visit-contact-value input'),save=form.locator('.profile-actions .button-primary');
 await expect(name).toBeVisible();await expect(form.locator('input[autocomplete=nickname]')).toHaveValue('');await name.fill('No nickname needed');await contact.fill('qa-recovery-contact');
 let attempts=0;await page.route('**/studio-api/auth/booking-profile',async r=>{if(r.request().method()!=='PUT')return r.continue();attempts++;if(attempts===1){await r.fetch();await r.abort('failed');}else await r.continue();});
 await save.click();await expect(form.locator('.form-error')).toBeVisible();await expect(name).toHaveValue('No nickname needed');await save.click();await expect(form).toBeHidden();
 let current=await (await page.request.get(base+'/studio-api/auth/booking-profile',{headers:{Authorization:'Bearer '+owner}})).json();assert.equal(current.version,1);assert.equal(current.name,'No nickname needed');
 assert(!writes.some(url=>url.endsWith('/api/v1/user/profile')));await page.unroute('**/studio-api/auth/booking-profile');
 checks.push('Booking details can be saved without setting a nickname; a lost response keeps inputs and retry saves only one version');
 await page.locator('.account-edit').click();await expect(name).toHaveValue('No nickname needed');await name.fill('Unsaved local edit');
 const remote=await page.request.put(base+'/studio-api/auth/booking-profile',{headers:{Authorization:'Bearer '+owner},data:{name:'Changed elsewhere',contact_method:'wechat',contact:'qa-recovery-contact',version:1}});assert.equal(remote.status(),200);
 await save.click();await expect(form.locator('.form-error')).toContainText('其他窗口');await expect(name).toHaveValue('Unsaved local edit');
 await form.getByRole('button',{name:'使用最新资料',exact:true}).click();await expect(name).toHaveValue('Changed elsewhere');await name.fill('Reviewed local edit');await save.click();await expect(form).toBeHidden();
 current=await (await page.request.get(base+'/studio-api/auth/booking-profile',{headers:{Authorization:'Bearer '+owner}})).json();assert.equal(current.version,3);assert.equal(current.name,'Reviewed local edit');
 checks.push('Conflicts preserve local edits; explicitly loading latest details allows review and a successful next save');
 await page.goto(base+'/visit?step=1');await page.locator('.visit-plans input[value=hourly]').check();await page.locator('.visit-actions .button-primary').click();await expect(page.locator('.visit-step-enter-active,.visit-step-leave-active')).toHaveCount(0);await page.locator('.reservation-grid button:not(:disabled)').first().click();await page.locator('.visit-actions .button-primary').click();await expect(page.locator('.visit-saved-contact')).toContainText('Reviewed local edit');
 assert.equal((await page.request.put(base+'/studio-api/auth/booking-profile',{headers:{Authorization:'Bearer '+owner},data:{name:'Changed before booking',contact_method:'wechat',contact:'qa-recovery-contact',version:3}})).status(),200);
 const conflict=page.waitForResponse(r=>r.request().method()==='POST'&&r.url().endsWith('/studio-api/reservations'));await page.locator('.visit-actions .button-primary').click();assert.equal((await conflict).status(),409);await expect(page.locator('.visit-feedback')).toContainText('其他窗口');await expect(page.locator('.visit-saved-contact')).toContainText('Changed before booking');
 let records=(await (await page.request.get(base+'/studio-api/manage/reservations')).json()).items.filter(r=>r.owner_id===owner);assert.equal(records.length,0);
 await page.locator('.visit-actions .button-primary').click();await expect(page).toHaveURL(/\/reservation\/VIS-/);records=(await (await page.request.get(base+'/studio-api/manage/reservations')).json()).items.filter(r=>r.owner_id===owner);assert.equal(records.length,1);assert.equal(records[0].name,'Changed before booking');
 checks.push('A changed saved contact is not silently substituted during submission: conflict first, review updated summary, then submit one booking');
 assert.deepEqual(errors,[]);await ctx.close();
}finally{await browser.close();await fs.writeFile(new URL('../../artifacts/booking-profile/recovery.json',import.meta.url),JSON.stringify({checks,errors},null,2));}
console.log(JSON.stringify({checks,errors},null,2));
