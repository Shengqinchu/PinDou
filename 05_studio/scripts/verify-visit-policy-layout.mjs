import {chromium,webkit,expect} from '@playwright/test';
import fs from 'node:fs/promises';import assert from 'node:assert/strict';
const base=process.env.PINDOU_QA_ORIGIN||'http://127.0.0.1:19678';
const results=[];
for(const [name,type] of [['chromium',chromium],['webkit',webkit]]){
 const browser=await type.launch({headless:true});const page=await browser.newPage({viewport:{width:390,height:844},locale:'en-CA'});
 try{
  const calendar=await (await page.request.get(base+'/studio-api/reservation-calendar')).json();
  for(const limit of [6,99]){
   await page.route('**/studio-api/reservation-calendar?*',route=>route.fulfill({json:{...calendar,max_guests_per_group:limit}}));
   for(const width of [320,390]){
    await page.setViewportSize({width,height:667});await page.goto(base+'/visit?step=1');await expect(page.locator('.visit-duo-offer')).toBeEnabled();
    const box=await page.evaluate(()=>({width:innerWidth,page:document.documentElement.scrollWidth,height:innerHeight,body:document.documentElement.scrollHeight,buttons:[...document.querySelectorAll('.visit-guests button')].map(b=>b.getBoundingClientRect().width)}));assert(box.page<=box.width+1&&box.body<=box.height+1);assert(box.buttons.every(w=>w>=43.9));
    if(limit===6){await page.locator('.visit-guests button').last().click();await expect(page.locator('.visit-guests button').last()).toHaveAttribute('aria-pressed','true');await expect(page.locator('.visit-guests input')).toHaveCount(0);}
    else{await page.locator('.visit-guests input').fill('8');await expect(page.locator('.visit-guests input')).toHaveValue('8');}
    results.push({name,limit,...box});
   }
   await page.unroute('**/studio-api/reservation-calendar?*');
  }
 }finally{await browser.close();}
}
await fs.writeFile(new URL('../../artifacts/visit-launch/policy-layout.json',import.meta.url),JSON.stringify(results,null,2));console.log(JSON.stringify({checks:results.length,passed:true}));
