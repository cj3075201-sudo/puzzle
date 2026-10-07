(()=>{'use strict';
const C=globalThis.JigsawCore,eq=(t,s)=>C.eq(t,s),R=(s,ok,message,changes={},speech=[])=>({state:{...s,...changes},ok,message,speech});
const T=(w,...children)=>({word:w,children:children.map(x=>typeof x==='string'?T(x):x)});
const initial={position:0,mark:'none',pin:true,heldReading:'inner',latch:false,basketUp:false,hatchOpen:false,lid:false,carrying:false,delivered:false,complete:false,trialCount:0,lastPass:null,physicalLog:[]};
function reading(s){return s.pin?s.heldReading:s.position===0?'inner':s.position===1?'window':'none';}
function seenMarked(s){return s.mark==='side'&&s.position!==2;}
function hasChild(t,spec){return (t.children||[]).some(c=>eq(c,spec));}
function matchRelease(t,s){
 // One explicit carriage with both a visible identifying condition and the requested action.
 if(t.word!=='함')return null;
 let action=(t.children||[]).find(c=>c.word==='풀다'&&hasChild(c,'빗장'));
 if(!action)return null;
 if(action.children.length!==1)return 'ambiguous';
 const props=t.children.filter(c=>c!==action);
 if(!props.length)return 'ambiguous';
 const marked=props.some(c=>eq(c,['표식','있다'])||eq(c,['가지다','표식'])||eq(c,['옆',['표식','있다']]));
 const unmarked=props.some(c=>eq(c,['표식',['아니다','있다']])||eq(c,['아니다',['가지다','표식']]));
 const books=props.some(c=>eq(c,['가지다','책'])||eq(c,['책','있다']));
 const empty=props.some(c=>eq(c,'비다'));
 const known=c=>eq(c,['표식','있다'])||eq(c,['가지다','표식'])||eq(c,['옆',['표식','있다']])||eq(c,['표식',['아니다','있다']])||eq(c,['아니다',['가지다','표식']])||eq(c,['가지다','책'])||eq(c,['책','있다'])||eq(c,'비다');
 if(props.some(c=>!known(c)))return 'ambiguous';
 if(marked&&unmarked)return 'contradiction';
 if(books||empty)return 'unseen-content';
 if(marked)return seenMarked(s)?'return':'no-visible-mark';
 if(unmarked)return seenMarked(s)?'far':'ambiguous';
 return 'ambiguous';
}
const sc={id:1,title:'돌아온 빈 운반함',theme:'같은 함이라고 생각한 것은 누구였을까',experimental:true,
goal:'진료소에 보낼 기록을 찾아, 기록원의 창구에 되돌려 놓으세요.',
intro:'기록원은 책을 실은 함을 보냈고, 잠시 뒤 빈 함이 왔다고 합니다. 그런데 진료소에서 온 쪽지에는 기록이 도착하지 않았다고 적혀 있습니다. 창구 아래에는 봉쇄된 운반로와 시험 손잡이가 남아 있습니다.',
rule:'노랑은 대상, 파랑은 행동·상태. 질문은 뒤에 붙인 말을 상대에게 묻습니다. 한 대상의 상태와 행동은 그 대상에서 갈라집니다. 단어 뜻은 알 수 있지만, 말 전체가 어느 장면과 대상을 뜻하는지는 상황으로 판단해야 합니다.',
words:['질문','이전','지금','책','함','표식','옆','위','창','저울','빗장','그물','문','보다','보이다','있다','아니다','가지다','움직이다','무겁다','비다','풀다','들다','열다','닫다','같다'],
blueWords:['질문','이전','지금','보다','보이다','있다','아니다','가지다','움직이다','무겁다','비다','풀다','들다','열다','닫다','같다'],
initial,actors:[{id:'clerk',label:'기록원',description:'낮은 창 안의 기록 담당',x:9,color:'#b9b5a0'}],
hint:['기록원은 떠난 함과 나중에 온 함을 같은 것으로 생각했습니다. 물건의 윗면에 붙인 표식과 옆면 표식 중 그 낮은 창에서 볼 수 있는 것은 무엇일까요?','움직임을 시험한 뒤 함 또는 표식에 대해 물어보세요. 저울 바늘은 고정핀을 풀기 전까지 지난 값을 붙잡습니다.','고정핀을 풀고 왕복 전후 저울을 물어보세요. 고정된 그물의 무게와 움직이는 운반함의 무게는 같은 방식으로 변하지 않습니다.','기록원이 빗장을 풀려면 어느 함인지 자기 시야에서 구별해야 합니다. 함에서 표식→있다와 풀다→빗장을 갈라 연결할 수 있습니다. 이후 손잡이로 들어온 함을 밀어 보세요.'],
inspect(id,s){return R(s,false,s.complete?'기록을 찾았군요. 빈 함이 왔다는 말과, 같은 함이 돌아왔다는 말은 달랐네요.':
 '아까 책이 든 함을 봤어. 함을 보내고 나서, 잠시 뒤 함이 왔어. 그 창에서는 책이 안 보였지. 그래서 배송이 끝난 줄 알았는데… 기억한 장면과 지금 보이는 것을 물어볼 수 있어.',{},[['책',['있다','함']],['함','움직이다'],['책',['아니다','보이다']]]);},
submit(t,s,l){if(l!=='clerk')return R(s,false,'기록원과 직접 이야기해 주세요.');
 const release=matchRelease(t,s);
 if(release){
  if(release==='return')return R(s,true,'기록원이 옆 표식으로 함을 구별하고, 그 함에 걸린 빗장을 풀어 잡아 줍니다. 손잡이의 멈춤턱이 내려갑니다.',{latch:true});
  if(release==='far')return R(s,true,'표식 없는 함 쪽 빗장은 이미 풀려 있습니다. 다른 쪽 멈춤턱은 그대로입니다.');
  if(release==='unseen-content')return R(s,false,'여기서는 함 안이 안 보여. 책이 있는지, 비었는지로는 어느 함인지 고를 수 없어.',{},[['책',['아니다','보이다']]]);
  if(release==='no-visible-mark')return R(s,false,'창으로 보이는 옆판에는 표식이 없어. 윗면은 이 창에서 보이지 않아.',{},[['표식',['아니다','보이다']]]);
  if(release==='contradiction')return R(s,false,'표식이 있으면서 없다는 함은 고를 수 없어.');
  return R(s,false,'빗장은 두 운반 줄에 하나씩 있어. 어느 함의 빗장인지 내가 볼 수 있는 것으로 구별해 줘.');
 }
 if(eq(t,['빗장','풀다'])||eq(t,['함',['풀다','빗장']]))return R(s,false,'어느 함의 빗장인가요? 여기서는 두 줄이 같은 모양이에요.');
 if(eq(t,['그물','들다']))return R(s,true,'기록원이 수거그물의 줄을 올려 고정합니다. 바깥의 그물을 살펴볼 수 있습니다.',{basketUp:true});
 if(eq(t,['문','열다']))return R(s,true,'기록원이 진료소 쪽 작은 수령문을 엽니다. 지난 배송의 수령판을 살펴볼 수 있습니다.',{hatchOpen:true});
 if(eq(t,['문','닫다']))return R(s,true,'수령문을 닫았습니다.',{hatchOpen:false});
 // Scope follows the question's direct content, without accepting a random bag of keywords.
 if(t.word!=='질문'||t.children.length!==1)return R(s,false,'기록원은 표현을 다시 봅니다. 관찰을 물을 때는 질문에 그 내용을 연결하고, 부탁할 때는 무엇의 행동인지 이어 주세요.');
 let q=t.children[0],past=false;if(['이전','지금'].includes(q.word)&&q.children.length===1){past=q.word==='이전';q=q.children[0];}
 if(q.word==='책')return R(s,true,past?'아까는 뚜껑이 열린 채 책을 실어서 책을 봤어. 그 뒤에는 뚜껑이 닫혔어. 나중에 온 함은 창 옆으로 보았고 책은 보이지 않았어.':'지금 낮은 창에서는 옆판만 보여. 안 보이는 책이 없다는 뜻인지는 알 수 없어.',{},past?[['책',['있다','함']]]:[['책',['아니다','보이다']]]);
 if(q.word==='표식'||(q.word==='보다'&&hasChild(q,'표식'))){
  const p=s.lastPass;if(!p)return R(s,true,seenMarked(s)?'현재 바깥 가까운 창에 옆 표식이 보여.':'보이는 옆판에 표식은 없어. 함의 윗면은 안 보여.',{},[[ '표식',seenMarked(s)?'보이다':['아니다','보이다'] ]]);
  return R(s,true,p.mark==='side'?(p.direction==='push'?'시험 때 표식 있는 옆판이 한 창에서 멀어졌어. 그동안 반대 창으로 들어온 옆판에는 표식이 없었어.':'당길 때 표식 없는 옆판이 반대 창에서 멀어지고, 표식 있는 옆판이 가까운 창으로 돌아왔어.'):'시험 때 두 창에서 옆판이 차례로 움직였어. 둘 다 보이는 표식은 없었어. 윗면에 무언가 붙였는지는 여기서 모르겠어.',{},p.mark==='side'?[['함',['가지다','표식'], '움직이다'],['함',['아니다',['가지다','표식']],'움직이다']]:[['표식',['아니다','보이다']]]);
 }
 if(q.word==='함'||q.word==='움직이다'){
  if(past)return R(s,true,'처음에는 책이 든 함의 열린 뚜껑을 봤어. 다음에는 닫힌 옆판만 봤지. 모양이 같아서 같은 함이라고 생각했어. 밑바퀴나 윗면을 확인한 것은 아니야.',{},[['책',['있다','함']],['함','움직이다']]);
  return R(s,true,s.lastPass?(s.lastPass.mark==='side'?'옆 표식이 멀어진 창과, 표식 없는 함이 다가온 창이 달랐어. 한 물체가 모퉁이를 돌아 되돌아왔는지는 표식 없이 구별할 수 없어.':'시험 동안 한 창에서 옆판이 멀어지고 반대 창에서 옆판이 다가왔어. 표식이 안 보여서 같은 몸인지는 모르겠어.'):'아직 손잡이로 움직이는 시험을 보지 못했어. 지금은 옆판 하나만 가만히 보여.');
 }
 if(q.word==='저울'||q.word==='무겁다'){
  const v=reading(s);return R(s,true,(s.pin?'핀에 걸린 바늘이 ':'자유롭게 움직이는 바늘이 ')+(v==='inner'?'안쪽 받침의 무게를 가리켜. 창 밑 받침에는 무게가 없어.':v==='window'?'안쪽은 가벼워지고 창 밑 받침에 무게가 실린 것을 가리켜.':'안쪽과 창 밑 받침 모두 가벼운 쪽을 가리켜.')+(s.pin?' 이건 바늘을 붙잡아 둔 표시야.':''),{},v==='inner'?[['안쪽','무겁다']]:v==='window'?[['창','무겁다']]:[['저울',['아니다','무겁다']]]);
 }
 if(q.word==='창')return R(s,true,'앉은 자리의 두 낮은 창은 함의 옆판만 보여. 윗면, 밑바퀴와 닫힌 함 안은 보이지 않아. 움직임은 창을 지날 때 볼 수 있어.',{},[['함','보이다'],['책',['아니다','보이다']]]);
 if(q.word==='그물')return R(s,true,'바닥 그물은 고정된 틀에 매달려 있어. 떨어진 것이 그물에 남으면 안쪽 받침에 무게가 걸려. 운반함과 함께 움직이지는 않아.');
 if(q.word==='문')return R(s,true,'받는 쪽은 도착한 기록을 꺼내면 수령판을 눌러. 오늘 나는 그 판을 직접 확인하지는 못했어. 문을 열어 달라면 열어 줄 수 있어.');
 return R(s,false,'그 관찰은 내가 본 적이 없어요. 예전의 책과 함, 지금 창으로 보이는 표식·함, 저울 바늘은 말해 줄 수 있어요.');
},solutions:[]};
function worldAction(s,action){let c={},msg='',ok=true;switch(action){
case 'lid':c.lid=!s.lid;msg=s.position===2&&!s.carrying&&!s.delivered?'뚜껑 아래에 진료 기록의 봉인된 책이 놓여 있습니다.':'가까운 함의 바닥이 보입니다. 빈칸뿐입니다.';break;
case 'mark-top':if(s.position!==0)return R(s,false,'표식을 붙이려면 손잡이를 당겨 처음 함을 바깥 작업 자리로 되돌려 주세요.');c.mark='top';msg='가까운 빈 함의 윗면에 종이 표식을 단단히 붙였습니다.';break;
case 'mark-side':if(s.position!==0)return R(s,false,'표식을 붙이려면 손잡이를 당겨 처음 함을 바깥 작업 자리로 되돌려 주세요.');c.mark='side';msg='가까운 빈 함의 옆둘레 전체에 종이띠를 둘렀습니다. 어느 옆에서 보아도 같은 띠가 보입니다.';break;
case 'mark-off':if(s.position!==0)return R(s,false,'처음 함을 작업 자리로 되돌린 뒤 표식을 뗄 수 있습니다.');c.mark='none';msg='표식을 떼었습니다.';break;
case 'pin':c.pin=!s.pin;if(!s.pin)c.heldReading=reading(s);msg=s.pin?'눈금 바늘을 붙잡던 고정핀이 빠졌습니다.':'고정핀이 지금 눈금을 붙잡았습니다.';break;
case 'push':if(s.position===1&&!s.latch)return R(s,false,'이미 시험 멈춤턱에 닿았습니다. 당기면 되돌아갑니다.');if(s.position===2){msg='돌아온 기록함이 바깥 멈춤턱에 닿아 있습니다.';break;}if(s.latch){c.position=2;c.lid=false;msg='표식 붙인 빈 함이 안으로 밀려갑니다. 반대 줄을 따라 다른 함이 바깥까지 나왔습니다.';}else{c.position=1;c.trialCount=s.trialCount+1;c.lastPass={mark:s.mark,direction:'push'};msg='가까운 함을 시험 거리만큼 밀었습니다. 멈춤턱에 닿아 더 밀리지 않습니다. 안쪽에서 줄 두 가닥이 반대로 움직입니다.';}break;
case 'pull':if(s.position===0)return R(s,false,'이미 바깥 작업 자리에 있습니다.');if(s.position===2){msg='함은 이미 바깥 멈춤턱에 있습니다.';break;}c.position=0;c.trialCount=s.trialCount+1;c.lastPass={mark:s.mark,direction:'pull'};msg='손잡이를 당기자 처음의 빈 함이 바깥 자리로 돌아왔습니다. 줄의 움직임도 되돌아갑니다.';break;
case 'basket':msg=s.basketUp?'올라온 수거그물은 비어 있습니다. 안쪽의 고정된 받침과 연결돼 있어 운반 줄과 함께 움직이지 않습니다.':'바깥에서는 수거그물을 들어 올린 채 안을 볼 수 없습니다. 창구 안의 당김줄과 연결돼 있습니다.';break;
case 'hatch':msg=s.hatchOpen?'수령판은 눌리지 않았고 진료소 쪽 보관칸도 비어 있습니다. 쪽지의 날짜는 오늘입니다.':'작은 수령문이 닫혀 있습니다. 창구 안에서 여는 걸쇠가 있습니다.';break;
case 'take':if(s.position!==2||s.carrying||s.delivered){msg='이 함에서 꺼낼 책이 없습니다.';ok=false;}else{c.carrying=true;c.lid=true;msg='진료 기록을 꺼냈습니다. 젖거나 찢어진 곳은 없습니다.';}break;
case 'deliver':if(!s.carrying){msg='지금은 창구에 놓을 진료 기록을 가지고 있지 않습니다.';ok=false;}else{c.carrying=false;c.delivered=true;c.complete=true;msg='기록원이 봉인을 확인하고 진료소에 보낼 기록을 다시 묶습니다. “책을 실은 함과 빈 채 온 함을 내가 같은 것으로 이었구나. 이제 어느 줄이 기록을 돌려보내는지 알겠어.”';}break;
default:return R(s,false,'그 물건에서 할 수 있는 행동을 골라 주세요.');}
const next={...s,...c};next.physicalLog=[...s.physicalLog,{action,position:next.position,mark:next.mark,pin:next.pin}];return R(next,ok,msg);}
sc.worldAction=worldAction;globalThis.SCENARIOS=[sc];globalThis.InvestigationRules={worldAction,reading,matchRelease};if(typeof module==='object')module.exports={sc,worldAction,reading,matchRelease};
})();
