// Execute the real login completion flow with disposable session/API stubs.
const fs=require('node:fs'),path=require('node:path'),vm=require('node:vm'),assert=require('node:assert/strict'),ts=require('typescript');
const source=fs.readFileSync(path.join(__dirname,'../src/pages/auth/studio-login.vue'),'utf8').match(/<script setup lang="ts">([\s\S]*?)<\/script>/)[1];
const code=ts.transpileModule(source+'\nexports.complete=complete;',{compilerOptions:{module:ts.ModuleKind.CommonJS,target:ts.ScriptTarget.ES2022,esModuleInterop:true}}).outputText;
async function run(previous){
 const user={token:'',userInfo:null},calls=[],exportsObject={};
 const modules={vue:{computed:fn=>({get value(){return fn();}}),ref:value=>({value})},'@dcloudio/uni-app':{onLoad(){},onUnload(){}},'../../store/studio-user':{useUserStore:()=>user},'../../utils/studio-native':{useStudioNative:()=>({language:{value:'zh'}})},'../../utils/customer-notifications':Object.fromEntries(['loadNotifications','saveNotifications','askWechatNotifications'].map(name=>[name,async()=>calls.push(name)]))};
 vm.runInNewContext(code,{exports:exportsObject,require:id=>modules[id]||{},getCurrentPages:()=>previous?[{route:previous},{route:'pages/auth/studio-login'}]:[{route:'pages/auth/studio-login'}],uni:{setStorageSync(){},navigateBack:o=>calls.push(['back',o.delta]),redirectTo:o=>calls.push(['redirect',o.url])}});
 await exportsObject.complete({token:'fixture',user:{nickname:'',email:''},shared_user:{nickname:'',email:''}},true);
 assert.equal(user.token,'fixture');assert.deepEqual(calls.slice(0,3),['loadNotifications','saveNotifications','askWechatNotifications']);
 assert.deepEqual(calls[3],previous?['back',1]:['redirect','/pages/studio/home']);
 assert.equal(calls.length,4,'No profile prerequisite, extra profile read, or onboarding redirect');
}
(async()=>{await run('');await run('pages/studio/visit');console.log('Optional profile checks passed: WeChat login proceeds with empty profile, notification consent retained, booking return preserved.');})().catch(e=>{console.error(e);process.exitCode=1;});
