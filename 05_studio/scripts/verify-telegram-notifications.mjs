import {chromium,webkit,expect} from '@playwright/test';
import AxeBuilder from '@axe-core/playwright';
import fs from 'node:fs/promises';
import assert from 'node:assert/strict';
import {fileURLToPath} from 'node:url';
const base='http://127.0.0.1:19689',out=new URL('../../artifacts/telegram/',import.meta.url);
await fs.mkdir(out,{recursive:true});
const errors=[],states=[];
for(const [engine,type] of [['chromium',chromium],['webkit',webkit]]){
 const browser=await type.launch({headless:true,ignoreDefaultArgs:['--hide-scrollbars']});
 try{
  for(const lang of ['zh','en'])for(const width of engine==='chromium'?[320,390,768,1440,2560]:[390,1440]){
   const context=await browser.newContext({viewport:{width,height:width<600?844:1000},locale:lang==='zh'?'zh-CN':'en-CA'});
   try{
    await context.addInitScript(lang=>{sessionStorage.setItem('puppy-studio-admin','qa-admin');localStorage.setItem('puppy-studio-locale',lang);},lang);
    const page=await context.newPage();page.on('pageerror',e=>errors.push(e.message));
    await page.request.post(base+'/qa/telegram-reset');await page.goto(base+'/manage?view=reservations');
    await page.locator('.telegram-notifications-open').click();
    const panel=page.locator('.studio-drawer[open] .telegram-notifications');
    await expect(panel).toBeVisible();const token=panel.locator('input[type=password]');
    await token.fill('invalid-token');await panel.locator('button[type=submit]').click();await expect(panel.locator('[role=alert]')).toBeVisible();
    await token.fill('1234567890:ABCDEFGHIJKLMNOPQRSTUVWXYZ_1234567890');await panel.locator('button[type=submit]').click();await expect(token).toHaveValue('');
    await panel.locator('.telegram-bind').click();const link=panel.locator('.telegram-pair-link');await expect(link).toBeVisible();
    const url=new URL(await link.getAttribute('href'));assert.equal(url.origin,'https://t.me');
    await page.request.post(base+'/qa/telegram-start',{data:{challenge:url.searchParams.get('start')}});
    await panel.locator('.telegram-pairing button.desk-link').click();
    await expect(panel.locator('.telegram-pairing')).toContainText('Local Owner',{timeout:20000});
    await expect(panel.locator('.telegram-log [data-state=accepted]')).toHaveCount(1,{timeout:12000});
    await panel.locator('.telegram-test button').click();await expect(panel.locator('.telegram-log [data-state=accepted]')).toHaveCount(2,{timeout:12000});
    const response=await page.request.get(base+'/studio-api/manage/telegram-notifications');const json=await response.json();assert.equal(json.connected,true);assert(!JSON.stringify(json).includes('ABCDEFGHIJKLMNOPQRSTUVWXYZ'));
    const sc=await (await page.request.get(base+'/studio-api/manage/owner-notifications')).json();assert.equal(sc.enabled,1);assert.equal(sc.used,0);
    await page.evaluate(()=>document.fonts.ready);
    const bounds=await panel.evaluate(el=>{const r=el.closest('.drawer-panel').getBoundingClientRect();const input=el.querySelector('input[type=password]').getBoundingClientRect();return{left:r.left,right:r.right,top:r.top,bottom:r.bottom,inputLeft:input.left,inputRight:input.right,width:innerWidth,height:innerHeight,scrollWidth:document.documentElement.scrollWidth};});
    assert(bounds.scrollWidth<=width+1);assert(bounds.left>=-1&&bounds.right<=width+1&&bounds.top>=-1&&bounds.bottom<=bounds.height+1);assert(bounds.inputLeft>=0&&bounds.inputRight<=width);
    states.push({engine,lang,...bounds});
    if(lang==='zh'&&[390,1440].includes(width))await page.screenshot({path:fileURLToPath(new URL(`${engine}-${width}.png`,out))});
    if(engine==='chromium'&&lang==='en'&&width===1440){const axe=await new AxeBuilder({page}).include('.studio-drawer[open]').analyze();await fs.writeFile(new URL('accessibility.json',out),JSON.stringify(axe.violations,null,2));assert.equal(axe.violations.length,0);}
    await token.fill('1234567890:UNSAVED_TOKEN_ABCDEFGHIJKLMNOPQRSTUVWXYZ');await page.keyboard.press('Escape');await expect(page.locator('.studio-drawer[open]')).toHaveCount(0);
    await page.locator('.telegram-notifications-open').click();await expect(token).toHaveValue('');
   }finally{await context.close();}
  }
 }finally{await browser.close();}
}
assert.deepEqual(errors,[]);await fs.writeFile(new URL('browser-verification.json',out),JSON.stringify({states,errors},null,2));console.log(JSON.stringify({states:states.length,errors}));
