(()=>{'use strict';
const eq=(t,s)=>JigsawCore.eq(t,s),R=(s,ok,message,changes={},speech=[])=>({state:{...s,...changes},ok,message,speech});
const A=(id,label,description,x)=>({id,label,description,x});
const items=[{
id:1,title:'울리지 않는 이유',theme:'무엇을 시험해야 원인이 갈릴까?',experimental:true,
goal:'멈춘 경보 장치의 고장 부위를 찾아 수리하세요.',
intro:'장치는 검사 모드라 아직 작동시킨 적이 없습니다. 전원·종·램프 중 정확히 하나가 고장입니다. 정비사와 이야기하면 부품 관계를 알 수 있어요.',
rule:'노랑 부품→파랑 시험하다로 그 부품을 시험하고, 부품→고치다로 수리합니다. 시험은 반복할 수 있습니다. 관측은 대화 기록에 남습니다.',
words:['전원','종','램프','받침','시험하다','고치다'],blueWords:['시험하다','고치다'],initial:{fault:"종",tested:[],repairs:0,complete:false},
actors:[A('mechanic','정비사','세 부품의 연결을 압니다',22),A('device','경보 장치','클릭하여 시험·수리할 대상',77)],
hint:['같은 결과를 내는 원인이 둘이면 그 관측만으로 원인을 정할 수 없어요. 각 고장일 때 종과 램프가 어떻게 될지 비교하세요.','전원이 고장 나면 종과 램프가 모두 꺼져요. 한 부품만 움직이면 전원은 살아 있습니다.'],
inspect(id,s){return id==='mechanic'?R(s,false,'전원이 종과 램프 둘에 힘을 줘요. 종과 램프는 서로 영향을 주지 않아요. 셋 중 딱 하나만 고장입니다. 받침 시험은 부품을 건드리지 않고 장치만 흔들어요. 모든 수리는 되돌릴 수 있지만 멀쩡한 부품을 바꾸면 헛수고예요.') : R(s,false,s.tested.length?'기록: '+s.tested.join(' / '):'아직 시험하지 않았습니다. 전원 자체는 밀봉되어 직접 시험할 수 없어요. 종과 램프의 반응으로 판단해야 합니다.');},
submit(t,s,l){if(l!=='device')return R(s,false,'정비사: 원격으로 장치를 만질 수는 없어요. 경보 장치를 골라 조작해 주세요.');
for(const word of ['종','램프','받침','전원'])if(eq(t,[word,'시험하다'])){if(word==='전원')return R(s,false,'전원은 밀봉되어 직접 볼 수 없습니다. 연결된 두 부품은 따로 시험할 수 있어요.');const msg={종:s.fault==='전원'||s.fault==='종'?'종: 울리지 않는다':'종: 맑게 울린다',램프:s.fault==='전원'||s.fault==='램프'?'램프: 켜지지 않는다':'램프: 밝게 켜진다',받침:'받침: 장치가 흔들린다. 어떤 고장에서도 같은 결과다'}[word];return R(s,true,msg,{tested:[...s.tested,msg]});}
for(const word of ['종','램프','전원','받침'])if(eq(t,[word,'고치다'])){if(word===s.fault)return R(s,true,word+' 부품을 수리하자 종과 램프가 모두 정상으로 작동합니다.',{repairs:s.repairs+1,complete:true});return R(s,false,word+'은 정상입니다. 원래대로 돌려놓았습니다. 아직 경보는 울리지 않습니다.',{repairs:s.repairs+1});}
return R(s,false,'장치: 부품에 시험하다 또는 고치다를 연결해 주세요.');},
solutions:[{listener:'device',spec:['종','시험하다']},{listener:'device',spec:['램프','시험하다']},{listener:'device',spec:['종','고치다']}]
},{
id:2,title:'안전해도 건너지 않는 사람',theme:'세계가 달라져도 믿음은 남는다',experimental:true,
goal:'겁먹은 여행자가 스스로 안전함을 확인하고 수문 옆 다리를 건너게 도와주세요.',
intro:'배관 수리는 끝났습니다. 이제 수문을 열면 물은 다리 대신 옆 수로로 흐릅니다. 여행자는 수리 전 홍수만 기억하며 벽 뒤에 서 있습니다.',
rule:'사람→가다→장소로 이동을 부탁합니다. 수문→열다/닫다는 기사에게, 여행자→건너다는 여행자에게 말합니다. 인물은 자신이 볼 수 있는 변화만 기억합니다.',
words:['여행자','관찰창','벽뒤','수문','열다','닫다','가다','건너다','안전하다'],blueWords:['열다','닫다','가다','건너다','안전하다'],
initial:{atWindow:false,open:false,witnessed:false,complete:false},
actors:[A('traveler','여행자','벽 뒤에서 홍수를 걱정합니다',19),A('engineer','수로 기사','배관 수리를 마쳤습니다',81)],
hint:['기사와 당신이 아는 안전을 여행자는 보지 못했습니다. 여행자가 무엇을 볼 수 있는지 바꿔 보세요.','관찰창에서는 흐르는 수로가 보입니다. 여행자가 그곳에 있을 때 물이 흐르면 직접 확인할 수 있어요. 이미 열려 있어도 관찰창으로 이동하면 볼 수 있습니다.'],
inspect(id,s){if(id==='engineer')return R(s,false,s.open?'물이 옆 수로로 흐르고 있어요. 다리는 마릅니다. 벽 뒤에서는 수로가 안 보이고, 관찰창에서는 보입니다.':'새 배관은 물을 옆 수로로 보내요. 여행자는 공사 때 없었어요. 관찰창은 안전해서 물이 흘러도 접근할 수 있어요.');return R(s,false,s.witnessed?'내가 직접 봤어요. 물은 다리를 덮지 않네요. 이제 건널 수 있어요.':s.atWindow?'관찰창에 왔어요. 지금은 물이 안 흐르네요. 열었을 때도 안전한지 아직 모르겠어요.':'수문이 열리면 다리가 잠겨요! 괜찮다는 말만으론 못 믿겠어요. 벽 뒤라 물길도 보이지 않아요.');},
submit(t,s,l){if(l==='engineer'&&eq(t,['수문','열다']))return R(s,true,s.atWindow?'여행자가 물이 옆 수로로 흐르고 다리가 마른 것을 봤습니다. “내가 알던 물길이 아니네!”':'물은 안전하게 옆 수로로 흐릅니다. 벽 뒤 여행자는 이 변화를 보지 못했습니다.',{open:true,witnessed:s.witnessed||s.atWindow});
if(l==='engineer'&&eq(t,['수문','닫다']))return R(s,true,'물이 멈췄습니다. 직접 보았던 기억은 남습니다.',{open:false});
if(l==='traveler'&&eq(t,['여행자',['가다','관찰창']]))return R(s,true,s.open?'여행자가 관찰창에서 실제 물길과 마른 다리를 보고 안심했습니다.':'여행자가 안전한 관찰창으로 이동했습니다. 수문은 아직 닫혀 있습니다.',{atWindow:true,witnessed:s.witnessed||s.open});
if(l==='traveler'&&eq(t,['여행자',['가다','벽뒤']]))return R(s,true,'여행자가 벽 뒤로 돌아갔습니다. 이미 본 사실은 잊지 않습니다.',{atWindow:false});
if(l==='traveler'&&eq(t,['여행자','건너다']))return s.witnessed?R(s,true,'여행자가 자신의 기억을 고치고 다리를 건넜습니다. 다음에 수문이 열려도 같은 공포를 반복하지 않을 것입니다.',{complete:true}):R(s,false,'여행자: 지금 안 잠겨 있어도 건너는 동안 열리면요? 물이 흐를 때도 다리가 안전한지 직접 보고 싶어요.');
if(eq(t,['수문','안전하다']))return R(s,false,'여행자: 안전하다는 말은 들었지만 예전 홍수를 봤어요. 바뀐 물길을 직접 확인해야 믿을 수 있어요.');
return R(s,false,l==='engineer'?'기사: 수문을 열거나 닫는 일은 제가 할게요. 여행자의 이동은 그 사람에게 부탁해 주세요.':'여행자: 안전한 곳으로 이동하거나 다리를 건너는 부탁은 들을 수 있어요.');},
solutions:[{listener:'traveler',spec:['여행자',['가다','관찰창']]},{listener:'engineer',spec:['수문','열다']},{listener:'traveler',spec:['여행자','건너다']}]
},{
id:3,title:'열어 달라, 닫아 달라',theme:'반대인 요구 뒤에 있는 목적',experimental:true,
goal:'정원사와 물고기 돌보미가 함께 받아들일 수문 상태를 만드세요.',
intro:'정원사는 “수문을 열어!” 돌보미는 “수문을 닫아!”라고 말합니다. 장치는 안전한 시험 수조라 어떤 조작도 되돌릴 수 있습니다. 두 사람의 이유를 먼저 들어볼 수 있어요.',
rule:'질문→사람→원하다로 그 사람이 원하는 결과를 묻습니다. 격자/천→끼우다 또는 빼다, 수문→열다/닫다는 장치에 부탁합니다. 관찰 결과가 두 사람의 실제 목적을 함께 만족하면 합의합니다.',
words:['질문','정원사','돌보미','원하다','수문','열다','닫다','격자','천','끼우다','빼다'],blueWords:['질문','원하다','열다','닫다','끼우다','빼다'],
initial:{open:false,insert:'없음',gardenKnown:false,fishKnown:false,complete:false},
actors:[A('gardener','정원사','수문을 열어 달라고 합니다',10),A('keeper','물고기 돌보미','수문을 닫아 달라고 합니다',90),A('device','수문 장치','끼울 수 있는 격자와 천',72)],
hint:['두 사람은 문짝 자체를 좋아하거나 싫어하는 걸까요? 원하는 결과를 질문해 보세요.','천은 물과 물고기를 모두 막습니다. 넓은 격자는 물은 통과시키고 물고기는 남깁니다.'],
inspect(id,s){if(id==='gardener')return R(s,false,s.gardenKnown?'문짝 모양보다 화단에 물이 오는 게 필요해요. 물고기는 화단에 필요 없어요.':'수문을 열어 줘요. 내가 왜 원하는지는 물어봐도 돼요.');if(id==='keeper')return R(s,false,s.fishKnown?'수문 자체보다 물고기가 이 수조에 남는 게 중요해요. 물이 빠져도 바닥 웅덩이는 남아요.':'수문을 닫아 줘요! 내가 걱정하는 게 뭔지는 물어봐도 돼요.');return R(s,false,'현재 '+(s.open?'열림':'닫힘')+' / 끼운 것: '+s.insert+'. 격자 구멍은 물고기보다 작고 물은 통과합니다. 천은 물도 물고기도 막습니다. 한 번에 하나만 끼울 수 있고 문이 닫혀 있을 때 교체합니다. 열린 수문에서 물고기가 넘어가면 안전통에 모여 닫는 즉시 돌아옵니다.');},
submit(t,s,l){if(l==='gardener'&&eq(t,['질문',['정원사','원하다']]))return R(s,true,'정원사: 화단에 물이 흘러야 해요. 물고기까지 보내 달라는 건 아니에요.',{gardenKnown:true});if(l==='keeper'&&eq(t,['질문',['돌보미','원하다']]))return R(s,true,'돌보미: 물고기가 이 수조에 남으면 돼요. 물이 흐르는 건 괜찮아요. 바닥 웅덩이에는 물이 남아요.',{fishKnown:true});
if(l!=='device')return R(s,false,'주민: 원하는 결과는 말해 줄 수 있지만 장치는 직접 다루지 않아요. 장치에 조작을 부탁해 주세요.');
if(eq(t,['수문','닫다']))return R(s,true,'수문을 닫았습니다. 물고기는 원래 수조에 있습니다. 화단에는 물이 가지 않습니다.',{open:false});
if(eq(t,['수문','열다'])){if(s.insert==='격자')return R(s,true,'물은 격자를 통과해 화단으로, 물고기는 수조에 남습니다. 정원사와 돌보미가 함께 고개를 끄덕입니다. “내가 바라던 건 그거예요.”',{open:true,complete:true});return R(s,true,s.insert==='천'?'천이 물과 물고기를 모두 막습니다. 돌보미는 안심하지만 정원사는 마른 화단을 가리킵니다.':'물과 물고기가 함께 넘어갑니다. 정원사는 안심하지만 돌보미는 안전통에 모인 물고기를 가리킵니다.',{open:true});}
for(const w of ['격자','천']){if(eq(t,[w,'끼우다']))return s.open?R(s,false,'물이 흐르는 중이라 교체할 수 없습니다. 수문을 닫으면 손이 닿습니다.'):R(s,true,w+'을 끼웠습니다. 이제 수문 상태를 바꿔 결과를 볼 수 있습니다.',{insert:w});if(eq(t,[w,'빼다']))return s.open?R(s,false,'수문이 열린 동안은 끼운 것을 빼지 않습니다.'):R(s,true,w+'을 뺐습니다.',{insert:s.insert===w?'없음':s.insert});}
return R(s,false,'장치: 수문에 열다·닫다, 격자나 천에 끼우다·빼다를 연결해 주세요.');},
solutions:[{listener:'gardener',spec:['질문',['정원사','원하다']]},{listener:'keeper',spec:['질문',['돌보미','원하다']]},{listener:'device',spec:['격자','끼우다']},{listener:'device',spec:['수문','열다']}]
}];
globalThis.SCENARIOS=items;if(typeof module==='object')module.exports=items;
})();
