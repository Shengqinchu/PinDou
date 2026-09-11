// Native DevTools QA only. Mocked transport is restored before disconnecting.
const assert=require('node:assert/strict'),fs=require('node:fs/promises');
const automator=require('../artifacts/miniapp-login/qa/node_modules/miniprogram-automator');
const pause=ms=>new Promise(resolve=>setTimeout(resolve,ms));
(async()=>{
 const mp=await automator.connect({wsEndpoint:'ws://127.0.0.1:9458'});let mocked=false;
 const timer=setTimeout(()=>{mp.disconnect();process.exit(2);},40000);
 try{
  await mp.evaluate(function(){
   var api=require('api/index.js').index;
   wx.__ownerQa={api:api,oldLogin:api.login,oldRequest:api.request,oldSubscribe:api.requestSubscribeMessage,bound:false,calls:[],subscribed:0};
   api.login=function(o){o.success({code:'local-qa-only'});};
   api.request=function(o){
    var q=wx.__ownerQa,path=o.url.split('/studio-api')[1];
    if(path==='/auth/wechat/miniapp/session')return o.success({statusCode:200,data:{ticket:'local-qa-ticket',linked:true,expires_in:300},header:{}});
    if(!path||!path.startsWith('/owner-wechat/'))return q.oldRequest(o);
    q.calls.push({path:path,method:o.method,data:o.data});var data={};
    if(path==='/owner-wechat/status')data={bound:q.bound,enabled:true,template_id:'local-template',nonce:'local-nonce',binding:{label:'店主测试',authorization_available:false}};
    if(path==='/owner-wechat/binding'&&o.method==='GET')data={label:'店主测试',expires_at:Date.now()/1000+300};
    if(path==='/owner-wechat/binding'&&o.method==='POST')q.bound=true;
    if(path==='/owner-wechat/reservations')data={items:[{id:'VIS-LOCAL-QA',name:'本地测试顾客',status:'pending',booking:{date:'2026-09-13',start:'14:00',end:'16:00',guests:2}}]};
    o.success({statusCode:200,data:data,header:{}});
   };
   api.requestSubscribeMessage=function(o){wx.__ownerQa.subscribed++;o.success({'local-template':'accept'});};
  });mocked=true;
  const page=await mp.reLaunch('/pages/studio/owner?scene=local-binding-scene');await pause(500);
  let button=await page.$('.owner-permission .studio-native-primary');assert(button,'Binding confirmation button');
  await button.tap();await pause(300);
  assert(await mp.evaluate(function(){return wx.__ownerQa.bound;}));
  button=await page.$('.owner-permission .studio-native-primary');await button.tap();await pause(300);
  const result=await mp.evaluate(function(){var q=wx.__ownerQa;return {bound:q.bound,subscribeCalls:q.subscribed,accepted:q.calls.some(function(c){return c.path==='/owner-wechat/subscribe'&&c.data.result==='accept'&&c.data.nonce==='local-nonce';}),loadedBookings:q.calls.some(function(c){return c.path==='/owner-wechat/reservations';})};});
  assert.equal(result.subscribeCalls,1);assert(result.accepted&&result.loadedBookings);
  await mp.screenshot({path:'C:/Users/123/Desktop/PinDou/artifacts/messaging-integration/native-owner.png'});
  await fs.writeFile('C:/Users/123/Desktop/PinDou/artifacts/messaging-integration/native-owner-check.json',JSON.stringify({...result,realPermissionSheet:false,realPush:false},null,2));
  console.log(JSON.stringify(result));
 }finally{
  if(mocked)await mp.evaluate(function(){var q=wx.__ownerQa;q.api.login=q.oldLogin;q.api.request=q.oldRequest;q.api.requestSubscribeMessage=q.oldSubscribe;delete wx.__ownerQa;wx.reLaunch({url:'/pages/studio/home'});});
  clearTimeout(timer);mp.disconnect();
 }
})().catch(e=>{console.error(e.message);process.exit(1);});
