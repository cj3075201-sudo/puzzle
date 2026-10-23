# -*- coding: utf-8 -*-
"""Export only the props / village / dressing kit (10/23 rework) to Unity without touching anything else.
Unlike build_all.py it MERGES into art_materials.json and asset_stats.json (other agents' entries are kept;
existing shared slots are not overwritten, only missing slots are added).
usage: blender -b --factory-startup --python export_props_kit.py -- [only=Name1,Name2] [groups=props,village,dressing,offering,offering2]
(default groups = props,village,dressing; the 10/23 story props need groups=offering / offering2)"""
import sys, os, json, time
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import bpy
import ouat_lib as L
import ouat_props as P
import ouat_village as VL
import ouat_dressing as D
import ouat_offering as OF   # 10/23 story props (fish courier / offerings); export with groups=offering
import ouat_offering2 as OF2  # 10/23 story props batch 2 (den door, trinkets, torch, cord basket/hook, workbench); groups=offering2

argv = sys.argv[sys.argv.index('--') + 1:] if '--' in sys.argv else []
args = dict(a.split('=', 1) for a in argv if '=' in a)
only = set(args['only'].split(',')) if 'only' in args else None
groups = set(args.get('groups', 'props,village,dressing').split(','))
ART = os.path.dirname(HERE)
PROJ = os.path.dirname(ART)
MODELS = os.path.join(PROJ, 'Unity', 'Assets', 'Game', 'Art', 'Models')
# terrain-ish village pieces are not part of this rework; leave their FBX alone unless asked by name
SKIP_DEFAULT = {'Paving_Hex', 'Paving_HexBroken', 'Spire_1', 'Spire_2', 'Spire_3', 'Cliff_1', 'Cliff_2', 'Cliff_3', 'CaveWall_1', 'CaveWall_2',
                'CaveWall_3', 'Rock_1', 'Rock_2', 'Rock_3', 'Pond', 'LightShaft', 'CeilingHole', 'FX_InkRing', 'FX_Splash', 'FX_Dust'}

todo = []
for grp, mod in (('props', P), ('village', VL), ('dressing', D), ('offering', OF), ('offering2', OF2)):
    if grp not in groups:
        continue
    for n, f in mod.ASSETS:
        if only is not None:
            if n in only:
                todo.append((n, f, grp))
        elif n not in SKIP_DEFAULT:
            todo.append((n, f, grp))

L.reset_scene()
stats, used = {}, set()
t0 = time.time()
for name, fn, grp in todo:
    A = fn()
    assert A.name == name
    tris, per = A.tris()
    per = {('Main' if k == name else k): v for k, v in per.items()}
    mn, mx = A.bounds()
    mats = sorted({m.name for ob in A.objs.values() if ob.type == 'MESH' for m in ob.data.materials})
    used.update(mats)

    def tree(ob, depth=0):
        out = []
        for ch in sorted(ob.children, key=lambda o: o.name):
            out.append(('  ' * depth) + L.bare_name(name, ch.name) + ('' if ch.type == 'MESH' else ' (empty)'))
            out += tree(ch, depth + 1)
        return out
    stats[name] = dict(group=grp, tris=tris, parts=per, size=[round(v, 2) for v in (mx - mn)], min=[round(v, 2) for v in mn],
                       max=[round(v, 2) for v in mx], materials=mats, hierarchy=tree(A.root), note=str(A.meta.get('note', '')))
    L.export_fbx(A, os.path.join(MODELS, name + '.fbx'))
    print(f'EXPORT {name:18s} tris={tris:5d} size={stats[name]["size"]} parts={sorted(per)}')
print('export', round(time.time() - t0, 1), 's')

mp = os.path.join(PROJ, 'Unity', 'Assets', 'Game', 'Art', 'art_materials.json')
mj = json.load(open(mp, encoding='utf-8'))
added = []
for k in sorted(used):
    if k in mj['materials'] or k not in L.MATS:
        continue
    base, shade, ol, cat, extra = L.MATS[k]
    d = {"base": base, "shade": shade, "outline": ol, "category": cat}
    d.update(extra)
    mj['materials'][k] = d
    added.append(k)
missing = sorted(k for k in used if k not in mj['materials'])
json.dump(mj, open(mp, 'w', encoding='utf-8'), ensure_ascii=False, indent=2)
print('MATERIALS added', added, 'missing', missing)
sp = os.path.join(ART, 'blend', 'asset_stats.json')
old = json.load(open(sp, encoding='utf-8')) if os.path.exists(sp) else {}
old.update(stats)
json.dump(old, open(sp, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
print('DONE', len(stats))
