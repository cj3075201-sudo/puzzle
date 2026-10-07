"""표시형·3노랑·문장 확장 설계 설명도. 본편 구현/자유 조립기가 아니다."""
from pathlib import Path
from itertools import combinations
import json, sys, io, base64

from shapely.geometry import box, Point, Polygon
from shapely.ops import unary_union
from shapely.affinity import translate
from fontTools.ttLib import TTFont
from fontTools import subset

OUT = Path(__file__).resolve().parent
NORMAL = {'N':(0,-1),'E':(1,0),'S':(0,1),'W':(-1,0)}
MID = {'N':(.5,0),'E':(1,.5),'S':(.5,1),'W':(0,.5)}
OPP = {'N':'S','E':'W','S':'N','W':'E'}
COLORS = {'yellow':('#E9C76A','#846B31'),'blue':('#91BECE','#496F80')}

def shape(ports, x=0, y=0):
    p = box(0,0,1,1)
    for side, kind, profile in ports:
        bx, by = MID[side]; nx, ny = NORMAL[side]
        if kind == 'socket': nx, ny = -nx, -ny
        tx, ty = -ny, nx
        fs = []
        for off in ([-.105,.105] if profile == 'twin' else [0]):
            r = .062 if profile == 'twin' else .099
            neck = .038 if profile == 'twin' else .055
            px, py = bx+tx*off, by+ty*off
            cx, cy = px+nx*.11, py+ny*.11
            stem = Polygon([(px+tx*neck,py+ty*neck),(px-tx*neck,py-ty*neck),(cx-tx*neck,cy-ty*neck),(cx+tx*neck,cy+ty*neck)])
            fs.append(unary_union([stem,Point(cx,cy).buffer(r,quad_segs=24)]))
        f = unary_union(fs)
        p = p.union(f) if kind == 'tab' else p.difference(f)
    return translate(p,x,y)

def part(key, color, x, y, label, ports):
    return dict(key=key,color=color,x=x,y=y,label=label,ports=ports)

def transfer(actor, obj, other, verb):
    return [part('actor','yellow',1,0,actor,[('S','tab','twin')]),
            part('object','yellow',0,1,obj,[('E','tab','round')]),
            part('verb','blue',1,1,verb,[('N','socket','twin'),('W','socket','round'),('E','tab','round')]),
            part('other','yellow',2,1,other,[('W','socket','round')])]

def chain(words):
    return [part(str(i),'yellow',i,0,word,
                 ([('W','socket','round')] if i else []) + ([('E','tab','round')] if i+1<len(words) else []))
            for i,word in enumerate(words)]

def event(which):
    if which == 'open':
        return [part('actor','yellow',1,0,'주민',[('S','tab','twin')]),
                part('object','yellow',0,1,'문',[('E','tab','round')]),
                part('verb','blue',1,1,'열다',[('N','socket','twin'),('W','socket','round')])]
    return [part('actor','yellow',0,0,'나',[('S','tab','twin')]),
            part('verb','blue',0,1,'들어가다',[('N','socket','twin')])]

def check(parts):
    ports=[]
    for p in parts:
        for side,kind,profile in p['ports']:
            dx,dy=MID[side]
            ports.append((p['key'],side,kind,profile,(p['x']+dx,p['y']+dy)))
    matched=set();edges=[]
    for i,j in combinations(range(len(ports)),2):
        a,b=ports[i],ports[j]
        if a[4]==b[4] and OPP[a[1]]==b[1] and a[2]!=b[2]:
            assert a[3]==b[3]
            matched.update([i,j]);edges.append([a[0],b[0],a[3]])
    assert len(matched)==len(ports)
    shapes=[shape(p['ports'],p['x'],p['y']) for p in parts]
    assert all(p.is_valid and p.geom_type=='Polygon' for p in shapes)
    assert all(a.intersection(b).area<1e-9 for a,b in combinations(shapes,2))
    return dict(pieces=len(parts),connections=edges,matched=True,no_overlap=True)

def svg(parts, width=420, height=260):
    maxx=max(p['x'] for p in parts)+1;maxy=max(p['y'] for p in parts)+1
    u=min((width-38)/maxx,(height-28)/maxy,112)
    ox=(width-maxx*u)/2;oy=(height-maxy*u)/2
    out=[f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {width} {height}" role="img" class="jigsaw" aria-label="낱개 연결 설명도">']
    for p in parts:
        geom=shape(p['ports'],p['x'],p['y'])
        coords=' L '.join(f'{ox+x*u:.3f},{oy+y*u:.3f}' for x,y in geom.exterior.coords)
        fill,stroke=COLORS[p['color']]
        size=min(23, .64*u/max(len(p['label']),1))
        out.append(f'<g data-piece="{p["key"]}"><path d="M {coords} Z" fill="{fill}" stroke="{stroke}" stroke-width="1.7"/>')
        out.append(f'<text x="{ox+(p["x"]+.5)*u:.3f}" y="{oy+(p["y"]+.5)*u:.3f}" text-anchor="middle" dominant-baseline="central" font-size="{size:.2f}">{p["label"]}</text></g>')
    return ''.join(out)+'</svg>'

NOUNS=[
    dict(words=['집','안','주민'],meaning='집 안에 있는 주민',status='사용자 기준',detail='집이 기준인 안쪽 공간을 먼저 잡고, 그곳의 주민을 지칭한다.'),
    dict(words=['집','안','열쇠'],meaning='집 안에 있는 열쇠',status='사용자 기준',detail='마지막 글자가 지칭할 대상이다. 주민의 위치를 말하는 문장과 구별된다.'),
    dict(words=['상자','안','열쇠'],meaning='상자 안에 있는 열쇠',status='공간 규칙 재사용',detail='집 대신 상자를 넣는다. 앞에서 특정한 상자의 내부라는 기준을 유지한다.'),
    dict(words=['문','앞','주민'],meaning='문 앞에 있는 주민',status='공간 규칙 재사용',detail='앞이라는 공간말을 배우면 같은 읽기 구조를 활용할 수 있다.'),
    dict(words=['다리','아래','배'],meaning='다리 아래에 있는 배',status='공간 규칙 재사용',detail='아래·배는 설명용 후보 어휘다. 이 사슬은 배를 지칭한다.'),
    dict(words=['주민','팔','손'],meaning='주민의 팔에 속한 손',status='관계 용법 추가 필요',detail='전체→부분 관계를 배웠을 때 성립한다. 공간말 규칙만으로 자동 도출되지는 않는다.'),
    dict(words=['주민','손','상처'],meaning='주민의 손에 난 상처',status='관계 용법 추가 필요',detail='전체→부분과 상처가 난 신체 위치의 관계를 알려줘야 한다.'),
    dict(words=['주민','집','안'],meaning='그 주민과 관련된 집의 안쪽',status='관계 용법 추가 필요',detail='주민→집이 거주·소유 중 무엇인지 용례를 정해야 한다. 그 집이라는 지칭을 다음 연결에 유지한다.'),
    dict(words=['주민','가방','열쇠'],meaning='가방 안의 열쇠? 가방을 여는 열쇠?',status='3개여도 뜻이 덜 정해짐',detail='안이라는 글자를 빼고도 내부라고 자동 판정하지 않는다. 이 조합의 용법을 따로 정해야 한다.'),
    dict(words=['나무','문','앞'],meaning='나무로 만든 문? 나무에 달린 문?',status='3개여도 뜻이 덜 정해짐',detail='나무가 재료인지 기준 대상인지 순서만으로 정해지지 않는다. 후보 용례 검토가 필요하다.'),
    dict(words=['집','안','주민','열쇠'],meaning='집 안에 있는 주민의 열쇠',status='현재 상한 밖',detail='노랑 4피스. 관계 용법을 정하더라도 3개 제한에는 들어가지 않는다. 열쇠 자체가 집 안에 있다는 뜻은 아니다.'),
    dict(words=['주민','가방','안','열쇠'],meaning='그 주민의 가방 안에 있는 열쇠',status='현재 상한 밖',detail='노랑 4피스. 가방과 안을 묶음 하나로 세어 제한을 우회하는 규칙은 채택하지 않았다.'),
]
VERBS={
 'give':dict(word='주다',obj='열쇠',other='나',meaning='주민이 나에게 열쇠를 준다.',swapped='내가 주민에게 열쇠를 준다.',relation='추가 상대 = 받는 쪽'),
 'send':dict(word='보내다',obj='열쇠',other='나',meaning='주민이 나에게 열쇠를 보낸다.',swapped='내가 주민에게 열쇠를 보낸다.',relation='추가 상대 = 도착 상대'),
 'show':dict(word='보여주다',obj='책',other='나',meaning='주민이 나에게 책을 보여준다.',swapped='내가 주민에게 책을 보여준다.',relation='추가 상대 = 보는 상대'),
 'take':dict(word='빼앗다',obj='열쇠',other='나',meaning='주민이 나에게서 열쇠를 빼앗는다.',swapped='내가 주민에게서 열쇠를 빼앗는다.',relation='추가 상대 = 빼앗기는 쪽'),
}
data={'nouns':NOUNS,'verbs':VERBS,'boards':{},'chains':[],'events':{}}
checks={}
def save_board(key,parts,width=420,height=260):
    checks[key]=check(parts)
    return svg(parts,width,height)
data['original']=save_board('old_send',transfer('주민','나','너','보내다'))
for key,c in VERBS.items():
    data['boards'][key]=save_board(key,transfer('주민',c['obj'],c['other'],c['word']))
    data['boards'][key+'_swap']=save_board(key+'_swap',transfer(c['other'],c['obj'],'주민',c['word']))
for i,c in enumerate(NOUNS):
    data['chains'].append(save_board('noun_'+str(i),chain(c['words']),640,160))
for e in ['open','enter']:
    data['events'][e]=save_board(e,event(e),360,244)
template=(OUT/'비교.template.html').read_text(encoding='utf-8')
font=TTFont(str(next(p / '기획서/source/assets/Pretendard-Regular.ttf' for p in Path(__file__).resolve().parents if (p / '기획서/source/assets/Pretendard-Regular.ttf').is_file())))
sub=subset.Subsetter();sub.populate(text=template+json.dumps(data,ensure_ascii=False));sub.subset(font)
buf=io.BytesIO();font.save(buf)
page=template.replace('__FONT__',base64.b64encode(buf.getvalue()).decode()).replace('__DATA__',json.dumps(data,ensure_ascii=False))
(OUT/'비교.html').write_text(page,encoding='utf-8')
(OUT/'도형검산.json').write_text(json.dumps({'scope':'낱개 피스의 도형/접합 검사. 새 문법 채택·문장 연결선의 물리 접합·사람 이해/재미 검증이 아니다.','layouts':checks},ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps({'html':str(OUT/'비교.html'),'boards':len(checks),'noun_examples':len(NOUNS)},ensure_ascii=False))
