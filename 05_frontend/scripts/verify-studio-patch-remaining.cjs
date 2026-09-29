// Native-page browser checks; all API writes use a disposable loopback database.
const fs=require('fs'),path=require('path'),http=require('http'),assert=require('node:assert/strict');
const {chromium,webkit,expect,request}=require('../../05_studio/node_modules/@playwright/test');
const root=path.resolve(__dirname,'../..'),build=path.join(root,'05_frontend/dist/build/h5'),out=path.join(root,'artifacts/patch-quota/native-browser');
fs.mkdirSync(out,{recursive:true});
const server=http.createServer((req,res)=>{const p=new URL(req.url,'http://localhost').pathname,f=path.resolve(build,p.replace(/^\/h5\/?/,'')||'index.html');if(!f.startsWith(build+path.sep))return res.writeHead(403).end();try{res.setHeader('Content-Type',({'.js':'application/javascript','.css':'text/css','.html':'text/html','.svg':'image/svg+xml','.webp':'image/webp','.png':'image/png'}[path.extname(f)]||'application/octet-stream'));res.end(fs.readFileSync(f));}catch{res.writeHead(404).end();}});
const guest={id:'mini-quota-qa',nickname:'QA Guest',email:'qa@example.invalid',is_admin:true};
(async()=>{
 await new Promise(r=>server.listen(0,'127.0.0.1',r));
 const fixture=await request.newContext({baseURL:'http://127.0.0.1:8137',extraHTTPHeaders:{Authorization:'Bearer local-admin-visits'}}),results=[];
 async function get(){return (await fixture.get('/studio-api/manage/patch-promotion')).json();}
 async function set(remaining){const p=await get();const r=await fixture.put('/studio-api/manage/patch-promotion',{data:{quota:10,remaining,version:p.version,enabled:true}});assert(r.ok());}
 try{
  for(const [engine,type,lang,width,height] of [['webkit',webkit,'zh',390,844],['chromium',chromium,'en',320,640]]){
   await set(10);const browser=await type.launch({headless:true}),ctx=await browser.newContext({viewport:{width,height}}),page=await ctx.newPage(),errors=[],calls=[];
   const key=[engine,lang,width].join('-'),base='http://127.0.0.1:'+server.address().port;
   page.setDefaultTimeout(12000);page.on('pageerror',e=>errors.push(e.message));
   await ctx.addInitScript(({lang,guest})=>{for(const [key,value] of [['pd_token','quota-qa-token'],['pd_user',JSON.stringify(guest)],['pd_studio_language',lang]])localStorage.setItem(key,JSON.stringify({type:'string',data:value}));},{lang,guest});
   await ctx.route('**/*',async route=>{
    const req=route.request(),url=new URL(req.url()),p=url.pathname;
    if(p.includes('/studio-api/')||p.includes('/api/v1/')){
     const headers={'Access-Control-Allow-Origin':'*','Access-Control-Allow-Headers':'*','Access-Control-Allow-Methods':'*'};
     if(req.method()==='OPTIONS')return route.fulfill({status:204,headers});
     if(p.endsWith('/auth/me'))return route.fulfill({json:{user:guest},headers});
     if(p.includes('/api/v1/'))return route.fulfill({json:{},headers});
     const r=await fixture.fetch(p+url.search,{method:req.method(),data:req.postDataBuffer()||undefined,headers:{'Content-Type':'application/json'}});
     if(p.endsWith('/patch-promotion'))calls.push({method:req.method(),body:req.postDataJSON(),status:r.status(),response:await r.json()});
     return route.fulfill({response:r,headers:{...r.headers(),...headers}});
    }
    if(req.url().startsWith(base)||req.url().startsWith('data:')||req.url().startsWith('blob:'))return route.continue();
    return route.abort();
   });
   try{
    await page.goto(base+'/h5/#/pages/studio/manage-patch-offer');
    const inputs=page.locator('.admin-input input'),save=page.locator('.admin-native-actions .admin-primary');
    await expect(inputs).toHaveCount(2);await expect(inputs.nth(0)).toHaveValue('10');await expect(inputs.nth(1)).toHaveValue('10');
    await inputs.nth(1).fill('6');await expect(inputs.nth(0)).toHaveValue('10');await expect(save).not.toHaveAttribute('disabled','true');await save.click();
    await expect(page.locator('.admin-name').first()).toHaveText(/6\/10/);assert.equal((await get()).quota,10);
    await page.reload();await expect(inputs.nth(1)).toHaveValue('6');
    await inputs.nth(1).fill('');await expect(save).toHaveAttribute('disabled','true');
    await inputs.nth(1).fill('3');await set(5);await expect(save).not.toHaveAttribute('disabled','true');await save.click();
    await expect(page.locator('.admin-error')).toBeVisible();await expect(inputs.nth(1)).toHaveValue('3');
    await page.locator('.admin-secondary').click();await expect(inputs.nth(1)).toHaveValue('5');
    await inputs.nth(1).fill('6');await expect(save).not.toHaveAttribute('disabled','true');await save.click();await expect(page.locator('.admin-name').first()).toHaveText(/6\/10/);
    assert.equal(await page.evaluate(()=>document.documentElement.scrollWidth>innerWidth+1),false);
    await page.screenshot({path:path.join(out,key+'.png')});assert.deepEqual(errors,[]);results.push({key,saveReload:true,conflictPreserved:true,invalidBlocked:true});
   }catch(e){await page.screenshot({path:path.join(out,key+'-failed.png')});fs.writeFileSync(path.join(out,key+'-failed.json'),JSON.stringify({calls,buttons:await page.locator('.admin-primary').evaluateAll(es=>es.map(e=>e.outerHTML))},null,2));throw e;}finally{await ctx.close();await browser.close();}
  }
  fs.writeFileSync(path.join(out,'results.json'),JSON.stringify(results,null,2));console.log(JSON.stringify({passed:results.length}));
 }finally{await fixture.dispose();server.close();}
})().catch(e=>{console.error(e);process.exitCode=1;server.close();});
