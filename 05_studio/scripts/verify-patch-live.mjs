// Public GET-only production verification. Does not create bookings or notifications.
import {chromium,expect} from '@playwright/test';
import assert from 'node:assert/strict';
import fs from 'node:fs/promises';
const browser=await chromium.launch(),results=[];
const out=new URL('../../artifacts/patch-booking/browser/',import.meta.url);
try{
 for(const [width,height,lang] of [[1440,1000,'zh'],[390,844,'en']]){
  const context=await browser.newContext({viewport:{width,height}});
  await context.addInitScript(lang=>localStorage.setItem('puppy-studio-language',lang),lang);
  await context.route('**/*',r=>['GET','HEAD','OPTIONS'].includes(r.request().method())?r.continue():r.abort('blockedbyclient'));
  const page=await context.newPage(),errors=[];page.on('pageerror',e=>errors.push(e.message));
  await page.goto('https://pindoupuppy.com/visit',{waitUntil:'domcontentloaded',timeout:60000});
  await expect(page.locator('.visit-plans>label')).toHaveCount(3,{timeout:45000});
  await page.evaluate(()=>document.fonts.ready);await page.waitForTimeout(500);
  await expect(page.locator('.visit-combined-offers>article')).toHaveCount(2);
  const card=page.locator('.visit-plans>label').filter({has:page.locator('input[value=patch]')});
  await expect(card.locator('.money-text')).toHaveCount(0);
  await page.screenshot({path:new URL('live-'+lang+'-experiences.png',out).pathname.replace(/^\/([A-Z]:)/,'$1'),animations:'disabled'});
  const version=await page.evaluate(()=>fetch('/version.json',{cache:'no-store'}).then(r=>r.json()));
  await card.locator('input').check();await page.locator('.visit-actions>.button').click();
  await expect(page.locator('.reservation-minimum-note')).toContainText(lang==='zh'?'1小时':'1 hour');
  const calendar=await page.evaluate(()=>fetch('/studio-api/reservation-calendar?experience=patch&guests=1',{cache:'no-store'}).then(r=>r.json()));
  assert.equal(calendar.experience,'patch');assert.equal(calendar.minimum_minutes,60);assert.equal(calendar.capacity_buffer_minutes,0);
  const free=page.locator('.reservation-grid button:not(:disabled)').first();await expect(free).toBeVisible();
  const day=await free.getAttribute('data-date'),start=await free.getAttribute('data-time');
  await page.locator('.reservation-grid button[data-date="'+day+'"][data-time="'+start+'"]').click();
  await expect(page.locator('.reservation-grid button.chosen')).toHaveCount(2);
  await expect(page.locator('.visit-actions>.button')).toBeEnabled();
  await page.waitForTimeout(450);
  await page.screenshot({path:new URL('live-'+lang+'-time.png',out).pathname.replace(/^\/([A-Z]:)/,'$1'),animations:'disabled'});
  assert(!await page.evaluate(()=>document.documentElement.scrollWidth>innerWidth+1));assert.deepEqual(errors,[]);
  results.push({width,height,lang,version,calendar:{policy_version:calendar.policy_version,max_guests_per_group:calendar.max_guests_per_group,minimum_minutes:calendar.minimum_minutes},selection:{day,start},passed:true});
  await context.close();
 }
}finally{await browser.close();await fs.writeFile(new URL('live-results.json',out),JSON.stringify(results,null,2));}
console.log(JSON.stringify(results));
