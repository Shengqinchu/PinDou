// Loopback-only VISION2 verification. Settings changes use the isolated QA database.
import {chromium,webkit,firefox,expect} from '@playwright/test';
import AxeBuilder from '@axe-core/playwright';
import assert from 'node:assert/strict';
import fs from 'node:fs';
const base='http://127.0.0.1:5184/studio/',out='../artifacts/studio-vision2/verification';
fs.mkdirSync(out,{recursive:true});
const results=[],errors=[];
const query=async p=>p.evaluate(()=>{
 const grid=document.querySelector('.reservation-grid-scroll');
 const h=document.querySelector('h1');
 return {overflow:document.documentElement.scrollWidth>innerWidth+1,gridOverflow:grid?grid.scrollWidth>grid.clientWidth+1:false,columns:document.querySelectorAll('.reservation-grid thead th').length-1,font:h?getComputedStyle(h).fontFamily:null,color:h?getComputedStyle(h).color:null};
});
for(const [engine,launcher,sizes] of [['chromium',chromium,[[320,740],[390,844],[768,1024],[1024,768],[1440,960],[2560,1440],[844,390]]],['webkit',webkit,[[390,844],[1440,960]]],['firefox',firefox,[[390,844],[1440,960]]]]){
 const b=await launcher.launch({headless:true});
 for(const [width,height] of sizes)for(const lang of ['zh','en']) {
  const c=await b.newContext({viewport:{width,height},reducedMotion:'reduce'});
  await c.addInitScript(lang=>{localStorage.setItem('puppy-studio-language',lang);sessionStorage.setItem('puppy-studio-admin','local-qa');},lang);
  const p=await c.newPage();p.on('pageerror',e=>errors.push({engine,width,lang,error:e.message}));
  const routes=process.env.STUDIO_VERIFY_SCOPE==='desk'?['manage']:engine==='chromium'?['','visit','details','journal','manage']:['','visit','manage'];
  for(const route of routes){
   try {
    await p.goto(base+route);await p.evaluate(()=>document.fonts.ready);
    if(route==='visit'){
     await p.locator('.reservation-grid').waitFor();
     await p.locator('input[value="hourly"]').check();
     await expect(p.locator('.reservation-plan-price')).toContainText('8.88');
     await p.locator('input[value="day"]').check();
     await expect(p.locator('.reservation-day-prices')).toContainText('129.9');
     await expect(p.locator('.reservation-plan-price')).toHaveCount(0);
    }
    if(route==='manage')await p.locator('.reservation-settings-entry:visible').waitFor();
    await p.waitForTimeout(120);
    const data=await query(p);assert.equal(data.overflow,false,'document overflow');assert.equal(data.gridOverflow,false,'calendar scrolls sideways');
    if(lang==='zh'&&data.font)assert(!data.font.includes('Serif'),'Chinese headline uses serif');
    if(engine==='chromium'&&[390,1440].includes(width)&&lang==='zh'){
      const violations=(await new AxeBuilder({page:p}).withTags(['wcag2a','wcag2aa','wcag21aa']).analyze()).violations;
      if(violations.length)errors.push({route,engine,width,lang,axe:violations.map(v=>({id:v.id,targets:v.nodes.map(n=>n.target)}))});
      await p.screenshot({path:`${out}/${route||'home'}-${width}.png`,fullPage:route==='visit'||route==='journal'});
    }
    results.push({engine,width,height,lang,route:route||'home',...data});
   }catch(e){errors.push({engine,width,lang,route,error:e.message});}
  }
  await c.close();
 }
 await b.close();
 console.log(engine,results.filter(r=>r.engine===engine).length,'layout checks');
}
// Editable hours/capacity, protected save and preserved input on failed saves.
const b=await chromium.launch({headless:true}),c=await b.newContext({viewport:{width:390,height:844},reducedMotion:'reduce'});
await c.addInitScript(()=>sessionStorage.setItem('puppy-studio-admin','local-qa'));
const p=await c.newPage();
try{
 await p.goto(base+'manage');await p.getByRole('button',{name:'编辑预约规则',exact:true}).click();
 await p.locator('input[name=max_guests_per_group]').fill('3');
 await p.locator('input[name=max_concurrent_groups]').fill('2');
 await p.locator('input[name=max_concurrent_guests]').fill('5');
 await p.getByLabel('周三结束时间',{exact:true}).selectOption('20:00');
 await p.screenshot({path:out+'/settings-mobile.png',fullPage:true});
 await p.getByRole('button',{name:'保存预约规则',exact:true}).click();
 await expect(p.locator('.reservation-settings-saved')).toBeVisible();
 const policy=await (await p.request.get('http://127.0.0.1:8011/studio-api/manage/reservation-policy')).json();
 assert.equal(policy.max_guests_per_group,3);assert.equal(policy.max_concurrent_groups,2);assert.equal(policy.weekly_hours[2].close,'20:00');
 await p.goto(base+'visit');await p.locator('.reservation-grid').waitFor();
 assert.equal(await p.getByLabel('同行人数（包括你自己）',{exact:true}).getAttribute('max'),'3');
 const calendar=await (await p.request.get('http://127.0.0.1:8011/studio-api/reservation-calendar')).json();
 assert.equal(calendar.days.find(d=>new Date(d.date+'T12:00:00Z').getUTCDay()===3).close,'20:00');
 await p.goto(base+'manage');await p.getByRole('button',{name:'编辑预约规则',exact:true}).click();
 await p.getByLabel('周三结束时间',{exact:true}).selectOption('10:30');
 await p.getByRole('button',{name:'保存预约规则',exact:true}).click();
 await expect(p.locator('.reservation-settings-form .desk-error')).toBeVisible();
 assert.equal(await p.getByLabel('周三结束时间',{exact:true}).inputValue(),'10:30');
 await p.keyboard.press('Escape');await expect(p.locator('.studio-drawer[open]')).toHaveCount(0);
 results.push({flow:'rules-saved-and-customer-synced',failedSavePreservesDraft:true});
 // Restore this test's changes in the local QA fixture.
 const current=await (await p.request.get('http://127.0.0.1:8011/studio-api/manage/reservation-policy')).json();
 current.max_guests_per_group=4;current.max_concurrent_groups=null;current.max_concurrent_guests=null;current.weekly_hours[2].close='22:00';
 const reset=await p.request.put('http://127.0.0.1:8011/studio-api/manage/reservation-policy',{data:current});assert.equal(reset.status(),200);
}catch(e){errors.push({flow:'settings',error:e.message});}
await b.close();
fs.writeFileSync(out+(process.env.STUDIO_VERIFY_SCOPE==='desk'?'/desk-results.json':'/results.json'),JSON.stringify({results,errors},null,2));
console.log(JSON.stringify({checks:results.length,errors}));
assert.deepEqual(errors,[]);
