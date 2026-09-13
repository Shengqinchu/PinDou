// Disposable loopback fixture only; never submits orders to production.
import {chromium,webkit,expect} from '@playwright/test';
import assert from 'node:assert/strict';
import fs from 'node:fs/promises';
import {fileURLToPath} from 'node:url';
const base='http://127.0.0.1:4184',out=new URL('../../artifacts/product-organizing-20260913/',import.meta.url),results=[];
for(const [name,engine] of [['chromium',chromium],['webkit',webkit]]){
 const browser=await engine.launch({headless:true});
 let activePage;
 try{
  const ctx=await browser.newContext({viewport:{width:1440,height:1000},reducedMotion:'reduce'});
  await ctx.addInitScript(()=>{localStorage.setItem('puppy-studio-locale','zh');sessionStorage.setItem('puppy-studio-admin','local-qa')});
  const page=await ctx.newPage(),errors=[];activePage=page;page.on('pageerror',e=>errors.push(e.message));
  const before=await (await ctx.request.get(base+'/studio-api/manage/shop')).json();
  await page.goto(base+'/shop?section=finished');await expect(page.locator('.shop-card')).toHaveCount(5);
  const small=page.locator('.shop-card').filter({hasText:'小号拼豆礼品'});
  assert.ok(await page.locator('.shop-card').filter({hasText:'待定价测试'}).locator('.shop-add').isDisabled());
  for(const width of [320,390,1440]){await page.setViewportSize({width,height:900});assert.equal(await page.evaluate(()=>document.documentElement.scrollWidth>innerWidth),false)}
  await page.screenshot({path:fileURLToPath(new URL(name+'-catalog.png',out))});
  const dialog=page.locator('dialog[data-phase="open"]');
  async function add(product,variant,choice){
   await page.locator('.shop-card').filter({hasText:product}).locator('.shop-add').click();await dialog.waitFor();
   assert.ok(await dialog.locator('.drawer-bottom button').isDisabled());
   await dialog.locator('.shop-option-group').first().getByRole('button',{name:variant,exact:true}).click();
   if(choice)await dialog.locator('.shop-option-group').nth(1).getByRole('button',{name:choice,exact:true}).click();
   await dialog.locator('.drawer-bottom button').click();await page.keyboard.press('Escape');await expect(dialog).toHaveCount(0);
  }
  await add('小号拼豆礼品','1 · 发夹');await add('小号拼豆礼品','2 · 发夹');await add('小号拼豆礼品','3 · 徽章');
  await add('中号拼豆礼品','1 · 挂件');await add('中号拼豆礼品','4 · 杯垫');
  await add('小猫摇摇乐','定制','冰箱贴');
  // Complete image is shown without cropping; English poster is the last photo.
  await page.locator('.shop-card').filter({hasText:'小猫摇摇乐'}).locator('.shop-card-preview').click();await dialog.waitFor();
  await dialog.locator('.shop-thumbnails button').last().click();
  await expect(dialog.locator('.shop-detail-image')).toHaveAttribute('src',/swinging-cats-en\.png$/);
  await dialog.locator('.shop-detail-image').evaluate(img=>img.decode());
  await page.screenshot({path:fileURLToPath(new URL(name+'-english-poster.png',out))});
  await page.keyboard.press('Escape');await expect(dialog).toHaveCount(0);
  await page.locator('.shop-action').first().click();await dialog.waitFor();
  await expect(dialog.locator('button[form="manual-shop-order"]')).toBeEnabled();
  await expect(dialog.locator('.shop-cart-total strong')).toHaveText(/21\.00/);
  await page.setViewportSize({width:390,height:844});
  assert.equal(await page.evaluate(()=>document.documentElement.scrollWidth>innerWidth),false);
  await dialog.getByLabel('怎么称呼您（可选）',{exact:true}).fill('Local '+name);
  await dialog.getByLabel('订单备注 / 定制要求（可选）',{exact:true}).fill('QA-only custom cat');
  await page.screenshot({path:fileURLToPath(new URL(name+'-cart-mobile.png',out))});
  let lost=false,createdId='';
  await page.route('**/studio-api/shop/orders',async route=>{
   if(route.request().method()==='POST'&&!lost){lost=true;const response=await route.fetch();assert.equal(response.status(),201);createdId=(await response.json()).id;await route.abort('failed');}
   else await route.continue();
  });
  await dialog.locator('button[form="manual-shop-order"]').click();
  await expect(dialog.getByRole('button',{name:'重试提交',exact:true})).toBeVisible();
  // Recovery survives a page refresh and keeps the original idempotency key.
  await page.reload();await dialog.waitFor();await dialog.getByRole('button',{name:'重试提交',exact:true}).click();
  await page.waitForURL('**/order/'+createdId);await expect(page.locator('.shop-manual-receipt')).toBeVisible();
  assert.equal(await page.locator('.shop-order-sum').last().textContent().then(t=>t.includes('21.00')),true);
  assert.equal(await page.locator('body').innerText().then(t=>/CNY|二维码支付|微信支付|支付宝支付/.test(t)),false);
  await page.getByLabel('留下联系方式（可选）',{exact:true}).fill('微');
  await page.getByRole('button',{name:'保存联系方式',exact:true}).click();
  await expect(page.getByRole('status').filter({hasText:'联系方式已保存'})).toBeVisible();
  await page.screenshot({path:fileURLToPath(new URL(name+'-receipt-mobile.png',out))});
  await page.reload();await expect(page.getByLabel('留下联系方式（可选）',{exact:true})).toHaveValue('微');
  await page.locator('.language-button').click();
  await expect(page.getByRole('heading',{name:'Order placed',exact:true})).toBeVisible();
  await page.screenshot({path:fileURLToPath(new URL(name+'-receipt-en.png',out))});
  await page.goto(base+'/manage?view=shop');await page.locator('.shop-admin-row').first().waitFor();
  if((await page.locator('.desk-language').textContent()).includes('中文'))await page.locator('.desk-language').click();
  await page.locator('.shop-tabs').getByRole('button',{name:'商品订单',exact:true}).click();
  const row=page.locator('.shop-manual-order-row').filter({hasText:createdId});await row.waitFor();
  await row.click();await dialog.waitFor();await expect(dialog.locator('.drawer-body')).toContainText('微');
  await dialog.getByLabel('订单状态',{exact:true}).selectOption('manual_confirmed');await dialog.locator('button[form="shop-order-status"]').click();await expect(dialog).toHaveCount(0);
  await row.click();await dialog.waitFor();await dialog.getByLabel('订单状态',{exact:true}).selectOption('manual_completed');await dialog.locator('button[form="shop-order-status"]').click();await expect(dialog).toHaveCount(0);
  await page.screenshot({path:fileURLToPath(new URL(name+'-admin-orders.png',out))});
  const orders=await (await ctx.request.get(base+'/studio-api/manage/shop/orders')).json();
  assert.equal(orders.items.filter(x=>x.id===createdId).length,1);assert.equal(orders.items.find(x=>x.id===createdId).status,'manual_completed');
  await page.locator('.shop-tabs').getByRole('button',{name:'小店商品',exact:true}).click();
  await page.getByLabel('搜索商品或色号',{exact:true}).fill('小号拼豆礼品');await page.locator('.shop-admin-row').first().click();await dialog.waitFor();
  await dialog.getByRole('button',{name:'增加规格',exact:true}).click();
  await dialog.getByLabel('规格名称（中文）',{exact:true}).last().fill('8 · 测试');
  await dialog.getByLabel('规格名称（英文）',{exact:true}).last().fill('8 · Test');
  await dialog.getByLabel('这些商品合计售价（CAD）',{exact:true}).fill('4.5');
  await dialog.locator('button[form="shop-product-editor"]').click();await expect(dialog).toHaveCount(0);
  const after=await (await ctx.request.get(base+'/studio-api/manage/shop')).json();
  const p=after.products.find(p=>p.id==='gift-small');assert.equal(p.variants.at(-1).zh,'8 · 测试');assert.equal(p.quantity_offer.price_cents,450);
  assert.equal(p.stock,before.products.find(p=>p.id==='gift-small').stock-3);
  // Restore only fixture catalog edits so the second engine sees the same products.
  const original=before.products.find(p=>p.id==='gift-small');
  const restore=await ctx.request.put(base+'/studio-api/manage/products/gift-small',{data:{...original,stock:p.stock,version:p.version}});assert.equal(restore.status(),200);
  assert.deepEqual(errors,[]);
  results.push({engine:name,passed:true,totalCents:2100,mixedVariantDiscount:200,retryAfterReloadSameOrder:true,contactSaved:true,adminCompletionDeductsOnce:true,editableVariantsAndOffer:true,englishPoster:true,widths:[320,390,1440]});
 }catch(e){if(activePage){await activePage.screenshot({path:fileURLToPath(new URL(name+'-failure.png',out))});await fs.writeFile(new URL(name+'-failure-dom.txt',out),await activePage.locator('body').innerText())}await fs.writeFile(new URL(name+'-failure.txt',out),String(e.stack));throw e}finally{await browser.close()}
}
await fs.writeFile(new URL('browser-verification.json',out),JSON.stringify(results,null,2));console.log(JSON.stringify(results));
