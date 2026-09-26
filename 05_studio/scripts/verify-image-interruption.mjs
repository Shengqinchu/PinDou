import {chromium,webkit,expect} from '@playwright/test';
import assert from 'node:assert/strict';
import fs from 'node:fs/promises';
const out=new URL('../../artifacts/image-delivery-20260914/',import.meta.url),results=[];
for(const [name,engine] of [['chromium',chromium],['webkit',webkit]]){
 const browser=await engine.launch();
 try{
  const context=await browser.newContext({viewport:{width:1440,height:900}});
  await context.addInitScript(()=>localStorage.setItem('puppy-studio-language','zh'));
  const page=await context.newPage();const errors=[];page.on('pageerror',e=>errors.push(e.message));
  await page.goto('http://127.0.0.1:4184/shop',{waitUntil:'domcontentloaded'});
  await page.locator('.shop-action').first().waitFor();
  const click=await page.evaluate(async()=>{
   const start=performance.now();document.querySelector('.shop-action').click();
   while(!document.querySelector('dialog[open]'))await new Promise(requestAnimationFrame);
   return {ms:performance.now()-start,titleOpacity:+getComputedStyle(document.querySelector('h1 > .lift-line')).opacity};
  });
  assert.ok(click.ms<500&&click.titleOpacity<1,'Cart opens while the page is entering');
  await page.keyboard.press('Escape');await expect(page.locator('dialog[open]')).toHaveCount(0);
  for(const path of ['/visit','/journal','/shop','/visit','/shop']){
   await page.locator(`.vision-header a[href="${path}"]`).first().evaluate(a=>a.click());
   await page.waitForTimeout(85);
  }
  await page.locator('.shop-page').waitFor();await page.waitForTimeout(1000);
  await expect(page.locator('h1 > .lift-line')).toHaveCSS('opacity','1');
  const children=page.locator('.shop-children button');await children.first().waitFor();
  for(const index of [1,2,3,1,3]){await children.nth(index).evaluate(b=>b.click());await page.waitForTimeout(45);}
  await expect(page.locator('.shop-children button.active')).toHaveText('D系列');
  await expect.poll(()=>page.locator('.shop-card-preview img').evaluateAll(images=>images.filter(i=>{const r=i.getBoundingClientRect();return r.top<innerHeight&&r.bottom>0}).every(i=>i.complete&&i.naturalWidth>0))).toBe(true);
  assert.deepEqual(errors,[]);
  results.push({engine:name,click,rapidNavigation:true,rapidCategorySwitch:true,errors});
 }finally{await browser.close();}
}
await fs.writeFile(new URL('interruption.json',out),JSON.stringify(results,null,2));console.log(JSON.stringify(results));
