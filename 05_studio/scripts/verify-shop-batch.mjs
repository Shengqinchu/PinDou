import { chromium,webkit } from 'playwright';
import fs from 'node:fs/promises';
import { stripTypeScriptTypes } from 'node:module';
import assert from 'node:assert/strict';
const out=new URL('../../artifacts/shop-bulk-20260912/',import.meta.url);
const sourceImages=new URL('../../artifacts/shop-round-20260912/images/',import.meta.url);
const originals=(await fs.readdir(sourceImages)).filter(n=>n.endsWith('.jpg'));
const buffers=await Promise.all(originals.slice(0,2).map(n=>fs.readFile(new URL(n,sourceImages))));
const helpers=await import('data:text/javascript;base64,'+Buffer.from(stripTypeScriptTypes(await fs.readFile(new URL('../src/shop-batch.ts',import.meta.url),'utf8'))).toString('base64'));
assert.equal(helpers.matchProductImage('A11_2.jpg',[{id:'a1',code:'A1'},{id:'a11',code:'A11'}]),'a11');
assert.equal(helpers.matchProductImage('A1.jpg',[{id:'a1',code:'A1'},{id:'a1-other',code:'A1'}]),'');
assert.equal(helpers.matchProductImage('A11.jpg',[{id:'a1',code:'A1'}]),'');
assert.equal(helpers.centsFromInput('0.29'),29);assert.throws(()=>helpers.centsFromInput('0.001'));
const results=[];
for(const [engineName,engine] of [['chromium',chromium],['webkit',webkit]]){
 const name=engineName+'-'+Date.now().toString(36);
 const browser=await engine.launch({headless:true});
 let tracePage;
 try{
  const c=await browser.newContext({viewport:{width:1440,height:1000},locale:'zh-CN'});
  await c.addInitScript(()=>{sessionStorage.setItem('puppy-studio-admin','local-qa');localStorage.setItem('puppy-studio-locale','zh')});
  const page=await c.newPage();tracePage=page;page.setDefaultTimeout(10000);const errors=[];page.on('pageerror',e=>errors.push(e.message));
  const getProducts=async()=>(await(await page.request.get('http://127.0.0.1:8011/studio-api/manage/shop')).json()).products;
  // Create a fresh group for each engine, so assertions never depend on earlier writes.
  for(const code of ['QA11','QA12','QA13','QA21','QA22']){
   const response=await page.request.put('http://127.0.0.1:8011/studio-api/manage/products/'+name+'-'+code.toLowerCase(),{data:{id:name+'-'+code.toLowerCase(),kind:'physical',category:'beads',zh:name+' '+code,en:name+' '+code,code,shop_collection:'home',shop_category_id:'refill-a',shop_visible:true,stock:7,version:1}});
   assert.equal(response.status(),200);
  }
  await page.goto('http://127.0.0.1:5184/manage?view=shop');await page.locator('.shop-admin-row').first().waitFor();
  await page.getByLabel('搜索商品或色号',{exact:true}).fill(name+' QA1');await page.getByLabel('图片状态',{exact:true}).selectOption('missing');
  await page.getByRole('checkbox',{name:'全选当前筛选结果',exact:true}).check();await page.getByRole('button',{name:'批量编辑',exact:true}).click();
  const panel=page.locator('.shop-bulk-editor');await panel.getByLabel('统一售价（CAD）',{exact:true}).fill('2.50');await panel.getByRole('button',{name:'填入所选商品',exact:true}).click();await panel.getByLabel('售价（CAD） · '+name+' QA12',{exact:true}).fill('3.00');
  await panel.locator('input[type=file]').setInputFiles([{name:'QA11.jpg',mimeType:'image/jpeg',buffer:buffers[0]},{name:'QA12_1.jpg',mimeType:'image/jpeg',buffer:buffers[0]},{name:'QA12_2.jpg',mimeType:'image/jpeg',buffer:buffers[1]},{name:'unknown.jpg',mimeType:'image/jpeg',buffer:buffers[1]}]);
  await page.getByRole('button',{name:'保存批量修改',exact:true}).click();await page.getByText('还有图片未匹配商品，请选择对应商品或移除文件。',{exact:true}).waitFor();
  assert.equal((await getProducts()).find(p=>p.id===name+'-qa11').price_cents,null);
  await panel.getByLabel('对应商品 · unknown.jpg',{exact:true}).selectOption(name+'-qa13');
  await page.getByRole('button',{name:'保存批量修改',exact:true}).click();await page.getByText('已更新 3 件商品',{exact:true}).waitFor({timeout:20000});await page.waitForFunction(()=>![...document.querySelectorAll('dialog')].some(d=>d.open));
  let products=await getProducts();let one=products.find(p=>p.id===name+'-qa11'),two=products.find(p=>p.id===name+'-qa12');
  assert.equal(one.price_cents,250);assert.equal(two.price_cents,300);assert.equal(one.stock,7);assert.equal(one.images.length,1);assert.equal(two.images.length,2);
  await page.getByLabel('图片状态',{exact:true}).selectOption('all');await page.getByLabel('搜索商品或色号',{exact:true}).fill(name+' QA2');await page.getByRole('checkbox',{name:'全选当前筛选结果',exact:true}).check();await page.getByRole('button',{name:'批量编辑',exact:true}).click();
  await panel.getByLabel('图片分配方式',{exact:true}).selectOption('shared');await panel.locator('input[type=file]').setInputFiles([{name:'shared.jpg',mimeType:'image/jpeg',buffer:buffers[0]}]);await page.getByRole('button',{name:'保存批量修改',exact:true}).click();await page.getByText('已更新 2 件商品',{exact:true}).waitFor();await page.waitForFunction(()=>![...document.querySelectorAll('dialog')].some(d=>d.open));
  products=await getProducts();assert.equal(products.find(p=>p.id===name+'-qa21').images.length,1);assert.equal(products.find(p=>p.id===name+'-qa22').images.length,1);
  await page.getByRole('checkbox',{name:'全选当前筛选结果',exact:true}).check();await page.getByRole('button',{name:'批量编辑',exact:true}).click();await panel.getByLabel('统一售价（CAD）',{exact:true}).fill('4.00');await panel.getByRole('button',{name:'填入所选商品',exact:true}).click();
  const concurrent=products.find(p=>p.id===name+'-qa22');assert.equal((await page.request.put('http://127.0.0.1:8011/studio-api/manage/products/'+concurrent.id,{data:{...concurrent,price_cents:999}})).status(),200);
  await page.getByRole('button',{name:'保存批量修改',exact:true}).click();await page.getByText('有商品已被其他操作更新，本次没有保存任何商品。请重新打开批量编辑后再试。',{exact:true}).waitFor();products=await getProducts();assert.equal(products.find(p=>p.id===name+'-qa21').price_cents,null);assert.equal(products.find(p=>p.id===name+'-qa22').price_cents,999);
  await page.keyboard.press('Escape');await page.waitForFunction(()=>![...document.querySelectorAll('dialog')].some(d=>d.open));await page.getByRole('button',{name:'批量编辑',exact:true}).click();await panel.waitFor({state:'visible'});assert.equal(await panel.getByLabel('售价（CAD） · '+name+' QA22',{exact:true}).inputValue(),'9.99');await page.keyboard.press('Escape');await page.getByRole('button',{name:'清除选择',exact:true}).click();
  await page.getByLabel('搜索商品或色号',{exact:true}).fill(name+' QA12');await page.locator('.shop-admin-row').first().click();await page.getByLabel('售价（CAD）',{exact:true}).fill('3.50');await page.locator('#shop-product-editor').getByRole('button',{name:'移除',exact:true}).first().click();await page.locator('button[form=shop-product-editor]').click();await page.waitForFunction(()=>!document.querySelector('#shop-product-editor')?.closest('dialog')?.open);
  two=(await getProducts()).find(p=>p.id===name+'-qa12');assert.equal(two.price_cents,350);assert.equal(two.images.length,1);
  await page.getByRole('checkbox',{name:'全选当前筛选结果',exact:true}).check();await page.getByRole('button',{name:'批量编辑',exact:true}).click();
  for(const width of [390,320,844]){await page.setViewportSize({width,height:844});await page.waitForTimeout(450);assert.equal(await page.evaluate(()=>document.documentElement.scrollWidth>innerWidth),false);assert.equal(await panel.evaluate(e=>e.scrollWidth>e.clientWidth+1),false);}
  await page.setViewportSize({width:390,height:844});await page.waitForTimeout(400);await page.screenshot({path:new URL(name+'-batch-mobile.png',out).pathname.replace(/^\/([A-Za-z]:)/,'$1')});
  assert.deepEqual(errors,[]);results.push({engine:engineName,passed:true,checks:['uniform and per-row pricing','filename matching and manual mapping','unmatched files blocked','shared photos','version conflict rollback','single edit after batch','mobile reflow']});
 }catch(e){if(tracePage){await fs.writeFile(new URL(engineName+'-failure.txt',out),(await tracePage.locator('body').innerText())+'\n'+JSON.stringify(await tracePage.locator('dialog').evaluateAll(es=>es.map(e=>({open:e.open,phase:e.dataset.phase,text:e.textContent.slice(-160)})))));await tracePage.screenshot({path:new URL(engineName+'-failure.png',out).pathname.replace(/^\/([A-Za-z]:)/,'$1')});}throw e;}finally{await browser.close()}
}
await fs.writeFile(new URL('browser-tests.json',out),JSON.stringify(results,null,2));console.log(JSON.stringify(results));
