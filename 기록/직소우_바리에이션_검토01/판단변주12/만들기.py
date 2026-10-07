"""기존 직소우 외곽으로 보는 세 가지 판단 비교. 본편 구현 아님."""
from pathlib import Path
import ast,sys,json,io,base64,copy
from itertools import combinations

OUT=Path(__file__).resolve().parent
source=OUT.parent/'연결확장08/만들기.py'
tree=ast.parse(source.read_text())
names={'shape','part','transfer','check'};constants={'NORMAL','MID','OPP','COLORS'}
nodes=[n for n in tree.body if isinstance(n,(ast.Import,ast.ImportFrom)) or isinstance(n,ast.FunctionDef) and n.name in names or isinstance(n,ast.Assign) and any(isinstance(t,ast.Name) and t.id in constants for t in n.targets)]
ns={};exec(compile(ast.Module(body=nodes,type_ignores=[]),str(source),'exec'),ns)
part=ns['part'];transfer=ns['transfer'];check=ns['check'];shape=ns['shape']
def p(key,color,x,y,label,ports):return part(key,color,x,y,label,ports)
def port(side,kind='tab',profile='round'):return (side,kind,profile)
def give(reverse):
    ps=transfer('나' if reverse else '주민','주민' if reverse else '나','열쇠','주다')
    for t in ps:t['y']+=2
    target=ps[1 if reverse else 0]
    target['ports'].append(port('N','socket'))
    x,y=target['x'],target['y']
    ps.extend([p('house','yellow',x,y-2,'집',[port('S')]),p('inside','yellow',x,y-1,'안',[port('N','socket'),port('S')])])
    return ps
boards={
'1a':give(False),'1b':give(True),
'2a':[p('hand','yellow',0,0,'손',[port('E'),port('S')]),p('pain','blue',1,0,'아프다',[port('W','socket')]),p('cold','blue',0,1,'차갑다',[port('N','socket')])],
'2b':[p('hand','yellow',0,0,'손',[port('E')]),p('pain','blue',1,0,'아프다',[port('W','socket')]),p('foot','yellow',0,2,'발',[port('E')]),p('cold','blue',1,2,'차갑다',[port('W','socket')])],
'3a':[p('house','yellow',0,0,'집',[port('S')]),p('inside','yellow',0,1,'안',[port('N','socket'),port('S')]),p('resident','yellow',0,2,'주민',[port('N','socket'),port('S')]),p('go','blue',0,3,'가다',[port('N','socket')])],
'3b':[p('resident','yellow',0,1,'주민',[port('E')]),p('go','blue',1,1,'가다',[port('W','socket'),port('E')]),p('inside','yellow',2,1,'안',[port('N','socket'),port('W','socket')]),p('house','yellow',2,0,'집',[port('S')])]
}
expected={
'1a':{('actor','verb'),('object','verb'),('verb','other'),('house','inside'),('inside','actor')},
'1b':{('actor','verb'),('object','verb'),('verb','other'),('house','inside'),('inside','object')},
'2a':{('hand','pain'),('hand','cold')},'2b':{('hand','pain'),('foot','cold')},
'3a':{('house','inside'),('inside','resident'),('resident','go')},'3b':{('resident','go'),('go','inside'),('house','inside')}
}
checks={}
for key,ps in boards.items():
    checks[key]=check(ps)
    ports=[]
    for t in ps:
        for side,kind,profile in t['ports']:
            dx,dy=ns['MID'][side];ports.append((t['key'],side,kind,profile,(t['x']+dx,t['y']+dy)))
    directed=set()
    for a,b in combinations(ports,2):
        if a[4]==b[4] and ns['OPP'][a[1]]==b[1] and a[2]!=b[2]:
            tab,socket=(a,b) if a[2]=='tab' else (b,a)
            directed.add((tab[0],socket[0]))
    assert directed==expected[key],(key,directed)
    checks[key]['directed_connections']=sorted(directed)
    adj={t['key']:set() for t in ps}
    for a,b in directed:adj[a].add(b);adj[b].add(a)
    unseen=set(adj);components=[]
    while unseen:
        pending=[next(iter(unseen))];group=set()
        while pending:
            n=pending.pop()
            if n in group:continue
            group.add(n);pending.extend(adj[n]-group)
        unseen-=group;components.append(sorted(group))
    checks[key]['components']=components
    assert len(components)==(2 if key=='2b' else 1)
    yellows={t['key'] for t in ps if t['color']=='yellow'}
    for start in yellows:
        stack=[(start,{start})]
        while stack:
            here,seen=stack.pop();assert len(seen)<=3
            for a,b in directed:
                if a==here and b in yellows and b not in seen:stack.append((b,seen|{b}))
    checks[key]['yellow_chain_at_most_3']=True
for key in ['1a','1b']:
    ps=boards[key]
    assert [t['label'] for t in ps[:4]]==(['주민','나','주다','열쇠'] if key=='1a' else ['나','주민','주다','열쇠'])
    assert ps[0]['ports'][0]==port('S','tab','twin')

def svg(key):
    ps=boards[key];u=84;w=500;h=370
    maxx=max(t['x'] for t in ps)+1;maxy=max(t['y'] for t in ps)+1
    ox=(w-maxx*u)/2;oy=(h-maxy*u)/2
    out=[f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {w} {h}" class="jigsaw" role="img" aria-label="사례 {key} 직소우 조립">']
    for t in ps:
        poly=shape(t['ports'],t['x'],t['y']);coords=' L '.join(f'{ox+x*u:.3f},{oy+y*u:.3f}' for x,y in poly.exterior.coords)
        fill,stroke=ns['COLORS'][t['color']]
        sockets={side for side,kind,_ in t['ports'] if kind=='socket'}
        left=.23*u if 'W' in sockets else 0;right=.23*u if 'E' in sockets else 0
        top=.23*u if 'N' in sockets else 0;bottom=.23*u if 'S' in sockets else 0
        tx=ox+(t['x']+.5)*u+(left-right)/2;ty=oy+(t['y']+.5)*u+(top-bottom)/2
        size=min(22,(u-left-right-8)/len(t['label']))
        out.append(f'<g data-piece="{t["key"]}"><path d="M {coords} Z" fill="{fill}" stroke="{stroke}" stroke-width="1.7"/><text x="{tx}" y="{ty}" text-anchor="middle" dominant-baseline="central" font-size="{size:.2f}">{t["label"]}</text></g>')
    return ''.join(out)+'</svg>'
content=[
 dict(id='1',label='01 · 누가 주는가',tag='기존 규칙의 응용',title='같은 주민을 가리켜도, 주는 사람은 바뀐다',lead='‘집 안의 주민’은 그대로다. 두 갈래에 연결된 사람이 누구인지 함께 읽는다.',a_title='A · 주민이 주는 쪽',b_title='B · 내가 주는 쪽',a_read='<b>집 안의 주민이 나에게</b> 열쇠를 준다.',b_read='<b>내가 집 안의 주민에게</b> 열쇠를 준다.',a_note='두 갈래에는 주민, 일반 입력에는 나.',b_note='두 갈래에는 나, 일반 입력에는 주민.',situation='열쇠를 받으려는 대화와, 빌린 열쇠를 돌려주려는 대화를 구별한다.',decision='주민의 위치를 읽은 뒤에도, 주는 쪽과 받는 쪽을 확인해야 한다.',detail='‘집 안의 주민’을 읽는 판단과 주체를 읽는 판단을 함께 쓰는 응용이다. 두 판단이 결합했다는 이유만으로 새 깊이를 입증한 것은 아니다. 주민/나의 입력과 열쇠 출력은 유지하며, 위치 사슬은 계속 주민을 특정한다.'),
 dict(id='2',label='02 · 어디가 어떤 상태인가',tag='기존 분기의 활용',title='두 증상이 같은 부위인가, 다른 부위인가?',lead='‘아프다’와 ‘차갑다’를 알아도, 각각 어느 부위의 상태인지 읽어야 한다.',a_title='A · 손 하나에 두 상태',b_title='B · 손과 발에 나뉜 상태',a_read='<b>손이 아프고, 손이 차갑다.</b>',b_read='<b>손이 아프고, 발이 차갑다.</b>',a_note='손 조각 하나에서 두 파랑 조각으로 갈라진다.',b_note='손의 발화와 발의 발화가 따로 있다.',situation='크리처가 몸의 상태를 설명한다. 플레이어는 어느 부위를 더 살필지 판단한다.',decision='증상 단어만 보고 넘기면, 차가운 부위를 잘못 짚을 수 있다.',detail='한 대상의 두 상태 분기는 기존 수용 범위다. B는 두 개의 독립 발화이며, 빈 공간이 문장 연결 기호인 것은 아니다. A는 3피스, B는 4피스다. A도 손이 아프다 / 손이 차갑다로 나눠 같은 뜻을 말할 수 있으며 분기 사용을 정답으로 강제하지 않는다. 치료법이나 특정 질환을 정한 예시가 아니다.'),
 dict(id='3',label='03 · 장소가 무슨 역할인가',tag='새 연결 용례 후보',title='집 안에 있는 주민인가, 집 안으로 가는가?',lead='같은 ‘집·안·주민·가다’ 네 글자. 장소가 사람을 설명하는지, 이동할 곳인지 비교한다.',a_title='A · 집 안의 주민이 이동',b_title='B · 주민이 집 안으로 이동',a_read='<b>집 안의 주민</b>이 간다.',b_read='주민이 <b>집 안으로</b> 간다.',a_note='어느 주민인지 말한다. 도착지는 말하지 않는다.',b_note='어디로 갈지 말한다. 현재 위치는 말하지 않는다.',situation='여러 주민 중 집 안의 주민을 지칭하는 말과, 특정 주민에게 목적지를 전하는 말을 구별한다.',decision='장소 글자를 봤다고 무조건 그곳으로 가라는 뜻은 아니다.',detail='B의 가다 입력=이동 주체 / 출력=목적지라는 연결 용례는 이번 제안이며 아직 확정하지 않았다. 가다의 단순 주체에는 두 갈래를 붙이지 않는다. A가 집 밖으로 간다는 뜻이라고 단정하지 않는다. B의 안에는 집과 가다가 서로 다른 관계로 접합하므로, 이 형태를 실제 발화에서 가르치고 구별할 수 있는지가 후속 판단 대상이다.')
]
style='''*{box-sizing:border-box}body{margin:0;background:#f4f1e7;color:#263e48;font-family:P,"Malgun Gothic",sans-serif;line-height:1.55}main{max-width:1250px;padding:27px 30px 32px;margin:auto}.eyebrow{font-size:12px;color:#71828a;letter-spacing:.06em}h1{font-size:29px;margin:7px 0 8px}.intro{margin:0;color:#61727a;font-size:16px}nav{display:flex;gap:10px;margin:22px 0 25px}button{font:inherit;border:1px solid #bac5c4;border-radius:8px;background:#fffdf7;color:#365862;padding:11px 16px;cursor:pointer}button[aria-selected=true]{background:#315965;color:white;border-color:#315965}button:focus-visible,summary:focus-visible{outline:3px solid #9e711e;outline-offset:4px}.tag{font-size:12px;background:#e4e9e0;color:#556b59;padding:4px 8px;border-radius:5px;display:inline-block}.tag.candidate{background:#f4e4be;color:#7a5a20}h2{font-size:26px;margin:9px 0 5px}.lead{font-size:17px;margin:0;color:#4a6069}.grid{display:grid;grid-template-columns:1fr 1fr;gap:22px;margin-top:20px}.card{background:#fffdf7;border:1px solid #dad6c9;border-radius:12px;padding:17px 20px}.card h3{font-size:19px;margin:0}.jigsaw{width:100%;height:340px;display:block}.jigsaw text{font-family:inherit;fill:#284653}.reading{border-top:1px solid #ddd9cc;padding-top:13px;margin:0;font-size:20px}.reading b{font-weight:600;background:#f6e6b0;color:#71521f}.note{font-size:13px;color:#6e7c80;margin:6px 0 0}.context{background:#e6eae2;border-radius:9px;padding:14px 19px;margin-top:16px;font-size:16px}.context p{margin:0}.context p+p{margin-top:5px}.context strong{margin-right:10px}.foot{font-size:12px;color:#778382;margin-top:13px}details{font-size:13px;color:#647780;margin-top:12px}details p{max-width:1000px;margin:9px 0}summary{cursor:pointer}section[hidden]{display:none}@media(max-width:760px){main{padding:20px 14px}h1{font-size:25px}h2{font-size:23px}nav{display:grid;grid-template-columns:1fr;gap:7px;margin:18px 0}button{text-align:left;padding:9px 12px}.grid{grid-template-columns:1fr;gap:12px}.jigsaw{height:300px}.reading{font-size:18px}}'''
html='''<!doctype html><html lang="ko"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>직소우 · 세 가지 판단 바리에이션</title><style>__FONT__'''+style+'''</style></head><body><main><header><div class="eyebrow">JIGSAW LANGUAGE · 판단 변주 12</div><h1>노랑·파랑으로 생각하는 세 가지 방식</h1><p class="intro">탭을 눌러 비교해 봐. 각 사례의 왼쪽과 오른쪽은 서로 다른 뜻이다.</p></header><nav role="tablist" aria-label="바리에이션 선택">'''
for c in content:
    html+=f'<button type="button" role="tab" id="tab-{c["id"]}" aria-controls="case-{c["id"]}" aria-selected="{str(c["id"]=="1").lower()}" tabindex="{0 if c["id"]=="1" else -1}" data-case="{c["id"]}">{c["label"]}</button>'
html+='</nav>'
for c in content:
    i=c['id'];html+=f'<section id="case-{i}" role="tabpanel" aria-labelledby="tab-{i}" {"hidden" if i!="1" else ""}><span class="tag {"candidate" if i=="3" else ""}">{c["tag"]}</span><h2>{c["title"]}</h2><p class="lead">{c["lead"]}</p><div class="grid">'
    for side in ['a','b']:
        html+=f'<article class="card"><h3>{c[side+"_title"]}</h3>'+svg(i+side)+f'<p class="reading">{c[side+"_read"]}</p><p class="note">{c[side+"_note"]}</p></article>'
    html+=f'</div><div class="context"><p><strong>상황 예시</strong>{c["situation"]}</p><p><strong>생각할 점</strong>{c["decision"]}</p></div><details><summary>설계 범위와 남은 부분</summary><p>{c["detail"]}</p></details></section>'
html+='''<p class="foot">기존 원형·두 갈래 접합으로 만든 설명용 조립도. 노랑은 대상, 파랑은 행동·상태. 각 조각은 낱개이며 외곽 구성·장면은 비교 후보다.</p></main><script>
const tabs=[...document.querySelectorAll('[role=tab]')];
function showCase(id,focus=false){if(!['1','2','3'].includes(id))id='1';for(const b of tabs){const on=b.dataset.case===id;b.setAttribute('aria-selected',String(on));b.tabIndex=on?0:-1;document.getElementById('case-'+b.dataset.case).hidden=!on;if(on&&focus)b.focus()}history.replaceState(null,'','#case-'+id)}
for(const b of tabs){b.addEventListener('click',()=>showCase(b.dataset.case));b.addEventListener('keydown',e=>{const n=tabs.indexOf(b);let i;if(e.key==='ArrowRight')i=(n+1)%3;else if(e.key==='ArrowLeft')i=(n+2)%3;else if(e.key==='Home')i=0;else if(e.key==='End')i=2;else return;e.preventDefault();showCase(tabs[i].dataset.case,true)})}
showCase(location.hash.replace('#case-',''));window.addEventListener('hashchange',()=>showCase(location.hash.replace('#case-','')));
</script></body></html>'''
from fontTools import subset
from fontTools.ttLib import TTFont
font=TTFont(str(OUT.parents[2]/'기획서/source/assets/Pretendard-Regular.ttf'))
sub=subset.Subsetter();sub.populate(text=html);sub.subset(font);buf=io.BytesIO();font.save(buf)
html=html.replace('__FONT__','@font-face{font-family:P;src:url(data:font/ttf;base64,'+base64.b64encode(buf.getvalue()).decode()+')}')
(OUT/'보기.html').write_text(html)
(OUT/'도형과접합.json').write_text(json.dumps({'scope':'조립6개. 각 실제 포트 방향·접합·겹침·연속노랑3개 이하 검사. 2B는 두 독립 발화. 게임/학습/재미 검증 아님.','checks':checks,'boards':boards},ensure_ascii=False,indent=2))
print(json.dumps({k:{'pieces':v['pieces'],'connections':len(v['connections']),'components':len(v['components'])} for k,v in checks.items()},ensure_ascii=False))
