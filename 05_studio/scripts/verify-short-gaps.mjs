import {createServer} from 'vite';
import {chromium,webkit} from '@playwright/test';
import fs from 'node:fs/promises';
import path from 'node:path';
import assert from 'node:assert/strict';
import {fileURLToPath} from 'node:url';
const root=fileURLToPath(new URL('..',import.meta.url)),out=path.resolve(root,'../artifacts/miniapp-smooth-20260915');
const fixture=JSON.parse(await fs.readFile(path.join(out,'gap-fixture.json'),'utf8'));
const html=`<html><head><meta name="viewport" content="width=device-width,initial-scale=1"></head><body><div id="app"></div><script type="module">
import {createApp,h,provide} from '/node_modules/.vite/deps/vue.js';
import Timetable from '/src/components/admin/ReservationTimetable.vue';import Calendar from '/src/components/ReservationCalendar.vue';import {deskKey} from '/src/admin.ts';
import '/src/style.css';import '/src/styles/reservations.css';import '/src/styles/desk.css';import '/src/styles/timetable.css';
const data=${JSON.stringify(fixture)};createApp({setup(){provide(deskKey,{request:async()=>data.host});return()=>h('div',{style:'padding:12px'},[h('div',{id:'qa-public'},[h(Calendar,{calendar:data.public,booking:{date:'',start:'',end:'',guests:1,plan:'hourly'}})]),h('div',{id:'qa-host'},[h(Timetable,{active:true,refreshKey:0,selectedDate:'',selectedTime:''})])]);}}).mount('#app');
</script></body></html>`;
const server=await createServer({root,configFile:path.join(root,'vite.config.ts'),server:{host:'127.0.0.1',port:0,open:false},plugins:[{name:'local-gap-fixture',configureServer(s){s.middlewares.use('/qa-gap',async(req,res)=>{res.setHeader('Content-Type','text/html');res.end(await s.transformIndexHtml('/qa-gap',html));});}}]});
const results=[];
try{await server.listen();const port=server.httpServer.address().port;
for(const [engine,type] of [['chromium',chromium],['webkit',webkit]]){const browser=await type.launch({headless:true});try{for(const width of [1440,390]){const page=await browser.newPage({viewport:{width,height:1000}}),errors=[];page.on('pageerror',e=>errors.push(e.message));await page.goto(`http://127.0.0.1:${port}/qa-gap`);const publicGap=page.locator('#qa-public button[data-date="2026-09-18"][data-time="12:00"]');await publicGap.waitFor();assert(await publicGap.isDisabled());assert.equal(await page.locator('#qa-public button[data-date="2026-09-19"][data-time="12:00"]').isEnabled(),true);const hostGap=page.locator('#qa-host button[data-date="2026-09-18"][data-time="12:00"]');await hostGap.waitFor();assert((await hostGap.getAttribute('class')).includes('closed'));await hostGap.scrollIntoViewIfNeeded();await page.screenshot({path:path.join(out,`short-gap-${engine}-${width}.png`)});assert.deepEqual(errors,[]);results.push({engine,width,publicGapDisabled:true,exactTwoHoursEnabled:true,hostGapClosed:true});await page.close();}}finally{await browser.close();}}
await fs.writeFile(path.join(out,'gap-ui-results.json'),JSON.stringify(results,null,2));console.log(JSON.stringify(results));
}finally{await server.close();}
