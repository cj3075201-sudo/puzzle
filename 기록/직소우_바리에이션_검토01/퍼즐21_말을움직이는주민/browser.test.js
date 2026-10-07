(async()=>{
const checks=[],errors=[];window.addEventListener('error',e=>errors.push(e.message));
const A=window.Meta21,$=s=>document.querySelector(s),click=n=>{if(!n)throw Error('missing control');n.dispatchEvent(new MouseEvent('click',{bubbles:true}));},assert=(name,ok)=>{checks.push({name,pass:!!ok});if(!ok)throw Error(name);};
function assemble(spec){click($('#clear'));const ps=JigsawCore.build(spec,A.models,A.blues);for(const p of ps){click($(`[data-color="${A.models[p.model].color}"]`));click($(`[data-model="${p.model}"]`));click($(`[data-cell="${p.x},${p.y}"]`));click($(`[data-word="${p.word}"]`));}assert('palette assembly: '+JSON.stringify(spec),JigsawCore.analyze(A.getState().pieces,A.models,A.blues).ok);}
try{
 if(localStorage.getItem(A.storageKey+'.phase')==='reload'){
  assert('completed world restored after browser restart',A.getState().world.complete&&A.getState().world.world.crossed);
  assert('board layout restored',A.getState().world.board.find(p=>p.id==='reader').y===3);
  assert('assembled speech restored',A.getState().pieces.length===5);
  assert('completed UI restored',!$('#finish').hidden&&$('#speak').disabled);
  localStorage.removeItem(A.storageKey+'.phase');
 }else{
 A.reset();assemble(['주민',['옮기다',['글자','글자'],'위']]);click($('#speak'));assert('detached quote loses visual quote marker',!document.querySelector('[data-npc-piece="quoted-resident"]').classList.contains('quote'));click($('#undo'));assert('quote marker restored by undo',document.querySelector('[data-npc-piece="quoted-resident"]').classList.contains('quote'));A.reset();assert('initial NPC reads close',MetaPuzzle.read(A.getState().world).tree.children[0].word==='닫다');assert('starter can be spoken',JigsawCore.analyze(A.getState().pieces,A.models,A.blues).ok);
 click($('#speak'));assert('world box moved by starter',A.getState().world.world.box.x===0);click($('#undo'));assert('world undo',A.getState().world.world.box.x===1);
 const p=A.getState().pieces[0];click($(`[data-piece="${p.id}"]`));click($('[data-word="열다"]'));assert('wrong color rejected',A.getState().pieces[0].word==='주민'&&$('#feedback').className==='error');
 // Actual pointer drag to a free bottom cell and back via undo.
 const n=$(`[data-piece="${p.id}"]`),r=n.getBoundingClientRect(),svg=$('#board'),mat=svg.getScreenCTM(),dest=new DOMPoint(20+6*70+35,20+5*70+35).matrixTransform(mat),cx=r.left+r.width/2,cy=r.top+r.height/2;
 n.dispatchEvent(new PointerEvent('pointerdown',{bubbles:true,pointerId:7,button:0,clientX:cx,clientY:cy}));window.dispatchEvent(new PointerEvent('pointermove',{bubbles:true,pointerId:7,clientX:dest.x,clientY:dest.y}));window.dispatchEvent(new PointerEvent('pointerup',{bubbles:true,pointerId:7,clientX:dest.x,clientY:dest.y}));
 assert('pointer drag moved piece',A.getState().pieces.find(x=>x.id===p.id).x===6);click($('#speak'));assert('disconnected speech rejected',!A.getState().world.world.doorOpen&&$('#feedback').className==='error');click($('#undo'));assert('drag undo',A.getState().pieces.find(x=>x.id===p.id).x===p.x);
 assemble(['주민',['열다','문']]);click($('#speak'));assert('direct opening followed by close',!A.getState().world.world.doorOpen&&A.getState().events.map(x=>x.open).join(',')==='true,false');
 assemble(['주민',['옮기다',['글자','문'],'왼쪽']]);click($('#speak'));assert('ambiguous door glyph rejected',/2개/.test($('#feedback').textContent));
 assemble(['주민',['옮기다',['글자',['아래','문']],'왼쪽']]);click($('#speak'));assert('lower door glyph repair',A.getState().world.board.find(p=>p.id==='bottom-door').x===2);
 assemble(['주민',['옮기다',['글자','주민'],'아래']]);click($('#speak'));assert('first root move pauses',A.getState().world.board.find(p=>p.id==='reader').y===1);
 // Exercise failed exit state changes after a direct opening on a disconnected board.
 assemble(['주민',['열다','문']]);click($('#speak'));assert('direct open while board paused',A.getState().world.world.doorOpen);click($('[data-world="door"]'));assert('failed exit updates closed door',!A.getState().world.complete&&!A.getState().world.world.doorOpen);click($('#undo'));assert('failed exit undo restores open',A.getState().world.world.doorOpen);
 assemble(['주민',['옮기다',['글자','주민'],'아래']]);click($('#speak'));assert('NPC self-moves root and opens',A.getState().world.board.find(p=>p.id==='reader').y===3&&A.getState().world.world.doorOpen&&A.getState().world.selfEdits===1);assert('all automatic actions are visible',A.getState().events.length===3&&$('#events').children.length===3);click($('#undo'));assert('whole automatic chain undo',A.getState().world.board.find(p=>p.id==='reader').y===1&&A.getState().world.selfEdits===0);click($('#speak'));click($('[data-world="door"]'));assert('world click finishes puzzle',A.getState().world.complete&&!$('#finish').hidden);assert('saved completion',JSON.parse(localStorage.getItem(A.storageKey)).world.complete);assert('no horizontal overflow',document.documentElement.scrollWidth<=innerWidth);assert('no JS error',!errors.length);localStorage.setItem(A.storageKey+'.phase','reload');
 }
}catch(e){checks.push({name:e.stack||String(e),pass:false});}
const result={passed:checks.every(c=>c.pass),checks,errors};const pre=document.createElement('pre');pre.id='verification';pre.hidden=true;pre.textContent=JSON.stringify(result);document.body.append(pre);
})();
