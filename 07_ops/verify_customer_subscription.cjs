// Real frontend logic with disposable transport. No real accounts or messages.
const assert=require('node:assert/strict'),fs=require('node:fs'),path=require('node:path'),vm=require('node:vm');
const root=path.resolve(__dirname,'..'),ts=require('../05_frontend/node_modules/typescript'),vue=require('../05_frontend/node_modules/vue');
const tests=[];
function compile(file,stubs,extra={},native=true){
 let source=fs.readFileSync(path.join(root,file),'utf8');
 source=source.replace(new RegExp('// #'+(native?'ifndef':'ifdef')+' MP-WEIXIN[\\s\\S]*?// #endif','g'),'');
 const code=ts.transpileModule(source,{compilerOptions:{module:ts.ModuleKind.CommonJS,target:ts.ScriptTarget.ES2020,esModuleInterop:true}}).outputText;
 const module={exports:{}};
 vm.runInNewContext(code,{module,exports:module.exports,require:id=>{if(id in stubs)return stubs[id];if(id.endsWith('.json'))return {};throw Error('Unexpected import '+id);},console,setInterval,clearInterval,...extra});
 return module.exports;
}
const tick=()=>new Promise(resolve=>setImmediate(resolve));
async function test(name,fn){await fn();tests.push(name);}
function client({choices={},recordFailures=0,native=true,manual=false}={}){
 let clock=Date.now(),next=0,onPermission;
 const calls=[],requests=[],sessionWaits=[];
 class MiniappError extends Error{constructor(code,status=0){super(code);this.code=code;this.status=status;}}
 const base={MiniappError,miniSession:async()=>({ticket:'proof',expires_in:300}),studioCall:async(p,d,t,token)=>{
  calls.push({path:p,data:d,token});
  if(p.endsWith('/session'))return {nonce:'nonce-'+(++next),templates:['confirmed','cancelled','reminder'].map(kind=>({kind,template_id:kind+'-template',title:kind}))};
  if(p.endsWith('/subscribe')&&recordFailures-->0)throw Error('Transport interrupted');
  if(p==='/auth/notifications')return {email:'',phone:'',email_enabled:false,sms_enabled:false,version:1};
  return {ok:true};
 }};
 const uni={requestSubscribeMessage(options){requests.push(options);onPermission?.();if(!manual)options.success(Object.fromEntries(['confirmed','cancelled','reminder'].map(kind=>[kind+'-template',choices[kind]||'accept'])));}};
 const api=compile('05_frontend/src/utils/customer-notifications.ts',{'vue':vue,'./miniapp-client':base},{uni,Date:{now:()=>clock}},native);
 return {api,base,calls,requests,uni,advance:ms=>clock+=ms,onPermission:fn=>onPermission=fn};
}
function booking(h,native=true){
 const hooks={},posts=[],storage=new Map(),user={token:'account-a',logout(){this.token='';}};
 const uni={hideKeyboard(){},pageScrollTo(){},getStorageSync:key=>storage.get(key),setStorageSync:(key,value)=>storage.set(key,value),removeStorageSync:key=>storage.delete(key),navigateTo(){},redirectTo(value){posts.push({redirect:value.url});}};
 const cached=async p=>p.startsWith('/auth/')?{profile:{owner_id:'member-a',complete:true,name:'QA guest',contact_method:'wechat',contact:'qa-only',version:1},can_omit_details:false}:{max_guests_per_group:4};
 const api=compile('05_frontend/src/utils/use-studio-visit.ts',{
  vue,'@dcloudio/uni-app':{onLoad:fn=>hooks.load=fn,onShow:fn=>hooks.show=fn,onHide:fn=>hooks.hide=fn,onUnload:fn=>hooks.unload=fn},
  './customer-notifications':h.api,'../store/studio-user':{useUserStore:()=>user},
  './miniapp-client':{MiniappError:h.base.MiniappError,studioCall:async(p,data,t,token,method,headers)=>{posts.push({p,data,method,headers});return {id:'VIS-LOCAL-QA',status:'pending'};}},
  './studio-cache':{peekStudioSnapshot:()=>null,readStudioCached:cached,invalidateStudioSnapshots(){},rememberStudioSnapshot(){}},
  './studio-content':{refreshStudioContent:async()=>{}},
  './studio-booking':{emptyBooking:()=>({date:'2026-10-01',start:'12:00',end:'14:00',guests:1,plan:'hourly'}),emptyContact:()=>({name:'',contact_method:'wechat',contact:''}),validBooking:()=>true,validContact:()=>true,requestId:()=> 'local-idempotency-key',retryUnchanged:()=>false,calendarPath:b=>'/reservation-calendar?guests='+b.guests+'&experience=beads',experienceFor:()=> 'beads'},
 },{uni},native);
 const flow=api.useStudioVisit({value:'zh'});flow.step.value=2;
 return {flow,posts,hooks,user};
}
(async()=>{
 await test('preparation never opens a permission sheet',async()=>{const h=client();await h.api.warmWechat('account-a');assert(h.api.wechatPermissionReady('account-a'));assert.equal(h.requests.length,0);});
 await test('each fresh booking requests and records distinct real callbacks',async()=>{const h=client();await h.api.warmWechat('account-a');const a=h.api.subscribeWechat('account-a');assert.equal(h.requests.length,1);assert(await a);await tick();assert(await h.api.subscribeWechat('account-a'));assert.equal(h.requests.length,2);const recorded=h.calls.filter(c=>c.path.endsWith('/subscribe'));assert.notEqual(recorded[0].data.nonce,recorded[1].data.nonce);});
 await test('cancellation permission is not confirmation permission',async()=>{const h=client({choices:{confirmed:'reject',cancelled:'accept',reminder:'accept'}});await h.api.warmWechat('account-a');assert.equal(await h.api.subscribeWechat('account-a'),false);assert.equal(h.api.wechatReady.value,false);assert.equal(h.api.wechatChoices.cancelled,'accept');assert.equal(h.api.wechatChoices.confirmed,'reject');});
 await test('expired preparation clears misleading previous allowed state',async()=>{const h=client();await h.api.warmWechat('account-a');await h.api.subscribeWechat('account-a');await tick();h.advance(300000);assert.equal(await h.api.subscribeWechat('account-a'),false);assert.equal(h.requests.length,1);assert.equal(h.api.wechatReady.value,false);assert.equal(h.api.wechatChoices.confirmed,'unavailable');await h.api.warmWechat('account-a',true);assert.equal(h.requests.length,1);assert(await h.api.subscribeWechat('account-a'));});
 await test('all rejected choices are retained separately',async()=>{const h=client({choices:{confirmed:'reject',cancelled:'ban',reminder:'reject'}});await h.api.warmWechat('account-a');assert.equal(await h.api.subscribeWechat('account-a'),false);assert.equal(h.api.wechatChoices.cancelled,'ban');assert.equal(h.api.wechatChoices.reminder,'reject');});
 await test('interrupted acknowledgement retries the identical nonce once',async()=>{const h=client({recordFailures:1});await h.api.warmWechat('account-a');assert(await h.api.subscribeWechat('account-a'));const records=h.calls.filter(c=>c.path.endsWith('/subscribe'));assert.equal(records.length,2);assert.equal(JSON.stringify(records[0]),JSON.stringify(records[1]));});
 await test('failed acknowledgement never displays allowed',async()=>{const h=client({recordFailures:2});await h.api.warmWechat('account-a');await assert.rejects(h.api.subscribeWechat('account-a'));assert.equal(h.api.wechatReady.value,false);assert.equal(h.api.wechatChoices.confirmed,'unavailable');});
 await test('duplicate success callbacks cannot add multiple records',async()=>{const h=client({manual:true});await h.api.warmWechat('account-a');const pending=h.api.subscribeWechat('account-a');h.requests[0].success({'confirmed-template':'accept'});h.requests[0].success({'confirmed-template':'accept'});assert(await pending);assert.equal(h.calls.filter(c=>c.path.endsWith('/subscribe')).length,1);});
 await test('changing accounts while permission is open does not record for new user',async()=>{const h=client({manual:true});await h.api.warmWechat('account-a');const pending=h.api.subscribeWechat('account-a');await h.api.warmWechat('account-b');h.requests[0].success({'confirmed-template':'accept'});assert.equal(await pending,false);assert.equal(h.calls.filter(c=>c.path.endsWith('/subscribe')).length,0);assert.equal(h.api.wechatReady.value,false);});
 await test('switching away and back cannot revive an earlier callback',async()=>{const h=client({manual:true});await h.api.warmWechat('account-a');const pending=h.api.subscribeWechat('account-a');h.api.resetWechatChoices('account-b');h.api.resetWechatChoices('account-a');h.requests[0].success({'confirmed-template':'accept'});assert.equal(await pending,false);assert.equal(h.calls.filter(c=>c.path.endsWith('/subscribe')).length,0);});
 await test('receipt result is scoped to the booking and account',async()=>{const h=client();await h.api.warmWechat('account-a');await h.api.subscribeWechat('account-a');h.api.saveBookingWechatChoices('account-a','VIS-A');assert.equal(h.api.bookingWechatChoices('account-a','VIS-A').confirmed,'accept');assert.equal(h.api.bookingWechatChoices('account-b','VIS-A'),null);assert.equal(h.api.bookingWechatChoices('account-a','VIS-B'),null);h.api.resetWechatChoices('account-b');assert.equal(h.api.bookingWechatChoices('account-a','VIS-A'),null);});
 await test('confirmation prepares again after a long form and requests directly on tap',async()=>{const h=client(),b=booking(h);await h.api.warmWechat('account-a');h.advance(300000);const submission=b.flow.submit();await tick();assert(b.flow.confirmation.value);assert.equal(h.requests.length,0);const confirmation=b.flow.confirmSubmission();assert.equal(h.requests.length,1);await confirmation;await submission;assert.equal(b.posts.filter(p=>p.p==='/reservations').length,1);assert.equal(h.api.bookingWechatChoices('account-a','VIS-LOCAL-QA').confirmed,'accept');});
 await test('expiry while confirmation is open requires a new visible tap',async()=>{const h=client(),b=booking(h),submission=b.flow.submit();await tick();h.advance(300000);await b.flow.confirmSubmission();assert(b.flow.confirmation.value);assert.equal(b.flow.notificationNote.value,'wechat_confirm_again');assert.equal(h.requests.length,0);assert.equal(b.posts.length,0);await b.flow.confirmSubmission();await submission;assert.equal(h.requests.length,1);assert.equal(b.posts.filter(p=>p.p==='/reservations').length,1);});
 await test('rejecting notifications still submits and records the exact result',async()=>{const h=client({choices:{confirmed:'reject'}}),b=booking(h),submission=b.flow.submit();await tick();await b.flow.confirmSubmission();await submission;assert.equal(b.posts.filter(p=>p.p==='/reservations').length,1);assert.equal(h.api.bookingWechatChoices('account-a','VIS-LOCAL-QA').confirmed,'reject');});
 await test('permission sheet hide does not cancel an explicitly confirmed booking',async()=>{const h=client(),b=booking(h);h.onPermission(()=>b.hooks.hide());const submission=b.flow.submit();await tick();await b.flow.confirmSubmission();await submission;assert.equal(b.posts.filter(p=>p.p==='/reservations').length,1);});
 await test('cancelled review does not request or create a booking',async()=>{const h=client(),b=booking(h),submission=b.flow.submit();await tick();b.flow.dismissSubmission();await submission;assert.equal(h.requests.length,0);assert.equal(b.posts.length,0);});
 await test('explicit skip does not invent permission or block submission',async()=>{const h=client(),b=booking(h),submission=b.flow.submit();await tick();b.flow.confirmWithoutWechat();await submission;assert.equal(h.requests.length,0);assert.equal(b.posts.filter(p=>p.p==='/reservations').length,1);assert.equal(h.api.bookingWechatChoices('account-a','VIS-LOCAL-QA').confirmed,'unavailable');});
 await test('H5 booking submits without native permission APIs',async()=>{const h=client({native:false}),b=booking(h,false),submission=b.flow.submit();await tick();await b.flow.confirmSubmission();await submission;assert.equal(h.requests.length,0);assert.equal(b.posts.filter(p=>p.p==='/reservations').length,1);});
 fs.mkdirSync(path.join(root,'artifacts/customer-notifications-20260915'),{recursive:true});
 fs.writeFileSync(path.join(root,'artifacts/customer-notifications-20260915/logic-checks.json'),JSON.stringify({passed:tests.length,tests,realWeChat:false,realBookings:false},null,2));
 console.log(JSON.stringify({passed:tests.length,realWeChat:false,realBookings:false}));
})().catch(error=>{console.error(error);process.exitCode=1;});
