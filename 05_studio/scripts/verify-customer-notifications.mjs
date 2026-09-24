import {chromium,expect} from '@playwright/test';
import assert from 'node:assert/strict';
import fs from 'node:fs/promises';
import {fileURLToPath} from 'node:url';
const dir=fileURLToPath(new URL('../../artifacts/notification-completion/ui',import.meta.url));await fs.mkdir(dir,{recursive:true});
const browser=await chromium.launch({channel:'msedge',headless:true}),results=[],stamp=Date.now();
const owner={Authorization:'Bearer qa-owner'};
async function routeLocal(context){await context.route('**/studio-api/**',async route=>{const request=route.request(),url=new URL(request.url());const response=await context.request.fetch('http://127.0.0.1:8011'+url.pathname+url.search,{method:request.method(),headers:{'Content-Type':'application/json',...owner},data:request.postData()||undefined});await route.fulfill({status:response.status(),contentType:'application/json',body:await response.body()});});await context.route('**/api/**',route=>route.fulfill({status:200,contentType:'application/json',body:JSON.stringify({user_id:'qa-owner',email:'qa-owner@example.test',nickname:'Local QA',free_credits_remaining:0,paid_credits:0})}));}
try{
 for(const viewport of [{width:1440,height:900},{width:390,height:844},{width:320,height:568},{width:844,height:390}]){
  const context=await browser.newContext({viewport,reducedMotion:'reduce'});await routeLocal(context);
  await context.addInitScript(()=>{localStorage.setItem('pd_web_token','qa-owner');localStorage.setItem('puppy-studio-locale','zh');sessionStorage.setItem('puppy-studio-admin','local-qa');});
  const customer=await context.newPage(),staff=await context.newPage(),errors=[];for(const p of [customer,staff])p.on('pageerror',e=>errors.push(e.message));
  await customer.goto('http://127.0.0.1:5184/messages');await expect(customer.getByRole('heading',{name:'我的消息'})).toBeVisible();await expect(customer.locator('.site-chat-composer')).toHaveCount(0);
  const question=`Local web question ${viewport.width} ${stamp}`;
  const seeded=await context.request.post('http://127.0.0.1:8011/studio-api/auth/messages',{headers:owner,data:{content:question,request_id:crypto.randomUUID(),reservation_id:''}});assert.equal(seeded.status(),201);
  await expect(customer.locator('.site-conversation-body')).toContainText(question);
  await staff.goto('http://127.0.0.1:5184/manage?view=messages');await staff.getByRole('button',{name:'站内消息',exact:true}).click();
  await staff.locator('.staff-site-inbox aside button').filter({hasText:question}).click();
  await expect(staff.locator('.site-conversation-body')).toContainText(question);
  const answer=`Local web answer ${viewport.width} ${stamp}`;
  await staff.locator('.site-chat-composer textarea').fill(answer);await staff.locator('.site-chat-composer button').click();
  // Customer tab remains open; updates arrive without re-entering the conversation.
  await expect(customer.locator('.site-conversation-body')).toContainText(answer,{timeout:9000});
  assert(await customer.evaluate(()=>document.documentElement.scrollWidth<=innerWidth+2));
  await customer.screenshot({path:`${dir}/web-chat-${viewport.width}x${viewport.height}.png`});
  await staff.getByText('通知设置',{exact:true}).first().click();await staff.getByRole('button',{name:'顾客通知记录',exact:true}).click();
  await expect(staff.locator('dialog[open]')).toContainText('顾客通知记录');
  await customer.goto('http://127.0.0.1:5184/account?notifications=1');
  await expect(customer.locator('.notification-preferences')).toBeVisible();
  await expect(customer.locator('.notification-preferences').getByLabel('邮箱提醒',{exact:true})).toBeEnabled();
  await customer.locator('.notification-preferences').getByLabel('邮箱提醒',{exact:true}).check();
  await customer.locator('.notification-preferences input[type=email]').fill('local-ui@example.test');
  await customer.locator('.notification-preferences').getByRole('button',{name:'保存提醒设置',exact:true}).click();
  await expect(customer.locator('.notification-preferences')).toContainText('提醒设置已保存');
  assert.deepEqual(errors,[]);results.push({surface:'web',viewport,customerReadOnly:true,hostToCustomerLive:true,preferences:true,history:true,noOverflow:true});await context.close();
 }
 for(const viewport of [{width:390,height:844},{width:320,height:568},{width:844,height:390}]){
  const context=await browser.newContext({viewport,reducedMotion:'reduce'});await routeLocal(context);
  await context.addInitScript(()=>{localStorage.setItem('pd_token','qa-owner');localStorage.setItem('pd_studio_language','zh');});
  const page=await context.newPage(),errors=[];page.on('pageerror',e=>errors.push(e.message));
  await page.goto('http://127.0.0.1:5186/h5/#/pages/studio/messages');await expect(page.locator('.site-native-composer textarea')).toBeVisible();
  const question=`Local native question ${viewport.width} ${stamp}`;
  await page.locator('.site-native-composer textarea').fill(question);await page.locator('.site-native-composer uni-button').click();
  await expect(page.locator('.site-native-messages')).toContainText(question);
  const threads=await (await context.request.get('http://127.0.0.1:8011/studio-api/manage/site-messages',{headers:owner})).json();const thread=threads.items.find(r=>r.latest.body===question);assert(thread);
  const answer=`Local native reply ${viewport.width} ${stamp}`;
  const response=await context.request.post('http://127.0.0.1:8011/studio-api/manage/site-messages/'+thread.id,{headers:owner,data:{content:answer,request_id:crypto.randomUUID()}});assert.equal(response.status(),201);
  await expect(page.locator('.site-native-messages')).toContainText(answer,{timeout:9000});
  const box=await page.locator('.site-native-composer').boundingBox();assert(box&&box.y+box.height<=viewport.height+3);
  assert(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth+2));
  await page.screenshot({path:`${dir}/native-chat-${viewport.width}x${viewport.height}.png`});
  await page.goto('http://127.0.0.1:5186/h5/#/pages/studio/notifications');await expect(page.locator('.native-notification-choices')).toBeVisible();
  await page.goto('http://127.0.0.1:5186/h5/#/pages/auth/studio-account');await expect(page.locator('uni-button').filter({hasText:/^管理员后台/})).toBeVisible();
  assert.deepEqual(errors,[]);results.push({surface:'native-h5',viewport,liveReplies:true,composerVisible:true,ownerEntry:true,notificationSettings:true});await context.close();
 }
 await fs.writeFile(dir+'/results.json',JSON.stringify(results,null,2));console.log(JSON.stringify(results));
}finally{await browser.close();}
