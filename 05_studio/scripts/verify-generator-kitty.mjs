// Loopback-only regression of the owner-selected tutorial and works navigation.
import {chromium, webkit, expect} from '@playwright/test';
import fs from 'node:fs/promises';
import crypto from 'node:crypto';
import assert from 'node:assert/strict';
const base='http://127.0.0.1:19678';
const out=new URL('../../artifacts/generator-kitty-fix/',import.meta.url);
const source=new URL('./fixtures/generator-tutorial/kitty-source.png',import.meta.url);
const png=await fs.readFile(source), results=[],errors=[];
const sha=body=>crypto.createHash('sha256').update(body).digest('hex');
for(const [engine,type] of [['chromium',chromium],['webkit',webkit]]){
 const browser=await type.launch({headless:true});
 try {for(const lang of ['zh','en']){
  const ctx=await browser.newContext({viewport:{width:1440,height:1000},reducedMotion:engine==='webkit'?'reduce':'no-preference'});
  await ctx.addInitScript(lang=>{localStorage.setItem('puppy-studio-language',lang);localStorage.setItem('pd_web_token','qa-owner');localStorage.setItem('pd_web_user',JSON.stringify({user_id:'qa-owner',nickname:'QA'}));},lang);
  const page=await ctx.newPage();page.setDefaultTimeout(8000);page.on('pageerror',e=>errors.push(e.message));
  await page.request.post(base+'/qa/controls',{data:{clear:true,tutorial:true}});
  await page.goto(base+'/tools');await expect(page.locator('.control-panel')).toBeVisible();
  await page.locator('input[type=file]').first().setInputFiles({name:'kitty.png',mimeType:'image/png',buffer:png});
  await page.locator('.generator-heading a[href="/tools/works"]').click();await expect(page.locator('.works-empty')).toBeVisible();
  await page.goBack();await expect(page.locator('.file-strip')).toContainText('kitty.png');
  await page.getByRole('button',{name:lang==='zh'?'普通模式':'Standard mode'}).click();await page.getByRole('button',{name:'104',exact:true}).click();
  await page.locator('.generate-cta').click();await page.locator('.confirm-submit').click();
  await expect(page).toHaveURL(/\/tools\/result\//);await expect(page.locator('.result-stats dd')).toHaveText(['104 × 104','6062','5']);
  const resultUrl=page.url();
  await page.locator('.generator-heading a[href="/tools/works"]').click();await expect(page.locator('button.work-card')).toHaveCount(1);
  await page.locator('button.work-card').click();await expect(page).toHaveURL(resultUrl);
  results.push({test:'upload survives works/back and new artwork opens from gallery',engine,lang});
  for(const [width,height] of [[320,568],[390,844],[768,1024],[844,390],[1440,1000],[2560,1440]]){
   await page.setViewportSize({width,height});await page.evaluate(()=>document.fonts.ready);
   const metrics=await page.locator('.result-size-number').evaluate(el=>({text:el.textContent,width:el.clientWidth,content:el.scrollWidth,page:document.documentElement.scrollWidth,viewport:innerWidth}));
   assert.equal(metrics.text,'104 × 104');assert(metrics.content<=metrics.width+1,JSON.stringify(metrics));assert(metrics.page<=metrics.viewport+1,JSON.stringify(metrics));
   results.push({test:'full size and layout',engine,lang,width,height});
  }
  await page.setViewportSize({width:1440,height:1000});await page.locator('.generator-heading a[href="/tools/tutorial"]').click();await expect(page.locator('.tutorial-page')).toBeVisible();
  const sources=await page.locator('.tutorial-page img').evaluateAll(images=>[...new Set(images.map(img=>img.src))]);
  assert.equal(sources.length,7);
  for(const src of sources){
   const match=new URL(src).pathname.match(/\/([^/]+)-(zh|en)-[^/]+\.png$/);assert(match,src);assert.equal(match[2],lang);
   const expected=await fs.readFile(new URL(`../../05_generator/src/assets/tutorial/${match[1]}-${lang}.png`,import.meta.url));
   const response=await page.request.get(src);assert(response.ok());assert.equal(sha(await response.body()),sha(expected));
  }
  for(const [width,height] of [[320,568],[390,844],[844,390],[1440,1000]]){
   await page.setViewportSize({width,height});
   await expect.poll(()=>page.evaluate(()=>document.documentElement.scrollWidth-innerWidth),{message:`tutorial overflow ${engine} ${lang} ${width}x${height}`}).toBeLessThanOrEqual(1);
   if(engine==='chromium'&&lang==='zh'&&(width===390||width===1440))await page.screenshot({path:new URL(`tutorial-${width}.png`,out).pathname.replace(/^\/([A-Za-z]:)/,'$1')});
  }
  results.push({test:'all seven tutorial panels match approved Kitty capture',engine,lang});await ctx.close();
 }}finally{await browser.close();}
}
assert.deepEqual(errors,[]);
await fs.writeFile(new URL('browser-verification.json',out),JSON.stringify({results,errors,productionWrites:0},null,2));
console.log(JSON.stringify({checks:results.length,errors:errors.length}));
