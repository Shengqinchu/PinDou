import {chromium,expect} from '@playwright/test';
import assert from 'node:assert/strict';
import fs from 'node:fs/promises';
const dir='../artifacts/finance-currency/ui';await fs.mkdir(dir,{recursive:true});
const browser=await chromium.launch({channel:'msedge',headless:true}),results=[];
const runId=Date.now();
try{
 for(const viewport of [{width:1440,height:900},{width:390,height:844},{width:320,height:568},{width:844,height:390}]){
  const context=await browser.newContext({viewport,reducedMotion:'reduce'});
  await context.addInitScript(()=>{sessionStorage.setItem('puppy-studio-admin','local-qa');localStorage.setItem('puppy-studio-locale','zh');});
  const page=await context.newPage(),errors=[];page.on('pageerror',e=>errors.push(e.message));
  await page.goto('http://127.0.0.1:5184/manage?view=finance');
  await expect(page.locator('.finance-panel h1')).toHaveText('营业状况');
  await page.getByRole('button',{name:'增加收入',exact:true}).click();
  const form=page.locator('.finance-form').first();
  await form.getByLabel('收款方式',{exact:true}).selectOption('wechat_alipay');
  await expect(form.locator('label').filter({has:page.locator('input[inputmode="decimal"]')})).toContainText('RMB');
  await form.getByLabel('收款方式',{exact:true}).selectOption('transfer');
  await expect(form.locator('label').filter({has:page.locator('input[inputmode="decimal"]')})).toContainText('CAD');
  await form.getByLabel('收款方式',{exact:true}).selectOption('wechat_alipay');
  await form.locator('input[inputmode="decimal"]').fill('100.00');
  const name=`Currency web ${viewport.width} ${runId}`;
  await form.getByLabel('客户名称',{exact:true}).fill(name);
  await form.getByRole('textbox',{name:'项目 1',exact:true}).fill('Local RMB receipt');
  await expect(form.locator('.finance-fx')).toContainText('1 RMB =',{timeout:12000});
  assert(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth+2));
  await page.screenshot({path:`${dir}/web-editor-${viewport.width}x${viewport.height}.png`});
  await form.getByRole('button',{name:'保存记录',exact:true}).click();
  await expect(page.locator('dialog[open]')).toHaveCount(0);
  const row=page.locator('.finance-records tr').filter({hasText:name});
  await expect(row).toContainText('100.00 RMB');await expect(row).toContainText('微信/支付宝');await expect(row.locator('.finance-converted')).toContainText('CAD');
  await page.getByRole('button',{name:'增加支出',exact:true}).click();
  await form.getByLabel('币种',{exact:true}).selectOption('CNY');
  await form.locator('input[inputmode="decimal"]').fill('25.80');
  await form.getByRole('textbox',{name:'项目 1',exact:true}).fill(`Currency supplies ${viewport.width} ${runId}`);
  await expect(form.locator('.finance-fx')).toContainText('1 RMB =');
  await form.getByRole('button',{name:'保存记录',exact:true}).click();await expect(page.locator('dialog[open]')).toHaveCount(0);
  await expect(page.locator('.finance-records tr').filter({hasText:`Currency supplies ${viewport.width} ${runId}`})).toContainText('25.80 RMB');
  await expect(page.locator('.finance-totals')).not.toContainText('RMB');
  assert(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth+2));
  await page.screenshot({path:`${dir}/web-list-${viewport.width}x${viewport.height}.png`});
  assert.deepEqual(errors,[]);results.push({surface:'web',viewport,paymentCurrency:true,rmbIncomeExpense:true,cadTotals:true,noOverflow:true});await context.close();
 }
 for(const viewport of [{width:390,height:844},{width:320,height:568},{width:844,height:390}]){
  const context=await browser.newContext({viewport,reducedMotion:'reduce'});let quoteFails=false;
  await context.route('**/studio-api/**',async route=>{
   const request=route.request(),url=new URL(request.url());
   if(quoteFails&&url.pathname.endsWith('/finance/exchange-rate')){await route.fulfill({status:503,contentType:'application/json',body:JSON.stringify({detail:'finance_rate_unavailable'})});return;}
   const response=await context.request.fetch('http://127.0.0.1:8011'+url.pathname+url.search,{method:request.method(),headers:{'Content-Type':'application/json',Authorization:'Bearer local-qa'},data:request.postData()||undefined});
   await route.fulfill({status:response.status(),headers:{'content-type':'application/json','access-control-allow-origin':'*'},body:await response.body()});
  });
  const page=await context.newPage(),errors=[];page.on('pageerror',e=>errors.push(e.message));
  await page.goto('http://127.0.0.1:5186/h5/#/pages/studio/manage-finance-edit?kind=income');
  await expect(page.locator('.admin-native-content .admin-card').first()).toBeVisible();
  const inputs=page.locator('.admin-native-content .admin-input input'),name=`Currency native ${viewport.width} ${runId}`;
  await inputs.nth(0).fill('100.00');await inputs.nth(1).fill(name);await inputs.nth(2).fill('Local RMB session');
  const pick=text=>page.locator('.admin-filters uni-button').filter({hasText:new RegExp('^'+text+'$')}).click();
  await pick('微信/支付宝');await expect(page.locator('.admin-label').filter({hasText:'金额'})).toContainText('RMB');
  await expect(page.locator('.admin-native-content')).toContainText('1 RMB =',{timeout:12000});
  await pick('EMT');await expect(page.locator('.admin-label').filter({hasText:'金额'})).toContainText('CAD');
  quoteFails=true;await pick('微信/支付宝');await expect(page.locator('.admin-error')).toContainText('汇率');
  await expect(inputs.nth(0)).toHaveValue('100.00');await expect(inputs.nth(1)).toHaveValue(name);
  quoteFails=false;await page.locator('.admin-native-content uni-button').filter({hasText:/^刷新$/}).click();
  await expect(page.locator('.admin-error')).toHaveCount(0);
  await expect(page.locator('.admin-native-content')).toContainText('1 RMB =');
  assert(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth+2));
  const buttons=page.locator('.admin-native-actions uni-button');
  await expect(buttons.first()).not.toHaveAttribute('disabled');
  await page.screenshot({path:`${dir}/native-editor-${viewport.width}x${viewport.height}.png`});
  await buttons.filter({hasText:/^保存记录$/}).click();await expect(page.locator('.admin-native-title')).toHaveText('编辑记录');
  await page.locator('.admin-native-tabs uni-button').filter({hasText:/^营业状况$/}).click();
  const current=page.locator('uni-page').filter({visible:true}).last();
  await expect(current.locator('.native-finance-entry').filter({hasText:name})).toContainText('100.00 RMB');
  await expect(current.locator('.native-finance-entry').filter({hasText:name})).toContainText('CAD');
  await expect(current.locator('.native-finance-totals')).not.toContainText('RMB');
  assert(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth+2));
  await page.screenshot({path:`${dir}/native-list-${viewport.width}x${viewport.height}.png`});
  assert.deepEqual(errors,[]);results.push({surface:'native-h5',viewport,paymentCurrency:true,rateFailureRetainsInput:true,rmbReceipt:true,cadTotals:true,noOverflow:true});await context.close();
 }
 await fs.writeFile(`${dir}/checks.json`,JSON.stringify(results,null,2));console.log(JSON.stringify(results));
}finally{await browser.close();}
