(function(root,factory){const api=factory();if(typeof module==='object'&&module.exports)module.exports=api;root.PurplePuzzle=api;})(typeof globalThis!=='undefined'?globalThis:this,function(){
  'use strict';
  const purple=['○','△','◇'], observations=['가지다','보다','내다'], actions=['열다','돕다'];
  const people=[{id:'a',label:'왼쪽 주민',type:'person'},{id:'b',label:'가운데 주민',type:'person'},{id:'c',label:'오른쪽 주민',type:'person'}];
  const levels=[
    {id:0,title:'같은 표식, 같은 대상',goal:'열쇠를 가진 주민에게 소리 나는 문을 열어 달라고 하세요.',entities:[...people,{id:'d1',label:'왼쪽 문',type:'door'},{id:'d2',label:'가운데 문',type:'door'},{id:'d3',label:'오른쪽 문',type:'door'},{id:'key',label:'열쇠',type:'thing'},{id:'sound',label:'소리',type:'thing'}],facts:[['가지다','a','key'],['가지다','b','key'],['보다','a','d1'],['보다','b','d2'],['보다','c','d2'],['내다','d2','sound'],['내다','d3','sound']]},
    {id:1,title:'서로를 찾는 말',goal:'열쇠를 가진 주민과 서로 바라보는 주민이 함께 문을 열게 하세요.',entities:[...people,{id:'key',label:'열쇠',type:'thing'}],facts:[['가지다','a','key'],['가지다','b','key'],['보다','a','c'],['보다','b','c'],['보다','c','b']]}
  ];
  function initial(level=0){return {level:Number.isInteger(level)&&levels[level]?level:0,complete:false,turn:0,last:null};}
  function info(state){return levels[state&&Number.isInteger(state.level)?state.level:0]||levels[0];}
  function normalize(tree){if(typeof tree==='string')return {word:tree,children:[]};if(Array.isArray(tree)){if(!tree.length)return null;return {word:tree[0],children:tree.slice(1).map(normalize)};}if(!tree||typeof tree.word!=='string'||(tree.children!==undefined&&!Array.isArray(tree.children)))return null;return {word:tree.word,children:(tree.children||[]).map(normalize)};}
  function parse(tree,index){const t=normalize(tree);if(!t||t.children.length!==1||!t.children[0])return {error:`${index+1}번째 말은 대상 → 행동 → 대상 세 조각으로 연결해 주세요.`};const v=t.children[0],o=v.children[0];if(v.children.length!==1||!o||o.children.length)return {error:`${index+1}번째 말은 대상 → 행동 → 대상 세 조각으로 연결해 주세요.`};if(!observations.includes(v.word)&&!actions.includes(v.word))return {error:`‘${v.word}’는 이 방에서 사용하는 행동이 아니에요.`};return {index,subject:t.word,verb:v.word,object:o.word,kind:actions.includes(v.word)?'action':'fact'};}
  function domain(word,level,binding){if(purple.includes(word))return binding[word]?[binding[word]]:[];if(word==='주민')return level.entities.filter(e=>e.type==='person').map(e=>e.id);if(word==='문')return level.entities.filter(e=>e.type==='door').map(e=>e.id);if(word==='열쇠')return level.entities.some(e=>e.id==='key')?['key']:[];if(word==='소리')return level.entities.some(e=>e.id==='sound')?['sound']:[];return [];}
  function has(level,verb,a,b){return level.facts.some(f=>f[0]===verb&&f[1]===a&&f[2]===b);}
  function matches(row,level,binding){return domain(row.subject,level,binding).some(a=>domain(row.object,level,binding).some(b=>has(level,row.verb,a,b)));}
  function solve(trees,state){
    const level=info(state),base={ok:false,bindings:[],candidates:{},actionPairs:[],rows:[],vars:[],code:'invalid',message:''};
    const fail=(message,code='invalid')=>Object.assign(base,{message,code});
    if(!Array.isArray(trees)||trees.length===0)return fail('연결한 말을 먼저 놓아 주세요.','empty');
    if(trees.length>6)return fail('이번 부탁판에는 여섯 문장까지 함께 놓을 수 있어요.');
    const rows=trees.map(parse);for(const r of rows)if(r.error)return fail(r.error);
    const validNouns=[...purple,'주민','문','열쇠','소리'];
    for(const r of rows)for(const word of [r.subject,r.object])if(!validNouns.includes(word))return fail(`‘${word}’ 대신 노란 뜻이나 보라 표식을 대상 자리에 놓아 주세요.`);
    base.rows=rows.map(r=>({...r,ok:null}));
    const vars=[...new Set(rows.flatMap(r=>[r.subject,r.object]).filter(w=>purple.includes(w)))];base.vars=vars;vars.forEach(v=>base.candidates[v]=[]);
    const facts=rows.filter(r=>r.kind==='fact'),commands=rows.filter(r=>r.kind==='action');
    const assignments=[];
    function visit(i,binding){if(i===vars.length){assignments.push({...binding});return;}for(const e of level.entities){binding[vars[i]]=e.id;visit(i+1,binding);}delete binding[vars[i]];}
    visit(0,{});
    base.bindings=assignments.filter(binding=>facts.every(r=>matches(r,level,binding)));
    base.rows=base.rows.map(r=>({...r,ok:r.kind==='fact'?assignments.some(b=>matches(r,level,b)):null}));
    for(const v of vars)base.candidates[v]=[...new Set(base.bindings.map(b=>b[v]))];
    if(!base.bindings.length)return fail('이 말들을 모두 만족하는 대상이 없어요. 같은 보라 표식은 모든 문장에서 같은 대상을 가리켜요.','contradiction');
    if(commands.length!==1)return fail(commands.length?'실행할 부탁은 하나만 놓아 주세요.':'마지막에 열다 또는 돕다로 실행할 부탁을 연결해 주세요.','action-count');
    const cmd=commands[0],pairs=new Map();
    for(const binding of base.bindings)for(const actor of domain(cmd.subject,level,binding))for(const target of domain(cmd.object,level,binding))pairs.set(actor+'|'+target,{actor,target});
    base.actionPairs=[...pairs.values()];base.action=cmd;
    if(base.actionPairs.length!==1)return fail(base.actionPairs.length?`아직 실행할 대상 조합이 ${base.actionPairs.length}가지예요. 관찰한 관계를 더 연결해 주세요.`:'실행할 대상이 없어요. 대상 자리에 있는 뜻을 확인해 주세요.',base.actionPairs.length?'ambiguous':'no-target');
    const {actor,target}=base.actionPairs[0],actorEntity=level.entities.find(e=>e.id===actor),targetEntity=level.entities.find(e=>e.id===target);
    let executable=false;
    if(level.id===0&&cmd.verb==='열다')executable=actorEntity.type==='person'&&targetEntity.type==='door'&&has(level,'가지다',actor,'key')&&has(level,'보다',actor,target)&&has(level,'내다',target,'sound');
    if(level.id===1&&cmd.verb==='돕다')executable=actorEntity.type==='person'&&targetEntity.type==='person'&&actor!==target&&has(level,'가지다',actor,'key')&&has(level,'보다',actor,target)&&has(level,'보다',target,actor);
    if(!executable)return fail(level.id===0?'대상은 정해졌어요. 열쇠를 가진 주민이 바라보는 소리 나는 문을 열어야 해요.':'대상은 정해졌어요. 열쇠를 가진 주민에게 서로 바라보는 상대를 돕도록 부탁해 주세요.','cannot-act');
    base.rows=base.rows.map(r=>({...r,ok:true}));
    return Object.assign(base,{ok:true,code:'ready',message:level.id===0?`${actorEntity.label}이 ${targetEntity.label}을 열었어요.`:`${actorEntity.label}과 ${targetEntity.label}이 함께 문을 열었어요.`});
  }
  function submit(state,trees){const analysis=solve(trees,state);if(!analysis.ok)return {ok:false,state:JSON.parse(JSON.stringify(state)),message:analysis.message,analysis};const next={...state,complete:true,turn:(state.turn||0)+1,last:{action:analysis.action.verb,...analysis.actionPairs[0],bindings:analysis.bindings}};return {ok:true,state:next,message:analysis.message,analysis};}
  return {levels,initial,solve,submit,info,purple,blue:[...observations,...actions]};
});
