const fs = require('fs');
const net = require('net');
const {spawn} = require('child_process');
const path = require('path');
const root = __dirname;
const results={checks:[],views:[]};
const chrome = spawn('/home/cj3071/.cache/ms-playwright/chromium-1243/chrome-linux64/chrome',[
  '--headless=new','--no-sandbox','--disable-gpu','--no-first-run','--remote-debugging-pipe',
  '--allow-file-access-from-files','--user-data-dir=/tmp/grad-combinations24-ui-profile'
],{stdio:['ignore','ignore',fs.openSync('/tmp/grad-combinations24-ui-chrome.log','a'),'pipe','pipe'],env:{...process.env,LD_LIBRARY_PATH:'/tmp/grad-blind-20260930/libs/usr/lib/x86_64-linux-gnu'}});
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
 const target=await cdp('Target.createTarget',{url:'about:blank'});const attach=await cdp('Target.attachToTarget',{targetId:target.targetId,flatten:true});const se=attach.sessionId;
 await cdp('Page.enable',{},se);await cdp('Emulation.setDeviceMetricsOverride',{width:1536,height:1200,deviceScaleFactor:1,mobile:false},se);
 await cdp('Page.navigate',{url:'file://'+root+'/플레이.html?test=1'},se);await delay(800);
 const initial=await evaluate(se,`({cards:document.querySelectorAll('[data-puzzle]').length,loaded:typeof Combinations24!=='undefined',font:document.fonts.check('15px P'),scrollWidth:document.documentElement.scrollWidth,width:innerWidth})`);results.checks.push({name:'six cards + API + font',pass:initial.cards===6&&initial.loaded&&initial.font,detail:initial});
 for(const width of [1536,900]){
  await cdp('Emulation.setDeviceMetricsOverride',{width,height:1200,deviceScaleFactor:1,mobile:false},se);
  for(let id=1;id<=6;id++){
   await evaluate(se,`Combinations24.open(${id});Combinations24.reset();`);
   const view=await evaluate(se,`(()=>{const r=e=>{const b=e.getBoundingClientRect();return{x:b.x,y:b.y,width:b.width,height:b.height,right:b.right,bottom:b.bottom}},sc=Combinations24.scenarios.find(x=>x.id===${id});return{id:${id},width:${width},docWidth:document.documentElement.scrollWidth,actors:document.querySelectorAll('[data-actor]').length,objects:document.querySelectorAll('[data-object]').length,board:r(document.querySelector('#board')),models:r(document.querySelector('#models')),words:r(document.querySelector('#words')),speaker:document.querySelector('#speaker').innerText,rule:document.querySelector('#new-rule').innerText}})()`);
   results.views.push(view);results.checks.push({name:'viewport '+width+' level '+id,pass:view.docWidth<=width&&view.actors===1&&view.board.width>=300&&view.models.width>150});
   if(id===1){await evaluate(se,`document.querySelector('[data-actor]').dispatchEvent(new MouseEvent('click',{bubbles:true}));window.scrollTo(0,0);`);await delay(70);const shot=await cdp('Page.captureScreenshot',{format:'png'},se);fs.writeFileSync(root+'/ui-'+width+'.png',Buffer.from(shot.data,'base64'));}
  }
 }
 const functional=await cdp('Runtime.evaluate',{awaitPromise:true,returnByValue:true,expression:`(async()=>{const checks=[],ok=(pass,name)=>checks.push({name,pass:!!pass}),api=Combinations24,click=s=>document.querySelector(s).dispatchEvent(new MouseEvent('click',{bubbles:true}));api.open(1);api.reset();click('[data-color="yellow"]');const m=document.querySelector('[data-model]').dataset.model;click('[data-model="'+m+'"]');click('[data-cell="0,0"]');ok(api.getState().pieces.length===1,'click model to cell');const word=api.scenarios[0].words.find(x=>!api.scenarios[0].blueWords.includes(x));click('[data-word="'+word+'"]');ok(api.getState().pieces[0].word===word,'assign letter');click('[data-cell="1,0"]');ok(api.getState().pieces[0].x===1,'selected piece move');click('#undo');ok(api.getState().pieces[0].x===0,'undo move');click('#clear');ok(!api.getState().pieces.length,'clear');click('#undo');ok(api.getState().pieces.length===1,'undo clear');click('#remove');ok(api.getState().pieces.length===1,'remove requires selected piece');document.querySelector('[data-piece]').dispatchEvent(new KeyboardEvent('keydown',{key:'Enter',bubbles:true}));click('#remove');ok(!api.getState().pieces.length,'delete selected');click('#hint-button');click('#hint-button');click('#hint-button');ok(!document.querySelector('#hint').innerText.includes('대표 풀이'),'only safe hints');click('[data-color="yellow"]');click('[data-model="'+m+'"]');click('[data-cell="0,0"]');click('[data-word="'+word+'"]');api.home();api.open(1);ok(api.getState().pieces.length===1&&api.getState().pieces[0].word===word,'saved piece and letter state');api.open(2);ok(api.getState().attempts.length===0,'independent level state');await document.fonts.ready;return checks;})()`},se);
 if(functional.exceptionDetails)throw Error(JSON.stringify(functional.exceptionDetails));results.checks.push(...functional.result.value);
 await cdp('Page.navigate',{url:'file://'+root+'/플레이.html'},se);await delay(700);results.checks.push({name:'QA API absent in public',pass:await evaluate(se,`typeof Combinations24==='undefined'&&typeof Communication12==='undefined'`)});
 fs.writeFileSync(root+'/ui-qa-results.json',JSON.stringify(results,null,2));console.log(JSON.stringify({checks:results.checks.length,failed:results.checks.filter(x=>!x.pass)}));if(results.checks.some(x=>!x.pass))process.exitCode=1;
 }catch(e){fs.writeFileSync(root+'/ui-qa-results.json',JSON.stringify({...results,error:String(e)},null,2));console.error(e);process.exitCode=1;}finally{chrome.kill();}})();
