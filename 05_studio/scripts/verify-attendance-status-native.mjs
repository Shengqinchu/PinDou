// Native page source rendered as H5; requests stay in the disposable loopback QA DB.
import {chromium,expect} from '@playwright/test';
import assert from 'node:assert/strict';
import fs from 'node:fs/promises';
import {fileURLToPath} from 'node:url';
import wallet from '../src/content/wallet.json' with {type:'json'};
const browser=await chromium.launch({headless:true}),out=new URL('../../artifacts/reservation-completion-20260912/',import.meta.url),results=[];
try{for(const viewport of [{width:390,height:844},{width:320,height:568},{width:844,height:390}]){
 const ctx=await browser.newContext({viewport}),errors=[],payloads=[];
 await ctx.route('**/studio-api/**',async route=>{const r=route.request(),u=new URL(r.url());if(r.method()==='POST'&&u.pathname.includes('/manage/reservations/')&&u.pathname.endsWith('/update'))payloads.push(r.postDataJSON());const response=await ctx.request.fetch('http://127.0.0.1:8011'+u.pathname+u.search,{method:r.method(),headers:{'Content-Type':'application/json',Authorization:'Bearer local-qa'},data:r.postData()||undefined});await route.fulfill({status:response.status(),contentType:'application/json',body:await response.body()});});
 await ctx.route('**/api/v1/**',route=>route.fulfill({json:{user_id:'qa-owner',nickname:'QA',role:'admin'}}));
 const api=async(path,method='GET')=>{const r=await ctx.request.fetch('http://127.0.0.1:8011/studio-api'+path,{method,headers:{Authorization:'Bearer local-qa'}});assert(r.ok(),await r.text());return r.json();};
 const seed=await api('/qa/completion-seed','POST'),page=await ctx.newPage();page.setDefaultTimeout(9000);page.on('pageerror',e=>errors.push(e.message));
 await page.goto('http://127.0.0.1:5190/h5/#/pages/studio/manage-reservation?id='+seed.id);
 await expect(page.locator('uni-picker .admin-input')).toHaveText('待确认');
 const hours=page.locator('.admin-field').filter({hasText:wallet.actual_hours[0]}).locator('input');
 const guests=page.locator('.admin-field').filter({hasText:wallet.actual_guests[0]}).locator('input');
 const select=async text=>{await page.locator('uni-picker').click();const option=page.locator('uni-picker-view .uni-picker-item:visible').filter({hasText:text}).first();await expect.poll(async()=>{const b=await option.boundingBox();return !!b&&b.y>=0&&b.y+b.height<=viewport.height;}).toBe(true);await option.click({force:true});await page.locator('.uni-picker-action-confirm:visible').first().click();await expect(page.locator('uni-picker .admin-input')).toHaveText(text);await expect(page.locator('.uni-picker-action-confirm:visible')).toHaveCount(0);};
 const save=async()=>{await page.locator('uni-button.admin-primary').filter({hasText:'保存'}).click();};
 const confirm=()=>page.locator('.uni-modal__btn_primary').click();
 await expect(hours).toHaveCount(0);await select('已确认');await save();await confirm();
 await expect.poll(async()=>(await api('/manage/reservations?search='+seed.id)).items[0].status).toBe('confirmed');
 assert.equal(payloads.at(-1).actual_minutes,undefined);assert.equal(payloads.at(-1).actual_guests,undefined);
 await select('已完成');await expect(hours).toHaveValue('0');await save();await expect(page.locator('.admin-error')).toContainText(wallet.wallet_actual_hours_details_required[0]);
 await hours.fill('0.5');await save();await expect(page.locator('.admin-error')).toContainText(wallet.wallet_actual_hours_details_required[0]);
 await select('已取消');await expect(hours).toHaveCount(0);await expect(page.locator('.admin-error')).toHaveCount(0);
 await select('已完成');await expect(hours).toHaveValue('0.5');await guests.fill('1');await save();await confirm();
 await expect.poll(async()=>(await api('/manage/reservations?search='+seed.id)).items[0].actual_minutes).toBe(30);
 await expect(hours).toHaveValue('0.5');assert(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth+1));
 await page.screenshot({path:fileURLToPath(new URL(`native-${viewport.width}.png`,out))});
 assert.deepEqual(errors,[]);results.push({viewport,confirmWithoutAttendance:true,completionRequiresBoth:true,halfHourSaved:true,draftPreservedOnStatusSwitch:true,errors});await ctx.close();
}}finally{await browser.close();}
await fs.writeFile(new URL('native-verification.json',out),JSON.stringify({results,realDevice:false,productionWrites:0},null,2));console.log(JSON.stringify({checks:results.length}));
