import {chromium,webkit,expect} from '@playwright/test';
import fs from 'node:fs/promises';
import assert from 'node:assert/strict';
const base='https://pindoupuppy.com',out=new URL('../../artifacts/cancellation/',import.meta.url);
const {build}=JSON.parse(await fs.readFile(new URL('../dist/version.json',import.meta.url),'utf8'));
const results=[];
for(const [name,engine] of [['chromium',chromium],['webkit',webkit]]){
 const browser=await engine.launch({headless:true});
 try{
  for(const viewport of [{width:1706,height:1100},{width:390,height:844}]){
   const context=await browser.newContext({viewport,locale:'zh-CN'}),page=await context.newPage(),errors=[];
   page.on('pageerror',e=>errors.push(e.message));
   await page.goto(base+'/account');await expect(page.locator('meta[name=studio-build]')).toHaveAttribute('content',build);
   await expect(page.getByRole('tab',{name:'登录',exact:true})).toHaveAttribute('aria-selected','true');
   assert(await page.evaluate(()=>[...document.styleSheets].some(sheet=>{try{return [...sheet.cssRules].some(rule=>rule.cssText.includes('.cancellation-dialog'));}catch{return false;}})));
   assert(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth+1));
   const denied=await page.request.get(base+'/studio-api/reservations/VIS-READONLY-CHECK/cancellation');assert.equal(denied.status(),401);
   results.push({engine:name,viewport,build,permission_status:denied.status(),errors});assert.deepEqual(errors,[]);
   await context.close();
  }
 }finally{await browser.close();}
}
await fs.writeFile(new URL('live-verification.json',out),JSON.stringify({read_only:true,results},null,2));
console.log(JSON.stringify({passed:true,read_only:true,states:results.length,build}));
