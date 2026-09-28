// Pure interval and native lifecycle tests; transport/storage are disposable.
const assert=require('node:assert/strict'),fs=require('fs'),path=require('path'),vm=require('vm'),ts=require('typescript'),vue=require('vue');
const root=path.resolve(__dirname,'../src'),tick=()=>new Promise(r=>setImmediate(r));
function compile(file,modules={},globals={}){
 const source=fs.readFileSync(path.join(root,file),'utf8').replace(/\/\/ #ifdef MP-WEIXIN[\s\S]*?\/\/ #endif/g,'');
 const code=ts.transpileModule(source,{compilerOptions:{module:ts.ModuleKind.CommonJS,target:ts.ScriptTarget.ES2022}}).outputText,ex={};
 vm.runInNewContext(code,{exports:ex,require:id=>{if(id==='vue')return vue;if(id in modules)return modules[id];throw Error('Unexpected import '+id);},setInterval:()=>1,clearInterval:()=>{},...globals});return ex;
}
const rules=compile('utils/studio-booking.ts');
function calendar(experience='patch'){
 const slots=Array.from({length:28},(_,i)=>({start:rules.clock(600+i*30),end:rules.clock(630+i*30),available:true,start_available:i<27,reason:null}));
 return {experience,today:'2026-10-01',timezone:'America/Toronto',minimum_minutes:experience==='patch'?60:120,max_guests_per_group:6,policy_version:8,days:[{date:'2026-10-01',open:'10:00',close:'24:00',closed:false,slots}]};
}
function booking(plan='patch'){return {date:'2026-10-01',start:'10:00',end:plan==='day'?'24:00':plan==='hourly'?'12:00':'11:00',plan,guests:2};}
function flowFixture({draft,pending,query={experience:'patch'}}={}){
 const hooks={},storage=new Map(),calls=[],waits=[];
 if(draft)storage.set('pd_studio_booking_draft:guest',{booking:draft,contact:{name:'Saved',contact_method:'wechat',contact:'saved'},step:2,editing:true,profileVersion:1});
 if(pending)storage.set('pd_studio_booking_attempt:guest',{owner:'guest',key:'same-key',body:{booking:pending,name:'Saved',contact_method:'wechat',contact:'saved',notes:'Keep me'}});
 const user={token:'fixture',logout(){this.token='';}};
 const profile={can_omit_details:false,profile:{owner_id:'guest',name:'Fixture',contact:'qa',contact_method:'wechat',complete:true,version:1}};
 const modules={
  '@dcloudio/uni-app':Object.fromEntries(['Load','Show','Hide','Unload'].map(n=>['on'+n,fn=>hooks[n]=fn])),
  './customer-notifications':{},'../store/studio-user':{useUserStore:()=>user},
  './miniapp-client':{MiniappError:class extends Error{},studioCall:()=>{throw Error('Unexpected write');}},
  './studio-cache':{peekStudioSnapshot:()=>null,readStudioCached:(p)=>{calls.push(p);return p.startsWith('/auth/')?Promise.resolve(profile):new Promise(resolve=>waits.push({p,resolve}));}},
  './studio-content':{refreshStudioContent:async()=>{}},'./studio-booking':rules,
 };
 const uni={getStorageSync:k=>storage.get(k),setStorageSync:(k,v)=>storage.set(k,JSON.parse(JSON.stringify(v))),pageScrollTo(){},removeStorageSync:k=>storage.delete(k)};
 const flow=compile('utils/use-studio-visit.ts',modules,{uni}).useStudioVisit({value:'zh'});
 hooks.Load(query);hooks.Show();
 return {flow,hooks,storage,calls,waits};
}
(async()=>{
 let c=calendar(),b=booking();
 assert(rules.validBooking(c,b));
 assert(!rules.validBooking(calendar('beads'),b),'Never validate patch against bead capacity');
 assert(!rules.validBooking(c,booking('hourly')));
 for(const end of ['10:30','11:30','12:00'])assert(!rules.validBooking(c,{...b,end}),'Patch must be exactly 60 minutes');
 assert(rules.validBooking(c,{...b,start:'23:00',end:'24:00'}),'Midnight endpoint is valid');
 assert(!rules.chooseCell(c,b,c.days[0],c.days[0].slots[27],false),'Last half hour cannot start a full patch visit');
 const single=rules.chooseCell(c,{...b,start:'',end:''},c.days[0],c.days[0].slots[2],true);
 assert.equal(single.booking.end,'12:00');assert.equal(single.choosingEnd,false);
 c.days[0].slots[1].available=false;assert(!rules.validBooking(c,b),'Every half hour must be free');
 c=calendar();c.days[0].slots[0].start_available=false;assert(!rules.validBooking(c,b),'Server start validity is authoritative');
 assert(rules.validBooking(calendar('beads'),booking('hourly')));
 assert(!rules.validBooking(calendar('beads'),{...booking('hourly'),end:'11:00'}));
 assert(rules.validBooking(calendar('beads'),booking('day')));
 assert(!rules.validBooking(calendar('beads'),{...booking('day'),end:'12:00'}));
 assert(!rules.validBooking(calendar(),{...b,guests:7}));
 assert.notEqual(rules.calendarPath(b),rules.calendarPath(booking('hourly')));
 const f=flowFixture({draft:booking('hourly')});await tick();
 assert.equal(f.flow.booking.plan,'patch');assert.equal(f.flow.step.value,0);assert.equal(f.flow.booking.start,'');assert.equal(f.flow.contact.name,'Saved');
 assert(f.waits[0].p.endsWith('experience=patch'));
 f.flow.choosePlan('hourly');await tick();assert(f.waits[1].p.endsWith('experience=beads'));
 f.waits[1].resolve(calendar('beads'));await tick();f.waits[0].resolve(calendar());await tick();
 assert.equal(f.flow.calendar.value.experience,'beads','Late patch response cannot replace bead calendar');
 f.hooks.Unload();
 const quick=flowFixture({draft:booking('day')});quick.flow.choosePlan('patch');quick.flow.select({...booking(),start:'13:00',end:'14:00'});await tick();
 assert.equal(quick.flow.booking.plan,'patch');assert.equal(quick.flow.booking.start,'13:00','A late account draft cannot overwrite this visit selection');
 for(const wait of quick.waits)wait.resolve(calendar());await tick();quick.hooks.Unload();
 const p=flowFixture({pending:booking('hourly')});await tick();
 assert.equal(p.flow.booking.plan,'hourly','Deep link must not mutate uncertain submission');
 p.flow.choosePlan('patch');assert.equal(p.flow.booking.plan,'hourly');assert.equal(p.flow.attempt.value.key,'same-key');
 p.waits[0].resolve(calendar('beads'));await tick();p.hooks.Unload();
 const hooks={},pending=[];
 const promo=compile('utils/studio-patch-promotion.ts',{'./miniapp-client':{studioRead:()=>new Promise((resolve,reject)=>pending.push({resolve,reject}))},'./studio-view-lifecycle':Object.fromEntries(['Show','Hide','Unload'].map(n=>['onView'+n,fn=>hooks[n]=fn]))}).usePatchPromotion(true);
 hooks.Show();pending[0].resolve({campaign:'qa',quota:10,remaining:1,enabled:true});await tick();assert(promo.open.value);
 promo.dismiss();await tick();const refresh=promo.refresh();pending[1].resolve({campaign:'qa',quota:10,remaining:0,enabled:true});await refresh;assert(!promo.open.value);assert.equal(promo.offer.value.remaining,0);
 const failed=promo.refresh();pending[2].reject(Error('offline'));await failed;assert.equal(promo.offer.value,null,'Remove stale promises when offline');
 const hidden=promo.refresh();hooks.Hide();pending[3].resolve({campaign:'new',quota:10,remaining:10,enabled:true});await hidden;assert(!promo.open.value);hooks.Unload();
 console.log('Patch checks passed: full-hour capacity, midnight, bead/day regression, deep link vs draft/idempotent attempt, request race, live promotion lifecycle.');
})().catch(e=>{console.error(e);process.exitCode=1;});
