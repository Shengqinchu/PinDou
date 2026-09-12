// All writes go to the isolated loopback qa_server.py, never a real customer DB.
import {chromium,expect} from '@playwright/test';
import assert from 'node:assert/strict';
import fs from 'node:fs/promises';
const base='http://127.0.0.1:4184',out=new URL('../../artifacts/studio-v5/',import.meta.url),results=[];
await fs.mkdir(out,{recursive:true});
const browser=await chromium.launch({headless:true,ignoreDefaultArgs:['--hide-scrollbars']});
try{
 const visitorContext=await browser.newContext({viewport:{width:1440,height:1000},reducedMotion:'no-preference'});
 await visitorContext.addInitScript(()=>localStorage.setItem('pd_web_token','qa-owner'));
 const guest=await visitorContext.newPage();const errors=[];guest.on('pageerror',e=>errors.push(e.message));
 guest.setDefaultTimeout(10000);
 await guest.goto(base+'/',{waitUntil:'networkidle'});
 await guest.locator('.account-trigger').click();
 await expect(guest.locator('.wallet-balances')).toBeVisible();
 const hostContext=await browser.newContext({viewport:{width:1500,height:1000},reducedMotion:'no-preference'});
 await hostContext.addInitScript(()=>sessionStorage.setItem('puppy-studio-admin','local-qa'));
 const host=await hostContext.newPage();host.setDefaultTimeout(10000);host.on('pageerror',e=>errors.push(e.message));
 await host.goto(base+'/manage?view=members',{waitUntil:'networkidle'});
 await host.locator('.member-row').filter({hasText:'qa-owner@example.test'}).click();
 const dialog=()=>host.locator('dialog[open]');
 async function entry(kind,minutes,points,note){
  await host.getByRole('button',{name:'登记一笔',exact:true}).click();
  await dialog().getByRole('combobox',{name:'记账类型',exact:true}).selectOption(kind);
  if(minutes!=null)await dialog().getByLabel('时长（小时）',{exact:true}).fill(String(minutes/60));
  if(points!=null)await dialog().getByLabel('积分数量',{exact:true}).fill(String(points));
  await dialog().getByLabel('记账说明（顾客可见）',{exact:true}).fill(note);
 }
 async function save(){await dialog().getByRole('button',{name:'保存并同步给顾客',exact:true}).click();await expect(dialog().locator('.wallet-saved')).toBeVisible();}
 await entry('topup',600,null,'QA time top-up');await save();
 await entry('gift',0,188,'QA gift 188');await save();
 await guest.getByRole('button',{name:'刷新记录',exact:true}).click();
 await expect(guest.locator('.wallet-balance.time strong')).toHaveText('10 小时');
 await expect(guest.locator('.wallet-balance.points strong')).toHaveText('188');
 await entry('redeem',null,null,'QA redemption');
 await dialog().getByLabel('抵扣金额（整数 CAD）',{exact:true}).fill('1');
 await dialog().getByLabel('本次可抵扣消费金额（CAD）',{exact:true}).fill('8.88');await save();
 await guest.getByRole('button',{name:'刷新记录',exact:true}).click();
 await expect(guest.locator('.wallet-balance.points strong')).toHaveText('88');
 await expect(guest.locator('.wallet-balance.points small')).toHaveText('可抵扣 CAD 0');
 results.push({kind:'wallet',timeTopup:true,gift188:true,wholeCadRedemption:true,remainder88Retained:true});
 // Server commits, response is lost: reload and retry must retain the original key.
 await entry('gift',0,88,'QA uncertain gift');
 await host.route('**/studio-api/manage/members/qa-owner/transactions',async route=>{
  await route.fetch();await route.fulfill({status:503,contentType:'application/json',body:'{"detail":"server_error"}'});
 });
 await dialog().getByRole('button',{name:'保存并同步给顾客',exact:true}).click();
 await expect(dialog().locator('.wallet-uncertain')).toBeVisible();
 await host.unroute('**/studio-api/manage/members/qa-owner/transactions');
 await host.reload({waitUntil:'networkidle'});
 await dialog().getByRole('button',{name:'重试这笔记账',exact:true}).click();
 await expect(dialog().locator('.wallet-balance.points strong')).toHaveText('176');
 await expect(dialog().locator('.wallet-ledger').getByText('QA uncertain gift',{exact:true})).toHaveCount(1);
 await dialog().locator('.wallet-ledger>li').filter({hasText:'QA uncertain gift'}).getByRole('button',{name:'撤销这笔',exact:true}).click();
 await dialog().getByLabel('记账说明（顾客可见）',{exact:true}).fill('QA reverse test entry');await save();
 await expect(dialog().locator('.wallet-balance.points strong')).toHaveText('88');
 results.push({kind:'retry',serverCommitLostResponse:true,reloadRecovery:true,singleEntry:true,reversal:true});
 await host.keyboard.press('Escape');
 const seed=await (await host.request.post(base+'/studio-api/qa/attended-visit')).json();
 await host.goto(base+'/manage',{waitUntil:'networkidle'});
 await host.locator('.reservation-desk-row').filter({hasText:seed.id}).click();
 await dialog().getByLabel('实际游玩时长（小时／人）',{exact:true}).fill('2.75');
 await dialog().getByLabel('实际游玩人数',{exact:true}).fill('2');
 await dialog().getByLabel('给顾客的备注',{exact:true}).fill('QA actual visit, customer visible');
 await dialog().locator('select').selectOption('completed');
 await dialog().getByRole('button',{name:'保存安排',exact:true}).click();
 await expect(host.locator('dialog[open]')).toHaveCount(0);
 await guest.getByRole('button',{name:'刷新记录',exact:true}).click();
 await expect(guest.locator('.wallet-balance.points strong')).toHaveText('188');
 await guest.getByRole('button',{name:'我的预约',exact:true}).click();
 await expect(guest.locator('.wallet-bookings')).toContainText('2 小时 45 分钟');
 await expect(guest.locator('.wallet-bookings')).toContainText('预约时长 · 2 小时');
 await host.locator('.reservation-desk-row').filter({hasText:seed.id}).click();
 await dialog().getByRole('button',{name:'删除预约',exact:true}).click();
 await dialog().getByLabel('删除／恢复原因',{exact:true}).fill('QA archive');
 await dialog().getByRole('button',{name:'确认删除预约',exact:true}).click();
 await expect(host.locator('.reservation-desk-row').filter({hasText:seed.id})).toHaveCount(0);
 await host.getByRole('button',{name:'已删除的预约',exact:true}).click();
 await host.locator('.reservation-desk-row').filter({hasText:seed.id}).click();
 await dialog().getByRole('button',{name:'恢复预约',exact:true}).click();
 await dialog().getByLabel('删除／恢复原因',{exact:true}).fill('QA restore');
 await dialog().locator('form').getByRole('button',{name:'恢复预约',exact:true}).click();
 await expect(host.locator('dialog[open]')).toHaveCount(0);
 await guest.getByRole('button',{name:'刷新记录',exact:true}).click();
 await expect(guest.locator('.wallet-bookings')).toContainText('QA actual visit, customer visible');
 results.push({kind:'attendance',booked120actual165:true,reward100:true,noAutomaticTimeDebit:true,deleteRestore:true});
 // Responsive layouts, original image ratios, live latest-three article selection.
 await guest.keyboard.press('Escape');
 const source=await (await guest.request.get(base+'/studio-api/journal')).json();
 const expected=source.posts.filter(p=>p.kind==='full'&&p.date>'2026-06-24').sort((a,b)=>b.date.localeCompare(a.date)||(b.published_at||0)-(a.published_at||0)).slice(0,3).map(p=>'/journal/'+p.id);
 for(const [width,height] of [[320,740],[390,844],[768,1024],[1024,768],[1280,720],[1440,900],[1920,1080],[2560,1440]]){
  await guest.setViewportSize({width,height});await guest.goto(base+'/',{waitUntil:'networkidle'});
  assert.deepEqual(await guest.locator('.home-journal-card').evaluateAll(nodes=>nodes.map(n=>n.getAttribute('href'))),expected);
  assert(await guest.evaluate(()=>document.documentElement.scrollWidth<=innerWidth+1));
  await guest.locator('.home-journal-grid').scrollIntoViewIfNeeded();
  if([390,1440].includes(width))await guest.screenshot({path:new URL(`home-${width}.png`,out).pathname.replace(/^\/(C:)/,'$1')});
  await guest.goto(base+'/details',{waitUntil:'networkidle'});await guest.locator('#process').scrollIntoViewIfNeeded();
  const measurements=await guest.locator('.process-step').evaluateAll(nodes=>nodes.map(n=>({height:n.getBoundingClientRect().height,photos:[...n.querySelectorAll('img')].map(img=>({w:img.clientWidth,h:img.clientHeight,nw:img.naturalWidth,nh:img.naturalHeight}))})));
  assert.equal(measurements.length,5);assert.equal(measurements.reduce((n,m)=>n+m.photos.length,0),7);
  assert(await guest.evaluate(()=>document.documentElement.scrollWidth<=innerWidth+1));
  for(const m of measurements)for(const p of m.photos)if(p.nw)assert(Math.abs(p.w/p.h-p.nw/p.nh)<.03,'photo ratio changed');
  if([390,1440].includes(width))await guest.locator('#process').screenshot({path:new URL(`process-${width}.png`,out).pathname.replace(/^\/(C:)/,'$1')});
  await guest.locator('.vision-header').scrollIntoViewIfNeeded();await guest.locator('.account-trigger').click();
  await expect(guest.locator('.wallet-balances')).toBeVisible();
  assert(await guest.locator('dialog[open] .drawer-panel').evaluate(e=>e.scrollWidth<=e.clientWidth+1));
  if([390,1440].includes(width))await guest.screenshot({path:new URL(`account-${width}.png`,out).pathname.replace(/^\/(C:)/,'$1')});
  results.push({kind:'layout',width,height,processHeight:measurements.reduce((n,m)=>n+m.height,0),uncropped:true});
  await guest.keyboard.press('Escape');
 }
 await guest.locator('.vision-header-actions .language-button').click();await guest.locator('.account-trigger').click();
 await expect(guest.locator('.wallet-balances')).toContainText('Time remaining');
 await expect(guest.locator('.wallet-balances')).toContainText('188');
 assert.deepEqual(errors,[]);results.push({kind:'language',english:true,consoleErrors:errors});
 await fs.writeFile(new URL('browser-verification.json',out),JSON.stringify(results,null,2));
 console.log(JSON.stringify(results,null,2));
}finally{await browser.close()}
