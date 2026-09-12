// Run only against the disposable local QA server with source catalog fixtures.
import { chromium, webkit } from 'playwright';
import assert from 'node:assert/strict';
import fs from 'node:fs/promises';
const base=process.env.SHOP_QA_ORIGIN||'http://127.0.0.1:5184';
if(!/^http:\/\/127\.0\.0\.1:/.test(base))throw Error('Local QA only');
const out=new URL('../../artifacts/shop-round-20260912/',import.meta.url);
const results=[];
for(const [name,engine] of [['chromium',chromium],['webkit',webkit]]){
 const browser=await engine.launch({headless:true});
 try{
  const context=await browser.newContext({viewport:{width:1440,height:1000},locale:'zh-CN',reducedMotion:'reduce'});
  await context.addInitScript(()=>{localStorage.setItem('puppy-studio-locale','zh');sessionStorage.setItem('puppy-studio-admin','local-qa')});
  const page=await context.newPage(),errors=[];page.on('pageerror',e=>errors.push(e.message));
  let catalogRequests=0;page.on('request',r=>{if(r.url().endsWith('/shop/catalog'))catalogRequests++});
  await page.goto(base+'/shop');await page.locator('.shop-card').first().waitFor();
  assert.equal(await page.locator('.shop-card').count(),27);
  await page.waitForFunction(()=>[...document.querySelectorAll('.shop-card img')].slice(0,4).every(e=>e.complete&&e.naturalWidth>0));
  await page.screenshot({path:new URL('shop-'+name+'-desktop.png',out).pathname.replace(/^\/([A-Za-z]:)/,'$1')});
  await page.getByRole('button',{name:'B系列',exact:true}).click();assert.equal(await page.locator('.shop-card').count(),33);
  await page.getByLabel('搜索商品或色号').fill('B32');assert.equal(await page.locator('.shop-card').count(),1);
  await page.locator('.shop-add').click();
  await page.getByRole('button',{name:/购物车/}).first().click();await page.getByText('小店暂未开放在线下单，购物车会为你保留。',{exact:true}).waitFor();
  assert.equal(await page.locator('.shop-bag-row').count(),1);await page.getByRole('button',{name:'继续逛逛',exact:true}).click();
  await page.getByRole('button',{name:'代拼/代烫服务',exact:true}).click();assert.equal(await page.locator('.shop-card').count(),2);
  await page.getByRole('button',{name:'在家拼豆',exact:true}).click();assert.equal(await page.getByLabel('搜索商品或色号').inputValue(),'B32');assert.equal(await page.locator('.shop-card').count(),1);
  await page.getByLabel('搜索商品或色号').fill('');assert.equal(await page.locator('.shop-card').count(),33);
  assert.equal(catalogRequests,1,'section/category switching must not refetch the catalog');
  for(const width of [390,320,844,2560]){await page.setViewportSize({width,height:844});await page.waitForTimeout(100);assert.equal(await page.evaluate(()=>document.documentElement.scrollWidth>innerWidth),false,'overflow at '+width);}
  await page.setViewportSize({width:390,height:844});await page.getByRole('button',{name:'A系列',exact:true}).click();
  await page.waitForFunction(()=>[...document.querySelectorAll('.shop-card img')].slice(0,4).every(e=>e.complete&&e.naturalWidth>0));
  await page.screenshot({path:new URL('shop-'+name+'-mobile.png',out).pathname.replace(/^\/([A-Za-z]:)/,'$1')});
  await page.reload();await page.locator('.shop-card').first().waitFor();await page.getByRole('button',{name:/购物车/}).first().click();assert.equal(await page.locator('.shop-bag-row').count(),1);await page.getByRole('button',{name:'移除',exact:true}).click();assert.equal(await page.locator('.shop-bag-row').count(),0);await page.getByRole('button',{name:'继续逛逛',exact:true}).click();
  await page.getByRole('button',{name:'我的订单',exact:true}).click();await page.getByText('暂无商品订单',{exact:true}).waitFor();await page.keyboard.press('Escape');
  await page.setViewportSize({width:1440,height:1000});await page.goto(base+'/manage?view=shop');await page.locator('.shop-admin-row').first().waitFor();
  await page.getByLabel('搜索商品或色号').fill('B32');await page.locator('.shop-admin-row').first().click();
  await page.getByLabel('中文名称',{exact:true}).fill('B32 QA '+name);
  await page.getByLabel('售价（CAD）',{exact:true}).fill('2.50');
  await page.locator('#shop-product-editor input[type=file]').setInputFiles([
   new URL('../../artifacts/shop-round-20260912/images/'+(await fs.readdir(new URL('images/',out)))[0],import.meta.url),
   new URL('../../artifacts/shop-round-20260912/images/'+(await fs.readdir(new URL('images/',out)))[1],import.meta.url)
  ].map(u=>u.pathname.replace(/^\/([A-Za-z]:)/,'$1')));
  await page.waitForFunction(()=>document.querySelectorAll('.shop-edit-photos img').length>=2);
  await page.getByRole('button',{name:'设为封面',exact:true}).first().click();
  await page.locator('button[form=shop-product-editor]').click();await page.waitForFunction(()=>!document.querySelector('#shop-product-editor')?.closest('dialog')?.open);
  assert.match(await page.locator('.shop-admin-row').first().innerText(),/2\.50/);
  await page.locator('.shop-admin-row').first().click();assert.equal(await page.getByLabel('中文名称',{exact:true}).inputValue(),'B32 QA '+name);assert.equal(await page.locator('.shop-edit-photos img').count(),2);await page.keyboard.press('Escape');
  await page.locator('.shop-admin .shop-tabs').getByRole('button',{name:'商品分类',exact:true}).click();await page.getByRole('button',{name:'增加分类/系列',exact:true}).click();
  await page.locator('#shop-category-editor').getByLabel('中文名称',{exact:true}).fill('测试系列 '+name);await page.locator('#shop-category-editor').getByLabel('英文名称',{exact:true}).fill('QA series '+name);await page.getByLabel('上级分类',{exact:true}).selectOption('refills');await page.locator('button[form=shop-category-editor]').click();await page.waitForFunction(()=>!document.querySelector('#shop-category-editor')?.closest('dialog')?.open);
  assert.ok((await page.locator('.shop-admin-categories').innerText()).includes('测试系列 '+name));
  await page.setViewportSize({width:390,height:844});await page.locator('.shop-admin .shop-tabs').getByRole('button',{name:'小店商品',exact:true}).click();await page.locator('.shop-admin-row').first().click();assert.equal(await page.evaluate(()=>document.documentElement.scrollWidth>innerWidth),false);
  await page.waitForFunction(()=>{const e=document.querySelector('.studio-drawer[open] .drawer-panel');return e&&e.getBoundingClientRect().top<30});
  await page.screenshot({path:new URL('shop-'+name+'-admin-mobile.png',out).pathname.replace(/^\/([A-Za-z]:)/,'$1')});
  assert.deepEqual(errors,[]);results.push({engine:name,passed:true,catalogRequestsBeforeReload:1,viewports:[320,390,844,1440,2560],flows:['categories','search','cart persistence','orders entry','services','product edit','multiple images','category create','mobile drawer']});
 } finally{await browser.close()}
}
await fs.writeFile(new URL('browser-verification.json',out),JSON.stringify(results,null,2));console.log(JSON.stringify(results));
