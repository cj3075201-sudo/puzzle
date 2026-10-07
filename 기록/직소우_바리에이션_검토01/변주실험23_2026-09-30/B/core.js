(function(root,factory){const api=factory();if(typeof module==='object'&&module.exports)module.exports=api;else root.JigsawCore=api;})(typeof globalThis!=='undefined'?globalThis:this,function(){
'use strict';
const DIR={N:[0,-1,'S'],E:[1,0,'W'],S:[0,1,'N'],W:[-1,0,'E']};
const DEFAULT_BLUE_WORDS=['차갑다','따뜻하다','아프다','뜨겁다','열다','닫다','가다','주다','가지다','오다','멈추다','움직이다','보다','보여주다','말하다','듣다','아니다','않다','부정','질문','묻다','원하다','필요하다','알다','모르다','먼저','다음','만','같다','다르다','크다','작다','밝다','어둡다','있다','없다','되다','괜찮다','쓰다','먹다','마시다','쉬다','기다리다','돕다','건네다','밀다','당기다','들어가다','나가다'];
function blueSet(words){return words instanceof Set?words:new Set(words||DEFAULT_BLUE_WORDS);}
function unwrap(models){return models&&models.models?models.models:models;}
function asTree(spec){
 if(typeof spec==='string')return {word:spec,children:[]};
 if(Array.isArray(spec)){if(!spec.length||typeof spec[0]!=='string')throw new Error('표현에는 글자가 필요합니다.');return {word:spec[0],children:spec.slice(1).map(asTree)};}
 if(spec&&typeof spec.word==='string'&&(!spec.children||Array.isArray(spec.children)))return {word:spec.word,children:(spec.children||[]).map(asTree)};
 throw new Error('표현 구조를 확인해 주세요.');
}
function canonical(tree){
 const t=asTree(tree);
 function normalize(n){return [n.word,...n.children.map(normalize).sort((a,b)=>{const sa=JSON.stringify(a),sb=JSON.stringify(b);return sa<sb?-1:sa>sb?1:0;})];}
 return JSON.stringify(normalize(t));
}
function eq(tree,spec){try{return canonical(tree)===canonical(spec);}catch(_){return false;}}
function analyze(pieces,models,blueWords){
 const table=unwrap(models),blues=blueSet(blueWords),edges=[];
 const fail=(code,message)=>({ok:false,code,message,tree:null,canonical:null,edges});
 if(!Array.isArray(pieces)||!pieces.length)return fail('empty','조각을 놓아 주세요.');
 if(pieces.length>12)return fail('piece_limit','조각은 열두 개까지 놓아 주세요.');
 const ids=new Map(),cells=new Map(),ports=new Map();
 for(const p of pieces){
  if(!p||p.id==null||ids.has(p.id))return fail('invalid_piece','조각 정보를 확인해 주세요.');
  if(!Number.isInteger(p.x)||!Number.isInteger(p.y)||p.x<0||p.x>=7||p.y<0||p.y>=6)return fail('out_of_bounds','조각을 판 안의 칸에 맞춰 주세요.');
  const model=table&&table[p.model];
  if(!model||!['yellow','blue'].includes(model.color)||!Array.isArray(model.ports))return fail('invalid_model','모형을 확인해 주세요.');
  if(typeof p.word!=='string'||!p.word.trim())return fail('empty_word','빈 조각에 글자를 넣어 주세요.');
  if(model.color!==(blues.has(p.word)?'blue':'yellow'))return fail('word_color','글자와 조각 색을 확인해 주세요.');
  if(p.rotation&&p.rotation%360!==0)return fail('rotation','모형은 돌리지 않고 사용해 주세요.');
  const cell=p.x+','+p.y;if(cells.has(cell))return fail('overlap','겹친 조각을 옮겨 주세요.');
  const sides=new Map();
  for(const port of model.ports){
   if(!Array.isArray(port)||!DIR[port[0]]||!['tab','socket'].includes(port[1])||!['round','twin'].includes(port[2])||sides.has(port[0]))return fail('invalid_model','모형을 확인해 주세요.');
   sides.set(port[0],port);
  }
  ids.set(p.id,p);cells.set(cell,p);ports.set(p.id,sides);
 }
 for(const p of pieces)for(const side of ['E','S']){
  const [dx,dy,opposite]=DIR[side],q=cells.get((p.x+dx)+','+(p.y+dy));if(!q)continue;
  const a=ports.get(p.id).get(side),b=ports.get(q.id).get(opposite);if(!a&&!b)continue;
  if(!a||!b||a[1]===b[1]||a[2]!==b[2])return fail('port_mismatch','맞닿은 홈과 돌출부를 확인해 주세요.');
  edges.push({from:a[1]==='tab'?p.id:q.id,to:a[1]==='tab'?q.id:p.id,profile:a[2]});
 }
 const incoming=new Map(pieces.map(p=>[p.id,[]])),outgoing=new Map(pieces.map(p=>[p.id,[]]));
 for(const e of edges){incoming.get(e.to).push(e.from);outgoing.get(e.from).push(e.to);}
 const reached=new Set([pieces[0].id]),queue=[pieces[0].id];
 while(queue.length){const id=queue.pop();for(const next of [...incoming.get(id),...outgoing.get(id)])if(!reached.has(next)){reached.add(next);queue.push(next);}}
 if(reached.size!==pieces.length)return fail('disconnected','떨어진 조각을 연결해 주세요.');
 const marks=new Map();
 function cyclic(id){if(marks.get(id)===1)return true;if(marks.get(id)===2)return false;marks.set(id,1);for(const next of outgoing.get(id))if(cyclic(next))return true;marks.set(id,2);return false;}
 if(pieces.some(p=>cyclic(p.id)))return fail('cycle','연결이 고리로 돌아오지 않게 해 주세요.');
 if(pieces.some(p=>incoming.get(p.id).length>1))return fail('multiple_parents','한 조각으로 들어오는 연결을 하나로 정리해 주세요.');
 const roots=pieces.filter(p=>incoming.get(p.id).length===0);
 if(roots.length!==1)return fail('root_count','한 표현으로 이어 주세요.');
 if(pieces.some(p=>outgoing.get(p.id).length>3))return fail('branch_limit','한 조각에서 세 갈래까지 이어 주세요.');
 let tooLong=false;
 function walk(id,previousYellow){const p=ids.get(id),n=table[p.model].color==='yellow'?previousYellow+1:0;if(n>3)tooLong=true;return {word:p.word,children:outgoing.get(id).map(child=>walk(child,n))};}
 const tree=walk(roots[0].id,0);
 if(tooLong)return fail('chain_limit','노란 조각은 연속 세 개까지 연결해 주세요.');
 return {ok:true,code:'parsed',message:'',tree,canonical:canonical(tree),edges};
}
function build(spec,models,blueWords){
 const table=unwrap(models),blues=blueSet(blueWords),tree=asTree(spec),nodes=[];
 function flatten(t,parent=null){const n={word:t.word,parent,children:[],index:nodes.length};nodes.push(n);if(t.children.length>3)throw new Error('한 조각에서 세 갈래까지 만들 수 있습니다.');for(const child of t.children)n.children.push(flatten(child,n));n.size=1+n.children.reduce((sum,c)=>sum+c.size,0);return n;}
 const root=flatten(tree);if(nodes.length>12)throw new Error('표현은 열두 조각까지 만들 수 있습니다.');
 function order(n,result=[]){result.push(n);for(const c of n.children.slice().sort((a,b)=>b.size-a.size))order(c,result);return result;}
 const traversal=order(root),used=new Set(),positions=new Map();let budget=400000;
 function search(i){if(i===traversal.length)return true;if(--budget<0)return false;const n=traversal[i];
  const choices=n.parent?Object.values(DIR).map(([dx,dy])=>{const p=positions.get(n.parent.index);return {x:p.x+dx,y:p.y+dy};}):[{x:3,y:2}];
  // Prefer right/down for readable chains; larger branches are laid out first.
  if(n.parent){const p=positions.get(n.parent.index);choices.sort((a,b)=>rank(a,p)-rank(b,p));}
  for(const pos of choices){const cell=pos.x+','+pos.y;if(pos.x<0||pos.x>=7||pos.y<0||pos.y>=6||used.has(cell))continue;
   const free=Object.values(DIR).filter(([dx,dy])=>pos.x+dx>=0&&pos.x+dx<7&&pos.y+dy>=0&&pos.y+dy<6&&!used.has((pos.x+dx)+','+(pos.y+dy))).length;
   if(free<n.children.length)continue;
   positions.set(n.index,pos);used.add(cell);if(search(i+1))return true;used.delete(cell);positions.delete(n.index);
  }return false;
 }
 function rank(a,p){return a.x>p.x?0:a.y>p.y?1:a.x<p.x?2:3;}
 if(!search(0))throw new Error('이 표현을 7×6 판에 배치할 수 없습니다.');
 const minX=Math.min(...[...positions.values()].map(p=>p.x)),minY=Math.min(...[...positions.values()].map(p=>p.y));
 function side(from,to){const a=positions.get(from.index),b=positions.get(to.index);return Object.keys(DIR).find(s=>a.x+DIR[s][0]===b.x&&a.y+DIR[s][1]===b.y);}
 function signature(ports){return ports.map(p=>p.join(':')).sort().join('|');}
 const pieces=nodes.map(n=>{const ports=[];if(n.parent)ports.push([side(n,n.parent),'socket','round']);for(const c of n.children)ports.push([side(n,c),'tab','round']);const color=blues.has(n.word)?'blue':'yellow',sig=signature(ports);
  const entry=Object.entries(table||{}).find(([,m])=>m&&m.color===color&&Array.isArray(m.ports)&&signature(m.ports)===sig);
  if(!entry)throw new Error('필요한 '+color+' 모형이 없습니다: '+sig);
  const p=positions.get(n.index);return {id:'p'+n.index,model:entry[0],word:n.word,x:p.x-minX,y:p.y-minY};
 });
 const check=analyze(pieces,table,blues);if(!check.ok)throw new Error(check.message);
 return pieces;
}
return {analyze,canonical,eq,build,DEFAULT_BLUE_WORDS};
});
