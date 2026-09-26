// Operates only on a loopback QA database. Never creates production content.
import { chromium,webkit,firefox,expect } from '@playwright/test';
import fs from 'node:fs/promises';
import assert from 'node:assert/strict';
const base='http://127.0.0.1:4184',out='../artifacts/vision4';
const checks=[],issues=[],errors=[];
await fs.mkdir(out,{recursive:true});
const sizes=[[320,568],[360,800],[390,844],[430,932],[568,320],[667,375],[768,1024],[820,1180],[1024,768],[1280,720],[1366,768],[1440,900],[1536,864],[1920,1080],[2560,1440],[720,450]];
async function settle(page){await page.evaluate(()=>new Promise(resolve=>requestAnimationFrame(()=>requestAnimationFrame(resolve))));}
async function layout(page,tag){
  await settle(page);
  const value=await page.evaluate(()=>{
    const children=[...document.querySelectorAll('.vision-header>*,.editor-commandbar>*')].filter(e=>getComputedStyle(e).display!=='none');
    const rect=children.map(e=>({parent:e.parentElement.className,r:e.getBoundingClientRect()}));
    const overlaps=rect.some((v,i)=>i&&v.parent===rect[i-1].parent&&v.r.x<rect[i-1].r.right-1&&v.r.y<rect[i-1].r.bottom-1);
    const clippedControls=[...document.querySelectorAll('button,input,textarea,select,a,summary')].filter(e=>{
      if(e.closest('[inert],[aria-hidden="true"]'))return false;
      const r=e.getBoundingClientRect();if(!r.width||!r.height||r.right<=innerWidth+1&&r.left>=-1)return false;
      let parent=e.parentElement;while(parent){const style=getComputedStyle(parent);if(/auto|scroll/.test(style.overflowX)&&parent.scrollWidth>parent.clientWidth+1)return false;parent=parent.parentElement;}
      return true;
    }).map(e=>e.className).slice(0,5);
    return {overflow:document.documentElement.scrollWidth>innerWidth+1,overlaps,clippedControls,scrollY,heroBottom:document.querySelector('.vision-hero-actions')?.getBoundingClientRect().bottom};
  });
  if(value.overflow||value.overlaps||value.clippedControls.length)issues.push({tag,...value});
  if(/-\/-\d+x\d+$/.test(tag)) {
    const [,width,height]=tag.match(/-(\d+)x(\d+)$/).map(Number);
    if(width>=761&&height>=720&&value.heroBottom>height+1)issues.push({tag,heroClipped:value.heroBottom-height});
  }
  checks.push({tag,...value});
}
for(const [name,engine,viewports] of (process.argv.includes('--functional-only')?[]:[['chromium',chromium,sizes],['webkit',webkit,[[320,568],[390,844],[667,375],[820,1180],[1440,900]]],['firefox',firefox,[[390,844],[1366,768]]]])){
  const browser=await engine.launch({headless:true});
  try{for(const lang of ['zh','en']){
    const context=await browser.newContext({viewport:{width:1440,height:900},reducedMotion:'reduce'});
    await context.addInitScript(lang=>localStorage.setItem('puppy-studio-language',lang),lang);
    const page=await context.newPage();page.on('pageerror',e=>errors.push({name,message:e.message}));
    for(const route of ['/','/visit','/details','/journal','/shop']){
      await page.goto(base+route);await expect(page.locator('h1').first()).toBeVisible();await page.evaluate(()=>document.fonts.ready);
      for(const [width,height] of viewports){await page.setViewportSize({width,height});await layout(page,`${name}-${lang}-${route}-${width}x${height}`);}
      if(name==='chromium'&&lang==='zh')for(const [width,height] of [[390,844],[1366,768]]){await page.setViewportSize({width,height});await settle(page);await page.screenshot({path:`${out}/${route.replaceAll('/','')||'home'}-${width}.png`,fullPage:true});}
    }
    await context.close();
  }}finally{await browser.close();}
}
const browser=await chromium.launch({headless:true,ignoreDefaultArgs:['--hide-scrollbars']});
try{
  const context=await browser.newContext({viewport:{width:1440,height:900},reducedMotion:'reduce',permissions:['clipboard-read','clipboard-write']});
  const page=await context.newPage();page.on('pageerror',e=>errors.push({name:'flows',message:e.message}));
  await page.goto(base+'/#space');await expect(page.locator('h1')).toBeVisible();assert.equal(await page.evaluate(()=>scrollY),0);assert.equal(new URL(page.url()).hash,'');
  await page.evaluate(()=>scrollTo(0,1100));await page.reload();await expect(page.locator('h1')).toBeVisible();assert.equal(await page.evaluate(()=>scrollY),0);
  const before=await page.locator('.vision-hero h1').boundingBox();await page.locator('.vision-header-actions>.icon-button').last().click();await expect(page.locator('dialog[open]')).toHaveCount(1);const during=await page.locator('.vision-hero h1').boundingBox();assert(Math.abs(before.x-during.x)<1);await page.keyboard.press('Escape');
  await page.locator('.vision-footer .copy-contact-button').click();assert.equal(await page.evaluate(()=>navigator.clipboard.readText()),'xiaogoushuangji');
  await page.evaluate(()=>{Object.defineProperty(navigator,'clipboard',{configurable:true,value:{writeText:()=>Promise.reject(new Error('denied'))}});document.execCommand=()=>false;});
  await page.locator('.vision-footer .copy-contact-button').click();await expect(page.locator('.copy-contact-manual input')).toHaveValue('xiaogoushuangji');
  checks.push({tag:'fresh-start-reload-menu-copy',scrollTop:true,menuShift:before.x-during.x,clipboard:true});
  await page.goto(base+'/details');assert.equal(await page.locator('#notes details[open]').count(),3);assert.equal(await page.locator('.process-step').count(),5);assert.equal(await page.locator('.process-photo').count(),7);await page.locator('.process-photo').first().click();await expect(page.locator('dialog[open]')).toHaveCount(1);await page.keyboard.press('Escape');
  // Editor round trip, global search, actual file chooser and repeated same-file selection.
  await page.evaluate(()=>sessionStorage.setItem('puppy-studio-admin','qa-admin'));
  await page.goto(base+'/manage?view=content');await expect(page.locator('.editor-fields')).toBeVisible();
  await expect(page.locator('.desk-navigation>button')).toHaveCount(4);
  await page.locator('.editor-global-search input').fill('铺子里');await page.locator('.editor-search-results button').first().click();await expect(page.locator('.editor-commandbar select')).toHaveValue('pages-Journal');
  await page.locator('.editor-fields textarea').first().fill('铺子里 · 本地验证');await page.getByRole('button',{name:'发布此页',exact:true}).click();await expect(page.locator('.editor-state')).toContainText('已发布');
  const live=await page.request.get(base+'/studio-api/content');assert.equal((await live.json()).modules['pages-Journal'].life_in_our_1d9155[0],'铺子里 · 本地验证');
  await page.getByRole('button',{name:'图片与品牌',exact:true}).click();await expect(page.locator('.editor-commandbar select')).toHaveValue('media');
  const field=page.locator('.editor-field-group').filter({has:page.getByRole('heading',{name:'首页插画',exact:true})});
  for(let i=0;i<2;i++){
    const chooser=page.waitForEvent('filechooser');await field.getByRole('button',{name:'替换图片',exact:true}).click();await(await chooser).setFiles('../artifacts/vision3/originals/space-01.jpg');
    await expect(field.locator('.media-upload-status')).toContainText('图片已加入');await expect(field.locator('.editor-image-preview')).toHaveAttribute('src',/studio-api\/media/);
    const b=await field.locator('.media-upload-button').boundingBox(),help=await field.locator('.form-help').boundingBox();assert(help.y>=b.y+b.height+6);
  }
  const chooser=page.waitForEvent('filechooser');await field.getByRole('button',{name:'替换图片',exact:true}).click();await(await chooser).setFiles({name:'broken.jpg',mimeType:'image/jpeg',buffer:Buffer.from('not-an-image')});
  await expect(field.locator('.media-upload-status[role=alert]')).toContainText('请选择有效');await expect(field.locator('.media-upload-status')).toContainText('请求编号');
  await expect(field.getByRole('button',{name:'替换图片',exact:true})).toBeEnabled();
  await page.locator('.editor-diagnostics summary').click();await expect(page.locator('.editor-diagnostics-events')).toContainText('image_invalid');
  await page.setViewportSize({width:390,height:844});await layout(page,'editor-mobile');await page.screenshot({path:out+'/editor-upload-390.png',fullPage:true});
  checks.push({tag:'editor-functional',findTitle:true,atomicPublish:true,fourTabs:true,sameFileTwice:true,localError:true,requestId:true,diagnostics:true});
  await page.setViewportSize({width:1440,height:900});
  const existing=(await(await page.request.get(base+'/studio-api/journal')).json()).posts[0];
  let polls=0;
  await page.route('**/studio-api/manage/journal-import-jobs',route=>route.fulfill({status:202,json:{id:'fixture-job',status:'queued',completed:0,total:0}}));
  await page.route('**/studio-api/manage/journal-import-jobs/fixture-job',route=>{polls++;return route.fulfill({json:polls<3?{status:polls===1?'queued':'running',completed:1,total:existing.images.length}:{status:'done',completed:existing.images.length,total:existing.images.length,result:{id:existing.id,data:existing,version:1,published:true}}});});
  await page.goto(base+'/manage?view=journal-editor');await page.locator('.journal-import-bar input').fill(existing.source);await page.getByRole('button',{name:'导入日记',exact:true}).click();
  await expect.poll(()=>page.evaluate(()=>sessionStorage.getItem('puppy-studio-import-job'))).toBe('fixture-job');
  await page.reload();await expect(page.locator('.journal-editor-form')).toBeVisible({timeout:15000});assert.equal(await page.evaluate(()=>sessionStorage.getItem('puppy-studio-import-job')),null);
  await expect(page.locator('.journal-editor-photos figure')).toHaveCount(existing.images.length);
  checks.push({tag:'tracked-import-resumes-after-reload',photos:existing.images.length});
  await context.close();
  const animated=await browser.newContext({viewport:{width:1366,height:768},reducedMotion:'no-preference'}),a=await animated.newPage();
  await a.goto(base+'/?motion=full');await expect(a.locator('.hero-star')).toBeVisible();await a.waitForTimeout(1800);
  const star=a.locator('.hero-star .motif-touch');await a.locator('.hero-star').hover();await a.waitForTimeout(500);const hover=await star.evaluate(e=>getComputedStyle(e).transform);assert.notEqual(hover,'none');
  await a.locator('.hero-star').click();await a.waitForTimeout(180);const press=await star.evaluate(e=>getComputedStyle(e).transform);assert.notEqual(press,hover);await a.waitForTimeout(1300);
  await a.screenshot({path:out+'/home-full-motion.png'});checks.push({tag:'motif-hover-and-pinch',hover,press});await animated.close();
}catch(e){issues.push({tag:'functional',error:e.stack});}finally{await browser.close();}
await fs.writeFile(out+(process.argv.includes('--functional-only')?'/qa-functional.json':'/qa-results.json'),JSON.stringify({checks,issues,errors},null,2));
console.log(JSON.stringify({checks:checks.length,issues,errors},null,2));
if(issues.length||errors.length)process.exitCode=1;
