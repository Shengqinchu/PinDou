import {chromium,expect} from '@playwright/test';import fs from 'node:fs/promises';import {fileURLToPath} from 'node:url';
const base='http://127.0.0.1:19678',out=new URL('../../artifacts/generator-integration/',import.meta.url);
const browser=await chromium.launch({headless:true,ignoreDefaultArgs:['--hide-scrollbars']});
const errors=[];
try{
 const context=await browser.newContext({locale:'zh-CN',viewport:{width:1440,height:1000},acceptDownloads:true});
 const page=await context.newPage();page.setDefaultTimeout(10000);page.on('pageerror',e=>errors.push(e.message));
 await page.goto(base+'/');await page.evaluate(()=>window.__sameDocument='native');
 await page.locator('.vision-navigation a[href="/tools"]').click();await expect(page.locator('.control-panel')).toBeVisible();
 if(await page.evaluate(()=>window.__sameDocument)!=='native')throw Error('Entry changed the document');
 await page.screenshot({path:fileURLToPath(new URL('upload-zh-desktop.png',out)),fullPage:true});
 await page.locator('input[type=file]').first().setInputFiles(fileURLToPath(new URL('../../01_research/tech/test_inputs/cartoon_synthetic.png',import.meta.url)));
 await page.locator('.generator-heading nav a[href="/tools/tutorial"]').click();await expect(page.locator('.tutorial-page')).toBeVisible();
 await page.locator('.generator-heading nav a[href="/tools"]').click();await expect(page.locator('.file-strip')).toContainText('cartoon_synthetic.png');
 await page.locator('.vision-header-actions .language-button').click();await expect(page.locator('.generator-heading h1')).toHaveText('Pattern maker');
 await expect(page.locator('.file-strip')).toContainText('cartoon_synthetic.png');
 const enText=await page.locator('.generator-workspace').first().innerText();
 await fs.writeFile(new URL('upload-english.txt',out),enText);
 await page.screenshot({path:fileURLToPath(new URL('upload-en-desktop.png',out)),fullPage:true});
 await page.getByRole('button',{name:/Standard mode/}).click();await page.getByRole('button',{name:'26',exact:true}).click();
 await page.locator('.generate-cta').click();await page.getByRole('button',{name:'Confirm generation',exact:true}).click();
 await expect(page).toHaveURL(/\/tools\/result\//);await expect(page.locator('.result-card')).toBeVisible();
 await page.getByRole('link',{name:'Edit pattern',exact:true}).click();await expect(page.locator('.pattern-editor__overlay')).toBeVisible();
 await page.screenshot({path:fileURLToPath(new URL('editor-en-desktop.png',out))});
 for(const width of [320,390,768,1440,2560]){
  await page.setViewportSize({width,height:900});await expect(page.locator('.pattern-editor__overlay')).toBeVisible();
  if(width===390)await page.screenshot({path:fileURLToPath(new URL('editor-en-mobile.png',out))});
 }
 await page.setViewportSize({width:1440,height:1000});await page.getByRole('button',{name:'All colours',exact:true}).click();
 await expect(page.getByRole('dialog',{name:'All colours',exact:true})).toBeVisible();
 await fs.writeFile(new URL('editor-english.txt',out),await page.locator('body').innerText());
 await fs.writeFile(new URL('stage1.json',out),JSON.stringify({sameDocument:true,draftRestored:true,languageKeptPhoto:true,generated:true,editorLoaded:true,errors},null,2));
 console.log(JSON.stringify({errors,englishUnknown:enText.includes('We could not complete this action')},null,2));
 await context.close();
}catch(error){await fs.writeFile(new URL('stage1-error.json',out),JSON.stringify({error:String(error),errors},null,2));throw error;}finally{await browser.close();}
