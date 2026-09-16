// Run the actual isolated store with Pinia and disposable network/storage fixtures.
const fs=require('node:fs'),path=require('node:path'),vm=require('node:vm'),assert=require('node:assert/strict'),ts=require('typescript'),pinia=require('pinia');
const source=fs.readFileSync(path.join(__dirname,'../src/store/studio-user.ts'),'utf8');
const code=ts.transpileModule(source,{compilerOptions:{module:ts.ModuleKind.CommonJS,target:ts.ScriptTarget.ES2022}}).outputText;
class MiniappError extends Error{constructor(code,status){super(code);this.status=status;}}
function fixture(token='saved-token'){
 const saved=new Map([['pd_token',token],['pd_user',JSON.stringify({user_id:'customer-a',nickname:'Existing customer'})]]),calls=[],owners=[];let read;
 pinia.setActivePinia(pinia.createPinia());const exports={};
 const modules={pinia,'../utils/miniapp-client':{MiniappError},'../utils/studio-cache':{setStudioCacheOwner:t=>owners.push(t),readStudioCached:(...args)=>{calls.push(args);return read(...args);}}};
 vm.runInNewContext(code,{exports,require:id=>{assert(id in modules,'Unexpected dependency: '+id);return modules[id];},uni:{getStorageSync:key=>saved.get(key),setStorageSync:(key,value)=>saved.set(key,value),removeStorageSync:key=>saved.delete(key)}});
 return {user:exports.useUserStore(),saved,calls,owners,read:fn=>read=fn};
}
const deferred=()=>{let resolve,reject;const promise=new Promise((yes,no)=>{resolve=yes;reject=no;});return {promise,resolve,reject};};
(async()=>{
 const existing=fixture();assert.equal(existing.user.isLoggedIn,true);assert.equal(existing.user.userInfo.nickname,'Existing customer');
 existing.read(async()=>({user:{id:'customer-a',nickname:'Current customer',is_admin:true}}));await existing.user.fetchProfile();
 assert.deepEqual(existing.calls,[['/auth/me','saved-token',30000]]);assert.equal(existing.user.userInfo.user_id,'customer-a');assert.equal(existing.user.userInfo.is_admin,true);
 assert.equal(JSON.parse(existing.saved.get('pd_user')).nickname,'Current customer');
 existing.read(async()=>{throw new MiniappError('network',0);});await assert.rejects(existing.user.fetchProfile());assert.equal(existing.user.token,'saved-token','Transient network errors must preserve login');
 const gone=fixture();gone.read(async()=>{throw new MiniappError('expired',401);});await assert.rejects(gone.user.fetchProfile());assert.equal(gone.user.token,'');assert.equal(gone.user.userInfo,null);assert(!gone.saved.has('pd_token'));assert.equal(gone.owners.at(-1),'');
 const guest=fixture('');guest.read(()=>{throw Error('Guest must not fetch or auto-register');});assert.equal(await guest.user.fetchProfile(),null);assert.equal(guest.calls.length,0);
 for(const fail of [false,true]){
  const current=fixture(),pending=deferred();current.read(()=>pending.promise);const request=current.user.fetchProfile();
  current.user.token='new-token';current.user.userInfo={user_id:'customer-b',nickname:'New customer'};current.saved.set('pd_token','new-token');
  if(fail){pending.reject(new MiniappError('expired',401));await assert.rejects(request);}else{pending.resolve({user:{id:'customer-a',nickname:'Old customer'}});assert.equal(await request,null);}
  assert.equal(current.user.token,'new-token');assert.equal(current.user.userInfo.nickname,'New customer');assert.equal(current.saved.get('pd_token'),'new-token');
 }
 const loggedOut=fixture(),pending=deferred();loggedOut.read(()=>pending.promise);const request=loggedOut.user.fetchProfile();loggedOut.user.logout();pending.resolve({user:{id:'customer-a'}});assert.equal(await request,null);assert.equal(loggedOut.user.userInfo,null);assert(!loggedOut.saved.has('pd_user'));
 console.log('Studio account checks passed: existing login, Studio-only profile API, public browsing, transient failure, expiry, account switch and logout race.');
})().catch(error=>{console.error(error);process.exitCode=1;});
