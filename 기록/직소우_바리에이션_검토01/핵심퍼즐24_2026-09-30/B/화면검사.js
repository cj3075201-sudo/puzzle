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
ok(api.scenarios.length===1,'단일 사건');ok(!document.body.innerText.includes('원인실험'),'이전 목록 제거');ok(document.querySelectorAll('[data-object]').length===8,'세계 8대상');click('[data-actor="clerk"]');ok(document.querySelector('#reaction').textContent.includes('봉인'),'NPC 직접 클릭');
ok(say(['질문',['이전','책']]).ok,'적재 기억 질문');ok(api.getState().speech[0][1][0]==='책'&&api.getState().speech[2][1][0]==='약','기억 순서는 실제 직소 발화');ok(!document.querySelector('#reaction').textContent.includes('먼저'),'prose 해답번역 없음');
ok(say(['질문',['이전','함']]).ok,'이동 기억 질문');ok(JSON.stringify(api.getState().speech).includes('위'),'과거 위 방향 직소');
world('handle','push');ok(say(['질문','함']).ok,'무표식 관찰도 허용');ok(JSON.stringify(api.getState().speech).includes('바깥'),'무표식 이동 발화');world('cart','mark-top');world('handle','push');say(['질문','표식']);ok(JSON.stringify(api.getState().speech.at(-1)).includes('아니다'),'윗면 보이지 않음');world('cart','mark-side');world('handle','push');say(['질문','표식']);ok(JSON.stringify(api.getState().speech).includes('아래'),'현재 표식 이동 직소');
ok(say(['빗장','풀다']).ok,'빗장 부탁');world('handle','pull');world('cart','lid');ok(!document.querySelector('#object-panel').textContent.includes('기록이 들어'),'봉인 내용 누출 없음');ok(say(['책',['문','열다']]).ok,'책 수령문 선택');world('counter','send');ok(api.getState().world.delivered.includes('book'),'기록 배송 성공');ok(!api.getState().world.complete,'첫 물건으로 전체완료 아님');ok(say(['빗장','풀다']).ok,'두번째 이동 부탁');world('handle','pull');ok(say(['약',['문','열다']]).ok,'약 수령문 선택');world('counter','send');ok(api.getState().world.complete,'정상 UI 완주');ok(!document.querySelector('#finish').hidden,'완료 표시');
api.reset();click('[data-actor="clerk"]');say(['질문',['이전','책']]);window.scrollTo(0,0);return checks;})()`;
const out=await cdp('Runtime.evaluate',{expression:exp,awaitPromise:true,returnByValue:true},se);fs.writeFileSync(root+'/화면검사.json',JSON.stringify(out,null,2));if(out.exceptionDetails)throw Error(JSON.stringify(out.exceptionDetails));const shot=await cdp('Page.captureScreenshot',{format:'png',captureBeyondViewport:true},se);fs.writeFileSync(root+'/브라우저검증.png',Buffer.from(shot.data,'base64'));await evaluate(se,`(()=>{const click=s=>document.querySelector(s).dispatchEvent(new MouseEvent('click',{bubbles:true}));click('[data-object="cart"]');click('[data-world-action="mark-side"]');click('[data-object="handle"]');click('[data-world-action="push"]');click('#clear');const api=Communication12;for(const p of JigsawCore.build(['질문','표식'],api.models,api.scenarios[0].blueWords)){click('[data-color="'+api.models[p.model].color+'"]');click('[data-model="'+p.model+'"]');click('[data-cell="'+p.x+','+p.y+'"]');click('[data-word="'+p.word+'"]');}click('#speak');window.scrollTo(0,0);})()`);const shot2=await cdp('Page.captureScreenshot',{format:'png',captureBeyondViewport:true},se);fs.writeFileSync(root+'/현재관찰_검증.png',Buffer.from(shot2.data,'base64'));console.log(JSON.stringify({passed:out.result.value.length}));
}catch(e){console.error(e);process.exitCode=1;}finally{chrome.kill();}})();
