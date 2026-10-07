'use strict';
const assert=require('node:assert/strict');
const {analyze,evaluate}=require('./core');
const Y=ports=>({color:'yellow',ports}),B=ports=>({color:'blue',ports});
const models={
 y_es:Y([['E','tab','round'],['S','tab','round']]),y_e:Y([['E','tab','round']]),y_s:Y([['S','tab','round']]),
 y_w:Y([['W','socket','round']]),y_n:Y([['N','socket','round']]),y_nw:Y([['N','socket','round'],['W','socket','round']]),
 b_we:B([['W','socket','round'],['E','tab','round']]),b_ns:B([['N','socket','round'],['S','tab','round']]),
 y_ne:Y([['N','socket','round'],['E','tab','round']]),y_nes:Y([['N','socket','round'],['E','tab','round'],['S','tab','round']])
};
const fixture=(full=true)=>[
 {id:'resident',model:'y_es',word:'주민',x:1,y:0},
 {id:'has',model:'b_we',word:'가지다',x:2,y:0},
 {id:'key',model:'y_w',word:'열쇠',x:3,y:0},
 {id:'go',model:'b_ns',word:'가다',x:1,y:1},
 {id:'inside',model:full?'y_nw':'y_n',word:'안',x:1,y:2},
 ...(full?[{id:'house',model:'y_e',word:'집',x:0,y:2}]:[])
];
const world=()=>({residents:[{id:'key_holder',location:'outside',holds:['열쇠']},{id:'book_holder',location:'outside',holds:['책']}],complete:false});
const run=(p,w=world(),m=models)=>evaluate(p,m,w);
const noCondition=()=>fixture(false).filter(p=>!['has','key'].includes(p.id));
let count=0;function test(name,fn){fn();count++;console.log('PASS '+name);}
test('short 5 and full 6 pieces resolve identically without mutating inputs',()=>{
 for(const full of [false,true]){const p=fixture(full),w=world(),before=JSON.stringify({p,w}),r=run(p,w);assert.equal(r.code,'complete');assert.equal(r.target,'key_holder');assert.equal(r.world.residents[0].location,'inside');assert.equal(r.world.complete,true);assert.equal(JSON.stringify({p,w}),before);assert.notEqual(r.world.residents[1].holds,w.residents[1].holds);}
});
test('book holder visits and returns without world mutation',()=>{const p=fixture();p[2].word='책';const w=world(),r=run(p,w);assert.equal(r.code,'wrong_person');assert.equal(r.action,'visit_return');assert.equal(r.target,'book_holder');assert.deepEqual(r.world,w);assert.notEqual(r.world,w);});
test('no possession condition leaves two residents ambiguous',()=>assert.equal(run(noCondition()).code,'ambiguous_resident'));
test('outside modifier still leaves both residents ambiguous',()=>{const p=noCondition();p[0].model='y_nes';p.push({id:'outside',model:'y_s',word:'밖',x:1,y:-1});assert.equal(run(p).code,'ambiguous_resident');});
test('single resident context permits short 3-piece request',()=>{const w=world();w.residents.pop();assert.equal(run(noCondition(),w).code,'complete');});
test('two key owners remain ambiguous',()=>{const w=world();w.residents[1].holds.push('열쇠');assert.equal(run(fixture(),w).code,'ambiguous_resident');});
test('zero matching owners cannot succeed',()=>{const w=world();w.residents[0].holds=[];assert.equal(run(fixture(),w).code,'no_matching_resident');});
test('reversed possession cannot imply ownership',()=>{const p=fixture();p[0].word='열쇠';p[2].word='주민';assert.equal(run(p).code,'invalid_possession');});
test('possession statement alone has no movement',()=>{const p=fixture().filter(p=>['resident','has','key'].includes(p.id));assert.equal(run(p).code,'movement_count');});
test('key as mover does not move its owner',()=>{const p=noCondition();p[0].word='열쇠';assert.equal(run(p).code,'invalid_mover');});
test('outside destination does not complete',()=>{const p=fixture(false);p[4].word='밖';assert.equal(run(p).code,'already_there');});
test('missing destination is incomplete',()=>{const p=fixture(false).filter(p=>p.id!=='inside');assert.equal(run(p).code,'movement_roles');});
test('floating extra pieces cannot be ignored',()=>{const p=fixture();p.push({id:'extra',model:'y_e',word:'나',x:9,y:9});assert.equal(run(p).code,'disconnected');});
test('translated layout has same graph meaning',()=>{const p=fixture().map(p=>({...p,x:p.x-19,y:p.y+31}));assert.equal(run(p).code,'complete');});
test('unused exposed port is allowed',()=>{const m={...models,y_n:Y([['N','socket','round'],['E','tab','round']])};assert.equal(run(fixture(false),world(),m).code,'complete');});
test('glyph assignment changes meaning independently from shape',()=>{const p=fixture();p[1].word='가다';p[3].word='가지다';assert.equal(run(p).code,'invalid_possession');});
test('mismatched connector and overlapping bodies fail',()=>{const m={...models,y_es:Y([['E','tab','twin'],['S','tab','round']])};assert.equal(run(fixture(),world(),m).code,'port_mismatch');const p=fixture();p[2].x=2;assert.equal(run(p).code,'overlap');});
test('blue output may enter house then inside chain',()=>{const p=fixture(false);p[4]={...p[4],model:'y_ne',word:'집'};p.push({id:'destination',model:'y_w',word:'안',x:2,y:2});const r=run(p);assert.equal(r.code,'complete');assert.deepEqual(r.meaning.destinationWords,['집','안']);});
test('reversed inside-house destination is not equivalent',()=>{const p=fixture(false);p[4]={...p[4],model:'y_ne'};p.push({id:'destination',model:'y_w',word:'집',x:2,y:2});assert.equal(run(p).code,'invalid_destination');});
test('completion cannot replay',()=>{const p=fixture(),r=run(p);assert.equal(run(p,r.world).code,'already_complete');});
test('separate resident possession never filters movement subject through shared item',()=>{
 const p=fixture(false);p[2].model='y_nw';
 p.push({id:'otherResident',model:'y_s',word:'주민',x:3,y:-2},{id:'otherHas',model:'b_ns',word:'가지다',x:3,y:-1});
 assert.equal(run(p).code,'unrelated_condition');
});
test('multiple possession clauses on same resident accumulate conditions',()=>{
 const m={...models,y_three:Y([['N','tab','round'],['E','tab','round'],['S','tab','round']]),b_se:B([['S','socket','round'],['E','tab','round']])};
 const p=fixture(false);p[0].model='y_three';
 p.push({id:'hasBook',model:'b_se',word:'가지다',x:1,y:-1},{id:'book',model:'y_w',word:'책',x:2,y:-1});
 assert.equal(run(p,world(),m).code,'no_matching_resident');
 const w=world();w.residents[0].holds.push('책');const r=run(p,w,m);
 assert.equal(r.code,'complete');assert.deepEqual(r.meaning.subject.conditions,['열쇠','책']);
});
test('four yellow modifiers exceed chain limit',()=>{
 const m={...models,y_ns:Y([['N','socket','round'],['S','tab','round']])};
 const p=fixture(false);p[0].model='y_nes';
 p.push({id:'a',model:'y_s',word:'집',x:1,y:-3},{id:'b',model:'y_ns',word:'집',x:1,y:-2},{id:'c',model:'y_ns',word:'밖',x:1,y:-1});
 assert.equal(run(p,world(),m).code,'chain_limit');
});
test('inventory exchange follows actual key holder regardless of resident id',()=>{
 const w=world();w.residents[0].holds=['책'];w.residents[1].holds=['열쇠'];
 const r=run(fixture(),w);assert.equal(r.code,'complete');assert.equal(r.target,'book_holder');
 assert.equal(r.world.residents[1].location,'inside');assert.equal(r.world.residents[0].location,'outside');
 assert.equal(r.message,'열쇠를 가진 주민이 안으로 들어가 관리인을 만납니다.');
 const p=fixture();p[2].word='책';const wrong=run(p,w);
 assert.equal(wrong.code,'wrong_person');assert.equal(wrong.target,'key_holder');assert.deepEqual(wrong.world,w);
});
test('renaming current key holder cannot break completion',()=>{
 const w=world();w.residents[0].id='visitor_73';
 const r=run(fixture(),w);assert.equal(r.code,'complete');assert.equal(r.target,'visitor_73');
});
console.log(count+' tests passed');
