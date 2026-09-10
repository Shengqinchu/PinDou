import {chromium,webkit,expect} from '@playwright/test';
import fs from 'node:fs/promises';import assert from 'node:assert/strict';import {fileURLToPath} from 'node:url';
const base=process.env.PINDOU_QA_ORIGIN||'http://127.0.0.1:19678';
const out=new URL('../../artifacts/visit-launch/',import.meta.url),results=[];
for(const [engine,type] of [['chromium',chromium],['webkit',webkit]]){
 const browser=await type.launch({headless:true});const ctx=await browser.newContext({viewport:{width:375,height:667},locale:'en-CA',hasTouch:true,isMobile:true});const page=await ctx.newPage();const errors=[];page.on('pageerror',e=>errors.push(e.message));
 try{
  await page.goto(base+'/visit');await expect(page.locator('.visit-duo-offer')).toBeEnabled();await expect(page.locator('.visit-guests button').first()).toHaveAccessibleName('1 guest');
  await page.locator('.visit-duo-offer').tap();await expect(page.locator('.visit-dates')).toBeVisible();await page.locator('.visit-dates button:not(:disabled)').first().tap();await expect(page.locator('.visit-times button').first()).toBeVisible();await page.locator('.visit-times button').first().tap();await page.locator('.visit-actions .button-primary').tap();await expect(page.locator('.visit-contact')).toBeVisible();await expect(page.locator('.visit-step-enter-active')).toHaveCount(0);
  const box=await page.evaluate(()=>{const s=document.querySelector('.visit-scroll');return {height:innerHeight,body:document.documentElement.scrollHeight,scroll:s.scrollHeight,client:s.clientHeight,overflow:document.documentElement.scrollWidth>innerWidth+1,footer:document.querySelector('.visit-actions').getBoundingClientRect().bottom};});assert(!box.overflow&&box.body<=box.height+1&&box.footer<=box.height+1);assert(box.scroll<=box.client+3,engine+' compact contact needs scrolling');
  await page.locator('input[autocomplete=name]').fill('Compatibility guest');await page.locator('.contact-method-picker label').nth(2).tap();await page.locator('.visit-contact-value input').fill('5551234567');await page.locator('.vision-header-actions .language-button').tap();await expect(page.locator('input[autocomplete=name]')).toHaveValue('Compatibility guest');await page.screenshot({path:fileURLToPath(new URL(engine+'-compact-contact.png',out)),fullPage:true});
  await page.locator('.visit-back').tap();await expect(page.locator('.visit-times')).toBeVisible();await page.reload();await expect(page.locator('.visit-times')).toBeVisible();assert.deepEqual(errors,[]);results.push({engine,box,errors});
 }finally{await browser.close();}
}
await fs.writeFile(new URL('compatibility.json',out),JSON.stringify(results,null,2));console.log(JSON.stringify(results,null,2));
