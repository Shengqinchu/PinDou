// All writes use the isolated local QA database and fictional customer.
import {chromium,webkit,expect} from '@playwright/test';
import assert from 'node:assert/strict';
import fs from 'node:fs/promises';
import {fileURLToPath} from 'node:url';
import wallet from '../src/content/wallet.json' with {type:'json'};
const base='http://127.0.0.1:5184',out=new URL('../../artifacts/hour-units/',import.meta.url),results=[],errors=[];
for(const [engine,type] of [['chromium',chromium],['webkit',webkit]]){
 const browser=await type.launch({headless:true});
 try{for(const lang of ['zh','en']){
  const index=lang==='zh'?0:1,word=key=>wallet[key][index];
  const ctx=await browser.newContext({viewport:{width:1440,height:1000}});
  await ctx.addInitScript(lang=>{sessionStorage.setItem('puppy-studio-admin','local-qa');localStorage.setItem('puppy-studio-language',lang);},lang);
  const page=await ctx.newPage();page.setDefaultTimeout(9000);page.on('pageerror',e=>errors.push(e.message));
  const api=async(path,method='GET',data)=>{const r=await page.request.fetch(base+'/studio-api'+path,{method,data});assert(r.ok(),`${path}: ${r.status()} ${await r.text()}`);return r.json();};
  const seed=await api('/qa/attended-visit','POST');
  let row=(await api('/manage/reservations?search='+seed.id)).items[0];
  await api('/manage/reservations/'+seed.id,'PATCH',{version:row.version,status:'confirmed',actual_minutes:90,actual_guests:2,staff_note:'',public_note:''});
  const openBooking=async()=>{await page.goto(base+'/manage?view=reservations&booking='+seed.id);await expect(page.locator('dialog[open]')).toBeVisible();};
  const dialog=()=>page.locator('dialog[open]');
  await openBooking();await expect(dialog().getByLabel(word('actual_hours'),{exact:true})).toHaveCount(0);await dialog().locator('select').selectOption('completed');await expect(dialog().getByLabel(word('actual_hours'),{exact:true})).toHaveValue('1.5');
  for(const [width,height] of [[320,568],[390,844],[844,390],[1440,1000]]){
   await page.setViewportSize({width,height});assert(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth+1));
   assert((await dialog().getByLabel(word('actual_hours'),{exact:true}).getAttribute('inputmode'))==='decimal');
   if(engine==='chromium'&&lang==='zh'&&width===390)await page.screenshot({path:fileURLToPath(new URL('web-hours-390.png',out))});
  }
  await dialog().getByLabel(word('actual_hours'),{exact:true}).fill('0.5');
  await dialog().locator('select').selectOption('completed');
  await dialog().getByRole('button',{name:lang==='zh'?'保存安排':'Save arrangement',exact:true}).click();await expect(dialog()).toHaveCount(0);
  row=(await api('/manage/reservations?search='+seed.id)).items[0];assert.equal(row.actual_minutes,30);
  const rewardPoints=(await api('/manage/members/qa-owner')).account.points;
  await openBooking();await expect(dialog().getByLabel(word('actual_hours'),{exact:true})).toHaveValue('0.5');
  await dialog().getByLabel(word('actual_hours'),{exact:true}).fill('0.001');
  await dialog().getByRole('button',{name:lang==='zh'?'保存安排':'Save arrangement',exact:true}).click();await expect(dialog()).toContainText(word('wallet_actual_hours_details_required'));
  assert.equal((await api('/manage/reservations?search='+seed.id)).items[0].actual_minutes,30);
  await dialog().getByLabel(word('actual_hours'),{exact:true}).fill('1.5');await dialog().getByRole('button',{name:lang==='zh'?'保存安排':'Save arrangement',exact:true}).click();await expect(dialog()).toHaveCount(0);
  assert.equal((await api('/manage/reservations?search='+seed.id)).items[0].actual_minutes,90);
  assert.equal((await api('/manage/members/qa-owner')).account.points,rewardPoints);
  results.push({engine,lang,test:'legacy 90m displays 1.5h, 0.5h saves 30m, invalid value rejected, no repeat attendance reward'});

  await page.goto(base+'/manage?view=members&member=qa-owner');await expect(dialog().locator('.wallet-new')).toBeVisible();
  const initial=(await api('/manage/members/qa-owner')).account.minutes;
  async function entry(kind,hours,note){
   await dialog().getByRole('button',{name:word('transaction'),exact:true}).click();
   await dialog().locator('.wallet-form select').first().selectOption(kind);
   await dialog().getByLabel(word('time_hours'),{exact:true}).fill(hours);
   await dialog().getByLabel(word('reason'),{exact:true}).fill(note);
  }
  const save=()=>dialog().getByRole('button',{name:word('save'),exact:true}).click();
  await entry('topup','0.5','Half-hour QA topup');await save();await expect(dialog().locator('.wallet-saved')).toBeVisible();
  assert.equal((await api('/manage/members/qa-owner')).account.minutes,initial+30);
  await entry('usage','0.5','Half-hour QA usage');await save();await expect(dialog().locator('.wallet-saved')).toBeVisible();
  assert.equal((await api('/manage/members/qa-owner')).account.minutes,initial);
  await entry('gift','0.5','Half-hour uncertain '+engine+lang);
  await page.route('**/studio-api/manage/members/qa-owner/transactions',async route=>{await route.fetch();await route.fulfill({status:503,contentType:'application/json',body:'{"detail":"server_error"}'});});
  await save();await expect(dialog().locator('.wallet-uncertain')).toBeVisible();
  await page.unroute('**/studio-api/manage/members/qa-owner/transactions');await page.reload();
  await dialog().getByRole('button',{name:word('retry'),exact:true}).click();await expect(dialog().locator('.wallet-saved')).toBeVisible();
  assert.equal((await api('/manage/members/qa-owner')).account.minutes,initial+30);
  results.push({engine,lang,test:'0.5h topup and debit; uncertain retry keeps original 30m and cannot double-convert or double-credit'});
  await ctx.close();
 }}finally{await browser.close();}
}
assert.deepEqual(errors,[]);await fs.writeFile(new URL('web-verification.json',out),JSON.stringify({results,errors,productionWrites:0},null,2));console.log(JSON.stringify({checks:results.length,errors}));
