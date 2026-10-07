const Scene24={draw(svg,E,sc,w,inspect,act){
 svg.replaceChildren(); const add=(tag,a,t,parent=svg)=>{const n=E(tag,a,t);parent.append(n);return n;};
 const text=(x,y,t,size=15,color='#304d4d',parent=svg)=>add('text',{x,y,'font-size':size,fill:color,'font-family':'P,sans-serif'},t,parent);
 const button=(id,label,fn)=>{const g=add('g',{'data-world':id,role:'button',tabindex:0,'aria-label':label,class:'world-target'});g.onclick=fn;g.onkeydown=e=>{if(e.key==='Enter'||e.key===' '){e.preventDefault();fn();}};add('title',{},label,g);return g;};
 const rect=(x,y,width,height,fill,parent=svg,extra={})=>add('rect',{x,y,width,height,fill,...extra},undefined,parent);
 const line=(x1,y1,x2,y2,stroke,width=2,parent=svg)=>add('line',{x1,y1,x2,y2,stroke,'stroke-width':width},undefined,parent);
 const outY=310-w.outsideLevel*10,inY=310-w.insideLevel*10;
 rect(0,0,1200,360,'#edf0df');rect(0,188,1200,172,'#8f9a81');
 rect(42,190,556,150,'#c6cfb4');rect(626,190,476,150,'#c6cfb4');
 const water=(id,x,y,width,label)=>{const g=button(id,label,()=>inspect(id));rect(x,y,width,340-y,'#79afb5',g);line(x,y,x+width,y,'#436f81',3,g);for(let i=x+15;i<x+width-20;i+=55)line(i,y+14,i+26,y+14,'#c2dfd8',2,g);return g;};
 water('outside',42,outY,556,'外 · 담장 밖 물');water('inside',626,inY,476,'內 · 수문실 부표');
 text(55,211,'바깥 수로',14);text(933,211,'수문실',14);
 line(58,270,588,270,'#a58655',1.5);text(60,266,'돌담의 물때 자국',11,'#716648');
 line(1090,222,1090,310,'#596857',3);line(1080,270,1100,270,'#a58655',3);
 rect(1077,inY-6,26,12,'#f0cb67',svg,{rx:4});text(1031,321,'안쪽 부표',12);
 const dock=button('dock','높은 선착장과 펌프',()=>inspect('dock'));rect(1110,215,90,15,'#a2825e',dock);rect(1130,230,13,108,'#766b50',dock);text(1087,184,'높은 선착장',15,'#304d4d',dock);rect(1165,245,25,55,'#728b78',dock,{rx:4});add('path',{d:'M1178 248 V236 H1150 V253',fill:'none',stroke:'#586858','stroke-width':7},undefined,dock);text(1160,320,'펌프',11,'#304d4d',dock);
 const gx=610;rect(gx-10,181,20,155,w.holding?'#8aad83':'#5c6a55');if(w.holding){rect(gx-10,222,20,105,'#d9e4cb');text(gx-17,351,'열림',12);}else{text(gx-17,351,w.mode==='blocked'&&w.lastCause==='early_release'?'걸림':'닫힘',12);}text(gx-15,174,'문',15);
 // Tall masonry wall blocks the keeper's direct sight of the external water.
 rect(303,60,110,131,'#9eaa92');for(let y=65;y<190;y+=26)line(306,y,410,y,'#bdc5ab');text(318,153,'돌담',15,'#435346');
 rect(430,23,510,154,'#d7d8bd',svg,{rx:10});text(443,46,'수문지기의 창',13);rect(617,60,303,98,'#809b85',svg,{rx:4});
 const keeper=button('keeper',w.mode==='shore'?'수문지기에게 말 걸기':'창 안 수문지기 살펴보기',()=>inspect('keeper'));
 rect(654,62,245,95,'transparent',keeper);
 add('circle',{cx:689,cy:93,r:20,fill:'#e9c294'},undefined,keeper);rect(665,113,50,39,'#566e5c',keeper,{rx:12});line(715,128,w.holding?756:727,w.holding?91:144,'#e9c294',9,keeper);text(726,83,w.mode==='shore'?'말 걸기':'창 안',14,'#f4f1d8',keeper);text(726,107,w.holding?'문을 붙드는 중':'손을 놓고 있다',13,'#f4f1d8',keeper);text(726,135,'배를 보는 옆 창',11,'#e4e9d8',keeper);
 add('path',{d:'M886 155 L905 176 L900 181',stroke:'#8c9d86','stroke-width':2,fill:'none','stroke-dasharray':'4 5'});
 const mirror=button('mirror','거울에 비친 현재 모습 살펴보기',()=>inspect('mirror'));rect(447,66,144,82,'#718877',mirror,{rx:5,stroke:'#e3c275','stroke-width':5});const reflected=w.mirror==='outside'?w.outsideLevel:w.insideLevel;const ry=140-reflected*5;rect(454,ry,130,141-ry,'#92c6cf',mirror);line(454,120,584,120,'#e3c275',2,mirror);text(457,85,'거울 · '+(w.mirror==='outside'?'담장 틈':'안쪽 부표'),12,'#f9f2d5',mirror);
 const handle=button('turn','거울 손잡이 돌리기',()=>act('turn'));add('circle',{cx:520,cy:163,r:12,fill:'#bfa673',stroke:'#6f674a','stroke-width':2},undefined,handle);line(511,170,529,156,'#615b45',3,handle);
 if(w.mirror==='outside')add('path',{d:'M449 94 L397 33 L375 53 L177 195',fill:'none',stroke:'#d2ad57','stroke-width':2,'stroke-dasharray':'6 5'});
 const shore=button('shore',w.mode==='shore'?'출발자리 살펴보기':'출발자리로 돌아오기',()=>w.mode==='shore'?inspect('boat'):act('back'));rect(0,305,150,28,'#a99066',shore);text(13,326,w.mode==='shore'?'출발자리':'← 돌아오기',15,'#fff8db',shore);
 const bx=70+w.boatBack*90,by=(w.boatBack>=6?inY:w.boatBack+2>=6?Math.min(inY,outY):outY)-5;
 const ship=button('boat',w.mode==='shore'?'배에 타기':w.mode==='voyage'?'배의 다음 움직임 보기':'배 살펴보기',()=>w.mode==='shore'?act('launch'):w.mode==='voyage'?act('step'):inspect('boat'));
 add('path',{d:`M${bx} ${by-10} L${bx+180} ${by-10} L${bx+157} ${by+15} L${bx+15} ${by+15} Z`,fill:'#986c49',stroke:'#614d38','stroke-width':3},undefined,ship);
 rect(bx+58,by-47,58,34,'#d1b980',ship,{rx:3});line(bx+87,by-46,bx+87,by-12,'#746d52',3,ship);text(bx+66,by-24,'책',14,'#594e35',ship);text(bx+8,by-16,'뒤',12,'#584530',ship);text(bx+145,by-16,'앞',12,'#584530',ship);
 const action=w.mode==='shore'?'배에 타기 →':w.mode==='voyage'?'배를 눌러 이어 보기 →':w.complete?'책 도착':'배가 멈췄다';text(bx+7,by+38,action,13,'#263f40',ship);
 text(15,26,'배·인물·거울·부표·선착장을 눌러 살펴보세요.',13,'#536a55');
 if(w.complete){rect(1108,181,38,32,'#d1b980');text(1118,203,'책',14,'#594e35');}
 // Include gaps between an object's art and label in the same pointer target.
 for(const target of svg.querySelectorAll('[data-world]')){const b=target.getBBox();target.prepend(E('rect',{x:b.x,y:b.y,width:b.width,height:b.height,fill:'transparent','pointer-events':'all','data-hitbox':'world','aria-hidden':'true'}));}
}};
