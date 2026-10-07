const fs = require('fs');
const net = require('net');
const {spawn} = require('child_process');
const path = require('path');
const root = __dirname;
let cases = {};
const chrome = spawn('/home/cj3071/.cache/ms-playwright/chromium-1243/chrome-linux64/chrome',[
  '--headless=new','--no-sandbox','--disable-gpu','--no-first-run','--remote-debugging-pipe',
  '--allow-file-access-from-files',`--user-data-dir=${root}/profile`
],{stdio:['ignore','ignore',fs.openSync(`${root}/chrome.log`,'a'),'pipe','pipe'],env:{...process.env,LD_LIBRARY_PATH:'/tmp/grad-blind-20260930/libs/usr/lib/x86_64-linux-gnu'}});
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
async function observe(agent,s){
  const data=await evaluate(s.session,`(() => {
    const visible=e=>{const r=e.getBoundingClientRect(),c=getComputedStyle(e);return r.width>0&&r.height>0&&c.display!=='none'&&c.visibility!=='hidden'&&Number(c.opacity)!==0;};
    const candidates=[...document.querySelectorAll('body *')].filter(e=>visible(e)&&(e.matches('button,input,textarea,select,a[href],[role="button"]')||e.onclick||getComputedStyle(e).cursor==='pointer')).filter(e=>{const r=e.getBoundingClientRect();return r.y<innerHeight&&r.y+r.height>0&&r.x<innerWidth&&r.x+r.width>0;});
    return {title:document.title,text:document.body.innerText,viewport:{width:innerWidth,height:innerHeight},controls:candidates.map((e,index)=>{const r=e.getBoundingClientRect();return {index,tag:e.tagName.toLowerCase(),text:(e.innerText||e.getAttribute('aria-label')||e.getAttribute('title')||'').trim().slice(0,140),value:e.matches('input,select,textarea')?e.value:undefined,options:e.matches('select')?[...e.options].map(o=>o.text):undefined,rect:{x:Math.round(r.x),y:Math.round(r.y),width:Math.round(r.width),height:Math.round(r.height)},disabled:!!e.disabled};})};
  })()`);
  const number=++s.step;
  const folder=path.join(root,'evidence',agent,s.case);fs.mkdirSync(folder,{recursive:true});
  const screenshot=path.join(folder,`${String(number).padStart(3,'0')}.png`);
  const shot=await cdp('Page.captureScreenshot',{format:'png',captureBeyondViewport:false},s.session);
  fs.writeFileSync(screenshot,Buffer.from(shot.data,'base64'));
  data.screenshot=screenshot;data.step=number;data.case=s.case;
  fs.writeFileSync(path.join(folder,`${String(number).padStart(3,'0')}.json`),JSON.stringify(data,null,2));
  return data;
}
async function action(req){
  const agent=req.agent;if(!/^[abcm]$/.test(agent))throw new Error('Unknown participant');
  let s=sessions.get(agent);
  if(req.action==='open'){
    cases=JSON.parse(fs.readFileSync(path.join(root,'cases.json')));
    if(!cases[req.case])throw new Error('Unknown case');
    if(!s){const context=await cdp('Target.createBrowserContext');s={context:context.browserContextId,step:0};sessions.set(agent,s);}
    if(s.target)await cdp('Target.closeTarget',{targetId:s.target});
    const target=await cdp('Target.createTarget',{url:'about:blank',browserContextId:s.context});
    s.target=target.targetId;s.case=req.case;s.step=0;
    const attached=await cdp('Target.attachToTarget',{targetId:s.target,flatten:true});s.session=attached.sessionId;
    await cdp('Page.enable',{},s.session);
    await cdp('Emulation.setDeviceMetricsOverride',{width:1536,height:1200,deviceScaleFactor:1,mobile:false},s.session);
    await cdp('Page.navigate',{url:'file://'+cases[req.case]},s.session);
    await delay(650);
  }else{
    if(!s?.session)throw new Error('Open a case first');
    if(req.action==='click'){
      const p={x:Number(req.x),y:Number(req.y),button:'left',clickCount:1};
      await cdp('Input.dispatchMouseEvent',{type:'mousePressed',...p},s.session);
      await cdp('Input.dispatchMouseEvent',{type:'mouseReleased',...p},s.session);
    }else if(req.action==='drag'){
      const start={x:Number(req.x),y:Number(req.y)};
      await cdp('Input.dispatchMouseEvent',{type:'mouseMoved',...start},s.session);
      await cdp('Input.dispatchMouseEvent',{type:'mousePressed',button:'left',clickCount:1,...start},s.session);
      for(let i=1;i<=12;i++){await cdp('Input.dispatchMouseEvent',{type:'mouseMoved',buttons:1,x:start.x+(Number(req.toX)-start.x)*i/12,y:start.y+(Number(req.toY)-start.y)*i/12},s.session);await delay(15);}
      await cdp('Input.dispatchMouseEvent',{type:'mouseReleased',button:'left',clickCount:1,x:Number(req.toX),y:Number(req.toY)},s.session);
    }else if(req.action==='type'){
      await cdp('Input.insertText',{text:String(req.text)},s.session);
    }else if(req.action==='key'){
      const key=String(req.key), codes={Enter:13,Escape:27,Tab:9,ArrowDown:40,ArrowUp:38,ArrowLeft:37,ArrowRight:39,Backspace:8,Delete:46};
      await cdp('Input.dispatchKeyEvent',{type:'keyDown',key,windowsVirtualKeyCode:codes[key]||0},s.session);
      await cdp('Input.dispatchKeyEvent',{type:'keyUp',key,windowsVirtualKeyCode:codes[key]||0},s.session);
    }else if(req.action==='scroll'){
      await cdp('Input.dispatchMouseEvent',{type:'mouseWheel',x:Number(req.x||1450),y:Number(req.y||600),deltaY:Number(req.dy||500),deltaX:0},s.session);
    }else if(req.action==='wait'){
      await delay(Math.min(4000,Math.max(0,Number(req.ms)||800)));
    }else if(req.action!=='state')throw new Error('Only player UI actions are supported');
    await delay(130);
  }
  const state=await observe(agent,s);
  fs.appendFileSync(path.join(root,'actions.jsonl'),JSON.stringify({at:new Date().toISOString(),request:req,case:s.case,step:s.step,screenshot:state.screenshot})+'\n');
  return state;
}
const socket=path.join(root,'browser.sock');try{fs.unlinkSync(socket);}catch{}
net.createServer(client=>{
  let input='';client.on('data',data=>{input+=data.toString();if(input.includes('\n')){const line=input.split('\n')[0];input='';Promise.resolve().then(()=>action(JSON.parse(line))).then(result=>client.end(JSON.stringify({ok:true,result})+'\n')).catch(error=>client.end(JSON.stringify({ok:false,error:String(error)})+'\n'));}});
}).listen(socket,()=>console.log('Browser UI broker ready'));
process.on('SIGTERM',()=>{chrome.kill();process.exit(0);});
