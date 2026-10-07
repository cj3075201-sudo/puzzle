'use strict';
const assert=require('node:assert/strict');
const core=require('./core'),data=require('./models.json'),models=data.models;
const blue=['차갑다','따뜻하다','아프다','아니다','묻다','가지다','열다','닫다','가다'];
const parse=p=>core.analyze(p,models,blue),make=spec=>core.build(spec,models,blue);
let count=0;function test(name,fn){fn();count++;console.log('PASS '+name);}
test('built physical assembly reconstructs the original tree',()=>{const spec=['주민',['손',['차갑다']],['발',['아프다']]],p=make(spec),r=parse(p);assert.equal(r.ok,true);assert.equal(core.eq(r.tree,spec),true);assert.equal(r.canonical,core.canonical(spec));assert.equal(r.edges.length,p.length-1);});
test('horizontal and vertical fixed shapes have equivalent meaning',()=>{const horizontal=[{id:'a',model:'y_e',word:'나',x:0,y:0},{id:'b',model:'y_we',word:'손',x:1,y:0},{id:'c',model:'b_w',word:'차갑다',x:2,y:0}],vertical=[{id:'a',model:'y_s',word:'나',x:0,y:0},{id:'b',model:'y_ns',word:'손',x:0,y:1},{id:'c',model:'b_n',word:'차갑다',x:0,y:2}];assert.equal(parse(horizontal).canonical,parse(vertical).canonical);});
test('child ordering is immaterial but multiplicity and identity are retained',()=>{assert.equal(core.eq(['주민',['손',['차갑다']],['발',['아프다']]],['주민',['발',['아프다']],['손',['차갑다']]]),true);assert.equal(core.eq(['주민','손','손'],['주민','손']),false);const r=parse(make(['주민',['손',['차갑다']],['손',['따뜻하다']]]));assert.equal(r.tree.children.length,2);assert.notEqual(r.tree.children[0].children[0].word,r.tree.children[1].children[0].word);});
test('negation attachment scope changes canonical meaning',()=>{const a=['주민',['손',['차갑다',['아니다']]],['발',['아프다']]],b=['아니다',['주민',['손',['차갑다']],['발',['아프다']]]];assert.notEqual(parse(make(a)).canonical,parse(make(b)).canonical);});
test('question attachment scope stays distinct',()=>{const a=['묻다',['주민',['손',['차갑다']]]],b=['주민',['손',['묻다',['차갑다']]]];assert.equal(parse(make(a)).ok,true);assert.equal(parse(make(b)).ok,true);assert.equal(core.eq(a,b),false);});
test('yellow branching is allowed and yellow path length is enforced',()=>{assert.equal(parse(make(['주민',['손',['차갑다']],['발',['아프다']]])).ok,true);const p=[0,1,2,3].map(i=>({id:'n'+i,model:i?'y_we':'y_e',word:'손',x:i,y:0}));p.push({id:'state',model:'b_w',word:'차갑다',x:4,y:0});assert.equal(parse(p).code,'chain_limit');});
test('reverse connecting direction changes tree',()=>{const a=['주민',['손',['차갑다']]],b=['차갑다',['손',['주민']]];assert.notEqual(parse(make(a)).canonical,parse(make(b)).canonical);});
test('meaning depends on glyph placement not model identity',()=>{const p=make(['주민',['손',['차갑다']]]),before=parse(p).canonical;p.find(p=>p.word==='주민').word='나';assert.notEqual(parse(p).canonical,before);assert.equal(core.eq(parse(p).tree,['나',['손',['차갑다']]]),true);});
test('empty words overlap bounds and color mismatch fail',()=>{let p=make(['나',['손',['차갑다']]]);p[0].word='';assert.equal(parse(p).code,'empty_word');p=make(['나',['손',['차갑다']]]);p[1].x=p[0].x;p[1].y=p[0].y;assert.equal(parse(p).code,'overlap');p=make(['나',['손',['차갑다']]]);p[0].x=7;assert.equal(parse(p).code,'out_of_bounds');p=make(['나',['손',['차갑다']]]);p[0].word='차갑다';assert.equal(parse(p).code,'word_color');});
test('flat adjacency cannot substitute for a connection',()=>{const flat=Object.entries(models).find(([,m])=>m.color==='yellow'&&!m.ports.length)[0];const p=[{id:'a',model:flat,word:'나',x:0,y:0},{id:'b',model:flat,word:'손',x:1,y:0}];assert.equal(parse(p).code,'disconnected');});
test('round and twin mismatch fails while actual twin pair connects',()=>{const p=[{id:'a',model:'y_s',word:'나',x:0,y:0},{id:'b',model:'b_give',word:'가다',x:0,y:1}];assert.equal(parse(p).code,'port_mismatch');p[0].model='y_twin';assert.equal(parse(p).ok,true);});
test('directed cycle is rejected',()=>{const custom={};const definitions=[[['S','socket','round'],['E','tab','round']],[['W','socket','round'],['S','tab','round']],[['N','socket','round'],['W','tab','round']],[['E','socket','round'],['N','tab','round']]];definitions.forEach((ports,i)=>custom['m'+i]={color:'blue',ports});const p=[[0,0],[1,0],[1,1],[0,1]].map(([x,y],i)=>({id:i,model:'m'+i,word:'차갑다',x,y}));assert.equal(core.analyze(p,custom,blue).code,'cycle');});
test('merging two parents is rejected instead of collapsing node identity',()=>{const custom={a:{color:'yellow',ports:[['E','tab','round'],['S','tab','round']]},b:{color:'blue',ports:[['W','socket','round'],['S','tab','round']]},c:{color:'blue',ports:[['N','socket','round'],['E','tab','round']]},d:{color:'yellow',ports:[['W','socket','round'],['N','socket','round']]}};const p=[{id:'a',model:'a',word:'주민',x:0,y:0},{id:'b',model:'b',word:'가지다',x:1,y:0},{id:'c',model:'c',word:'가지다',x:0,y:1},{id:'d',model:'d',word:'손',x:1,y:1}];assert.equal(core.analyze(p,custom,blue).code,'multiple_parents');});
test('unused exposed ports do not force a grammar failure',()=>{const p=[{id:'a',model:'y_es',word:'손',x:0,y:0},{id:'b',model:'b_w',word:'차갑다',x:1,y:0}];assert.equal(parse(p).ok,true);});
test('three-child twelve-piece tree builds inside seven by six',()=>{const spec=['묻다',['주민',['손',['차갑다']],['발',['아프다']]],['나',['손',['따뜻하다']]],['주민',['가다',['집']]]];const p=make(spec);assert.equal(p.length,12);assert.equal(parse(p).ok,true);assert.equal(core.eq(parse(p).tree,spec),true);assert.ok(p.every(p=>p.x<7&&p.y<6));});
test('construction and analysis preserve input specs and model tables',()=>{const spec=['주민',['손',['차갑다']]],before=JSON.stringify({spec,models}),p=make(spec),saved=JSON.stringify(p);parse(p);assert.equal(JSON.stringify({spec,models}),before);assert.equal(JSON.stringify(p),saved);});
test('physical rotation flag is rejected; alternative models are used instead',()=>{const p=make(['손',['차갑다']]);p[0].rotation=90;assert.equal(parse(p).code,'rotation');});
test('all supplied model paths are real geometry with one port per side',()=>{for(const m of Object.values(models)){assert.match(m.path,/^M /);assert.match(m.path,/ Z$/);assert.equal(new Set(m.ports.map(p=>p[0])).size,m.ports.length);}assert.ok(models.y_ws&&models.b_ws);});
test('all twelve scenario speech and solution structures round-trip with supplied colors',()=>{
 globalThis.JigsawCore=core;globalThis.SCENARIOS=[];require('./scenarios-a.js');require('./scenarios-b.js');
 assert.equal(globalThis.SCENARIOS.length,12);let checked=0;
 for(const scenario of globalThis.SCENARIOS)for(const spec of [...scenario.actors.flatMap(a=>a.speech||[]),...(scenario.solutions||[]).map(s=>s.spec)]){
  const pieces=core.build(spec,models,scenario.blueWords),r=core.analyze(pieces,models,scenario.blueWords);
  assert.equal(r.ok,true,scenario.id+': '+r.message);assert.equal(core.eq(r.tree,spec),true);checked++;
  assert.ok(pieces.every(p=>data.palette.includes(p.model)),'displayed model must be available: '+scenario.id);
 }
 assert.ok(checked>=40);
});
console.log(count+' tests passed');
