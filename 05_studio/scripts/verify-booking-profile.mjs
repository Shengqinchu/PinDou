import {chromium,webkit,expect} from '@playwright/test';
import AxeBuilder from '@axe-core/playwright';
import fs from 'node:fs/promises';
import assert from 'node:assert/strict';
import {fileURLToPath} from 'node:url';
const base=process.env.PINDOU_QA_ORIGIN||'http://127.0.0.1:19685',out=new URL('../../artifacts/booking-profile/',import.meta.url);
if(!base.startsWith('http://127.0.0.1:'))throw new Error('Isolated QA database only');
await fs.mkdir(out,{recursive:true});
const errors=[],checks=[],measures=[];let page;
const browser=await chromium.launch({headless:true,ignoreDefaultArgs:['--hide-scrollbars']});
async function context(engine,owner,viewport={width:1440,height:1000}){
 const ctx=await engine.newContext({viewport,locale:'zh-CN'});
 await ctx.addInitScript(owner=>{if(!localStorage.getItem('qa-profile-seeded')){localStorage.setItem('pd_web_token',owner);localStorage.setItem('qa-profile-seeded','yes');}sessionStorage.setItem('puppy-studio-admin','qa-admin');},owner);
 page=await ctx.newPage();page.on('pageerror',e=>errors.push(e.message));return ctx;
}
async function settle(){await expect(page.locator('.visit-step-enter-active,.visit-step-leave-active')).toHaveCount(0);await page.evaluate(()=>document.fonts.ready);}
async function goContact(){
 await page.goto(base+'/visit?step=1');await page.locator('.visit-plans input[value=hourly]').check();await page.locator('.visit-actions .button-primary').click();
 await expect(page.locator('.reservation-grid')).toBeVisible();await settle();await page.locator('.reservation-grid button:not(:disabled)').first().click();
 await page.locator('.visit-actions .button-primary').click();await expect(page.locator('.visit-contact,.visit-saved-contact')).toBeVisible();await settle();
}
const name=()=>page.locator('.visit-contact input[autocomplete=name]');
const contact=()=>page.locator('.visit-contact-value input');
async function profile(owner='qa-owner'){return (await page.request.get(base+'/studio-api/auth/booking-profile',{headers:{Authorization:'Bearer '+owner}})).json();}
async function shot(label){await settle();await page.screenshot({path:fileURLToPath(new URL(label+'.png',out))});}
async function measure(label){
 await settle();await page.evaluate(()=>new Promise(resolve=>requestAnimationFrame(()=>requestAnimationFrame(resolve))));
 const result=await page.evaluate(()=>({width:innerWidth,height:innerHeight,body:document.documentElement.scrollWidth,footer:document.querySelector('.visit-actions')?.getBoundingClientRect().bottom}));
 measures.push({label,...result});assert(result.body<=result.width+1,label+' overflow');if(result.footer)assert(result.footer<=result.height+1,label+' hidden actions');
}
try{
 const ctx=await context(browser,'qa-owner');await goContact();
 await expect(name()).toHaveAttribute('required','');await expect(page.locator('.visit-returning-help')).toHaveCount(0);
 await name().fill('First booking name');await contact().fill('first-wechat');
 await page.locator('.visit-actions .button-primary').click();await expect(page).toHaveURL(/\/reservation\/VIS-/);const firstId=page.url().split('/').at(-1);
 let saved=await profile();assert.equal(saved.name,'First booking name');assert.equal(saved.contact,'first-wechat');assert.equal(saved.version,1);
 checks.push('First successful booking saves immediately while status is pending');
 await goContact();await expect(page.locator('.visit-saved-contact')).toContainText('first-wechat');await expect(name()).toHaveCount(0);await shot('returning-desktop');
 await page.locator('.visit-saved-contact button').click();await expect(name()).toBeFocused();await name().fill('Updated booking name');await page.locator('.contact-method-picker input[value=phone]').check();await contact().fill('+1 416 555 0123');
 await page.locator('.visit-back').click();await page.locator('.visit-actions .button-primary').click();await expect(name()).toHaveValue('Updated booking name');
 await page.reload();await expect(name()).toHaveValue('Updated booking name');await expect(contact()).toHaveValue('+1 416 555 0123');
 let submissions=0,original;await page.route('**/studio-api/reservations',async route=>{submissions++;if(submissions===1){original=route.request();await route.fetch();await route.abort('failed');}else await route.continue();});
 await page.locator('.visit-actions .button-primary').click();await expect(page.locator('.visit-feedback')).not.toBeEmpty();
 await page.reload();const next=page.waitForRequest(r=>r.method()==='POST'&&r.url().endsWith('/studio-api/reservations'));await page.locator('.visit-actions .button-primary').click();const replay=await next;
 assert.equal(replay.headers()['idempotency-key'],original.headers()['idempotency-key']);await expect(page).toHaveURL(/\/reservation\/VIS-/);await page.unroute('**/studio-api/reservations');
 saved=await profile();assert.equal(saved.version,2);assert.equal(saved.contact_method,'phone');
 const list=await (await page.request.get(base+'/studio-api/manage/reservations')).json();assert.equal(list.items.length,2);assert.equal(list.items.find(r=>r.id===firstId).payload.contact,'first-wechat');
 checks.push('Summary opens editable fields; back/reload preserve edits; lost response retry creates one booking and changes profile once; old snapshot retained');
 await page.goto(base+'/account');await page.locator('.account-edit').click();await expect(page.locator('.profile-contact input[autocomplete=name]')).toHaveValue('Updated booking name');
 await page.locator('.profile-contact input[autocomplete=name]').fill('Profile preferred name');await page.locator('.profile-contact input[value=email]').check();await page.locator('.profile-contact .visit-contact-value input').fill('booking-only@example.test');
 await page.locator('.profile-actions .button-primary').click();await expect(page.locator('.profile-form')).toBeHidden();
 saved=await profile();assert.equal(saved.name,'Profile preferred name');assert.equal(saved.version,3);const account=await (await page.request.get(base+'/studio-api/auth/me',{headers:{Authorization:'Bearer qa-owner'}})).json();assert.equal(account.user.email,'qa-owner@example.test');
 await page.goto(base+'/manage?view=members');await page.locator('.member-search input').fill('booking-only');await expect(page.locator('.member-row')).toHaveCount(1);await expect(page.locator('.member-row')).toContainText('Profile preferred name');
 await page.locator('.member-row').click();await expect(page.locator('.booking-profile-summary')).toContainText('booking-only@example.test');await page.locator('.booking-profile-summary button').click();
 await page.locator('.profile-contact input[autocomplete=name]').fill('Host corrected name');await page.locator('.booking-profile-actions .primary').click();await expect(page.locator('.booking-profile-summary')).toContainText('Host corrected name');await shot('admin-profile');
 checks.push('Personal profile and admin search/detail/edit share booking details; login email remains unchanged');
 await goContact();await expect(page.locator('.visit-saved-contact')).toContainText('Host corrected name');
 const axe=(await new AxeBuilder({page}).include('.visit-flow-page').analyze()).violations.map(v=>({id:v.id,targets:v.nodes.map(n=>n.target)}));await fs.writeFile(new URL('accessibility.json',out),JSON.stringify(axe,null,2));assert.deepEqual(axe,[]);
 for(const lang of ['zh','en']){
  if(!(await page.locator('html').getAttribute('lang')).startsWith(lang))await page.locator('.language-button').first().click();
  for(const [width,height] of [[320,568],[390,844],[844,390],[1024,768],[1440,900],[2560,1440]]){
   await page.setViewportSize({width,height});await measure(lang+' saved summary');if(width===390)await shot(lang+'-summary-mobile');
   await page.locator('.visit-saved-contact button').click();await expect(name()).toBeFocused();await measure(lang+' edit fields');await expect(contact()).toHaveValue('booking-only@example.test');if(width===390)await shot(lang+'-edit-mobile');
   await page.locator('.visit-contact-cancel').click();await expect(page.locator('.visit-saved-contact')).toBeVisible();
  }
 }
 await page.setViewportSize({width:1440,height:900});
 const other=await ctx.newPage();await other.goto(base+'/');await other.evaluate(()=>{localStorage.setItem('pd_web_token','qa-email-cross');localStorage.setItem('pd_web_user',JSON.stringify({user_id:'qa-email-cross'}));});await page.bringToFront();
 await expect(name()).toBeVisible();await expect(name()).toHaveValue('');await expect(contact()).toHaveValue('');await expect(page.locator('.visit-saved-contact')).toHaveCount(0);await other.close();
 checks.push('24 bilingual summary/edit layouts; accessible summary; changing accounts clears previous name and contact');
 await ctx.close();
}catch(error){if(page&&!page.isClosed())await page.screenshot({path:fileURLToPath(new URL('failure.png',out))});throw error;}
finally{await browser.close();await fs.writeFile(new URL('verification.json',out),JSON.stringify({checks,measures,errors},null,2));}
const safari=await webkit.launch({headless:true});
try{
 const ctx=await context(safari,'qa-owner',{width:390,height:844});await goContact();await expect(page.locator('.visit-saved-contact')).toContainText('Host corrected name');await measure('WebKit fresh-context profile');
 await page.locator('.visit-saved-contact button').click();await name().fill('Unsaved Safari edit');await page.locator('.language-button').first().click();await expect(name()).toHaveValue('Unsaved Safari edit');
 await page.setViewportSize({width:844,height:390});await measure('WebKit short landscape edit');
 await page.goto(base+'/account');await page.locator('.account-edit').click();await expect(page.locator('.profile-contact input[autocomplete=name]')).toHaveValue('Host corrected name');await page.setViewportSize({width:390,height:844});await measure('WebKit personal profile');await shot('profile-mobile');await ctx.close();
 checks.push('A different browser reads saved profile from server; Safari edits survive language change; personal profile fits mobile');
}finally{await safari.close();await fs.writeFile(new URL('verification.json',out),JSON.stringify({checks,measures,errors},null,2));}
assert.deepEqual(errors,[]);console.log(JSON.stringify({checks,states:measures.length,errors},null,2));
