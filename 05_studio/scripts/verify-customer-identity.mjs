// Production code against disposable loopback accounts. No live messages or bookings.
import {chromium,webkit,expect} from '@playwright/test';
import assert from 'node:assert/strict';
import fs from 'node:fs/promises';
import {fileURLToPath} from 'node:url';
import profileCopy from '../src/content/profile.json' with {type:'json'};
const out=new URL('../../artifacts/profile-completion/',import.meta.url),results=[];
const avatar=fileURLToPath(new URL('../public/studio-brand/puppy-icon-180-v6.png',import.meta.url));
const origin='http://127.0.0.1:8011',web='http://127.0.0.1:5184',native='http://127.0.0.1:5190/h5/#/';
for(const [engine,browserType] of [['chromium',chromium],['webkit',webkit]]){
 const browser=await browserType.launch({headless:true});
 try{for(const lang of ['zh','en']){
  const word=key=>profileCopy[key][lang==='zh'?0:1],ctx=await browser.newContext({viewport:{width:390,height:844},reducedMotion:'reduce'}),errors=[];
  await ctx.addInitScript(lang=>{
   localStorage.setItem('pd_web_token','qa-owner');localStorage.setItem('pd_token','qa-owner');
   localStorage.setItem('puppy-studio-locale',lang);localStorage.setItem('pd_studio_language',lang);
   sessionStorage.setItem('puppy-studio-admin','local-qa');
  },lang);
  const api=async(path,method='GET',data)=>{const r=await ctx.request.fetch(origin+path,{method,data,headers:{Authorization:'Bearer qa-owner'}});assert(r.ok(),`${path} ${r.status()} ${await r.text()}`);return r.json();};
  await ctx.route('**/studio-api/**',async route=>{
   const req=route.request(),u=new URL(req.url());
   const headers={'Content-Type':req.headers()['content-type']||'application/json',Authorization:'Bearer qa-owner'};
   if(req.headers()['idempotency-key'])headers['Idempotency-Key']=req.headers()['idempotency-key'];
   const r=await ctx.request.fetch(origin+u.pathname+u.search,{method:req.method(),headers,data:req.postDataBuffer()||undefined});
   await route.fulfill({status:r.status(),headers:{'content-type':r.headers()['content-type']||'application/json'},body:await r.body()});
  });
  await ctx.route('**/api/v1/**',async route=>{
   const req=route.request(),u=new URL(req.url());
   if(!/\/api\/v1\/user\/(profile|avatar)$/.test(u.pathname)){await route.fulfill({json:{}});return;}
   // CDP omits binary file parts in intercepted multipart bodies. Forward the
   // explicitly selected local fixture file via Playwright's multipart API.
   const options=u.pathname.endsWith('/avatar')?
    {method:req.method(),headers:{Authorization:'Bearer qa-owner'},multipart:{image:{name:'qa.png',mimeType:'image/png',buffer:await fs.readFile(avatar)}}}:
    {method:req.method(),headers:{'Content-Type':req.headers()['content-type']||'application/json',Authorization:'Bearer qa-owner'},data:req.postDataBuffer()||undefined};
   const r=await ctx.request.fetch(origin+u.pathname,options);
   if(!r.ok())console.log({path:u.pathname,status:r.status(),body:await r.text()});
   await route.fulfill({status:r.status(),contentType:'application/json',body:await r.body()});
  });
  const page=await ctx.newPage();page.setDefaultTimeout(9000);page.on('pageerror',e=>errors.push(e.message));
  await api('/studio-api/qa/profile/reset','POST');
  await page.goto(web+'/account?setup=1');
  const dialog=page.locator('dialog[open]');await expect(dialog).toBeVisible();
  await expect(dialog.locator('.booking-contact-fields')).toBeVisible();
  await dialog.locator('input[autocomplete="nickname"]').fill('Customer '+engine);
  await dialog.getByPlaceholder(word('wechat_id_placeholder')).fill('local_wechat');
  await dialog.locator('input[autocomplete="name"]').fill('Booking '+engine);
  await dialog.locator('.contact-method-picker label').filter({has:page.locator('input[value="phone"]')}).click();
  await dialog.locator('.visit-contact-value input').fill('+1 416 555 0199');
  await dialog.locator('input[type=file]').setInputFiles(avatar);
  for(const [width,height] of [[320,568],[390,844],[844,390],[1440,1000]]){
   await page.setViewportSize({width,height});assert(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth+1));
   await expect(dialog.getByRole('button',{name:word('save'),exact:true})).toBeEnabled();
  }
  await page.setViewportSize({width:390,height:844});
  await page.screenshot({path:fileURLToPath(new URL(`web-profile-${engine}-${lang}.png`,out))});
  await dialog.getByRole('button',{name:word('save'),exact:true}).click();await expect(dialog).toHaveCount(0).catch(async e=>{console.log({stage:'web-save',errors:await dialog.locator('.form-error').allTextContents()});throw e;});
  const account=(await api('/studio-api/manage/members/qa-owner')).account;
  assert.equal(account.name,'Customer '+engine);assert(account.avatar);assert.equal(account.booking_profile.wechat_id,'local_wechat');
  const code=account.customer_code;
  await page.goto(web+'/manage?view=members&member=qa-owner');await expect(page.locator('dialog[open] .customer-identity')).toContainText('Booking '+engine);
  await expect(page.locator('dialog[open] .customer-identity')).toContainText(code);
  await expect(page.locator('dialog[open] .customer-identity')).toContainText('+1 416 555 0199');
  await expect(page.locator('dialog[open] .customer-identity')).toContainText('local_wechat');
  await expect(page.locator('dialog[open] .customer-identity img')).toBeVisible();
  await page.screenshot({path:fileURLToPath(new URL(`web-admin-${engine}-${lang}.png`,out))});
  assert((await api('/studio-api/manage/members?search='+code)).items.some(row=>row.owner_id==='qa-owner'));
  // The same native Vue page runs in H5 for portable request and layout checks.
  await api('/studio-api/qa/profile/reset','POST');
  await page.goto(native+'pages/auth/studio-profile?onboard=1');
  await expect(page.locator('.studio-profile-form .studio-native-title')).toHaveText(word('setup_title'));
  await expect(page.locator('.studio-profile-form input').first()).toBeVisible();
  const inputs=page.locator('.studio-profile-form input');await expect(inputs).toHaveCount(4);
  await expect(inputs.nth(0)).toHaveValue('');
  await inputs.nth(0).fill('Native '+engine);await inputs.nth(1).fill('native_wechat');
  await inputs.nth(2).fill('Native booking');await inputs.nth(3).fill('primary_wechat');
  for(const [width,height] of [[320,568],[390,844],[844,390]]){
   await page.setViewportSize({width,height});
   assert(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth+1));
   const save=page.locator('uni-button.studio-native-primary').filter({hasText:word('save')});
   await expect(save).toBeVisible();await expect.poll(async()=>{const box=await save.boundingBox();return !!box&&box.y>=0&&box.y+box.height<=height+1;}).toBe(true);
  }
  await page.setViewportSize({width:390,height:844});
  await expect.poll(async()=>{const box=await page.locator('uni-button.studio-native-primary').filter({hasText:word('save')}).boundingBox();return !!box&&box.y+box.height>800;}).toBe(true);
  await page.screenshot({path:fileURLToPath(new URL(`native-profile-${engine}-${lang}.png`,out))});
  const sent=page.waitForRequest(r=>r.url().endsWith('/studio-api/auth/profile')&&r.method()==='PUT');
  await page.locator('uni-button.studio-native-primary').filter({hasText:word('save')}).click();await sent;
  await expect.poll(async()=>(await api('/studio-api/manage/members/qa-owner')).account.name).toBe('Native '+engine);
  await expect.poll(async()=>(await api('/studio-api/manage/members/qa-owner')).account.booking_profile.wechat_id).toBe('native_wechat');
  assert.equal((await api('/studio-api/manage/members/qa-owner')).account.customer_code,code);
  await page.goto(native+'pages/studio/manage-member?id=qa-owner');await expect(page.locator('.native-customer-identity')).toContainText('Native booking');
  await expect(page.locator('.native-customer-identity')).toContainText('native_wechat');
  await expect(page.locator('.native-customer-identity')).toContainText(code);
  await page.screenshot({path:fileURLToPath(new URL(`native-admin-${engine}-${lang}.png`,out))});
  assert.deepEqual(errors,[]);results.push({engine,lang,webAvatarAndContactsSaved:true,nativePutAndContactsSaved:true,sameAccountAndReference:true,responsiveWidths:[320,390,844,1440],errors});
  await ctx.close();
 }}finally{await browser.close();}
}
await fs.writeFile(new URL('ui-verification.json',out),JSON.stringify({results,productionWrites:0,realDevice:false},null,2));console.log(JSON.stringify({cases:results.length}));
