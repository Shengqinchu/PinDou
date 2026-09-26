import {chromium,expect} from '@playwright/test';
import fs from 'node:fs/promises';
import assert from 'node:assert/strict';
const dir='../artifacts/owner-workbench/ui';await fs.mkdir(dir,{recursive:true});
const browser=await chromium.launch({channel:'msedge',headless:true});
const results=[];const runId=Date.now().toString(36);
try{
 for(const viewport of (process.argv.includes('--native')?[]:[{width:1440,height:900},{width:390,height:844},{width:320,height:568},{width:844,height:390}])){
  const context=await browser.newContext({viewport,reducedMotion:'reduce'});
  await context.addInitScript(()=>{sessionStorage.setItem('puppy-studio-admin','local-qa');localStorage.setItem('puppy-studio-language','zh');});
  const page=await context.newPage(),errors=[];page.on('pageerror',e=>errors.push(e.message));
  await page.goto('http://127.0.0.1:5184/manage?view=finance');
  await expect(page.locator('.finance-panel h1')).toHaveText('营业状况');
  await page.getByRole('button',{name:'增加支出',exact:true}).click();
  await page.locator('.finance-form input[inputmode="decimal"]').fill('25.80');
  await page.getByRole('textbox',{name:'项目 1',exact:true}).fill('Local supplies '+viewport.width+'-'+runId);
  await page.getByRole('button',{name:'增加一项',exact:true}).click();
  await page.getByRole('textbox',{name:'项目 2',exact:true}).fill('Storage boxes');
  await page.getByRole('button',{name:'保存记录',exact:true}).click();
  await expect(page.locator('dialog[open]')).toHaveCount(0);
  await expect(page.locator('.finance-records')).toContainText('Local supplies '+viewport.width+'-'+runId);
  await page.locator('.finance-records tr').filter({hasText:'Local supplies '+viewport.width+'-'+runId}).getByRole('button',{name:'编辑记录'}).click();
  await page.locator('.finance-form input[inputmode="decimal"]').fill('29.90');
  await page.getByRole('button',{name:'保存记录',exact:true}).click();
  await expect(page.locator('dialog[open]')).toHaveCount(0);
  await expect(page.locator('.finance-records tr').filter({hasText:'Local supplies '+viewport.width+'-'+runId})).toContainText('29.90 CAD');
  assert(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth+2));
  await page.screenshot({path:`${dir}/web-finance-${viewport.width}x${viewport.height}.png`,fullPage:true});
  assert.deepEqual(errors,[]);results.push({surface:'web',viewport,expenseCreateEdit:true,noOverflow:true});
  await context.close();
 }
 for(const viewport of [{width:390,height:844},{width:320,height:568},{width:844,height:390}]){
  const context=await browser.newContext({viewport,reducedMotion:'reduce'});
  // Only fixture data from the loopback server. No live business reads or writes.
  await context.route('**/studio-api/**',async route=>{
    const request=route.request(),url=new URL(request.url());
    const response=await context.request.fetch('http://127.0.0.1:8011'+url.pathname+url.search,{method:request.method(),headers:{'Content-Type':'application/json',Authorization:'Bearer local-qa'},data:request.postData()||undefined});
    await route.fulfill({status:response.status(),headers:{'content-type':'application/json','access-control-allow-origin':'*'},body:await response.body()});
  });
  const page=await context.newPage(),errors=[];page.on('pageerror',e=>errors.push(e.message));
  const base='http://127.0.0.1:5186/h5/#/pages/studio/';
  for(const route of ['manage','manage-reservations','manage-messages','manage-finance','manage-members','manage-calendar']){
    await page.goto(base+route);
    await expect(page.locator('.admin-native')).toBeVisible();
    await expect(page.locator('.admin-loading')).toHaveCount(0,{timeout:15000});
    if(await page.locator('.admin-error').count())console.log({route,error:await page.locator('.admin-error').innerText()});
    await expect(page.locator('.admin-error')).toHaveCount(0);
    await expect(page.locator('.admin-native-content .admin-card').first()).toBeVisible();
    assert(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth+2),route+' overflow');
    const tabs=await page.locator('.admin-native-tabs').boundingBox();
    assert(tabs&&tabs.y+tabs.height<=viewport.height+2,JSON.stringify({route,viewport,tabs}));
    await page.screenshot({path:`${dir}/${route}-${viewport.width}x${viewport.height}.png`,fullPage:true});
  }
  await page.goto(base+'manage-finance-edit?kind=income');
  await expect(page.locator('.admin-native-content .admin-card')).toBeVisible();
  const inputs=page.locator('.admin-native-content .admin-input input');
  await inputs.nth(0).fill('42.50');
  await inputs.nth(1).fill('Native customer '+viewport.width);
  await inputs.nth(2).fill('Local beading session');
  await page.locator('uni-button').filter({hasText:/^现金$/}).click();
  await page.locator('.admin-native-actions uni-button').filter({hasText:/^保存记录$/}).click();
  await expect(page.locator('.admin-native-title')).toHaveText('编辑记录');
  assert(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth+2));
  await page.screenshot({path:`${dir}/native-income-${viewport.width}x${viewport.height}.png`,fullPage:true});
  await page.locator('.admin-language').click();
  await expect(page.locator('.admin-native-title')).toHaveText('Edit record');
  assert(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth+2));
  await page.locator('.admin-language').click();
  if(viewport.width===390){
    await page.goto(base+'manage-reservation?id=VIS-LOCAL-WORKSPACE-0');
    await expect(page.locator('.admin-native-content .admin-card').first()).toContainText('Local customer 0');
    await page.locator('.admin-native-content textarea').nth(0).fill('Edited on mobile');
    await page.locator('.admin-native-actions uni-button').filter({hasText:/^保存$/}).click();
    await page.locator('.uni-modal__btn_primary').click();
    await expect.poll(async()=>{
      const result=await(await context.request.get('http://127.0.0.1:8011/studio-api/manage/reservations?search=VIS-LOCAL-WORKSPACE-0')).json();
      return result.items[0].staff_note;
    }).toBe('Edited on mobile');
    await page.goto(base+'manage-member?id=qa-owner');
    await expect(page.locator('.admin-native-content textarea').first()).toHaveValue('Preserve this private note');
    await page.locator('.admin-native-content textarea').first().fill('Mobile private note');
    await page.locator('uni-button').filter({hasText:/^保存备注$/}).click();
    await expect.poll(async()=>{
      const result=await(await context.request.get('http://127.0.0.1:8011/studio-api/manage/members/qa-owner')).json();return result.account.staff_note;
    }).toBe('Mobile private note');
    const threads=await(await context.request.get('http://127.0.0.1:8011/studio-api/manage/messages/threads')).json();
    const thread=threads.items.find(t=>t.phone==='+14165550123');
    await page.goto(base+'manage-conversation?id='+thread.id);
    await expect(page.locator('.native-chat-content').first()).toBeVisible();
    await page.locator('.native-chat-composer textarea').fill('Native message '+runId);
    await page.locator('.native-chat-composer uni-button').filter({hasText:/^发送消息$/}).click();
    await expect(page.locator('.native-chat-content').last()).toHaveText('Native message '+runId);
    await expect(page.locator('.native-chat-composer textarea')).toHaveValue('');
    await page.screenshot({path:`${dir}/native-conversation-${viewport.width}x${viewport.height}.png`,fullPage:true});
  }
  await expect(page.locator('.admin-error')).toHaveCount(0);
  assert.deepEqual(errors,[]);results.push({surface:'native-h5-layout',viewport,incomeCreate:true,noOverflow:true});
  await context.close();
 }
 await fs.writeFile(`${dir}/checks.json`,JSON.stringify(results,null,2));console.log(JSON.stringify(results));
}finally{await browser.close();}
