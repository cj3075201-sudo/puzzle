'use strict';
const assert=require('node:assert/strict');
const {analyze,evaluate}=require('./core');
const Y=ports=>({color:'yellow',ports}),B=ports=>({color:'blue',ports});
const models={
 y_s:Y([['S','tab','round']]),y_nTab:Y([['N','tab','round']]),
 y_actor:Y([['N','socket','round'],['S','tab','twin']]),
 y_receiver:Y([['S','socket','round'],['E','tab','round']]),
 y_esTwin:Y([['E','tab','round'],['S','tab','twin']]),y_neOut:Y([['N','tab','round'],['E','tab','round']]),
 y_w:Y([['W','socket','round']]),y_eSocket:Y([['E','socket','round']]),y_n:Y([['N','socket','round']]),
 b_we:B([['W','socket','round'],['E','tab','round']]),b_ns:B([['N','socket','round'],['S','tab','round']]),
 b_sw:B([['S','socket','round'],['W','tab','round']]),
 b_give:B([['N','socket','twin'],['W','socket','round'],['S','tab','round']])
};
const world=()=>({residents:[{id:'keeper',location:'inside',holds:['열쇠']},{id:'courier',location:'outside',holds:['책']}],player:{holds:[]},deposited:false,complete:false});
function locationGive(actor,recipient,item){const p=[
 {id:'actor',model:'y_actor',word:actor==='나'?'나':'주민',x:1,y:0},
 {id:'actorPlace',model:'y_s',word:actor,x:1,y:-1},
 {id:'recipient',model:'y_receiver',word:recipient==='나'?'나':'주민',x:0,y:1},
 {id:'recipientPlace',model:'y_nTab',word:recipient,x:0,y:2},
 {id:'give',model:'b_give',word:'주다',x:1,y:1},
 {id:'item',model:'y_n',word:item,x:1,y:2}
];return p.filter(p=>!(actor==='나'&&p.id==='actorPlace')&&!(recipient==='나'&&p.id==='recipientPlace'));}
function ownershipGive(actorItem,recipientItem,item){return [
 {id:'actor',model:'y_esTwin',word:'주민',x:1,y:0},{id:'actorHas',model:'b_we',word:'가지다',x:2,y:0},{id:'actorItem',model:'y_w',word:actorItem,x:3,y:0},
 {id:'recipient',model:'y_neOut',word:'주민',x:0,y:1},{id:'recipientHas',model:'b_sw',word:'가지다',x:0,y:0},{id:'recipientItem',model:'y_eSocket',word:recipientItem,x:-1,y:0},
 {id:'give',model:'b_give',word:'주다',x:1,y:1},{id:'item',model:'y_n',word:item,x:1,y:2}
];}
const run=(p,w=world(),m=models)=>evaluate(p,m,w);
const deposited=()=>run(locationGive('밖','안','책')).world;
let count=0;function test(name,fn){fn();count++;console.log('PASS '+name);}
test('initial book deposit exchanges positions and preserves snapshot',()=>{const w=world(),p=locationGive('밖','안','책'),before=JSON.stringify({w,p}),r=run(p,w);assert.equal(r.code,'exchange_positions');assert.equal(r.actor,'courier');assert.equal(r.recipient,'keeper');assert.equal(r.exchangedPositions,true);assert.equal(r.world.deposited,true);assert.equal(r.world.complete,false);assert.equal(r.world.residents[0].location,'outside');assert.equal(r.world.residents[1].location,'inside');assert.deepEqual(r.world.residents[0].holds,['열쇠','책']);assert.equal(JSON.stringify({w,p}),before);});
test('updated location references give key to courier and complete',()=>{const r=run(locationGive('밖','안','열쇠'),deposited());assert.equal(r.code,'complete');assert.equal(r.target,'courier');assert.equal(r.world.complete,true);assert.deepEqual(r.world.residents[0].holds,['책']);assert.deepEqual(r.world.residents[1].holds,['열쇠']);});
test('key cannot leave keeper before deposit',()=>{const w=world(),r=run(locationGive('안','밖','열쇠'),w);assert.equal(r.code,'deposit_required');assert.equal(r.action,'deposit_required');assert.equal(r.target,'keeper');assert.deepEqual(r.world,w);});
test('possession-conditioned book deposit also exchanges locations',()=>{const r=run(ownershipGive('책','열쇠','책'));assert.equal(r.code,'exchange_positions');assert.equal(r.recipient,'keeper');});
test('book-owner recipient now resolves to same keeper as key-owner actor',()=>{const r=run(ownershipGive('열쇠','책','열쇠'),deposited());assert.equal(r.code,'self_transfer');assert.equal(r.actor,'keeper');assert.equal(r.recipient,'keeper');});
test('both book and key may pass through player',()=>{const a=run(locationGive('밖','나','책'));assert.equal(a.code,'transfer');assert.equal(a.world.deposited,false);const b=run(locationGive('나','안','책'),a.world);assert.equal(b.code,'exchange_positions');const c=run(locationGive('밖','나','열쇠'),b.world);assert.equal(c.code,'transfer');const d=run(locationGive('나','안','열쇠'),c.world);assert.equal(d.code,'complete');assert.deepEqual(d.world.player.holds,[]);});
test('removing deposited book blocks keeper key release again',()=>{const w=run(locationGive('밖','나','책'),deposited()).world;assert.equal(w.deposited,true);const r=run(locationGive('밖','안','열쇠'),w);assert.equal(r.code,'deposit_required');assert.deepEqual(r.world,w);});
test('re-deposit does not replay automatic exchange',()=>{const removed=run(locationGive('밖','나','책'),deposited()).world;const r=run(locationGive('나','밖','책'),removed);assert.equal(r.code,'transfer');assert.equal(r.exchangedPositions,false);assert.equal(r.world.residents[0].location,'outside');assert.equal(r.world.residents[1].location,'inside');});
test('courier key without current deposit is legal transfer but not completion',()=>{const a=run(locationGive('밖','나','열쇠'),deposited());const b=run(locationGive('밖','나','책'),a.world);const c=run(locationGive('나','안','열쇠'),b.world);assert.equal(c.code,'transfer');assert.equal(c.world.complete,false);const d=run(locationGive('나','밖','책'),c.world);assert.equal(d.code,'complete');assert.equal(d.target,'keeper');});
test('missing item and ambiguous resident remain distinct',()=>{const missing=run(locationGive('밖','안','열쇠'));assert.equal(missing.code,'no_item');assert.equal(missing.target,missing.actor);assert.equal(missing.target,'courier');const p=locationGive('밖','안','책').filter(p=>p.id!=='recipientPlace');assert.equal(run(p).code,'ambiguous_resident');});
test('no matching location is rejected',()=>{const w=world();w.residents[0].location='outside';assert.equal(run(locationGive('안','밖','열쇠'),w).code,'no_matching_resident');});
test('movement requests keep waiting residents in place',()=>{const p=[{id:'place',model:'y_s',word:'안',x:0,y:-1},{id:'resident',model:'y_ns',word:'주민',x:0,y:0},{id:'go',model:'b_ns',word:'가다',x:0,y:1},{id:'dest',model:'y_n',word:'밖',x:0,y:2}],m={...models,y_ns:Y([['N','socket','round'],['S','tab','round']])};const r=run(p,world(),m);assert.equal(r.code,'waiting_turn');assert.equal(r.action,'stay');assert.deepEqual(r.world,world());});
test('world result arrays do not alias original state',()=>{const w=world(),r=run(locationGive('밖','안','책'),w);r.world.player.holds.push('책');r.world.residents[0].holds.push('책');assert.deepEqual(w,world());});
test('translated graph retains meaning',()=>{const p=locationGive('밖','안','책').map(p=>({...p,x:p.x-23,y:p.y+11}));assert.equal(run(p).code,'exchange_positions');});
test('completed puzzle blocks further transfers',()=>{const done=run(locationGive('밖','안','열쇠'),deposited()).world;assert.equal(run(locationGive('안','밖','열쇠'),done).code,'already_complete');});
test('missing recipient and floating extra cannot execute',()=>{const p=locationGive('밖','나','책').filter(p=>p.id!=='recipient');assert.equal(run(p).code,'give_roles');const q=locationGive('밖','안','책');q.push({id:'extra',model:'y_s',word:'나',x:8,y:8});assert.equal(run(q).code,'disconnected');});
console.log(count+' tests passed');
