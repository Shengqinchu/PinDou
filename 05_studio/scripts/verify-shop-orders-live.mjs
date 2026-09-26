// Production acceptance: catalog, image display and quotes only. No order writes.
import {chromium,webkit,expect} from '@playwright/test';
import assert from 'node:assert/strict';
import fs from 'node:fs/promises';
import {fileURLToPath} from 'node:url';
const base='https://pindoupuppy.com',out=new URL('../../artifacts/product-organizing-20260913/',import.meta.url),results=[];
for(const [name,engine] of [['chromium',chromium],['webkit',webkit]]){
 const browser=await engine.launch({headless:true});
 try{
  const ctx=await browser.newContext({viewport:{width:390,height:844},reducedMotion:'reduce'});
  await ctx.addInitScript(()=>localStorage.setItem('puppy-studio-language','zh'));
  const page=await ctx.newPage(),errors=[],telemetryErrors=[];
  page.on('pageerror',e=>{if(e.message==='/pindoupuppy.com/cdn-cgi/rum? due to access control checks.')telemetryErrors.push(e.message);else errors.push(e.message)});
  page.on('console',m=>{if(m.type()==='error'&&m.text().includes('/cdn-cgi/rum'))telemetryErrors.push(m.text())});
  await page.route(/\/studio-api\/(?:shop\/)?orders(?:\/|$)/,route=>{assert.equal(route.request().method(),'GET','Production order mutation blocked');return route.continue()});
  await page.goto(base+'/shop?section=finished');await expect(page.locator('.shop-card')).toHaveCount(4,{timeout:30000});
  const catalog=await (await ctx.request.get(base+'/studio-api/shop/catalog')).json();
  assert.equal(catalog.manual_ordering_ready,true);assert.equal(catalog.checkout_ready,false);assert.equal(catalog.products.length,240);
  for(const [id,cents,count] of [['gift-swinging-cats',600,5],['gift-stardew-charms',800,5],['gift-small',300,7],['gift-medium',400,4]]){
   const p=catalog.products.find(p=>p.id===id);assert.equal(p.price_cents,cents);assert.equal(p.variants.length,count);assert.equal(p.stock,999);
  }
  await page.locator('.shop-card-preview img').evaluateAll(images=>Promise.all(images.map(i=>i.decode())));
  for(const width of [320,390,1440]){await page.setViewportSize({width,height:900});assert.equal(await page.evaluate(()=>document.documentElement.scrollWidth>innerWidth),false)}
  await page.screenshot({path:fileURLToPath(new URL('live-'+name+'-catalog.png',out))});
  const dialog=page.locator('dialog[data-phase="open"]');
  const cat=page.locator('.shop-card').filter({hasText:'小猫摇摇乐'});
  await cat.locator('.shop-card-preview').click();await dialog.waitFor();
  for(let i=0;i<4;i++){await dialog.locator('.shop-thumbnails button').nth(i).click();await dialog.locator('.shop-detail-image').evaluate(img=>img.decode())}
  await page.setViewportSize({width:390,height:844});await page.screenshot({path:fileURLToPath(new URL('live-'+name+'-poster.png',out))});
  await page.keyboard.press('Escape');await expect(dialog).toHaveCount(0);
  for(const variant of ['1 · 发夹','2 · 发夹']){
   await page.locator('.shop-card').filter({hasText:'小号拼豆礼品'}).locator('.shop-add').click();await dialog.waitFor();
   await dialog.locator('.shop-option-group').getByRole('button',{name:variant,exact:true}).click();await dialog.locator('.drawer-bottom button').click();
   await page.keyboard.press('Escape');await expect(dialog).toHaveCount(0);
  }
  await page.locator('.shop-action').first().click();await dialog.waitFor();await expect(dialog.locator('button[form="manual-shop-order"]')).toBeEnabled({timeout:20000});
  await expect(dialog.locator('.shop-cart-total strong')).toHaveText(/5\.00/);
  await page.screenshot({path:fileURLToPath(new URL('live-'+name+'-cart.png',out))});
  assert.equal(await page.evaluate(()=>document.documentElement.scrollWidth>innerWidth),false);
  await page.keyboard.press('Escape');await expect(dialog).toHaveCount(0);
  await page.goto(base+'/shop?section=services');await expect(page.locator('.shop-card')).toHaveCount(2);
  await page.locator('.shop-card-preview').first().click();await dialog.waitFor();await expect(dialog.getByText('请联系店主确认总价',{exact:false})).toBeVisible();
  assert.equal(await dialog.getByRole('button',{name:'加入购物车',exact:true}).count(),0);
  assert.deepEqual(errors,[]);
  results.push({engine:name,passed:true,publicProducts:240,finishedProducts:4,variantCounts:[5,5,7,4],mixedPairCents:500,serviceQuoteOnly:true,noOrderCreated:true,telemetryErrors});
 }finally{await browser.close()}
}
await fs.writeFile(new URL('live-browser-verification.json',out),JSON.stringify(results,null,2));console.log(JSON.stringify(results));
