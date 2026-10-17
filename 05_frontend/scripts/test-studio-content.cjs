const fs=require('node:fs'),path=require('node:path'),vm=require('node:vm'),assert=require('node:assert/strict'),ts=require('typescript');
const file=path.join(__dirname,'../src/utils/studio-content.ts'),exportsObject={};let response={modules:{}},now=100000;
const code=ts.transpileModule(fs.readFileSync(file,'utf8'),{compilerOptions:{module:ts.ModuleKind.CommonJS,target:ts.ScriptTarget.ES2022,esModuleInterop:true}}).outputText;
vm.runInNewContext(code,{exports:exportsObject,Date:{now:()=>now},require:id=>id==='vue'?{shallowRef:value=>({value})}:id==='./miniapp-client'?{studioRead:async()=>response}:id==='./public-store'?{readPublic:()=>undefined,writePublic:()=>{}}:require(path.resolve(path.dirname(file),id))});
const c=exportsObject;
(async()=>{
 const original=c.studioMedia('process-pattern');assert(original.src.endsWith('/studio-media/v4/process-pattern.webp'));assert.equal(original.width,1400);
 response={modules:{'pages-Details':{studio_address_171634:['店主最新标题','Current title']},'components-BeadingProcess':{patternAlt:['店主图注','Current caption']},'contact-fields':{address:['新地址','New address']},media:{'process-pattern':{src:'/studio-api/media/new-photo.webp',width:800,height:600}}}};
 await c.refreshStudioContent();assert.equal(c.studioWords('details','studio_address_171634')[0],'店主最新标题');assert.equal(c.studioWords('process','patternAlt')[1],'Current caption');assert.equal(c.studioWords('contacts','address')[1],'New address');
 assert.equal(c.studioWords('process','title')[0],'拼豆流程','Partial published modules preserve approved defaults');const replaced=c.studioMedia('process-pattern');assert.equal(replaced.src,'https://pindoupuppy.com/studio-api/media/new-photo.webp');assert.equal(replaced.height/replaced.width,.75);
 now+=60001;response={modules:{media:{'process-pattern':{src:'//invalid.example/image.jpg',width:1,height:99}},'pages-Details':{studio_address_171634:['bad-shape']}}};await c.refreshStudioContent();assert.equal(c.studioMedia('process-pattern').src,original.src);assert.equal(c.studioMedia('process-pattern').width,1400);assert.equal(c.studioWords('details','studio_address_171634')[0],'拼豆铺详细地址');
 console.log('Published detail content passed: partial defaults, bilingual live text/contact overrides, original photo replacement and ratio, invalid asset fallback.');
})().catch(e=>{console.error(e);process.exitCode=1;});
