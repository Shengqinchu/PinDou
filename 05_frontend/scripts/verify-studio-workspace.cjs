// Disposable browser fixture only. No request is sent to a production API.
const {createRequire}=require('node:module'),fs=require('node:fs'),path=require('node:path'),http=require('node:http'),assert=require('node:assert/strict');
const {chromium,webkit,expect}=createRequire(path.resolve(__dirname,'../../05_studio/package.json'))('@playwright/test');
const root=path.resolve(__dirname,'../..'),out=path.resolve(process.env.STUDIO_TEST_OUT||path.join(root,'artifacts/miniapp-smooth-20260915'));fs.mkdirSync(out,{recursive:true});
const build=path.resolve(process.env.STUDIO_QA_BUILD||path.join(root,'05_frontend/dist/build/h5'));
const server=http.createServer((req,res)=>{const pathname=decodeURIComponent(new URL(req.url,'http://localhost').pathname);const file=path.resolve(build,pathname.replace(/^\/h5\/?/,'')||'index.html');if(!file.startsWith(build+path.sep)&&file!==path.join(build,'index.html')){res.writeHead(403).end();return;}try{res.setHeader('Content-Type',({'.js':'application/javascript','.css':'text/css','.html':'text/html','.svg':'image/svg+xml','.png':'image/png','.webp':'image/webp','.jpg':'image/jpeg'}[path.extname(file)]||'application/octet-stream'));res.end(fs.readFileSync(file));}catch{res.writeHead(404).end();}});
const checks=[];
async function run(browser,engine,lang,width,height){
 const context=await browser.newContext({viewport:{width,height},locale:lang==='zh'?'zh-CN':'en-CA'}),page=await context.newPage(),calls=[],errors=[];
 const origin=`http://127.0.0.1:${server.address().port}`,base=origin+'/h5/';
 page.setDefaultTimeout(6500);page.on('pageerror',e=>errors.push(e.message));
 const person={id:'smooth-fixture',user_id:'smooth-fixture',nickname:'Fixture Owner',email:'owner@example.invalid',is_admin:true,customer_code:'PD-QA'};
 const contact={owner_id:person.id,name:'Fixture Owner',contact_method:'wechat',contact:'fixture',complete:true,version:1};
 const reservations=Array.from({length:20},(_,i)=>({id:'VIS-FIXTURE'+i,name:'Guest '+i,status:'pending',version:1,booking:{date:'2026-09-18',start:'18:30',end:'20:30',guests:1,plan:'hourly'},payload:{notes:''},can_cancel:true}));
 await context.addInitScript(({lang,person})=>{const set=(key,data,type)=>localStorage.setItem(key,JSON.stringify({type,data}));set('pd_token','smooth-fixture-token','string');set('pd_user',JSON.stringify(person),'string');set('pd_studio_language',lang,'string');},{lang,person});
 let slowOwner=false;
 await context.route('**/*',async route=>{
  const request=route.request(),url=request.url(),p=new URL(url).pathname;
  if(url.includes('/studio-api/')||url.includes('/api/v1/')){
   if(request.method()==='OPTIONS')return route.fulfill({status:204,headers:{'Access-Control-Allow-Origin':'*','Access-Control-Allow-Headers':'*','Access-Control-Allow-Methods':'GET,POST,PUT,OPTIONS'}});
   calls.push({path:p,method:request.method(),query:new URL(url).search});let data={};
   if(p.endsWith('/user/profile'))data=person;
   else if(p.endsWith('/auth/me'))data={user:person};
   else if(p.endsWith('/auth/wallet'))data={account:{minutes:120,points:166},booking_profile:contact};
   else if(p.endsWith('/auth/owner-notifications')){if(slowOwner)await new Promise(r=>setTimeout(r,2500));data={bound:true};}
   else if(p.endsWith('/auth/reservations'))data={items:reservations,total:20};
   else if(p.endsWith('/manage/desk-summary'))data={today:'2026-09-18',pending:20,visits:2,unread:0,finance:{income_cents:1234,expense_cents:100,needs_amount:0}};
   else if(p.endsWith('/manage/reservations'))data={items:reservations,total:20};
   else if(p.endsWith('/manage/messages/threads'))data={items:[],next_cursor:null,bridge:{online:true,sender:'fixture'}};
   else if(p.endsWith('/manage/finance'))data={items:[],total:0,categories:[],summary:{income_cents:1234,expense_cents:100,balance_cents:1134,needs_amount:0}};
   else if(p.endsWith('/manage/members'))data={items:[],total:0};
   else if(p.endsWith('/content'))data={modules:{}};
   else if(p.endsWith('/cancellation'))data={limit:3,remaining:3,used:0,eligible:true,version:1};
   return route.fulfill({status:200,headers:{'Access-Control-Allow-Origin':'*'},contentType:'application/json',body:JSON.stringify(data)});
  }
  if(url.startsWith(origin)||url.startsWith('data:')||url.startsWith('blob:'))return route.continue();return route.abort();
 });
 const visible=s=>page.locator(s).filter({visible:true}),tabs=()=>visible('.admin-native-tabs').locator('uni-button'),nav=()=>visible('.studio-app-nav').locator('uni-button');
 const count=s=>calls.filter(c=>c.path.endsWith(s)).length;
 try{
  await page.goto(base+'#/pages/studio/manage');await visible('.admin-home-number').first().waitFor();
  await tabs().nth(1).click();await expect(visible('.admin-booking-card')).toHaveCount(20);
  await visible('.admin-input').locator('input').fill('remember this filter');
  await visible('.admin-native-body').evaluate(el=>{const scroll=[el,...el.querySelectorAll('*')].find(n=>n.scrollHeight>n.clientHeight+150&&/scroll|auto/.test(getComputedStyle(n).overflowY));if(!scroll)throw Error('No admin scroller');window.__keptScroll=scroll;scroll.scrollTop=350;});
  const reads=count('/manage/reservations'),timings=[];
  for(let i=0;i<5;i++){
   await tabs().nth(0).click();await visible('.admin-home-number').first().waitFor();
   const start=Date.now();await tabs().nth(1).click();await visible('.admin-booking-card').first().waitFor();timings.push(Date.now()-start);
  }
  assert.equal(count('/manage/reservations'),reads,'Warm tab must not refetch');
  assert.equal(await visible('.admin-input').locator('input').inputValue(),'remember this filter');
  const kept=await visible('.admin-native-body').evaluate(el=>({same:el.contains(window.__keptScroll),top:window.__keptScroll.scrollTop}));
  if(!process.env.STUDIO_QA_BASELINE){assert(kept.same,'Retain rendered list instance');assert(Math.abs(kept.top-350)<3,'Retain actual scroll position');}
  await tabs().nth(2).click();await page.locator('.native-message-threads').waitFor({state:'attached'});await page.waitForTimeout(100);const messageReads=count('/manage/messages/threads');
  await tabs().nth(3).click();await visible('.native-finance-totals').waitFor();await page.waitForTimeout(5200);assert.equal(count('/manage/messages/threads'),messageReads,'Hidden message pane must not poll');
  await tabs().nth(0).click();await visible('.admin-home-links').waitFor();await visible('.admin-home-links').locator('uni-button').nth(3).click();await page.locator('.native-member-list').waitFor({state:'attached'});await visible('.admin-native-heading').locator('uni-button').first().click();await visible('.admin-home-number').first().waitFor();
  await tabs().nth(1).click();await visible('.admin-booking-card').first().waitFor();assert.equal(await visible('.admin-input').locator('input').inputValue(),'remember this filter');
  await page.screenshot({path:path.join(out,`admin-${engine}-${lang}-${width}.png`)});
  // Cold account: nonessential owner metadata delayed 2.5 seconds.
  slowOwner=true;const start=Date.now();await page.goto(base+'#/pages/auth/studio-account');await visible('.studio-native-name').filter({hasText:'Fixture Owner'}).waitFor();await visible('.studio-native-balance-value').filter({hasText:'166'}).waitFor();const accountReady=Date.now()-start;
  if(!process.env.STUDIO_QA_BASELINE)assert(accountReady<1800,'Owner metadata must not block the profile or wallet');
  await nav().nth(1).click();await visible('.studio-booking-card').first().waitFor();await nav().nth(0).click();await visible('.studio-home').waitFor();await nav().nth(2).click();await visible('.studio-account').waitFor();
  let brandContinuity;
  if(!process.env.STUDIO_QA_BASELINE){
   await expect(page.locator('.studio-native-top')).toHaveCount(1);
   await expect(page.locator('.studio-app-nav')).toHaveCount(1);
   await page.locator('.studio-brand-window').evaluate(el=>{window.__fixedBrand=el;window.__fixedNav=document.querySelector('.studio-app-nav');window.__brandFrames=[];window.__brandTracking=true;const sample=()=>{if(!window.__brandTracking)return;const r=el.getBoundingClientRect(),s=getComputedStyle(el);window.__brandFrames.push({connected:el.isConnected,x:r.x,y:r.y,width:r.width,height:r.height,opacity:s.opacity,visibility:s.visibility});requestAnimationFrame(sample);};requestAnimationFrame(sample);});
   for(let i=0;i<3;i++){await nav().nth(0).click();await visible('.studio-home').waitFor();await nav().nth(1).click();await visible('.studio-booking-card').first().waitFor();await nav().nth(2).click();await visible('.studio-account').waitFor();}
   brandContinuity=await page.evaluate(()=>{window.__brandTracking=false;return {sameLogo:window.__fixedBrand===document.querySelector('.studio-brand-window'),sameNav:window.__fixedNav===document.querySelector('.studio-app-nav'),frames:window.__brandFrames};});
   brandContinuity.layout=await page.evaluate(()=>({scrollY,window:innerHeight,body:document.body.scrollHeight,shells:[...document.querySelectorAll('.studio-native')].map(el=>({classes:el.className,style:el.getAttribute('style'),rect:el.getBoundingClientRect().toJSON(),css:{height:getComputedStyle(el).height,padding:getComputedStyle(el).padding,minHeight:getComputedStyle(el).minHeight}})),parents:(()=>{const result=[];let el=document.querySelector('.studio-brand-window');while(el){result.push({tag:el.tagName,classes:el.className,rect:el.getBoundingClientRect().toJSON()});el=el.parentElement;}return result;})()}));
   fs.writeFileSync(path.join(out,`brand-${engine}-${lang}-${width}.json`),JSON.stringify(brandContinuity,null,2));
   assert(brandContinuity.sameLogo&&brandContinuity.sameNav,'Keep a single header image and dock across tab switches');
   assert(brandContinuity.frames.length>0);const first=brandContinuity.frames[0];
   assert(brandContinuity.frames.every(f=>f.connected&&f.opacity==='1'&&f.visibility==='visible'&&f.width>0&&f.x===first.x&&f.y===first.y&&f.height===first.height),'Logo must remain visible at one position throughout switching');
  }
  // Capture settled text and typefaces, after the functional entry animation.
  await page.waitForTimeout(250);
  await page.screenshot({path:path.join(out,`account-${engine}-${lang}-${width}.png`)});
  const layout=await page.evaluate(()=>({width:innerWidth,body:document.body.scrollWidth,buttons:[...document.querySelectorAll('.studio-app-nav uni-button')].filter(e=>e.getClientRects().length).map(e=>{const r=e.getBoundingClientRect();return {top:r.top,bottom:r.bottom,height:r.height};})}));
  assert(layout.body<=width+1);assert(layout.buttons.every(b=>b.top>=0&&b.bottom<=height+1&&b.height>=40));
  assert.deepEqual(errors,[]);assert(calls.every(c=>c.method==='GET'),'No production-like writes in performance fixture');
  if(!process.env.STUDIO_QA_BASELINE){
   await visible('.studio-account-end .studio-native-link').click();await page.locator('.studio-native-form').waitFor();
   await page.waitForTimeout(2600);
   assert.equal(await visible('.studio-native-profile').count(),0,'Late optional response must not restore a logged-out profile');
   assert.equal(await visible('.admin-native').count(),0,'Logout must discard retained private panes');
  }
  checks.push({engine,lang,width,height,retained:kept,warm_switch_ms:timings,account_ready_ms:accountReady,brand_continuity:brandContinuity,layout,passed:true});
 }catch(e){await page.screenshot({path:path.join(out,'failure.png')});console.error(JSON.stringify({engine,lang,calls,errors,body:(await page.locator('body').innerText()).slice(-2500)}));throw e;}
 finally{await context.close();}
}
(async()=>{await new Promise(r=>server.listen(0,'127.0.0.1',r));for(const [name,type] of process.argv.includes('--probe')?(process.argv.includes('--webkit')?[['webkit',webkit]]:[['chromium',chromium]]):[['chromium',chromium],['webkit',webkit]]){const browser=await type.launch({headless:true});try{for(const lang of process.argv.includes('--probe')?['zh']:['zh','en'])for(const [w,h] of process.argv.includes('--probe')?[[390,844]]:[[390,844],[844,390]])await run(browser,name,lang,w,h);}finally{await browser.close();}}fs.writeFileSync(path.join(out,process.env.STUDIO_QA_BASELINE?'baseline-results.json':process.argv.includes('--probe')?'workspace-probe-'+checks[0].engine+'.json':'workspace-results.json'),JSON.stringify(checks,null,2));console.log(JSON.stringify(checks));})().catch(e=>{console.error(e.stack);process.exitCode=1}).finally(()=>server.close());
