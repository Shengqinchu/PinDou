// Runs only against qa_generator.py and its isolated database/provider doubles.
import {chromium,expect} from '@playwright/test';
import assert from 'node:assert/strict';
import fs from 'node:fs/promises';
import {fileURLToPath} from 'node:url';
import AxeBuilder from '@axe-core/playwright';
const base='http://127.0.0.1:19678',out=new URL('../../artifacts/wallet-menu-refinement/',import.meta.url);
const results=[],errors=[],browser=await chromium.launch({headless:true,ignoreDefaultArgs:['--hide-scrollbars']});
const record=(test)=>results.push({test,passed:true});
const screenshot=(page,name)=>page.screenshot({path:fileURLToPath(new URL(name,out)),fullPage:true});
const tipText='100 积分抵扣 CAD 1，每次按整数 CAD 使用，剩余积分保留。';
const earnText='注册账号即可获得166积分；每次通过网站预约并到店游玩可获得166 积分。';
await fs.mkdir(out,{recursive:true});
try{
 const context=await browser.newContext({locale:'zh-CN',viewport:{width:1440,height:1000}});
 await context.addInitScript(()=>localStorage.setItem('pd_web_token','qa-owner'));
 const page=await context.newPage();page.setDefaultTimeout(12000);page.on('pageerror',e=>errors.push(e.message));
 await page.goto(base+'/account');await expect(page.locator('.wallet-balance.points strong')).toHaveText('166');
 await expect(page.locator('.wallet-balance.time strong')).toHaveText('0 小时');
 await expect(page.locator('.account-page .account-avatar-link')).not.toHaveAttribute('href');
 await page.getByRole('button',{name:'积分明细',exact:true}).click();await expect(page.locator('.wallet-ledger>li')).toHaveCount(1);
 await expect(page.locator('.wallet-ledger')).toContainText('注册赠分');
 await page.getByRole('button',{name:'刷新记录',exact:true}).click();await page.reload();
 await expect(page.locator('.wallet-balance.points strong')).toHaveText('166');
 const pointTip=()=>page.getByRole('button',{name:'积分说明',exact:true});
 await pointTip().hover();await expect(page.getByRole('tooltip')).toContainText('可抵扣 CAD 1');
 for(const text of [tipText,earnText,'积分在到店结算时由店主确认抵扣，也可在拼豆小店购物使用。','积分和优惠活动不可同时使用。'])await expect(page.getByRole('tooltip')).toContainText(text);
 await page.getByRole('tooltip').hover();await expect(page.getByRole('tooltip')).toBeVisible();
 await screenshot(page,'account-desktop.png');await page.keyboard.press('Escape');await expect(page.getByRole('tooltip')).toHaveCount(0);
 record('Registration gives 166 once; exact Chinese copy and dynamic CAD 1 tooltip');
 for(const selector of ['.account-avatar-link','.account-name-link']){
  await page.goto(base+'/');await page.locator('.account-trigger').click();const drawer=page.locator('dialog[open]');
  await expect(drawer.locator('.wallet-balances')).toBeVisible();await expect(drawer.locator('a[href="/account"]')).toHaveCount(2);
  await expect(drawer.getByText('账号中心',{exact:true})).toHaveCount(0);
  await drawer.locator(selector).click();await expect(page).toHaveURL(base+'/account');await expect(page.locator('dialog[open]')).toHaveCount(0);
 }
 await page.getByRole('button',{name:'编辑资料',exact:true}).click();await expect(page.locator('dialog[open] input[autocomplete="nickname"]')).toBeVisible();
 await page.locator('dialog[open]').getByRole('button',{name:'取消',exact:true}).click();
 record('Avatar and nickname open account center and close drawer; profile editor remains accessible');
 for(const width of [320,390,768,1024,1440]){
  await page.setViewportSize({width,height:900});await page.locator('.vision-header-actions button[aria-expanded]').last().click();
  const menu=page.locator('dialog[open] .vision-menu');await expect(menu.locator('a')).toHaveCount(6);
  assert.deepEqual(await menu.locator('a').evaluateAll(nodes=>nodes.map(n=>[n.getAttribute('href'),n.querySelector('.vision-menu-number').textContent])),[['/','01'],['/visit','02'],['/shop','03'],['/journal','04'],['/details','05'],['/tools','06']]);
  await expect(page.locator('dialog[open] a[href="/manage"],dialog[open] .motion-settings')).toHaveCount(0);
  await expect(page.locator('dialog[open]')).not.toContainText('页面动效');await expect(page.locator('dialog[open]')).not.toContainText('店主管理');
  assert(await page.locator('dialog[open] .drawer-panel').evaluate(e=>e.scrollWidth<=e.clientWidth+1));
  if([390,1440].includes(width))await screenshot(page,`menu-${width}.png`);
  await page.keyboard.press('Escape');await pointTip().click();await expect(page.getByRole('tooltip')).toBeVisible();
  const bounds=await page.getByRole('tooltip').boundingBox();assert(bounds.x>=0&&bounds.x+bounds.width<=width+1);
  await page.keyboard.press('Escape');assert(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth+1));
 }
 await page.locator('.vision-header-actions .language-button').click();
 await page.getByRole('button',{name:'About your points',exact:true}).click();
 await expect(page.getByRole('tooltip')).toContainText('Redeemable: CAD 1');await expect(page.getByRole('tooltip')).toContainText('Receive 166 points when you register');
 await expect(page.getByRole('tooltip')).toContainText('Points cannot be combined with promotional offers.');
 await page.keyboard.press('Escape');
 const axe=await new AxeBuilder({page}).include('.account-page').analyze();assert.deepEqual(axe.violations.map(v=>({id:v.id,nodes:v.nodes.length})),[]);
 await page.locator('.vision-header-actions .language-button').click();
 record('Six numbered menu destinations, no removed controls, 5 responsive widths, bilingual tooltips and accessibility');

 const adminContext=await browser.newContext({locale:'zh-CN',viewport:{width:1440,height:1000}});
 await adminContext.addInitScript(()=>sessionStorage.setItem('puppy-studio-admin','local-qa'));
 const host=await adminContext.newPage();host.setDefaultTimeout(12000);host.on('pageerror',e=>errors.push(e.message));
 await host.goto(base+'/manage?view=members');await host.locator('.member-row').filter({hasText:'qa-owner@example.test'}).click();
 const dialog=()=>host.locator('dialog[open]');
 const privateNote='Jessica，微信\n只在店主列表显示的备注';
 await dialog().getByLabel('店主私密备注',{exact:true}).fill(privateNote);await dialog().getByRole('button',{name:'保存备注',exact:true}).click();
 await expect(dialog().locator('.wallet-saved')).toBeVisible();await host.keyboard.press('Escape');await expect(dialog()).toHaveCount(0);
 await expect(host.locator('.member-row .member-list-note')).toHaveText(privateNote);
 await host.locator('.member-search input').fill('Jessica');await expect(host.locator('.member-row')).toHaveCount(1);
 await screenshot(host,'admin-notes-desktop.png');
 for(const width of [320,390,768,1024,1440]){
  await host.setViewportSize({width,height:900});await expect(host.locator('.member-list-note')).toBeVisible();
  assert(await host.locator('.member-row').evaluate(e=>e.scrollWidth<=e.clientWidth+1),`Member row overflow at ${width}`);
  assert(await host.evaluate(()=>document.documentElement.scrollWidth<=innerWidth+1),`Admin page overflow at ${width}`);
 }
 await host.setViewportSize({width:390,height:844});await screenshot(host,'admin-notes-mobile.png');
 await page.reload();await expect(page.locator('body')).not.toContainText('Jessica');
 record('Private notes save, appear directly, search and wrap on desktop/mobile; absent from customer page');
 await host.setViewportSize({width:1440,height:1000});await host.locator('.member-row').click();
 await dialog().getByRole('button',{name:'登记一笔',exact:true}).click();
 await dialog().getByRole('combobox',{name:'记账类型',exact:true}).selectOption('redeem');
 await dialog().getByLabel('抵扣金额（整数 CAD）',{exact:true}).fill('1');
 await dialog().getByLabel('本次可抵扣消费金额（CAD）',{exact:true}).fill('8.88');
 await dialog().getByRole('combobox',{name:'抵扣用途',exact:true}).selectOption('shop');
 await dialog().getByLabel('记账说明（顾客可见）',{exact:true}).fill('QA shop purchase');
 let requests=0;host.on('request',req=>{if(req.method()==='POST'&&req.url().includes('/transactions'))requests++;});
 await dialog().getByRole('button',{name:'保存并同步给顾客',exact:true}).click();assert.equal(requests,0);
 await dialog().getByLabel('确认本单未使用其他优惠活动',{exact:true}).check();await screenshot(host,'shop-redemption.png');
 await dialog().getByRole('button',{name:'保存并同步给顾客',exact:true}).click();await expect(dialog().locator('.wallet-saved')).toBeVisible();
 await expect(dialog().locator('.wallet-balance.points strong')).toHaveText('66');assert.equal(requests,1);
 await expect(dialog().locator('.wallet-ledger')).toContainText('小店购物');
 await page.getByRole('button',{name:'刷新记录',exact:true}).click();await expect(page.locator('.wallet-balance.points strong')).toHaveText('66');
 await pointTip().click();await expect(page.getByRole('tooltip')).toContainText('可抵扣 CAD 0');await page.keyboard.press('Escape');
 // Opening time is permitted after the registration reward, tested in pytest; add a top-up for decimal-hour UI regression.
 await dialog().getByRole('button',{name:'登记一笔',exact:true}).click();await dialog().getByRole('combobox',{name:'记账类型',exact:true}).selectOption('topup');
 await dialog().getByLabel('时长（分钟）',{exact:true}).fill('90');await dialog().getByLabel('记账说明（顾客可见）',{exact:true}).fill('QA time 1.5 hours');
 await dialog().getByRole('button',{name:'保存并同步给顾客',exact:true}).click();await expect(dialog().locator('.wallet-saved')).toBeVisible();
 await page.getByRole('button',{name:'刷新记录',exact:true}).click();await expect(page.locator('.wallet-balance.time strong')).toHaveText('1.5 小时');
 record('Shop redemption requires explicit no-promotion confirmation, debits only 100, retains 66, and decimal hours remain correct');
 const touchContext=await browser.newContext({locale:'zh-CN',viewport:{width:390,height:844},isMobile:true,hasTouch:true});
 await touchContext.addInitScript(()=>localStorage.setItem('pd_web_token','qa-other'));const touch=await touchContext.newPage();
 await touch.goto(base+'/account');await expect(touch.locator('.wallet-balances')).toBeVisible();await touch.getByRole('button',{name:'积分说明',exact:true}).tap();
 await expect(touch.getByRole('tooltip')).toContainText(earnText);await screenshot(touch,'account-touch.png');
 await touch.locator('h1').tap();await expect(touch.getByRole('tooltip')).toHaveCount(0);
 record('Touch tap opens the complete help text and outside tap dismisses it');
 assert.deepEqual(errors,[]);await context.close();await adminContext.close();await touchContext.close();
}finally{await browser.close();await fs.writeFile(new URL('browser-verification.json',out),JSON.stringify({results,errors},null,2));}
console.log(JSON.stringify({results,errors},null,2));
