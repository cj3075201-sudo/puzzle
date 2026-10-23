# -*- coding: utf-8 -*-
"""Build Level_Ch1 (slice 1 + slice 2 dioramas + Global) and export it to Unity WITHOUT touching anything else.
Merges new material slots into art_materials.json (existing slots kept), updates asset_stats.json['Level_Ch1'],
writes art/layout_slice2.json and patches art/layout_dressing.json (only the slice-2 areas).
usage: blender -b --factory-startup --python export_level.py -- [noexport] [nojson] [slice2json]"""
import sys, os, json, time
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import bpy
import ouat_lib as L

argv = sys.argv[sys.argv.index('--') + 1:] if '--' in sys.argv else []
ART = os.path.dirname(HERE)
PROJ = os.path.dirname(ART)
MODELS = os.path.join(PROJ, 'Unity', 'Assets', 'Game', 'Art', 'Models')

L.reset_scene()
t0 = time.time()
import ouat_areas as AR
import ouat_slice2 as SL2
A = AR.build_level_areas()
print('build', round(time.time() - t0, 1), 's')

# per-area triangle report (everything under Area_<id>)
per_area = {}
for nm, ob in A.objs.items():
    if ob.type != 'MESH':
        continue
    p = ob.parent
    area = None
    while p is not None:
        bn = p.name.split('|', 1)[-1]
        if bn.startswith('Area_') or bn == 'Global':
            area = bn
            break
        p = p.parent
    t = sum(len(pp.vertices) - 2 for pp in ob.data.polygons)
    per_area.setdefault(area, {})[nm] = t
for a in sorted(per_area, key=str):
    tot = sum(per_area[a].values())
    print(f'AREA {a:16s} tris={tot:6d}  ' + '  '.join(f'{k}={v}' for k, v in sorted(per_area[a].items(), key=lambda kv: -kv[1])))

if 'noexport' not in argv:
    L.export_fbx(A, os.path.join(MODELS, 'Level_Ch1.fbx'))
    print('EXPORTED Level_Ch1.fbx')
    used = sorted({m.name for ob in A.objs.values() if ob.type == 'MESH' for m in ob.data.materials})
    mp = os.path.join(PROJ, 'Unity', 'Assets', 'Game', 'Art', 'art_materials.json')
    mj = json.load(open(mp, encoding='utf-8'))
    added = []
    for k in used:
        if k in mj['materials'] or k not in L.MATS:
            continue
        base, shade, ol, cat, extra = L.MATS[k]
        d = {'base': base, 'shade': shade, 'outline': ol, 'category': cat}
        d.update(extra)
        mj['materials'][k] = d
        added.append(k)
    json.dump(mj, open(mp, 'w', encoding='utf-8'), ensure_ascii=False, indent=2)
    print('MATERIALS added', added, 'missing', [k for k in used if k not in mj['materials']])
    sp = os.path.join(ART, 'blend', 'asset_stats.json')
    st = json.load(open(sp, encoding='utf-8')) if os.path.exists(sp) else {}
    tris, per = A.tris()
    mn, mx = A.bounds()
    st['Level_Ch1'] = dict(group='level', tris=tris, parts=per, size=[round(v, 2) for v in (mx - mn)], min=[round(v, 2) for v in mn],
                           max=[round(v, 2) for v in mx], materials=used, per_area={str(a): sum(v.values()) for a, v in per_area.items()},
                           note=str(A.meta.get('note', '')))
    json.dump(st, open(sp, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
if 'slice2json' in argv:          # (re)write layout_slice2.json — off by default since the polish round (main has integrated it)
    print('LAYOUT', SL2.write_layout_json(all_areas=AR.AREAS))
if 'nojson' not in argv:
    print('LAYOUT3', SL2.write_layout3_json())
    print('DRESSING items', SL2.patch_dressing_json())
print('DONE')
