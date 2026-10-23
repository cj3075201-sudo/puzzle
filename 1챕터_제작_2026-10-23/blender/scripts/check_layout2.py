# -*- coding: utf-8 -*-
"""Sanity check for art/layout_slice2.json against the built level (run in Blender):
 - every exit pos resolves (AreaSystem.Of = smallest signed distance) to its own area, every spawn to the target area
 - a spawn is not inside the target area's exit circles (no ping-pong)
 - exits, spawns, zones, props, npc spawns stand on Ground_Walk_<area> (downward ray) and report the height
usage: blender -b --factory-startup --python check_layout2.py"""
import sys, os, json, math
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import bpy
from mathutils import Vector as V
import ouat_lib as L
L.reset_scene()
import ouat_areas as AR
import ouat_slice as SL
A = AR.build_level_areas()
bpy.context.view_layer.update()
ART = os.path.dirname(HERE)
lay = json.load(open(os.path.join(ART, 'layout_slice2.json'), encoding='utf-8'))
areas = {a['id']: a for a in lay['areas']}


def sd(a, p):
    best = 1e9
    for s in a['shape']:
        if 'line' in s:
            pts = [V(q) for q in s['line']]
            d = min(SL.LV.seg_dist(V(p), pts[i], pts[i + 1])[0] for i in range(len(pts) - 1)) - s['w']
        else:
            d = (V(p) - V(s['c'])).length - s['r']
        best = min(best, d)
    return best


def of(p):
    return min(areas.values(), key=lambda a: sd(a, p))['id']


walk = {}
for nm, ob in A.objs.items():
    if ob.type == 'MESH' and nm.startswith('Ground_Walk_'):
        walk[nm[len('Ground_Walk_'):]] = ob


def hit(area, p):
    ob = walk.get(area[2:])
    if ob is None:
        return None
    mi = ob.matrix_world.inverted()
    org = mi @ SL.B(p[0], p[1], 50.0)
    d = (mi.to_3x3() @ V((0, 0, -1))).normalized()
    ok, loc, n, i = ob.ray_cast(org, d, distance=100.0)
    return round((ob.matrix_world @ loc).z, 2) if ok else None


bad = 0
for a in lay['areas']:
    for e in a['exits']:
        o1, o2 = of(e['pos']), of(e['spawn'])
        h1, h2 = hit(a['id'], e['pos']), hit(e['to'], e['spawn'])
        pp = [x for x in areas[e['to']]['exits'] if math.dist(x['pos'], e['spawn']) <= x['radius'] + 0.3]
        flag = (o1 != a['id']) or (o2 != e['to']) or h1 is None or h2 is None or pp
        bad += bool(flag)
        print(('BAD ' if flag else 'ok  ') + f"{a['id']}->{e['to']}: pos {e['pos']} Of={o1} y={h1} | spawn {e['spawn']} Of={o2} y={h2}" + (f' PINGPONG {pp[0]["to"]}' if pp else ''))
P = lay['positions2']
items = list(P['zones'].items()) + [(k, v['pos']) for k, v in P['props'].items()] + [(k, v['spawn']) for k, v in P['npcs'].items()] + \
    list(P['inscriptions'].items()) + list(P['puzzles'].items())
for k, p in items:
    a = of(p)
    h = hit(a, p)
    flag = h is None and k not in ('pond', 'fish', 'z_pond_center', 'bell')
    bad += flag
    print(('BAD ' if flag else 'ok  ') + f'{k:22s} {p} area={a} y={h}')
for d in lay['alley_seated_lumps'] + [lay['kid_house_chair']]:
    print('chair', d['chair'], of(d['chair']), hit('a_alley', d['chair']))
for d in lay['pond_lineup']:
    print('lineup', d['pos'], of(d['pos']), hit('a_field', d['pos']))
# polish round: slice-3 positions + every zone the data uses on the slice-2 pages (chapter1.json)
l3p = os.path.join(ART, 'layout_slice3.json')
if os.path.exists(l3p):
    l3 = json.load(open(l3p, encoding='utf-8'))
    for k, p in l3['positions3']['zones_checked'].items():
        a = of(p); h = hit(a, p); flag = h is None; bad += flag
        print(('BAD ' if flag else 'ok  ') + f'3 {k:20s} {p} area={a} y={h}')
    for d in l3['pond_lineup3']:
        a = of(d['pos']); h = hit('a_field', d['pos']); flag = h is None or a != 'a_field'; bad += flag
        print(('BAD ' if flag else 'ok  ') + f"3 lineup {d['pos']} row {d['row']} y={h}")
    for k, v in l3['positions3']['props'].items():
        print('3 prop', k, v['pos'], of(v['pos']), hit(of(v['pos']), v['pos']))
CH = json.load(open(SL.LV.CH1, encoding='utf-8'))
NEW = ('plaza', 'alley', 'hideout', 'depot', 'field', 'pond')
for z in CH['zones']:
    if z.get('place') in NEW:
        a = of(z['pos']); h = hit(a, z['pos']); flag = h is None and z['id'] not in ('z_pond_center',); bad += flag
        print(('BAD ' if flag else 'ok  ') + f"ch1 {z['id']:20s} {z['pos']} area={a} y={h}")
print('BAD COUNT', bad)
