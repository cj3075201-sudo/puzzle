'use strict';
const assert=require('node:assert/strict');
const tree=s=>typeof s==='string'?{word:s,children:[]}:{word:s[0],children:s.slice(1).map(tree)};
const canon=t=>JSON.stringify([t.word,...t.children.map(canon).sort()]);
globalThis.JigsawCore={eq:(t,s)=>canon(t)===canon(tree(s))};
const scenes=require('./scenarios-a.js');
let checks=0;
function check(c,msg){assert.ok(c,msg);checks++}
function run(scene,spec,state,listener){return scene.submit(tree(spec),state,listener)}
for(const scene of scenes){
 let s=structuredClone(scene.initial);
 for(const a of scene.actors){const r=scene.inspect(a.id,s);check(!r.state.complete,`inspection cannot solve ${scene.id}`);check(JSON.stringify(s)===JSON.stringify(scene.initial),`inspect pure ${scene.id}`)}
 for(const step of scene.solutions){const old=JSON.stringify(s),r=run(scene,step.spec,s,step.listener);check(r.ok,`${scene.id} representative accepted`);check(JSON.stringify(s)===old,`${scene.id} input not mutated`);s=r.state}
 check(s.complete,`${scene.id} representative complete`);
 const bad=run(scene,['나','차갑다'],scene.initial,scene.actors.at(-1).id);check(!bad.state.complete,`${scene.id} unrelated cannot complete`);
 const specs=[...scene.actors.flatMap(a=>a.speech),...scene.solutions.map(s=>s.spec),...(scene.starter?[scene.starter]:[])];
 for(const spec of specs){const walk=(t,yellow=0)=>{check(scene.words.includes(t.word),`${scene.id} known word ${t.word}`);const chain=scene.blueWords.includes(t.word)?0:yellow+1;check(chain<=3,`${scene.id} yellow chain`);check(t.children.length<=2,`${scene.id} max branch`);t.children.forEach(c=>walk(c,chain))};walk(tree(spec))}
}
let s=scenes[0].initial;const p=scenes[0].solutions[0];s=run(scenes[0],p.spec,s,p.listener).state;s=run(scenes[0],p.spec,s,p.listener).state;check(!s.complete&&s.reported.length===1,'duplicate report does not finish 1');
check(!run(scenes[0],['나',['손','차갑다']],scenes[0].initial,'doctor').state.complete,'speaker perspective matters');
check(!run(scenes[1],['주민',['가지다','책'],['가다','문']],scenes[1].initial,'guard').state.complete,'audience cannot use hidden possession');
check(!run(scenes[2],scenes[2].actors[0].speech[0],scenes[2].initial,'mechanic').state.complete,'single witness copying insufficient');
check(!run(scenes[3],scenes[3].starter,scenes[3].initial,'messenger').state.complete,'incorrect relay rejected');
check(!run(scenes[4],['주민',['손','차갑다']],scenes[4].initial,'doctor').state.complete,'one condition ambiguous');
const swapped=['주민',['발','아프다'],['손','차갑다']];check(run(scenes[4],swapped,scenes[4].initial,'doctor').state.complete,'branch order irrelevant');
s=run(scenes[5],scenes[5].solutions[0].spec,scenes[5].initial,'expert').state;s=run(scenes[5],scenes[5].solutions[0].spec,s,'expert').state;check(!s.complete,'repeat observation is not requested change');
check(!run(scenes[5],['손','따뜻하다'],scenes[5].initial,'expert').state.complete,'expert needs observed condition');
check(run(scenes[5],['손','따뜻하다'],s,'expert').state.complete,'context permits short equivalent request');
check(run(scenes[1],['안',['주민',['가지다','책'],['가다','문']]],scenes[1].initial,'guard').state.complete,'visible location still works with true possession qualifier');
for(const report of [['주민',['손','차갑다'],['발','따뜻하다']],['안',['주민',['손','차갑다'],['발','따뜻하다']]]]){
 const r=run(scenes[5],report,scenes[5].initial,'expert');check(r.ok&&r.state.reported&&!r.state.complete,'full truthful report is understood');
 check(run(scenes[5],['손','따뜻하다'],r.state,'expert').state.complete,'full report continues to hand request');
 const repeated=run(scenes[5],report,r.state,'expert');check(!repeated.state.complete,'repeating whole report cannot complete');
}
check(!run(scenes[5],['주민',['손','차갑다'],['발','차갑다']],scenes[5].initial,'expert').state.reported,'contradictory extra information is not accepted');
check(run(scenes[5],['주민',['손','따뜻하다'],['발','따뜻하다']],s,'expert').state.complete,'already warm feet may be retained in desired state');
console.log(`Scenarios 1-6: ${checks} assertions passed`);
