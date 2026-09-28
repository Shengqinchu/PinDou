// Disposable loopback service only; no real reservations or outbound delivery.
import { chromium, webkit, expect } from '@playwright/test';
import assert from 'node:assert/strict';
import fs from 'node:fs/promises';
import patchCopy from '../src/content/patch-reservations.json' with {type:'json'};
import adminCopy from '../src/content/components-admin-ReservationsPanel.json' with {type:'json'};
const base='http://127.0.0.1:5287', apiBase='http://127.0.0.1:8127';
const out=new URL('../../artifacts/patch-booking/browser/',import.meta.url);
await fs.mkdir(out,{recursive:true});
const results=[];
const minute=t=>Number(t.slice(0,2))*60+Number(t.slice(3));
const clock=n=>String(Math.floor(n/60)).padStart(2,'0')+':'+String(n%60).padStart(2,'0');
for(const [engine,browserType,width,height,lang] of [
 ['chromium',chromium,1440,1000,'zh'],['chromium',chromium,390,844,'en'],
 ['webkit',webkit,390,844,'zh'],['webkit',webkit,1440,1000,'en'],
]){
 const browser=await browserType.launch({headless:true});
 const ctx=await browser.newContext({viewport:{width,height},hasTouch:width<700});
 const key=engine+'-'+lang,owner='qa-email-patch-'+key+'-'+Date.now();
 const word=k=>patchCopy[k][lang==='zh'?0:1],admin=k=>adminCopy[k][lang==='zh'?0:1];
 const errors=[],sent=[];
 const call=async(path,method='GET',data,staff=false)=>{
  const r=await ctx.request.fetch(apiBase+'/studio-api'+path,{method,data,headers:{Authorization:'Bearer '+(staff?'local-admin-visits':owner)}});
  assert(r.ok(),path+': '+r.status()+' '+await r.text());return r.json();
 };
 await ctx.addInitScript(({owner,lang})=>{
  localStorage.setItem('pd_web_token',owner);localStorage.setItem('pd_token',owner);
  localStorage.setItem('puppy-studio-language',lang);
  sessionStorage.setItem('puppy-studio-admin','local-admin-visits');
 },{owner,lang});
 await ctx.route('**/studio-api/**',async route=>{
  const req=route.request(),url=new URL(req.url()),headers={};
  for(const k of ['authorization','content-type','idempotency-key'])if(req.headers()[k])headers[k]=req.headers()[k];
  if(req.method()==='POST'&&url.pathname==='/studio-api/reservations')sent.push(req.postDataJSON());
  const r=await ctx.request.fetch(apiBase+url.pathname+url.search,{method:req.method(),headers,data:req.postDataBuffer()||undefined});
  await route.fulfill({response:r});
 });
 await ctx.route('**/api/v1/**',route=>route.fulfill({json:{}}));
 const page=await ctx.newPage();page.setDefaultTimeout(15000);page.on('pageerror',e=>errors.push(e.message));
 const shot=async(name)=>{await page.evaluate(()=>document.fonts.ready);await page.waitForTimeout(450);return page.screenshot({path:new URL(key+'-'+name+'.png',out).pathname.replace(/^\/([A-Z]:)/,'$1'),fullPage:true,animations:'disabled'});};
 try{
  await page.goto(base+'/visit?step=1');
  await expect(page.locator('.visit-plans>label')).toHaveCount(3);
  await expect(page.locator('.visit-plans>.visit-combined-offers')).toHaveCount(1);
  await expect(page.locator('.visit-combined-offers>article')).toHaveCount(2);
  const card=page.locator('.visit-plans>label').filter({has:page.locator('input[value=patch]')});
  await expect(card).toContainText(word('description'));await expect(card.locator('.money-text')).toHaveCount(0);
  await expect(page.locator('.visit-actions>.button')).toBeDisabled();
  const geometry=await page.locator('.visit-plans').evaluate(e=>({columns:getComputedStyle(e).gridTemplateColumns,children:[...e.children].filter(x=>x.tagName!=='LEGEND').map(x=>({left:x.getBoundingClientRect().left,width:x.getBoundingClientRect().width,border:getComputedStyle(x).borderRadius}))}));
  assert.equal(geometry.children.length,4);
  if(width>700)assert(geometry.children[0].left===geometry.children[2].left);
  else assert(geometry.children.every(r=>r.left===geometry.children[0].left));
  await shot('experiences');
  await card.locator('input').focus();assert(await card.locator('input').evaluate(e=>e.matches(':focus-visible')));
  await page.keyboard.press('Space');await expect(card).toHaveClass(/selected/);
  // The new radio card must use the same state geometry and easing as an old card.
  const motion=await card.evaluate(e=>({transition:getComputedStyle(e).transitionDuration,ease:getComputedStyle(e).transitionTimingFunction}));
  assert(motion.transition.includes('0.3s'));assert(motion.ease.includes('0.4, 0, 0.2, 1'));
  await page.locator('.visit-actions>.button').click();
  await expect(page.locator('.reservation-grid')).toBeVisible();
  await expect(page.locator('.reservation-minimum-note')).toHaveText(word('booking_note'));
  const free=page.locator('.reservation-grid button:not(:disabled)').first();
  const day=await free.getAttribute('data-date'),start=await free.getAttribute('data-time');
  await page.locator('.reservation-grid button[data-date="'+day+'"][data-time="'+start+'"]').click();
  await expect(page.locator('.visit-time-selection')).toContainText(start+'–'+clock(minute(start)+60));
  await expect(page.locator('.reservation-grid button.chosen')).toHaveCount(2);
  // A second click relocates the one-hour slot instead of extending it.
  const next=page.locator('.reservation-grid button:not(:disabled)[data-date="'+day+'"][data-time="'+clock(minute(start)+60)+'"]');
  let chosenStart=start;
  if(await next.count()){
   await next.click();chosenStart=clock(minute(start)+60);
   await expect(page.locator('.visit-time-selection')).toContainText(chosenStart+'–'+clock(minute(chosenStart)+60));
  }
  await expect(page.locator('.reservation-grid button.chosen')).toHaveCount(2);
  await page.reload();await expect(page.locator('.visit-time-selection')).toContainText(chosenStart+'–'+clock(minute(chosenStart)+60));
  await shot('time');
  await page.locator('.visit-actions>.button').click();
  await expect(page.locator('.visit-review')).toContainText(word('patch'));
  if(!await page.locator('.booking-contact-fields input[autocomplete=name]').count())await page.locator('.visit-saved-contact button').click();
  await page.locator('.booking-contact-fields input[autocomplete=name]').fill('Patch QA '+key);
  await page.locator('.booking-contact-fields .visit-contact-value input').fill('patch-qa-local');
  await page.locator('.visit-actions>.button').click();
  await expect(page).toHaveURL(/\/reservation\/VIS-/);
  const reference=page.url().split('/').at(-1);
  assert.equal(sent.length,1);assert.equal(sent[0].booking.plan,'patch');
  assert.equal(sent[0].booking.date,day);assert.equal(sent[0].booking.start,chosenStart);
  assert.equal(minute(sent[0].booking.end)-minute(sent[0].booking.start),60);
  await expect(page.locator('main')).toContainText(word('patch'));
  const reserved=await call('/reservation-calendar?experience=patch');
  assert(!reserved.days.find(d=>d.date===day).slots.find(s=>s.start===chosenStart).available);
  const bead=await call('/reservation-calendar?experience=beads');
  assert(bead.days.find(d=>d.date===day).slots.find(s=>s.start===chosenStart).available);
  await shot('receipt');
  await page.goto(base+'/manage?view=reservations');
  const desk=page.locator('.reservation-desk:visible');
  await expect(desk.locator('.reservation-experience-filter')).toBeVisible();
  await desk.locator('.reservation-experience-filter button').filter({hasText:word('patch')}).click();
  const row=desk.locator('.reservation-desk-row').filter({hasText:reference});
  await expect(row).toBeVisible();await expect(row).toContainText(word('patch'));
  await expect(desk.locator('.timetable-scroll')).toHaveAttribute('aria-busy','false');
  // Narrow admin timetables show one day; advance to this booking's date.
  for(let n=0;n<14&&!await desk.locator('.timetable-slot[data-date="'+day+'"]').count();n++){
   await desk.locator('.timetable-navigation button').last().click();
   await page.waitForTimeout(80);
   await expect(desk.locator('.timetable-scroll')).toHaveAttribute('aria-busy','false');
  }
  await expect(desk.locator('.timetable-booking.is-patch').filter({hasText:'Patch QA '+key})).toBeVisible();
  await shot('admin');
  await row.click();
  await expect(page.locator('dialog[open]')).toContainText(word('patch'));
  await page.getByRole('combobox',{name:admin('update_reservation_status_0ddee8'),exact:true}).selectOption('confirmed');
  await page.getByRole('button',{name:admin('save_arrangement_87aa75'),exact:true}).click();
  await expect(page.locator('dialog[open]')).toHaveCount(0);
  assert.equal((await call('/reservations/'+reference)).status,'confirmed');
  // Refresh keeps the patch filter and a new cancellation releases the slot.
  const current=await call('/reservations/'+reference);
  await call('/manage/reservations/'+reference,'PATCH',{status:'cancelled',version:current.version},true);
  const after=await call('/reservation-calendar?experience=patch');
  assert(after.days.find(d=>d.date===day).slots.find(s=>s.start===chosenStart).available);
  const overflow=await page.evaluate(()=>document.documentElement.scrollWidth>innerWidth+1);assert(!overflow);
  assert.deepEqual(errors,[]);
  results.push({engine,width,height,lang,reference,day,chosenStart,geometry,motion,passed:true});
 }catch(e){await shot('FAIL');throw e;}
 finally{await ctx.close();await browser.close();await fs.writeFile(new URL('results.json',out),JSON.stringify(results,null,2));}
}
console.log(JSON.stringify({passed:results.length,results}));
