'use strict';
const {test}=require('node:test'),assert=require('node:assert/strict');
const P=require('./state.js'),Core=require('./core.js'),Models=require('./models.json');
const move=(selector,direction)=>['주민',['옮기다',['글자',selector],direction]];
const rootDown=move('주민','아래');
const bottomLeft=move(['아래','문'],'왼쪽');
function send(s,t){const r=P.submit(s,t);assert.equal(r.ok,true,r.message);return r;}
test('initial geometry has valid separate components and reads close door',()=>{const s=P.initial(),r=P.read(s);assert.equal(r.ok,true);assert(Core.eq(r.tree,['주민',['닫다','문']]));assert.equal(Core.analyze(s.board,Models,P.BLUE_WORDS).code,'disconnected');});
test('direct open is immediately followed by resident board close',()=>{const r=send(P.initial(),['주민',['열다','문']]);assert.equal(r.state.world.doorOpen,false);assert.deepEqual(r.events.map(e=>e.open),[true,false]);});
test('physical box and written word have distinct targets',()=>{const r=send(P.initial(),['주민',['옮기다','상자','오른쪽']]);assert.equal(r.state.world.box.x,2);assert.equal(r.state.board[0].x,0);});
test('same-word selector ambiguity returns actionable feedback',()=>{const r=P.submit(P.initial(),move('문','왼쪽'));assert.equal(r.ok,false);assert.match(r.message,/2개/);assert.equal(r.state.turn,0);});
test('quoted resident is excluded from referents',()=>{const r=P.selectWord(P.initial(),'주민');assert.equal(r.ok,true);assert.equal(r.piece.id,'reader');});
test('bottom modifier selects real lower door',()=>{const r=P.selectWord(P.initial(),['아래','문']);assert.equal(r.piece.id,'bottom-door');});
test('physical socket mismatch is rejected',()=>{const s=P.initial();s.board.find(p=>p.id==='bottom-door').x=5;const r=P.submit(s,move(['아래','문'],'위'));assert.equal(r.ok,false);assert.match(r.message,/조각이 맞물리지/);});
test('move to occupied destination does not mutate state',()=>{const s=P.initial(),before=JSON.stringify(s),r=P.submit(s,move('주민','오른쪽'));assert.equal(r.ok,false);assert.equal(JSON.stringify(s),before);});
test('board edges reject leaving grid',()=>{const r=P.submit(P.initial(),move('주민','왼쪽'));assert.equal(r.ok,false);assert.match(r.message,/판 밖/);});
test('first reader move breaks closing instruction but does not win',()=>{const r=send(P.initial(),rootDown);assert.equal(r.state.board.find(p=>p.id==='reader').y,1);assert.equal(r.state.world.doorOpen,false);assert.equal(P.exit(r.state).ok,false);});
test('one-off opening with disconnected board cannot bypass exit',()=>{let s=send(P.initial(),rootDown).state;s=send(s,['주민',['열다','문']]).state;assert.equal(s.world.doorOpen,true);const r=P.exit(s);assert.equal(r.ok,false);assert.equal(r.state.world.doorOpen,false);assert.equal(r.state.complete,false);});
test('complete intended path self-modifies exact live board and then opens',()=>{let s=P.initial();s=send(s,bottomLeft).state;s=send(s,rootDown).state;const r=send(s,rootDown);assert.equal(r.state.world.doorOpen,true);assert.equal(r.state.selfEdits,1);assert.equal(r.state.board.find(p=>p.id==='reader').y,3);assert.deepEqual(r.events.map(e=>e.source),['player','board','board']);assert(Core.eq(P.read(r.state).tree,['주민',['열다','문']]));const end=P.exit(r.state);assert.equal(end.ok,true);assert.equal(end.state.complete,true);});
test('dormant fragment is not executed before root connects',()=>{const r=P.tick(P.initial());assert.equal(r.state.selfEdits,0);assert.equal(r.state.world.doorOpen,false);});
test('unprepared lower door makes final read incomplete',()=>{let s=send(P.initial(),rootDown).state;const r=send(s,rootDown);assert.equal(r.state.selfEdits,1);assert.equal(r.state.world.doorOpen,false);assert.equal(P.exit(r.state).ok,false);});
test('can repair after activating: no mandatory ordering gate',()=>{let s=send(P.initial(),rootDown).state;s=send(s,rootDown).state;s=send(s,bottomLeft).state;assert.equal(P.exit(s).ok,true);});
test('alternate valid upper opening arrangement is accepted, no fixed layout check',()=>{const s=P.initial();s.board.find(p=>p.id==='close').word='열다';const r=P.exit(s);assert.equal(r.ok,true);assert.equal(r.state.selfEdits,0);});
test('state and all nested data remain immutable across submissions',()=>{const s=P.initial(),before=JSON.stringify(s);send(s,bottomLeft);assert.equal(JSON.stringify(s),before);});
test('nested direction syntax equals sibling syntax',()=>{const a=send(P.initial(),rootDown),b=send(P.initial(),['주민',['옮기다',['아래',['글자','주민']]]]);assert.deepEqual(a.state,b.state);});
test('own instruction malformed extra branch is rejected',()=>{const r=P.submit(P.initial(),['주민',['열다','문'],'상자']);assert.equal(r.ok,false);});
test('all sample player trees can be constructed with existing real jigsaw models',()=>{for(const t of [rootDown,bottomLeft,['주민',['열다','문']],['주민',['옮기다','상자','오른쪽']]]){const board=Core.build(t,Models,P.BLUE_WORDS),r=Core.analyze(board,Models,P.BLUE_WORDS);assert.equal(r.ok,true);assert(Core.eq(r.tree,t));}});

test('quote operator tile itself remains a movable word',()=>{const r=P.selectWord(P.initial(),'글자');assert.equal(r.ok,true);assert.equal(r.piece.id,'quote');});

test('quoted ids track current geometry after quote operator moves',()=>{
 const before=P.initial();
 assert.deepEqual([...P.quotedIds(before)],['quoted-resident']);
 const moved=send(before,move('글자','위')).state;
 assert.equal(P.quotedIds(moved).size,0);
 const ambiguous=P.selectWord(moved,'주민');
 assert.equal(ambiguous.ok,false);assert.match(ambiguous.message,/2개/);
 const upper=P.selectWord(moved,['위','주민']);
 assert.equal(upper.ok,true);assert.equal(upper.piece.id,'reader');
 const lower=P.selectWord(moved,['아래','주민']);
 assert.equal(lower.ok,true);assert.equal(lower.piece.id,'quoted-resident');
});
test('restoring quote operator restores reference exclusion',()=>{
 let s=send(P.initial(),move('글자','위')).state;
 s=send(s,move('글자','아래')).state;
 assert.deepEqual([...P.quotedIds(s)],['quoted-resident']);
 const picked=P.selectWord(s,'주민');
 assert.equal(picked.ok,true);assert.equal(picked.piece.id,'reader');
});
