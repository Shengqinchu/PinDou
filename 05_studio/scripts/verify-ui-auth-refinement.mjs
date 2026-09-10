import {chromium,webkit,expect} from '@playwright/test';
import AxeBuilder from '@axe-core/playwright';
import fs from 'node:fs/promises';
import assert from 'node:assert/strict';
import {fileURLToPath} from 'node:url';
const base=process.env.PINDOU_QA_ORIGIN||'http://127.0.0.1:19680';
const out=new URL('../../artifacts/ui-auth-refinement/',import.meta.url);await fs.mkdir(out,{recursive:true});
const measurements=[],checks=[],errors=[],axes=[];let page;
const settle=async()=>{await expect(page.locator('.visit-step-enter-active,.picker-swap-enter-active,.picker-swap-leave-active')).toHaveCount(0);await page.evaluate(()=>document.fonts.ready);};
const shot=async name=>{await settle();await page.waitForTimeout(750);await page.screenshot({path:fileURLToPath(new URL(name+'.png',out)),fullPage:true});};
async function measure(label){
 await settle();const m=await page.evaluate(()=>{const s=document.querySelector('.visit-scroll'),a=document.querySelector('.visit-actions'),f=document.querySelector('.visit-flow-page');return {width:innerWidth,height:innerHeight,bodyWidth:document.documentElement.scrollWidth,bodyHeight:document.documentElement.scrollHeight,form:f.clientWidth,content:s.scrollHeight,visible:s.clientHeight,actionBottom:a.getBoundingClientRect().bottom};});
 measurements.push({label,...m});assert(m.bodyWidth<=m.width+1,label+' horizontal overflow');assert(m.bodyHeight<=m.height+1,label+' document height');assert(m.actionBottom<=m.height+1,label+' hidden actions');
}
async function toContact(){await page.locator('.visit-duo-offer').click();await page.locator('.visit-dates button:not(:disabled)').first().click();await page.locator('.visit-times button').first().click();await page.locator('.visit-actions .button-primary').click();await expect(page.locator('.visit-contact')).toBeVisible();await settle();}
async function fakeQr(){
 let state='qr_pending',starts=0,polls=0;const flow='a'.repeat(43);
 await page.route('**/studio-api/auth/options',r=>r.fulfill({json:{wechat:true,password:true,email:false,recovery:true}}));
 await page.route('**/studio-api/auth/wechat/qr/start',r=>{starts++;return r.fulfill({json:{state:flow,image:base+'/qa/pattern.png',expires_in:120}});});
 await page.route('**/studio-api/auth/wechat/qr/poll',r=>{polls++;assert.deepEqual(r.request().postDataJSON(),{state:flow});return r.fulfill({json:{status:state,error:state==='failed'?'wechat_flow_expired':''}});});
 return {set:value=>state=value,counts:()=>({starts,polls}),flow};
}
const browser=await chromium.launch({headless:true,ignoreDefaultArgs:['--hide-scrollbars']});
try{
 let ctx=await browser.newContext({viewport:{width:1920,height:1080},locale:'zh-CN'});page=await ctx.newPage();page.on('pageerror',e=>errors.push(e.message));
 if(!process.env.PINDOU_QA_SKIP_LAYOUT)for(const lang of ['zh','en']){
  await page.goto(base+'/visit');if(!(await page.locator('html').getAttribute('lang')).startsWith(lang))await page.locator('.language-button').first().click();
  for(const size of [[1920,1080],[2560,1440],[3440,1440],[3840,2160],[1440,900],[1280,720],[1024,768],[768,1024],[390,844],[375,667],[320,568],[844,390],[960,540]]){
   await page.setViewportSize({width:size[0],height:size[1]});await page.goto(base+'/visit?step=1');await expect(page.locator('.visit-duo-offer')).toBeEnabled();await measure(lang+' experience');
   if([1920,3840,390].includes(size[0]))await shot(`${lang}-${size[0]}-experience`);
   await toContact();await measure(lang+' contact');await page.locator('.visit-notes summary').click();await page.locator('.visit-notes textarea').fill('Local multiline notes\nKept after resizing.');await page.locator('.visit-notes textarea').focus();await measure(lang+' expanded notes');
   const ring=await page.locator('.visit-notes textarea').evaluate(e=>({offset:parseFloat(getComputedStyle(e).outlineOffset),width:parseFloat(getComputedStyle(e).outlineWidth),box:e.getBoundingClientRect().toJSON(),clip:document.querySelector('.visit-scroll').getBoundingClientRect().toJSON()}));
   assert(ring.offset<=0);assert(ring.box.left>=ring.clip.left+3&&ring.box.right<=ring.clip.right-3);
   if([1920,390].includes(size[0]))await shot(`${lang}-${size[0]}-notes`);
  }
 }
 if(!process.env.PINDOU_QA_SKIP_LAYOUT)checks.push('78 layout states: 320 px to 4K, ultrawide, landscape and short windows in Chinese/English; visible actions and contained focus rings');
 await page.setViewportSize({width:1920,height:1080});await page.goto(base+'/visit?step=1&motion=full');await expect(page.locator('.visit-duo-offer')).toBeEnabled();
 await page.route('**/studio-api/reservation-calendar?*',async r=>{await new Promise(resolve=>setTimeout(resolve,450));await r.continue();});
 await page.evaluate(()=>{window.qrUiSamples=[];const el=document.querySelector('.visit-duo-offer');let start=performance.now();function sample(){window.qrUiSamples.push({opacity:getComputedStyle(el).opacity,disabled:el.disabled,connected:el.isConnected});if(performance.now()-start<2800)requestAnimationFrame(sample);}sample();});
 await page.locator('.visit-guests button').nth(1).click();await page.locator('.visit-guests button').nth(2).click();await page.evaluate(()=>{window.dispatchEvent(new Event('focus'));document.dispatchEvent(new Event('visibilitychange'));});await page.waitForTimeout(2900);
 const samples=await page.evaluate(()=>window.qrUiSamples);assert(samples.length>30);assert(samples.every(s=>s.opacity==='1'&&!s.disabled&&s.connected));await page.unroute('**/studio-api/reservation-calendar?*');
 checks.push(`${samples.length} consecutive frames: duo offer stays mounted and fully opaque through guest changes and focus/visibility refresh`);
 const guest=page.locator('.visit-guests button').first();await guest.hover();await page.waitForTimeout(350);assert.notEqual(await guest.evaluate(e=>getComputedStyle(e).transform),'matrix(1, 0, 0, 1, 0, 0)');await guest.click();assert(await guest.evaluate(e=>e.getAnimations().some(a=>a.id==='studio-press-feedback')));
 await page.goto(base+'/?motion=full');await page.waitForTimeout(1600);for(const selector of ['.hero-puppy','.vision-welcome .puppy-motif']){const root=page.locator(selector).first();await root.click();await expect.poll(()=>root.locator('.motif-touch').evaluate(e=>getComputedStyle(e).transform)).not.toBe('none');}
 for(const route of ['/?motion=full','/details?motion=full','/shop?motion=full','/visit?step=1&motion=full','/account?motion=full']){
  await page.goto(base+route);await page.waitForTimeout(1400);const title=page.locator('main .lift-title').first(),hit=title.locator('.lift-hit').first();await hit.hover();await page.waitForTimeout(850);let y=await hit.locator('.lift-glyph').evaluate(e=>new DOMMatrix(getComputedStyle(e).transform).m42);assert(y<-3,route);await page.waitForTimeout(400);assert.equal(await hit.locator('.lift-glyph').evaluate(e=>new DOMMatrix(getComputedStyle(e).transform).m42),y);await page.mouse.move(5,5);await page.waitForTimeout(550);assert(Math.abs(await hit.locator('.lift-glyph').evaluate(e=>new DOMMatrix(getComputedStyle(e).transform).m42))<.1);
 }
 checks.push('Guest controls have hover and tap rebound; puppy/stars squeeze; public title glyphs lift independently, hold and return');
 await ctx.close();
 ctx=await browser.newContext({viewport:{width:1440,height:900},locale:'zh-CN'});page=await ctx.newPage();page.on('pageerror',e=>errors.push(e.message));const qr=await fakeQr();
 await page.goto(base+'/visit?step=1');await toContact();await page.locator('.visit-contact input[autocomplete=name]').fill('Local guest');await page.locator('.visit-contact-value input').fill('local-contact');await page.locator('.account-trigger').click();await expect(page.locator('dialog[open]')).toBeVisible();await expect(page.locator('.wechat-qr-window img')).toBeVisible();const url=page.url();await shot('wechat-dialog');
 assert.equal(ctx.pages().length,1);await expect(page.locator('.account-content')).not.toContainText('与拼豆图纸工具共用账号');await expect(page.locator('.account-content')).not.toContainText('用手机微信扫描');await expect(page.locator('.account-form')).toHaveCount(0);
 qr.set('qr_scanned');await expect(page.locator('.wechat-qr-title')).toContainText('请在微信中确认');qr.set('failed');await expect(page.locator('.wechat-qr-title')).toContainText('刷新二维码');await page.locator('.wechat-qr-placeholder button').click();qr.set('qr_pending');await expect(page.locator('.wechat-qr-window img')).toBeVisible();
 await page.locator('.auth-method-choice').filter({hasText:'密码登录'}).click();const count=qr.counts().polls;await page.waitForTimeout(2100);assert.equal(qr.counts().polls,count);
 await page.locator('.account-recovery-link').click();await page.locator('.account-form input[type=email]').fill('fixture@example.test');
 let sends=0;await page.route('**/studio-api/auth/recovery/send-code',r=>{sends++;return r.fulfill({json:{success:true,cooldown_seconds:60}});});await page.route('**/studio-api/auth/recovery/reset-password',r=>r.fulfill({json:{success:true}}));
 await page.locator('.account-code-field button').click();await expect(page.locator('.account-code-field button')).toBeDisabled();assert.equal(sends,1);
 await page.locator('.account-code-field input').fill('123456');await page.locator('.account-password input').fill('new-password');await page.locator('.account-form input[autocomplete=new-password]').last().fill('different');await expect(page.locator('.account-form .button-primary')).toBeDisabled();await page.locator('.account-form input[autocomplete=new-password]').last().fill('new-password');await shot('recovery-dialog');await page.locator('.account-form .button-primary').click();await expect(page.locator('.account-note')).toContainText('密码已重设');assert.equal(await page.evaluate(()=>localStorage.getItem('pd_web_token')),null);
 await page.keyboard.press('Escape');await expect(page.locator('dialog[open]')).toHaveCount(0);await expect(page.locator('.visit-contact input[autocomplete=name]')).toHaveValue('Local guest');assert.equal(page.url(),url);assert.equal(ctx.pages().length,1);
 checks.push('Same-page QR, scan/expiry/retry states, switching stops polling; recovery only sends on request, enforces cooldown and confirmation; recovery does not sign in; closing preserves booking');
 await page.locator('.account-trigger').click();await page.locator('.auth-method-choice').filter({hasText:'微信'}).click();qr.set('needs_email');await expect(page.getByRole('button',{name:'绑定已有账号',exact:true})).toBeVisible();
 let bound=false;await page.route('**/studio-api/auth/wechat/bind',async r=>{assert(r.request().headers().authorization.startsWith('Bearer qa-email-'));assert.equal(r.request().postDataJSON().state,qr.flow);assert.equal(await page.evaluate(()=>localStorage.getItem('pd_web_token')),null);bound=true;await r.fulfill({json:{status:'linked'}});});
 await page.getByRole('button',{name:'绑定已有账号',exact:true}).click();await page.locator('.account-form input[type=email]').fill('fixture@example.test');await page.locator('.account-password input').fill('local-password');await page.locator('.account-form .button-primary').click();await expect(page.locator('.account-identity')).toBeVisible();assert(bound);assert.equal(page.url(),url);await ctx.close();
 checks.push('Existing-account password proof is bound to the verified QR before publishing a shared login session');
 ctx=await browser.newContext({viewport:{width:390,height:844},locale:'en-CA'});page=await ctx.newPage();page.on('pageerror',e=>errors.push(e.message));await fakeQr();await page.goto(base+'/account');await expect(page.locator('.wechat-qr-window img')).toBeVisible();await shot('en-mobile-wechat');
 let violations=(await new AxeBuilder({page}).include('.account-page').analyze()).violations;axes.push({page:'account',violations});assert.deepEqual(violations,[]);await page.locator('.auth-method-choice').filter({hasText:'Password'}).click();await page.locator('.account-recovery-link').click();await shot('en-mobile-recovery');violations=(await new AxeBuilder({page}).include('.account-page').analyze()).violations;axes.push({page:'recovery',violations});assert.deepEqual(violations,[]);
 await page.emulateMedia({reducedMotion:'reduce'});await page.goto(base+'/?motion=system');await expect(page.locator('html')).toHaveAttribute('data-motion','reduced');await page.locator('.hero-puppy').click();assert(['none','matrix(1, 0, 0, 1, 0, 0)'].includes(await page.locator('.hero-puppy .motif-touch').evaluate(e=>getComputedStyle(e).transform)));await ctx.close();
 checks.push('English mobile auth/recovery have no axe violations; reduced motion disables decorative movement');assert.deepEqual(errors,[]);
}catch(e){if(page&&!page.isClosed())await shot('failure');throw e;}finally{await browser.close();await fs.writeFile(new URL('verification.json',out),JSON.stringify({checks,measurements,errors,axes},null,2));}
const safari=await webkit.launch({headless:true});
try{for(const [width,height] of [[390,844],[844,390],[1920,1080]]){const ctx=await safari.newContext({viewport:{width,height},locale:'zh-CN',hasTouch:width<1000});page=await ctx.newPage();await page.goto(base+'/visit');await toContact();await page.locator('.visit-notes summary').click();await page.locator('.visit-notes textarea').fill('WebKit local notes');await measure('webkit contact');await ctx.close();}}finally{await safari.close();await fs.writeFile(new URL('verification.json',out),JSON.stringify({checks,measurements,errors,axes},null,2));}
console.log(JSON.stringify({checks,layouts:measurements.length,errors},null,2));
