/* 각 대화의 장소와 실행 결과. 기존 직소 조작과 별도인 순수 SVG 표시. */
window.Scene12={
backdrop(svg,E,s,w){
 const add=(tag,a,t)=>{const n=E(tag,a,t);svg.append(n);return n;};
 const label=(x,y,t)=>add('text',{x,y,'text-anchor':'middle',fill:'#d7ddbe','font-size':12,'font-family':'P,sans-serif'},t);
 const door=(x,open=false,crack=false)=>{add('path',{d:`M${x-48} 159V55Q${x} 6 ${x+48} 55V159`,fill:open?'#a8ba87':'#6d806b',stroke:'#9eaa82','stroke-width':7});if(!open)add('path',{d:`M${x} 48V151M${x-36} 98H${x+36}`,stroke:'#394f43','stroke-width':4});if(crack)add('path',{d:`M${x-5} 50L${x+10} 75L${x-5} 98L${x+13} 136`,stroke:'#f0c67e',fill:'none','stroke-width':4});};
 if([1,5,6,7,9].includes(s.id)){
  for(const x of [310,700,1000])add('path',{d:`M${x-80} 141H${x+80}M${x-66} 141V175M${x+66} 141V175`,stroke:'#c0b692','stroke-width':7});
  if([1,6].includes(s.id)){add('path',{d:'M720 34H795V160Q756 146 720 160Z',fill:'#adc0a3',opacity:.75});add('path',{d:'M730 37V151M747 37V148M766 37V152M784 37V152',stroke:'#758f76','stroke-width':3});label(758,21,'가림막');}
  label(88,44,'진료 대기실');
 }
 if(s.id===2){door(675,w.complete);label(674,25,w.complete?'통과':'통행문');add('rect',{x:884,y:34,width:170,height:115,rx:25,fill:'#829783',stroke:'#b6bd91','stroke-width':6});label(970,25,'높은 창');for(const x of[310,610]){add('rect',{x:x-69,y:127,width:138,height:33,fill:'#9da78a'});add('path',{d:`M${x-75} 171H${x+75}`,stroke:'#d5cb9b','stroke-width':3});}}
 if([3,4].includes(s.id)){door(680,w.complete);label(680,27,w.complete?'열린 통로':'통로');if(s.id===3){const bx=w.complete?745:625;add('rect',{x:bx,y:111,width:91,height:48,fill:'#b19a6d',stroke:'#534d39','stroke-width':3});add('path',{d:`M${bx} 111L${bx+91} 159M${bx+91} 111L${bx} 159`,stroke:'#6f6147','stroke-width':3});}}
 if(s.id===8){door(300,w.warmSent);label(300,26,'진료소');add('path',{d:'M795 162L915 114L1070 163M797 181L916 136L1070 181',stroke:'#b1b193','stroke-width':9,fill:'none'});label(916,76,w.coldStopped?'진입을 멈췄다':'차가운 다리');for(const [x,c] of [[w.warmSent?300:440,'#d7b678'],[w.coldStopped?760:878,'#88bac5']]){add('circle',{cx:x,cy:112,r:12,fill:c});add('path',{d:`M${x-12} 129L${x-18} 158H${x+18}L${x+12} 129Z`,fill:c});}}
 if(s.id===10){door(359,false);door(812,true);label(359,27,'서문 · 닫힘');label(812,27,'동문');if(w.complete)label(952,160,'짐꾼 통과 →');}
 if(s.id===11){door(600,false,w.checked||w.warned);label(600,25,w.checked?'균열을 확인한 문':'점검 중인 문');if(w.sourceRecorded)label(420,151,'✓ 발언 기록');if(w.warned)label(1090,147,'진입 보류');}
 if(s.id===12){door(624,w.holding);add('path',{d:w.onPlate?'M438 168H511L523 175H429Z':'M438 154H511L523 171H429Z',fill:w.onPlate?'#e9ce87':'#a6aa87',stroke:'#465d4c','stroke-width':3});label(475,194,'발판');label(624,27,w.holding?'문을 잡고 있다':'잠긴 문');if(w.crossed)label(964,155,'건넜다 →');}
},
pose(s,w,a){let dx=0,dy=0;if(s.id===2&&a.id==='guard')dy=-12;if(s.id===2&&w.complete&&a.id==='inside')dx=95;if(s.id===4&&w.complete&&a.id==='inside')dx=160;if(s.id===5&&w.complete&&a.id==='middle')dx=65;if(s.id===12){if(a.id==='suri')dx=w.crossed?430:w.onPlate?113:0;if(a.id==='moru'&&w.holding)dx=-156;}return{dx,dy};},
decorate(g,E,s,w,a){const add=(tag,attrs,t)=>g.append(E(tag,attrs,t));
 if(s.id===2&&a.id==='inside'){add('rect',{x:-27,y:109,width:20,height:26,rx:2,fill:'#d1c59b',stroke:'#625d47','stroke-width':2});add('path',{d:'M-17 111V133',stroke:'#8a8062'});}
 if(s.id===2&&a.id==='outside'){add('circle',{cx:-22,cy:119,r:5,fill:'none',stroke:'#ebce7f','stroke-width':3});add('path',{d:'M-22 124V138H-14',fill:'none',stroke:'#ebce7f','stroke-width':3});}
 if([1,5,6,9].includes(s.id)&&['patient','inside','outside','left','middle','right','suri','moru'].includes(a.id)){
  const cold=(s.id===1&&a.id==='inside')||(s.id===5&&a.id!=='right')||s.id===6||(s.id===9&&a.id==='moru');
  const warm=(s.id===6&&w.complete)||(s.id===9&&w.mitten&&a.id==='moru');
  if(cold||warm)add('circle',{cx:-40,cy:122,r:10,fill:warm?'#e8c06a':'#82c3d4',stroke:'#dbe4c3','stroke-width':2});
  if((s.id===1&&a.id==='outside')||(s.id===5&&a.id!=='left'))add('path',{d:'M22 156L30 161L21 167',fill:'none',stroke:'#ecb17d','stroke-width':3});
  if(s.id===9&&w.splint&&a.id==='suri')add('rect',{x:-52,y:116,width:21,height:13,rx:3,fill:'#d7c7a2',stroke:'#786d51','stroke-width':2});
 }
}
};
