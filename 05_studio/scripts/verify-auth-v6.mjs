// Loopback fixtures only. Real Authing scanning is a separate acceptance step.
import {chromium,expect} from '@playwright/test';
import assert from 'node:assert/strict';
import fs from 'node:fs/promises';
const base='http://127.0.0.1:19676',out=new URL('../../artifacts/studio-auth-v6/',import.meta.url),results=[];
const browser=await chromium.launch({headless:true,ignoreDefaultArgs:['--hide-scrollbars']});
try{
 const context=await browser.newContext({locale:'zh-CN',viewport:{width:1440,height:1000}});
 await context.request.post(base+'/qa/reset-auth');
 await context.route('**/studio-api/auth/wechat/start',async route=>{
   const response=await route.fetch(),data=await response.json(),provider=new URL(data.url);
   await route.fulfill({response,json:{url:base+'/qa/provider?state='+provider.searchParams.get('state')}});
 });
 const tool=await context.newPage(),site=await context.newPage(),errors=[];
 for(const page of [tool,site]){page.setDefaultTimeout(12000);page.on('pageerror',e=>errors.push(e.message));}
 await tool.goto(base+'/upload');await site.goto(base+'/account');
 await expect(site.getByRole('button',{name:'微信扫码登录',exact:true})).toBeVisible();
 await site.getByRole('button',{name:'密码登录',exact:true}).click();
 await site.getByLabel('邮箱地址',{exact:true}).fill('v6@example.test');await site.getByLabel('密码',{exact:true}).fill('local-password');
 await site.locator('.account-form').getByRole('button',{name:'登录',exact:true}).click();
 await expect(site.locator('.wallet-balances')).toBeVisible();
 await expect(tool.locator('.account-trigger__name')).toHaveText('Local QA');
 await tool.locator('.account-trigger').click();await tool.getByRole('menuitem',{name:'账号中心 · 时长与积分',exact:true}).click();
 await expect(tool).toHaveURL(base+'/account');await expect(tool.locator('.wallet-balances')).toBeVisible();
 await tool.goto(base+'/upload');
 await site.getByRole('button',{name:'退出登录',exact:true}).click();
 await expect(tool.locator('.account-login')).toBeVisible();
 results.push({test:'email session shared across existing tabs, account centre, logout',passed:true});
 await site.getByRole('button',{name:'微信扫码登录',exact:true}).click();
 await expect(site.getByText(/首次使用微信/)).toBeVisible();
 await site.getByRole('button',{name:'密码登录',exact:true}).click();
 await site.getByLabel('邮箱地址',{exact:true}).fill('v6@example.test');await site.getByLabel('密码',{exact:true}).fill('local-password');
 await site.locator('.account-form').getByRole('button',{name:'登录',exact:true}).click();
 await site.getByRole('button',{name:'将微信绑定到这个账号',exact:true}).click();
 await expect(site.getByText('微信已绑定',{exact:true})).toBeVisible();
 await site.getByRole('link',{name:'继续访问',exact:true}).click();
 await expect(site.locator('.wallet-balances')).toBeVisible();
 await site.getByRole('button',{name:'退出登录',exact:true}).click();
 await site.getByRole('button',{name:'微信扫码登录',exact:true}).click();
 await expect(site).toHaveURL(base+'/account');
 await expect(site.locator('.wallet-balances')).toBeVisible();
 await expect(tool.locator('.account-trigger__name')).toHaveText('Local QA');
 results.push({test:'first WeChat email binding and subsequent WeChat-only login, fixture provider',passed:true});
 await site.getByRole('button',{name:'退出登录',exact:true}).click();
 await tool.locator('.account-login').click();
 await expect(tool).toHaveURL(base+'/account?intent=login&return_to=%2Fupload');
 results.push({test:'generator redirects to shared sign-in with safe return',passed:true});
 await site.goto(base+'/');await expect(site.locator('.vision-header-actions .language-button')).toHaveText('English');
 assert.deepEqual(await site.locator('.vision-navigation a').evaluateAll(list=>list.map(a=>a.getAttribute('href'))),['/','/visit','/shop','/journal','/upload']);
 await site.locator('.vision-navigation a[href="/visit"]').click();await expect(site).toHaveURL(base+'/visit');
 await site.goto(base+'/');
 await site.locator('.vision-header-actions .language-button').click();
 await expect(site.locator('.vision-header-actions .language-button')).toHaveText('中文');
 await site.reload();await expect(site.locator('.vision-header-actions .language-button')).toHaveText('中文');
 await site.locator('.vision-header-actions .language-button').click();
 for(const [width,height] of [[320,760],[390,844],[768,1024],[1024,768],[1280,720],[1440,900],[1920,1080],[2560,1440]]){
  await site.setViewportSize({width,height});await site.goto(base+'/account');
  assert(await site.evaluate(()=>document.documentElement.scrollWidth<=innerWidth+1),`Overflow ${width}`);
  const links=await site.locator('.vision-navigation a').evaluateAll(list=>list.map(el=>({left:el.getBoundingClientRect().left,right:el.getBoundingClientRect().right,top:el.getBoundingClientRect().top,bottom:el.getBoundingClientRect().bottom})));
  if(width>=1024){for(let i=1;i<links.length;i++)assert(links[i].left>=links[i-1].right,`nav overlap ${width}`);}
  await site.screenshot({path:new URL(`account-${width}.png`,out).pathname.replace(/^\/([A-Z]:)/,'$1')});
  results.push({test:'account and five-link header layout',width,height,passed:true});
 }
 const english=await browser.newContext({locale:'en-CA'}),englishPage=await english.newPage();await englishPage.goto(base+'/');
 await expect(englishPage.locator('.vision-header-actions .language-button')).toHaveText('中文');
 await english.close();
 const mobile=await browser.newContext({locale:'zh-CN',viewport:{width:390,height:844},userAgent:'Mozilla/5.0 (Linux; Android 14) AppleWebKit/537.36 Chrome/132.0.0.0 Mobile Safari/537.36',isMobile:true,hasTouch:true});
 const phone=await mobile.newPage();await phone.goto(base+'/account');
 await expect(phone.getByText(/手机上请使用下方邮箱登录/)).toBeVisible();
 await expect(phone.getByRole('button',{name:'微信扫码登录',exact:true})).toHaveCount(0);
 results.push({test:'fresh English locale; phone uses supported email without self-scan',passed:true});
 await mobile.close();assert.deepEqual(errors,[]);
 await fs.writeFile(new URL('ui-verification.json',out),JSON.stringify({results,errors},null,2));console.log(JSON.stringify(results));
 await context.close();
}finally{await browser.close();}
