// Identical public catalogue/source files and link simulation for both builds.
// The baseline is the hash-verified previous release served on loopback :4185.
import {chromium,expect} from '@playwright/test';
import assert from 'node:assert/strict';
import fs from 'node:fs/promises';
const out=new URL('../../artifacts/image-delivery-20260914/',import.meta.url);
const browser=await chromium.launch(),results=[];
async function ready(page){
 await expect.poll(()=>page.locator('.shop-card-preview img').evaluateAll(images=>{
  const visible=images.filter(i=>{const r=i.getBoundingClientRect();return r.top<innerHeight&&r.bottom>0});
  return visible.length===8&&visible.every(i=>i.complete&&i.naturalWidth>0);
 }),{timeout:30000,intervals:[40]}).toBe(true);
}
try{
 for(const mode of ['baseline','optimized','prefetched'])for(let trial=1;trial<=3;trial++){
  const context=await browser.newContext({viewport:{width:1440,height:1000},deviceScaleFactor:1});
  await context.addInitScript(limited=>{
   localStorage.setItem('puppy-studio-locale','zh');localStorage.setItem('puppy-studio-motion','reduced');
   Object.defineProperty(navigator,'connection',{value:{saveData:limited,effectiveType:'4g'},configurable:true});
  },mode!=='prefetched');
  const page=await context.newPage(),base='http://127.0.0.1:'+(mode==='baseline'?4185:4186);
  await page.goto(base+'/shop');await ready(page);await page.waitForTimeout(800);
  const session=await context.newCDPSession(page);await session.send('Network.enable');
  await session.send('Network.emulateNetworkConditions',{offline:false,latency:150,downloadThroughput:1000000,uploadThroughput:1000000});
  let prepMs=0;
  if(mode!=='prefetched')await session.send('Network.clearBrowserCache');
  else{
   const start=Date.now();
   await page.locator('.shop-children button').filter({hasText:'B系列'}).hover();
   await page.waitForTimeout(2500);prepMs=Date.now()-start;
  }
  await page.evaluate(()=>performance.clearResourceTimings());
  const b=page.locator('.shop-children button').filter({hasText:'B系列'});
  const start=Date.now();await b.evaluate(button=>button.click());await ready(page);
  const milliseconds=Date.now()-start;
  const timing=await page.evaluate(()=>performance.getEntriesByType('resource').filter(r=>r.name.includes('/studio-api/media/')).map(r=>({url:r.name,type:r.initiatorType,bytes:r.encodedBodySize,transfer:r.transferSize,duration:r.duration})));
  const visible=await page.locator('.shop-card-preview img').evaluateAll(images=>images.filter(i=>{const r=i.getBoundingClientRect();return r.top<innerHeight&&r.bottom>0}).map(i=>i.currentSrc));
  assert.equal(visible.length,8);
  // Record exact source bytes separately: memory-cache responses transfer zero.
  let visibleBytes=0;
  for(const src of visible){const response=await context.request.get(src);visibleBytes+=(await response.body()).length;}
  const row={mode,trial,milliseconds,prepMs,visibleImages:visible.length,visibleBytes,completedRequests:timing.length,transferBytes:timing.reduce((s,r)=>s+r.transfer,0),resources:timing};
  results.push(row);console.log(JSON.stringify({...row,resources:undefined}));await context.close();
 }
}finally{await browser.close();}
const summary=Object.fromEntries(['baseline','optimized','prefetched'].map(mode=>{
 const rows=results.filter(r=>r.mode===mode),times=rows.map(r=>r.milliseconds).sort((a,b)=>a-b);
 return [mode,{medianMs:times[1],rangeMs:[times[0],times[2]],visibleBytes:rows[0].visibleBytes}];
}));
await fs.writeFile(new URL('benchmark.json',out),JSON.stringify({conditions:{downMbps:8,rttMs:150,viewport:'1440x1000',dpr:1,images:8,loopback:true,trialsPerMode:3},summary,results},null,2));
console.log(JSON.stringify(summary));
