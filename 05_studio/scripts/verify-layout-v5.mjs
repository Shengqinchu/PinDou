// Read-only visual verification against the local QA service, after wallet flow QA.
import {chromium,expect} from '@playwright/test';
import {fileURLToPath} from 'node:url';
import fs from 'node:fs/promises';
import assert from 'node:assert/strict';
const out=new URL('../../artifacts/studio-v5/',import.meta.url),base='http://127.0.0.1:4184',results=[];
const browser=await chromium.launch({headless:true,ignoreDefaultArgs:['--hide-scrollbars']});
try{
 const context=await browser.newContext({reducedMotion:'reduce'});
 await context.addInitScript(()=>{localStorage.setItem('pd_web_token','qa-owner');sessionStorage.setItem('puppy-studio-admin','local-qa');});
 const page=await context.newPage();page.setDefaultTimeout(12000);
 async function photos(selector){
   const images=page.locator(selector);
   for(let i=0;i<await images.count();i++){await images.nth(i).scrollIntoViewIfNeeded();await expect.poll(()=>images.nth(i).evaluate(e=>e.complete&&e.naturalWidth>0)).toBe(true);}
   await page.evaluate(()=>document.fonts.ready);
 }
 async function screenshot(name,locator){await (locator||page).screenshot({path:fileURLToPath(new URL(name,out))});}
 for(const [width,height] of [[320,740],[390,844],[768,1024],[1024,768],[1280,720],[1440,900],[1920,1080],[2560,1440]]){
   await page.setViewportSize({width,height});
   await page.goto(base+'/?motion=reduced',{waitUntil:'networkidle'});
   await photos('.home-journal-photo img');await page.locator('.vision-journal').scrollIntoViewIfNeeded();
   assert(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth+1));
   if([390,1440].includes(width))await screenshot(`home-${width}.png`,page.locator('.vision-journal'));
   await page.goto(base+'/details?motion=reduced',{waitUntil:'networkidle'});await photos('.process-photo img');
   const shapes=await page.locator('.process-step').evaluateAll(nodes=>nodes.map(n=>({height:n.getBoundingClientRect().height,images:[...n.querySelectorAll('img')].map(img=>({width:img.clientWidth,height:img.clientHeight,nw:img.naturalWidth,nh:img.naturalHeight,opacity:getComputedStyle(img).opacity}))})));
   for(const shape of shapes)for(const p of shape.images){assert(p.nw>0&&p.width>0&&p.opacity==='1');assert(Math.abs(p.width/p.height-p.nw/p.nh)<.03);}
   assert(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth+1));
   if([390,1440].includes(width))await screenshot(`process-${width}.png`,page.locator('#process'));
   await page.locator('#arrival').scrollIntoViewIfNeeded();
   if([390,1440].includes(width))await screenshot(`arrival-${width}.png`,page.locator('#arrival'));
   await page.locator('.vision-header').scrollIntoViewIfNeeded();await page.locator('.account-trigger').click();
   await expect(page.locator('dialog[open]')).toHaveAttribute('data-phase','open');
   await expect(page.locator('.wallet-balances')).toBeVisible();
   const panel=page.locator('dialog[open] .drawer-panel');assert(await panel.evaluate(e=>e.scrollWidth<=e.clientWidth+1));
   if([390,1440].includes(width))await screenshot(`account-${width}.png`);
   await page.keyboard.press('Escape');await expect(page.locator('dialog[open]')).toHaveCount(0);
   await page.goto(base+'/manage?view=members&motion=reduced',{waitUntil:'networkidle'});
   assert(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth+1));
   await page.locator('.member-row').filter({hasText:'qa-owner@example.test'}).click();
   await expect(page.locator('dialog[open]')).toHaveAttribute('data-phase','open');
   await page.getByRole('button',{name:'登记一笔',exact:true}).click();
   await page.getByRole('combobox',{name:'记账类型',exact:true}).selectOption('gift');
   assert(await panel.evaluate(e=>e.scrollWidth<=e.clientWidth+1));
   if([390,1440].includes(width))await screenshot(`admin-${width}.png`);
   results.push({width,height,processHeight:Math.round(shapes.reduce((n,s)=>n+s.height,0)),loadedImages:shapes.reduce((n,s)=>n+s.images.length,0),uncropped:true,account:true,admin:true,overflow:false});
   await page.keyboard.press('Escape');
 }
 await fs.writeFile(new URL('layout-verification.json',out),JSON.stringify(results,null,2));console.log(JSON.stringify(results,null,2));
}finally{await browser.close()}
