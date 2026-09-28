// Read-only browser checks against the disposable qa_admin_visits.py service.
import {chromium,webkit,expect} from '@playwright/test';
import assert from 'node:assert/strict';
import fs from 'node:fs/promises';
const out=new URL('../../artifacts/patch-booking/browser/',import.meta.url),results=[];
for(const [name,type,width,reduced] of [['desktop',chromium,1440,false],['small-phone',chromium,320,true],['safari-phone',webkit,390,false]]){
 const browser=await type.launch();const context=await browser.newContext({viewport:{width,height:900},reducedMotion:reduced?'reduce':'no-preference'});
 await context.addInitScript(reduced=>{localStorage.setItem('puppy-studio-language','en');localStorage.setItem('puppy-studio-motion',reduced?'reduced':'full');},reduced);
 await context.route('**/studio-api/**',async route=>{const u=new URL(route.request().url());const r=await context.request.get('http://127.0.0.1:8127'+u.pathname+u.search);await route.fulfill({response:r});});
 const page=await context.newPage();const errors=[];page.on('pageerror',e=>errors.push(e.message));
 try{
  await page.goto('http://127.0.0.1:5287/visit');await expect(page.locator('.visit-plans>label')).toHaveCount(3);await page.evaluate(()=>document.fonts.ready);await page.waitForTimeout(500);
  const card=page.locator('.visit-plans>label').filter({has:page.locator('input[value=patch]')}),old=page.locator('.visit-plans>label').first();
  const skin=async locator=>locator.evaluate(e=>{const s=getComputedStyle(e),t=getComputedStyle(e.querySelector('strong'));return{radius:s.borderRadius,font:t.fontFamily,weight:t.fontWeight,color:t.color,press:s.getPropertyValue('--tactile-press-transform'),ease:s.getPropertyValue('--control-ease'),opacity:s.opacity};});
  const cardSkin=await skin(card);assert.deepEqual(cardSkin,await skin(old));
  await card.locator('input').focus();assert.equal(await card.evaluate(e=>getComputedStyle(e).outlineStyle),'solid');
  let held;
  if(!reduced&&width>700){await card.hover();await page.mouse.down();await page.waitForTimeout(350);held=await card.evaluate(e=>getComputedStyle(e).transform);assert(held.includes('0.975'));await page.mouse.up();}
  if(reduced){await expect(page.locator('html')).toHaveAttribute('data-motion','reduced');assert.equal(await card.evaluate(e=>getComputedStyle(e).transform),'none');}
  for(const [plan,duration] of [['hourly',120],['day',null],['patch',60]]){
   await page.locator('.visit-progress button').first().click();
   await page.locator('.visit-plans input[value='+plan+']').check();
   await page.locator('.visit-actions>.button').click();
   const free=page.locator('.reservation-grid button:not(:disabled)').first();await expect(free).toBeVisible();
   const day=await free.getAttribute('data-date'),start=await free.getAttribute('data-time');
   await page.locator('.reservation-grid button[data-date="'+day+'"][data-time="'+start+'"]').click();
   if(duration)await expect(page.locator('.reservation-grid button.chosen')).toHaveCount(duration/30);
   else {const end=await page.locator('.reservation-grid button.chosen').last().getAttribute('aria-label');assert(end);assert(await page.locator('.reservation-grid button.chosen').count()>=4);}
   await expect(page.locator('.visit-actions>.button')).toBeEnabled();
   assert(!await page.evaluate(()=>document.documentElement.scrollWidth>innerWidth+1));
  }
  await page.evaluate(()=>document.fonts.ready);await page.waitForTimeout(450);
  await page.screenshot({path:new URL(name+'-style.png',out).pathname.replace(/^\/([A-Z]:)/,'$1'),animations:'disabled'});
  assert.deepEqual(errors,[]);results.push({name,width,reduced,skin:cardSkin,held,passed:true});
 }finally{await browser.close();}
}
await fs.writeFile(new URL('style-results.json',out),JSON.stringify(results,null,2));console.log(JSON.stringify(results));
