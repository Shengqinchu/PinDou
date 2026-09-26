// Local tests may write only to loopback. --live allows catalog reads and quotes.
import {chromium,webkit,expect} from '@playwright/test';
import assert from 'node:assert/strict';
import fs from 'node:fs/promises';
import {fileURLToPath} from 'node:url';
const live=process.argv.includes('--live');
const base=live?'https://pindoupuppy.com':'http://127.0.0.1:4184';
const out=new URL('../../artifacts/scenery-products-20260913/',import.meta.url),results=[];
const goods=[['scenery-sunset-apocalypse','落日末世系列风景拼豆',1200,4500,2],['scenery-blue-coast','蓝色海岸系列风景拼豆',1000,3800,1]];
for(const [name,engine] of [['chromium',chromium],['webkit',webkit]]){
 const browser=await engine.launch({headless:true});let page;
 try{
  const ctx=await browser.newContext({viewport:{width:390,height:844},reducedMotion:'reduce'});
  await ctx.addInitScript(local=>{localStorage.setItem('puppy-studio-language','zh');if(local)sessionStorage.setItem('puppy-studio-admin','local-qa')},!live);
  page=await ctx.newPage();const errors=[],telemetryErrors=[];
  page.on('pageerror',e=>{if(e.message.includes('/cdn-cgi/rum'))telemetryErrors.push(e.message);else errors.push(e.message)});
  if(live)await ctx.route(/\/studio-api\//,route=>{
   const req=route.request();assert.ok(['GET','HEAD'].includes(req.method())||(req.method()==='POST'&&new URL(req.url()).pathname==='/studio-api/shop/cart/quote'),'Unexpected live write');return route.continue();
  });
  await page.goto(base+'/shop?section=finished');await expect(page.locator('.shop-card')).toHaveCount(6,{timeout:30000});
  const catalog=await (await ctx.request.get(base+'/studio-api/shop/catalog')).json();
  for(const [id,title,single,full,photos] of goods){
   const p=catalog.products.find(p=>p.id===id);assert.ok(p);assert.equal(p.price_cents,single);assert.equal(p.variants.at(-1).price_cents,full);assert.equal(p.variants.length,5);assert.equal(p.images.length,photos);
  }
  for(const width of [320,390,1440]){
   await page.setViewportSize({width,height:900});
   assert.equal(await page.evaluate(()=>document.documentElement.scrollWidth>innerWidth),false);
   const clipped=await page.locator('.shop-card').evaluateAll(cards=>cards.filter(card=>{
    const c=card.getBoundingClientRect();return [...card.querySelectorAll('.shop-price,.shop-add')].some(el=>{const r=el.getBoundingClientRect();return r.left<c.left||r.right>c.right+1});
   }).map(c=>c.querySelector('.shop-name').textContent));
   assert.deepEqual(clipped,[],`Clipped price at ${width}`);
  }
  await page.setViewportSize({width:390,height:844});
  const dialog=page.locator('dialog[data-phase="open"]');
  for(const [id,title,single,full,photos] of goods){
   await page.locator('.shop-card').filter({hasText:title}).locator('.shop-card-preview').click();await dialog.waitFor();
   await expect(dialog.locator('.shop-option-group button')).toHaveCount(5);
   for(let i=0;i<photos;i++){
    if(photos>1)await dialog.locator('.shop-thumbnails button').nth(i).click();
    await dialog.locator('.shop-detail-image').evaluate(img=>img.decode());
   }
   for(let i=0;i<5;i++){
    await dialog.locator('.shop-option-group button').nth(i).click();
    await expect(dialog.locator('.shop-detail-price')).toContainText(((i===4?full:single)/100).toFixed(2));
   }
   await page.screenshot({path:fileURLToPath(new URL(`${live?'live':'local'}-${name}-${id}.png`,out))});
   await dialog.locator('.drawer-bottom button').click();await page.keyboard.press('Escape');await expect(dialog).toHaveCount(0);
  }
  await page.locator('.shop-action').first().click();await dialog.waitFor();
  await expect(dialog.locator('.shop-cart-total strong')).toHaveText(/83\.00/,{timeout:20000});
  await expect(dialog.locator('.shop-bag-info>p').first()).toContainText('45.00');
  await dialog.locator('.shop-cart-select select').first().selectOption('1');
  await expect(dialog.locator('.shop-cart-total strong')).toHaveText(/50\.00/);
  await expect(dialog.locator('.shop-bag-info>p').first()).toContainText('12.00');
  await dialog.locator('.shop-cart-select select').first().selectOption('full-set');
  await expect(dialog.locator('.shop-cart-total strong')).toHaveText(/83\.00/);
  await page.screenshot({path:fileURLToPath(new URL(`${live?'live':'local'}-${name}-cart.png`,out))});
  if(!live){
   await dialog.locator('button[form="manual-shop-order"]').click();await page.waitForURL('**/order/**');
   await expect(page.locator('.shop-manual-receipt')).toBeVisible();await expect(page.locator('.shop-order-sum').last()).toContainText('83.00');
   await expect(page.locator('.shop-receipt-line').first()).toContainText('全套（四图）');
   await page.locator('.language-button').click();await expect(page.getByRole('heading',{name:'Order placed',exact:true})).toBeVisible();
   await expect(page.locator('.shop-receipt-line').first()).toContainText('Full set (4 pieces)');
   await page.goto(base+'/manage?view=shop');await page.locator('.shop-admin-row').first().waitFor();
   if((await page.locator('.desk-language').textContent()).includes('中文'))await page.locator('.desk-language').click();
   await page.getByLabel('搜索商品或色号',{exact:true}).fill(goods[0][1]);await page.locator('.shop-admin-row').first().click();await dialog.waitFor();
   const price=dialog.getByLabel('规格售价（CAD，可选）',{exact:true}).last();await expect(price).toHaveValue('45');
   await price.fill('44.5');await dialog.locator('button[form="shop-product-editor"]').click();await expect(dialog).toHaveCount(0);
   await page.locator('.shop-admin-row').first().click();await dialog.waitFor();await expect(price).toHaveValue('44.5');
   for(const width of [320,390,1440]){
    await page.setViewportSize({width,height:900});assert.equal(await page.evaluate(()=>document.documentElement.scrollWidth>innerWidth),false);
    assert.equal(await dialog.evaluate(el=>el.scrollWidth>el.clientWidth+1),false);
   }
   await page.setViewportSize({width:390,height:844});await price.scrollIntoViewIfNeeded();
   await page.screenshot({path:fileURLToPath(new URL(`local-${name}-admin-variant-price.png`,out))});
   await price.fill('45');await dialog.locator('button[form="shop-product-editor"]').click();await expect(dialog).toHaveCount(0);
  }else{await page.keyboard.press('Escape');await expect(dialog).toHaveCount(0);}
  await page.goto(base+'/shop?section=finished');await page.locator('.shop-card').first().waitFor();
  if(!await page.locator('.shop-name').filter({hasText:'Sunset Apocalypse'}).count())await page.locator('.language-button').click();
  await page.locator('.shop-card').filter({hasText:'Sunset Apocalypse'}).locator('.shop-card-preview').click();await dialog.waitFor();
  await dialog.getByRole('button',{name:/^Full set/}).click();await expect(dialog.locator('.shop-detail-price')).toContainText('45.00');
  await page.screenshot({path:fileURLToPath(new URL(`${live?'live':'local'}-${name}-english.png`,out))});
  assert.deepEqual(errors,[]);
  results.push({engine:name,passed:true,live,variantsPerProduct:5,fullSetsCents:8300,changedToSingleCents:5000,originalPhotos:3,adminVariantEditVerified:!live,productionOrdersCreated:0,telemetryErrors});
 }catch(e){if(page){await page.screenshot({path:fileURLToPath(new URL(`${live?'live':'local'}-${name}-failure.png`,out))});await fs.writeFile(new URL(`${live?'live':'local'}-${name}-failure-dom.txt`,out),await page.locator('body').innerText())}throw e}
 finally{await browser.close()}
}
await fs.writeFile(new URL((live?'live':'local')+'-browser-verification.json',out),JSON.stringify(results,null,2));console.log(JSON.stringify(results));
