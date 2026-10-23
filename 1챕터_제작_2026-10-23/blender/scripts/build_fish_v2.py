# Fish v2 (10/23): build -> bake clips -> export art/blend/chars_v2/fbx/Fish.fbx (+ report.json entry 'Fish').
# usage: blender -b --factory-startup --python build_fish_v2.py -- [publish]
#   publish = copy to Unity/Assets/Game/Art/Models/Fish.fbx and MERGE the new material slots into art_materials.json
#   (only missing keys are added; every other entry is left exactly as it is). Never touches build_all.py outputs.
import sys, os, json, time, shutil
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import bpy
import ouat_lib as L
import ouat_rig as RG
import ouat_fish_v2 as FV

argv = sys.argv[sys.argv.index('--') + 1:] if '--' in sys.argv else []
publish = 'publish' in argv
ART = os.path.dirname(HERE)
PROJ = os.path.dirname(ART)
MODELS = os.path.join(PROJ, 'Unity', 'Assets', 'Game', 'Art', 'Models')
OUT = os.path.join(ART, 'blend', 'chars_v2')
os.makedirs(os.path.join(OUT, 'fbx'), exist_ok=True)

t0 = time.time()
L.reset_scene()
bpy.context.scene.render.fps = RG.FPS
R = FV.build_fish()
R.build()
clips = []
FV.bake(R, clips)
tris = R.tris()
# rest-pose bounds + waterline footprint (world z = 0 = pond surface)
geo = R.meshes['Geo']
vs = [geo.matrix_world @ v.co for v in geo.data.vertices]
mn = [min(v[i] for v in vs) for i in range(3)]
mx = [max(v[i] for v in vs) for i in range(3)]
wl = []
for e in geo.data.edges:
    a, b = vs[e.vertices[0]], vs[e.vertices[1]]
    if (a.z > 0) != (b.z > 0):
        t = a.z / (a.z - b.z)
        wl.append(a.lerp(b, t))
foot = [[round(min(p[i] for p in wl), 2), round(max(p[i] for p in wl), 2)] for i in range(2)] if wl else None
mats = [m.name for m in geo.data.materials]
info = dict(tris=tris, bones=list(R.order), parents={b: R.parent(b) for b in R.order}, meshes=list(R.meshes), clips=clips,
            height=R.meta.get('height'), bounds_min=[round(x, 2) for x in mn], bounds_max=[round(x, 2) for x in mx],
            waterline_xy=foot, materials=mats)
print(f'FISH tris={tris} bones={len(R.order)} clips={len(clips)} {time.time() - t0:.1f}s')
print('BOUNDS', info['bounds_min'], info['bounds_max'], 'WATERLINE', foot)
print('MATS', mats)
for c in clips:
    print('   CLIP', c)
rep_path = os.path.join(OUT, 'report.json')
rep = json.load(open(rep_path, encoding='utf-8')) if os.path.exists(rep_path) else {}
rep['Fish'] = info
json.dump(rep, open(rep_path, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
fbx = os.path.join(OUT, 'fbx', 'Fish.fbx')
RG.export(R, fbx)
bpy.ops.wm.save_as_mainfile(filepath=os.path.join(OUT, 'Fish.blend'))
if publish:
    shutil.copyfile(fbx, os.path.join(MODELS, 'Fish.fbx'))
    mp = os.path.join(PROJ, 'Unity', 'Assets', 'Game', 'Art', 'art_materials.json')
    mj = json.load(open(mp, encoding='utf-8'))      # re-read right before writing (other agents merge too)
    added = []
    for k in mats:
        if k in mj['materials'] or k not in L.MATS:
            continue
        base, shade, ol, cat, extra = L.MATS[k]
        d = {"base": base, "shade": shade, "outline": ol, "category": cat}
        d.update(extra)
        mj['materials'][k] = d
        added.append(k)
    missing = [k for k in mats if k not in mj['materials']]
    json.dump(mj, open(mp, 'w', encoding='utf-8'), ensure_ascii=False, indent=2)
    print('PUBLISHED', os.path.join(MODELS, 'Fish.fbx'), 'materials added', added, 'missing', missing)
print('DONE')
