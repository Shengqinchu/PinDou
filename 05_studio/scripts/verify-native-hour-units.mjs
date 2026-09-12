// Native Vue pages rendered in H5; every request is routed to loopback QA.
import {chromium,expect} from '@playwright/test';
import assert from 'node:assert/strict';
import fs from 'node:fs/promises';
import {fileURLToPath} from 'node:url';
const browser=await chromium.launch({headless:true}),out=new URL('../../artifacts/hour-units/',import.meta.url),results=[];
try{for(const viewport of [{width:390,height:844},{width:320,height:568},{width:844,height:390}]){
 const ctx=await browser.newContext({viewport,reducedMotion:'reduce'}),errors=[];
 await ctx.route('**/studio-api/**',async route=>{const request=route.request(),u=new URL(request.url());const r=await ctx.request.fetch('http://127.0.0.1:8011'+u.pathname+u.search,{method:request.method(),headers:{'Content-Type':'application/json',Authorization:'Bearer local-qa',...(request.headers()['idempotency-key']?{'Idempotency-Key':request.headers()['idempotency-key']}:{})},data:request.postData()||undefined});await route.fulfill({status:r.status(),contentType:'application/json',body:await r.body()});});
 await ctx.route('**/api/v1/**',route=>route.fulfill({json:{user_id:'qa-owner',nickname:'QA',role:'admin',ai_points_balance:166,normal_trial_remaining:1}}));
 const api=async(path,method='GET',data)=>{const r=await ctx.request.fetch('http://127.0.0.1:8011/studio-api'+path,{method,data,headers:{Authorization:'Bearer local-qa'}});assert(r.ok());return r.json();};
 const seed=await api('/qa/attended-visit','POST'),row=(await api('/manage/reservations?search='+seed.id)).items[0];
 await api('/manage/reservations/'+seed.id,'PATCH',{version:row.version,status:'confirmed',actual_minutes:90,actual_guests:2,staff_note:'',public_note:''});
 const page=await ctx.newPage();page.setDefaultTimeout(9000);page.on('pageerror',e=>errors.push(e.message));
 const base='http://127.0.0.1:5190/h5/#/pages/studio/';
 await page.goto(base+'manage-reservation?id='+seed.id);await expect(page.locator('.admin-loading')).toHaveCount(0);
 const hours=page.locator('.admin-field').filter({hasText:'实际游玩时长（小时／人）'}).locator('input');
 await expect(hours).toHaveValue('1.5');await hours.fill('0.5');
 await page.locator('uni-button.admin-primary').filter({hasText:'保存'}).click();
 await page.locator('.uni-modal__btn_primary').click();
 await expect.poll(async()=>(await api('/manage/reservations?search='+seed.id)).items[0].actual_minutes).toBe(30);
 await expect(hours).toHaveValue('0.5');
 assert(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth+1));
 await page.screenshot({path:fileURLToPath(new URL(`native-hours-${viewport.width}.png`,out))});
 await page.goto(base+'manage-member?id=qa-owner');await expect(page.locator('.admin-native-content')).toContainText('小时');
 const initial=(await api('/manage/members/qa-owner')).account.minutes;
 await page.locator('uni-button.admin-primary').filter({hasText:'登记一笔'}).click();
 await page.locator('.admin-field').filter({hasText:'时长（小时）'}).locator('input').fill('0.5');
 await page.locator('.admin-field').filter({hasText:'记账说明（顾客可见）'}).locator('textarea').fill('Native half-hour QA');
 await page.locator('uni-button.admin-primary').filter({hasText:'保存并同步给顾客'}).click();
 await expect(page.locator('.uni-modal__bd')).toContainText('时长（小时）: 0.5');
 await page.locator('.uni-modal__btn_primary').click();
 await expect.poll(async()=>(await api('/manage/members/qa-owner')).account.minutes).toBe(initial+30).catch(async error=>{console.log({viewport,error:await page.locator('.admin-error').allTextContents()});throw error;});
 await expect(page.locator('.admin-native-content')).toContainText('+0.5 · 时长（小时）');
 assert.deepEqual(errors,[]);results.push({viewport,bookingHours:true,halfHourTransaction:true,confirmationAndHistoryHours:true,errors});await ctx.close();
}}finally{await browser.close();}
await fs.writeFile(new URL('native-h5-verification.json',out),JSON.stringify({results,realDevice:false,productionWrites:0},null,2));console.log(JSON.stringify({checks:results.length}));
