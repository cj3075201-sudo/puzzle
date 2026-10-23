# Round-4 skinned characters: build -> bake clips -> export one FBX per character -> report json.
# usage: blender -b --factory-startup --python build_chars_v2.py -- [only=Hero_Bluebird,Kinopio] [noexport]
import sys, os, json, time
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import bpy
import ouat_lib as L
import ouat_rig as RG
import ouat_chars_v2 as CH
import ouat_clips_r6 as R6      # round 6 (10/23): extra takes appended to existing characters
import ouat_collector as COL    # round 6: Collector

argv = sys.argv[sys.argv.index('--') + 1:] if '--' in sys.argv else []
only = None
for a in argv:
    if a.startswith('only='):
        only = set(a[5:].split(','))
noexport = 'noexport' in argv
publish = 'publish' in argv   # copy into Unity/Assets/Game/Art/Models + merge material json
stage = None                  # stage=<dir name under art/blend/chars_v2>: export there instead of fbx/ (no Unity copy)
for a in argv:
    if a.startswith('stage='):
        stage = a[6:]

ART = os.path.dirname(HERE)
PROJ = os.path.dirname(ART)
MODELS = os.path.join(PROJ, 'Unity', 'Assets', 'Game', 'Art', 'Models')
OUT = os.path.join(ART, 'blend', 'chars_v2')
os.makedirs(OUT, exist_ok=True)

BUILDERS = [(n, getattr(CH, f)) for n, f in (('Hero_Bluebird', 'build_hero'), ('Kinopio', 'build_kinopio'), ('Chief', 'build_chief'),
             ('Mother', 'build_mother'), ('Villager_A', 'build_villager_a'), ('Villager_B', 'build_villager_b'),
             ('Villager_C', 'build_villager_c'), ('Silhouette_A', 'build_silhouette_a'), ('Silhouette_B', 'build_silhouette_b'))
            if hasattr(CH, f)] + [('Collector', COL.build_collector)]

rep_path = os.path.join(OUT, 'report.json')
report = json.load(open(rep_path, encoding='utf-8')) if os.path.exists(rep_path) else {}
for name, fn in BUILDERS:
    if only and name not in only:
        continue
    t0 = time.time()
    L.reset_scene()
    bpy.context.scene.render.fps = RG.FPS
    R = fn()
    assert R.name == name, (R.name, name)
    R6.add_clips(R)
    R.build()
    clips = []
    RG.bake(R, clips)
    tris = R.tris()
    info = dict(tris=tris, bones=list(R.order), parents={b: R.parent(b) for b in R.order}, meshes=list(R.meshes),
                clips=clips, speeds=R.meta.get('speeds', {}), height=R.meta.get('height'))
    report[name] = info
    print(f'CHAR {name} tris={tris} bones={len(R.order)} clips={len(clips)} {time.time() - t0:.1f}s')
    for c in clips:
        print('   CLIP', c)
    if not noexport:
        fdir = os.path.join(OUT, stage or 'fbx')
        os.makedirs(fdir, exist_ok=True)
        RG.export(R, os.path.join(fdir, name + '.fbx'))
        if publish and not stage:
            import shutil
            shutil.copyfile(os.path.join(OUT, 'fbx', name + '.fbx'), os.path.join(MODELS, name + '.fbx'))
    if not stage:
        bpy.ops.wm.save_as_mainfile(filepath=os.path.join(OUT, name + '.blend'))

json.dump(report, open(rep_path, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
if not publish:
    print('DONE (staged only)')
    sys.exit(0)
# merge the new material slots into art_materials.json (keep every existing entry)
mp = os.path.join(PROJ, 'Unity', 'Assets', 'Game', 'Art', 'art_materials.json')
mj = json.load(open(mp, encoding='utf-8'))
for k, (base, shade, ol, cat, extra) in list(CH.NEW_MATS.items()) + list(COL.NEW_MATS.items()):
    d = {"base": base, "shade": shade, "outline": ol, "category": cat}
    d.update(extra)
    mj['materials'][k] = d
json.dump(mj, open(mp, 'w', encoding='utf-8'), ensure_ascii=False, indent=2)
print('DONE')
