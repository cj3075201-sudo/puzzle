'use strict';
const assert=require('node:assert/strict');
const {analyze,evaluate}=require('./core');
const Y=ports=>({color:'yellow',ports}),B=ports=>({color:'blue',ports});
const models={
 y_es:Y([['E','tab','round'],['S','tab','round']]),y_s:Y([['S','tab','round']]),
 y_nes:Y([['N','socket','round'],['E','tab','round'],['S','tab','round']]),
 y_ns:Y([['N','socket','round'],['S','tab','round']]),y_e:Y([['E','tab','round']]),
 y_w:Y([['W','socket','round']]),y_n:Y([['N','socket','round']]),
 y_nw:Y([['N','socket','round'],['W','socket','round']]),y_ne:Y([['N','socket','round'],['E','tab','round']]),
 b_we:B([['W','socket','round'],['E','tab','round']]),b_ns:B([['N','socket','round'],['S','tab','round']])
};
const world=()=>({residents:[{id:'key_holder',location:'outside',holds:['열쇠']},{id:'book_holder',location:'inside',holds:['책']}],complete:false});
function ownership(item,destination){return [
 {id:'resident',model:'y_es',word:'주민',x:1,y:0},
 {id:'has',model:'b_we',word:'가지다',x:2,y:0},
 {id:'item',model:'y_w',word:item,x:3,y:0},
 {id:'go',model:'b_ns',word:'가다',x:1,y:1},
 {id:'destination',model:'y_n',word:destination,x:1,y:2}
];}
function location(place,destination,full=false){const p=ownership('열쇠',destination).filter(p=>!['has','item'].includes(p.id));p[0].model='y_nes';p.push({id:'location',model:full?'y_ns':'y_s',word:place,x:1,y:-1});if(full)p.push({id:'house',model:'y_s',word:'집',x:1,y:-2});return p;}
function fullDestination(p,throughHouse=false){p=p.map(p=>({...p}));const d=p.find(p=>p.id==='destination');if(throughHouse){const place=d.word;d.model='y_ne';d.word='집';p.push({id:'place',model:'y_w',word:place,x:2,y:2});}else{d.model='y_nw';p.push({id:'destHouse',model:'y_e',word:'집',x:0,y:2});}return p;}
const run=(p,w=world(),m=models)=>evaluate(p,m,w);
let count=0;function test(name,fn){fn();count++;console.log('PASS '+name);}
test('key first then book completes with preserved input snapshots',()=>{const w=world(),p=ownership('열쇠','안'),before=JSON.stringify({w,p});const a=run(p,w);assert.equal(a.code,'move');assert.equal(a.action,'move');assert.equal(a.target,'key_holder');assert.equal(a.destination,'inside');assert.equal(a.world.complete,false);assert.equal(JSON.stringify({w,p}),before);const b=run(ownership('책','밖'),a.world);assert.equal(b.code,'complete');assert.equal(b.world.complete,true);assert.equal(a.world.residents[1].location,'inside');});
test('book first then key also completes',()=>{const a=run(ownership('책','밖'));assert.equal(a.code,'move');assert.equal(run(ownership('열쇠','안'),a.world).code,'complete');});
test('inside reference becomes ambiguous after moving key inside',()=>{const w=run(location('밖','안')).world;assert.equal(run(location('안','밖'),w).code,'ambiguous_resident');});
test('outside reference becomes ambiguous after moving book outside',()=>{const w=run(location('안','밖')).world;assert.equal(run(location('밖','안'),w).code,'ambiguous_resident');});
test('ownership selects correct resident after location becomes shared',()=>{const w=run(location('밖','안')).world;const r=run(ownership('책','밖'),w);assert.equal(r.code,'complete');assert.equal(r.target,'book_holder');});
test('unfinished movement is reversible and can still finish',()=>{const first=run(ownership('열쇠','안'));const back=run(ownership('열쇠','밖'),first.world);assert.equal(back.code,'move');assert.deepEqual(back.world,world());const book=run(ownership('책','밖'),back.world);assert.equal(run(ownership('열쇠','안'),book.world).code,'complete');});
test('empty location cannot select a resident',()=>{const w=run(ownership('열쇠','안')).world;assert.equal(run(location('밖','안'),w).code,'no_matching_resident');});
test('resident alone remains ambiguous',()=>{const p=ownership('열쇠','안').filter(p=>!['has','item'].includes(p.id));assert.equal(run(p).code,'ambiguous_resident');});
test('already-there request has no movement result',()=>{const w=world(),r=run(ownership('열쇠','밖'),w);assert.equal(r.code,'already_there');assert.equal(r.world,undefined);assert.deepEqual(w,world());});
test('short and full location references agree',()=>{assert.equal(run(location('밖','안')).target,'key_holder');assert.equal(run(location('밖','안',true)).target,'key_holder');assert.equal(run(location('안','밖',true)).target,'book_holder');});
test('inside and outside destinations support both full house attachments',()=>{for(const through of [false,true]){const a=run(fullDestination(ownership('책','밖'),through));assert.equal(a.code,'move');const b=run(fullDestination(ownership('열쇠','안'),through),a.world);assert.equal(b.code,'complete');}});
test('goal follows actual holdings when ids and inventories change',()=>{const w=world();w.residents[0]={id:'a',location:'outside',holds:['책']};w.residents[1]={id:'b',location:'outside',holds:['열쇠']};const r=run(ownership('열쇠','안'),w);assert.equal(r.code,'complete');assert.equal(r.target,'b');});
test('world must have distinct sole key and book holders',()=>{for(const mutate of [w=>w.residents.pop(),w=>w.residents[1].holds.push('열쇠'),w=>w.residents[0].holds=[],w=>{w.residents[0].holds=['열쇠','책'];w.residents[1].holds=[];}]){const w=world();mutate(w);assert.equal(run(ownership('열쇠','안'),w).code,'invalid_world');}});
test('location and possession constraints both apply',()=>{const p=ownership('열쇠','안');p[0].model='y_nes';p.push({id:'place',model:'y_s',word:'안',x:1,y:-1});assert.equal(run(p).code,'no_matching_resident');});
test('translated assembly has identical behavior',()=>{const p=ownership('열쇠','안').map(p=>({...p,x:p.x+30,y:p.y-15}));assert.equal(run(p).code,'move');});
test('result inventories are deep copies',()=>{const w=world(),r=run(ownership('열쇠','안'),w);r.world.residents[0].holds.push('책');assert.deepEqual(w,world());});
test('completed goal blocks replay and undo',()=>{const a=run(ownership('책','밖'));const done=run(ownership('열쇠','안'),a.world);assert.equal(run(ownership('열쇠','밖'),done.world).code,'already_complete');});
test('missing destination and floating extra fail',()=>{assert.equal(run(ownership('열쇠','안').filter(p=>p.id!=='destination')).code,'movement_roles');const p=ownership('열쇠','안');p.push({id:'extra',model:'y_e',word:'나',x:9,y:9});assert.equal(run(p).code,'disconnected');});
console.log(count+' tests passed');
