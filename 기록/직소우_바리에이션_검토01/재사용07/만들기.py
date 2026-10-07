"""관계 규칙/모형 재사용 비교. 본편 구현이 아닌 독립 설계 자료 생성기."""
from pathlib import Path
from itertools import combinations
import json,sys,io,base64,copy

from shapely.geometry import box,Point,Polygon
from shapely.ops import unary_union
from shapely.affinity import translate
from fontTools import subset
from fontTools.ttLib import TTFont

OUT=Path(__file__).resolve().parent
NORMAL={'N':(0,-1),'E':(1,0),'S':(0,1),'W':(-1,0)}
OPP={'N':'S','S':'N','E':'W','W':'E'}
MID={'N':(.5,0),'E':(1,.5),'S':(.5,1),'W':(0,.5)}
# 06의 검산된 원형/두 갈래 외곽 구성법을 그대로 재사용한다.
MODELS={
 'y_e':('yellow',[('E','tab','round')]),
 'y_s':('yellow',[('S','tab','round')]),
 'y_s2':('yellow',[('S','tab','twin')]),
 'y_e2':('yellow',[('E','tab','twin')]),
 'y_w':('yellow',[('W','socket','round')]),
 'send0':('blue',[('W','socket','round'),('N','socket','round'),('E','tab','round')]),
 'sendN':('blue',[('W','socket','round'),('N','socket','twin'),('E','tab','round')]),
 'pair0':('blue',[('W','socket','round'),('N','socket','round')]),
 'pairW':('blue',[('W','socket','twin'),('N','socket','round')]),
 'stateW':('blue',[('W','socket','round')]),
}
CASES={
 'send':dict(word='보내다',kind='action',mark='N',base='send0',explicit='sendN',palette=['send0','sendN','y_e','y_s','y_s2','y_w'],title='배운 관계',note='두 갈래의 대상이 보내는 쪽. 너는 도착 상대.',reuse='관계 규칙의 기준',pieces=4),
 'push':dict(word='밀다',kind='action',mark='W',base='pair0',explicit='pairW',palette=['pair0','pairW','y_e','y_e2','y_s'],title='방향이 달라도 같은 관계',note='두 갈래가 왼쪽으로 옮겨도 행동하는 쪽이라는 뜻은 같다.',reuse='규칙 재사용 · 파랑 외곽은 달라짐',pieces=3),
 'pull':dict(word='당기다',kind='action',mark='W',base='pair0',explicit='pairW',palette=['pair0','pairW','y_e','y_e2','y_s'],title='같은 모형에 다른 행동 글자',note='밀다의 모든 모형을 유지하고 행동 글자를 바꾼다.',reuse='밀다의 모형 5종 모두 재사용',pieces=3),
 'pain':dict(word='아프다',kind='state',mark=None,base='stateW',explicit=None,palette=['stateW','y_e'],title='상태에는 역할을 강요하지 않기',note='손의 상태를 말한다. 원형을 피동자라는 뜻으로 읽지 않는다.',reuse='기본 연결 · 관계 구별 불필요',pieces=2),
}

def shape(mid,x=0,y=0):
    poly=box(0,0,1,1)
    for side,kind,profile in MODELS[mid][1]:
        px,py=MID[side];nx,ny=NORMAL[side]
        if kind=='socket':nx,ny=-nx,-ny
        tx,ty=-ny,nx
        features=[]
        for offset in ([-.105,.105] if profile=='twin' else [0]):
            r=.062 if profile=='twin' else .099
            neck=.038 if profile=='twin' else .055
            bx,by=px+tx*offset,py+ty*offset
            cx,cy=bx+nx*.11,by+ny*.11
            stem=Polygon([(bx+tx*neck,by+ty*neck),(bx-tx*neck,by-ty*neck),(cx-tx*neck,cy-ty*neck),(cx+tx*neck,cy+ty*neck)])
            features.append(unary_union([stem,Point(cx,cy).buffer(r,quad_segs=24)]))
        f=unary_union(features)
        poly=poly.union(f) if kind=='tab' else poly.difference(f)
    assert poly.is_valid and poly.geom_type=='Polygon'
    return translate(poly,x,y)

def pieces(case,explicit):
    c=CASES[case]
    if c['kind']=='state':return [('W','y_e',0,1,'손'),('verb','stateW',1,1,'아프다')]
    action=c['explicit'] if explicit else c['base']
    n='y_s2' if explicit and c['mark']=='N' else 'y_s'
    w='y_e2' if explicit and c['mark']=='W' else 'y_e'
    p=[('verb',action,1,1,c['word']),('N',n,1,0,'주민' if c['mark']=='N' else '나'),('W',w,0,1,'주민' if c['mark']=='W' else '나')]
    if case=='send':p.append(('E','y_w',2,1,'너'))
    return p

def verify(case,explicit):
    p=pieces(case,explicit);ports=[];matched=set();edges=[]
    assert all(mid in CASES[case]['palette'] for _,mid,_,_,_ in p)
    for key,mid,x,y,_ in p:
        for side,kind,profile in MODELS[mid][1]:
            px,py=MID[side];ports.append((key,side,kind,profile,(x+px,y+py)))
    for i,j in combinations(range(len(ports)),2):
        a,b=ports[i],ports[j]
        if a[4]==b[4] and OPP[a[1]]==b[1] and a[2]!=b[2]:
            assert a[3]==b[3]
            matched.update([i,j]);tab,socket=(a,b) if a[2]=='tab' else (b,a)
            edges.append([tab[0],socket[0],a[3]])
    assert len(matched)==len(ports)
    polys=[shape(mid,x,y) for _,mid,x,y,_ in p]
    assert all(a.intersection(b).area<1e-9 for a,b in combinations(polys,2))
    expected={('W','verb')} if case=='pain' else {('N','verb'),('W','verb')}
    if case=='send':expected.add(('verb','E'))
    assert {(a,b) for a,b,_ in edges}==expected
    return {'piece_count':len(p),'contacts':edges,'palette_membership':True,'no_overlap':True,'ports_matched':True}

def path(poly,ox,oy,u):
    return 'M '+' L '.join(f'{ox+x*u:.3f},{oy+y*u:.3f}' for x,y in poly.exterior.coords)+' Z'

COLORS={'yellow':('#E9C76A','#806522'),'blue':('#8FBFD2','#416C7E')}
def svg(case,explicit):
    p=pieces(case,explicit);u=88;ox=52 if case=='send' else 98;oy=16
    out=['<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 376 212" class="assembly" role="img" aria-label="조립 모형">']
    for key,mid,x,y,word in p:
        fill,stroke=COLORS[MODELS[mid][0]]
        out.append(f'<g data-piece="{key}" data-model="{mid}"><path d="{path(shape(mid,x,y),ox,oy,u)}" fill="{fill}" stroke="{stroke}" stroke-width="1.8"/>')
        size=17 if key=='verb' else 21
        out.append(f'<text x="{ox+(x+.5)*u}" y="{oy+(y+.5)*u+1}" text-anchor="middle" dominant-baseline="central" font-size="{size}">{word}</text></g>')
    out.append('</svg>');return ''.join(out)

def mini(mid):
    fill,stroke=COLORS[MODELS[mid][0]]
    return f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 100 96" role="img" aria-label="사용 가능한 낱개 모형"><path d="{path(shape(mid),20,15,59)}" fill="{fill}" stroke="{stroke}" stroke-width="1.7"/></svg>'

svgs={};checks={}
for name,c in CASES.items():
    for explicit in ([False] if c['kind']=='state' else [False,True]):
        key=name+('_mark' if explicit else '_plain')
        svgs[key]=svg(name,explicit);checks[key]=verify(name,explicit)
        (OUT/(key+'.svg')).write_text(svgs[key],encoding='utf-8')
minis={mid:mini(mid) for mid in MODELS}
counts={k:len(v['palette']) for k,v in CASES.items()}
assert counts=={'send':6,'push':5,'pull':5,'pain':2}
assert CASES['push']['palette']==CASES['pull']['palette']
unique_used=set(mid for c in CASES.values() for mid in c['palette'])
assert len(unique_used)==10
checks_summary={'scope':'7종 기하 배치. 단어교환은 외곽을 바꾸지 않음. 전체 자유조립/사람 경험 검증 아님.','layouts':checks,'palette_counts':counts,'unique_color_and_outline_items':10,'unique_outline_profiles':9,'full_palette_reuse':['push','pull']}
(OUT/'접합과목록_검산.json').write_text(json.dumps(checks_summary,ensure_ascii=False,indent=2),encoding='utf-8')
data={'cases':CASES,'models':MODELS,'boards':svgs,'minis':minis}
(OUT/'도형과사례.json').write_text(json.dumps(data,ensure_ascii=False,indent=2),encoding='utf-8')
template=(OUT/'보기.template.html').read_text(encoding='utf-8')
chars=''.join(set(template+json.dumps(CASES,ensure_ascii=False)+'주민이 나를 너에게 보낸다 내가 주민을 너에게 보낸다 민다 당긴다 손 발이 아프다 누가 하는지는 문맥 두 갈래 원형'))
font=TTFont(str(next(p / '기획서/source/assets/Pretendard-Regular.ttf' for p in Path(__file__).resolve().parents if (p / '기획서/source/assets/Pretendard-Regular.ttf').is_file())))
sub=subset.Subsetter();sub.populate(text=chars);sub.subset(font)
buffer=io.BytesIO();font.save(buffer)
page=template.replace('__FONT__',base64.b64encode(buffer.getvalue()).decode()).replace('__DATA__',json.dumps(data,ensure_ascii=False))
(OUT/'보기.html').write_text(page,encoding='utf-8')
print(json.dumps({'layouts':len(checks),'palette_counts':counts,'items':len(unique_used),'html_bytes':len(page.encode())},ensure_ascii=False))
