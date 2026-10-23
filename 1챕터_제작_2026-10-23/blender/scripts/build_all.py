# Build every chapter-1 asset, export one FBX per asset for Unity, write stats + material json, save the .blend.
# usage: blender -b --factory-startup --python build_all.py -- [only=Name1,Name2] [noexport]
import sys, os, json, time
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import bpy
import ouat_lib as L
import ouat_characters as C
import ouat_creatures as CR
argv = sys.argv[sys.argv.index('--') + 1:] if '--' in sys.argv else []
only = None
for a in argv:
    if a.startswith('only='):
        only = set(a[5:].split(','))
noexport = 'noexport' in argv

ART = os.path.dirname(HERE)
PROJ = os.path.dirname(ART)
MODELS = os.path.join(PROJ, 'Unity', 'Assets', 'Game', 'Art', 'Models')
os.makedirs(MODELS, exist_ok=True)

ASSETS = [
    ('Hero_Bluebird', C.build_hero), ('Kinopio', CR.build_kinopio), ('Chief', CR.build_chief), ('Mother', CR.build_mother),
    ('Villager_A', CR.build_villager_a), ('Villager_B', CR.build_villager_b), ('Villager_C', CR.build_villager_c),
    ('Silhouette_A', CR.build_silhouette_a), ('Silhouette_B', CR.build_silhouette_b),
    ('Lump_1', CR.build_lump_1), ('Lump_2', CR.build_lump_2), ('Lump_3', CR.build_lump_3),
    ('Fish', C.build_fish), ('Puppet', CR.build_puppet),
]
GROUP = {n: 'characters' for n, _ in ASSETS}
for modname, grp in (('ouat_props', 'props'), ('ouat_village', 'village'), ('ouat_dressing', 'dressing'), ('ouat_areas', 'level')):
    try:
        m = __import__(modname)
        for n, f in m.ASSETS:
            ASSETS.append((n, f))
            GROUP[n] = grp
    except Exception as e:
        import traceback; traceback.print_exc()
        print('SKIP module', modname, e)

L.reset_scene()
stats = {}
t0 = time.time()
for name, fn in ASSETS:
    if only and name not in only:
        continue
    A = fn()
    assert A.name == name, (A.name, name)
    tris, per = A.tris()
    per = {('Main' if k == name else k): v for k, v in per.items()}
    mn, mx = A.bounds()
    mats = sorted({m.name for ob in A.objs.values() if ob.type == 'MESH' for m in ob.data.materials})
    def tree(ob, depth=0):
        out = []
        for ch in sorted(ob.children, key=lambda o: o.name):
            out.append(('  ' * depth) + L.bare_name(name, ch.name) + ('' if ch.type == 'MESH' else ' (empty)'))
            out += tree(ch, depth + 1)
        return out
    stats[name] = dict(group=GROUP[name], tris=tris, parts=per, size=[round(v, 2) for v in (mx - mn)],
                       min=[round(v, 2) for v in mn], max=[round(v, 2) for v in mx], materials=mats, hierarchy=tree(A.root), note=str(A.meta.get('note', '')))
    print(f'ASSET {name:16s} tris={tris:5d} size={stats[name]["size"]}')
    # round-4 skinned characters come from build_chars_v2.py; never overwrite them with the old rigid versions
    V2_CHARS = {'Hero_Bluebird', 'Kinopio', 'Chief', 'Mother', 'Villager_A', 'Villager_B', 'Villager_C', 'Silhouette_A', 'Silhouette_B'}
    if not noexport and name not in V2_CHARS:
        L.export_fbx(A, os.path.join(MODELS, name + '.fbx'))
    # keep assets apart in the .blend
    A.coll.hide_viewport = False
print('build+export', round(time.time() - t0, 1), 's')

L.write_material_json(os.path.join(PROJ, 'Unity', 'Assets', 'Game', 'Art', 'art_materials.json'))
os.makedirs(os.path.join(ART, 'blend'), exist_ok=True)
sp = os.path.join(ART, 'blend', 'asset_stats.json')
old = {}
if only and os.path.exists(sp):
    old = json.load(open(sp, encoding='utf-8'))
old.update(stats)
json.dump(old, open(sp, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
if not only:
    bpy.ops.wm.save_as_mainfile(filepath=os.path.join(ART, 'blend', 'ouat_ch1_assets.blend'))
print('DONE')
