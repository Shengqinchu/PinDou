// Pre-change baseline against the verified production frontend; synthetic API only.
import {chromium,expect} from '@playwright/test';
import http from 'node:http';
import fs from 'node:fs/promises';
import path from 'node:path';
import {fileURLToPath} from 'node:url';
import assert from 'node:assert/strict';
const root=fileURLToPath(new URL('../../',import.meta.url)),out=path.join(root,'artifacts/studio-integration-audit');
const dist=path.join(root,'artifacts/studio-auth-v6/frontend-current-baseline/05_web/dist');
const png=await fs.readFile(path.join(root,'01_research/tech/test_inputs/cartoon_synthetic.png'));
const palette=[{brand:'MARD',code:'A1',name_cn:'红色',name_en:'Red',hex:'#E23C38',rgb:[226,60,56]},
 {brand:'MARD',code:'B1',name_cn:'蓝色',name_en:'Blue',hex:'#2D79C7',rgb:[45,121,199]}];
let pattern={grid:Array.from({length:26},(_,r)=>Array.from({length:26},(_,c)=>palette[(r+c)%2])),palette_used:palette,color_counts:{A1:338,B1:338},bead_total:676,image_url:'/audit.png',metadata:{labeled_image_url:'/audit.png'}};
let writes=[],generationDelay=0;
const profile={user_id:'integration-audit',email:'audit@example.test',nickname:'Audit',paid_credits:512,ai_points_balance:512,ai_generation_cost_points:128,normal_trial_remaining:3,membership_expires_at:'2099-01-01T00:00:00Z'};
const artwork=id=>({artwork_id:id,title:'Audit pattern',size_preset:'26x26',style_preset:'script',pattern_data:pattern,preview_url:'/audit.png',thumbnail_url:'/audit.png'});
const server=http.createServer(async(req,res)=>{
 const url=new URL(req.url,'http://127.0.0.1');const send=(data,status=200)=>{res.writeHead(status,{'Content-Type':'application/json','Cache-Control':'no-store'});res.end(JSON.stringify(data));};
 if(url.pathname.startsWith('/api/v1/')){
   const chunks=[];for await(const chunk of req)chunks.push(chunk);const body=Buffer.concat(chunks);
   const endpoint=url.pathname.replace('/api/v1','');if(req.method!=='GET')writes.push({endpoint,method:req.method});
   if(['/user/profile','/wallet/profile'].includes(endpoint))return send(profile);
   if(endpoint==='/user/consent')return send({success:true});
   if(endpoint==='/payment/skus')return send({skus:[],ai_generation_cost_points:128});
   if(endpoint==='/generate/script'){
     const form=body.toString('latin1');
     const field=name=>form.match(new RegExp(`name="${name}"\\r\\n\\r\\n([^\\r]+)`))?.[1];
     Object.assign(writes.at(-1),{mode:field('mode'),size:field('size'),brand:field('brand'),hasImage:form.includes('name="raw_image"; filename="audit.png"')});
     if(generationDelay)await new Promise(r=>setTimeout(r,generationDelay));
     return send({artwork_id:'audit1',pattern,pattern_url:'/audit.png'});
   }
   if(endpoint==='/artwork/gallery')return send({items:Array.from({length:8},(_,i)=>({...artwork('audit'+i),bead_count:676,color_count:2})),total:16,page:Number(url.searchParams.get('page')||1),size:Number(url.searchParams.get('size')||8),has_more:true});
   if(/^\/artwork\/[^/]+\/pattern$/.test(endpoint)&&req.method==='PUT'){
     pattern=JSON.parse(body.toString()).pattern_json;return send({success:true,pattern,artwork:artwork('audit1'),pattern_url:'/audit.png'});
   }
   if(/^\/artwork\/[^/]+$/.test(endpoint))return send(artwork(endpoint.split('/').at(-1)));
   return send({});
 }
 if(url.pathname==='/audit.png'){res.writeHead(200,{'Content-Type':'image/png'});return res.end(png);}
 let file=path.resolve(dist,'.'+decodeURIComponent(url.pathname));
 if(!file.startsWith(dist+path.sep))file=path.join(dist,'index.html');
 try{if(!(await fs.stat(file)).isFile())file=path.join(dist,'index.html');}catch{file=path.join(dist,'index.html');}
 const types={'.html':'text/html','.js':'text/javascript','.css':'text/css','.png':'image/png','.woff2':'font/woff2','.svg':'image/svg+xml'};
 res.writeHead(200,{'Content-Type':types[path.extname(file)]||'application/octet-stream','Cache-Control':'no-store'});res.end(await fs.readFile(file));
});
await new Promise(r=>server.listen(19677,'127.0.0.1',r));
const base='http://127.0.0.1:19677',browser=await chromium.launch({headless:true,ignoreDefaultArgs:['--hide-scrollbars']}),results=[],findings=[],errors=[];
try{
 const context=await browser.newContext({viewport:{width:1440,height:960},locale:'zh-CN',acceptDownloads:true});
 await context.addInitScript(p=>{localStorage.setItem('pd_web_token','qa-integration');localStorage.setItem('pd_web_user',JSON.stringify(p));},profile);
 await context.route('**/*',r=>new URL(r.request().url()).hostname==='127.0.0.1'?r.continue():r.abort());
 const page=await context.newPage();page.setDefaultTimeout(8000);page.on('pageerror',e=>errors.push(e.message));
 await page.goto(base+'/upload');await expect(page.locator('.control-panel')).toBeVisible();
 await page.locator('input[type=file]').first().setInputFiles({name:'audit.png',mimeType:'image/png',buffer:png});
 await expect(page.locator('.file-strip')).toContainText('audit.png');
 await page.getByRole('link',{name:'教程',exact:true}).click();await page.goBack();
 const uploadLost=await page.locator('.file-strip').count()===0;
 findings.push({id:'draft-navigation',observed:uploadLost,detail:'Selected upload is lost after tutorial and browser Back.'});
 await page.locator('input[type=file]').first().setInputFiles({name:'audit.png',mimeType:'image/png',buffer:png});
 await page.getByRole('button',{name:/普通模式 消耗/}).click();await page.getByRole('button',{name:'26',exact:true}).click();
 await page.locator('.generate-cta').click();
 // Capture the exact confirmation controls from the actual page, not a guessed submission sequence.
 const confirmation=page.locator('[role=dialog]');
 if(await confirmation.count())await confirmation.getByRole('button',{name:'确认生成',exact:true}).click();
 await expect(page).toHaveURL(base+'/result/audit1');
 assert.equal(writes.filter(x=>x.endpoint==='/generate/script').length,1);
 assert.deepEqual(writes.find(x=>x.endpoint==='/generate/script'),{endpoint:'/generate/script',method:'POST',mode:'script',size:'26x26',brand:'MARD',hasImage:true});
 results.push({test:'upload, script request payload route and result (synthetic API)',passed:true});
 await page.goto(base+'/editor/audit1');await expect(page.locator('.pattern-editor__overlay')).toBeVisible();
 await page.getByRole('button',{name:'橡皮擦',exact:true}).click();
 const canvas=await page.locator('.pattern-editor__overlay').boundingBox();await page.mouse.click(canvas.x+canvas.width/2+4,canvas.y+canvas.height/2+4);
 await expect(page.getByRole('button',{name:'撤销',exact:true})).toBeEnabled();
 await page.getByRole('button',{name:'撤销',exact:true}).click();await expect(page.getByRole('button',{name:'重做',exact:true})).toBeEnabled();
 await page.getByRole('button',{name:'重做',exact:true}).click();
 await page.getByRole('button',{name:'保存',exact:true}).click();
 await expect.poll(()=>writes.filter(x=>x.endpoint.endsWith('/pattern')).length).toBeGreaterThan(0);
 assert.equal(pattern.grid.flat().filter(c=>c===null).length,1);
 await page.getByRole('button',{name:'全部颜色',exact:true}).click();await expect(page.getByRole('dialog',{name:'全部颜色'})).toBeVisible();
 await page.getByRole('button',{name:'关闭全部颜色',exact:true}).click();
 const downloadPromise=page.waitForEvent('download');await page.getByRole('button',{name:'下载',exact:true}).click();const download=await downloadPromise;assert(download.suggestedFilename().endsWith('.png'));
 results.push({test:'canvas erase, undo, redo, saved grid, palette and PNG download (synthetic API)',passed:true});
 for(const width of [320,390,768,1440,2560])for(const route of ['/upload','/result/audit1','/editor/audit1','/works','/tutorial']){
   await page.setViewportSize({width,height:900});await page.goto(base+route);
   const selector=route.startsWith('/editor/')?'.pattern-editor__overlay':route.startsWith('/result/')?'.result-card':route==='/works'?'.works-grid[aria-label="我的作品"]':route==='/tutorial'?'.tutorial-page':'.control-panel';
   await expect(page.locator(selector)).toBeVisible();await page.evaluate(()=>document.fonts.ready);
   const metrics=await page.evaluate(()=>({client:innerWidth,scroll:document.documentElement.scrollWidth}));
   results.push({test:'baseline layout',width,route,overflow:metrics.scroll>metrics.client+1});
   if(width===390&&route==='/editor/audit1')await page.screenshot({path:path.join(out,'editor-before-mobile.png')});
 }
 await page.setViewportSize({width:1440,height:960});await page.goto(base+'/upload');
 await page.locator('input[type=file]').first().setInputFiles({name:'audit.png',mimeType:'image/png',buffer:png});
 await page.getByRole('button',{name:/普通模式 消耗/}).click();generationDelay=1800;
 await page.locator('.generate-cta').click();if(await confirmation.count())await confirmation.getByRole('button',{name:'确认生成',exact:true}).click();
 await expect(page).toHaveURL(/\/loading/);await page.getByRole('link',{name:'教程',exact:true}).click();
 await expect(page).toHaveURL(/\/tutorial/);await page.waitForTimeout(2300);
 findings.push({id:'late-generation-navigation',observed:page.url().includes('/result/'),detail:'Generation completion navigates away from the tutorial after the user left the loading page.'});
 assert.deepEqual(errors,[]);await context.close();
}finally{
 await browser.close();server.closeAllConnections();await new Promise(r=>server.close(r));
 await fs.writeFile(path.join(out,'baseline.json'),JSON.stringify({fixture:'verified production frontend, loopback synthetic APIs, no paid generation or production writes',results,findings,errors},null,2));
}
console.log(JSON.stringify({results,findings,errors},null,2));
