"""설명용 비교 모형. 본편 코드/최종 글자/문법이 아니다."""
from pathlib import Path
from itertools import combinations
import sys, json, re, base64, io
sys.path.insert(0, '/tmp/jigsaw_geometry_deps')
from shapely.geometry import box, Point, Polygon
from shapely.ops import unary_union
from shapely.affinity import translate
from fontTools import subset
from fontTools.ttLib import TTFont

OUT = Path(__file__).resolve().parent
NORMAL = {'N': (0,-1), 'E': (1,0), 'S': (0,1), 'W': (-1,0)}
OPP = {'N':'S','S':'N','E':'W','W':'E'}
P = {'N':(.5,0),'E':(1,.5),'S':(.5,1),'W':(0,.5)}

def make_piece(pid, word, color, x, y, ports):
    poly = box(0,0,1,1)
    for side, kind, profile in ports:
        px,py=P[side]; nx,ny=NORMAL[side]
        if kind=='socket': nx,ny=-nx,-ny
        tx,ty=-ny,nx
        lobes=[]
        offsets = [-.105,.105] if profile=='twin' else [0]
        radius=.062 if profile=='twin' else .099
        neck=.038 if profile=='twin' else .055
        for offset in offsets:
            bx,by=px+tx*offset,py+ty*offset
            cx,cy=bx+nx*.11,by+ny*.11
            stem=Polygon([(bx+tx*neck,by+ty*neck),(bx-tx*neck,by-ty*neck),
                          (cx-tx*neck,cy-ty*neck),(cx+tx*neck,cy+ty*neck)])
            lobes.append(unary_union([stem,Point(cx,cy).buffer(radius,quad_segs=24)]))
        feature=unary_union(lobes)
        poly=poly.union(feature) if kind=='tab' else poly.difference(feature)
    poly=translate(poly,x,y)
    assert poly.is_valid and poly.geom_type=='Polygon'
    assert poly.covers(box(x+.25,y+.3,x+.75,y+.7)), (pid,'text clearance')
    return {'id':pid,'word':word,'color':color,'x':x,'y':y,'ports':ports,'poly':poly}

def layout(mode, mark):
    # 왼쪽/위쪽 자체에는 역할이 없다. 표시된 쪽만 이 후보에서 행위자다.
    left_twin=mode=='shape' and mark=='left'
    top_twin=mode=='shape' and mark=='top'
    lp='twin' if left_twin else 'round'; tp='twin' if top_twin else 'round'
    pieces=[make_piece('verb','보내다','blue',2,2,[('W','socket',lp),('N','socket',tp),('E','tab','round')]),
            make_piece('left','나','yellow',0 if mode=='tile' and mark=='left' else 1,2,[('E','tab',lp)]),
            make_piece('top','주민','yellow',2,0 if mode=='tile' and mark=='top' else 1,[('S','tab',tp)]),
            make_piece('dest','너','yellow',3,2,[('W','socket','round')])]
    if mode=='tile' and mark!='none':
        ports=[('W','socket','round'),('E','tab','round')] if mark=='left' else [('N','socket','round'),('S','tab','round')]
        pieces.append(make_piece('alpha','α','purple',1 if mark=='left' else 2,2 if mark=='left' else 1,ports))
    return pieces

def check(mode, mark, pieces):
    ports=[]; joins=[]; matched=set()
    for p in pieces:
        for side,kind,profile in p['ports']:
            px,py=P[side]
            ports.append((p['id'],side,kind,profile,(p['x']+px,p['y']+py)))
    for i,j in combinations(range(len(ports)),2):
        a,b=ports[i],ports[j]
        if a[4]==b[4] and OPP[a[1]]==b[1] and a[2]!=b[2]:
            assert a[3]==b[3]
            matched.update([i,j]);tab,socket=(a,b) if a[2]=='tab' else (b,a)
            joins.append([tab[0],socket[0]])
    assert len(matched)==len(ports), (mode,mark,'open port')
    for a,b in combinations(pieces,2):
        assert a['poly'].intersection(b['poly']).area<1e-9,(a['id'],b['id'],'overlap')
    expected={('left','verb'),('top','verb'),('verb','dest')}
    if mode=='tile' and mark!='none':
        expected.remove((mark,'verb'));expected.update([(mark,'alpha'),('alpha','verb')])
    assert set(map(tuple,joins))==expected
    return {'pieces':len(pieces),'joins':joins,'overlaps':0,'all_ports_matched':True,'text_safe':True}

def svg(mode,mark):
    pieces=layout(mode,mark)
    # Same scale and canvas in all candidates: the extra tile visibly costs room.
    ox,oy,u=42,18,94
    colors={'yellow':('#E9C76A','#806522'),'blue':('#8FBFD2','#416C7E'),'purple':('#BAA3D4','#71558A')}
    out=['<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 466 336" class="puzzle-svg" role="img" aria-label="직소우 조립 비교">']
    for p in pieces:
        points=[(ox+x*u,oy+y*u) for x,y in p['poly'].exterior.coords]
        path='M '+' L '.join(f'{x:.3f},{y:.3f}' for x,y in points)+' Z'
        fill,stroke=colors[p['color']]
        out.append(f'<g data-piece="{p["id"]}"><path d="{path}" fill="{fill}" stroke="{stroke}" stroke-width="2" stroke-linejoin="round"/>')
        x,y=ox+(p['x']+.5)*u,oy+(p['y']+.5)*u
        font_size=28 if p['id']=='alpha' else 18 if p['id']=='verb' else 21
        out.append(f'<text x="{x}" y="{y+2}" text-anchor="middle" dominant-baseline="central" class="piece-word" font-size="{font_size}" font-weight="650">{p["word"]}</text></g>')
    if mode=='stamp' and mark!='none':
        x,y=(ox+2*u,oy+2.5*u) if mark=='left' else (ox+2.5*u,oy+2*u)
        out.append(f'<g class="stamp"><circle cx="{x}" cy="{y}" r="16" fill="#FBF8EF" stroke="#38464D" stroke-width="2"/><text x="{x}" y="{y+1}" text-anchor="middle" dominant-baseline="central" font-size="23" fill="#23333D">α</text></g>')
    out.append('</svg>')
    return ''.join(out),check(mode,mark,pieces)

all_svgs={};checks={}
for mode in ['tile','stamp','shape']:
    for mark in ['none','left','top']:
        key=f'{mode}_{mark}'
        all_svgs[key],checks[key]=svg(mode,mark)
        (OUT/f'{key}.svg').write_text(all_svgs[key],encoding='utf-8')
(OUT/'접합검사.json').write_text(json.dumps({'scope':'설명용 9배치. 접합과 글자 여백만 검증; 문법 채택/재미 검증 아님.','layouts':checks},ensure_ascii=False,indent=2),encoding='utf-8')
template=(OUT/'비교.template.html').read_text(encoding='utf-8')
# Embed only characters used by this standalone comparison, using an existing OFL project font.
chars=''.join(set(template+'주민이나너보내다α표시대상해석원형두갈래목적지입력접합모형관계미정기대유력충돌변경4 5'))
font=TTFont('/mnt/c/Users/cj307/Desktop/졸프/기획서/source/assets/Pretendard-Regular.ttf')
sub=subset.Subsetter();sub.populate(text=chars);sub.subset(font)
buf=io.BytesIO();font.save(buf)
font_data=base64.b64encode(buf.getvalue()).decode()
page=template.replace('__FONT__',font_data).replace('__SVGS__',json.dumps(all_svgs,ensure_ascii=False))
(OUT/'비교.html').write_text(page,encoding='utf-8')
print(json.dumps({'layouts':len(checks),'font_bytes':len(buf.getvalue()),'html_bytes':len(page.encode()),'geometry_passed':True},ensure_ascii=False))
