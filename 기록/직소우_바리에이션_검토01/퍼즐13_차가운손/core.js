(function (root, factory) {
  const api = factory();
  if (typeof module === 'object' && module.exports) module.exports = api;
  else root.PuzzleCore = api;
})(typeof globalThis !== 'undefined' ? globalThis : this, function () {
  'use strict';
  const dirs = { N: [0,-1,'S'], E: [1,0,'W'], S: [0,1,'N'], W: [-1,0,'E'] };
  const yellowWords = new Set(['나','주민','집','안','밖','열쇠']);
  function analyze(pieces, models) {
    const edges = [];
    const fail = (code, message) => ({ok:false,code,message,edges});
    if (!Array.isArray(pieces) || !pieces.length) return fail('empty','조각을 놓아 주세요.');
    const cells = new Map(), ids = new Map(), ports = new Map();
    for (const p of pieces) {
      if (!p || p.id == null || ids.has(p.id)) return fail('invalid_piece','조각 정보를 확인해 주세요.');
      if (!Number.isInteger(p.x) || !Number.isInteger(p.y)) return fail('off_grid','조각을 칸에 맞춰 주세요.');
      const model = models && models[p.model];
      if (!model || !['yellow','blue'].includes(model.color) || !Array.isArray(model.ports)) return fail('invalid_model','모형을 확인해 주세요.');
      if (typeof p.word !== 'string' || !p.word.trim()) return fail('empty_word','빈 조각에 글자를 넣어 주세요.');
      if (model.color === 'yellow' ? !yellowWords.has(p.word) : p.word !== '주다') return fail('word_color','글자와 조각 색을 확인해 주세요.');
      const cell = p.x + ',' + p.y;
      if (cells.has(cell)) return fail('overlap','겹친 조각을 옮겨 주세요.');
      const sidePorts = new Map();
      for (const port of model.ports) {
        if (!Array.isArray(port) || !dirs[port[0]] || !['tab','socket'].includes(port[1]) || !['round','twin'].includes(port[2]) || sidePorts.has(port[0])) return fail('invalid_model','모형을 확인해 주세요.');
        sidePorts.set(port[0],port);
      }
      cells.set(cell,p); ids.set(p.id,p); ports.set(p.id,sidePorts);
    }
    for (const p of pieces) for (const side of ['E','S']) {
      const [dx,dy,opposite] = dirs[side];
      const q = cells.get((p.x+dx)+','+(p.y+dy));
      if (!q) continue;
      const a = ports.get(p.id).get(side), b = ports.get(q.id).get(opposite);
      if (!a && !b) continue;
      if (!a || !b || a[1] === b[1] || a[2] !== b[2]) return fail('port_mismatch','맞닿은 홈과 돌출부를 확인해 주세요.');
      edges.push({from:a[1]==='tab'?p.id:q.id,to:a[1]==='tab'?q.id:p.id,profile:a[2]});
    }
    const reached = new Set([pieces[0].id]);
    let change = true;
    while (change) { change=false; for (const e of edges) {
      if (reached.has(e.from) && !reached.has(e.to)) {reached.add(e.to);change=true;}
      if (reached.has(e.to) && !reached.has(e.from)) {reached.add(e.from);change=true;}
    }}
    if (reached.size !== pieces.length) return fail('disconnected','떨어진 조각을 연결해 주세요.');
    const blues = pieces.filter(p=>models[p.model].color==='blue');
    if (blues.length !== 1) return fail('verb_count','행동 글자를 하나 사용해 주세요.');
    const verb=blues[0], incoming=edges.filter(e=>e.to===verb.id), outgoing=edges.filter(e=>e.from===verb.id);
    const actorEdge=incoming.filter(e=>e.profile==='twin'), recipientEdge=incoming.filter(e=>e.profile==='round');
    if (actorEdge.length!==1 || recipientEdge.length!==1 || outgoing.length!==1 || outgoing[0].profile!=='round') return fail('missing_roles','주는 쪽·받는 쪽·물건의 연결을 확인해 주세요.');
    const yy=edges.filter(e=>e.from!==verb.id && e.to!==verb.id);
    for (const p of pieces.filter(p=>p.id!==verb.id)) {
      if (edges.filter(e=>e.to===p.id).length>1 || edges.filter(e=>e.from===p.id).length>1) return fail('branch','이 표현에서는 노란 조각을 한 줄로 연결해 주세요.');
    }
    const used=new Set([verb.id]);
    function chain(start, reverse) {
      const list=[], visited=new Set(); let current=start;
      while (current!=null) {
        if (visited.has(current) || used.has(current)) return null;
        visited.add(current);used.add(current);list.push(ids.get(current).word);
        const next=yy.find(e=>reverse?e.to===current:e.from===current);
        current=next?(reverse?next.from:next.to):null;
      }
      return reverse?list.reverse():list;
    }
    const actor=chain(actorEdge[0].from,true), recipient=chain(recipientEdge[0].from,true), item=chain(outgoing[0].to,false);
    if (!actor || !recipient || !item || used.size!==pieces.length) return fail('invalid_chain','노란 조각의 연결 방향을 확인해 주세요.');
    if ([actor,recipient,item].some(c=>c.length>3)) return fail('chain_limit','노란 조각은 연속 세 개까지 연결해 주세요.');
    // This scene has one shared house reference. The speaker can omit 집:
    // 안→주민 / 밖→주민 still identify a unique resident here.
    // Keep sequence and roles exact; do not infer from keyword presence.
    const sceneReferences = new Map([
      ['나','player'], ['주민','ambiguous'],
      ['집|안|주민','inside'], ['안|주민','inside'],
      ['집|밖|주민','outside'], ['밖|주민','outside']
    ]);
    const resolve = c => sceneReferences.get(c.join('|')) || null;
    const meaning={actor:resolve(actor),recipient:resolve(recipient),item:item.join('|')==='열쇠'?'key':null,chains:{actor,recipient,item}};
    if (!meaning.actor || !meaning.recipient || !meaning.item) return fail('unsupported_meaning','이 조합으로는 전달할 대상을 알아듣지 못했어요.');
    return {ok:true,code:'parsed',message:'',edges,meaning};
  }
  function evaluate(pieces,models,world) {
    const result=analyze(pieces,models);
    if (!result.ok) return result;
    const respond=(ok,code,message,extra)=>Object.assign({},result,{ok,code,message},extra);
    if (!world || !['player','inside','outside'].includes(world.keyOwner)) return respond(false,'invalid_world','열쇠 위치를 확인할 수 없어요.');
    if (world.complete) return respond(false,'already_complete','열쇠를 이미 건넸어요.');
    const m=result.meaning;
    if (m.actor==='ambiguous' || m.recipient==='ambiguous') return respond(false,'ambiguous_resident','두 주민이 서로를 바라봅니다. 누구를 말한 걸까요?');
    if (m.actor===m.recipient) return respond(false,'self_transfer','주는 쪽과 받는 쪽이 같아요.');
    if (world.keyOwner!==m.actor) return respond(false,'no_item','주는 쪽이 빈손을 보여 줍니다.');
    if (m.actor==='player' && m.recipient==='outside') return respond(false,'wrong_target','바깥 주민이 열쇠를 보고 고개를 젓습니다.',{action:'return_key',target:'outside',world:{...world}});
    if (m.actor==='player' && m.recipient==='inside') return respond(true,'complete','안쪽 주민이 열쇠를 받아 문을 엽니다.',{action:'complete',target:'inside',world:{...world,keyOwner:'inside',complete:true}});
    return respond(false,'unsupported_transfer','지금은 그 전달을 할 수 없어요.');
  }
  return {analyze,evaluate};
});
