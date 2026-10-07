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
const world=()=>({residents:[{id:'keeper',location:'inside',holds:['열쇠']},{id:'courier',location:'outside',holds:['책']},{id:'lamplighter',location:'outside',holds:['등']}],player:{holds:[]},complete:false});
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
models.y_n_esTwin=Y([['N','socket','round'],['E','tab','round'],['S','tab','twin']]);
models.y_ns_e=Y([['N','tab','round'],['S','socket','round'],['E','tab','round']]);
models.y_es=Y([['E','tab','round'],['S','tab','round']]);
models.y_nes=Y([['N','socket','round'],['E','tab','round'],['S','tab','round']]);
function give(actor,recipient,item){
 let p=locationGive(typeof actor==='string'?actor:actor.location||'안',typeof recipient==='string'?recipient:recipient.location||'안',item);
 for(const [ref,role]of [[actor,'actor'],[recipient,'recipient']])if(typeof ref==='object'){
  if(!ref.location)p=p.filter(piece=>piece.id!==role+'Place');
  p.find(piece=>piece.id===role).model=role==='actor'?(ref.location?'y_n_esTwin':'y_esTwin'):(ref.location?'y_ns_e':'y_neOut');
  const x=role==='actor'?2:0,y=0;
  p.push({id:role+'Has',model:role==='actor'?'b_we':'b_sw',word:'가지다',x,y},{id:role+'Item',model:role==='actor'?'y_w':'y_eSocket',word:ref.holds,x:role==='actor'?3:-1,y});
 }
 return p;
}
function go(item,destination='안',location){const p=[
 {id:'resident',model:location?'y_nes':'y_es',word:'주민',x:1,y:0},{id:'has',model:'b_we',word:'가지다',x:2,y:0},{id:'item',model:'y_w',word:item,x:3,y:0},{id:'go',model:'b_ns',word:'가다',x:1,y:1},{id:'dest',model:'y_n',word:destination,x:1,y:2}];if(location)p.push({id:'location',model:'y_s',word:location,x:1,y:-1});return p;}
function act(w,p,code){const r=run(p,w);assert.equal(r.code,code);return r.world;}
let count=0;function test(name,fn){fn();count++;console.log('PASS '+name);}
test('four actions solve by transferring then relocating lamp holder',()=>{let w=world();w=act(w,give('안','나','열쇠'),'transfer');w=act(w,give({holds:'책'},'안','책'),'transfer');w=act(w,go('등'),'move');w=act(w,give('나','밖','열쇠'),'complete');assert.equal(w.complete,true);assert.deepEqual(w.residents.map(r=>r.holds),[['책'],['열쇠'],['등']]);assert.deepEqual(w.player.holds,[]);});
test('initial outside residents are ambiguous but book holder is unique',()=>{assert.equal(run(give('밖','나','책')).code,'ambiguous_resident');const r=run(give({holds:'책'},'나','책'));assert.equal(r.code,'transfer');assert.equal(r.actor,'courier');});
test('after book leaves courier outside cannot be inferred from free capacity',()=>{let w=act(world(),give('안','나','열쇠'),'transfer');w=act(w,give({holds:'책'},'안','책'),'transfer');const r=run(give('나','밖','열쇠'),w);assert.equal(r.code,'ambiguous_resident');assert.equal(r.world,undefined);});
test('stale book-holder recipient now refers to occupied keeper',()=>{let w=act(world(),give('안','나','열쇠'),'transfer');w=act(w,give({holds:'책'},'안','책'),'transfer');const r=run(give('나',{holds:'책'},'열쇠'),w);assert.equal(r.code,'recipient_full');assert.equal(r.target,'keeper');});
test('moving lamp holder makes empty courier uniquely outside',()=>{const w=act(world(),go('등'),'move');assert.equal(w.residents[2].location,'inside');const r=run(give('밖','나','책'),w);assert.equal(r.code,'transfer');assert.equal(r.actor,'courier');});
test('early movement creates inside ambiguity and can be reversed',()=>{const w=act(world(),go('등'),'move');assert.equal(run(give('안','나','열쇠'),w).code,'ambiguous_resident');const back=act(w,go('등','밖'),'move');assert.deepEqual(back,world());});
test('book-first route succeeds without prescribed action count',()=>{let w=act(world(),give({holds:'책'},'나','책'),'transfer');w=act(w,go('등'),'move');w=act(w,give({holds:'열쇠'},'밖','열쇠'),'transfer');assert.equal(run(give('나','안','책'),w).code,'ambiguous_resident');w=act(w,go('등','밖'),'move');w=act(w,give('나','안','책'),'complete');assert.equal(w.complete,true);});
test('lamp identifies holder but cannot be transferred',()=>{const r=run(give({holds:'등'},'나','등'));assert.equal(r.code,'fixed_item');assert.equal(r.action,'fixed_item');assert.equal(r.target,'lamplighter');assert.deepEqual(r.world,world());});
test('lamp and location constraints both apply',()=>{assert.equal(run(go('등','안','안')).code,'no_matching_resident');assert.equal(run(go('등','안','밖')).code,'move');});
test('already-there request does not move lamp',()=>{const r=run(go('등','밖'));assert.equal(r.code,'already_there');assert.equal(r.target,'lamplighter');});
test('keeper and courier may move just like lamp holder',()=>{const k=run(go('열쇠','밖'));assert.equal(k.code,'move');assert.equal(k.target,'keeper');const c=run(go('책','안'));assert.equal(c.code,'move');assert.equal(c.target,'courier');});
test('goal permits keeper outside and courier inside',()=>{let w=world();w.residents[0].location='outside';w.residents[1].location='inside';w=act(w,give({holds:'열쇠'},'나','열쇠'),'transfer');w=act(w,go('등'),'move');w=act(w,give({holds:'책'},'밖','책'),'transfer');w=act(w,go('등','밖'),'move');w=act(w,give('나','안','열쇠'),'complete');assert.equal(w.residents[0].location,'outside');assert.equal(w.residents[1].location,'inside');assert.equal(run(go('등'),w).code,'already_complete');});
test('inputs and nested arrays stay unchanged',()=>{const w=world(),p=give('안','나','열쇠'),before=JSON.stringify({w,p}),r=run(p,w);assert.equal(JSON.stringify({w,p}),before);r.world.player.holds.push('책');r.world.residents[2].holds.push('책');assert.deepEqual(w,world());});
test('no-item reaction targets giver',()=>{const r=run(give('안','나','책'));assert.equal(r.code,'no_item');assert.equal(r.target,'keeper');});
test('unfinished transfers can be undone',()=>{const w=act(world(),give('안','나','열쇠'),'transfer');assert.deepEqual(act(w,give('나','안','열쇠'),'transfer'),world());});
test('simultaneous actions and unused pieces are rejected',()=>{const p=ownershipGive('열쇠','책','열쇠');p.find(p=>p.id==='actorHas').word='가다';assert.equal(run(p).code,'action_count');const q=give('안','나','열쇠');q.push({id:'extra',model:'y_s',word:'나',x:9,y:9});assert.equal(run(q).code,'disconnected');});
test('translated assembly preserves target and transfer',()=>{const p=give({holds:'책'},'나','책').map(p=>({...p,x:p.x+15,y:p.y-20}));const r=run(p);assert.equal(r.code,'transfer');assert.equal(r.actor,'courier');});
console.log(count+' tests passed');
