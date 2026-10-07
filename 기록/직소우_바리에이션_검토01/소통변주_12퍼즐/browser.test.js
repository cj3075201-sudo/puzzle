(async()=>{
const checks=[],errors=[];window.addEventListener('error',e=>errors.push(e.message));
const q=s=>document.querySelector(s),click=s=>{const e=q(s);if(!e)throw Error('missing '+s);e.dispatchEvent(new MouseEvent('click',{bubbles:true}));},ok=(name,condition)=>{checks.push({name,pass:!!condition});if(!condition)throw Error(name);};
try{
 await document.fonts.ready;
 const api=Communication12;ok('12 lobby cards',document.querySelectorAll('[data-puzzle]').length===12);
 const add=p=>{click('[data-color="'+api.models[p.model].color+'"]');click('[data-model="'+p.model+'"]');click('[data-cell="'+p.x+','+p.y+'"]');click('[data-word="'+p.word+'"]');};
 for(const sc of api.scenarios){
  api.open(sc.id);api.reset();
  for(const a of sc.actors){click('[data-actor="'+a.id+'"]');ok(sc.id+' NPC '+a.id+' hears',api.getState().listener===a.id);}
  ok(sc.id+' hearing does not complete',!api.getState().world.complete);
  if(api.getState().pieces.length)click('#clear');
  // Build every solution through actual model/cell/word controls; don't bypass input.
  for(const [i,step] of sc.solutions.entries()){
   if(api.getState().pieces.length)click('#clear');
   const pieces=JigsawCore.build(step.spec,api.models,sc.blueWords);
   for(const p of pieces)add(p);
   ok(sc.id+' step '+i+' UI graph matches',api.analyze().ok&&JigsawCore.eq(api.analyze().tree,step.spec));
   click('[data-actor="'+step.listener+'"]');click('#speak');
   ok(sc.id+' step '+i+' accepted',api.getState().attempts.at(-1).ok);
  }
  ok(sc.id+' completed',api.getState().world.complete&&!q('#finish').hidden);
  const stored=JSON.parse(localStorage.getItem('grad.communication12.v1.test'));
  ok(sc.id+' completion saved',stored[sc.id].world.complete);
 }
 api.open(4);api.reset();const original=api.getState().pieces.length;click('#clear');ok('clear',!api.getState().pieces.length);click('#undo');ok('undo clear',api.getState().pieces.length===original);
 const p=api.getState().pieces[0];const oldWord=p.word;click('[data-word="가다"]');
 const target=q('[data-piece="'+p.id+'"]');target.dispatchEvent(new KeyboardEvent('keydown',{key:'Enter',bubbles:true}));
 ok('wrong color does not replace',api.getState().pieces[0].word===oldWord);
 click('[data-color="yellow"]');click('[data-word="나"]');q('[data-piece="'+p.id+'"]').dispatchEvent(new KeyboardEvent('keydown',{key:'Enter',bubbles:true}));
 ok('word replacement',api.getState().pieces[0].word==='나');click('#undo');ok('undo word',api.getState().pieces[0].word===oldWord);
 // Move with actual pointer drag events in SVG coordinates.
 const target2=q('[data-piece="'+p.id+'"]'),r=target2.getBoundingClientRect(),empty=q('[data-cell="6,5"]'),er=empty.getBoundingClientRect();
 target2.dispatchEvent(new PointerEvent('pointerdown',{button:0,clientX:r.x+r.width/2,clientY:r.y+r.height/2,bubbles:true,pointerId:1}));
 window.dispatchEvent(new PointerEvent('pointermove',{clientX:er.x+er.width/2,clientY:er.y+er.height/2,bubbles:true,pointerId:1}));
 window.dispatchEvent(new PointerEvent('pointerup',{clientX:er.x+er.width/2,clientY:er.y+er.height/2,bubbles:true,pointerId:1}));
 ok('pointer drag moved',api.getState().pieces[0].x===6&&api.getState().pieces[0].y===5);click('#undo');
 api.open(1);ok('switch restores complete',api.getState().world.complete);api.open(7);api.reset();click('#hint-button');ok('hint opens',!q('#hint').hidden);ok('hint not completion',!api.getState().world.complete);
 api.home();ok('lobby returns',!q('#lobby').hidden);ok('no horizontal overflow',document.documentElement.scrollWidth<=innerWidth);ok('no runtime errors',!errors.length);
 api.open(9);api.reset();click('[data-actor="suri"]');const step=api.scenarios.find(s=>s.id===9).solutions[0];for(const p of JigsawCore.build(step.spec,api.models,api.scenarios.find(s=>s.id===9).blueWords))add(p);
}catch(e){checks.push({name:'exception '+e.stack,pass:false});}
const out=document.createElement('pre');out.id='verification';out.style.display='none';out.textContent=JSON.stringify({passed:checks.every(c=>c.pass),checks,errors});document.body.append(out);
})();
