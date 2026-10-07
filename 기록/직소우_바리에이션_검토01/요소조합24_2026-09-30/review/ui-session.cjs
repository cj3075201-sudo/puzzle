const fs = require('fs');
const path = require('path');
const readline = require('readline');
const { spawn } = require('child_process');
const root = path.resolve(__dirname, '..');
const evidence = path.join(__dirname, 'evidence-c');
fs.mkdirSync(evidence, { recursive: true });
const chrome = spawn('/home/cj3071/.cache/ms-playwright/chromium-1243/chrome-linux64/chrome', [
  '--headless=new', '--no-sandbox', '--disable-gpu', '--no-first-run', '--remote-debugging-pipe',
  '--allow-file-access-from-files', '--user-data-dir=/tmp/grad-combinations24-c-profile'
], { stdio: ['ignore', 'ignore', fs.openSync(path.join(__dirname, 'chrome-c.log'), 'a'), 'pipe', 'pipe'],
  env: { ...process.env, LD_LIBRARY_PATH: '/tmp/grad-blind-20260930/libs/usr/lib/x86_64-linux-gnu' } });
let serial = 0, buffer = '', step = Math.max(0,...fs.readdirSync(evidence).filter(n=>/^\d+\.json$/.test(n)).map(n=>parseInt(n))), session, viewport = { width: 1536, height: 1200 };
const pending = new Map();
chrome.stdio[4].on('data', chunk => {
  buffer += chunk.toString();
  let end;
  while ((end = buffer.indexOf('\0')) >= 0) {
    const raw = buffer.slice(0, end); buffer = buffer.slice(end + 1);
    if (!raw) continue;
    const message = JSON.parse(raw), handler = pending.get(message.id);
    if (handler) { pending.delete(message.id); message.error ? handler.reject(Error(JSON.stringify(message.error))) : handler.resolve(message.result || {}); }
  }
});
function cdp(method, params = {}, sessionId = session) {
  return new Promise((resolve, reject) => {
    const id = ++serial; pending.set(id, { resolve, reject });
    chrome.stdio[3].write(JSON.stringify({ id, method, params, ...(sessionId ? { sessionId } : {}) }) + '\0');
    setTimeout(() => { if (pending.has(id)) { pending.delete(id); reject(Error('CDP timeout: ' + method)); } }, 20000).unref();
  });
}
const delay = ms => new Promise(resolve => setTimeout(resolve, ms));
async function readUI() {
  const expression = `(() => ({title:document.title,text:document.body.innerText,viewport:{width:innerWidth,height:innerHeight},controls:[...document.querySelectorAll('button,select,input,summary,[role="button"],svg g[aria-label],svg rect[aria-label]')].map((e,index)=>{const r=e.getBoundingClientRect();return {index,tag:e.tagName.toLowerCase(),text:e.innerText||e.getAttribute('aria-label')||e.getAttribute('title')||'',rect:{x:Math.round(r.x),y:Math.round(r.y),width:Math.round(r.width),height:Math.round(r.height)},disabled:!!e.disabled}}).filter(e=>e.rect.width>0&&e.rect.height>0&&e.rect.y<innerHeight&&e.rect.y+e.rect.height>0&&e.rect.x<innerWidth&&e.rect.x+e.rect.width>0)}))()`;
  const r = await cdp('Runtime.evaluate', { expression, returnByValue: true });
  if (r.exceptionDetails) throw Error('UI observation failed');
  return r.result.value;
}
async function snapshot(action) {
  const ui = await readUI(), id = String(++step).padStart(3, '0');
  const shot = await cdp('Page.captureScreenshot', { format: 'png' });
  ui.screenshot = path.join(evidence, id + '.png');
  ui.step = step;
  fs.writeFileSync(ui.screenshot, Buffer.from(shot.data, 'base64'));
  fs.writeFileSync(path.join(evidence, id + '.json'), JSON.stringify({ action, ...ui }, null, 2));
  fs.appendFileSync(path.join(__dirname, 'ui-actions-c.jsonl'), JSON.stringify({ action, ...ui }) + '\n');
  return ui;
}
async function click(x, y) {
  await cdp('Input.dispatchMouseEvent', { type: 'mouseMoved', x, y });
  await cdp('Input.dispatchMouseEvent', { type: 'mousePressed', x, y, button: 'left', clickCount: 1 });
  await cdp('Input.dispatchMouseEvent', { type: 'mouseReleased', x, y, button: 'left', clickCount: 1 });
}
async function action(a) {
  if (a.action === 'open') { await cdp('Page.navigate', { url: 'file://' + root + '/' + (a.file || '플레이.html') }); await delay(700); }
  else if (a.action === 'source-hashes') {
    const r=await cdp('Runtime.evaluate',{expression:'[...document.scripts].map(s=>s.textContent)',returnByValue:true});
    const names=['model-data','core.js','state.js','levels.js','scene.js','app.js'];
    const hashes=r.result.value.map((source,i)=>({name:names[i],bytes:Buffer.byteLength(source),sha256:require('crypto').createHash('sha256').update(source).digest('hex'),matchesFile:i>0&&source===fs.readFileSync(path.join(root,names[i]),'utf8')}));
    fs.writeFileSync(path.join(__dirname,'embedded-final-hashes.json'),JSON.stringify({method:'read only document.scripts textContent from actual final browser DOM',hashes},null,2));
  }
  else if (a.action === 'click') await click(a.x, a.y);
  else if (a.action === 'selector') {
    const query = JSON.stringify(a.selector);
    const result = await cdp('Runtime.evaluate', { expression: `(() => {const e=document.querySelector(${query});if(!e)return null;e.scrollIntoView({block:'nearest',inline:'nearest'});const r=e.getBoundingClientRect();return {x:r.x+r.width/2,y:r.y+r.height/2,width:r.width,height:r.height,disabled:!!e.disabled}})()`, returnByValue: true });
    const rect = result.result.value;
    if (!rect || !rect.width || !rect.height || rect.disabled) throw Error('Visible enabled control missing: '+a.selector);
    await delay(80); await click(rect.x, rect.y);
  }
  else if (a.action === 'wait') await delay(a.ms || 500);
  else if (a.action === 'reload') { await cdp('Page.reload'); await delay(700); }
  else if (a.action === 'width') { viewport = { width: a.width, height: a.height || 1200 }; await cdp('Emulation.setDeviceMetricsOverride', { ...viewport, deviceScaleFactor: 1, mobile: false }); await delay(150); }
  else if (a.action === 'scroll') { await cdp('Input.dispatchMouseEvent', { type: 'mouseWheel', x: a.x || 100, y: a.y || 500, deltaX: 0, deltaY: a.dy }); await delay(120); }
  else if (a.action === 'type') await cdp('Input.insertText', { text: a.text });
  else if (a.action === 'key') {
    const codes = { Delete: 46, Backspace: 8, Escape: 27, Enter: 13, Tab: 9, z: 90 };
    const opts = { key: a.key, windowsVirtualKeyCode: codes[a.key] || 0, nativeVirtualKeyCode: codes[a.key] || 0, modifiers: a.ctrl ? 2 : 0 };
    await cdp('Input.dispatchKeyEvent', { type: 'keyDown', ...opts }); await cdp('Input.dispatchKeyEvent', { type: 'keyUp', ...opts });
  } else if (a.action === 'drag') {
    await cdp('Input.dispatchMouseEvent', { type: 'mousePressed', x: a.x, y: a.y, button: 'left', clickCount: 1 });
    for (let k = 1; k <= 8; k++) { await cdp('Input.dispatchMouseEvent', { type: 'mouseMoved', x: a.x + (a.toX-a.x)*k/8, y: a.y + (a.toY-a.y)*k/8, button: 'left', buttons: 1 }); await delay(25); }
    await cdp('Input.dispatchMouseEvent', { type: 'mouseReleased', x: a.toX, y: a.toY, button: 'left', clickCount: 1 });
  } else if (a.action === 'quit') { chrome.kill(); process.exit(0); }
  else if (a.action !== 'state') throw Error('Unsupported action');
  await delay(70);
  return snapshot(a);
}
(async () => {
  const target = await cdp('Target.createTarget', { url: 'about:blank' }, null);
  session = (await cdp('Target.attachToTarget', { targetId: target.targetId, flatten: true }, null)).sessionId;
  await cdp('Page.enable');
  await cdp('Emulation.setDeviceMetricsOverride', { ...viewport, deviceScaleFactor: 1, mobile: false });
  process.stdout.write(JSON.stringify({ ready: true }) + '\n');
  for await (const line of readline.createInterface({ input: process.stdin })) {
    try { const a = JSON.parse(line), out = a.action === 'batch' ? await runBatch(a.actions) : await action(a); process.stdout.write(JSON.stringify({ ok: true, result: out }) + '\n'); }
    catch (error) { process.stdout.write(JSON.stringify({ ok: false, error: error.message }) + '\n'); }
  }
  chrome.kill();
})().catch(error => { console.error(error); chrome.kill(); process.exitCode = 1; });
async function runBatch(actions) {
  let out; for (const a of actions) out = await action(a); return out;
}
