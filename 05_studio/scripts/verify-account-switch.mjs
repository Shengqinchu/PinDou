import {chromium,expect} from '@playwright/test';
import fs from 'node:fs/promises';import assert from 'node:assert/strict';
const base=process.env.PINDOU_QA_ORIGIN||'http://127.0.0.1:19680';
const browser=await chromium.launch({headless:true});
try{
 const ctx=await browser.newContext({viewport:{width:1440,height:900},locale:'en-CA'});
 await ctx.addInitScript(()=>{if(!localStorage.getItem('pd_web_token'))localStorage.setItem('pd_web_token','qa-owner');});
 const page=await ctx.newPage();const errors=[];page.on('pageerror',e=>errors.push(e.message));
 await page.route('**/studio-api/auth/me',async r=>{const reply=await r.fetch(),data=await reply.json();data.user.nickname=r.request().headers().authorization==='Bearer qa-other'?'Second account':'First account';await r.fulfill({response:reply,json:data});});
 await page.route('**/studio-api/auth/wallet?*',async r=>{const reply=await r.fetch(),data=await reply.json();const other=r.request().headers().authorization==='Bearer qa-other';data.account.points=other?87:12345;if(other)await new Promise(resolve=>setTimeout(resolve,1200));await r.fulfill({response:reply,json:data});});
 await page.goto(base+'/account');await expect(page.locator('.wallet-balance.points strong')).toContainText('12,345');
 await page.evaluate(()=>{window.oldAccountFrames=0;window.sampleAccountFrames=true;function check(){if(document.querySelector('.account-identity strong')?.textContent==='Second account'&&document.querySelector('.wallet-balance.points strong')?.textContent?.includes('12,345'))window.oldAccountFrames++;if(window.sampleAccountFrames)requestAnimationFrame(check);}check();});
 const other=await ctx.newPage();await other.goto(base+'/');await other.evaluate(()=>{localStorage.setItem('pd_web_token','qa-other');localStorage.setItem('pd_web_user',JSON.stringify({user_id:'qa-other',email:'qa-other@example.test'}));});
 await page.bringToFront();await expect(page.locator('.account-identity strong')).toHaveText('Second account');await expect(page.locator('.wallet-balance.points strong')).not.toContainText('12,345');await expect(page.locator('.wallet-balance.points strong')).toHaveText('87');
 const staleFrames=await page.evaluate(()=>{window.sampleAccountFrames=false;return window.oldAccountFrames;});assert.equal(staleFrames,0);assert.deepEqual(errors,[]);
 await fs.writeFile(new URL('../../artifacts/ui-auth-refinement/account-switch.json',import.meta.url),JSON.stringify({passed:true,staleFrames,errors},null,2));console.log(JSON.stringify({passed:true,staleFrames,errors}));
}finally{await browser.close();}
