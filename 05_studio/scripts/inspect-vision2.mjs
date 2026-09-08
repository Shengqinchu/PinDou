import {chromium} from '@playwright/test';
import fs from 'node:fs';
const out='../artifacts/studio-vision2';
const b=await chromium.launch({headless:true});
for(const w of [1440,390]) {
 const c=await b.newContext({viewport:{width:w,height:1000},reducedMotion:'reduce'}),p=await c.newPage();
 for(const route of ['', 'visit','details','manage']){
  await p.goto('http://127.0.0.1:5184/studio/'+route);await p.waitForTimeout(700);await p.evaluate(()=>document.fonts.ready);
  if(route==='visit')await p.locator('input[value="day"]').check();
  if(route==='manage') {await p.evaluate(()=>localStorage.setItem('pindou_token','local-qa'));}
  await p.screenshot({path:`${out}/${route||'home'}-${w}.png`,fullPage:route==='visit'});
  console.log(w,route,await p.evaluate(()=>({overflow:document.documentElement.scrollWidth>innerWidth,font:getComputedStyle(document.querySelector('h1')||document.body).fontFamily,text:document.body.innerText.slice(0,120)})));
 }
 await c.close();
}
const c=await b.newContext({viewport:{width:390,height:844},isMobile:true}),p=await c.newPage();
const requests=[];
p.on('request',r=>{if(r.resourceType()==='xhr'||r.resourceType()==='fetch')requests.push({url:r.url(),method:r.method(),body:r.postData()});});
await p.goto('https://www.xiaohongshu.com/collection/item/69dee77800ba000000000001?xhsshare=CopyLink&appuid=65f8375c000000000b00c921&apptime=1788838035&share_id=ff259b614e4248fb9fba8ba26115c27f',{waitUntil:'domcontentloaded'});
await p.waitForTimeout(1500);await p.screenshot({path:out+'/collection.png',fullPage:true});
console.log('COLLECTION',await p.locator('body').innerText());
await p.evaluate(()=>window.scrollTo(0,document.body.scrollHeight));await p.waitForTimeout(1200);
fs.writeFileSync(out+'/collection-requests.json',JSON.stringify(requests,null,2));
console.log('request URLs',requests.map(r=>r.url));
await b.close();
