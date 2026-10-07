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
const world=()=>({residents:[{id:'keeper',location:'inside',holds:['열쇠']},{id:'courier',location:'outside',holds:['책']}],player:{holds:[]},complete:false});
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
let count=0;function test(name,fn){fn();count++;console.log('PASS '+name);}
function transfer(w,actor,recipient,item){const result=run(locationGive(actor,recipient,item),w);assert.equal(result.ok,true);return result;}
function assertConserved(w){assert.deepEqual([...w.player.holds,...w.residents.flatMap(r=>r.holds)].sort(),['열쇠','책'].sort());assert.ok(w.residents.every(r=>r.holds.length<=1));assert.equal(w.residents[0].location,'inside');assert.equal(w.residents[1].location,'outside');}
test('direct transfers in either direction fail on recipient capacity',()=>{for(const [a,r,item,target]of [['안','밖','열쇠','courier'],['밖','안','책','keeper']]){const w=world(),result=run(locationGive(a,r,item),w);assert.equal(result.code,'recipient_full');assert.equal(result.action,'recipient_full');assert.equal(result.target,target);assert.deepEqual(result.world,w);assert.notEqual(result.world,w);assert.deepEqual(w,world());}});
test('key-first three transfers complete',()=>{const a=transfer(world(),'안','나','열쇠');const b=transfer(a.world,'밖','안','책');const c=transfer(b.world,'나','밖','열쇠');assert.equal(a.code,'transfer');assert.equal(b.code,'transfer');assert.equal(c.code,'complete');assert.equal(c.world.complete,true);assert.deepEqual(c.world.residents[0].holds,['책']);assert.deepEqual(c.world.residents[1].holds,['열쇠']);for(const w of [a.world,b.world,c.world])assertConserved(w);});
test('book-first three transfers also complete',()=>{const a=transfer(world(),'밖','나','책');const b=transfer(a.world,'안','밖','열쇠');const c=transfer(b.world,'나','안','책');assert.equal(c.code,'complete');assertConserved(c.world);});
test('player can temporarily hold both items and finish in four transfers',()=>{const a=transfer(world(),'안','나','열쇠');const b=transfer(a.world,'밖','나','책');assert.deepEqual(b.world.player.holds,['열쇠','책']);assert.deepEqual(b.world.residents.map(r=>r.holds),[[],[]]);const c=transfer(b.world,'나','안','책');const d=transfer(c.world,'나','밖','열쇠');assert.equal(d.code,'complete');for(const w of [b.world,c.world,d.world])assertConserved(w);});
test('returning temporary key restores initial state and allows retry',()=>{const a=transfer(world(),'안','나','열쇠');const back=transfer(a.world,'나','안','열쇠');assert.deepEqual(back.world,world());const b=transfer(back.world,'밖','나','책');const c=transfer(b.world,'안','밖','열쇠');assert.equal(transfer(c.world,'나','안','책').code,'complete');});
test('wrong recipient remains full after taking other item',()=>{const a=transfer(world(),'안','나','열쇠');const r=run(locationGive('나','밖','열쇠'),a.world);assert.equal(r.code,'recipient_full');assert.equal(r.target,'courier');assert.deepEqual(r.world,a.world);});
test('self transfer is rejected before capacity check',()=>{const p=locationGive('안','안','열쇠'),r=run(p);assert.equal(r.code,'self_transfer');assert.equal(r.actor,'keeper');assert.equal(r.recipient,'keeper');});
test('no-item reaction targets empty giver rather than occupied receiver',()=>{const r=run(locationGive('안','밖','책'));assert.equal(r.code,'no_item');assert.equal(r.target,'keeper');assert.equal(r.target,r.actor);});
test('ownership references still resolve from current snapshot',()=>{const initial=run(ownershipGive('열쇠','책','열쇠'));assert.equal(initial.code,'recipient_full');assert.equal(initial.actor,'keeper');assert.equal(initial.recipient,'courier');const a=transfer(world(),'안','나','열쇠');const noHolder=run(ownershipGive('열쇠','책','열쇠'),a.world);assert.equal(noHolder.code,'no_matching_resident');});
test('unqualified receiver is not chosen from available capacity',()=>{const a=transfer(world(),'안','나','열쇠');const p=locationGive('나','안','열쇠').filter(p=>p.id!=='recipientPlace');assert.equal(run(p,a.world).code,'ambiguous_resident');});
test('multiple execution verbs cannot create simultaneous swap',()=>{const p=ownershipGive('열쇠','책','열쇠');p.find(p=>p.id==='actorHas').word='주다';assert.equal(run(p).code,'action_count');});
test('inputs and nested inventory arrays are preserved',()=>{const w=world(),p=locationGive('안','나','열쇠'),before=JSON.stringify({w,p}),r=run(p,w);assert.equal(JSON.stringify({w,p}),before);r.world.player.holds.push('책');r.world.residents[0].holds.push('책');assert.deepEqual(w,world());});
test('resident movement requests stay in place',()=>{const p=[{id:'place',model:'y_s',word:'안',x:0,y:-1},{id:'resident',model:'y_ns',word:'주민',x:0,y:0},{id:'go',model:'b_ns',word:'가다',x:0,y:1},{id:'dest',model:'y_n',word:'밖',x:0,y:2}],m={...models,y_ns:Y([['N','socket','round'],['S','tab','round']])};const r=run(p,world(),m);assert.equal(r.code,'waiting_turn');assert.equal(r.action,'stay');assert.deepEqual(r.world,world());});
test('completed exchange blocks replay',()=>{const a=transfer(world(),'안','나','열쇠');const b=transfer(a.world,'밖','안','책');const c=transfer(b.world,'나','밖','열쇠');assert.equal(run(locationGive('안','나','책'),c.world).code,'already_complete');});
test('duplicate or missing items and overfilled resident are invalid states',()=>{for(const mutate of [w=>w.player.holds.push('열쇠'),w=>w.residents[0].holds=[],w=>{w.residents[0].holds.push('책');w.residents[1].holds=[];}]){const w=world();mutate(w);assert.equal(run(locationGive('안','나','열쇠'),w).code,'invalid_world');}});
test('translated physical assembly has same behavior',()=>{const p=locationGive('안','나','열쇠').map(p=>({...p,x:p.x+20,y:p.y-16}));assert.equal(run(p).code,'transfer');});
console.log(count+' tests passed');
