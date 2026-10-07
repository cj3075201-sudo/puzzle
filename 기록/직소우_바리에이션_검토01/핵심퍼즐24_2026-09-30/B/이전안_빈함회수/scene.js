(()=>{let focus='note';const E=(t,a={},v)=>{const e=document.createElementNS('http://www.w3.org/2000/svg',t);for(const[k,x]of Object.entries(a))e.setAttribute(k,x);if(v!==undefined)e.textContent=v;return e;};
const data={
 note:{title:'진료소에서 돌아온 쪽지',text:'“오늘 보낸 기록은 아직 받지 못했습니다. 표지의 봉인은 풀지 말고 되찾아 주세요.” 쪽지 아래에는 기록원이 그린 운반함의 옆모습이 있습니다. 책이 든 모습과 빈 모습은 서로 떨어져 그려져 있습니다.',actions:[]},
 cart:{title:'바깥으로 온 운반함',text:'뚜껑은 위에, 넓은 옆판은 낮은 창 높이에 있습니다. 함 안을 살피거나 표식을 붙일 수 있습니다. 같은 표식을 두 곳에 동시에 붙일 수는 없습니다.',actions:[['lid','뚜껑 살피기'],['mark-top','윗면에 표식 붙이기'],['mark-side','옆둘레에 표식 두르기'],['mark-off','표식 떼기'],['take','책 꺼내기']]},
 window:{title:'두 개의 낮은 관찰창',text:'기록원의 자리에서만 안쪽 창을 들여다볼 수 있습니다. 바깥에서는 어두운 창턱과 지나가는 줄이 보입니다. 한 창은 바깥 함 옆판 높이이고 다른 창도 같은 높이에 있습니다.',actions:[]},
 handle:{title:'시험 손잡이',text:'밀기와 당기기를 작게 시험할 수 있습니다. 각 운반 줄의 빗장이 안전 멈춤턱을 붙잡습니다. 창구 안에서 해당 빗장을 풀어 잡으면 시험 거리보다 멀리 움직일 수 있습니다.',actions:[['push','함을 밀어 보기'],['pull','함을 당겨 보기']]},
 gauge:{title:'저울 고정핀',text:'낡은 표찰: “핀을 끼우면 바늘이 그때의 눈금을 붙잡음. 빈 운반함의 무게는 이미 빼 둠.” 안쪽 받침과 창 밑 받침의 바늘은 기록원 쪽을 향해 있습니다.',actions:[['pin','고정핀 올리기 / 내리기']]},
 basket:{title:'바닥 수거그물',text:'운반 중 떨어진 것을 받는 그물입니다. 그물의 무게는 안쪽 받침에 걸립니다. 그물은 고정된 틀에 달려 있어 함과 함께 움직이지 않습니다. 안에서 줄을 잡아 올리면 바깥에서 안을 살필 수 있습니다.',actions:[['basket','그물 안 살피기']]},
 hatch:{title:'진료소 쪽 수령문',text:'기록을 꺼내면 눌리는 수령판이 있습니다. 이 작은 문을 여는 걸쇠는 기록원 쪽에 있습니다.',actions:[['hatch','수령판 살피기']]},
 counter:{title:'기록원의 창구',text:'되찾은 책을 여기에 올려놓으면 기록원이 진료소 봉인을 확인할 수 있습니다.',actions:[['deliver','기록을 창구에 놓기']]}
};
function context(w){const d=data[focus],p=document.querySelector('#object-panel');if(!p)return;p.replaceChildren();const h=document.createElement('h3');h.textContent=d.title;p.append(h);const txt=document.createElement('p');txt.textContent=d.text;p.append(txt);const note=window.Core24?.getState()?.worldNote;if(note){const n=document.createElement('p');n.className='world-feedback';n.textContent=note;p.append(n);}if(focus==='gauge'){const st=document.createElement('p');st.className='physical-state';st.textContent=w.pin?'핀: 걸려 있음':'핀: 빠져 있음';p.append(st);}if(focus==='cart'){const st=document.createElement('p');st.className='physical-state';st.textContent='표식: '+(w.position===2?'지금 바깥 함에는 없음':{none:'없음',top:'윗면',side:'옆둘레'}[w.mark])+(w.carrying?' · 기록을 들고 있음':'');p.append(st);}const a=document.createElement('div');a.className='object-actions';for(const[id,label]of d.actions){const b=document.createElement('button');b.textContent=label;b.dataset.worldAction=id;b.onclick=()=>window.Core24.act(id);a.append(b);}p.append(a);}
window.InvestigationUI={render(sc,w){context(w);},select(id){focus=id;window.Core24.refresh();}};
window.Scene12={backdrop(svg,e,sc,w){
 const add=(t,a,v)=>{let n=e(t,a,v);svg.append(n);return n;},txt=(x,y,t,sz=13,c='#e6e4c9')=>add('text',{x,y,fill:c,'text-anchor':'middle','font-size':sz,'font-family':'P,sans-serif'},t);
 add('rect',{width:1200,height:260,fill:'#354e48'});add('path',{d:'M0 190H1200V260H0Z',fill:'#677663'});add('rect',{x:285,y:32,width:865,height:142,rx:12,fill:'#253a36',stroke:'#8b9c80','stroke-width':5});
 add('path',{d:'M300 146H1120M300 158H1120',stroke:'#a19d77','stroke-width':4});
 add('path',{d:'M477 140L501 140L493 133M845 158L821 158L829 166',stroke:'#d4c887','stroke-width':3,fill:'none'});
 const cartX=w.position===2?360:w.position===1?475:360;const g=e('g');g.append(e('rect',{x:cartX-45,y:96,width:90,height:59,rx:5,fill:'#a49266',stroke:'#d7cca2','stroke-width':3}));g.append(e('path',{d:`M${cartX-45} 96l14 -13h73l3 13`,fill:w.lid?'#333e35':'#c4b98b',stroke:'#d7cca2','stroke-width':2}));for(const x of[cartX-25,cartX+25])g.append(e('circle',{cx:x,cy:165,r:10,fill:'#1c3531',stroke:'#b6b393','stroke-width':2}));if(w.mark==='side'&&w.position!==2)g.append(e('rect',{x:cartX-8,y:96,width:16,height:59,fill:'#e7d5b4'}));if(w.mark==='top'&&w.position!==2)g.append(e('path',{d:`M${cartX-10} 83h19l5 13h-20Z`,fill:'#e7d5b4'}));if(w.lid&&w.position===2&&!w.carrying&&!w.delivered)g.append(e('rect',{x:cartX-28,y:99,width:51,height:35,rx:3,fill:'#839eaf',stroke:'#e3cd8a','stroke-width':3}));svg.append(g);
 add('rect',{x:543,y:61,width:175,height:88,rx:7,fill:'#566e61',stroke:'#c1c4a2','stroke-width':4});for(const x of[563,636])add('rect',{x,y:99,width:53,height:20,fill:'#172f2a',stroke:'#aab69a','stroke-width':3});txt(629,48,'관찰창');
 add('rect',{x:765,y:83,width:101,height:67,rx:8,fill:'#a9976c'});add('path',{d:w.pin?'M809 93v41h27':'M809 76v35h27',stroke:'#e8d89f','stroke-width':7,fill:'none'});txt(816,71,'고정핀');
 add('path',{d:'M938 70v103M918 99h40M918 122h40',stroke:'#aeb99b','stroke-width':6});add('path',{d:'M985 77h96v81h-96Z',fill:w.hatchOpen?'#182f29':'#7e8a69',stroke:'#c0c5a0','stroke-width':4});txt(1033,61,'수령문');
 add('path',{d:'M535 195h129l-13 38h-102Z',fill:'#586c55',stroke:'#acb897','stroke-width':3});for(let x=548;x<655;x+=20)add('path',{d:`M${x} 195l8 38`,stroke:'#acb897','stroke-width':2});txt(599,253,'수거그물');
 add('path',{d:'M388 219h78M427 192v44',stroke:'#d6cda4','stroke-width':8,'stroke-linecap':'round'});txt(432,253,'손잡이');
 add('rect',{x:200,y:198,width:114,height:31,fill:'#baa681',rx:3});txt(257,251,'창구');
 txt(960,210,w.position===2?'함 하나가 바깥에 나와 있다':w.position===1?'줄이 시험 거리에서 멈췄다':'시험 손잡이가 바깥 멈춤턱에 있다');
 const targets=[['note',251,55,75,55,'쪽지 읽기'],['cart',cartX-53,78,112,99,'돌아온 운반함 살피기'],['window',540,59,182,99,'관찰창 살피기'],['handle',381,185,98,70,'시험 손잡이 살피기'],['gauge',758,72,118,91,'저울 고정핀 살피기'],['basket',530,187,141,69,'수거그물 살피기'],['hatch',977,67,116,105,'수령문 살피기'],['counter',194,192,123,65,'기록 창구 살피기']];
 add('rect',{x:265,y:70,width:35,height:43,fill:'#e2d4b0',transform:'rotate(-8 265 70)'});add('path',{d:'M274 80h18M273 89h18M272 98h13',stroke:'#687162','stroke-width':2});
 for(const[id,x,y,width,height,label]of targets){const n=e('rect',{x,y,width,height,rx:5,fill:'transparent',class:'world-target',tabindex:0,role:'button','data-object':id,'aria-label':label});n.append(e('title',{},label));n.onclick=()=>window.InvestigationUI.select(id);n.onkeydown=evt=>{if(evt.key==='Enter'||evt.key===' '){evt.preventDefault();window.InvestigationUI.select(id);}};svg.append(n);}
},pose(){return{dx:0,dy:10};},decorate(){}};
})();
