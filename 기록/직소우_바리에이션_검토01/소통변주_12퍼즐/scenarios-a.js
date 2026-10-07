(function(){
'use strict';
const eq=(tree,spec)=>globalThis.JigsawCore.eq(tree,spec);
const any=(tree,specs)=>specs.some(s=>eq(tree,s));
const out=(state,ok,message,speech)=>({state,ok,message,...(speech?{speech}:{})});
const copy=s=>JSON.parse(JSON.stringify(s));
const INS=['안',['주민',['손','차갑다']]], OUT=['밖',['주민',['발','아프다']]];
const items=[
{id:1,title:'두 사람의 나',theme:'진료소 · 관점 전달',goal:'진료 담당자에게 두 환자의 서로 다른 불편을 전달하자.',experimental:false,
intro:'진료 담당자는 커튼 때문에 환자를 볼 수 없다. 안쪽과 바깥 대기석의 환자가 각자 자기 몸을 말한다. 담당자에게 누구의 어느 부위인지 전해 주자.',
words:['나','주민','안','밖','손','발','차갑다','아프다'],blueWords:['차갑다','아프다'],
hint:['환자가 말한 나와 네가 말하는 나는 같은 사람일까?','담당자에게 안쪽 주민의 손 상태와 바깥 주민의 발 상태를 각각 전한다.'],
actors:[{id:'inside',label:'안쪽 환자',role:'patient',color:'#8da69b',x:24,description:'안쪽 대기석. 손을 품 안에 넣고 있다.',speech:[['나',['손','차갑다']]]},{id:'outside',label:'바깥 환자',role:'patient',color:'#b4a084',x:54,description:'바깥 대기석. 한쪽 발을 들고 있다.',speech:[['나',['발','아프다']]]},{id:'doctor',label:'진료 담당자',role:'doctor',color:'#8b91af',x:82,description:'커튼 너머. 두 환자의 상태를 기다린다.',speech:[]}],initial:{reported:[],complete:false},
inspect(id,s){const a=this.actors.find(a=>a.id===id);return out(copy(s),true,id==='doctor'?'담당자가 안쪽과 바깥 대기석 표지를 번갈아 짚는다.':'환자가 자기 몸을 가리키며 말한다.',a.speech)},
submit(t,s,l){const n=copy(s);if(l!=='doctor')return out(n,false,'환자가 진료 담당자가 있는 쪽을 가리킨다.');let key=eq(t,INS)?'inside':eq(t,OUT)?'outside':null;if(!key)return out(n,false,'담당자가 대기석 두 곳을 짚는다. 네 몸이 아니라 어느 환자의 어느 부위인지 알려 달라는 뜻이다.');if(n.reported.includes(key))return out(n,true,'담당자가 이미 적어 둔 같은 기록을 보여 준다. 다른 환자의 불편도 기다린다.');n.reported.push(key);n.complete=n.reported.length===2;return out(n,true,n.complete?'담당자가 안쪽 환자에게 손 덮개를, 바깥 환자에게 발 받침을 준비한다.':'담당자가 한 환자의 상태를 기록하고 다른 대기석을 가리킨다.');},
solutions:[{listener:'doctor',spec:INS},{listener:'doctor',spec:OUT}]},
{id:2,title:'창 너머에서 아는 것',theme:'수문 · 청자의 정보',goal:'책을 가진 주민의 통과 요청을 수문장에게 전하자.',experimental:false,
intro:'책을 가진 주민이 문을 지나고 싶어 한다. 수문장은 높은 창으로 안쪽과 바깥 대기선만 볼 수 있고 손에 든 물건은 가림막에 가려 보지 못한다. 네가 알아본 사람을 수문장도 찾게 말하자.',
words:['나','주민','안','밖','책','열쇠','문','가지다','가다'],blueWords:['가지다','가다'],
hint:['네가 본 물건을 수문장도 볼 수 있을까?','책 소유자는 안쪽 대기선에 있다. 수문장에게 위치로 특정한 주민의 통과 요청을 전한다.'],
actors:[{id:'inside',label:'안쪽 대기 주민',role:'resident',color:'#9d9ab4',x:25,description:'책을 든 손은 낮은 가림막 아래에 있다.',speech:[['나',['가지다','책'],['가다','문']]]},{id:'outside',label:'바깥 대기 주민',role:'resident',color:'#b49d7e',x:51,description:'열쇠를 들고 바깥 대기선에 서 있다.',speech:[['나',['가지다','열쇠']]]},{id:'guard',label:'높은 창의 수문장',role:'guard',color:'#879f91',x:84,description:'대기선은 보지만 가림막 아래 소지품은 보지 못한다.',speech:[]}],initial:{complete:false},
inspect(id,s){return out(copy(s),true,id==='guard'?'수문장이 창 아래의 가림막을 짚고, 안쪽과 바깥 대기선을 가리킨다.':'주민이 자기 소지품을 보이며 말한다.',this.actors.find(a=>a.id===id).speech)},
submit(t,s,l){const n=copy(s);if(l!=='guard')return out(n,false,'주민이 위쪽 창의 수문장을 바라본다.');if(any(t,[['안',['주민',['가다','문']]],['안',['주민',['가지다','책'],['가다','문']]]])){n.complete=true;return out(n,true,'수문장이 안쪽 대기선의 주민을 확인하고 문을 연다. 책을 든 주민이 지나간다.');}if(eq(t,['밖',['주민',['가다','문']]]))return out(n,false,'수문장이 바깥 주민을 부른다. 열쇠를 든 주민은 고개를 젓고, 책을 든 주민은 안쪽에서 기다린다.');return out(n,false,'수문장이 손을 펴 보인다. 소지품은 창에서 보이지 않는다. 자신이 볼 수 있는 위치로 알려 달라는 몸짓이다.');},
solutions:[{listener:'guard',spec:['안',['주민',['가다','문']]]}]},
{id:3,title:'상자가 멈춘 자리',theme:'사고 현장 · 증언 연결',goal:'정비 담당자에게 누가 무엇을 밀어 어느 곳을 막았는지 설명하자.',experimental:false,
intro:'문 앞에 상자가 멈춰 통로가 막혔다. 안쪽 목격자는 누가 상자를 움직였는지 봤고, 바깥 목격자는 문이 막힌 마지막 모습만 봤다. 정비 담당자가 손댈 대상을 고를 수 있도록 두 증언을 한 관계로 연결하자.',
words:['주민','책','열쇠','상자','문','가지다','밀다','막다'],blueWords:['가지다','밀다','막다'],
hint:['한 목격자는 행동한 사람을, 다른 목격자는 상자와 문의 관계를 알려 준다.','책을 가진 주민의 밀기와, 그 상자가 문을 막는 상태를 같은 상자에 이어 설명한다.'],
actors:[{id:'inside',label:'안쪽 목격자',role:'witness',color:'#8aa59c',x:23,description:'상자가 움직이기 시작할 때를 보았다.',speech:[['주민',['가지다','책'],['밀다','상자']]]},{id:'outside',label:'바깥 목격자',role:'witness',color:'#b0a07b',x:49,description:'하나뿐인 상자가 문 앞에 멈추는 것을 보았다.',speech:[['상자',['막다','문']]]},{id:'mechanic',label:'정비 담당자',role:'expert',color:'#8c93ad',x:82,description:'문과 상자 중 무엇부터 살펴볼지 기다린다.',speech:[]}],initial:{complete:false},
inspect(id,s){return out(copy(s),true,id==='mechanic'?'담당자가 상자와 문을 번갈아 짚는다.':'목격자가 자신이 본 부분을 말한다.',this.actors.find(a=>a.id===id).speech)},
submit(t,s,l){const n=copy(s);if(l!=='mechanic')return out(n,false,'목격자는 정비 담당자에게 설명해 달라고 손짓한다.');if(eq(t,['주민',['가지다','책'],['밀다',['상자',['막다','문']]]])){n.complete=true;return out(n,true,'담당자가 문을 뜯으려던 손을 멈추고, 주민에게 상자가 밀린 방향을 확인한다. 함께 상자를 비켜 통로를 연다.');}if(eq(t,['주민',['가지다','책'],['밀다','상자']]))return out(n,false,'누가 밀었는지는 알았다. 담당자가 상자 다음으로 어디에 문제가 생겼는지 되묻는다.');if(eq(t,['상자',['막다','문']]))return out(n,false,'막힌 곳은 알았다. 담당자가 상자를 움직인 주민을 찾아 어떻게 밀었는지 확인하려 한다.');return out(n,false,'담당자가 목격자 두 사람을 가리킨다. 움직인 주민, 상자, 막힌 문이 하나의 설명에 연결되어야 한다.');},
solutions:[{listener:'mechanic',spec:['주민',['가지다','책'],['밀다',['상자',['막다','문']]]]}]},
{id:4,title:'뒤바뀐 부탁',theme:'대기실 · 전달 수정',goal:'전달자가 잘못 옮긴 이동 부탁을 바로잡자.',experimental:false,
intro:'안쪽 주민이 자기 부탁을 전해 달라고 했지만 전달자가 대상을 바꾸어 적었다. 조립판에는 전달자의 초안이 있다. 원래 말한 사람과 가려는 곳을 확인하고 전달자에게 수정본을 말하자.',
words:['나','주민','안','밖','가다'],blueWords:['가다'],
hint:['조립판의 앞쪽 장소는 주민을 특정하고, 가다 뒤 장소는 목적지다.','원래 말한 사람은 안쪽에 있다. 그 주민이 밖으로 가려는 부탁을 전달자에게 말한다.'],
actors:[{id:'inside',label:'안쪽 주민',role:'resident',color:'#9da68c',x:25,description:'안쪽에 앉아 바깥 바람을 쐬고 싶어 한다.',speech:[['나',['가다','밖']]]},{id:'outside',label:'바깥 주민',role:'resident',color:'#b2a08d',x:50,description:'자신이 불리자 어리둥절해한다.',speech:[]},{id:'messenger',label:'전달자',role:'messenger',color:'#889fb0',x:82,description:'위치와 목적지가 뒤바뀐 초안을 들고 있다.',speech:[['밖',['주민',['가다','안']]]]}],
starter:['밖',['주민',['가다','안']]],initial:{complete:false},
inspect(id,s){return out(copy(s),true,id==='outside'?'바깥 주민이 자신을 가리키며 고개를 젓는다.':id==='messenger'?'전달자가 자신이 옮겨 적은 말을 보여 준다.':'안쪽 주민이 자기를 가리키고 바깥으로 손을 내민다.',this.actors.find(a=>a.id===id).speech)},
submit(t,s,l){const n=copy(s);if(l!=='messenger')return out(n,false,'수정한 부탁은 전달자에게 알려 주자.');if(eq(t,['안',['주민',['가다','밖']]])){n.complete=true;return out(n,true,'전달자가 두 장소의 역할을 확인하고 부탁을 고친다. 안쪽 주민이 바깥으로 나와 고개를 끄덕인다.');}if(eq(t,['밖',['주민',['가다','안']]]))return out(n,false,'전달자가 원래 초안과 같다고 보여 준다. 바깥 주민은 자신의 부탁이 아니라고 고개를 젓는다.');return out(n,false,'전달자가 부탁한 주민과 목적지를 따로 짚는다. 어느 주민이 어디로 가려는지 다시 확인하자.');},
solutions:[{listener:'messenger',spec:['안',['주민',['가다','밖']]]}]},
{id:5,title:'한 사람의 두 불편',theme:'진료 대기실 · 공유 대상',goal:'손이 차갑고 발도 아픈 같은 환자를 진료 담당자에게 알려 주자.',experimental:false,
intro:'환자 셋이 기다린다. 손이 차가운 환자는 둘, 발이 아픈 환자도 둘이다. 담당자는 두 불편을 함께 겪는 한 사람을 먼저 부르려 한다. 두 상태가 같은 주민의 몸인지 드러내자.',
words:['나','주민','손','발','차갑다','따뜻하다','아프다','편하다'],blueWords:['차갑다','따뜻하다','아프다','편하다'],
hint:['한 가지 상태만 말하면 두 환자가 자신을 가리킨다.','주민 하나에서 손의 차가움과 발의 아픔으로 갈라지는 두 가지를 만든다.'],
actors:[{id:'left',label:'왼쪽 환자',role:'patient',color:'#aaa183',x:16,description:'두 손을 덮고 발을 편히 내려놓았다.',speech:[['나',['손','차갑다'],['발','편하다']]]},{id:'middle',label:'가운데 환자',role:'patient',color:'#a393ad',x:39,description:'손을 덮고 한쪽 발을 들고 있다.',speech:[['나',['손','차갑다'],['발','아프다']]]},{id:'right',label:'오른쪽 환자',role:'patient',color:'#7d9fa0',x:63,description:'손을 펴고 한쪽 발을 들고 있다.',speech:[['나',['손','따뜻하다'],['발','아프다']]]},{id:'doctor',label:'진료 담당자',role:'doctor',color:'#91a387',x:86,description:'두 불편이 함께 있는 환자를 부르려 한다.',speech:[]}],initial:{complete:false,selected:null},
inspect(id,s){return out(copy(s),true,id==='doctor'?'담당자가 한 사람의 손과 발을 함께 살펴보는 몸짓을 한다.':'환자가 자신의 손과 발 상태를 차례로 말한다.',this.actors.find(a=>a.id===id).speech)},
submit(t,s,l){const n=copy(s);if(l!=='doctor')return out(n,false,'환자가 진료 순서를 정하는 담당자를 가리킨다.');if(eq(t,['주민',['손','차갑다'],['발','아프다']])){n.complete=true;n.selected='middle';return out(n,true,'가운데 환자가 손과 발을 함께 가리킨다. 담당자가 그 환자를 진료석으로 부른다.');}if(any(t,[['주민',['손','차갑다']],['손','차갑다']]))return out(n,false,'왼쪽과 가운데 환자가 함께 손을 든다. 둘을 구별할 다른 불편이 필요하다.');if(any(t,[['주민',['발','아프다']],['발','아프다']]))return out(n,false,'가운데와 오른쪽 환자가 함께 발을 가리킨다. 둘을 구별할 다른 불편이 필요하다.');return out(n,false,'담당자가 한 사람을 가리킨 뒤 손과 발을 짚는다. 두 불편이 같은 주민에게 연결되는지 확인하자.');},
solutions:[{listener:'doctor',spec:['주민',['손','차갑다'],['발','아프다']]}]},
{id:6,title:'장치를 아는 사람',theme:'진료실 · 전문지식 나누기',goal:'관리인과 함께 주민의 불편을 줄일 방법을 정하자.',experimental:false,
intro:'환자는 가림막 앞에, 장치 관리인은 그 뒤에 있다. 몸의 부위마다 상태가 다르다. 주민의 현재 상태와 필요한 변화를 전달해서 관리인이 알맞은 장치를 선택하도록 돕자.',
words:['나','주민','안','손','발','차갑다','따뜻하다'],blueWords:['차갑다','따뜻하다'],
hint:['차가운 부위를 알리는 말과, 데우고 싶은 부위를 알리는 말은 이 대화에서 역할이 다르다. 관리인은 현재 상태를 먼저 듣는다.','안쪽 주민의 손이 차갑다고 보고한 뒤, 관리인이 원하는 변화를 물으면 손이 따뜻해지는 상태를 전한다. 발이나 주민 전체로 범위를 넓히지 않는다.'],
actors:[{id:'patient',label:'안쪽 주민',role:'patient',color:'#9a9cb4',x:29,description:'손은 덮고 발은 따뜻한 받침에 올렸다.',speech:[['나',['손','차갑다'],['발','따뜻하다']]]},{id:'expert',label:'장치 관리인',role:'expert',color:'#95a486',x:78,description:'환자는 보이지 않지만 작은 손 덮개와 큰 난방 장치의 기능을 안다.',speech:[]}],initial:{reported:false,complete:false},
inspect(id,s){return out(copy(s),true,id==='patient'?'주민이 손과 발의 서로 다른 상태를 말한다.':s.reported?'관리인이 작은 덮개와 큰 난방기를 번갈아 가리킨다. 어느 부위를 데우려는지 기다린다.':'관리인이 상태 기록판을 펼친다. 보이지 않는 환자의 현재 상태부터 기다린다.',this.actors.find(a=>a.id===id).speech)},
submit(t,s,l){const n=copy(s);if(l!=='expert')return out(n,false,'주민이 장치를 맡은 관리인을 가리킨다.');const cold=any(t,[['안',['주민',['손','차갑다']]],['주민',['손','차갑다']],['주민',['손','차갑다'],['발','따뜻하다']],['안',['주민',['손','차갑다'],['발','따뜻하다']]]]),warm=any(t,[['안',['주민',['손','따뜻하다']]],['주민',['손','따뜻하다']],['손','따뜻하다'],['주민',['손','따뜻하다'],['발','따뜻하다']],['안',['주민',['손','따뜻하다'],['발','따뜻하다']]]]);if(cold){if(n.reported)return out(n,true,'관리인이 기록된 손의 차가움을 짚고, 이제 어느 부위를 데울지 다시 묻는다.');n.reported=true;return out(n,true,'관리인이 손의 차가움을 기록한다. 작은 손 덮개와 큰 난방기를 보이며, 원하는 변화의 범위를 묻는다.');}if(warm){if(!n.reported)return out(n,false,'관리인이 상태 기록판을 먼저 짚는다. 보이지 않는 환자가 지금 어떤 상태인지 알아야 한다.');n.complete=true;return out(n,true,'관리인이 방 전체 난방 대신 손 덮개를 작동한다. 발의 온도는 그대로 두고 손을 데운다.');}return out(n,false,n.reported?'관리인이 환자의 손과 발 중 어느 부위를 바꾸려는지 되묻는다.':'관리인이 환자를 볼 수 없다는 듯 가림막을 짚는다. 현재 불편을 먼저 알려 주자.');},
solutions:[{listener:'expert',spec:['주민',['손','차갑다']]},{listener:'expert',spec:['주민',['손','따뜻하다']]}]}
];
globalThis.SCENARIOS=[...(globalThis.SCENARIOS||[]),...items];
if(typeof module!=='undefined')module.exports=items;
})();
