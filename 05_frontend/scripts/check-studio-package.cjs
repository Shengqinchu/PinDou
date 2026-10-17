const fs=require('node:fs'),path=require('node:path'),assert=require('node:assert/strict');
const project=path.resolve(__dirname,'..'),output=path.resolve(process.argv.find(arg=>arg.startsWith('--path='))?.slice(7)||path.join(project,'dist/build/mp-weixin'));
const allowedPage=p=>/^pages\/studio\/[a-z-]+$/.test(p)||/^pages\/auth\/studio-[a-z-]+$/.test(p)||p==='pages/consent/consent'||/^pages\/(tools|shop)\/[a-z-]+$/.test(p);
const read=file=>fs.readFileSync(file,'utf8'),app=JSON.parse(read(path.join(output,'app.json')));
assert.equal(app.pages[0],'pages/studio/home');assert(app.pages.every(allowedPage),'Only studio routes belong in the mini program');assert(!app.tabBar,'Legacy generator tabBar must not ship');assert(!app.subPackages?.length,'Review any new subpackage before shipping it');
if(process.argv.includes('--prepare')){
 // uni-app copies the full static directory. Remove only generated legacy assets,
 // after resolving each target beneath this build directory. Source files stay intact.
 const generated=path.resolve(project,'dist/build/mp-weixin');assert.equal(output,generated);
 const realOutput=fs.realpathSync(output);
 for(const relative of ['static/assets','static/tabbar','static/styles/components.css','static/styles/colors_and_type.css']){
  const target=path.resolve(output,relative);if(!fs.existsSync(target))continue;
  const realTarget=fs.realpathSync(target);assert(realTarget.startsWith(realOutput+path.sep),'Refuse to remove outside the generated package');
  fs.rmSync(target,{recursive:true,force:true});
 }
}
const walk=dir=>fs.readdirSync(dir,{withFileTypes:true}).flatMap(item=>item.isDirectory()?walk(path.join(dir,item.name)):[path.join(dir,item.name)]);
const files=walk(output),forbidden=['AI 精品生成','AI 重绘','AI 智能生成','拼豆图纸生成器','生成英文','/preview/generate','/pattern/build','generateAIPreview','generatePreview(','CDK 兑换','choice-ai-target','pages/generate/','pages/upload/','pages/preview/','pages/result/','pages/cdk/','pages/artwork/','pages/user/','pages/index/','/generate/ai','/generate/status','/payment/','/cdk/redeem','AI 生成','AI 积分'];
for(const file of files){
 const relative=path.relative(output,file).replaceAll('\\','/');assert(!/^static\/(assets|tabbar)\//.test(relative),'Legacy visual assets must not ship');
 if(relative.startsWith('pages/')&&relative.endsWith('.json'))assert(allowedPage(relative.slice(0,-5)),'Unregistered legacy page left in package');
 if(/\.(?:js|json|wxml|wxss)$/.test(file)&&!relative.includes('project.')){
  const content=read(file);for(const needle of forbidden)assert(!content.includes(needle),`Legacy generator content in ${relative}: ${needle}`);
 }
}
assert(!files.some(f=>path.relative(output,f).replaceAll('\\','/').startsWith('store/user.')),'Legacy user store would pull generator APIs back in');
assert(files.some(f=>f.endsWith(path.join('store','studio-user.js'))),'Dedicated studio account store missing');
const summary={pages:app.pages.length,files:files.length,bytes:files.reduce((n,f)=>n+fs.statSync(f).size,0),legacy_routes:0,legacy_assets:0,generation_api_markers:0};
console.log(JSON.stringify(summary));
