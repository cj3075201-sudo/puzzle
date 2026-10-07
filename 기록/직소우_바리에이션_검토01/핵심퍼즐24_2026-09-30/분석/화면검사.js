const fs=require('fs'),path=require('path'),{spawn}=require('child_process');
const root=path.resolve(__dirname,'..'),profile='/tmp/grad-core24-qa-main';
const chrome=spawn('/home/cj3071/.cache/ms-playwright/chromium-1243/chrome-linux64/chrome',['--headless=new','--no-sandbox','--disable-gpu','--no-first-run','--remote-debugging-pipe','--allow-file-access-from-files','--user-data-dir='+profile],{stdio:['ignore','ignore','ignore','pipe','pipe'],env:{...process.env,LD_LIBRARY_PATH:'/tmp/grad-blind-20260930/libs/usr/lib/x86_64-linux-gnu'}});
let serial=0,buffer='',sid;const pending=new Map(),results=[];
chrome.stdio[4].on('data',b=>{buffer+=b;let k;while((k=buffer.indexOf('\0'))>=0){const raw=buffer.slice(0,k);buffer=buffer.slice(k+1);if(!raw)continue;const m=JSON.parse(raw),h=pending.get(m.id);if(h){pending.delete(m.id);m.error?h.reject(Error(JSON.stringify(m.error))):h.resolve(m.result||{});}}});
function cdp(method,params={},sessionId){return new Promise((resolve,reject)=>{const id=++serial;pending.set(id,{resolve,reject});chrome.stdio[3].write(JSON.stringify({id,method,params,...(sessionId?{sessionId}:{})})+'\0');setTimeout(()=>{if(pending.has(id)){pending.delete(id);reject(Error('CDP timeout'));}},15000).unref();});}
const delay=ms=>new Promise(r=>setTimeout(r,ms));
async function ev(expression){const r=await cdp('Runtime.evaluate',{expression,returnByValue:true},sid);if(r.exceptionDetails)throw Error(JSON.stringify(r.exceptionDetails));return r.result.value;}
function check(name,value){results.push({name,pass:!!value});if(!value)throw Error(name);}
async function click(selector){const r=await ev(`(()=>{const e=document.querySelector(${JSON.stringify(selector)});if(!e)throw Error('not found');e.scrollIntoView({block:'center'});const r=e.getBoundingClientRect();return{x:r.x+r.width/2,y:r.y+r.height/2};})()`);await cdp('Input.dispatchMouseEvent',{type:'mousePressed',button:'left',clickCount:1,...r},sid);await cdp('Input.dispatchMouseEvent',{type:'mouseReleased',button:'left',clickCount:1,...r},sid);await delay(90);}
async function shot(name){const r=await cdp('Page.captureScreenshot',{format:'png',captureBeyondViewport:false},sid);fs.writeFileSync(path.join(__dirname,name),Buffer.from(r.data,'base64'));}
async function navigate(file){await cdp('Page.navigate',{url:'file://'+file},sid);await delay(300);}
(async()=>{try{
const t=await cdp('Target.createTarget',{url:'about:blank'});sid=(await cdp('Target.attachToTarget',{targetId:t.targetId,flatten:true})).sessionId;await cdp('Page.enable',{},sid);await cdp('Emulation.setDeviceMetricsOverride',{width:1536,height:1200,deviceScaleFactor:1,mobile:false},sid);
await navigate(path.join(root,'플레이와_검토.html'));
check('two playable cards',await ev('document.querySelectorAll(".card .play").length===2'));
check('review hidden at entry',await ev('document.querySelector("#review-panel").hidden'));
check('desktop overview fits',await ev('document.documentElement.scrollWidth<=innerWidth'));
await shot('플레이_입구.png');await click('#review-tab');check('review tab shows only review',await ev('!document.querySelector("#review-panel").hidden&&document.querySelector("#play-panel").hidden'));
check('solutions collapsed by default',await ev('[...document.querySelectorAll("#review-panel details")].every(d=>!d.open)'));
await shot('비교_화면.png');await click('#play-tab');
for(const width of [900,400]){await cdp('Emulation.setDeviceMetricsOverride',{width,height:1000,deviceScaleFactor:1,mobile:false},sid);check('overview '+width+' fits',await ev('document.documentElement.scrollWidth<=innerWidth'));}
for(const letter of ['A','B']){
 await cdp('Emulation.setDeviceMetricsOverride',{width:1536,height:1200,deviceScaleFactor:1,mobile:false},sid);await navigate(path.join(root,letter,'플레이.html')+'?test=1#p1');
 check(letter+' script and world loaded',await ev('!!document.querySelector("#scene")&&document.querySelector("#scene").children.length>3'));
 check(letter+' one interlocutor',await ev('typeof Communication12!=="undefined"&&Communication12.scenarios.length===1&&Communication12.scenarios[0].actors.length===1'));
 check(letter+' separate save key',await ev('document.documentElement.outerHTML.includes("grad.core24.'+letter+'.v")'));
 check(letter+' desktop fits',await ev('document.documentElement.scrollWidth<=innerWidth'));
 await shot(letter+'_처음_화면.png');
 await cdp('Emulation.setDeviceMetricsOverride',{width:900,height:1000,deviceScaleFactor:1,mobile:false},sid);check(letter+' 900px fits',await ev('document.documentElement.scrollWidth<=innerWidth'));
}
fs.writeFileSync(path.join(__dirname,'화면검사.json'),JSON.stringify({at:new Date().toISOString(),checks:results},null,2));console.log(JSON.stringify(results,null,2));
}finally{chrome.kill();}})().catch(e=>{fs.writeFileSync(path.join(__dirname,'화면검사.json'),JSON.stringify({at:new Date().toISOString(),checks:results,error:String(e)},null,2));console.error(String(e));process.exitCode=1;});
