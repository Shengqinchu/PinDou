// Browser rendering of the native uni-app pages. All external traffic is mocked.
const fs=require('fs'),path=require('path'),http=require('http'),assert=require('node:assert/strict');
const {chromium,webkit,expect}=require('../../05_studio/node_modules/@playwright/test');
const root=path.resolve(__dirname,'../..'),build=path.join(root,'05_frontend/dist/build/h5'),out=path.join(root,'artifacts/miniapp-patch');
fs.mkdirSync(out,{recursive:true});
const server=http.createServer((req,res)=>{const p=new URL(req.url,'http://localhost').pathname,f=path.resolve(build,p.replace(/^\/h5\/?/,'')||'index.html');if(!f.startsWith(build+path.sep))return res.writeHead(403).end();try{res.setHeader('Content-Type',({'.js':'application/javascript','.css':'text/css','.html':'text/html','.svg':'image/svg+xml','.webp':'image/webp','.png':'image/png'}[path.extname(f)]||'application/octet-stream'));res.end(fs.readFileSync(f));}catch{res.writeHead(404).end();}});
const clock=n=>String(Math.floor(n/60)).padStart(2,'0')+':'+String(n%60).padStart(2,'0');
const cal=experience=>({experience,today:'2026-10-01',timezone:'America/Toronto',minimum_minutes:experience==='patch'?60:120,max_guests_per_group:6,policy_version:8,days:Array.from({length:14},(_,i)=>({date:'2026-10-'+String(i+1).padStart(2,'0'),open:'10:00',close:'22:00',closed:false,slots:Array.from({length:24},(_,j)=>({start:clock(600+j*30),end:clock(630+j*30),available:!(i===0&&experience==='patch'&&j<2),start_available:j<23&&!(i===0&&j<2),reason:null,low_capacity:false,remaining_seats:6}))}))});
const guest={id:'mini-patch-qa',nickname:'QA Guest',email:'qa@example.invalid',is_admin:true};
const contact={owner_id:guest.id,name:'QA Guest',contact_method:'wechat',contact:'qa-only',version:1,complete:true};
const entry={id:'VIS-ABCDEF0123456789',status:'pending',name:'QA Guest',version:1,booking:{date:'2026-10-01',start:'11:00',end:'12:00',plan:'patch',guests:2},booked_minutes:60,actual_minutes:null,actual_guests:null,public_note:'',can_cancel:true,payload:{contact:'qa-only',notes:''},patch_gift_guests:2};
const results=[];
async function run(browser,engine,lang,width,height){
 const ctx=await browser.newContext({viewport:{width,height},locale:lang==='zh'?'zh-CN':'en-CA'}),page=await ctx.newPage(),calls=[],errors=[];
 const base='http://127.0.0.1:'+server.address().port+'/h5/',suffix=engine+'-'+lang+'-'+width;
 let offer={campaign:'patch-qa',enabled:true,quota:10,remaining:1,allocated:9,version:1,started_at:'2026-09-28'},calendarDelay=0;
 page.setDefaultTimeout(6500);page.on('pageerror',e=>errors.push(e.message));
 await ctx.addInitScript(({lang,guest})=>{for(const [key,value] of [['pd_token','patch-qa-token'],['pd_user',JSON.stringify(guest)],['pd_studio_language',lang]])localStorage.setItem(key,JSON.stringify({type:'string',data:value}));},{lang,guest});
 await ctx.route('**/*',async route=>{
  const req=route.request(),u=new URL(req.url()),p=u.pathname;
  if(p.includes('/studio-api/')||p.includes('/api/v1/')){
   if(req.method()==='OPTIONS')return route.fulfill({status:204,headers:{'Access-Control-Allow-Origin':'*','Access-Control-Allow-Headers':'*','Access-Control-Allow-Methods':'*'}});
   calls.push({path:p,query:u.search,method:req.method(),body:req.postDataJSON()});let data={};
   if(p.endsWith('/content'))data={modules:{}};
   else if(p.endsWith('/patch-promotion')){if(req.method()==='PUT'){const body=req.postDataJSON();assert.equal(body.version,offer.version);offer={...offer,...body,remaining:Math.max(0,body.quota-offer.allocated),version:offer.version+1};}data=offer;}
   else if(p.endsWith('/auth/me'))data={user:guest};
   else if(p.endsWith('/auth/wallet'))data={account:{minutes:0,points:0},booking_profile:contact};
   else if(p.endsWith('/auth/reservation-context'))data={profile:contact,can_omit_details:false};
   else if(p.endsWith('/reservation-calendar')){if(calendarDelay)await new Promise(r=>setTimeout(r,calendarDelay));data=cal(u.searchParams.get('experience')||'beads');}
   else if(p.endsWith('/auth/notifications'))data={email:'',phone:'',email_enabled:false,sms_enabled:false,version:1};
   else if(p.endsWith('/reservations')&&req.method()==='POST'){assert.equal(req.postDataJSON().booking.plan,'patch');data=entry;}
   else if(p.endsWith('/manage/reservations')||p.endsWith('/auth/reservations'))data={items:[entry],total:1};
   else if(p.endsWith('/manage/reservation-timetable'))data={days:[{date:'2026-10-01',open:'10:00',close:'22:00',bookings:[{...entry,...entry.booking}]}]};
   else if(p.endsWith('/reservations/'+entry.id))data=entry;
   else if(p.endsWith('/cancellation'))data={limit:3,used:0,remaining:3,eligible:true,version:1};
   else if(p.endsWith('/manage/desk-summary'))data={today:'2026-10-01',pending:1,visits:0,unread:0,finance:{income_cents:0,expense_cents:0,needs_amount:0}};
   return route.fulfill({status:200,headers:{'Access-Control-Allow-Origin':'*'},contentType:'application/json',body:JSON.stringify(data)});
  }
  if(req.url().startsWith(base.slice(0,-4))||req.url().startsWith('data:')||req.url().startsWith('blob:'))return route.continue();
  if(p.includes('hero'))return route.fulfill({contentType:'image/webp',body:fs.readFileSync(path.join(root,'05_frontend/src/static/studio/hero.webp'))});
  return route.abort();
 });
 const shown=s=>page.locator(s).filter({visible:true});
 const shot=async label=>{await page.waitForTimeout(350);await page.screenshot({path:path.join(out,label+'-'+suffix+'.png')});};
 const overflow=()=>page.evaluate(()=>document.documentElement.scrollWidth>innerWidth+2);
 try{
  await page.goto(base+'#/pages/studio/home');await shown('.studio-patch-popup').waitFor();
  assert((await shown('.studio-patch-popup').innerText()).includes(lang==='zh'?'帆布带':'canvas strap'));
  await shot('home');
  await shown('.studio-patch-popup .studio-native-primary').click();
  await expect(shown('.studio-plan-patch')).toHaveClass(/studio-plan--selected/);
  assert((await shown('.studio-patch-card-offer').innerText()).includes('1/10'));
  assert.equal(await shown('.studio-visit-plans>.studio-plan').count(),4);
  assert(!await overflow());await shot('choices');
  const choices=await shown('.studio-visit-plans').boundingBox(),action=await shown('.studio-visit-actions').boundingBox();
  if(height>=700)assert(choices.y+choices.height<=action.y+2,'Four choices must fit above action dock');
  await shown('.studio-visit-actions .studio-native-primary').click();
  await expect.poll(()=>calls.some(c=>c.path.endsWith('/reservation-calendar')&&c.query.includes('experience=patch'))).toBe(true);
  const row=shown('.studio-calendar-row').filter({has:page.locator('.studio-calendar-time',{hasText:'11:00'})});
  await row.locator('uni-button').first().click();
  await expect(shown('.studio-visit-selection')).toContainText('11:00–12:00');
  assert(await shown('.studio-calendar-scroll').evaluate(e=>e.getBoundingClientRect().height)<=300);
  await shot('calendar');
  await shown('.studio-visit-actions .studio-native-primary').click();
  await expect(shown('.studio-visit-review')).toContainText(lang==='zh'?'布贴DIY':'Patch DIY');
  await shown('.studio-visit-actions .studio-native-primary').click();
  await shown('.studio-submit-panel').waitFor();await expect(shown('.studio-submit-panel')).toContainText(lang==='zh'?'布贴DIY':'Patch DIY');
  await shot('confirm');
  await shown('.studio-submit-panel .studio-native-primary').click();
  await expect.poll(()=>calls.filter(c=>c.path.endsWith('/reservations')&&c.method==='POST').length).toBe(1);
  await expect(shown('.studio-native-definition')).toContainText(lang==='zh'?'布贴DIY':'Patch DIY');
  const posted=calls.find(c=>c.path.endsWith('/reservations')&&c.method==='POST').body;
  assert.equal(posted.booking.end,'12:00');assert.equal(posted.booking.plan,'patch');
  await page.goto(base+'#/pages/studio/manage-reservations');await shown('.admin-booking-card').waitFor();
  await expect(shown('.admin-patch-gift')).toContainText(lang==='zh'?'帆布带':'canvas strap');
  await shown('.admin-filters').first().locator('uni-button').nth(2).click();
  await expect.poll(()=>calls.some(c=>c.path.endsWith('/manage/reservations')&&c.query.includes('experience=patch'))).toBe(true);
  await shot('admin');
  await page.goto(base+'#/pages/studio/manage-calendar');await shown('.native-calendar-booking').waitFor();
  await shown('.admin-filters').locator('uni-button').nth(2).click();
  await expect.poll(()=>calls.some(c=>c.path.endsWith('/manage/reservation-timetable')&&c.query.includes('experience=patch'))).toBe(true);
  await page.goto(base+'#/pages/studio/manage-patch-offer');
  await page.locator('.admin-input input').first().fill('12');await shown('.admin-native-actions .admin-primary').click();
  await expect.poll(()=>calls.filter(c=>c.path.endsWith('/manage/patch-promotion')&&c.method==='PUT').length).toBe(1);
  assert.equal(offer.quota,12);assert.equal(offer.version,2);await shot('quota');
  offer.enabled=false;await page.goto(base+'#/pages/studio/home');await shown('.studio-home').waitFor();await page.waitForTimeout(250);assert.equal(await shown('.studio-patch-popup').count(),0);
  assert(!errors.length,errors.join('\n'));
  results.push({engine,lang,width,height,passed:true,submission:posted.booking,versionedQuota:true,realWrites:false});
 }catch(e){await shot('failed');fs.writeFileSync(path.join(out,'failed-'+suffix+'.json'),JSON.stringify({error:e.message,calls,errors},null,2));throw e;}
 finally{await ctx.close();}
}
(async()=>{
 await new Promise(r=>server.listen(0,'127.0.0.1',r));
 const chrome=await chromium.launch({headless:true}),safari=await webkit.launch({headless:true});
 try{for(const [browser,engine,lang,width,height] of [[chrome,'chromium','zh',390,780],[chrome,'chromium','en',390,780],[safari,'webkit','zh',375,700],[chrome,'chromium','en',320,640]])await run(browser,engine,lang,width,height);fs.writeFileSync(path.join(out,'browser-checks.json'),JSON.stringify(results,null,2));console.log(JSON.stringify(results));}
 finally{await chrome.close();await safari.close();server.close();}
})().catch(e=>{console.error(e);process.exitCode=1;server.close();});
