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
const t=await cdp('Target.createTarget',{url:'about:blank'}),a=await cdp('Target.attachToTarget',{targetId:t.targetId,flatten:true}),se=a.sessionId;
await cdp('Page.enable',{},se);await cdp('Emulation.setDeviceMetricsOverride',{width:1536,height:1200,deviceScaleFactor:1,mobile:false},se);await cdp('Page.navigate',{url:'file://'+root+'/플레이.html?test=1'},se);await delay(900);
const exp=`(async()=>{await document.fonts.ready;const checks=[],ok=(x,m)=>{checks.push({name:m,pass:!!x});if(!x)throw Error(m)},click=s=>{const e=document.querySelector(s);if(!e)throw Error('missing '+s);e.dispatchEvent(new MouseEvent('click',{bubbles:true}));};const api=Communication12;api.reset();
const world=(obj,action)=>{click('[data-object="'+obj+'"]');click('[data-world-action="'+action+'"]');};
const say=spec=>{if(api.getState().pieces.length)click('#clear');const ps=JigsawCore.build(spec,api.models,api.scenarios[0].blueWords);for(const p of ps){click('[data-color="'+api.models[p.model].color+'"]');click('[data-model="'+p.model+'"]');click('[data-cell="'+p.x+','+p.y+'"]');click('[data-word="'+p.word+'"]');}ok(api.analyze().ok,'실제 모형/글자 UI 연결 '+JSON.stringify(spec));click('#speak');return api.getState().attempts.at(-1);};
ok(api.scenarios.length===1,'단일 사건');ok(!document.body.innerText.includes('원인실험'),'이전 3종 목록 제거');ok(document.querySelectorAll('[data-object]').length===8,'세계 8대상');click('[data-actor="clerk"]');ok(document.querySelector('#reaction').textContent.includes('아까'),'NPC 직접 클릭');
ok(say(['질문',['이전','책']]).ok,'기억 질문');world('cart','mark-top');ok(!say(['함',['표식','있다'],['풀다','빗장']]).ok,'윗면 표식 잘못된 지시 복구');world('cart','mark-side');world('handle','push');ok(say(['질문','표식']).ok,'옆면 식별 시험');ok(document.querySelector('#reaction').textContent.includes('표식이 없었'),'함 차이 증언');world('gauge','pin');ok(say(['질문','저울']).ok,'현재 하중 질문');ok(document.querySelector('#reaction').textContent.includes('창 밑'),'하중 이동');world('handle','pull');ok(say(['질문','저울']).ok,'왕복 하중 질문');ok(say(['함',['표식','있다'],['풀다','빗장']]).ok,'분기 관계 부탁');world('handle','push');world('cart','lid');world('cart','take');world('counter','deliver');ok(api.getState().world.complete,'UI 완주');ok(!document.querySelector('#finish').hidden,'완료 표시');
api.reset();click('[data-actor="clerk"]');world('cart','mark-side');world('handle','push');say(['질문','표식']);window.scrollTo(0,0);return checks;})()`;
const out=await cdp('Runtime.evaluate',{expression:exp,awaitPromise:true,returnByValue:true},se);fs.writeFileSync(root+'/화면검사.json',JSON.stringify(out,null,2));if(out.exceptionDetails)throw Error(JSON.stringify(out.exceptionDetails));const shot=await cdp('Page.captureScreenshot',{format:'png',captureBeyondViewport:true},se);fs.writeFileSync(root+'/브라우저검증.png',Buffer.from(shot.data,'base64'));console.log(JSON.stringify(out.result.value));
}catch(e){console.error(e);process.exitCode=1;}finally{chrome.kill();}})();
