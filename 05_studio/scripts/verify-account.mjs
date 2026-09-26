// Writes only to the isolated loopback QA database; never run against production.
import { chromium,webkit,expect } from '@playwright/test';
import fs from 'node:fs/promises';
import assert from 'node:assert/strict';
const base='http://127.0.0.1:4184',out='../artifacts/studio-account';
await fs.mkdir(out,{recursive:true});
const checks=[],errors=[];
const run=Date.now();
async function layout(page,tag){
 await page.evaluate(()=>new Promise(resolve=>requestAnimationFrame(()=>requestAnimationFrame(resolve))));
 const value=await page.evaluate(()=>{
  const header=document.querySelector('.vision-header'),panel=document.querySelector('dialog[open] .drawer-panel');
  const children=[...(header?.children||[])].filter(el=>getComputedStyle(el).display!=='none').map(el=>el.getBoundingClientRect());
  return {overflow:document.documentElement.scrollWidth>innerWidth+1,headerOverlap:children.some((r,i)=>i>0&&r.x<children[i-1].right-1),panelInside:!panel||panel.getBoundingClientRect().right<=innerWidth+1&&panel.getBoundingClientRect().left>=-1};
 });
 assert.deepEqual(value,{overflow:false,headerOverlap:false,panelInside:true},tag);checks.push({tag,...value});
}
for(const [name,engine,widths] of [['chromium',chromium,[320,390,768,1440]],['webkit',webkit,[390]]]){
 const browser=await engine.launch({headless:true});
 try{for(const width of widths)for(const lang of ['zh','en']){
  const context=await browser.newContext({viewport:{width,height:900},reducedMotion:'reduce'});
  await context.addInitScript(lang=>localStorage.setItem('puppy-studio-language',lang),lang);
  const page=await context.newPage();page.on('pageerror',e=>errors.push(e.message));
  await page.goto(base+'/');await expect(page.locator('h1')).toBeVisible();await expect(page.locator('dialog[open]')).toHaveCount(0);
  await layout(page,`${name}-${width}-${lang}-public`);
  await page.locator('.account-trigger').click();await expect(page.locator('.account-form')).toBeVisible();await page.evaluate(()=>document.fonts.ready);
  await layout(page,`${name}-${width}-${lang}-login`);
  assert.equal(await page.locator('.account-form input[type=email]').evaluate(e=>getComputedStyle(e).fontSize),'16px');
  await page.locator('.account-form input[type=email]').fill(`layout-${run}@example.test`);
  await page.getByRole('button',{name:lang==='zh'?'密码登录':'Password',exact:true}).click();
  await expect(page.locator('input[autocomplete="current-password"]')).toBeVisible();
  await layout(page,`${name}-${width}-${lang}-password`);
  if(width===320||width===1440)await page.screenshot({path:`${out}/${name}-${width}-${lang}.png`});
  await context.close();
 }}finally{await browser.close();}
}
for(const [name,engine] of [['desktop',chromium],['wechat-android',chromium],['wechat-ios-simulation',webkit]]){
 const browser=await engine.launch({headless:true});
 try{
  const mobile=name!=='desktop';
  const context=await browser.newContext({viewport:{width:mobile?390:1440,height:900},isMobile:mobile,hasTouch:mobile,reducedMotion:'reduce',...(mobile?{userAgent:name.includes('ios')?'Mozilla/5.0 (iPhone; CPU iPhone OS 18_0 like Mac OS X) AppleWebKit/605.1.15 Mobile/15E148 MicroMessenger/8.0.50':'Mozilla/5.0 (Linux; Android 14) AppleWebKit/537.36 Chrome/126.0 Mobile Safari/537.36 MicroMessenger/8.0.50'}:{})});
  const page=await context.newPage();page.on('pageerror',e=>errors.push(e.message));let submissions=0;
  page.on('request',r=>{if(r.method()==='POST'&&r.url().endsWith('/studio-api/reservations'))submissions++;});
  await page.goto(base+'/visit');await page.locator('label:has(input[value="hourly"])').click();
  await page.locator('button[data-cell]:not([disabled])').first().click();
  await page.getByLabel('客人名称',{exact:false}).fill('Account flow QA');
  await page.locator('.reservation-contact-fields input').nth(1).fill('local-qa-only');
  await page.locator('.reservation-consent input').check();
  const selection=await page.locator('.reservation-selection').innerText();
  await page.locator('.reservation-submit .button').click();await expect(page.locator('.account-form')).toBeVisible();assert.equal(submissions,0);
  await page.keyboard.press('Escape');await expect(page.locator('dialog[open]')).toHaveCount(0);assert.equal(await page.locator('.reservation-selection').innerText(),selection);
  await expect(page.getByLabel('客人名称',{exact:false})).toHaveValue('Account flow QA');
  await page.locator('.reservation-submit .button').click();await expect(page.locator('.account-form')).toBeVisible();
  const email=`${name}-${run}@example.test`;await page.getByLabel('邮箱地址',{exact:true}).fill(email);
  await page.getByRole('button',{name:'发送验证码',exact:true}).click();await expect(page.locator('.account-content')).toContainText('验证码已发送');
  await expect(page.locator('.account-send')).toBeDisabled();
  if(mobile){await page.setViewportSize({width:844,height:390});await layout(page,`${name}-landscape`);await page.setViewportSize({width:390,height:560});await layout(page,`${name}-keyboard-height`);}
  await page.getByLabel('6 位验证码',{exact:true}).fill('000000');await page.locator('.account-form .button-primary').click();await expect(page.locator('.account-form .form-error')).toContainText('验证码');assert.equal(submissions,0);
  await page.getByLabel('6 位验证码',{exact:true}).fill('123456');await page.locator('.account-form .button-primary').click();
  await page.waitForURL('**/reservation/VIS-*');await expect(page.locator('.reservation-receipt dl')).toBeVisible();assert.equal(submissions,1);
  const receipt=page.url();const token=await page.evaluate(()=>localStorage.getItem('pd_web_token'));assert(token);
  await page.locator('.account-trigger').click();await expect(page.locator('.account-bookings li')).toHaveCount(1);await page.getByRole('button',{name:'退出登录',exact:true}).click();
  assert.equal(await page.evaluate(()=>localStorage.getItem('pd_web_token')),null);
  await page.goto(receipt);await expect(page.locator('.reservation-receipt .button-primary')).toHaveText('登录');
  await page.goto(base+'/');await expect(page.locator('h1')).toBeVisible();await expect(page.locator('dialog[open]')).toHaveCount(0);
  // The existing generator's storage is sufficient; no second registration/session.
  await page.evaluate(token=>localStorage.setItem('pd_web_token',token),token);await page.reload();
  await expect(page.locator('.account-trigger')).toHaveAttribute('aria-label','我的账号');
  await page.goto(receipt);await expect(page.locator('.reservation-receipt dl')).toBeVisible();
  checks.push({tag:name+'-auth-flow',cancelPreservesDraft:true,invalidCodeRejected:true,loginResumesOneSubmission:true,sharedGeneratorToken:true,logoutRequiresLogin:true});
  await page.screenshot({path:`${out}/${name}-receipt.png`});await context.close();
 }finally{await browser.close();}
}
{
 const browser=await chromium.launch({headless:true});
 try{
  const page=await browser.newPage({viewport:{width:390,height:900},reducedMotion:'reduce'});page.on('pageerror',e=>errors.push(e.message));
  await page.goto(base+'/');await page.locator('.account-trigger').click();
  await page.getByLabel('邮箱地址',{exact:true}).fill(`password-${run}@example.test`);
  await page.getByLabel('6 位验证码',{exact:true}).fill('123456');
  await page.getByLabel('同时设置密码（可选）',{exact:true}).check();
  await page.getByLabel('设置密码，至少 6 位',{exact:true}).fill('local-password');
  await page.getByLabel('再次输入密码',{exact:true}).fill('does-not-match');
  await page.locator('.account-form .button-primary').click();await expect(page.locator('.account-form .form-error')).toContainText('不一致');
  await page.getByLabel('再次输入密码',{exact:true}).fill('local-password');
  await page.locator('.account-form .button-primary').click();await expect(page.locator('.account-identity')).toBeVisible();
  await page.getByRole('button',{name:'退出登录',exact:true}).click();await page.locator('.account-trigger').click();
  await page.getByRole('button',{name:'密码登录',exact:true}).click();
  await page.getByLabel('密码',{exact:true}).fill('incorrect');await page.locator('.account-form .button-primary').click();
  await expect(page.locator('.account-form .form-error')).toContainText('邮箱或密码');
  await page.getByLabel('密码',{exact:true}).fill('local-password');await page.locator('.account-form .button-primary').click();
  await expect(page.locator('.account-identity')).toBeVisible();
  checks.push({tag:'optional-password-registration-and-login',mismatchRejected:true,wrongPasswordRejected:true,registeredAccountReused:true});
 }finally{await browser.close();}
}
await fs.writeFile(`${out}/browser-verification.json`,JSON.stringify({checks,errors},null,2));
console.log(JSON.stringify({checks:checks.length,errors}));assert.deepEqual(errors,[]);
