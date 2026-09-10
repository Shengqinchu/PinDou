import {chromium,webkit,expect} from '@playwright/test';
import AxeBuilder from '@axe-core/playwright';
import fs from 'node:fs/promises';
import assert from 'node:assert/strict';
import {fileURLToPath} from 'node:url';
const base=process.env.PINDOU_QA_ORIGIN||'http://127.0.0.1:19682';
if(!base.startsWith('http://127.0.0.1:'))throw new Error('Local isolated account QA only');
const out=new URL('../../artifacts/auth-tabs/',import.meta.url);await fs.mkdir(out,{recursive:true});
const checks=[],layouts=[],errors=[];let page;
const browser=await chromium.launch({headless:true,ignoreDefaultArgs:['--hide-scrollbars']});
async function qrFixture(page){
 const counts={starts:0,polls:0,mail:0};
 await page.route('**/studio-api/auth/options',r=>r.fulfill({json:{wechat:true,password:true,email:false,recovery:true}}));
 await page.route('**/studio-api/auth/wechat/qr/start',async r=>{counts.starts++;await r.fulfill({json:{state:'a'.repeat(43),image:base+'/qa/pattern.png',expires_in:120}});});
 await page.route('**/studio-api/auth/wechat/qr/poll',r=>{counts.polls++;return r.fulfill({json:{status:'qr_pending'}});});
 page.on('request',r=>{if(/send-code|email\/verify|code-login/.test(r.url()))counts.mail++;});
 return counts;
}
async function measure(label){
 const data=await page.evaluate(()=>({width:innerWidth,body:document.documentElement.scrollWidth,buttons:[...document.querySelectorAll('.auth-methods button')].map(e=>({client:e.clientWidth,scroll:e.scrollWidth,height:e.getBoundingClientRect().height,left:e.getBoundingClientRect().left,right:e.getBoundingClientRect().right}))}));
 assert(data.body<=data.width+1,label);assert(data.buttons.every(b=>b.scroll<=b.client+1&&b.left>=0&&b.right<=data.width&&b.height>=44),label);layouts.push({label,...data});
}
try{
 for(const lang of ['zh-CN','en-CA']){
  const ctx=await browser.newContext({viewport:{width:1440,height:900},locale:lang});page=await ctx.newPage();page.on('pageerror',e=>errors.push(e.message));const counts=await qrFixture(page);
  await page.goto(base+'/account');const tabs=page.locator('.auth-methods [role=tab]');
  await expect(tabs).toHaveText(lang==='zh-CN'?['注册','登录','微信登录']:['Register','Sign in','WeChat']);await expect(tabs.nth(1)).toHaveAttribute('aria-selected','true');await expect(page.locator('.account-form')).toBeVisible();assert.equal(counts.starts,0);
  for(const size of [[1440,900],[2560,1440],[768,1024],[390,844],[375,667],[320,568],[844,390]]){
   await page.setViewportSize({width:size[0],height:size[1]});
   for(const mode of [1,0,2]){await tabs.nth(mode).click();await measure(`${lang} ${size.join('x')} ${mode}`);}
  }
  await tabs.nth(1).click();const stopped=counts.polls;await page.waitForTimeout(2100);assert.equal(counts.polls,stopped);assert.equal(counts.mail,0);
  await page.setViewportSize({width:390,height:844});await tabs.nth(0).click();await page.screenshot({path:fileURLToPath(new URL(lang+'-register.png',out)),fullPage:true});
  assert.deepEqual((await new AxeBuilder({page}).include('.account-page').analyze()).violations,[]);
  await tabs.nth(1).focus();await page.keyboard.press('Home');await expect(tabs.nth(0)).toBeFocused();await expect(tabs.nth(0)).toHaveAttribute('aria-selected','true');await page.keyboard.press('ArrowRight');await expect(tabs.nth(1)).toBeFocused();
  await ctx.close();
 }
 checks.push('42 bilingual layout states; tab order, 44px targets, keyboard navigation, zero default QR or mail requests, no registration accessibility violations');
 const ctx=await browser.newContext({viewport:{width:1440,height:900},locale:'zh-CN'});page=await ctx.newPage();page.on('pageerror',e=>errors.push(e.message));const counts=await qrFixture(page);
 await page.goto(base+'/visit?step=1');await page.locator('.visit-duo-offer').click();await page.locator('.visit-dates button:not(:disabled)').first().click();await page.locator('.visit-times button').first().click();await page.locator('.visit-actions .button-primary').click();await page.locator('.visit-contact input[autocomplete=name]').fill('Local auth test');await page.locator('.visit-contact-value input').fill('local-contact');
 await page.locator('.account-trigger').click();const tabs=page.locator('dialog[open] .auth-methods [role=tab]');await expect(tabs.nth(1)).toHaveAttribute('aria-selected','true');assert.equal(counts.starts,0);
 await tabs.nth(2).click();await expect(page.locator('.wechat-qr-window img')).toBeVisible();await expect.poll(()=>counts.starts).toBe(1);await page.keyboard.press('Escape');await expect(page.locator('dialog[open]')).toHaveCount(0);const stopped=counts.polls;await page.waitForTimeout(2100);assert.equal(counts.polls,stopped);
 await page.locator('.account-trigger').click();await expect(tabs.nth(1)).toHaveAttribute('aria-selected','true');await expect(page.locator('.wechat-qr')).toHaveCount(0);assert.equal(counts.starts,1);await page.screenshot({path:fileURLToPath(new URL('default-password-dialog.png',out)),fullPage:true});assert.deepEqual((await new AxeBuilder({page}).include('dialog[open]').analyze()).violations,[]);
 checks.push('Opening, closing after WeChat, and reopening keeps the current page and returns to password login without a second QR request');
 await tabs.nth(0).click();const email=`auth-tabs-${Date.now()}@example.test`,password='local-password';
 await page.locator('.account-form input[type=email]').fill(email);await page.locator('.account-password input').fill(password);await page.locator('.account-form input[autocomplete=new-password]').last().fill('wrong-password');await expect(page.locator('.account-form .button-primary')).toBeDisabled();await page.locator('.account-form input[autocomplete=new-password]').last().fill(password);await page.locator('.account-form .button-primary').click();
 await expect(page.locator('.account-identity')).toBeVisible();await expect(page.locator('.wallet-balance.points strong')).toHaveText('166');assert.equal(counts.mail,0);assert.equal(ctx.pages().length,1);
 const token=await page.evaluate(()=>localStorage.getItem('pd_web_token'));
 const profile=await page.request.get('http://127.0.0.1:19683/api/v1/user/profile',{headers:{Authorization:'Bearer '+token}});assert.equal(profile.status(),200);assert.equal((await profile.json()).email,email);
 await page.keyboard.press('Escape');await expect(page.locator('.visit-contact input[autocomplete=name]')).toHaveValue('Local auth test');await expect(page.locator('.visit-contact-value input')).toHaveValue('local-contact');
 await page.locator('.account-trigger').click();await page.locator('.account-signout').click();await page.locator('.account-trigger').click();await tabs.nth(0).click();await page.locator('.account-form input[type=email]').fill(email);await page.locator('.account-password input').fill('replacement-password');await page.locator('.account-form input[autocomplete=new-password]').last().fill('replacement-password');await page.locator('.account-form .button-primary').click();await expect(page.locator('.account-form .form-error')).toContainText('已注册');
 await tabs.nth(1).click();await page.locator('.account-password input').fill(password);await page.locator('.account-form .button-primary').click();await expect(page.locator('.wallet-balance.points strong')).toHaveText('166');assert.equal(counts.mail,0);
 checks.push('Real local Studio-to-pinned-generator HTTP signup and password re-login; duplicate email cannot replace the password; 166 points exactly once; shared generator JWT works; booking draft retained; zero emails');
 await ctx.close();assert.deepEqual(errors,[]);
}catch(e){if(page&&!page.isClosed())await page.screenshot({path:fileURLToPath(new URL('failure.png',out)),fullPage:true});throw e;}
finally{await browser.close();await fs.writeFile(new URL('verification.json',out),JSON.stringify({checks,layouts,errors},null,2));}
const safari=await webkit.launch({headless:true});
try{
 const ctx=await safari.newContext({viewport:{width:375,height:667},locale:'en-CA',isMobile:true,hasTouch:true});page=await ctx.newPage();const counts=await qrFixture(page);await page.goto(base+'/');await page.locator('.account-trigger').click();const tabs=page.locator('dialog[open] [role=tab]');await expect(tabs.nth(1)).toHaveAttribute('aria-selected','true');assert.equal(counts.starts,0);await tabs.nth(0).click();await measure('WebKit mobile registration');await page.locator('.account-form input[type=email]').fill('webkit@example.test');await page.locator('.account-password input').focus();await measure('WebKit mobile input focus');await page.screenshot({path:fileURLToPath(new URL('webkit-register.png',out)),fullPage:true});await ctx.close();checks.push('Mobile WebKit default password, registration, input focus and no QR preloading');
}finally{await safari.close();await fs.writeFile(new URL('verification.json',out),JSON.stringify({checks,layouts,errors},null,2));}
console.log(JSON.stringify({checks,layouts:layouts.length,errors},null,2));
