const fs = require('fs');
const net = require('net');
const {spawn} = require('child_process');
const path = require('path');
const root = path.resolve(__dirname,'..');
let cases = {};
const chrome = spawn('/home/cj3071/.cache/ms-playwright/chromium-1243/chrome-linux64/chrome',[
  '--headless=new','--no-sandbox','--disable-gpu','--no-first-run','--remote-debugging-pipe',
  '--allow-file-access-from-files','--user-data-dir=/tmp/grad-variants23-final-profile'
],{stdio:['ignore','ignore',fs.openSync('/tmp/grad-variants23-final-chrome.log','a'),'pipe','pipe'],env:{...process.env,LD_LIBRARY_PATH:'/tmp/grad-blind-20260930/libs/usr/lib/x86_64-linux-gnu'}});
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


(async()=>{const checks=[];try{
 const ok=(name,value)=>{checks.push({name,pass:!!value});if(!value)throw Error(name)};
 const t=await cdp('Target.createTarget',{url:'about:blank'}),a=await cdp('Target.attachToTarget',{targetId:t.targetId,flatten:true});const se=a.sessionId;
 await cdp('Page.enable',{},se);
 const nav=async file=>{await cdp('Page.navigate',{url:'file://'+root+'/'+file},se);await delay(500)};
 const viewport=async width=>cdp('Emulation.setDeviceMetricsOverride',{width,height:1100,deviceScaleFactor:1,mobile:false},se);
 const shot=async file=>{const s=await cdp('Page.captureScreenshot',{format:'png'},se);fs.writeFileSync(root+'/분석/'+file,Buffer.from(s.data,'base64'))};
 await viewport(1536);await nav('플레이와_비교결과.html');
 ok('six play cards',await evaluate(se,"document.querySelectorAll('.card a.play').length===6"));
 ok('play default',await evaluate(se,"!document.querySelector('#games').hidden&&document.querySelector('#analysis').hidden"));
 ok('desktop no overflow',await evaluate(se,'document.documentElement.scrollWidth<=innerWidth'));
 await shot('모음_화면.png');
 await evaluate(se,"document.querySelector('[data-tab=analysis]').click()");
 ok('analysis tab displays',await evaluate(se,"!document.querySelector('#analysis').hidden&&document.querySelector('#games').hidden"));
 ok('six sample and five baseline rows',await evaluate(se,"document.querySelectorAll('tbody tr').length===11"));
 ok('A3 evidence summary',await evaluate(se,"document.body.innerText.includes('25클릭')&&document.body.innerText.includes('16클릭')"));
 await shot('분석_화면.png');
 await evaluate(se,"location.hash='detail-A3'");await delay(200);
 ok('detail anchor opens',await evaluate(se,"document.querySelector('#detail-A3').open"));
 await viewport(900);await nav('플레이와_비교결과.html');
 ok('900px no overflow',await evaluate(se,'document.documentElement.scrollWidth<=innerWidth'));
 await viewport(400);await nav('플레이와_비교결과.html');
 ok('400px no overflow',await evaluate(se,'document.documentElement.scrollWidth<=innerWidth'));
 await viewport(1536);await nav('A/플레이.html?test=1#p1');
 ok('A final observation scope text',await evaluate(se,"document.body.innerText.includes('상류에서 떠내려온 책')"));
 await shot('A_최종문구.png');
 await cdp('Page.navigate',{url:'about:blank'},se);await delay(100);
 await nav('A/플레이.html?test=1#p2');
 ok('A final morning time text',await evaluate(se,"document.body.innerText.includes('아침에는 수리가')"));
 }catch(e){checks.push({name:String(e),pass:false});process.exitCode=1}finally{fs.writeFileSync(root+'/분석/화면검증.json',JSON.stringify({passed:checks.every(x=>x.pass),checks},null,2));console.log(JSON.stringify(checks));chrome.kill()}})();
