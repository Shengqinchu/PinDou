const fs=require('node:fs'),path=require('node:path'),vm=require('node:vm'),assert=require('node:assert/strict'),ts=require('typescript');
const file=path.join(__dirname,'../src/utils/pattern-tool.ts');
const code=ts.transpileModule(fs.readFileSync(file,'utf8'),{compilerOptions:{module:ts.ModuleKind.CommonJS,target:ts.ScriptTarget.ES2022}}).outputText;
let storage={},calls=[],replies=[];
const uni={
 getStorageSync:key=>storage[key]||'',setStorageSync:(key,value)=>{storage[key]=value;},removeStorageSync:key=>{delete storage[key];},
 request:options=>{calls.push({url:options.url,method:options.method,header:options.header,data:options.data});const next=replies.shift();if(!next)throw new Error('unexpected request '+options.url);next==='fail'?options.fail():options.success(next);},
};
const exportsObject={};vm.runInNewContext(code,{exports:exportsObject,uni,globalThis:{}});
const t=exportsObject,ok=body=>({statusCode:200,data:body});
const pattern={artwork_id:'a1',pattern:{bead_total:12,color_counts:{H7:2,G6:10},palette_used:[{code:'G6',hex:'#F3A014'},{code:'H7',hex:'#010101'}],image_url:'/static/patterns/p.png'}};
(async()=>{
 // Guest: fetch a signed device identity once, then reuse it.
 replies=[ok({device_token:'dev-1'}),ok(pattern)];
 const first=await t.makePattern('AAA',52,'jpg');
 assert.equal(calls[0].url,'https://pindoupuppy.com/api/v1/wallet/profile');
 assert.equal(calls[1].url,'https://pindoupuppy.com/api/v1/generate/script');assert.equal(calls[1].header['X-PinDou-Device'],'dev-1');assert.equal(calls[1].header.Authorization,undefined);
 assert.deepEqual({size:calls[1].data.size,filename:calls[1].data.filename,brand:calls[1].data.brand},{size:'52x52',filename:'photo.jpg',brand:'MARD'});
 assert.equal(first.imageUrl,'https://pindoupuppy.com/static/patterns/p.png');assert.equal(first.total,12);
 assert.equal(JSON.stringify(first.colors.map(c=>[c.code,c.hex,c.count])),JSON.stringify([['G6','#F3A014',10],['H7','#010101',2]]));
 calls=[];replies=[ok(pattern)];await t.makePattern('AAA',26,'png');assert.equal(calls.length,1);assert.equal(calls[0].data.filename,'photo.png');
 // Signed in: account token first; consent is recorded once and the request retried.
 storage.pd_token='acct';calls=[];replies=[{statusCode:403,data:{error:'CONSENT_REQUIRED'}},ok({}),ok(pattern)];
 await t.makePattern('AAA',52,'jpg');
 assert.deepEqual(calls.map(c=>c.url.split('/v1')[1]),['/generate/script','/user/consent','/generate/script']);
 assert.equal(calls[1].header.Authorization,'Bearer acct');assert.equal(calls[1].data.type,'sensitive');assert.equal(calls[2].header.Authorization,'Bearer acct');
 // Expired account token falls back to this device instead of blocking a free tool.
 calls=[];replies=[{statusCode:401,data:{error:'AUTH_REQUIRED'}},ok(pattern)];
 await t.makePattern('AAA',52,'jpg');assert.equal(calls[1].header['X-PinDou-Device'],'dev-1');assert.equal(calls[1].header.Authorization,undefined);
 // Errors map to user-facing copy keys.
 delete storage.pd_token;
 for(const [reply,codeKey] of [[{statusCode:429,data:{}},'pattern_error_busy'],[{statusCode:413,data:{}},'pattern_error_large'],[{statusCode:500,data:{error:'PATTERN_BUILD_FAILED'}},'pattern_error'],['fail','pattern_error_network']]){
  replies=[reply];await assert.rejects(t.makePattern('AAA',52,'jpg'),error=>error.code===codeKey);
 }
 // A rejected device identity is replaced once; a second rejection surfaces an error and clears it.
 calls=[];replies=[{statusCode:401,data:{}},ok({device_token:'dev-2'}),ok(pattern)];await t.makePattern('AAA',52,'jpg');
 assert.equal(calls[1].url.split('/v1')[1],'/wallet/profile');assert.equal(calls[2].header['X-PinDou-Device'],'dev-2');assert.equal(storage.pd_pattern_device,'dev-2');
 replies=[{statusCode:401,data:{}},ok({device_token:'dev-3'}),{statusCode:401,data:{}}];await assert.rejects(t.makePattern('AAA',52,'jpg'));assert.equal(storage.pd_pattern_device,undefined);
 assert.equal(replies.length,0);
 console.log('Pattern tool checks passed: guest device identity, account token, consent retry, expired-token fallback, error mapping, colour list and image URL.');
})().catch(error=>{console.error(error);process.exitCode=1;});
