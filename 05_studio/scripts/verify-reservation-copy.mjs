// Isolated loopback QA only: start a fresh 06_studio/qa_server.py and a built preview on port 4184.
import {chromium,expect} from '@playwright/test';
import fs from 'node:fs/promises';
import assert from 'node:assert/strict';
const base='http://127.0.0.1:4184';
await fs.mkdir(new URL('../../artifacts/studio-regression-20260909/',import.meta.url),{recursive:true});
const policyPath=base+'/studio-api/manage/reservation-policy';
const policy=await (await fetch(policyPath)).json();
const calendar=await (await fetch(base+'/studio-api/reservation-calendar')).json();
const thursday=calendar.days.find(d=>new Date(d.date+'T12:00Z').getUTCDay()===4&&d.date>calendar.today);
assert(thursday);
const booking={date:thursday.date,start:'10:00',end:'12:00',plan:'hourly',guests:1};
const browser=await chromium.launch({headless:true});
const results=[];
try {
 const context=await browser.newContext({viewport:{width:1500,height:1000},reducedMotion:'reduce'});
 await context.addInitScript(booking=>{
  sessionStorage.setItem('puppy-studio-admin','local-qa');
  if(parent===window&&!sessionStorage.getItem('puppy-reservation-draft-v1'))sessionStorage.setItem('puppy-reservation-draft-v1',JSON.stringify({booking,name:'',contact_method:'wechat',contact:'',notes:'',consent:false}));
 },booking);
 const page=await context.newPage();page.setDefaultTimeout(10000);
 await page.goto(base+'/visit',{waitUntil:'networkidle'});
 const day=page.locator('.reservation-plans label').filter({has:page.locator('input[value="day"]')});
 await expect(day).toContainText('22:00');assert(!(await day.innerText()).includes('18:00'));
 await day.click();await expect(day).toContainText('22:00');
 await page.locator(`button[data-date="${thursday.date}"][data-time="10:00"]`).click();
 await expect(day.locator('.selected-day-context')).toContainText(thursday.date+' 营业至 18:00');
 let saved=await page.evaluate(()=>JSON.parse(sessionStorage.getItem('puppy-reservation-draft-v1')));
 assert.equal(saved.booking.end,'18:00');
 results.push({case:'retained hourly Thursday',unselectedDay:'22:00',selectedDate:thursday.date,selectedDayEnds:saved.booking.end});
 const beforePreview=await page.evaluate(()=>sessionStorage.getItem('puppy-reservation-draft-v1'));
 await page.goto(base+'/manage?view=content',{waitUntil:'networkidle'});
 await page.locator('.editor-commandbar select').selectOption('pages-Visit');
 await expect(page.locator('.editor-preview-state')).toHaveAttribute('data-state','synced');
 const preview=page.frameLocator('.editor-preview-canvas iframe');
 await expect(preview.locator('.reservation-plans label').last()).toContainText('22:00');
 assert.equal(await page.evaluate(()=>sessionStorage.getItem('puppy-reservation-draft-v1')),beforePreview);
 const key='make_from_your_chosen_arrival_until_37196a';
 const field=page.locator(`[data-content-key="${key}"] textarea`).last();
 await field.fill('Owner preview closes at {v0}.');
 await page.locator('.desk-language').click();
 await expect(preview.getByText('Owner preview closes at 22:00.',{exact:true})).toBeVisible();
 // A child preview cannot turn buttons/links into real submissions.
 await preview.locator('.reservation-plans label').last().click();
 assert.equal(await page.evaluate(()=>sessionStorage.getItem('puppy-reservation-draft-v1')),beforePreview);
 results.push({case:'isolated bilingual preview',customerDraftUnchanged:true,initialDay:'22:00',englishEdit:true});
 const updated={...policy,weekly_hours:policy.weekly_hours.map(h=>({...h,close:h.close==='22:00'?'21:00':h.close}))};
 const update=await fetch(policyPath,{method:'PUT',headers:{'Content-Type':'application/json'},body:JSON.stringify(updated)});
 assert.equal(update.status,200,await update.text());
 const fresh=await context.newPage();await fresh.goto(base+'/visit',{waitUntil:'networkidle'});
 // Existing selected Thursday still follows Thursday. Clear the selection first.
 await fresh.locator('input[value="hourly"]').check({force:true});
 await expect(fresh.locator('.reservation-plans label').last()).toContainText('21:00');
 await fresh.locator('.reservation-plans label').last().click();
 await fresh.locator(`button[data-date="${thursday.date}"][data-time="10:00"]`).click();
 await expect(fresh.locator('.selected-day-context')).toContainText('18:00');
 results.push({case:'latest policy wins',ordinaryDayAfterEdit:'21:00',thursdayStill:'18:00'});
 await fs.writeFile(new URL('../../artifacts/studio-regression-20260909/hours-verification.json',import.meta.url),JSON.stringify(results,null,2));
 console.log(JSON.stringify(results,null,2));
}finally{
 const latest=await (await fetch(policyPath)).json();
 const restore=await fetch(policyPath,{method:'PUT',headers:{'Content-Type':'application/json'},body:JSON.stringify({...policy,version:latest.version})});
 assert.equal(restore.status,200);
 await browser.close();
}
