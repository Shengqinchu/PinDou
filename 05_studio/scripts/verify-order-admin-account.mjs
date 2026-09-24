// Disposable browser fixture; all writes are intercepted on loopback.
import assert from 'node:assert/strict';
import {chromium,expect} from '@playwright/test';
const base=process.env.PINDOU_STUDIO_QA_URL||'http://127.0.0.1:4184';
const browser=await chromium.launch({headless:true});
const order={id:'PS'+'B'.repeat(24),status:'manual_pending',created_at:Date.now()/1000,expires_at:0,hold_until:0,paid_at:null,fulfillment:'awaiting_contact',version:1,staff_note:'',quote:{mode:'manual',lines:[{product_id:'qa-a1',quantity:2,zh:'A1',en:'A1',kind:'physical',image:'',unit_cents:200,total_cents:400}],subtotal_cents:400,total_cents:400,tax_cents:0,cny_fen:0},customer:{name:'QA guest',contact:'qa@example.test',contact_method:'email',notes:'无',delivery_method:'pickup',address:''}};
let current={...order},deleted=false,address='8 Hughson St N, Hamilton',savedAddress='';
try{
 const context=await browser.newContext({viewport:{width:1280,height:900},locale:'zh-CN'});
 await context.addInitScript(()=>{localStorage.setItem('puppy-studio-locale','zh');localStorage.setItem('pd_web_token','fixture-token');sessionStorage.setItem('puppy-studio-admin','fixture-admin')});
 const page=await context.newPage(),errors=[];page.on('pageerror',error=>errors.push(error.message));
 await page.route('**/studio-api/**',async route=>{
  const url=new URL(route.request().url()),path=url.pathname,method=route.request().method();let response={};let status=200;
  if(path==='/studio-api/manage/requests')response={items:[],total:0};
  else if(path==='/studio-api/manage/shop/orders'&&method==='GET')response={items:deleted?[]:[current],total:deleted?0:1};
  else if(path==='/studio-api/manage/orders/'+order.id)response=current;
  else if(path==='/studio-api/manage/shop/orders/'+order.id&&method==='PATCH'){const body=route.request().postDataJSON();current={...current,status:body.status,version:current.version+1,staff_note:body.staff_note};response=current;}
  else if(path==='/studio-api/manage/shop/orders/'+order.id&&method==='DELETE'){deleted=true;response={id:order.id,deleted:true};}
  else if(path==='/studio-api/auth/me')response={user:{id:'qa-owner',email:'qa@example.test',nickname:'QA guest',avatar:'',is_admin:false,customer_code:'PD-QA'}};
  else if(path==='/studio-api/auth/options')response={wechat:true,miniapp_available:false};
  else if(path==='/studio-api/auth/wechat/binding')response={linked:false};
  else if(path==='/studio-api/auth/wallet')response={account:{owner_id:'qa-owner',minutes:0,points:0},entries:[],total:0};
  else if(path==='/studio-api/auth/reservations')response={items:[],total:0};
  else if(path==='/studio-api/auth/shop/orders/claim')response={claimed:0};
  else if(path==='/studio-api/auth/shop/orders')response={items:[current],total:1};
  else if(path==='/studio-api/auth/booking-profile'&&method==='GET')response={owner_id:'qa-owner',name:'QA guest',contact_method:'email',contact:'qa@example.test',wechat_id:'',delivery_address:address,version:1,complete:true};
  else if(path==='/studio-api/auth/booking-profile'&&method==='PUT'){savedAddress=route.request().postDataJSON().delivery_address;address=savedAddress;response={owner_id:'qa-owner',name:'QA guest',contact_method:'email',contact:'qa@example.test',wechat_id:'',delivery_address:address,version:2,complete:true};}
  await route.fulfill({status,contentType:'application/json',body:JSON.stringify(response)});
 });
 await page.goto(base+'/manage?view=shop-orders');
 await expect(page.locator('.shop-orders-admin')).toBeVisible();
 await expect(page.locator('.desk-navigation')).toContainText('商品订单');
 await expect(page.locator('.desk-navigation')).not.toContainText('顾客消息');
 await page.locator('.shop-manual-order-row').click();
 await page.locator('#shop-order-status select').selectOption('manual_preparing');
 await page.locator('button[form="shop-order-status"]').click();
 await expect(page.locator('.shop-manual-order-row')).toContainText('备货中');
 await page.locator('.shop-manual-order-row').click();
 await page.getByRole('button',{name:'删除订单'}).first().click();
 await expect(page.getByText('删除后订单将从正常列表移除，历史记录仍保留用于查账。确定删除吗？')).toBeVisible();
 await page.locator('.shop-order-delete-confirm .admin-delete-button').click();
 await expect(page.locator('.shop-manual-order-row')).toHaveCount(0);
 await page.goto(base+'/account');
 await expect(page.locator('.account-identity')).toContainText('QA guest');
 await expect(page.getByRole('link',{name:'staywithcsq@outlook.com'})).toBeVisible();
 await page.getByRole('button',{name:'我的订单'}).click();
 await expect(page.locator('.shop-order-history-card')).toContainText('A1 × 2');
 await page.locator('.account-edit').click();
 await expect(page.locator('.profile-form .wechat-link')).toContainText('绑定微信');
 await expect(page.locator('.profile-form .booking-profile-section')).not.toHaveAttribute('open','');
 await expect(page.locator('.profile-form .profile-contact')).toBeHidden();
 await page.locator('.profile-form .booking-profile-section summary').click();
 await expect(page.locator('.profile-form .profile-contact')).toBeVisible();
 await expect(page.locator('.profile-form .booking-profile-toggle')).toBeVisible();
 await expect(page.locator('.profile-form').getByLabel('称呼')).toBeVisible();
 await page.getByLabel('收货地址（选填）').fill('75 John St N, Hamilton');
 await page.locator('.profile-actions button').last().click();
 assert.equal(savedAddress,'75 John St N, Hamilton');
 assert.deepEqual(errors,[]);
 console.log('admin order status/delete and account orders/address OK');
}finally{await browser.close()}
