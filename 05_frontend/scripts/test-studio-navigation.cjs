const assert=require('node:assert/strict'),fs=require('node:fs'),path=require('node:path'),vm=require('node:vm'),ts=require('typescript');
const cache={},calls=[];let pages=[{route:'pages/studio/home'}];
const action=type=>options=>calls.push({type,options});
function load(name){if(cache[name])return cache[name];const ex={};cache[name]=ex;const code=ts.transpileModule(fs.readFileSync(path.join(__dirname,'../src/utils/'+name+'.ts'),'utf8'),{compilerOptions:{module:ts.ModuleKind.CommonJS,target:ts.ScriptTarget.ES2022}}).outputText;vm.runInNewContext(code,{exports:ex,require:id=>load(id.replace('./','')),getCurrentPages:()=>pages,uni:{navigateTo:action('push'),navigateBack:action('back'),redirectTo:action('replace')}});return ex;}
const router=load('studio-workspace-router'),nav=load('studio-navigation'),selected=[];
router.registerWorkspace('pages/studio/home',command=>selected.push(command.tab));
for(let i=0;i<5;i++){nav.navigateStudio('/pages/studio/reservations');nav.navigateStudio('/pages/auth/studio-account');nav.navigateStudio('/pages/studio/home');}
assert.equal(calls.length,0,'warm customer tabs do not create or destroy native pages');assert.equal(selected.length,15);
function finish(){const {type,options}=calls.at(-1);if(type==='push')pages.push({route:options.url.slice(1).split('?')[0]});else if(type==='back')pages.splice(-options.delta);else pages[pages.length-1]={route:options.url.slice(1).split('?')[0]};options.complete();}
nav.navigateStudio('/pages/studio/manage');nav.navigateStudio('/pages/studio/home');finish();assert.equal(calls.at(-1).type,'back','last target wins during a native transition');finish();assert.equal(pages.length,1);
nav.navigateStudio('/pages/studio/manage-reservations?status=confirmed&date=2026-09-18');finish();let cmd=router.takeWorkspace('pages/studio/manage');assert.equal(cmd.tab,'reservations');assert.equal(cmd.query.status,'confirmed');assert.equal(cmd.query.date,'2026-09-18');
const admin=[];router.registerWorkspace('pages/studio/manage',command=>admin.push(command));const count=calls.length;
for(let i=0;i<5;i++){nav.navigateStudio('/pages/studio/manage');nav.navigateStudio('/pages/studio/manage-finance');nav.navigateStudio('/pages/studio/manage-messages');nav.navigateStudio('/pages/studio/manage-reservations');}
assert.equal(calls.length,count,'warm admin tabs reuse one workspace');assert.equal(admin.length,20);
nav.navigateStudio('/pages/studio/manage-reservations?status=all');assert.equal(admin.at(-1).query.status,'all','same-tab filter intent is delivered');
pages.push({route:'pages/studio/manage-member'});nav.navigateStudio('/pages/studio/manage-finance');assert.equal(calls.at(-1).options.delta,1);finish();assert.equal(router.takeWorkspace('pages/studio/manage').tab,'finance');
pages=[{route:'pages/auth/studio-account'}];nav.navigateStudio('/pages/auth/studio-account');assert.equal(calls.at(-1).type,'replace','old QR page replaces itself with the root');finish();assert.equal(router.takeWorkspace('pages/studio/home').tab,'account');
assert.equal(router.workspaceCommand('/pages/studio/home?_tab=__proto__').tab,'home');assert.equal(router.workspaceCommand('/pages/studio/manage?_tab=constructor').tab,'home');assert.equal(router.workspaceCommand('/pages/studio/manage-reservation?id=record'),undefined);
pages=Array.from({length:8},(_,i)=>({route:'detail/'+i}));nav.navigateStudio('/pages/studio/manage');assert.equal(calls.at(-1).type,'replace');finish();assert.equal(pages.length,8);
console.log('Workspace navigation passed: 35 warm tab switches without native page churn, details/back, deep links, same-tab filters, latest target, unknown tabs and bounded stack.');
