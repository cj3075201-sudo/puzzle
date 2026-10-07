const fs = require('fs');
const net = require('net');
const {spawn} = require('child_process');
const path = require('path');
const root = __dirname;
let cases = {};
const chrome = spawn('/home/cj3071/.cache/ms-playwright/chromium-1243/chrome-linux64/chrome',[
  '--headless=new','--no-sandbox','--disable-gpu','--no-first-run','--remote-debugging-pipe',
  '--allow-file-access-from-files','--user-data-dir=/tmp/grad-core24-b-profile'
],{stdio:['ignore','ignore',fs.openSync('/tmp/grad-core24-b-chrome.log','a'),'pipe','pipe'],env:{...process.env,LD_LIBRARY_PATH:'/tmp/grad-blind-20260930/libs/usr/lib/x86_64-linux-gnu'}});
let serial=0, buffer='';
const pending=new Map(), sessions=new Map();
chrome.stdio[4].on('data',chunk=>{
  buffer+=chunk.toString();
  let end;
  while((end=buffer.indexOf('\0'))>=0){
    const raw=buffer.slice(0,end);buffer=buffer.slice(end+1);
    if(!raw)continue;
    const message=JSON.parse(raw), handler=pending.get(message.id);
    if(handler){pending.delete(message.id);message.error?handler.reject(new Error(JSON.stringify(message.error))):handler.resolve(message.result||{});}
  }
});
function cdp(method,params={},sessionId){
  return new Promise((resolve,reject)=>{
    const id=++serial;
    pending.set(id,{resolve,reject});
    chrome.stdio[3].write(JSON.stringify({id,method,params,...(sessionId?{sessionId}:{})})+'\0');
    setTimeout(()=>{if(pending.has(id)){pending.delete(id);reject(new Error('Browser command timed out'));}},20000).unref();
  });
}
const delay=ms=>new Promise(resolve=>setTimeout(resolve,ms));
async function evaluate(session,expression){
  const r=await cdp('Runtime.evaluate',{expression,returnByValue:true},session);
  if(r.exceptionDetails)throw new Error('Visible UI observation failed');
  return r.result.value;
}

(async()=>{try{
const t=await cdp('Target.createTarget',{url:'about:blank'}),a=await cdp('Target.attachToTarget',{targetId:t.targetId,flatten:true}),se=a.sessionId;await cdp('Page.enable',{},se);await cdp('Emulation.setDeviceMetricsOverride',{width:1536,height:1200,deviceScaleFactor:1,mobile:false},se);await cdp('Page.navigate',{url:'file://'+path.dirname(root)+'/플레이.html?test=1'},se);await delay(800);await evaluate(se,'Communication12.reset()');
const checks=[];for(const [selector,want]of [['[data-actor="clerk"]','npc'],['[data-object="cart"]','cart']]){const rect=await evaluate(se,`(()=>{const r=document.querySelector(${JSON.stringify(selector)}).getBoundingClientRect();return{x:r.x+r.width/2,y:r.y+r.height/2};})()`);for(const type of ['mousePressed','mouseReleased'])await cdp('Input.dispatchMouseEvent',{type,...rect,button:'left',clickCount:1},se);const state=await evaluate(se,`({listener:Communication12.getState().listener,panel:document.querySelector('#object-panel h3').textContent})`);const pass=want==='npc'?state.listener==='clerk':state.panel==='바깥 작업 자리의 운반함';checks.push({selector,rect,state,pass});if(!pass)throw Error('Pointer check failed');}
const screenshot=await cdp('Page.captureScreenshot',{format:'png',captureBeyondViewport:true},se);fs.writeFileSync(root+'/시야칸막이_검증.png',Buffer.from(screenshot.data,'base64'));fs.writeFileSync(root+'/포인터검사.json',JSON.stringify({checks,semanticTest:'not repeated: visual-only, hashes unchanged'},null,2));console.log(JSON.stringify(checks));
}catch(e){console.error(e);process.exitCode=1;}finally{chrome.kill();}})();