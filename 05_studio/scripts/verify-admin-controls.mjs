// Isolated qa_server.py only; never use production accounts or balances.
import {chromium,webkit,expect} from '@playwright/test';
import assert from 'node:assert/strict';
import fs from 'node:fs/promises';
import {fileURLToPath} from 'node:url';
const base='http://127.0.0.1:4184',out=new URL('../../artifacts/admin-controls/browser/',import.meta.url);
await fs.mkdir(out,{recursive:true});
const results=[];
for(const [engineName,engine] of [['chromium',chromium],['webkit',webkit]]){
 const browser=await engine.launch({headless:true,ignoreDefaultArgs:['--hide-scrollbars']});
 try{for(const [lang,width,height] of [['zh',1440,900],['en',390,844]]){
  const tag=engineName+'-'+lang+'-'+Date.now().toString(36),owner='qa-email-'+tag;
  const ctx=await browser.newContext({viewport:{width,height},locale:lang==='zh'?'zh-CN':'en-CA',reducedMotion:'reduce'});
  await ctx.addInitScript(({lang,owner})=>{sessionStorage.setItem('puppy-studio-admin','local-qa');localStorage.setItem('puppy-studio-locale',lang);localStorage.setItem('pd_web_token',owner);},{lang,owner});
  const page=await ctx.newPage(),errors=[];page.on('pageerror',e=>errors.push(e.message));page.setDefaultTimeout(15000);
  const word=(zh,en)=>lang==='zh'?zh:en;
  const get=async path=>{const r=await page.request.get(base+'/studio-api'+path);assert.equal(r.status(),200);return r.json();};
  const mutate=async(path,data,method='post')=>{const r=await page.request[method](base+'/studio-api'+path,{data,headers:{'Idempotency-Key':crypto.randomUUID()}});assert.equal(r.status(),200,await r.text());return r.json();};
  let r=await page.request.get(base+'/studio-api/auth/me',{headers:{Authorization:'Bearer '+owner}});assert.equal(r.status(),200);
  let wallet=await get('/manage/members/'+owner);
  for(const [kind,minutes_delta,points_delta,note] of [['topup',600,0,'QA reversible top-up'],['gift',0,166,'QA additional points']]){
   wallet=await mutate('/manage/members/'+owner+'/transactions',{version:wallet.account.version,kind,minutes_delta,points_delta,note,effective_date:'2026-09-07'});
  }
  await page.goto(base+'/manage?view=members');
  await page.locator('.member-row').filter({hasText:owner+'@example.test'}).click();
  const dialog=()=>page.locator('dialog[open]');
  await expect(dialog().locator('.wallet-balance.points small')).toHaveText(word('可抵扣 CAD 3.32','Redeemable: CAD 3.32'));
  const original=dialog().locator('.wallet-ledger>li').filter({hasText:'QA reversible top-up'});
  await original.getByRole('button',{name:word('撤销这笔','Reverse entry'),exact:true}).click();
  const form=dialog().locator('.wallet-form');await expect(form).toBeFocused();await expect(form).toBeInViewport({ratio:.15});
  await page.screenshot({path:fileURLToPath(new URL(tag+'-reverse.png',out))});
  await form.getByLabel(word('记账说明（顾客可见）','Entry note (visible to guest)'),{exact:true}).fill('QA reversal verified');
  await form.getByRole('button',{name:word('保存并同步给顾客','Save and sync with guest'),exact:true}).click();
  await expect(dialog().locator('.wallet-saved')).toBeVisible();
  assert.equal((await get('/manage/members/'+owner)).account.minutes,0);
  await dialog().getByRole('button',{name:word('登记一笔','Record an entry'),exact:true}).click();
  await dialog().getByRole('combobox',{name:word('记账类型','Entry type'),exact:true}).selectOption('redeem');
  await dialog().getByRole('button',{name:word('使用全部积分','Use all points'),exact:true}).click();
  await expect(dialog().getByLabel(word('抵扣金额（CAD）','Amount to redeem (CAD)'),{exact:true})).toHaveValue('3.32');
  await dialog().getByLabel(word('本次可抵扣消费金额（CAD）','Eligible bill amount (CAD)'),{exact:true}).fill('3.32');
  await dialog().getByRole('checkbox',{name:word('确认本单未使用其他优惠活动','I confirm this bill does not use another promotional offer')}).check();
  await dialog().getByLabel(word('记账说明（顾客可见）','Entry note (visible to guest)'),{exact:true}).fill('QA all points');
  await page.screenshot({path:fileURLToPath(new URL(tag+'-points.png',out))});
  // Commit once, drop the response, then retry the exact operation.
  await page.route('**/manage/members/'+owner+'/transactions',async route=>{await route.fetch();await route.fulfill({status:503,contentType:'application/json',body:'{"detail":"server_error"}'});});
  await dialog().getByRole('button',{name:word('保存并同步给顾客','Save and sync with guest'),exact:true}).click();
  await expect(dialog().locator('.wallet-uncertain')).toBeVisible();
  await page.unroute('**/manage/members/'+owner+'/transactions');
  await dialog().getByRole('button',{name:word('重试这笔记账','Retry this entry'),exact:true}).click();
  await expect(dialog().locator('.wallet-balance.points strong')).toHaveText('0');
  wallet=await get('/manage/members/'+owner);
  assert.equal(wallet.entries.filter(e=>e.note==='QA all points').length,1);
  assert.equal(wallet.entries[0].points_delta,-332);
  // Removal is reversible and keeps all historical financial entries.
  const entries=wallet.entries;
  await dialog().getByRole('button',{name:word('删除顾客账户','Delete guest account'),exact:true}).click();
  await expect(dialog()).toHaveCount(1);
  await dialog().getByRole('button',{name:word('确认删除','Confirm deletion'),exact:true}).click();
  await expect(page.locator('.member-row').filter({hasText:owner+'@example.test'})).toHaveCount(0);
  await page.getByRole('button',{name:word('已删除账户','Deleted accounts'),exact:true}).click();
  await page.locator('.member-row').filter({hasText:owner+'@example.test'}).click();
  assert.deepEqual((await get('/manage/members/'+owner)).entries,entries);
  await dialog().getByRole('button',{name:word('恢复顾客账户','Restore guest account'),exact:true}).click();
  await dialog().getByRole('button',{name:word('确认恢复','Confirm restore'),exact:true}).click();
  await expect(dialog()).toHaveCount(0);
  assert.equal((await get('/manage/members/'+owner)).account.deleted_at,null);
  // Customer response and wording remain in whole CAD.
  const customer=await page.request.get(base+'/studio-api/auth/wallet',{headers:{Authorization:'Bearer '+owner}});
  assert.equal((await customer.json()).account.redeemable_cad,0);
  // Seed two local products and exercise the actual bulk deletion UI.
  for(const index of [1,2])await mutate('/manage/products/'+tag+'-'+index,{id:tag+'-'+index,kind:'physical',category:'beads',shop_collection:'home',shop_category_id:'refill-a',zh:tag+' '+index,en:tag+' '+index,price_cents:299,stock:8,shop_visible:true},'put');
  await page.goto(base+'/manage?view=shop');
  await page.getByLabel(word('搜索商品或色号','Search products or colour codes'),{exact:true}).fill(tag);
  await expect(page.locator('.shop-admin-row')).toHaveCount(2);
  await page.getByRole('checkbox',{name:word('全选当前筛选结果','Select filtered products'),exact:true}).check();
  await page.getByRole('button',{name:word('删除所选','Delete selected'),exact:true}).click();
  await expect(dialog().locator('.archive-items li')).toHaveCount(2);
  await page.screenshot({path:fileURLToPath(new URL(tag+'-delete-products.png',out))});
  await dialog().getByRole('button',{name:word('取消','Cancel'),exact:true}).click();
  await expect(page.locator('.shop-admin-row')).toHaveCount(2);
  await page.getByRole('button',{name:word('删除所选','Delete selected'),exact:true}).click();
  await dialog().getByRole('button',{name:word('确认删除','Confirm deletion'),exact:true}).click();
  await expect(page.locator('.shop-admin-row')).toHaveCount(0);
  await page.getByRole('button',{name:word('已删除商品','Deleted products'),exact:true}).click();
  await expect(page.locator('.shop-admin-row')).toHaveCount(2);
  await page.getByRole('checkbox',{name:word('全选当前筛选结果','Select filtered products'),exact:true}).check();
  await page.getByRole('button',{name:word('恢复所选','Restore selected'),exact:true}).click();
  await dialog().getByRole('button',{name:word('确认恢复','Confirm restore'),exact:true}).click();
  await expect(page.locator('.shop-admin-row')).toHaveCount(0);
  await page.getByRole('button',{name:word('当前商品','Current products'),exact:true}).click();
  await expect(page.locator('.shop-admin-row')).toHaveCount(2);
  assert.equal(await page.evaluate(()=>document.documentElement.scrollWidth>innerWidth+1),false);
  assert.deepEqual(errors,[]);
  results.push({engine:engineName,lang,width,reversalVisible:true,exactPoints:332,lostResponseRetry:true,memberRestore:true,productBatchRestore:true,noOverflow:true});
  await fs.writeFile(new URL('results.json',out),JSON.stringify(results,null,2));
  console.log(JSON.stringify(results.at(-1)));await ctx.close();
 }}finally{await browser.close();}
}
