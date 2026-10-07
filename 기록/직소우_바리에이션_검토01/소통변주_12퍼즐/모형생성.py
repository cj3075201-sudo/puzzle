"""기존 연결확장08의 실제 round/twin 직소 외곽을 재사용한다."""
from pathlib import Path
from itertools import combinations
import json, sys
sys.path.insert(0, '/tmp/jigsaw_geometry_deps')
from shapely.geometry import box, Point, Polygon
from shapely.ops import unary_union
NORMAL = {'N':(0,-1),'E':(1,0),'S':(0,1),'W':(-1,0)}
MID = {'N':(.5,0),'E':(1,.5),'S':(.5,1),'W':(0,.5)}
def shape(ports):
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
    assert p.is_valid and p.geom_type == 'Polygon'
    return p
models={}
def add(key,color,ports):
    geom=shape(ports)
    models[key]={'color':color,'ports':ports,'path':'M '+' L '.join(f'{x*100:.3f},{y*100:.3f}' for x,y in geom.exterior.coords)+' Z','socketSides':[p[0] for p in ports if p[1]=='socket']}
# Familiar names preserve the existing incoming/outgoing meanings.
named={'e':[('E','tab','round')],'s':[('S','tab','round')],'w':[('W','socket','round')],'n':[('N','socket','round')],
'we':[('W','socket','round'),('E','tab','round')],'ns':[('N','socket','round'),('S','tab','round')],
'ne':[('N','socket','round'),('E','tab','round')],'nes':[('N','socket','round'),('E','tab','round'),('S','tab','round')],
'es':[('E','tab','round'),('S','tab','round')],'ws':[('W','socket','round'),('S','tab','round')]}
for prefix,color in [('y','yellow'),('b','blue')]:
    for name,ports in named.items():add(prefix+'_'+name,color,ports)
    # All fixed-orientation tree joints: zero/one input, at most three outputs.
    for incoming in [None,*NORMAL]:
        available=[s for s in NORMAL if s!=incoming]
        for count in range(4):
            for outgoing in combinations(available,count):
                ports=([(incoming,'socket','round')] if incoming else [])+[(s,'tab','round') for s in outgoing]
                signature=sorted(ports)
                if any(m['color']==color and sorted(m['ports'])==signature for m in models.values()):continue
                key=prefix+'_i'+(incoming or '0').lower()+'_o'+(''.join(outgoing) or '0').lower()
                add(key,color,ports)
add('y_twin','yellow',[('S','tab','twin')])
add('b_give','blue',[('N','socket','twin'),('W','socket','round'),('E','tab','round')])
palette=[prefix+'_'+name for prefix in ['y','b'] for name in named]+['b_iw_oes','b_in_osw','y_ie_o0']
(Path(__file__).parent/'models.json').write_text(json.dumps({'models':models,'palette':palette},ensure_ascii=False,separators=(',',':')),encoding='utf-8')
print(f'{len(models)} fixed-orientation models generated; {len(palette)} familiar palette entries')
