'use strict';
const test = require('node:test');
const assert = require('node:assert/strict');
const toTree = spec => typeof spec === 'string' ? { word: spec, children: [] } : { word: spec[0], children: spec.slice(1).map(toTree) };
const canonical = value => { const t = Array.isArray(value) || typeof value === 'string' ? toTree(value) : value; return JSON.stringify([t.word, ...(t.children || []).map(canonical).sort()]); };
globalThis.JigsawCore = require('./core.js');
const models = require('./models.json');
globalThis.SCENARIOS = [];
require('./scenarios-b.js');
const get = id => SCENARIOS.find(s => s.id === id);
const say = (id, spec, state, listener) => get(id).submit(toTree(spec), state || { ...get(id).initial }, listener || get(id).solutions[0].listener);
for (const s of SCENARIOS) {
  test(`${s.id}: representative solution completes without mandatory inspections`, () => {
    let state = { ...s.initial };
    for (const step of s.solutions) { const before = JSON.stringify(state); const r = s.submit(toTree(step.spec), state, step.listener); assert.equal(JSON.stringify(state), before, 'submit must not mutate input state'); assert.equal(r.ok, true, r.message); state = r.state; }
    assert.equal(state.complete, true);
  });
  test(`${s.id}: all shown and solution words supplied; binary tree; yellow chain ≤3`, () => {
    const vocabulary = new Set(s.words), blue = new Set(s.blueWords);
    for (const w of blue) assert.ok(vocabulary.has(w), w);
    assert.equal(vocabulary.size, s.words.length);
    const visit = (node, run = 0) => { const t = toTree(node); assert.ok(vocabulary.has(t.word), t.word); assert.ok(t.children.length <= 2, t.word); const yellowRun = blue.has(t.word) ? 0 : run + 1; assert.ok(yellowRun <= 3, t.word); for (const child of t.children) visitObject(child, yellowRun); };
    const visitObject = (t, run) => { assert.ok(vocabulary.has(t.word), t.word); assert.ok(t.children.length <= 2); const n = blue.has(t.word) ? 0 : run + 1; assert.ok(n <= 3); for (const c of t.children) visitObject(c,n); };
    for (const a of s.actors) for (const spec of a.speech || []) visit(spec);
    for (const step of s.solutions) visit(step.spec);
  });
  test(`${s.id}: unrelated sentence does not complete`, () => { const r = say(s.id, ['손', '아프다']); assert.equal(r.state.complete, false); });
}
test('7: question scope answers person versus body; cold is not pain', () => {
  let r = say(7, ['질문', ['손', '차갑다']], undefined, 'guide'); assert.equal(r.state.named, true); assert.deepEqual(r.speech, [['수리', ['손', '차갑다']]]);
  r = say(7, ['수리', ['질문', '아프다']], r.state, 'guide'); assert.equal(r.state.located, true); assert.deepEqual(r.speech, [['수리', ['발', '아프다']]]);
  assert.equal(say(7, ['수리', ['손', '아프다']], r.state, 'doctor').ok, false);
  assert.equal(say(7, ['질문', ['수리', '아프다']], r.state, 'guide').ok, false);
});
test('8: negation on selection differs from negation on movement', () => {
  assert.equal(say(8, ['주민', ['손', '차갑다'], ['가다', '다리']]).ok, false);
  assert.equal(say(8, ['주민', ['손', '차갑다'], ['아니다', ['가다', '진료소']]]).ok, false);
  let r = say(8, get(8).solutions[0].spec); assert.equal(r.state.warmSent, true); assert.equal(r.state.coldStopped, false); assert.equal(r.state.complete, false);
  r = say(8, get(8).solutions[0].spec, r.state); assert.equal(r.state.complete, false);
});
test('9: condition and result differ by attachment and preserve subject to action direction', () => {
  assert.equal(say(9, ['수리', ['손', ['움직이다', ['때', ['손', '아프다']]]]]).ok, false);
  assert.equal(say(9, ['모루', ['손', ['아프다', ['때', ['손', '움직이다']]]]]).ok, false);
  const r = say(9, ['수리', ['손', ['아프다', ['때', ['손', '움직이다']]]]]); assert.equal(r.ok, true); assert.equal(r.state.splint, true); assert.equal(r.state.mitten, false);
});
test('10: old testimony does not supply current route', () => {
  let r = say(10, ['질문', ['이전', '길']], undefined, 'guard'); assert.equal(r.ok, true); assert.equal(r.state.learnedNow, false);
  assert.equal(say(10, ['이전', ['서문', '열리다']], r.state, 'porter').ok, false);
  assert.equal(say(10, ['지금', ['서문', '열리다']], r.state, 'porter').ok, false);
});
test('11: source record and current warning are distinct obligations', () => {
  assert.equal(say(11, ['문', '안전하다'], undefined, 'scribe').ok, false);
  assert.equal(say(11, ['말하다', '문지기', ['문', '안전하다']], undefined, 'explorer').ok, false);
  let r = say(11, get(11).solutions[2].spec, undefined, 'explorer'); assert.equal(r.state.warned, true); assert.equal(r.state.complete, false);
  r = say(11, get(11).solutions[0].spec, r.state, 'scribe'); assert.equal(r.state.complete, true);
});
test('12: blocked actions do not change world; preparation unlocks cooperation', () => {
  const s = get(12); let state = { ...s.initial };
  assert.equal(say(12, ['수리', '건너다'], state, 'suri').ok, false);
  assert.equal(say(12, ['모루', ['잡다', '문']], state, 'moru').ok, false);
  const conditional = ['수리', ['건너다', ['때', ['모루', ['잡다', '문']]]]];
  let r = say(12, conditional, state, 'suri'); assert.equal(r.ok, true); assert.equal(r.state.crossed, false);
  assert.equal(say(12, ['수리', ['서다', '발판']], state, 'moru').ok, false);
  for (const step of s.solutions) state = say(12, step.spec, state, step.listener).state;
  assert.equal(state.holding, true); assert.equal(state.onPlate, false); assert.equal(state.crossed, true);
});

for (const s of SCENARIOS) test(`${s.id}: physical jigsaw build/analyze preserves all solutions and NPC speech`, () => {
 const specs = [...s.solutions.map(step => step.spec), ...s.actors.flatMap(a => a.speech || [])];
 for (const spec of specs) { const pieces = JigsawCore.build(spec, models, s.blueWords); const parsed = JigsawCore.analyze(pieces, models, s.blueWords); assert.equal(parsed.ok,true,parsed.message); assert.ok(JigsawCore.eq(parsed.tree,spec)); }
});

test('8/9/12: actions cannot reverse the existing subject to action direction', () => {
 assert.equal(say(8, ['가다', ['주민', ['손', ['아니다', '차갑다']]], '진료소']).ok, false);
 assert.equal(say(9, ['아프다', ['수리', '손'], ['때', ['손', '움직이다']]]).ok, false);
 assert.equal(say(12, ['서다', '수리', '발판'], undefined, 'suri').ok, false);
});
