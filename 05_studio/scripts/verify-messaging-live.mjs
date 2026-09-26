import {chromium,expect} from '@playwright/test';
import assert from 'node:assert/strict';
import fs from 'node:fs/promises';
import {randomUUID} from 'node:crypto';

// Only the isolated qa_messaging.py service, with fictional contacts and no Mac.
const api='http://127.0.0.1:8011/studio-api';
const browser=await chromium.launch({channel:'msedge',headless:true});
const checks=[];
try {
  const context=await browser.newContext({viewport:{width:590,height:900}});
  await context.addInitScript(()=>{
    sessionStorage.setItem('puppy-studio-admin','local-qa');
    localStorage.setItem('puppy-studio-language','zh');
    window.qaVisibility='hidden';
    Object.defineProperty(document,'visibilityState',{get:()=>window.qaVisibility});
  });
  const page=await context.newPage();
  const errors=[];page.on('pageerror',e=>errors.push(e.message));
  const readRequests=[];
  page.on('request',r=>{if(r.url().endsWith('/read'))readRequests.push(r.url());});
  await page.goto('http://127.0.0.1:5184/manage?view=messages');
  await page.locator('.sms-thread').filter({hasText:'+14165550123'}).click();
  const chat=page.locator('vue-advanced-chat');
  await expect(chat).toContainText('你好，可以提前十分钟到吗？');
  const threads=await (await context.request.get(api+'/manage/messages/threads')).json();
  const thread=threads.items.find(t=>t.phone==='+14165550123');
  assert(thread);
  const selectedRoom=await chat.getAttribute('room-id');
  async function receive(label) {
    const content=label+' '+randomUUID();
    const response=await context.request.post(api+'/message-bridge/messages',{
      headers:{Authorization:'Bearer '+'A'.repeat(43)},
      data:{messages:[{thread_id:thread.id,phone:thread.phone,external_id:randomUUID(),direction:'inbound',channel:'SMS',content,timestamp:Date.now()/1000}]},
    });
    assert(response.ok(),await response.text());
    const started=Date.now();
    await expect(chat).toContainText(content,{timeout:6000});
    await expect(chat.getByText(content,{exact:true})).toBeInViewport();
    checks.push({case:label,serverToScreenMs:Date.now()-started});
    await expect(chat).toHaveAttribute('room-id',selectedRoom);
    return content;
  }
  await page.locator('#sms-draft').fill('继续编辑的草稿');
  await receive('embedded-hidden');
  assert.equal(readRequests.length,0,'Hidden panes must not mark new messages read');
  await expect(page.locator('#sms-draft')).toHaveValue('继续编辑的草稿');
  await expect(page.locator('#sms-draft')).toBeFocused();
  await page.evaluate(()=>{window.qaVisibility='visible';document.dispatchEvent(new Event('visibilitychange'));});
  await expect.poll(()=>readRequests.length,{timeout:6000}).toBeGreaterThan(0);
  await receive('visible');

  // A delayed sidebar must not hold up the selected conversation.
  const held=[];
  const holdList=route=>{held.push(route);};
  await page.route('**/manage/messages/threads?*',holdList);
  await page.getByRole('button',{name:'刷新',exact:true}).click();
  await expect.poll(()=>held.length).toBeGreaterThan(0);
  await receive('sidebar-stalled');
  await page.unroute('**/manage/messages/threads?*',holdList);
  for(const route of held)await route.abort().catch(()=>{});

  // A hung conversation request must time out, then resume on its own.
  const heldDetails=[];
  const holdDetails=route=>{heldDetails.push(route);};
  await page.route('**/manage/messages/threads/'+thread.id,holdDetails);
  await expect.poll(()=>heldDetails.length,{timeout:6000}).toBeGreaterThan(0);
  await page.unroute('**/manage/messages/threads/'+thread.id,holdDetails);
  const recovered='recovered '+randomUUID();
  const ingested=await context.request.post(api+'/message-bridge/messages',{
    headers:{Authorization:'Bearer '+'A'.repeat(43)},
    data:{messages:[{thread_id:thread.id,phone:thread.phone,external_id:randomUUID(),direction:'inbound',channel:'SMS',content:recovered,timestamp:Date.now()/1000}]},
  });
  assert(ingested.ok());
  await expect(chat).toContainText(recovered,{timeout:14000});
  checks.push({case:'hung-request-recovers',passed:true});
  for(const route of heldDetails)await route.abort().catch(()=>{});
  await expect(page.locator('#sms-draft')).toHaveValue('继续编辑的草稿');
  assert.deepEqual(errors,[]);
  await fs.mkdir('../artifacts/messaging-integration/ui',{recursive:true});
  await fs.writeFile('../artifacts/messaging-integration/ui/live-checks.json',JSON.stringify(checks,null,2));
  console.log(JSON.stringify(checks));
} finally {await browser.close();}
