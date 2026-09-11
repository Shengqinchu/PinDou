const assert=require('node:assert/strict'),fs=require('node:fs'),vm=require('node:vm'),path=require('node:path'),ts=require('typescript');
const filename=path.join(__dirname,'../src/utils/studio-cache.ts');
const code=ts.transpileModule(fs.readFileSync(filename,'utf8'),{compilerOptions:{module:ts.ModuleKind.CommonJS,target:ts.ScriptTarget.ES2022}}).outputText;
let now=1000;const calls=[],exportsObject={};
class MiniappError extends Error{constructor(code,status){super(code);this.code=code;this.status=status;}}
vm.runInNewContext(code,{exports:exportsObject,Date:{now:()=>now},require:name=>{assert.equal(name,'./miniapp-client');return {MiniappError,studioRead:(route,token)=>new Promise((resolve,reject)=>calls.push({route,token,resolve,reject}))};}});
const c=exportsObject,flush=()=>new Promise(resolve=>setImmediate(resolve));
(async()=>{
 c.setStudioCacheOwner('owner-a');
 const first=c.readStudioCached('/auth/wallet','owner-a'),second=c.readStudioCached('/auth/wallet','owner-a');
 assert.equal(calls.length,1);calls[0].resolve({points:166});assert.equal((await first).points,166);await second;
 const snapshot=c.peekStudioSnapshot('/auth/wallet','owner-a');snapshot.data.points=0;assert.equal(c.peekStudioSnapshot('/auth/wallet','owner-a').data.points,166);
 await c.readStudioCached('/auth/wallet','owner-a');assert.equal(calls.length,1);
 const forced=c.readStudioCached('/auth/wallet','owner-a',15000,true);assert.equal(calls.length,2);calls[1].resolve({points:200});assert.equal((await forced).points,200);
 now+=15001;const expired=c.readStudioCached('/auth/wallet','owner-a');assert.equal(calls.length,3);calls[2].resolve({points:201});await expired;
 const old=c.readStudioCached('/auth/me','owner-a');const rejected=assert.rejects(old,e=>e.status===401);c.setStudioCacheOwner('owner-b');calls[3].resolve({id:'owner-a'});await rejected;
 assert.equal(c.peekStudioSnapshot('/auth/wallet','owner-b'),undefined);assert.equal(c.peekStudioSnapshot('/auth/wallet','owner-a'),undefined);
 const stale=c.readStudioCached('/auth/reservations?page=1','owner-b');c.invalidateStudioSnapshots('owner-b');calls[4].resolve({items:[{status:'pending'}]});await flush();
 assert.equal(calls.length,6);calls[5].resolve({items:[{status:'cancelled'}]});assert.equal((await stale).items[0].status,'cancelled');
 c.rememberStudioSnapshot('/reservations/VIS-test','owner-b',{status:'cancelled'});assert.equal(c.peekStudioSnapshot('/reservations/VIS-test','owner-b').data.status,'cancelled');
 now+=300001;assert.equal(c.peekStudioSnapshot('/reservations/VIS-test','owner-b'),undefined);
 for(let i=0;i<40;i++)c.rememberStudioSnapshot('/public/'+i,'',{value:i});assert.equal(c.peekStudioSnapshot('/public/0',''),undefined);assert.equal(c.peekStudioSnapshot('/public/39','').data.value,39);
 c.setStudioCacheOwner('');assert.equal(c.peekStudioSnapshot('/auth/reservations?page=1',''),undefined);
 console.log('Cache checks passed: deduplication, fresh/forced/expired reads, copy isolation, account switch, in-flight invalidation, mutation seed, bounded storage and logout.');
})().catch(e=>{console.error(e);process.exit(1)});
