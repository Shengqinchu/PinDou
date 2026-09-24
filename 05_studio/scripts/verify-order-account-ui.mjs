// Isolated browser fixture. All API calls are intercepted; no production data is touched.
import assert from 'node:assert/strict';
import fs from 'node:fs/promises';
import {chromium,webkit,expect} from '@playwright/test';

const base=process.env.PINDOU_STUDIO_QA_URL||'http://127.0.0.1:4184';
const output=new URL('../../artifacts/order-account-ui/',import.meta.url);
await fs.mkdir(output,{recursive:true});
async function capture(page,file){await page.screenshot({path:new URL(file,output).pathname.replace(/^\/([A-Za-z]:)/,'$1')});}
const original={id:'PS'+'A'.repeat(24),status:'manual_pending',created_at:Date.now()/1000,version:1,staff_note:'',quote:{mode:'manual',lines:[{product_id:'qa-a1',quantity:1,zh:'A1',en:'A1',total_cents:200}],subtotal_cents:200,total_cents:200,discount_cents:0},customer:{name:'QA guest',contact:'qa@example.test',notes:'无',delivery_method:'pickup',address:''}};
const orders=[original,{...original,id:'PS'+'B'.repeat(24),customer:{...original.customer,name:'Second guest'}},{...original,id:'PS'+'C'.repeat(24),customer:{...original.customer,name:'Third guest'}}];
const reservation={id:'VIS-QA-UI',status:'confirmed',can_cancel:true,booking:{date:'2026-10-01',start:'10:00',end:'12:00',plan:'hourly',guests:1},name:'QA guest',version:1,created_at:'2026-09-23T12:00:00Z',updated_at:'2026-09-23T12:00:00Z',booked_minutes:120,actual_minutes:null,actual_guests:null,public_note:''};

for(const [name,engine] of [['chromium',chromium],['webkit',webkit]]){
 const browser=await engine.launch({headless:true});
 try{
  let orderReads=0,savedAddress='not-saved';
  async function fixture(context){
   await context.addInitScript(()=>{localStorage.setItem('puppy-studio-locale','zh');localStorage.setItem('pd_web_token','fixture-token');sessionStorage.setItem('puppy-studio-admin','fixture-admin')});
   await context.route('**/studio-api/**',route=>{
    const path=new URL(route.request().url()).pathname,method=route.request().method();let response={};
    if(path==='/studio-api/manage/requests')response={items:[],total:0};
    else if(path==='/studio-api/manage/shop/orders')response={items:orders,total:orders.length};
    else if(path==='/studio-api/auth/me')response={user:{id:'qa-owner',email:'qa@example.test',nickname:'QA guest',avatar:'',is_admin:false,customer_code:'PD-QA'}};
    else if(path==='/studio-api/auth/options')response={wechat:true,miniapp_available:false};
    else if(path==='/studio-api/auth/wechat/binding')response={linked:false};
    else if(path==='/studio-api/auth/wallet')response={account:{owner_id:'qa-owner',minutes:0,points:0},entries:[],total:0};
    else if(path==='/studio-api/auth/reservations')response={items:[],total:0};
    else if(path==='/studio-api/auth/shop/orders/claim')response={claimed:0};
    else if(path==='/studio-api/auth/shop/orders'){orderReads++;response={items:orders,total:orders.length};}
    else if(path==='/studio-api/auth/booking-profile'&&method==='GET')response={owner_id:'qa-owner',name:'QA guest',contact_method:'email',contact:'qa@example.test',wechat_id:'',delivery_address:'8 Hughson St N, Hamilton',version:1,complete:true};
    else if(path==='/studio-api/auth/booking-profile'&&method==='PUT'){savedAddress=route.request().postDataJSON().delivery_address;response={owner_id:'qa-owner',name:'QA guest',contact_method:'email',contact:'qa@example.test',wechat_id:'',delivery_address:savedAddress,version:2,complete:true};}
    else if(path==='/studio-api/reservations/'+reservation.id)response=reservation;
    return route.fulfill({status:200,contentType:'application/json',body:JSON.stringify(response)});
   });
  }

  const adminContext=await browser.newContext({viewport:{width:1280,height:900},locale:'zh-CN'});
  await fixture(adminContext);
  const admin=await adminContext.newPage(),errors=[];admin.on('pageerror',error=>errors.push(error.stack||error.message));
  await admin.goto(base+'/manage?view=shop-orders');
  const rows=admin.locator('.shop-orders-admin .shop-manual-order-row');
  await expect(rows).toHaveCount(3);
  await capture(admin,`${name}-admin-desktop.png`);
  for(const width of [1280,768,390,320]){
   await admin.setViewportSize({width,height:900});
   if(await admin.locator('.desk-sidebar.expanded').count()){
    await admin.locator('.desk-mobile-close').click();
    await expect(admin.locator('.desk-sidebar')).not.toHaveClass(/expanded/);
    await admin.waitForTimeout(750);
   }
   if(width<=390){
    await expect.poll(()=>admin.locator('.desk-sidebar').evaluate(node=>node.getBoundingClientRect().right)).toBeLessThanOrEqual(1);
   }
   const boxes=await rows.evaluateAll(nodes=>nodes.map(node=>{const box=node.getBoundingClientRect();return {display:getComputedStyle(node).display,x:box.x,y:box.y,width:box.width,height:box.height}}));
   assert(boxes.every(box=>box.display==='grid'&&box.width>0&&box.height>0),`${name}: order cards lack grid layout at ${width}px`);
   assert(boxes.every((box,index)=>index===0||box.y>=boxes[index-1].y+boxes[index-1].height-1),`${name}: orders overlap at ${width}px`);
   assert(boxes.every(box=>box.x>=-1&&box.x+box.width<=width+1),`${name}: order card overflows at ${width}px`);
   if(width===390)await capture(admin,`${name}-admin-mobile.png`);
  }
  await admin.reload();await expect(rows).toHaveCount(3);
  assert.deepEqual(errors.filter(error=>!error.includes('static.cloudflareinsights.com/beacon.min.js')),[]);
  await adminContext.close();

  const accountContext=await browser.newContext({viewport:{width:390,height:844},locale:'zh-CN'});
  await fixture(accountContext);
  const page=await accountContext.newPage();page.on('pageerror',error=>errors.push(error.stack||error.message));
  await page.goto(base+'/account');
  await expect(page.locator('.account-identity')).toContainText('QA guest');
  await expect(page.locator('.account-identity .wechat-signin')).toHaveCount(0);
  const actions=page.locator('.account-content > .account-action, .account-notifications > summary');
  await expect(actions).toHaveCount(3);
  const styles=await actions.evaluateAll(nodes=>nodes.map(node=>({decoration:getComputedStyle(node).textDecorationLine,border:getComputedStyle(node).borderBottomWidth,pseudo:getComputedStyle(node,'::after').content,font:getComputedStyle(node).fontSize})));
  assert(styles.every(style=>style.decoration==='none'&&style.border==='0px'&&style.pseudo==='none'),`${name}: account action underline remains`);
  assert.equal(new Set(styles.map(style=>style.font)).size,1);
  await page.locator('.account-notifications summary').click();
  await expect(page.locator('.account-notifications')).toHaveAttribute('open','');

  await page.getByRole('button',{name:'我的订单'}).click();
  await expect(page.locator('.shop-order-history-card')).toHaveCount(3);
  await capture(page,`${name}-account-orders.png`);
  await expect(page.locator('.shop-order-history-tools')).toHaveCount(0);
  const refresh=page.locator('.wallet-toolbar .icon-button');await expect(refresh).toHaveCount(1);await expect(refresh).toBeEnabled();
  const before=orderReads;await refresh.click();await expect.poll(()=>orderReads).toBeGreaterThan(before);
  for(const width of [320,390,768,1280]){
   await page.setViewportSize({width,height:900});
   const toolbar=await page.locator('.wallet-toolbar').boundingBox(),button=await refresh.boundingBox();
   assert(toolbar&&button&&button.x>=toolbar.x&&button.x+button.width<=toolbar.x+toolbar.width+1,`${name}: refresh leaves common tab bar at ${width}px`);
  }

  await page.locator('.account-edit').click();
  await expect(page.locator('.profile-form .wechat-link')).toBeVisible();
  await page.locator('.profile-form .booking-profile-section summary').click();
  await expect(page.locator('.booking-profile-help')).toHaveText('填写信息可用于预约到店或商品收货。');
  await expect(page.getByLabel('收货地址',{exact:true})).toBeVisible();
  await page.getByLabel('收货地址',{exact:true}).fill('');
  await page.locator('.profile-actions button').last().click();
  await expect.poll(()=>savedAddress).toBe('');
  await page.setViewportSize({width:390,height:844});
  await page.goto(base+'/');
  await page.locator('.account-trigger').click();
  await expect(page.locator('.studio-drawer[open] .account-content')).toBeVisible();
  await expect(page.locator('.studio-drawer[open] .account-identity .wechat-signin')).toHaveCount(0);
  await expect(page.locator('.studio-drawer[open] .account-action')).toHaveCount(3);
  await capture(page,`${name}-account-drawer.png`);
  await page.goto(base+'/reservation/'+reservation.id);
  await expect(page.locator('.reservation-receipt-actions')).toBeVisible();
  await expect(page.locator('.reservation-receipt-actions button')).toHaveCount(2);
  await expect(page.locator('.reservation-receipt-actions')).not.toContainText('联系店主');
  await expect(page.locator('.reservation-receipt-contacts')).toContainText('staywithcsq@outlook.com');
  await capture(page,`${name}-reservation.png`);
  assert.deepEqual(errors.filter(error=>!error.includes('static.cloudflareinsights.com/beacon.min.js')),[]);
  await accountContext.close();
  console.log(`${name}: cold admin order layout, account tabs/actions, optional address and receipt OK`);
 }finally{await browser.close()}
}
