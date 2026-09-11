const fs=require('node:fs'),vm=require('node:vm'),assert=require('node:assert/strict'),ts=require('typescript');
const user={token:'owner-a'};
let now=100000;
const source=fs.readFileSync(require('node:path').join(__dirname,'../src/utils/studio-admin-cache.ts'),'utf8');
const exportsValue={};
vm.runInNewContext(ts.transpileModule(source,{compilerOptions:{module:ts.ModuleKind.CommonJS}}).outputText,{
 exports:exportsValue,require:()=>({useUserStore:()=>user}),Date:{now:()=>now},Map,JSON,
});
const {adminView,invalidateAdminViews,clearAdminViews}=exportsValue;
function fill(key,state){const view=adminView(key);view.loaded(view.begin());view.save(state);return view;}
const home=fill('home',{pending:2}),finance=fill('finance',{page:3,items:['cash']}),messages=fill('messages',{draft:'hello'});
assert.equal(adminView('finance').snapshot.page,3);
assert.equal(home.fresh(),true);
invalidateAdminViews('/manage/finance/one');
assert.equal(home.fresh(),false);assert.equal(finance.fresh(),false);assert.equal(messages.fresh(),true);
const revision=finance.begin();invalidateAdminViews('/manage/finance/two');finance.loaded(revision);
assert.equal(finance.fresh(),false,'An edit during a read must not bless a stale response');
messages.loaded(messages.begin());now+=30001;assert.equal(messages.fresh(),false);
messages.loaded(messages.begin());clearAdminViews();
assert.equal(messages.valid(),false);assert.equal(messages.fresh(),false);
messages.save({draft:'old'});assert.equal(adminView('messages').snapshot,undefined);
const ownerA=fill('home',{secret:'a'});user.token='owner-b';
assert.equal(adminView('home').snapshot,undefined);ownerA.save({secret:'a'});
assert.equal(adminView('home').snapshot,undefined);
console.log('Admin cache: warm reuse, selective invalidation, in-flight edit, TTL, authorization reset, and account isolation passed.');
