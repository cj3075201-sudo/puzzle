const assert=require('node:assert/strict');
const fs=require('node:fs');const path=require('node:path');const levels=require('./levels.js');const engine=require('./state.js');const core=require('./core.js');const models=JSON.parse(fs.readFileSync(path.join(__dirname,'models.json'),'utf8'));
const copy=x=>JSON.parse(JSON.stringify(x));
const policy=(target,sense='켜짐',action='열다')=>['수리',['말',['문',[action,['때',[target,sense]]]]]];
const move=x=>['수리',['가다',x]];
const bind=x=>['수리',['○',['묶다',x]]];
let checks=0;
function say(s,w,t){const pieces=core.build(t,models,s.blueWords);const a=core.analyze(pieces,models,s.blueWords);assert(a.ok,a.message);const o=s.submit(a.tree,w,'suri');assert(o.ok,o.message);checks++;return o.state;}
function ring(s,w){return s.interact('bell',w).state;}
function all(s,w){for(let i=0;i<4;i++)w=ring(s,w);return w;}
for(const s of levels){let w=copy(s.initial);for(const sol of s.solutions)w=say(s,w,sol.spec);if(s.id===5){w=ring(s,w);w=say(s,w,move('왼쪽'));w=ring(s,w);w=ring(s,w);w=say(s,w,move('오른쪽'));w=ring(s,w);}else w=all(s,w);assert(w.complete,`level ${s.id} representative failed: ${JSON.stringify(w.trace)}`);assert(w.trace.every(x=>x.pass));checks++;}
// Complementing either action or condition is a valid alternate solution, not a string match.
for(const s of levels.slice(0,4)){let w=copy(s.initial);if(s.id===3)w=say(s,w,bind('왼등'));const ref=s.id===3?'○':'왼등';w=say(s,w,policy(ref,s.id===2?'켜짐':'꺼짐','닫다'));assert(all(s,w).complete);checks++;}
// Earlier strategy counterexamples; current-state coincidence cannot complete the trial.
for(const id of [1,2,3,4,5,6]){const s=levels[id-1];assert(!all(s,copy(s.initial)).complete);checks++;}
const five=levels[4];let w=copy(five.initial);w=say(five,w,move('오른쪽'));w=say(five,w,bind('오른등'));w=say(five,w,policy('○'));const fixed=all(five,w);assert(!fixed.complete);assert(fixed.trace.some(t=>!t.known));assert(fixed.trace.filter(t=>!t.known).every(t=>t.actual===false));assert(fixed.trace.some(t=>!t.known&&t.wanted===true));checks++;
let u=five.submit(bind('오른등'),five.initial,'suri');assert(!u.ok);assert.equal(u.state.binding,null);checks++;
// Moving and rebinding keep policy and progress; a new policy starts its own four-state trial.
w=ring(five,w);const oldPolicy=copy(w.policy);let m=say(five,w,move('왼쪽'));assert.equal(m.tick,w.tick);assert.deepEqual(m.policy,oldPolicy);assert.equal(m.binding,'b');checks++;
m=say(five,m,policy('○'));assert.equal(m.tick,-1);assert.equal(m.trace.length,0);assert.equal(m.binding,'b');checks++;
let s=levels[0];w=say(s,copy(s.initial),policy('왼등'));w=ring(s,w);w=say(s,w,['너',['문','열다']]);assert.equal(w.tick,0);assert.deepEqual(w.policy,{target:'왼등',sense:'켜짐',action:'열다'});w=all({...s,interact:s.interact},w);assert(w.complete);checks++;
const saved=copy(levels[2].initial);const failed=levels[2].submit(policy('○'),saved,'other');assert(!failed.ok);assert.deepEqual(saved,levels[2].initial);assert.deepEqual({...failed.state,last:saved.last},saved);checks++;
const mixed=levels[2].submit(['수리',['가다','오른쪽'],['문','열다']],saved,'suri');assert(!mixed.ok);checks++;
for(const l of levels){assert(l.blueWords.includes('열다'));assert(!l.blueWords.includes('문'));assert.deepEqual(JSON.parse(JSON.stringify(l.initial)),l.initial);}checks++;
console.log(`PASS: six representative paths, alternate policies, earlier-strategy failures, unknown perception, policy restart, persistence and jigsaw assembly (${checks} assertions/groups)`);
