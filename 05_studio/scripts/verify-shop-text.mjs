// Local fixture only. Long strings and draft validation must never touch production.
import {chromium,webkit} from '@playwright/test';
import assert from 'node:assert/strict';
import fs from 'node:fs/promises';
import {fileURLToPath} from 'node:url';
const base='http://127.0.0.1:4184';
const out=new URL('../../artifacts/shop-text-20260912/',import.meta.url);
const zh=('第一段：拼豆服务说明。\n第二段：保留换行和详细规则。\n').repeat(500).slice(0,9995)+'中文结尾标';
const en=('First paragraph: bead instructions.\nSecond paragraph stays on a new line.\n'+ 'x'.repeat(220)+'\n').repeat(70).slice(0,9994)+'EN-END';
assert.equal(zh.length,10000);assert.equal(en.length,10000);
const results=[];
for(const [name,engine] of [['chromium',chromium],['webkit',webkit]]){
 const browser=await engine.launch({headless:true});
 try{
  const context=await browser.newContext({viewport:{width:1440,height:1000},reducedMotion:'reduce'});
  await context.addInitScript(()=>{localStorage.setItem('puppy-studio-language','zh');sessionStorage.setItem('puppy-studio-admin','local-qa')});
  const page=await context.newPage(),errors=[];page.on('pageerror',e=>errors.push(e.message));
  await page.goto(base+'/manage?view=shop');await page.locator('.shop-admin-row').first().waitFor();
  await page.getByLabel('搜索商品或色号',{exact:true}).fill('长文字测试');
  await page.locator('.shop-admin-row').first().click();
  const form=page.locator('#shop-product-editor');
  const zhInput=form.getByLabel('中文介绍',{exact:true}),enInput=form.getByLabel('英文介绍',{exact:true});
  assert.equal(await enInput.getAttribute('maxlength'),null);
  await enInput.fill(en+'X');
  assert.equal((await enInput.inputValue()).length,10001);
  assert.ok(await page.locator('button[form=shop-product-editor]').isDisabled());
  await form.getByRole('alert').filter({hasText:'10000'}).waitFor();
  await zhInput.fill(zh);await enInput.fill(en);
  assert.ok(!(await page.locator('button[form=shop-product-editor]').isDisabled()));
  await page.locator('button[form=shop-product-editor]').click();
  await page.waitForFunction(()=>!document.querySelector('#shop-product-editor')?.closest('dialog')?.open);
  await page.locator('.shop-admin-row').first().click();
  assert.equal(await zhInput.inputValue(),zh);assert.equal(await enInput.inputValue(),en);
  await page.keyboard.press('Escape');
  await page.goto(base+'/shop');await page.locator('.shop-root').first().waitFor();
  await page.locator('.shop-root').filter({hasText:'拼豆套装'}).click();
  await page.locator('.shop-search input').fill('长文字测试');
  assert.equal(await page.locator('.shop-card').count(),1);
  await page.getByRole('button',{name:'查看完整介绍',exact:true}).click();
  await page.locator('dialog[data-phase="open"] .shop-description').waitFor();
  assert.equal(await page.locator('.shop-description').textContent(),zh);
  for(const width of [320,390,1440]){
   await page.setViewportSize({width,height:844});
   const measured=await page.locator('.shop-description').evaluate(e=>({whiteSpace:getComputedStyle(e).whiteSpace,wrap:getComputedStyle(e).overflowWrap,overflow:e.scrollWidth>e.clientWidth+1}));
   assert.equal(measured.whiteSpace,'pre-wrap');assert.equal(measured.wrap,'anywhere');assert.equal(measured.overflow,false);
   assert.equal(await page.evaluate(()=>document.documentElement.scrollWidth>innerWidth),false);
  }
  await page.keyboard.press('Escape');
  await page.locator('.language-button').click();
  await page.getByRole('button',{name:'Read full description',exact:true}).click();
  await page.locator('dialog[data-phase="open"] .shop-description').waitFor();
  assert.equal(await page.locator('.shop-description').textContent(),en);
  await page.setViewportSize({width:390,height:844});
  const tail=await page.locator('.shop-description').evaluate(e=>{
   const body=e.closest('.drawer-body');body.scrollTop=body.scrollHeight;
   const node=e.firstChild,range=document.createRange();range.setStart(node,node.textContent.length-6);range.setEnd(node,node.textContent.length);
   const r=range.getBoundingClientRect(),b=body.getBoundingClientRect();return {text:range.toString(),visible:r.top>=b.top&&r.bottom<=b.bottom};
  });
  assert.deepEqual(tail,{text:'EN-END',visible:true});
  await page.screenshot({path:fileURLToPath(new URL('full-text-'+name+'-mobile.png',out))});
  const data=await (await context.request.get(base+'/studio-api/manage/shop')).json();
  const product=data.products.find(p=>p.id==='qa-long-copy');
  const fresh=en.slice(0,9970)+'\nUPDATED-FROM-ANOTHER-TAB';
  const update=await context.request.put(base+'/studio-api/manage/products/qa-long-copy',{data:{...product,detailEn:fresh}});assert.equal(update.status(),200);
  await page.evaluate(()=>window.dispatchEvent(new Event('focus')));
  await page.waitForFunction(text=>document.querySelector('.shop-description')?.textContent===text,fresh);
  assert.equal(await page.locator('.shop-search input').inputValue(),'长文字测试');
  assert.equal(await page.locator('.shop-card').count(),1);
  assert.deepEqual(errors,[]);
  results.push({engine:name,passed:true,charactersPerLanguage:10000,overLimitPastePreserved:10001,fullTailVisible:true,widths:[320,390,1440],newlines:true,longWordsWrap:true,focusRefreshKeepsFilter:true});
 }finally{await browser.close()}
}
await fs.writeFile(new URL('browser-verification.json',out),JSON.stringify(results,null,2));console.log(JSON.stringify(results));
