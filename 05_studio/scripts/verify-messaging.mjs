import {chromium,expect} from '@playwright/test';
import assert from 'node:assert/strict';
import fs from 'node:fs/promises';
const output='../artifacts/messaging-integration/ui';
await fs.mkdir(output,{recursive:true});
const browser=await chromium.launch({channel:'msedge',headless:true});
const checks=[];
try{
 for(const viewport of [{width:1440,height:900},{width:390,height:844},{width:320,height:568},{width:844,height:390}]){
  const ctx=await browser.newContext({viewport,reducedMotion:'reduce'});
  await ctx.addInitScript(()=>{sessionStorage.setItem('puppy-studio-admin','local-qa');localStorage.setItem('puppy-studio-locale','zh');});
  const page=await ctx.newPage();const errors=[];page.on('pageerror',e=>errors.push(e.message));
  await page.goto('http://127.0.0.1:5184/manage?view=messages');
  await page.locator('.sms-thread').filter({hasText:'+14165550123'}).click();
  await expect(page.locator('vue-advanced-chat')).toContainText('你好，可以提前十分钟到吗？');
  await page.locator('#sms-draft').fill('本地测试：请稍候 <script>alert(1)</script>');
  await page.getByRole('button',{name:'发送消息',exact:true}).click();
  await expect(page.locator('vue-advanced-chat')).toContainText('本地测试：请稍候 <script>alert(1)</script>');
  await expect(page.locator('#sms-draft')).toHaveValue('');
  assert(await page.locator('vue-advanced-chat').locator('script').count()===0);
  assert(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth+2));
  const composer=await page.locator('.sms-composer').boundingBox();
  assert(composer&&composer.width<=viewport.width);assert(composer.y+composer.height<=viewport.height+2,JSON.stringify({viewport,composer}));
  await page.locator('#sms-draft').fill('保留草稿');
  await page.route('**/studio-api/manage/messages/threads/*/messages',route=>route.abort('failed'));
  await page.getByRole('button',{name:'发送消息',exact:true}).click();
  await expect(page.locator('#sms-draft')).toHaveValue('保留草稿');
  await expect(page.locator('.sms-workspace>.desk-error')).toBeVisible();
  await page.screenshot({path:`${output}/messages-${viewport.width}x${viewport.height}.png`,fullPage:true});
  assert.deepEqual(errors,[]);checks.push({viewport,conversation:true,draftRetained:true,noHorizontalOverflow:true});
  await ctx.close();
 }
 await fs.writeFile(`${output}/checks.json`,JSON.stringify(checks,null,2));
 console.log(JSON.stringify(checks));
}finally{await browser.close();}
