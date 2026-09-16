// Exercise the gate against contaminated disposable release artifacts.
const fs=require('node:fs'),path=require('node:path'),os=require('node:os'),assert=require('node:assert/strict'),{spawnSync}=require('node:child_process');
const built=path.resolve(__dirname,'../dist/build/mp-weixin'),base=fs.realpathSync(os.tmpdir()),temp=fs.mkdtempSync(path.join(base,'pindou-studio-package-'));
assert(fs.realpathSync(temp).startsWith(base+path.sep+'pindou-studio-package-'));
const run=()=>spawnSync(process.execPath,[path.join(__dirname,'check-studio-package.cjs'),'--path='+temp],{encoding:'utf8'});
try{
 fs.cpSync(built,temp,{recursive:true});assert.equal(run().status,0);
 const manifest=path.join(temp,'app.json'),original=fs.readFileSync(manifest,'utf8'),app=JSON.parse(original);app.pages.push('pages/generate/choice');fs.writeFileSync(manifest,JSON.stringify(app));assert.notEqual(run().status,0,'Reject registered legacy route');fs.writeFileSync(manifest,original);
 const file=path.join(temp,'app.js'),script=fs.readFileSync(file,'utf8');fs.writeFileSync(file,script+'\nconst legacyApi="/preview/generate";');assert.notEqual(run().status,0,'Reject a generator API dependency');fs.writeFileSync(file,script);
 fs.writeFileSync(file,script+'\nconst retiredLabel="AI 精品生成";');assert.notEqual(run().status,0,'Reject legacy service copy');fs.writeFileSync(file,script);
 fs.writeFileSync(path.join(temp,'store/user.js'),'module.exports={}');assert.notEqual(run().status,0,'Reject a resurrected legacy account store');fs.unlinkSync(path.join(temp,'store/user.js'));
 assert.equal(run().status,0);console.log('Studio release gate passed: clean artifact accepted; legacy route, API, service copy and user store rejected.');
}finally{
 const resolved=fs.realpathSync(temp);assert(resolved.startsWith(base+path.sep+'pindou-studio-package-'));fs.rmSync(resolved,{recursive:true,force:true});
}
