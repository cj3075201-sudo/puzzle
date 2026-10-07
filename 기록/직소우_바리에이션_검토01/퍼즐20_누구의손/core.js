(function(root,factory){const api=factory();if(typeof module==='object'&&module.exports)module.exports=api;else root.PuzzleCore=api;})(typeof globalThis!=='undefined'?globalThis:this,function(){
'use strict';
const directions={N:[0,-1,'S'],E:[1,0,'W'],S:[0,1,'N'],W:[-1,0,'E']};
const nouns=new Set(['나','주민','손']),verbs=new Set(['차갑다','따뜻하다']);
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
 const yellow=id=>models[ids.get(id).model].color==='yellow',blues=pieces.filter(p=>!yellow(p.id));
 if(blues.length!==1)return fail('state_count','상태 글자를 하나 연결해 주세요.');
 if(edges.some(e=>e.profile!=='round'))return fail('unsupported_connector','이 표현에는 둥근 연결부를 사용해 주세요.');
 const state=blues[0],incoming=edges.filter(e=>e.to===state.id),outgoing=edges.filter(e=>e.from===state.id);
 if(incoming.length!==1||outgoing.length!==0||!yellow(incoming[0].from))return fail('state_roles','상태를 말할 대상의 연결을 확인해 주세요.');
 const yellowPieces=pieces.filter(p=>yellow(p.id));
 if(yellowPieces.length>3)return fail('chain_limit','노란 조각은 연속 세 개까지 연결해 주세요.');
 for(const p of yellowPieces){
  if(edges.filter(e=>e.to===p.id).length>1||edges.filter(e=>e.from===p.id).length!==1)return fail('noun_branch','대상을 한 줄로 이어 상태에 연결해 주세요.');
 }
 const words=[],visited=new Set();let id=incoming[0].from;
 while(id!=null){
  if(visited.has(id))return fail('noun_cycle','노란 조각의 연결 방향을 확인해 주세요.');
  visited.add(id);words.unshift(ids.get(id).word);const previous=edges.find(e=>e.to===id);id=previous?previous.from:null;
 }
 if(visited.size!==yellowPieces.length)return fail('unused_piece','모든 조각의 연결을 확인해 주세요.');
 const phrase=words.join('|'),subject=phrase==='나|손'?'player':phrase==='주민|손'?'patient':phrase==='손'?'unspecified':null;
 if(!subject)return fail('unsupported_subject','누구의 손을 말하는지 알아듣지 못했어요.');
 return {ok:true,code:'parsed',message:'',edges,meaning:{subject,state:state.word==='차갑다'?'cold':'warm',words}};
}
function validWorld(world){return world&&['playerWarm','understood','heard','complete'].every(k=>typeof world[k]==='boolean');}
function evaluate(pieces,models,world){
 const parsed=analyze(pieces,models);
 if(!validWorld(world))return {ok:false,code:'invalid_world',message:'현재 상태를 확인할 수 없어요.',edges:parsed.edges||[]};
 const next={...world};
 const respond=(ok,code,message,extra)=>Object.assign({},parsed,{ok,code,message,world:next},extra);
 if(world.complete)return respond(false,'already_complete','주민이 이미 손을 맡겼어요.');
 if(!parsed.ok)return {...parsed,world:next};
 const {subject,state}=parsed.meaning;
 if(subject==='unspecified')return respond(false,'clarify_owner','주민이 당신의 손을 가리킵니다.',{action:'point_player',reply:world.playerWarm?'player_warm':'complaint'});
 if(subject==='patient'){
  if(state==='warm')return respond(true,'patient_warm','주민이 자기 손을 보여 줍니다.',{action:'show_patient_hand',reply:'patient_warm'});
  return respond(false,'wrong_owner','주민이 고개를 젓고 당신의 손을 가리킵니다.',{action:'point_player',reply:world.playerWarm?'player_warm':'complaint'});
 }
 if(state==='cold'&&!world.playerWarm){next.understood=true;return respond(true,'understood','주민이 당신의 손을 보고 고개를 끄덕입니다.',{action:'acknowledge',reply:'player_cold'});}
 if(state==='warm'&&world.playerWarm)return respond(true,'player_warm','주민이 당신의 손을 보고 고개를 끄덕입니다.',{action:'acknowledge',reply:'player_warm'});
 return respond(false,'wrong_state','주민이 당신의 손을 가리키며 고개를 젓습니다.',{action:'point_player',reply:world.playerWarm?'player_warm':'complaint'});
}
function interact(event,world){
 if(!validWorld(world))return {ok:false,code:'invalid_world',message:'현재 상태를 확인할 수 없어요.'};
 const next={...world},respond=(ok,code,message,extra)=>Object.assign({ok,code,message,world:next},extra);
 if(world.complete)return respond(false,'already_complete','주민이 이미 손을 맡겼어요.');
 if(event==='listen'){next.heard=true;return respond(true,'heard','주민이 당신의 손을 가리킵니다.',{action:'listen',reply:world.playerWarm?'player_warm':'complaint'});}
 if(event==='warm'){next.playerWarm=true;return respond(true,'warmed','손이 따뜻해졌습니다.',{action:'warm'});}
 if(event==='approach'){
  if(!world.playerWarm){next.heard=true;return respond(false,'withdraw','주민이 손을 움츠리고 당신의 손을 가리킵니다.',{action:'withdraw',reply:'complaint'});}
  next.complete=true;return respond(true,'complete','주민이 편안하게 손을 맡깁니다.',{action:'accepted'});
 }
 return respond(false,'invalid_event','그 행동을 할 수 없어요.');
}
return {analyze,evaluate,interact};
});
