import {chromium,webkit,expect} from '@playwright/test';
import AxeBuilder from '@axe-core/playwright';
import fs from 'node:fs/promises';
import assert from 'node:assert/strict';
import {fileURLToPath} from 'node:url';
const base='http://127.0.0.1:19688',out=new URL('../../artifacts/serverchan/',import.meta.url);
await fs.mkdir(out,{recursive:true});
const engines=[['chromium',chromium],['webkit',webkit]],errors=[],states=[];
for(const [engine,type] of engines){
 const browser=await type.launch({headless:true,ignoreDefaultArgs:['--hide-scrollbars']});
 try{
  for(const lang of ['zh','en'])for(const width of engine==='chromium'?[320,390,768,1440,2560]:[390,1440]){
   const context=await browser.newContext({viewport:{width,height:width<600?844:1000},locale:lang==='zh'?'zh-CN':'en-CA'});
   try{
    await context.addInitScript(lang=>{sessionStorage.setItem('puppy-studio-admin','qa-admin');localStorage.setItem('puppy-studio-locale',lang);},lang);
    const page=await context.newPage();page.on('pageerror',e=>errors.push(e.message));
    await page.request.post(base+'/qa/owner-alert-reset');await page.goto(base+'/manage?view=reservations');
    await page.locator('.owner-notifications-open').click();
    const panel=page.locator('.studio-drawer[open] .owner-notifications');
    await expect(panel).toBeVisible();await expect(panel.locator('input[type=password]')).toBeVisible();
    const key=panel.locator('input[type=password]');
    await key.fill('wrong-key');await panel.getByRole('switch').click();await panel.locator('button[type=submit]').click();
    await expect(panel.locator('[role=alert]')).toBeVisible();
    await key.fill('SCT12345678901234567890ForLocalBrowserOnly');
    await panel.locator('button[type=submit]').click();await expect(key).toHaveValue('');
    const test=panel.locator('.owner-notification-test button');await expect(test).toBeEnabled();
    await test.click();await expect(panel.locator('.owner-notification-log [data-state=accepted]')).toHaveCount(1,{timeout:12000});
    const status=await page.request.get(base+'/studio-api/manage/owner-notifications');const json=await status.json();
    assert.equal(json.used,1);assert(!JSON.stringify(json).includes('SCT123'));
    await page.evaluate(()=>document.fonts.ready);
    const bounds=await panel.evaluate(el=>{const r=el.closest('.drawer-panel').getBoundingClientRect();const input=el.querySelector('input[type=password]').getBoundingClientRect();return {right:r.right,left:r.left,top:r.top,bottom:r.bottom,inputLeft:input.left,inputRight:input.right,width:innerWidth,height:innerHeight,scrollWidth:document.documentElement.scrollWidth};});
    assert(bounds.scrollWidth<=width+1);assert(bounds.left>=-1&&bounds.right<=width+1&&bounds.top>=-1&&bounds.bottom<=bounds.height+1);assert(bounds.inputLeft>=0&&bounds.inputRight<=width);
    states.push({engine,lang,width,...bounds});
    if(lang==='zh'&&[390,1440].includes(width))await page.screenshot({path:fileURLToPath(new URL(`${engine}-${width}.png`,out))});
    if(engine==='chromium'&&lang==='en'&&width===1440){const axe=await new AxeBuilder({page}).include('.studio-drawer[open]').analyze();await fs.writeFile(new URL('accessibility.json',out),JSON.stringify(axe.violations,null,2));assert.equal(axe.violations.length,0);}
    // Unsaved key is cleared on dismissal; only the private server copy remains.
    await key.fill('SCTUnsaved12345678901234567890');await page.keyboard.press('Escape');
    await expect(page.locator('.studio-drawer[open]')).toHaveCount(0);
    await page.locator('.owner-notifications-open').click();await expect(key).toHaveValue('');
   }finally{await context.close();}
  }
 }finally{await browser.close();}
}
assert.deepEqual(errors,[]);await fs.writeFile(new URL('browser-verification.json',out),JSON.stringify({states,errors},null,2));console.log(JSON.stringify({states:states.length,errors}));
