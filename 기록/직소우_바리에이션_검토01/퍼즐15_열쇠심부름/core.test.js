'use strict';
const assert=require('node:assert/strict');
const {analyze,evaluate}=require('./core');
const Y=ports=>({color:'yellow',ports}),B=ports=>({color:'blue',ports});
const models={
 y_es:Y([['E','tab','round'],['S','tab','round']]),
 y_esTwin:Y([['E','tab','round'],['S','tab','twin']]),
 y_neOut:Y([['N','tab','round'],['E','tab','round']]),
 y_w:Y([['W','socket','round']]),y_eSocket:Y([['E','socket','round']]),y_n:Y([['N','socket','round']]),
 y_e:Y([['E','tab','round']]),y_nw:Y([['N','socket','round'],['W','socket','round']]),
 y_ne:Y([['N','socket','round'],['E','tab','round']]),
 b_we:B([['W','socket','round'],['E','tab','round']]),b_ns:B([['N','socket','round'],['S','tab','round']]),
 b_sw:B([['S','socket','round'],['W','tab','round']]),
 b_give:B([['N','socket','twin'],['W','socket','round'],['S','tab','round']])
};
const world=()=>({residents:[{id:'keeper',location:'outside',holds:['열쇠']},{id:'courier',location:'outside',holds:['책']}],player:{holds:[]},complete:false});
const give=()=>[
 {id:'actor',model:'y_esTwin',word:'주민',x:1,y:0},
 {id:'actorHas',model:'b_we',word:'가지다',x:2,y:0},
 {id:'actorItem',model:'y_w',word:'열쇠',x:3,y:0},
 {id:'receiver',model:'y_neOut',word:'주민',x:0,y:1},
 {id:'receiverHas',model:'b_sw',word:'가지다',x:0,y:0},
 {id:'receiverItem',model:'y_eSocket',word:'책',x:-1,y:0},
 {id:'give',model:'b_give',word:'주다',x:1,y:1},
 {id:'item',model:'y_n',word:'열쇠',x:1,y:2}
];
const go=(item='열쇠')=>[
 {id:'actor',model:'y_es',word:'주민',x:1,y:0},
 {id:'has',model:'b_we',word:'가지다',x:2,y:0},
 {id:'heldItem',model:'y_w',word:item,x:3,y:0},
 {id:'go',model:'b_ns',word:'가다',x:1,y:1},
 {id:'destination',model:'y_n',word:'안',x:1,y:2}
];
const withoutCondition=(p,role)=>p.filter(p=>![(role==='actor'?'actor':'receiver')+'Has',(role==='actor'?'actor':'receiver')+'Item'].includes(p.id));
const run=(p,w=world(),m=models)=>evaluate(p,m,w);
let count=0;function test(name,fn){fn();count++;console.log('PASS '+name);}
test('both conditioned references transfer using snapshot and preserve books',()=>{
 const w=world(),p=give(),before=JSON.stringify({w,p}),r=run(p,w);
 assert.equal(r.code,'transfer');assert.equal(r.actor,'keeper');assert.equal(r.recipient,'courier');assert.equal(r.item,'열쇠');
 assert.deepEqual(r.world.residents[0].holds,[]);assert.deepEqual(r.world.residents[1].holds,['책','열쇠']);assert.equal(r.world.complete,false);assert.equal(JSON.stringify({w,p}),before);
});
test('same go utterance refers to keeper before transfer and courier after',()=>{
 const p=go(),before=run(p);assert.equal(before.code,'lever_return');assert.equal(before.target,'keeper');assert.deepEqual(before.world,world());
 const transferred=run(give()),after=run(p,transferred.world);assert.equal(after.code,'complete');assert.equal(after.target,'courier');assert.equal(after.world.residents[1].location,'inside');
});
test('player can receive then deliver using separate physical assemblies',()=>{
 let first=withoutCondition(give(),'receiver');first.find(p=>p.id==='receiver').word='나';
 const a=run(first);assert.equal(a.code,'transfer');assert.equal(a.recipient,'player');assert.deepEqual(a.world.player.holds,['열쇠']);
 let second=withoutCondition(give(),'actor');second.find(p=>p.id==='actor').word='나';
 const b=run(second,a.world);assert.equal(b.code,'transfer');assert.equal(b.actor,'player');assert.equal(b.recipient,'courier');assert.deepEqual(b.world.player.holds,[]);assert.deepEqual(b.world.residents[1].holds,['책','열쇠']);assert.equal(run(go(),b.world).code,'complete');
});
test('reverse giver with no requested item fails',()=>{const p=give();p.find(p=>p.id==='actorItem').word='책';p.find(p=>p.id==='receiverItem').word='열쇠';assert.equal(run(p).code,'no_item');});
test('unqualified receiver remains ambiguous',()=>assert.equal(run(withoutCondition(give(),'receiver')).code,'ambiguous_resident'));
test('unqualified actor remains ambiguous',()=>assert.equal(run(withoutCondition(give(),'actor')).code,'ambiguous_resident'));
test('same resolved entity cannot transfer to itself',()=>{const p=give();p.find(p=>p.id==='receiverItem').word='열쇠';assert.equal(run(p).code,'self_transfer');});
test('book is transferable too and key remains with keeper',()=>{const p=give();p.find(p=>p.id==='actorItem').word='책';p.find(p=>p.id==='receiverItem').word='열쇠';p.find(p=>p.id==='item').word='책';const r=run(p);assert.equal(r.code,'transfer');assert.deepEqual(r.world.residents[0].holds,['열쇠','책']);assert.deepEqual(r.world.residents[1].holds,[]);});
test('courier without key visits then returns',()=>{const r=run(go('책'));assert.equal(r.code,'visit_return');assert.equal(r.target,'courier');assert.deepEqual(r.world,world());});
test('empty player cannot supply a key',()=>{const p=withoutCondition(give(),'actor');p.find(p=>p.id==='actor').word='나';assert.equal(run(p).code,'no_item');});
test('player movement is rejected',()=>{const p=go().filter(p=>!['has','heldItem'].includes(p.id));p[0].word='나';assert.equal(run(p).code,'wrong_mover');});
test('outside destination does not move already outside resident',()=>{const p=go();p[4].word='밖';assert.equal(run(p).code,'already_there');});
test('conditions only are not executed',()=>{const p=go().filter(p=>['actor','has','heldItem'].includes(p.id));assert.equal(run(p).code,'action_count');});
test('two execution verbs cannot be bundled',()=>{const p=give();p.find(p=>p.id==='actorHas').word='가다';assert.equal(run(p).code,'action_count');});
test('round actor cannot fit twin give socket',()=>{const p=give();p[0].model='y_es';assert.equal(run(p).code,'port_mismatch');});
test('separate graph pieces are not ignored',()=>{const p=give();p.push({id:'extra',model:'y_e',word:'나',x:9,y:9});assert.equal(run(p).code,'disconnected');});
test('translation changes no meaning',()=>{const p=give().map(p=>({...p,x:p.x+40,y:p.y-22}));assert.equal(run(p).code,'transfer');});
test('full destination with incoming house modifier is supported',()=>{const p=go();p[4].model='y_nw';p.push({id:'house',model:'y_e',word:'집',x:0,y:2});const after=run(give()).world;assert.equal(run(p,after).code,'complete');});
test('destination can be entered through house then inside',()=>{const p=go();p[4]={...p[4],model:'y_ne',word:'집'};p.push({id:'inside',model:'y_w',word:'안',x:2,y:2});assert.equal(run(p,run(give()).world).code,'complete');});
test('completion locks subsequent actions',()=>{const w=run(go(),run(give()).world).world;assert.equal(run(give(),w).code,'already_complete');});
test('missing object and empty glyph are rejected',()=>{assert.equal(run(give().filter(p=>p.id!=='item')).code,'give_roles');const p=give();p[0].word='';assert.equal(run(p).code,'empty_word');});
test('possession belonging to a separate noun cannot filter mover',()=>{
 const p=go();p[2].model='y_nw';p.push({id:'other',model:'y_s',word:'주민',x:3,y:-2},{id:'otherHas',model:'b_ns',word:'가지다',x:3,y:-1});
 const m={...models,y_s:Y([['S','tab','round']])};assert.equal(run(p,world(),m).code,'unrelated_condition');
});
test('zero or two holders resolve against current snapshot',()=>{
 const w=world();w.residents[0].holds=[];assert.equal(run(go(),w).code,'no_matching_resident');
 w.residents[0].holds=['열쇠'];w.residents[1].holds.push('열쇠');assert.equal(run(go(),w).code,'ambiguous_resident');
});
test('overlap and duplicate ids cannot bypass graph lookup',()=>{
 const p=give();p[1].x=1;assert.equal(run(p).code,'overlap');
 const q=give();q[1].id=q[0].id;assert.equal(run(q).code,'invalid_piece');
});
console.log(count+' tests passed');
