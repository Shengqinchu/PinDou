// Live smoke check: public reads only; never submits a customer order.
import assert from 'node:assert/strict';
import { chromium, expect } from '@playwright/test';

const base=process.env.PINDOU_STUDIO_QA_URL||'https://pindoupuppy.com';
const expected=process.env.PINDOU_STUDIO_EXPECT_BUILD||'';
const browser=await chromium.launch({headless:true});
try{
 const context=await browser.newContext({locale:'zh-CN',viewport:{width:390,height:844}});
 await context.addInitScript(()=>localStorage.setItem('puppy-studio-locale','zh'));
 const page=await context.newPage(),errors=[];
 page.on('pageerror',error=>errors.push(error.message));
 const version=await (await page.request.get(base+'/version.json')).json();
 assert(!expected||version.build===expected,`Unexpected production build: ${version.build}`);
 const health=await (await page.request.get(base+'/studio-api/health')).json();
 assert.equal(health.status,'ok');
 assert.equal((await page.request.get(base+'/studio-api/auth/shop/orders')).status(),401);
 assert.equal((await page.request.get(base+'/studio-api/manage/shop/orders')).status(),401);
 await page.goto(base+'/shop?view=cart');
 await expect(page.locator('.studio-drawer[open] .shop-notice').first()).toContainText('下单后店主会主动联系您');
 await expect(page.getByRole('heading',{name:'拼豆小店'})).toBeVisible();
 assert.deepEqual(errors,[]);
 console.log(JSON.stringify({publicBuild:version.build,health:health.status,cartNotice:true,privateOrdersProtected:true}));
}finally{await browser.close()}
