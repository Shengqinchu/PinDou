import {chromium,webkit,expect} from '@playwright/test';import fs from 'node:fs/promises';import assert from 'node:assert/strict';import {fileURLToPath} from 'node:url';
const out=new URL('../../artifacts/visit-simple/',import.meta.url),base='http://127.0.0.1:19684';const checks=[];
for(const [engine,name] of [[chromium,'chromium'],[webkit,'webkit']]){
 const browser=await engine.launch({headless:true});
 try{const page=await browser.newPage({viewport:{width:844,height:390},locale:'en-CA'});await page.goto(base+'/visit?step=1');await page.locator('.visit-plans input[value=hourly]').check();await page.locator('.visit-actions .button-primary').click();await page.locator('.reservation-grid button:not(:disabled)').first().click();await page.locator('.visit-actions .button-primary').click();await expect(page.locator('.visit-contact')).toBeVisible();await expect(page.locator('.visit-step-enter-active')).toHaveCount(0);const dimensions=await page.evaluate(()=>{const s=document.querySelector('.visit-scroll'),box=s.getBoundingClientRect();return {height:innerHeight,scroll:s.scrollHeight,client:s.clientHeight,inputs:[...s.querySelectorAll('input:not([type=radio])')].map(e=>{const r=e.getBoundingClientRect();return {top:r.top,bottom:r.bottom,within:r.top>=box.top&&r.bottom<=box.bottom};})};});assert(dimensions.inputs.every(x=>x.within),name+' landscape input clipped');checks.push({name,dimensions});await page.screenshot({path:fileURLToPath(new URL('landscape-final-'+name+'.png',out))});
 if(name==='chromium'){
  const original=await (await page.request.get(base+'/studio-api/manage/reservation-policy')).json();const policy=original.policy||original;
  const updated=await page.request.put(base+'/studio-api/manage/reservation-policy',{data:{...policy,max_guests_per_group:99}});assert.equal(updated.status(),200);
  try{await page.goto(base+'/visit?step=2');await page.locator('.visit-guest-trigger').click();await page.keyboard.press('End');await expect(page.locator('[data-count="99"]')).toBeFocused();await page.keyboard.press('Enter');await expect(page.locator('.visit-guest-trigger')).toContainText('99');await expect(page.locator('.visit-guest-options')).toHaveCount(0);checks.push({maximum99:true});}
  finally{const latest=await (await page.request.get(base+'/studio-api/manage/reservation-policy')).json();const p=latest.policy||latest;const restore=await page.request.put(base+'/studio-api/manage/reservation-policy',{data:{...policy,version:p.version}});assert.equal(restore.status(),200);}
 }
 }finally{await browser.close();}
}
await fs.writeFile(new URL('extra-verification.json',out),JSON.stringify(checks,null,2));console.log(JSON.stringify(checks,null,2));
