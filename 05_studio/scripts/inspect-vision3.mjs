import {chromium} from '@playwright/test';
import fs from 'node:fs';
const out='../artifacts/vision3/inspection';fs.mkdirSync(out,{recursive:true});
const browser=await chromium.launch({headless:true,ignoreDefaultArgs:['--hide-scrollbars'],args:['--disable-features=OverlayScrollbar']});
const errors=[],results=[];
try{
 for(const width of [1440,390]){
  const context=await browser.newContext({viewport:{width,height:width===1440?1000:844},reducedMotion:null});
  await context.addInitScript(()=>{localStorage.setItem('puppy-studio-motion','full');sessionStorage.setItem('puppy-studio-admin','local-qa');});
  const page=await context.newPage();page.on('pageerror',e=>errors.push(e.message));
  for(const route of ['', 'visit','journal','manage?view=content','manage?view=journal-editor','manage?view=reservation-calendar']){
   await page.goto('http://127.0.0.1:5184/'+route);
   await page.waitForTimeout(1800);await page.evaluate(()=>document.fonts.ready);
   const file=(route||'home').replace(/[?=]/g,'-');await page.screenshot({path:`${out}/${file}-${width}.png`,fullPage:route==='visit'});
   results.push({width,route,url:page.url(),...(await page.evaluate(()=>({overflow:document.documentElement.scrollWidth>innerWidth+1,heading:document.querySelector('h1')?.textContent,font:document.querySelector('h1')?getComputedStyle(document.querySelector('h1')).fontFamily:null,brokenImages:[...document.images].filter(i=>i.complete&&!i.naturalWidth).map(i=>i.src)})))});
  }
  await context.close();
 }
 fs.writeFileSync(out+'/results.json',JSON.stringify({results,errors},null,2));console.log(JSON.stringify({results,errors}));
}finally{await browser.close();}
