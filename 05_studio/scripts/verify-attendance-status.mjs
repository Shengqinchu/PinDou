// Run against the disposable 06_studio/qa_attendance.py fixture.
import {chromium,webkit,expect} from '@playwright/test';
import assert from 'node:assert/strict';
import fs from 'node:fs/promises';
import {fileURLToPath} from 'node:url';
import wallet from '../src/content/wallet.json' with {type:'json'};
const out=new URL('../../artifacts/reservation-completion-20260912/',import.meta.url),results=[],errors=[];
const base='http://127.0.0.1:5184';
for(const [engine,type] of [['chromium',chromium],['webkit',webkit]]){
 const browser=await type.launch({headless:true});
 try{for(const [lang,viewport] of [['zh',{width:390,height:844}],['en',{width:1440,height:1000}]]){
  const ctx=await browser.newContext({viewport});
  await ctx.addInitScript(lang=>{sessionStorage.setItem('puppy-studio-admin','local-qa');localStorage.setItem('puppy-studio-language',lang);},lang);
  const page=await ctx.newPage();page.setDefaultTimeout(9000);page.on('pageerror',e=>errors.push(e.message));
  const api=async(path,method='GET',data)=>{const r=await ctx.request.fetch(base+'/studio-api'+path,{method,data});assert(r.ok(),await r.text());return r.json();};
  const seed=await api('/qa/completion-seed','POST'),payloads=[];
  page.on('request',r=>{if(r.method()==='PATCH'&&r.url().endsWith('/manage/reservations/'+seed.id))payloads.push(r.postDataJSON());});
  const dialog=page.locator('dialog[open]'),hours=dialog.getByLabel(wallet.actual_hours[lang==='zh'?0:1],{exact:true});
  const guests=dialog.getByLabel(wallet.actual_guests[lang==='zh'?0:1],{exact:true});
  const open=async()=>{await page.goto(base+'/manage?view=reservations&booking='+seed.id);await expect(dialog).toBeVisible();};
  const save=()=>dialog.getByRole('button',{name:lang==='zh'?'保存安排':'Save arrangement',exact:true}).click();
  await open();await expect(hours).toHaveCount(0);
  await dialog.locator('select').selectOption('confirmed');await save();await expect(dialog).toHaveCount(0);
  assert.equal(payloads.at(-1).actual_minutes,undefined);assert.equal(payloads.at(-1).actual_guests,undefined);
  await open();await dialog.locator('select').selectOption('completed');await expect(hours).toHaveValue('0');
  await save();await expect(dialog).toContainText(wallet.wallet_actual_hours_details_required[lang==='zh'?0:1]);
  assert.equal((await api('/manage/reservations?search='+seed.id)).items[0].status,'confirmed');
  await hours.fill('0.5');await save();await expect(dialog).toContainText(wallet.wallet_actual_hours_details_required[lang==='zh'?0:1]);
  await dialog.locator('select').selectOption('pending');await expect(hours).toHaveCount(0);await expect(dialog.locator('.desk-error')).toHaveCount(0);
  await save();await expect(dialog).toHaveCount(0);assert.equal(payloads.at(-1).actual_minutes,undefined);
  await open();await dialog.locator('select').selectOption('confirmed');await save();await expect(dialog).toHaveCount(0);
  await open();await dialog.locator('select').selectOption('completed');await hours.fill('0.5');await guests.fill('1');
  assert(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth+1));
  await page.screenshot({path:fileURLToPath(new URL(`web-${engine}-${lang}.png`,out))});
  await save();await expect(dialog).toHaveCount(0);
  const row=(await api('/manage/reservations?search='+seed.id)).items[0];assert.equal(row.actual_minutes,30);assert.equal(row.actual_guests,1);assert.equal(row.status,'completed');
  await open();await expect(hours).toHaveValue('0.5');await save();await expect(dialog).toHaveCount(0);
  results.push({engine,lang,viewport,confirmedWithoutAttendance:true,incompleteCompletionRejected:true,switchingClearsError:true,halfHourSaved:true,productionWrites:0});
  await ctx.close();
 }}finally{await browser.close();}
}
assert.deepEqual(errors,[]);
await fs.writeFile(new URL('web-verification.json',out),JSON.stringify({results,errors},null,2));
console.log(JSON.stringify({checks:results.length,errors}));
