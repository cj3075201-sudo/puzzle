'use strict';
const assert=require('node:assert/strict');
const {analyze,evaluate}=require('./core');
const models={
  actor:{color:'yellow',ports:[['S','tab','twin']]},
  start:{color:'yellow',ports:[['E','tab','round']]},
  middle:{color:'yellow',ports:[['W','socket','round'],['E','tab','round']]},
  item:{color:'yellow',ports:[['W','socket','round']]},
  verb:{color:'blue',ports:[['N','socket','twin'],['W','socket','round'],['E','tab','round']]},
  flat:{color:'yellow',ports:[]}
};
const fixture=()=>[
  {id:'actor',model:'actor',word:'나',x:3,y:1},
  {id:'house',model:'start',word:'집',x:0,y:2},
  {id:'place',model:'middle',word:'안',x:1,y:2},
  {id:'resident',model:'middle',word:'주민',x:2,y:2},
  {id:'give',model:'verb',word:'주다',x:3,y:2},
  {id:'key',model:'item',word:'열쇠',x:4,y:2}
];
const world={keyOwner:'player',complete:false};
let count=0;
function test(name,fn){fn();count++;console.log('PASS '+name);}
const run=p=>evaluate(p,models,world);
test('six pieces complete without input mutations',()=>{
  const p=fixture(), before=JSON.stringify(p), w=JSON.stringify(world),r=run(p);
  assert.equal(r.code,'complete'); assert.equal(r.world.keyOwner,'inside');assert.equal(r.world.complete,true);
  assert.equal(r.edges.length,5);assert.equal(JSON.stringify(p),before);assert.equal(JSON.stringify(world),w);
});
test('translation preserves graph meaning',()=>{const p=fixture().map(p=>({...p,x:p.x-30,y:p.y+51}));assert.equal(run(p).code,'complete');});
test('outside recipient refuses and retains key',()=>{const p=fixture();p[2].word='밖';const r=run(p);assert.equal(r.code,'wrong_target');assert.equal(r.action,'return_key');assert.deepEqual(r.world,world);});
test('reverse actor is determined by twin connection',()=>{
  const reverseModels={...models,actor:{color:'yellow',ports:[['S','tab','round']]},middleTwin:{color:'yellow',ports:[['W','socket','round'],['E','tab','twin']]},verb:{color:'blue',ports:[['N','socket','round'],['W','socket','twin'],['E','tab','round']]}};
  const p=fixture();p[3].model='middleTwin';const r=evaluate(p,reverseModels,world);assert.equal(r.code,'no_item');assert.equal(r.meaning.actor,'inside');assert.equal(r.meaning.recipient,'player');
});
test('four-piece resident remains ambiguous',()=>{const p=fixture().filter(p=>!['house','place'].includes(p.id));assert.equal(run(p).code,'ambiguous_resident');});
test('same person cannot transfer to self',()=>{const p=fixture().filter(p=>!['house','place'].includes(p.id));p.find(p=>p.id==='resident').word='나';assert.equal(run(p).code,'self_transfer');});
test('missing item does not succeed',()=>assert.equal(run(fixture().filter(p=>p.id!=='key')).code,'missing_roles'));
test('empty glyph is rejected',()=>{const p=fixture();p[1].word='';assert.equal(run(p).code,'empty_word');});
test('mismatched connector fails',()=>{const p=fixture();const bad={...models,middle:{color:'yellow',ports:[['W','socket','twin'],['E','tab','round']]}};assert.equal(evaluate(p,bad,world).code,'port_mismatch');});
test('flat neighbors do not connect',()=>{const r=analyze([{id:'a',model:'flat',word:'나',x:0,y:0},{id:'b',model:'flat',word:'주민',x:1,y:0}],models);assert.equal(r.code,'disconnected');assert.deepEqual(r.edges,[]);});
test('four yellow pieces exceed chain limit',()=>{const p=fixture();p[1].model='middle';p.push({id:'extra',model:'start',word:'집',x:-1,y:2});assert.equal(run(p).code,'chain_limit');});
test('model and glyph are independent',()=>{const p=fixture();p[2].word='집';p[1].word='안';assert.equal(run(p).code,'unsupported_meaning');});
test('yellow glyph on blue shape fails',()=>{const p=fixture();p[4].word='주민';assert.equal(run(p).code,'word_color');});
test('overlap fails',()=>{const p=fixture();p[0].x=0;p[0].y=2;assert.equal(run(p).code,'overlap');});
test('empty input fails',()=>assert.equal(run([]).code,'empty'));
test('unconnected remaining ports are allowed',()=>{const spare={...models,start:{color:'yellow',ports:[['E','tab','round'],['N','socket','round']]}};assert.equal(evaluate(fixture(),spare,world).code,'complete');});
test('complete cannot run twice',()=>{const r=run(fixture());assert.equal(evaluate(fixture(),models,r.world).code,'already_complete');});
test('different layout with different shapes keeps meaning',()=>{
  const p=fixture().map(p=>({...p,x:p.y,y:p.x,model:p.model+'_alt'}));
  const swap={N:'W',E:'S',S:'E',W:'N'}, alt={};
  for(const [id,m] of Object.entries(models))alt[id+'_alt']={color:m.color,ports:m.ports.map(([d,t,s])=>[swap[d],t,s])};
  assert.equal(evaluate(p,alt,world).code,'complete');
});
// The real palette is loaded too, so connector changes cannot silently diverge
// between this semantic fixture and the browser's supplied shapes.
const actualModels=require('./모형데이터.json').models;
const actualFixture=()=>[
  {id:'actor',model:'y_twin',word:'나',x:1,y:1},
  {id:'house',model:'y_s',word:'집',x:0,y:0},
  {id:'place',model:'y_ns',word:'안',x:0,y:1},
  {id:'resident',model:'y_ne',word:'주민',x:0,y:2},
  {id:'give',model:'b_give',word:'주다',x:1,y:2},
  {id:'key',model:'y_w',word:'열쇠',x:2,y:2}
];
test('real palette completes then rejects a round actor connector',()=>{
  const p=actualFixture();assert.equal(evaluate(p,actualModels,world).code,'complete');
  p[0].model='y_s';const r=evaluate(p,actualModels,world);
  assert.equal(r.code,'port_mismatch');assert.equal(r.world,undefined);
});
test('moving house-inside chain to item cannot count as identifying recipient',()=>{
  // A permissive extra test shape lets the item carry a chain. Even if supplied
  // later, its location words must never silently identify the resident.
  const p=fixture();
  p[1]={...p[1],model:'middle',x:4,y:2};
  p[2]={...p[2],model:'middle',x:5,y:2};
  p[3]={...p[3],model:'start'};
  p[5]={...p[5],x:6,y:2};
  const r=run(p);assert.equal(r.edges.length,5);
  assert.equal(r.code,'unsupported_meaning');assert.equal(r.world,undefined);
});
test('resident and key role swap is semantically rejected after valid assembly',()=>{
  const p=actualFixture();p[3].word='열쇠';p[5].word='주민';
  const r=evaluate(p,actualModels,world);
  assert.equal(r.edges.length,5);assert.equal(r.code,'unsupported_meaning');assert.equal(r.world,undefined);
});
test('correct assembly plus floating extra cannot succeed',()=>{
  const p=actualFixture();p.push({id:'extra',model:'y_e',word:'나',x:8,y:8});
  const r=evaluate(p,actualModels,world);assert.equal(r.code,'disconnected');assert.equal(r.world,undefined);
});
test('unsupported glyph cannot be interpreted as a known word',()=>{
  const p=actualFixture();p[2].word='안쪽';
  assert.equal(evaluate(p,actualModels,world).code,'word_color');
});
test('duplicate ids cannot overwrite another piece in graph lookup',()=>{
  const p=actualFixture();p[1].id=p[0].id;
  assert.equal(evaluate(p,actualModels,world).code,'invalid_piece');
});
test('outside refusal preserves input and allows correction to inside',()=>{
  const p=actualFixture();p[2].word='밖';const before=JSON.stringify(p);
  const refusal=evaluate(p,actualModels,world);
  assert.equal(refusal.code,'wrong_target');assert.equal(JSON.stringify(p),before);
  assert.deepEqual(refusal.world,world);assert.notEqual(refusal.world,world);
  p[2].word='안';const corrected=evaluate(p,actualModels,refusal.world);
  assert.equal(corrected.code,'complete');assert.equal(corrected.world.keyOwner,'inside');
  assert.deepEqual(refusal.world,world);
});
// User screenshot: the visible single house supplies the reference for 안/밖.
const screenshotFixture=()=>[
  {id:'place',model:'y_s',word:'안',x:2,y:1},
  {id:'actor',model:'y_twin',word:'나',x:3,y:1},
  {id:'resident',model:'y_ne',word:'주민',x:2,y:2},
  {id:'give',model:'b_give',word:'주다',x:3,y:2},
  {id:'key',model:'y_w',word:'열쇠',x:4,y:2}
];
test('user screenshot five-piece contextual inside resident succeeds',()=>{
  const r=evaluate(screenshotFixture(),actualModels,world);
  assert.equal(r.code,'complete');assert.equal(r.meaning.recipient,'inside');
  assert.deepEqual(r.meaning.chains.recipient,['안','주민']);
  assert.equal(r.world.keyOwner,'inside');
});
test('five-piece outside resident is understood then refuses',()=>{
  const p=screenshotFixture();p[0].word='밖';const r=evaluate(p,actualModels,world);
  assert.equal(r.code,'wrong_target');assert.equal(r.meaning.recipient,'outside');assert.deepEqual(r.world,world);
});
test('contextual short chain works for giver without reversing ownership',()=>{
  const p=[
    {id:'place',model:'y_s',word:'안',x:1,y:0},
    {id:'actor',model:'y_ntwin',word:'주민',x:1,y:1},
    {id:'recipient',model:'y_e',word:'나',x:0,y:2},
    {id:'give',model:'b_give',word:'주다',x:1,y:2},
    {id:'key',model:'y_w',word:'열쇠',x:2,y:2}
  ];
  const r=evaluate(p,actualModels,world);assert.equal(r.code,'no_item');assert.equal(r.meaning.actor,'inside');assert.equal(r.meaning.recipient,'player');
});
test('short chain preserves word order instead of searching keywords',()=>{
  const p=screenshotFixture();p[0].word='주민';p[2].word='안';
  assert.equal(evaluate(p,actualModels,world).code,'unsupported_meaning');
});
test('both full and short location chains denote the same receiver',()=>{
  for(const word of ['안','밖']){
    const a=actualFixture(),b=screenshotFixture();a.find(p=>p.id==='place').word=word;b[0].word=word;
    const ra=evaluate(a,actualModels,world),rb=evaluate(b,actualModels,world);
    assert.equal(ra.code,rb.code);assert.equal(ra.meaning.recipient,rb.meaning.recipient);
  }
});

console.log(count+' tests passed');
