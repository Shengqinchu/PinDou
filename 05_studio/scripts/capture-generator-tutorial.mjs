// Capture the actual integrated UI with the owner's approved Kitty example.
import {chromium,expect} from '@playwright/test';import fs from 'node:fs/promises';import {fileURLToPath} from 'node:url';
const base='http://127.0.0.1:19678',assets=new URL('../../05_generator/src/assets/tutorial/',import.meta.url),browser=await chromium.launch({headless:true});
const png=await fs.readFile(new URL('./fixtures/generator-tutorial/kitty-source.png',import.meta.url));
try{for(const lang of ['zh','en']){
 const ctx=await browser.newContext({viewport:{width:1440,height:1000},locale:lang==='zh'?'zh-CN':'en-CA'});
 await ctx.addInitScript(lang=>{localStorage.setItem('puppy-studio-locale',lang);localStorage.setItem('pd_web_token','qa-owner');localStorage.setItem('pd_web_user',JSON.stringify({user_id:'qa-owner',nickname:'Example'}));},lang);
 const page=await ctx.newPage();const shot=async(name,selector)=>{await page.evaluate(()=>document.fonts.ready);await page.locator(selector).first().screenshot({path:fileURLToPath(new URL(`${name}-${lang}.png`,assets))});};
 await page.request.post(base+'/qa/controls',{data:{delay:2,tutorial:true}});await page.goto(base+'/tools');await expect(page.locator('.control-panel')).toBeVisible();
 await page.locator('input[type=file]').first().setInputFiles({name:'kitty.png',mimeType:'image/png',buffer:png});
 await page.getByRole('button',{name:lang==='zh'?'普通模式':'Standard mode',exact:false}).click();
 await page.getByRole('button',{name:'104',exact:true}).click();
 await shot('upload-page','.upload-stage');await shot('options-panel','.control-panel');
 await page.locator('.generate-cta').click();await page.locator('.confirm-submit').click();await expect(page.locator('.loading-panel')).toBeVisible();await shot('loading-page','.loading-panel');await expect(page).toHaveURL(/\/tools\/result\//,{timeout:15000});
 await expect(page.locator('.result-stats dd').nth(0)).toHaveText('104 × 104');
 await expect(page.locator('.result-stats dd').nth(1)).toHaveText('6062');
 await expect(page.locator('.result-stats dd').nth(2)).toHaveText('5');
 await shot('result-page','.result-shell');
 await page.locator('a[href*="/tools/editor/"]').click();await expect(page.locator('.pattern-editor__overlay')).toBeVisible();await shot('editor-page','.editor-page');
 await page.goto(base+'/tools');await page.locator('.generator-allowance>button').click();await expect(page.locator('.pricing-modal[open]')).toBeVisible();await expect(page.locator('.sku-card').first()).toBeVisible();await shot('pricing-modal','.pricing-modal');
 await page.locator('.cdk-toggle').click();await shot('cdk-redeem','.pricing-modal');await page.keyboard.press('Escape');await ctx.close();
}console.log('Captured 14 bilingual tutorial panels.');}finally{await browser.close();}
