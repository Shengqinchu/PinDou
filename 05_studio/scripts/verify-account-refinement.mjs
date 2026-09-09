// Isolated loopback fixture only; never writes to a real customer account.
import {chromium,webkit,expect} from '@playwright/test';
import assert from 'node:assert/strict';
import fs from 'node:fs/promises';
import AxeBuilder from '@axe-core/playwright';
const base='http://127.0.0.1:19676',out=new URL('../../artifacts/account-refinement/',import.meta.url),results=[];
const browser=await chromium.launch({headless:true,ignoreDefaultArgs:['--hide-scrollbars']});
const errors=[];
async function login(page,email){
 await page.goto(base+'/account');await page.getByRole('button',{name:'密码登录',exact:true}).click();
 await page.getByLabel('邮箱地址',{exact:true}).fill(email);await page.getByLabel('密码',{exact:true}).fill('local-password');
 await page.locator('.account-form').getByRole('button',{name:'登录',exact:true}).click();await expect(page.locator('.wallet-balances')).toBeVisible();
}
try{
 const context=await browser.newContext({locale:'zh-CN',viewport:{width:1440,height:960}});
 const page=await context.newPage(),tool=await context.newPage();
 for(const p of [page,tool]){p.setDefaultTimeout(12000);p.on('pageerror',e=>errors.push(e.message));}
 const email=`profile-${Date.now()}@example.test`;
 await login(page,email);await tool.goto(base+'/tools');
 await expect(page.locator('.account-content').getByText('已登录',{exact:true})).toHaveCount(0);
 await expect(page.locator('.account-content a[href="/tools"]')).toHaveCount(0);
 await expect(page.locator('.wallet-rule,.wallet-rules,.wallet-sync')).toHaveCount(0);
 await expect(page.getByText('暂无时长记录',{exact:true})).toBeVisible();
 const tips=page.getByRole('tooltip'),pointTip=page.getByRole('button',{name:'积分说明',exact:true});
 await expect(tips).toHaveCount(0);await pointTip.hover();await expect(tips).toContainText('100 积分抵扣 CAD 1');
 await tips.hover();await expect(tips).toBeVisible();await page.keyboard.press('Escape');await expect(tips).toHaveCount(0);
 await pointTip.focus();await page.keyboard.press('Tab');await pointTip.focus();await expect(tips).toBeVisible();
 await page.keyboard.press('Escape');await expect(tips).toHaveCount(0);
 await page.getByRole('button',{name:'积分明细',exact:true}).click();await expect(page.getByText('暂无积分记录',{exact:true})).toBeVisible();
 await page.screenshot({path:new URL('desktop.png',out).pathname.replace(/^\/([A-Z]:)/,'$1'),fullPage:true});
 results.push({test:'simplified account and hover/focus/Escape hints',passed:true});
 const edit=()=>page.getByRole('button',{name:'编辑资料',exact:true}).click();
 const dialog=page.locator('dialog[open]').last(),name=dialog.locator('input[autocomplete="nickname"]');
 await edit();await expect(dialog).toBeVisible();await expect(dialog.getByText(email,{exact:true})).toBeVisible();
 await name.fill('A'.repeat(21));await expect(dialog.getByRole('button',{name:'保存',exact:true})).toBeDisabled();
 await name.fill('  小狗 同学  ');await dialog.getByRole('button',{name:'保存',exact:true}).click();
 await expect(page.locator('.account-identity strong')).toHaveText('小狗 同学');await expect(tool.locator('.account-trigger__name')).toHaveText('小狗 同学');
 await page.reload();await expect(page.locator('.account-identity strong')).toHaveText('小狗 同学');
 await edit();await name.fill('Unsaved');await dialog.getByRole('button',{name:'取消',exact:true}).click();await expect(page.locator('.account-identity strong')).toHaveText('小狗 同学');
 results.push({test:'shared nickname update, trim, limit, cancellation and reload',passed:true});
 await edit();const upload=dialog.locator('input[type=file]');
 await upload.setInputFiles({name:'bad.svg',mimeType:'image/svg+xml',buffer:Buffer.from('<svg/>')});await expect(dialog.getByRole('alert')).toContainText('请选择 JPG');
 await upload.setInputFiles({name:'large.png',mimeType:'image/png',buffer:Buffer.alloc(2*1024*1024+1)});await expect(dialog.getByRole('alert')).toContainText('不能超过 2 MB');
 const png=await fs.readFile(new URL('../public/studio-brand/puppy-icon-192-v6.png',import.meta.url));
 await upload.setInputFiles({name:'puppy.png',mimeType:'image/png',buffer:png});
 await dialog.getByRole('button',{name:'保存',exact:true}).click();
 await expect(page.locator('img.account-portrait')).toBeVisible();await expect(tool.locator('img.account-avatar')).toBeVisible();
 assert.equal(await page.locator('img.account-portrait').evaluate(el=>el.naturalWidth),256);
 await page.reload();await expect(page.locator('img.account-portrait')).toBeVisible();
 results.push({test:'avatar format/size validation, upload, shared display and reload',passed:true});
 await edit();await name.fill('Partial save');await upload.setInputFiles({name:'puppy.png',mimeType:'image/png',buffer:png});
 await page.route('**/api/v1/user/avatar',r=>r.fulfill({status:503,json:{error:'UNAVAILABLE'}}));
 await dialog.getByRole('button',{name:'保存',exact:true}).click();await expect(dialog.getByRole('alert')).toHaveText('昵称已保存；头像未确认保存，请重试。');
 await expect(name).toHaveValue('Partial save');await expect(dialog.locator('.profile-preview')).toHaveAttribute('src',/^blob:/);
 await page.unroute('**/api/v1/user/avatar');await dialog.getByRole('button',{name:'保存',exact:true}).click();await expect(page.locator('.account-identity strong')).toHaveText('Partial save');
 results.push({test:'partial failure retains pending avatar and retries without losing saved nickname',passed:true});
 await page.route('**/studio-api/auth/wechat/binding',r=>r.fulfill({json:{linked:true}}));await page.reload();
 await expect(page.getByText('微信已绑定',{exact:true})).toBeVisible();await page.getByRole('button',{name:'微信绑定说明',exact:true}).click();await expect(tips).toContainText('未提供真实微信昵称');await page.keyboard.press('Escape');
 for(const width of [320,375,390,768,1024,1440,1920,2560]){
   await page.setViewportSize({width,height:900});await expect(page.locator('.wallet-balances')).toBeVisible();
   assert(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth+1));
   await pointTip.click();await expect(tips).toBeVisible();
   const bounds=await tips.boundingBox();assert(bounds.x>=0&&bounds.x+bounds.width<=width+1);await page.keyboard.press('Escape');
   await edit();await expect(dialog).toHaveAttribute('data-phase','open');await expect(name).toBeVisible();
   assert(await dialog.evaluate(el=>el.scrollWidth<=el.clientWidth+1),`Editor overflow at ${width}px`);
   await dialog.getByRole('button',{name:'取消',exact:true}).click();await expect(dialog).toHaveCount(0);
 }
 await page.setViewportSize({width:390,height:844});await page.screenshot({path:new URL('mobile.png',out).pathname.replace(/^\/([A-Z]:)/,'$1'),fullPage:true});
 await page.locator('.vision-header-actions .language-button').click();await expect(page.getByRole('button',{name:'Edit profile',exact:true})).toBeVisible();
 const axe=await new AxeBuilder({page}).include('.account-page').analyze();assert.deepEqual(axe.violations.map(v=>({id:v.id,nodes:v.nodes.length})),[]);
 results.push({test:'bound WeChat description, 8 widths, Chinese/English, axe account accessibility',passed:true});
 // A late save must never restore the previous login or write its profile into another account.
 await page.locator('.vision-header-actions .language-button').click();await edit();await name.fill('Stale response');
 let release,requested;const arrived=new Promise(r=>requested=r),wait=new Promise(r=>release=r);
 await page.route('**/api/v1/user/profile',async r=>{if(r.request().method()!=='PATCH')return r.continue();await r.fetch();requested();await wait;await r.fulfill({json:{user_id:'qa-owner',email:'another@example.test',nickname:'Stale response'}});});
 await dialog.getByRole('button',{name:'保存',exact:true}).click();await arrived;
 await page.evaluate(()=>{localStorage.removeItem('pd_web_token');localStorage.removeItem('pd_web_user');window.dispatchEvent(new Event('focus'));});
 release();await expect(page.getByRole('button',{name:'密码登录',exact:true})).toBeVisible();assert.equal(await page.evaluate(()=>localStorage.getItem('pd_web_token')),null);
 results.push({test:'late profile response cannot restore a signed-out account',passed:true});
 assert.deepEqual(errors,[]);await context.close();
 const touch=await browser.newContext({locale:'zh-CN',viewport:{width:390,height:844},isMobile:true,hasTouch:true,userAgent:'Mozilla/5.0 (iPhone; CPU iPhone OS 18_0 like Mac OS X) AppleWebKit/605.1.15 Version/18.0 Mobile/15E148 Safari/604.1'});
 const mobile=await touch.newPage();await login(mobile,'touch-profile@example.test');
 await mobile.getByRole('button',{name:'积分说明',exact:true}).tap();await expect(mobile.getByRole('tooltip')).toBeVisible();
 await mobile.getByRole('button',{name:'积分说明',exact:true}).tap();await expect(mobile.getByRole('tooltip')).toHaveCount(0);
 await mobile.getByRole('button',{name:'时长说明',exact:true}).tap();await mobile.locator('h1').tap();await expect(mobile.getByRole('tooltip')).toHaveCount(0);
 await touch.close();results.push({test:'touch tap toggles and outside dismissal',passed:true});
}finally{await browser.close();await fs.writeFile(new URL('verification.json',out),JSON.stringify({results,errors},null,2));}
console.log(JSON.stringify(results,null,2));
