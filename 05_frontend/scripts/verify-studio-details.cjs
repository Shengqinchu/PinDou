// Uses published public text/photos with isolated customer API fixtures. No business writes.
const {createRequire}=require('node:module'),fs=require('node:fs'),path=require('node:path'),http=require('node:http'),assert=require('node:assert/strict');
const {chromium,webkit,expect}=createRequire(path.resolve(__dirname,'../../05_studio/package.json'))('@playwright/test');
const root=path.resolve(__dirname,'../..'),build=path.join(root,'05_frontend/dist/build/h5'),out=path.join(root,'artifacts/miniapp-details-20260915');fs.mkdirSync(out,{recursive:true});
const json=file=>JSON.parse(fs.readFileSync(path.join(root,file),'utf8'));
const published=json('artifacts/miniapp-details-20260915/published-details.json').modules;
const defaults=json('05_studio/src/content/pages-Details.json'),processDefaults=json('05_studio/src/content/components-BeadingProcess.json'),media=json('05_studio/src/media-assets.json');
const detailCopy={...defaults,...published['pages-Details']},processCopy={...processDefaults,...published['components-BeadingProcess']};
const photoKeys=['arrival-entrance','parking-entrance','parking-location','process-pattern','process-tools','process-making','process-ironing','process-findings','process-finishes','process-packaging'];
const webSource=fs.readFileSync(path.join(root,'05_studio/src/pages/Details.vue'),'utf8'),webKeys=[...new Set([...webSource.matchAll(/copyText\.([a-z0-9_]+)/g)].map(m=>m[1]))];
const photos=new Map(),photoEvidence=[];const normal=s=>s.replace(/\s+/g,' ').trim();
const server=http.createServer((req,res)=>{const pathname=decodeURIComponent(new URL(req.url,'http://localhost').pathname),file=path.resolve(build,pathname.replace(/^\/h5\/?/,'')||'index.html');if(!file.startsWith(build+path.sep)){res.writeHead(403).end();return;}try{res.setHeader('Content-Type',({'.js':'application/javascript','.css':'text/css','.html':'text/html','.svg':'image/svg+xml','.png':'image/png','.webp':'image/webp','.jpg':'image/jpeg'}[path.extname(file)]||'application/octet-stream'));res.end(fs.readFileSync(file));}catch{res.writeHead(404).end();}});
const checks=[];
async function loadPhotos(){
 for(let i=0;i<photoKeys.length;i+=3)await Promise.all(photoKeys.slice(i,i+3).map(async key=>{const item=published.media?.[key]||media[key],url='https://pindoupuppy.com'+item.src;const response=await fetch(url,{signal:AbortSignal.timeout(25000)});assert.equal(response.status,200,url);const body=Buffer.from(await response.arrayBuffer());photos.set(new URL(url).pathname,{body,contentType:response.headers.get('content-type')||'image/jpeg'});photoEvidence.push({key,url,status:response.status,bytes:body.length,width:item.width,height:item.height});}));
 fs.writeFileSync(path.join(out,'photo-evidence.json'),JSON.stringify(photoEvidence,null,2));
}
async function run(browser,engine,lang,width,height){
 const context=await browser.newContext({viewport:{width,height},locale:lang==='zh'?'zh-CN':'en-CA'}),page=await context.newPage(),errors=[],calls=[];page.setDefaultTimeout(7000);page.on('pageerror',e=>errors.push(e.message));
 const origin='http://127.0.0.1:'+server.address().port,base=origin+'/h5/';
 const person={id:'details-fixture',nickname:'Fixture Customer',email:'customer@example.invalid',is_admin:false,customer_code:'PD-HIDDEN'};let retryImage=false;
 await context.addInitScript(({lang,person})=>{const set=(key,data,type)=>localStorage.setItem(key,JSON.stringify({type,data}));set('pd_token','details-fixture','string');set('pd_user',JSON.stringify(person),'string');set('pd_studio_language',lang,'string');},{lang,person});
 await context.route('**/*',async route=>{const request=route.request(),url=request.url(),p=new URL(url).pathname;
  if(photos.has(p)){if(p===media['process-tools'].src&&!retryImage){retryImage=true;return route.abort();}return route.fulfill({status:200,...photos.get(p)});}
  if(url.includes('/studio-api/')||url.includes('/api/v1/')){
   const headers={'Access-Control-Allow-Origin':'*','Access-Control-Allow-Headers':'*','Access-Control-Allow-Methods':'GET,POST,PUT,OPTIONS'};
   if(request.method()==='OPTIONS')return route.fulfill({status:204,headers});calls.push({path:p,method:request.method()});let data={};
   if(p.endsWith('/content'))data={modules:published};
   else if(p.endsWith('/user/profile'))data=person;
   else if(p.endsWith('/auth/me'))data={user:person};
   else if(p.endsWith('/auth/wallet'))data={account:{minutes:0,points:166},booking_profile:{complete:false,name:'',contact_method:'wechat',contact:''}};
   else if(p.endsWith('/auth/owner-notifications'))data={bound:false};
   else if(p.endsWith('/auth/reservations'))data={items:[],total:0};
   return route.fulfill({status:200,headers,contentType:'application/json',body:JSON.stringify(data)});
  }
  if(url.startsWith(origin)||url.startsWith('data:')||url.startsWith('blob:'))return route.continue();return route.abort();
 });
 try{
  await page.goto(base+'#/pages/studio/details');await page.locator('.studio-details').waitFor();await page.waitForTimeout(400);
  const body=normal(await page.locator('.studio-native').innerText());
  for(const key of webKeys.filter(k=>k!=='studio_information_sections_45baee'))assert(body.includes(normal(detailCopy[key][lang==='zh'?0:1])),`Missing website text: ${key}`);
  for(const [key,value] of Object.entries(processCopy).filter(([k])=>!['toolsUrl','photoLabel'].includes(k)))assert(body.includes(normal(value[lang==='zh'?0:1])),`Missing process text: ${key}`);
  await expect(page.locator('.studio-detail-photo')).toHaveCount(10);await expect(page.locator('.studio-detail-step')).toHaveCount(5);await expect(page.locator('#studio-detail-notes .studio-detail-article')).toHaveCount(3);
  await page.screenshot({path:path.join(out,`details-top-${engine}-${lang}-${width}.png`)});
  const imageChecks=[];
  for(let i=0;i<10;i++){
   const photo=page.locator('.studio-detail-photo-button').nth(i);await photo.scrollIntoViewIfNeeded();
   if(photoKeys[i]==='process-tools'){await expect(photo.locator('.studio-detail-photo-state')).toContainText(lang==='zh'?'重新尝试':'Try again');await photo.click();}
   await expect(photo.locator('.studio-native-progress')).toHaveCount(0,{timeout:10000});
   const box=await photo.boundingBox(),item=media[photoKeys[i]];assert(box&&box.width>100&&box.height>100);assert(Math.abs(box.height/box.width-item.height/item.width)<.03,'Original photo proportions');
   assert.equal(await photo.locator('uni-image').count(),1);assert.equal(await photo.locator('.studio-detail-photo-state').count(),0);
   imageChecks.push({key:photoKeys[i],width:box.width,height:box.height});
  }
  const cta=page.locator('.studio-native-dock .studio-native-primary'),ctaBox=await cta.boundingBox();assert(ctaBox&&ctaBox.y>=0&&ctaBox.y+ctaBox.height<=height+1,'Booking button remains in view');
  await page.screenshot({path:path.join(out,`details-end-${engine}-${lang}-${width}.png`)});
  await page.locator('.studio-detail-photo-button').last().click();await expect(page.locator('#u-a-p>div')).toBeVisible();await expect(page.locator('#u-a-p uni-swiper-item')).toHaveCount(10);await page.keyboard.press('Escape');await expect(page.locator('#u-a-p')).toBeEmpty();
  // The navigator must move this scroll view, including repeated same-section clicks.
  await page.locator('.studio-detail-nav').evaluate(el=>el.scrollIntoView());await page.locator('.studio-detail-nav uni-button').nth(4).click();
  await expect(page.locator('#studio-detail-process')).toBeInViewport();
  const logo=await page.locator('.studio-native-top').boundingBox();assert(logo&&logo.y>=0,'Detail navigation keeps the shared header in view');
  await page.screenshot({path:path.join(out,`details-process-${engine}-${lang}-${width}.png`)});
  await page.goto(base+'#/pages/auth/studio-account');await page.locator('.studio-native-name').filter({hasText:'Fixture Customer'}).waitFor();await page.waitForTimeout(220);
  const account=await page.locator('.studio-account').innerText();assert(!account.includes('PD-HIDDEN'));assert(!/完善顾客资料|Complete your customer profile|我的消息|My messages/.test(account));
  await expect(page.locator('.studio-profile-edit')).toBeVisible();await expect(page.locator('.studio-native-balance-value').filter({hasText:'166'})).toBeVisible();
  await page.screenshot({path:path.join(out,`account-clean-${engine}-${lang}-${width}.png`)});
  await page.goto(base+'#/pages/studio/messages');await page.locator('.studio-account').waitFor();assert.equal(calls.filter(c=>c.path==='/studio-api/auth/messages').length,0,'Retired customer chat must not fetch or poll');
  assert.deepEqual(errors,[]);assert(calls.every(c=>c.method==='GET'));assert(await page.evaluate(()=>document.body.scrollWidth<=innerWidth+1));
  checks.push({engine,lang,width,height,website_texts:webKeys.length,process_texts:Object.keys(processCopy).length-2,photos:imageChecks,passed:true});
 }catch(e){await page.screenshot({path:path.join(out,'failure.png')});console.error({engine,lang,width,errors,calls,error:e.message});throw e;}finally{await context.close();}
}
(async()=>{await loadPhotos();await new Promise(resolve=>server.listen(0,'127.0.0.1',resolve));for(const [name,type] of [['chromium',chromium],['webkit',webkit]]){const browser=await type.launch({headless:true});try{for(const lang of ['zh','en'])await run(browser,name,lang,390,844);await run(browser,name,'zh',844,390);}finally{await browser.close();}}fs.writeFileSync(path.join(out,'ui-results.json'),JSON.stringify(checks,null,2));console.log(checks.map(({photos,...check})=>({...check,photos:photos.length})));})().catch(e=>{console.error(e.stack);process.exitCode=1;}).finally(()=>server.close());
