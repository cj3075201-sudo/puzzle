(function(root,factory){const api=factory();if(typeof module==='object'&&module.exports)module.exports=api;else root.PuzzleCore=api;})(typeof globalThis!=='undefined'?globalThis:this,function(){
'use strict';
const directions={N:[0,-1,'S'],E:[1,0,'W'],S:[0,1,'N'],W:[-1,0,'E']};
const nouns=new Set(['나','주민','집','안','밖','열쇠','책']),verbs=new Set(['가지다','가다']);
function analyze(pieces,models){
 const edges=[],fail=(code,message)=>({ok:false,code,message,edges});
 if(!Array.isArray(pieces)||!pieces.length)return fail('empty','조각을 놓아 주세요.');
 const ids=new Map(),cells=new Map(),ports=new Map();
 for(const p of pieces){
  if(!p||p.id==null||ids.has(p.id))return fail('invalid_piece','조각 정보를 확인해 주세요.');
  if(!Number.isInteger(p.x)||!Number.isInteger(p.y))return fail('off_grid','조각을 칸에 맞춰 주세요.');
  const m=models&&models[p.model];
  if(!m||!['yellow','blue'].includes(m.color)||!Array.isArray(m.ports))return fail('invalid_model','모형을 확인해 주세요.');
  if(typeof p.word!=='string'||!p.word.trim())return fail('empty_word','빈 조각에 글자를 넣어 주세요.');
  if(!(m.color==='yellow'?nouns:verbs).has(p.word))return fail('word_color','글자와 조각 색을 확인해 주세요.');
  const cell=p.x+','+p.y;if(cells.has(cell))return fail('overlap','겹친 조각을 옮겨 주세요.');
  const sidePorts=new Map();for(const port of m.ports){
   if(!Array.isArray(port)||!directions[port[0]]||!['tab','socket'].includes(port[1])||!['round','twin'].includes(port[2])||sidePorts.has(port[0]))return fail('invalid_model','모형을 확인해 주세요.');
   sidePorts.set(port[0],port);
  }
  ids.set(p.id,p);cells.set(cell,p);ports.set(p.id,sidePorts);
 }
 for(const p of pieces)for(const side of ['E','S']){
  const [dx,dy,other]=directions[side],q=cells.get((p.x+dx)+','+(p.y+dy));if(!q)continue;
  const a=ports.get(p.id).get(side),b=ports.get(q.id).get(other);if(!a&&!b)continue;
  if(!a||!b||a[1]===b[1]||a[2]!==b[2])return fail('port_mismatch','맞닿은 홈과 돌출부를 확인해 주세요.');
  edges.push({from:a[1]==='tab'?p.id:q.id,to:a[1]==='tab'?q.id:p.id,profile:a[2]});
 }
 const reached=new Set([pieces[0].id]);let more=true;
 while(more){more=false;for(const e of edges){if(reached.has(e.from)&&!reached.has(e.to)){reached.add(e.to);more=true;}if(reached.has(e.to)&&!reached.has(e.from)){reached.add(e.from);more=true;}}}
 if(reached.size!==pieces.length)return fail('disconnected','떨어진 조각을 연결해 주세요.');
 const yellow=id=>models[ids.get(id).model].color==='yellow',blues=pieces.filter(p=>!yellow(p.id)),moves=blues.filter(p=>p.word==='가다');
 if(moves.length!==1)return fail('movement_count','이동할 행동을 하나 연결해 주세요.');
 if(edges.some(e=>!yellow(e.from)&&!yellow(e.to)))return fail('blue_connection','대상과 행동의 연결을 확인해 주세요.');
 if(edges.some(e=>e.profile!=='round'))return fail('unsupported_connector','이 표현에는 둥근 연결부를 사용해 주세요.');
 const yy=edges.filter(e=>yellow(e.from)&&yellow(e.to)),groups=new Map();
 for(const p of pieces.filter(p=>yellow(p.id))){
  if(yy.filter(e=>e.from===p.id).length>1||yy.filter(e=>e.to===p.id).length>1)return fail('noun_branch','노란 조각의 수식은 한 줄로 이어 주세요.');
 }
 for(const p of pieces.filter(p=>yellow(p.id)&&!yy.some(e=>e.to===p.id))){
  const members=[],seen=new Set();let id=p.id;
  while(id!=null){if(seen.has(id))return fail('noun_cycle','노란 조각의 연결 방향을 확인해 주세요.');seen.add(id);members.push(id);const next=yy.find(e=>e.from===id);id=next?next.to:null;}
  if(members.length>3)return fail('chain_limit','노란 조각은 연속 세 개까지 연결해 주세요.');
  const group={root:members[members.length-1],words:members.map(id=>ids.get(id).word)};
  for(const member of members)groups.set(member,group);
 }
 if(groups.size!==pieces.length-blues.length)return fail('noun_cycle','노란 조각의 연결 방향을 확인해 주세요.');
 const clauses=[];
 for(const b of blues){
  const incoming=edges.filter(e=>e.to===b.id),outgoing=edges.filter(e=>e.from===b.id);
  if(incoming.length!==1||outgoing.length!==1)return fail(b.word==='가다'?'movement_roles':'possession_roles',b.word==='가다'?'이동할 대상과 장소를 연결해 주세요.':'가진 대상과 물건을 연결해 주세요.');
  const subject=groups.get(incoming[0].from),object=groups.get(outgoing[0].to);
  if(subject.root!==incoming[0].from)return fail('modifier_attachment','수식하는 대상에 행동을 연결해 주세요.');
  clauses.push({verb:b.word,subject,object});
 }
 function person(group){const w=group.words.join('|');if(w==='나')return {kind:'player',location:null};if(w==='주민')return {kind:'resident',location:null};if(['안|주민','집|안|주민'].includes(w))return {kind:'resident',location:'inside'};if(['밖|주민','집|밖|주민'].includes(w))return {kind:'resident',location:'outside'};return null;}
 for(const clause of clauses.filter(c=>c.verb==='가지다')){
  if(!person(clause.subject)||clause.object.words.length!==1||!['열쇠','책'].includes(clause.object.words[0]))return fail('invalid_possession','가진 대상과 물건의 방향을 확인해 주세요.');
 }
 const movement=clauses.find(c=>c.verb==='가다'),mover=person(movement.subject);
 if(!mover)return fail('invalid_mover','이동할 대상을 다시 확인해 주세요.');
 const destinationWord=movement.object.words.join('|'),destination=['안','집|안'].includes(destinationWord)?'inside':['밖','집|밖'].includes(destinationWord)?'outside':null;
 if(!destination)return fail('invalid_destination','이동할 장소를 다시 확인해 주세요.');
 const conditions=[];
 for(const clause of clauses.filter(c=>c.verb==='가지다')){
  if(clause.subject.root!==movement.subject.root)return fail('unrelated_condition','같은 대상을 설명하는 연결인지 확인해 주세요.');
  conditions.push(clause.object.words[0]);
 }
 const meaning={subject:{root:movement.subject.root,words:movement.subject.words.slice(),kind:mover.kind,location:mover.location,conditions:[...new Set(conditions)]},destination,destinationWords:movement.object.words.slice()};
 return {ok:true,code:'parsed',message:'',edges,meaning};
}
function evaluate(pieces,models,world){
 const result=analyze(pieces,models);if(!result.ok)return result;
 const respond=(ok,code,message,extra)=>Object.assign({},result,{ok,code,message},extra);
 if(!world||!Array.isArray(world.residents)||world.residents.length!==2||world.residents.some(r=>!r||typeof r.id!=='string'||!['inside','outside'].includes(r.location)||!Array.isArray(r.holds))||new Set(world.residents.map(r=>r.id)).size!==2)return respond(false,'invalid_world','두 주민의 상태를 확인할 수 없어요.');
 const keyHolders=world.residents.filter(r=>r.holds.includes('열쇠')),bookHolders=world.residents.filter(r=>r.holds.includes('책'));
 if(keyHolders.length!==1||bookHolders.length!==1||keyHolders[0].id===bookHolders[0].id)return respond(false,'invalid_world','열쇠와 책을 가진 두 주민의 상태를 확인할 수 없어요.');
 if(world.complete)return respond(false,'already_complete','두 주민이 자리를 바꿨어요.');
 const {subject,destination}=result.meaning;
 if(subject.kind==='player')return respond(false,'wrong_mover','주민들이 당신을 바라봅니다.');
 const candidates=world.residents.filter(r=>(!subject.location||r.location===subject.location)&&subject.conditions.every(item=>r.holds.includes(item)));
 if(!candidates.length)return respond(false,'no_matching_resident','그 조건에 맞는 주민이 없어요.');
 if(candidates.length>1)return respond(false,'ambiguous_resident','두 주민이 서로를 바라봅니다. 누구를 말한 걸까요?');
 const selected=candidates[0];
 if(selected.location===destination)return respond(false,'already_there','주민이 지금 서 있는 곳을 가리킵니다.',{target:selected.id,destination});
 const next=cloneWorld(world);next.residents.find(r=>r.id===selected.id).location=destination;
 next.complete=next.residents.find(r=>r.holds.includes('열쇠')).location==='inside'&&next.residents.find(r=>r.holds.includes('책')).location==='outside';
 return respond(true,next.complete?'complete':'move',next.complete?'열쇠를 가진 주민은 안에, 책을 가진 주민은 밖에 도착했습니다.':'주민이 자리를 옮깁니다.',{action:next.complete?'complete':'move',target:selected.id,destination,world:next});
}
function cloneWorld(world){return {...world,residents:world.residents.map(r=>({...r,holds:r.holds.slice()}))};}
return {analyze,evaluate};
});
