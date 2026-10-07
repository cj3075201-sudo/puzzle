(function(root,factory){const api=factory();if(typeof module==='object'&&module.exports)module.exports=api;else root.PuzzleCore=api;})(typeof globalThis!=='undefined'?globalThis:this,function(){
'use strict';
const directions={N:[0,-1,'S'],E:[1,0,'W'],S:[0,1,'N'],W:[-1,0,'E']};
const nouns=new Set(['나','주민','집','안','밖','열쇠','책']),verbs=new Set(['가지다','가다','주다']);
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
 const yellow=id=>models[ids.get(id).model].color==='yellow',blues=pieces.filter(p=>!yellow(p.id)),actions=blues.filter(p=>p.word!=='가지다');
 if(actions.length!==1)return fail('action_count','실행할 행동을 하나 연결해 주세요.');
 if(edges.some(e=>!yellow(e.from)&&!yellow(e.to)))return fail('blue_connection','대상과 행동의 연결을 확인해 주세요.');
 if(edges.some(e=>e.profile==='twin'&&(yellow(e.to)||ids.get(e.to).word!=='주다')))return fail('unsupported_connector','주체 표시의 연결 대상을 확인해 주세요.');
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
  if(b.word==='주다'){
   const actors=incoming.filter(e=>e.profile==='twin'),recipients=incoming.filter(e=>e.profile==='round');
   if(actors.length!==1||recipients.length!==1||outgoing.length!==1||outgoing[0].profile!=='round')return fail('give_roles','주는 쪽·받는 쪽·물건의 연결을 확인해 주세요.');
   const subject=groups.get(actors[0].from),recipient=groups.get(recipients[0].from),object=groups.get(outgoing[0].to);
   if(subject.root!==actors[0].from||recipient.root!==recipients[0].from)return fail('modifier_attachment','수식하는 대상에 행동을 연결해 주세요.');
   clauses.push({verb:b.word,subject,recipient,object});
  }else{
   if(incoming.length!==1||outgoing.length!==1)return fail(b.word==='가다'?'movement_roles':'possession_roles',b.word==='가다'?'이동할 대상과 장소를 연결해 주세요.':'가진 대상과 물건을 연결해 주세요.');
   const subject=groups.get(incoming[0].from),object=groups.get(outgoing[0].to);
   if(subject.root!==incoming[0].from)return fail('modifier_attachment','수식하는 대상에 행동을 연결해 주세요.');
   clauses.push({verb:b.word,subject,object});
  }
 }
 function person(group){const w=group.words.join('|');if(w==='나')return {kind:'player',location:null};if(w==='주민')return {kind:'resident',location:null};if(['안|주민','집|안|주민'].includes(w))return {kind:'resident',location:'inside'};if(['밖|주민','집|밖|주민'].includes(w))return {kind:'resident',location:'outside'};return null;}
 function item(group){return group.words.length===1&&['열쇠','책'].includes(group.words[0])?group.words[0]:null;}
 const active=clauses.find(c=>c.verb!=='가지다'),conditions=clauses.filter(c=>c.verb==='가지다');
 for(const clause of conditions){
  if(!person(clause.subject)||!item(clause.object))return fail('invalid_possession','가진 대상과 물건의 방향을 확인해 주세요.');
  if(clause.subject.root!==active.subject.root&&(!active.recipient||clause.subject.root!==active.recipient.root))return fail('unrelated_condition','같은 대상을 설명하는 연결인지 확인해 주세요.');
 }
 function describe(group){const kind=person(group);return kind?{root:group.root,words:group.words.slice(),...kind,conditions:[...new Set(conditions.filter(c=>c.subject.root===group.root).map(c=>item(c.object)))]}:null;}
 const subject=describe(active.subject);if(!subject)return fail(active.verb==='가다'?'invalid_mover':'invalid_actor','행동할 대상을 다시 확인해 주세요.');
 const meaning={verb:active.verb,subject};
 if(active.verb==='가다'){
  const w=active.object.words.join('|');meaning.destination=['안','집|안'].includes(w)?'inside':['밖','집|밖'].includes(w)?'outside':null;
  if(!meaning.destination)return fail('invalid_destination','이동할 장소를 다시 확인해 주세요.');
  meaning.destinationWords=active.object.words.slice();
 }else{
  meaning.actor=subject;meaning.recipient=describe(active.recipient);meaning.item=item(active.object);
  if(!meaning.recipient)return fail('invalid_recipient','받을 대상을 다시 확인해 주세요.');
  if(!meaning.item)return fail('invalid_item','건넬 물건을 다시 확인해 주세요.');
 }
 return {ok:true,code:'parsed',message:'',edges,meaning};
}
function evaluate(pieces,models,world){
 const result=analyze(pieces,models);if(!result.ok)return result;
 const respond=(ok,code,message,extra)=>Object.assign({},result,{ok,code,message},extra);
 if(!world||!world.player||!Array.isArray(world.player.holds)||!Array.isArray(world.residents)||world.residents.length!==2||world.residents.some(r=>!r||!['keeper','courier'].includes(r.id)||!['inside','outside'].includes(r.location)||!Array.isArray(r.holds))||new Set(world.residents.map(r=>r.id)).size!==2)return respond(false,'invalid_world','현재 상태를 확인할 수 없어요.');
 if(world.complete)return respond(false,'already_complete','책을 맡기고 열쇠를 받았어요.');
 function resolve(noun){
  const candidates=noun.kind==='player'?[{...world.player,id:'player'}]:world.residents.filter(r=>!noun.location||r.location===noun.location);
  const matches=candidates.filter(r=>noun.conditions.every(item=>r.holds.includes(item)));
  if(!matches.length)return {error:respond(false,'no_matching_resident','그 조건에 맞는 대상을 찾지 못했어요.')};
  if(matches.length>1)return {error:respond(false,'ambiguous_resident','두 주민이 서로를 바라봅니다. 누구를 말한 걸까요?')};
  return {entity:matches[0]};
 }
 const m=result.meaning,actor=resolve(m.subject);if(actor.error)return actor.error;
 if(m.verb==='가다'){
  if(actor.entity.id==='player')return respond(false,'wrong_mover','주민들이 당신을 바라봅니다.');
  return respond(false,'waiting_turn','주민이 대여 절차를 기다리며 자리에 머뭅니다.',{action:'stay',target:actor.entity.id,destination:m.destination,world:cloneWorld(world)});
 }
 // Resolve both references before a transfer or the automatic position exchange.
 const recipient=resolve(m.recipient);if(recipient.error)return recipient.error;
 const a=actor.entity,r=recipient.entity,extra={actor:a.id,recipient:r.id,item:m.item,target:r.id};
 if(a.id===r.id)return respond(false,'self_transfer','주는 쪽과 받는 쪽이 같아요.',extra);
 if(!a.holds.includes(m.item))return respond(false,'no_item','주는 쪽이 빈손을 보여 줍니다.',{...extra,target:a.id});
 if(a.id==='keeper'&&m.item==='열쇠'&&!a.holds.includes('책'))return respond(false,'deposit_required','대여 담당자가 책을 맡길 자리를 가리킵니다.',{...extra,action:'deposit_required',target:'keeper',world:cloneWorld(world)});
 const next=cloneWorld(world),nextA=a.id==='player'?next.player:next.residents.find(e=>e.id===a.id),nextR=r.id==='player'?next.player:next.residents.find(e=>e.id===r.id);
 nextA.holds.splice(nextA.holds.indexOf(m.item),1);nextR.holds.push(m.item);
 const keeper=next.residents.find(e=>e.id==='keeper'),courier=next.residents.find(e=>e.id==='courier');
 const exchangedPositions=!next.deposited&&r.id==='keeper'&&m.item==='책';
 if(exchangedPositions){next.deposited=true;keeper.location='outside';courier.location='inside';}
 next.complete=Boolean(next.deposited&&keeper.holds.includes('책')&&courier.holds.includes('열쇠'));
 const action=next.complete?'complete':exchangedPositions?'exchange_positions':'transfer';
 const message=next.complete?'책을 맡기고 심부름꾼이 열쇠를 받았습니다.':exchangedPositions?'책을 맡겼습니다. 두 주민이 자리를 바꿉니다.':'물건을 건넸습니다.';
 return respond(true,action,message,{...extra,action,exchangedPositions,world:next});
}
function cloneWorld(world){return {...world,player:{...world.player,holds:world.player.holds.slice()},residents:world.residents.map(r=>({...r,holds:r.holds.slice()}))};}
return {analyze,evaluate};
});
