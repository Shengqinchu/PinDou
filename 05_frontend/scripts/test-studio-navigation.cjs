const assert=require('node:assert/strict'),fs=require('node:fs'),path=require('node:path'),vm=require('node:vm'),ts=require('typescript');
const code=ts.transpileModule(fs.readFileSync(path.join(__dirname,'../src/utils/studio-navigation.ts'),'utf8'),{compilerOptions:{module:ts.ModuleKind.CommonJS,target:ts.ScriptTarget.ES2022}}).outputText;
let pages=[{route:'pages/studio/home'}];const calls=[],ex={};
const action=type=>options=>calls.push({type,options});
vm.runInNewContext(code,{exports:ex,getCurrentPages:()=>pages,uni:{navigateTo:action('push'),navigateBack:action('back'),redirectTo:action('replace')}});
function finish(){const {type,options}=calls.at(-1);if(type==='push')pages.push({route:options.url.slice(1)});else if(type==='back')pages.splice(-options.delta);else pages[pages.length-1]={route:options.url.slice(1)};options.complete();}
ex.navigateStudio('/pages/studio/home');assert.equal(calls.length,0);
ex.navigateStudio('/pages/studio/reservations');ex.navigateStudio('/pages/auth/studio-account');assert.equal(calls.length,1);finish();assert.equal(calls.length,2);finish();assert.equal(pages.at(-1).route,'pages/auth/studio-account');
ex.navigateStudio('/pages/studio/home');assert.equal(calls.at(-1).type,'back');assert.equal(calls.at(-1).options.delta,2);finish();assert.equal(pages.length,1);
ex.navigateStudio('/pages/studio/reservations');ex.navigateStudio('/pages/auth/studio-account');ex.navigateStudio('/pages/studio/home');finish();assert.equal(calls.at(-1).type,'back');finish();assert.equal(pages.at(-1).route,'pages/studio/home');
pages=Array.from({length:8},(_,i)=>({route:'detail/'+i}));ex.navigateStudio('/pages/auth/studio-account');assert.equal(calls.at(-1).type,'replace');finish();assert.equal(pages.length,8);
pages=[{route:'pages/studio/home'}];ex.navigateStudio('/pages/studio/reservations');const interrupted=calls.at(-1);ex.navigateStudio('/pages/auth/studio-account');ex.studioPageShown('pages/studio/home');
const count=calls.length;ex.navigateStudio('/pages/auth/studio-account');assert.equal(calls.length,count+1);interrupted.options.complete();ex.navigateStudio('/pages/studio/home');assert.equal(calls.length,count+1);finish();assert.equal(calls.at(-1).type,'back');finish();
console.log('Navigation checks passed: no-op current tab, keep existing pages, latest target, bounded stack, interrupted navigation recovery and stale callback protection.');
