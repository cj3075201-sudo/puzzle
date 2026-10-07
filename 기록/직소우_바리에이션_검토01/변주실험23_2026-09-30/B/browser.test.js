const fs = require('fs');
const net = require('net');
const {spawn} = require('child_process');
const path = require('path');
const root = __dirname;
let cases = {};
const chrome = spawn('/home/cj3071/.cache/ms-playwright/chromium-1243/chrome-linux64/chrome',[
  '--headless=new','--no-sandbox','--disable-gpu','--no-first-run','--remote-debugging-pipe',
  '--allow-file-access-from-files','--user-data-dir=/tmp/grad-variants23-b-profile'
],{stdio:['ignore','ignore',fs.openSync('/tmp/grad-variants23-b-chrome.log','a'),'pipe','pipe'],env:{...process.env,LD_LIBRARY_PATH:'/tmp/grad-blind-20260930/libs/usr/lib/x86_64-linux-gnu'}});
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
 const t=await cdp('Target.createTarget',{url:'about:blank'}),a=await cdp('Target.attachToTarget',{targetId:t.targetId,flatten:true});const se=a.sessionId;
 await cdp('Page.enable',{},se);await cdp('Emulation.setDeviceMetricsOverride',{width:1536,height:1100,deviceScaleFactor:1,mobile:false},se);await cdp('Page.navigate',{url:'file://'+root+'/플레이.html?test=1'},se);await delay(900);
 const exp=`(async()=>{await document.fonts.ready;const checks=[],ok=(x,m)=>{checks.push({name:m,pass:!!x});if(!x)throw Error(m)},click=s=>{const e=document.querySelector(s);if(!e)throw Error('missing '+s);e.dispatchEvent(new MouseEvent('click',{bubbles:true}));}; const api=Communication12;
 ok(document.querySelectorAll('[data-puzzle]').length===3,'three cards');
 for(const sc of api.scenarios){api.open(sc.id);api.reset();for(const st of sc.solutions){if(api.getState().pieces.length)click('#clear');const ps=JigsawCore.build(st.spec,api.models,sc.blueWords);for(const p of ps){click('[data-color="'+api.models[p.model].color+'"]');click('[data-model="'+p.model+'"]');click('[data-cell="'+p.x+','+p.y+'"]');click('[data-word="'+p.word+'"]');}ok(api.analyze().ok,'parse '+sc.id);document.querySelector('[data-actor="'+st.listener+'"]').dispatchEvent(new MouseEvent('click',{bubbles:true}));click('#speak');ok(api.getState().attempts.at(-1).ok,'say '+sc.id);}ok(api.getState().world.complete,'complete '+sc.id);}
 api.open(2);api.reset();document.querySelector('[data-actor="traveler"]').dispatchEvent(new MouseEvent('click',{bubbles:true}));return checks;})()`;
 const out=await cdp('Runtime.evaluate',{expression:exp,awaitPromise:true,returnByValue:true},se);fs.writeFileSync(root+'/browser-results.json',JSON.stringify(out,null,2));if(out.exceptionDetails)throw Error(JSON.stringify(out.exceptionDetails));
 const shot=await cdp('Page.captureScreenshot',{format:'png'},se);fs.writeFileSync(root+'/브라우저검증.png',Buffer.from(shot.data,'base64'));console.log(JSON.stringify(out.result.value));
 }catch(e){console.error(e);process.exitCode=1;}finally{chrome.kill();}})();
