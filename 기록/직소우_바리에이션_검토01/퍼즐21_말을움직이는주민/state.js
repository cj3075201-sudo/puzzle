(function(root,factory){if(typeof module==='object'&&module.exports)module.exports=factory(require('./core.js'),require('./models.json'));else root.MetaPuzzle=factory(root.JigsawCore,root.JIGSAW_MODELS||root.MODELS);})(typeof globalThis!=='undefined'?globalThis:this,function(Core,Models){
'use strict';
const BLUE_WORDS=['옮기다','열다','닫다'];
const DIR={위:[0,-1],아래:[0,1],왼쪽:[-1,0],오른쪽:[1,0]};
const clone=x=>JSON.parse(JSON.stringify(x));
function initialBoard(){return [
 ['reader','y_e','주민',0,0],['close','b_we','닫다',1,0],['top-door','y_w','문',2,0],
 ['move','b_we','옮기다',1,2],['down','y_we','아래',2,2],['quote','y_we','글자',3,2],['quoted-resident','y_w','주민',4,2],
 ['open','b_we','열다',1,3],['bottom-door','y_w','문',3,3]
].map(([id,model,word,x,y])=>({id,model,word,x,y}));}
function initial(){return {version:1,board:initialBoard(),world:{doorOpen:false,box:{x:1,y:1},crossed:false},turn:0,selfEdits:0,complete:false};}
function table(){return Models.models||Models;}
function tree(spec){if(typeof spec==='string')return {word:spec,children:[]};if(Array.isArray(spec))return {word:spec[0],children:spec.slice(1).map(tree)};return {word:spec.word,children:(spec.children||[]).map(tree)};}
function geometry(board){return Core.analyze(board,Models,BLUE_WORDS);}
function read(state){
 const full=geometry(state.board);
 if(!full.ok&&full.code!=='disconnected')return full;
 const reader=state.board.find(p=>p.id==='reader');if(!reader)return {ok:false,code:'reader_missing',message:'부탁을 읽기 시작하는 주민 조각이 없습니다.'};
 const edges=full.edges||[], ids=new Set([reader.id]);let changed=true;
 while(changed){changed=false;for(const e of edges)if(ids.has(e.from)||ids.has(e.to)){if(!ids.has(e.from)||!ids.has(e.to))changed=true;ids.add(e.from);ids.add(e.to);}}
 const active=state.board.filter(p=>ids.has(p.id)), parsed=Core.analyze(active,Models,BLUE_WORDS);
 if(!parsed.ok)return parsed;
 if(edges.some(e=>e.to===reader.id))return {ok:false,code:'reader_not_root',message:'주민 조각에서 시작하는 부탁을 만들어 주세요.'};
 return {...parsed,activeIds:[...ids],pieces:active};
}
function quotedIds(state){
 const result=geometry(state.board), edges=result.edges||[], excluded=new Set();
 for(const p of state.board.filter(p=>p.word==='글자')){const todo=edges.filter(e=>e.from===p.id).map(e=>e.to);while(todo.length){const id=todo.pop();if(excluded.has(id))continue;excluded.add(id);for(const e of edges)if(e.from===id)todo.push(e.to);}}
 return excluded;
}
function selectWord(state,spec){
 let s=tree(spec),filter=null;
 if(DIR[s.word]&&s.children.length===1){filter=s.word;s=s.children[0];}
 if(s.children.length)return {ok:false,message:'글자 뒤에는 찾을 글자 하나를 붙여 주세요. 위치를 덧붙일 때는 위·아래·왼쪽·오른쪽을 사용해요.'};
 const exclude=quotedIds(state);let candidates=state.board.filter(p=>p.word===s.word&&!exclude.has(p.id));
 if(filter&&candidates.length){const axis=['위','아래'].includes(filter)?'y':'x',values=candidates.map(p=>p[axis]);const value=['위','왼쪽'].includes(filter)?Math.min(...values):Math.max(...values);candidates=candidates.filter(p=>p[axis]===value);}
 if(!candidates.length)return {ok:false,message:`부탁판에서 '${s.word}' 글자를 찾지 못했어. 글자를 가리키는 설명 속 조각은 대상에서 빼고 찾아.`};
 if(candidates.length>1)return {ok:false,message:`'${s.word}' 글자가 ${candidates.length}개야. 위·아래·왼쪽·오른쪽으로 어느 글자인지 알려 줘.`};
 return {ok:true,piece:candidates[0]};
}
function command(spec){
 const t=tree(spec);if(t.word!=='주민'||t.children.length!==1)return {ok:false,message:'주민에게 한 가지 행동을 부탁해 주세요.'};
 const a=t.children[0];if(!BLUE_WORDS.includes(a.word))return {ok:false,message:'이 주민에게는 열다·닫다·옮기다를 부탁할 수 있어요.'};
 if(a.word!=='옮기다'){if(a.children.length!==1||a.children[0].word!=='문'||a.children[0].children.length)return {ok:false,message:'열거나 닫을 대상은 문이에요.'};return {ok:true,action:a.word};}
 let direction=null,target=null;
 if(a.children.length===1&&DIR[a.children[0].word]&&a.children[0].children.length===1){direction=a.children[0].word;target=a.children[0].children[0];}
 else if(a.children.length===2){const ds=a.children.filter(c=>DIR[c.word]&&c.children.length===0);const ts=a.children.filter(c=>!ds.includes(c));if(ds.length===1&&ts.length===1){direction=ds[0].word;target=ts[0];}}
 if(!direction||!target)return {ok:false,message:'옮기다에 대상과 방향을 연결해 주세요. 방향 뒤에 대상을 이어도 돼요.'};
 if(target.word==='글자'&&target.children.length===1)return {ok:true,action:'옮기다',direction,target:'tile',selector:target.children[0]};
 if(target.word==='상자'&&target.children.length===0)return {ok:true,action:'옮기다',direction,target:'box'};
 return {ok:false,message:'상자를 움직이려면 상자, 부탁판 조각을 움직이려면 글자에 그 이름을 이어 주세요.'};
}
function act(state,spec,source){
 const parsed=command(spec);if(!parsed.ok)return {...parsed,state,events:[]};
 const next=clone(state),events=[];
 if(parsed.action==='열다'||parsed.action==='닫다'){
  next.world.doorOpen=parsed.action==='열다';events.push({type:'door',open:next.world.doorOpen,source});return {ok:true,state:next,events,message:next.world.doorOpen?'주민이 문을 열었어.':'주민이 문을 닫았어.'};
 }
 const [dx,dy]=DIR[parsed.direction];
 if(parsed.target==='box'){const before={...next.world.box};next.world.box.x+=dx;next.world.box.y+=dy;if(next.world.box.x<0||next.world.box.x>3||next.world.box.y<0||next.world.box.y>2)return {ok:false,state,events,message:'상자는 그쪽 벽을 지나갈 수 없어.'};events.push({type:'box-move',from:before,to:{...next.world.box},source});return {ok:true,state:next,events,message:`주민이 상자를 ${parsed.direction}으로 한 칸 옮겼어.`};}
 const picked=selectWord(next,parsed.selector);if(!picked.ok)return {...picked,state,events};
 const p=picked.piece,from={x:p.x,y:p.y},to={x:p.x+dx,y:p.y+dy};
 if(to.x<0||to.x>=7||to.y<0||to.y>=6)return {ok:false,state,events,message:'그 글자는 판 밖으로 옮길 수 없어.'};
 if(next.board.some(q=>q.id!==p.id&&q.x===to.x&&q.y===to.y))return {ok:false,state,events,message:'옮길 칸에 다른 조각이 있어. 먼저 자리를 비워 줘.'};
 p.x=to.x;p.y=to.y;const g=geometry(next.board);
 if(!g.ok&&g.code!=='disconnected')return {ok:false,state,events,message:`그 자리에서는 조각이 맞물리지 않아. ${g.message}`};
 if(source==='board')next.selfEdits++;
 events.push({type:'tile-move',id:p.id,word:p.word,from,to,source});return {ok:true,state:next,events,message:`주민이 '${p.word}' 글자를 ${parsed.direction}으로 한 칸 옮겼어.`};
}
function runBoard(state){
 let next=clone(state),events=[],message='';const seen=new Set();
 for(let i=0;i<8;i++){
  const r=read(next);if(!r.ok)return {ok:true,state:next,events,message:`지금 부탁판은 읽을 수 없어. ${r.message}`,reading:r};
  if(r.tree.children.length===0)return {ok:true,state:next,events,message:'주민 조각에서 행동이 이어지지 않아. 다음 부탁을 기다리고 있어.',reading:r};
  const key=JSON.stringify(next.board.map(p=>[p.id,p.x,p.y]));if(seen.has(key))return {ok:true,state:next,events,message:'같은 연결로 되돌아왔어. 반복을 멈추고 기다리고 있어.',reading:r};seen.add(key);
  const result=act(next,r.tree,'board');if(!result.ok)return {ok:true,state:next,events,message:`주민이 자기 부탁을 읽었지만 실행하지 못했어. ${result.message}`,reading:r};
  next=result.state;events.push(...result.events);message=result.message;
  if(!result.events.some(e=>e.type==='tile-move'))return {ok:true,state:next,events,message,reading:read(next)};
 }
 return {ok:true,state:next,events,message:'연속 실행 여덟 번에서 잠시 멈췄어.',reading:read(next)};
}
function submit(state,spec){
 const first=act(state,spec,'player');if(!first.ok)return first;
 first.state.turn++;const after=runBoard(first.state);
 return {ok:true,state:after.state,events:[...first.events,...after.events],message:first.message+' '+after.message,reading:after.reading};
}
function tick(state){const result=runBoard(state);result.state.turn++;return result;}
function cross(state){
 const waiting=clone(state);waiting.world.doorOpen=false;
 const attempt=runBoard(waiting),r=read(attempt.state),c=r.ok?command(r.tree):null;
 if(!attempt.state.world.doorOpen||!c||!c.ok||c.action!=='열다')return {ok:false,state:attempt.state,events:[{type:'door',open:false,source:'arrival'},...attempt.events],message:'문 앞에 도착하자 주민이 부탁판을 다시 확인했어. 문을 열어 주라는 부탁이 이어져야 통과할 수 있어.'};
 attempt.state.world.crossed=true;attempt.state.complete=true;return {ok:true,state:attempt.state,events:[{type:'door',open:false,source:'arrival'},...attempt.events,{type:'cross'}],message:'주민이 바뀐 부탁을 읽고 문을 열어 주었어. 무사히 건넜어!'};
}
return {initial,initialBoard,submit,tick,read,cross,exit:cross,command,selectWord,quotedIds,BLUE_WORDS};
});
