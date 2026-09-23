import assert from 'node:assert/strict';
import fs from 'node:fs/promises';
import { chromium } from 'playwright';

const base=process.env.PINDOU_SHOP_URL||'https://pindoupuppy.com';
const expected={a:4000,b:5000,c:4500,d:4000,e:3600,f:3800,g:3200,h:3500,m:2300};
const browser=await chromium.launch({headless:true});
try{
 const context=await browser.newContext({viewport:{width:390,height:844},locale:'zh-CN'});
 const page=await context.newPage();page.setDefaultTimeout(15000);
 await page.route('**/studio-api/shop/orders',route=>route.abort());
 const catalog=await(await page.request.get(base+'/studio-api/shop/catalog')).json();
 const refills=catalog.products.filter(p=>/^refill-[a-hm]$/.test(p.shop_category_id||''));
 assert.equal(refills.length,230);
 for(const p of refills){const series=p.shop_category_id.at(-1);assert.equal(p.price_cents,p.code.endsWith(' SET')?expected[series]:200,p.code);assert.equal(p.stock,999,p.code);}
 const a1=refills.find(p=>p.code==='A1'),bset=refills.find(p=>p.code==='B SET');
 const response=await page.request.post(base+'/studio-api/shop/cart/quote',{data:{items:[a1,bset].map(p=>({product_id:p.id,quantity:1,variant_id:'',choice_id:''}))}});
 assert.equal(response.status(),200);assert.equal((await response.json()).total_cents,5200);
 await page.goto(base+'/shop');
 await page.locator('.shop-name').filter({hasText:/^A1$/}).click();
 await page.locator('.studio-drawer[open] .drawer-bottom button').click();
 await page.waitForFunction(()=>!document.querySelector('.studio-drawer')?.open);
 await page.getByText('加入成功！',{exact:true}).waitFor();
 await page.locator('.shop-cart-notice .notice-action').click();
 await page.getByRole('button',{name:'提交订单'}).click();
 await page.waitForURL('**/shop/checkout');
 await page.getByRole('heading',{name:'请填写收货信息'}).waitFor();
 await page.getByText('8 Hughson St N, Hamilton, ON L8R 0B1').waitFor();
 const folder=new URL('../../artifacts/shop-checkout-20260923/',import.meta.url);await fs.mkdir(folder,{recursive:true});
 await page.screenshot({path:new URL('production-checkout-readonly.png',folder).pathname.replace(/^\/([A-Za-z]:)/,'$1')});
 console.log('Live read-only shop check passed: 230 prices, stock, CAD 52 quote, cart and delivery page; no order submitted');
}finally{await browser.close()}
