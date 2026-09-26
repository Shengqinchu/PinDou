// Only loopback writes: tests use the isolated qa_server database and fake auth.
import {chromium,webkit,expect} from '@playwright/test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
const base='http://127.0.0.1:5184',api='http://127.0.0.1:8011/studio-api';
const out='../artifacts/vision3/verification';fs.mkdirSync(out,{recursive:true});
const results=[],errors=[];
async function layout(page,tag){
 const data=await page.evaluate(()=>({overflow:document.documentElement.scrollWidth>innerWidth+1,gridOverflow:[...document.querySelectorAll('.reservation-grid-scroll')].some(x=>x.scrollWidth>x.clientWidth+1),broken:[...document.images].filter(i=>i.complete&&!i.naturalWidth).map(i=>i.src)}));
 assert.equal(data.overflow,false,tag+' page overflow');assert.equal(data.gridOverflow,false,tag+' calendar overflow');assert.deepEqual(data.broken,[],tag+' broken images');results.push({tag,...data});
}
for(const [engine,launch,sizes] of (process.env.STUDIO_FLOW_ONLY?[]:[['chromium',chromium,[[320,740],[390,844],[768,1024],[1440,1000],[2560,1440],[844,390]]],['webkit',webkit,[[390,844],[1440,960]]]])){
 const browser=await launch.launch({headless:true,ignoreDefaultArgs:engine==='chromium'?['--hide-scrollbars']:undefined});
 try{
  for(const [width,height] of sizes){
   const context=await browser.newContext({viewport:{width,height},reducedMotion:'reduce'});
   await context.addInitScript(()=>sessionStorage.setItem('puppy-studio-admin','local-qa'));
   const page=await context.newPage();page.on('pageerror',e=>errors.push({engine,width,error:e.message}));
   for(const lang of ['zh','en']){
    await page.addInitScript(lang=>localStorage.setItem('puppy-studio-language',lang),lang);
    for(const route of ['', 'visit','details','journal', 'manage?view=content', 'manage?view=journal-editor','manage?view=reservation-calendar']){
     await page.goto(base+'/'+route);await page.waitForTimeout(160);await page.evaluate(()=>document.fonts.ready);
     if(route==='visit')await page.locator('.reservation-grid').waitFor();
     if(route==='journal')await page.locator('.journal-story').first().waitFor();
     if(route==='manage?view=content')await page.locator('.editor-field-group').first().waitFor();
     await layout(page,`${engine}-${width}-${lang}-${route}`);
     if(engine==='chromium'&&[390,1440].includes(width)&&lang==='zh'&&['','visit','manage?view=content','manage?view=reservation-calendar'].includes(route))await page.screenshot({path:`${out}/${(route||'home').replace(/[?=]/g,'-')}-${width}.png`});
    }
   }
   await context.close();
  }
 }finally{await browser.close();}
 console.log(engine,'layout complete');
}
const browser=await chromium.launch({headless:true,ignoreDefaultArgs:['--hide-scrollbars']});
try{
 const context=await browser.newContext({viewport:{width:1440,height:1000},reducedMotion:null});
 await context.addInitScript(()=>{localStorage.setItem('puppy-studio-motion','full');sessionStorage.setItem('puppy-studio-admin','local-qa');});
 const page=await context.newPage();page.on('pageerror',e=>errors.push({flow:true,error:e.message}));
 // Continuous interactions, classic scrollbar menu, all 12 slides without eager loading all images.
 await page.goto(base);await page.evaluate(()=>document.fonts.ready);await page.waitForTimeout(1500);
 const position=()=>page.locator('.vision-hero-photo').evaluate(e=>({x:e.getBoundingClientRect().x,width:e.getBoundingClientRect().width}));
 const before=await position();await page.getByRole('button',{name:'网站菜单',exact:true}).click();await page.waitForTimeout(550);assert.deepEqual(await position(),before);await page.getByRole('button',{name:'关闭菜单',exact:true}).click();await page.waitForTimeout(650);assert.deepEqual(await position(),before);
 assert.equal(await page.locator('.vision-carousel-window figure').count(),12);assert((await page.locator('.vision-carousel-window img').count())<=3);
 await page.locator('.vision-carousel').scrollIntoViewIfNeeded();for(let i=0;i<11;i++){await page.locator('.vision-carousel-controls button').last().click();await page.waitForTimeout(350);}
 await expect(page.locator('.vision-carousel-bottom')).toContainText('12 / 12');
 // Every selected row is 30 minutes; both data and visual end label are 2h.
 await page.goto(base+'/visit');await page.locator('.reservation-grid').waitFor();await page.locator('input[value="hourly"]').check();
 const calendar=await (await page.request.get(api+'/reservation-calendar')).json();const futureDate=calendar.days[1].date;const target=page.locator(`.reservation-grid button[data-date="${futureDate}"]:not([disabled])`).first();await target.click();
 await expect(page.locator('.reservation-grid button.chosen')).toHaveCount(4);
 assert.match(await page.locator('.reservation-grid button.chosen').last().innerText(),/\d{2}:\d{2} 结束/);
 // Actual inline preview, draft/public separation, publishing and conflict recovery.
 await page.goto(base+'/manage?view=content');await page.locator('.editor-field-group').first().waitFor();
 const text=page.locator('.editor-field-group textarea').first();const original=await text.inputValue();await text.fill('V3 本地预览测试');
 await expect(page.frameLocator('.editor-preview-canvas iframe').locator('.vision-location')).toContainText('V3 本地预览测试');
 let publicData=await (await page.request.get(api+'/content')).json();assert(!JSON.stringify(publicData).includes('V3 本地预览测试'));
 await page.getByRole('button',{name:'保存草稿',exact:true}).click();await expect(page.locator('.editor-state')).toContainText('草稿已保存');
 publicData=await (await page.request.get(api+'/content')).json();assert(!JSON.stringify(publicData).includes('V3 本地预览测试'));
 await page.getByRole('button',{name:'发布此页',exact:true}).click();await expect(page.locator('.editor-state')).toContainText('已发布');
 publicData=await (await page.request.get(api+'/content')).json();assert(JSON.stringify(publicData).includes('V3 本地预览测试'));
 await text.fill(original);await page.getByRole('button',{name:'发布此页',exact:true}).click();await expect(page.locator('.editor-state')).toContainText('已发布');
 const saved=await (await page.request.get(api+'/manage/content/pages-Home')).json();await page.request.put(api+'/manage/content/pages-Home',{data:{version:saved.version,data:saved.data}});
 await text.fill('keep conflict draft');await page.getByRole('button',{name:'保存草稿',exact:true}).click();await expect(page.locator('.studio-editor .desk-error')).toContainText('另一个窗口');assert.equal(await text.inputValue(),'keep conflict draft');
 await page.getByRole('button',{name:'重新读取服务器版本',exact:true}).click();await expect(text).toHaveValue(original);
 // Journal editor loads complete originals, preserves all 17 photos, changes English independently.
 await page.goto(base+'/manage?view=journal-editor');await page.locator('.journal-editor-list>button:has(img)').first().click();await expect(page.locator('.journal-editor-photos figure')).toHaveCount(17);
 await expect(page.getByLabel('英文正文',{exact:true})).not.toBeEmpty();
 await page.getByRole('button',{name:'预览',exact:true}).click();await expect(page.locator('.journal-editor-reading > img')).toHaveCount(17);
 await page.getByRole('button',{name:'编辑',exact:true}).click();await page.getByRole('button',{name:'保存草稿',exact:true}).click();await expect(page.locator('.editor-state')).toContainText('已保存');
 await page.setViewportSize({width:390,height:844});await layout(page,'mobile-selected-journal-editor');await page.screenshot({path:out+'/journal-editor-selected-390.png'});
 await page.goto(base+'/');await page.locator('.photo-tile').first().click();await expect(page.locator('.photo-dialog[open] .photo-current img')).toBeVisible();await page.keyboard.press('Escape');
 results.push({tag:'editor-and-runtime-flows',passed:true});
 await context.close();
}catch(e){errors.push({flow:true,error:e.stack});}finally{await browser.close();}
fs.writeFileSync(out+(process.env.STUDIO_FLOW_ONLY?'/flows.json':'/results.json'),JSON.stringify({results,errors},null,2));console.log(JSON.stringify({checks:results.length,errors}));if(errors.length)process.exitCode=1;
