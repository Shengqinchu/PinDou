const assert=require('node:assert/strict'),fs=require('node:fs'),vm=require('node:vm'),path=require('node:path'),ts=require('typescript');
const code=ts.transpileModule(fs.readFileSync(path.join(__dirname,'../src/utils/studio-native.ts'),'utf8'),{compilerOptions:{module:ts.ModuleKind.CommonJS,target:ts.ScriptTarget.ES2022,esModuleInterop:true}}).outputText;
for(const modern of [true,false]){
 const hooks={show:[],hide:[],resize:[],unmount:[]},calls={window:0,system:0,listen:0,unlisten:0,title:0};let inherited,keyboard,language='zh';
 const info={windowHeight:800,windowWidth:390,screenHeight:844,safeArea:{bottom:810},language:'zh'};
 const vue={ref:value=>({value}),computed:fn=>({get value(){return fn();}}),inject:()=>inherited,provide:(_key,value)=>{inherited=value},watch:()=>{},onUnmounted:fn=>hooks.unmount.push(fn)};
 const uni={getStorageSync:()=>language,setStorageSync:(_key,value)=>language=value,getSystemInfoSync:()=>{calls.system++;return {...info}},setNavigationBarTitle:()=>calls.title++,onKeyboardHeightChange:fn=>{calls.listen++;keyboard=fn},offKeyboardHeightChange:()=>calls.unlisten++};
 if(modern)uni.getWindowInfo=()=>{calls.window++;return {...info}};
 const modules={'vue':vue,'@dcloudio/uni-app':{onShow:fn=>hooks.show.push(fn),onHide:fn=>hooks.hide.push(fn),onResize:fn=>hooks.resize.push(fn)},'../../../05_studio/src/content/miniapp.json':{brand:['店铺','Studio']},'../store/studio-user':{useUserStore:()=>({token:'fixture'})},'./studio-cache':{setStudioCacheOwner:()=>{}},'./studio-navigation':{studioPageShown:()=>{}}};
 const ex={};vm.runInNewContext(code,{exports:ex,require:id=>modules[id],uni,getCurrentPages:()=>[{route:'pages/studio/home'}],setTimeout,clearTimeout});
 const root=ex.useStudioNative();hooks.show.forEach(f=>f());ex.provideStudioNative(root);
 for(let i=0;i<7;i++)assert.equal(ex.useStudioNative(),root,'All retained views use one native window context');
 assert.equal(calls.window+calls.system,1);assert.equal(hooks.show.length,1);assert.equal(calls.listen,1);assert.equal(calls.title,1);
 keyboard({height:300});assert.equal(root.shellStyle.value['--studio-window-height'],'500px');assert.equal(root.shellStyle.value['--studio-safe-bottom'],'0px');
 hooks.hide.forEach(f=>f());assert.equal(calls.unlisten,1);assert.equal(root.keyboardOpen.value,false);
 hooks.show.forEach(f=>f());assert.equal(calls.listen,2);assert.equal(calls.title,1,'Do not repeat unchanged native title writes');
 info.windowHeight=340;info.windowWidth=844;info.screenHeight=390;info.safeArea={bottom:370};hooks.resize.forEach(f=>f({size:{windowHeight:340,windowWidth:844}}));
 assert.equal(root.width.value,844);assert.equal(root.shellStyle.value['--studio-safe-bottom'],'20px');assert.equal(root.shellStyle.value['--studio-window-height'],'340px');
 hooks.resize.forEach(f=>f({}));root.changeLanguage();assert.equal(root.language.value,'en');assert.equal(calls.title,2);hooks.unmount.forEach(f=>f());assert.equal(calls.unlisten,2);
}
console.log('Native shell checks passed: one window read, shared panes, keyboard listener lifecycle, insets, rotation, missing resize data, title deduplication and language.');
