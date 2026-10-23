# Preview renders for art-direction review. Opens art/blend/ouat_ch1_assets.blend (made by build_all.py).
# usage: blender -b <blend> --python render_previews.py -- shot=lineup|hero|props|kit|village_overview|village_plaza|village_pond [samples=32]
# Writes raw renders + label json to art/renders/raw/; compose_previews.py (python3) makes the final sheets.
import sys, os, json, math
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import bpy
from mathutils import Vector, Matrix
import ouat_lib as L
import ouat_render as R

argv = sys.argv[sys.argv.index('--') + 1:] if '--' in sys.argv else []
args = dict(a.split('=', 1) for a in argv if '=' in a)
SHOT = args.get('shot', 'lineup')
SAMPLES = int(args.get('samples', 32))
ART = os.path.dirname(HERE)
RAW = os.path.join(ART, 'renders', 'raw')
os.makedirs(RAW, exist_ok=True)
STATS = json.load(open(os.path.join(ART, 'blend', 'asset_stats.json'), encoding='utf-8'))


def root(name):
    return bpy.data.objects[name]


def part(asset, p):
    return bpy.data.objects[f'{asset}|{p}']


def hide_all_but(names):
    keep = set(names)
    for c in bpy.data.collections:
        on = c.name in keep
        c.hide_render = not on
        c.hide_viewport = not on


def place(name, x, y, z=0.0, rz=0.0):
    r = root(name)
    r.location = (x, y, z)
    r.rotation_euler = (0, 0, math.radians(rz))
    return r


def unity_place(name, ux, uz, uy=0.0, yaw=0.0, copy=False):
    """Place by Unity world coords (x, z, y-up, yaw deg). Blender = (-ux, -uz, uy), rot_z = -yaw."""
    r = root(name) if not copy else dup(name)
    r.location = (-ux, -uz, uy)
    r.rotation_euler = (0, 0, math.radians(-yaw))
    return r


_dup_count = {}


def dup(name):
    """Instance an asset hierarchy again (linked mesh data)."""
    src = root(name)
    _dup_count[name] = _dup_count.get(name, 0) + 1
    coll = bpy.data.collections.get(name)
    mapping = {}

    def copy(ob, parent):
        n = ob.copy()
        n.name = ob.name + f'#{_dup_count[name]}'
        coll.objects.link(n)
        n.parent = parent
        if parent:
            n.matrix_parent_inverse = ob.matrix_parent_inverse.copy()
        mapping[ob] = n
        for ch in ob.children:
            copy(ch, n)
        return n
    return copy(src, None)


def bounds_of(obj_root):
    mn = Vector((1e9,) * 3)
    mx = Vector((-1e9,) * 3)
    bpy.context.view_layer.update()
    for ob in [obj_root] + list(obj_root.children_recursive):
        if ob.type != 'MESH':
            continue
        for c in ob.bound_box:
            w = ob.matrix_world @ Vector(c)
            mn = Vector(map(min, mn, w))
            mx = Vector(map(max, mx, w))
    return mn, mx


def write_labels(cam, items, path, extra=None):
    bpy.context.view_layer.update()
    sc = bpy.context.scene
    out = {'res': [sc.render.resolution_x, sc.render.resolution_y], 'labels': []}
    for name, label, pt in items:
        x, y, z = R.project(cam, [pt])[0]
        out['labels'].append({'name': name, 'label': label, 'x': x, 'y': y})
    if extra:
        out.update(extra)
    json.dump(out, open(path, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)


def light_studio():
    R.add_sun((55, 0, -40), 3.0, name='Key')
    R.add_sun((60, 0, 140), 0.6, color=(0.85, 0.9, 1.0), shadow=False, name='Rim')
    R.world_light(L.hex2rgb('F1EEE6'), 0.25)


# ======================================================================
CHAR_ORDER = ['Hero_Bluebird', 'Kinopio', 'Villager_A', 'Villager_B', 'Villager_C', 'Mother', 'Chief',
              'Silhouette_A', 'Silhouette_B', 'Puppet', 'Lump_1', 'Lump_2', 'Lump_3']
KR = {'Hero_Bluebird': '주인공 파랑새', 'Kinopio': '키노피오', 'Villager_A': '주민 A', 'Villager_B': '주민 B',
      'Villager_C': '주민 C', 'Mother': '어미', 'Chief': '촌장(수호목)', 'Silhouette_A': '실루엣 A',
      'Silhouette_B': '실루엣 B', 'Puppet': '나무 인형+끈', 'Lump_1': '덩어리 1', 'Lump_2': '덩어리 2(표시)',
      'Lump_3': '덩어리 3', 'Fish': '물고기(약 9.9m)'}


def shot_lineup():
    names = CHAR_ORDER + ['Fish']
    hide_all_but(names)
    x = 0.0
    items = []
    gap = 0.6
    for n in CHAR_ORDER:
        r = root(n)
        mn, mx = bounds_of(r)
        w = mx.x - mn.x
        place(n, x - mn.x, 0, 0, 0)
        mn2, mx2 = bounds_of(r)
        items.append((n, KR[n], ((mn2.x + mx2.x) / 2, mn2.y, 0)))
        x += w + gap
    total = x
    # fish behind, bursting upward with the mouth open
    f = root('Fish')
    f.location = (total + 3.6, 4.0, 2.2)
    f.rotation_euler = (math.radians(-42), 0, math.radians(80))
    part('Fish', 'JawUpper').rotation_euler = (math.radians(-28), 0, 0)
    part('Fish', 'JawLower').rotation_euler = (math.radians(30), 0, 0)
    part('Fish', 'Tail').rotation_euler = (0, 0, math.radians(14))
    mnf, mxf = bounds_of(f)
    items.append(('Fish', KR['Fish'], ((mnf.x + mxf.x) / 2, mnf.y, 0.0)))
    R.setup_render(res=(3200, 1750), samples=SAMPLES, transparent=True)
    R.prepare_all()
    light_studio()
    # gentle ground shadow catcher: paper floor
    bpy.ops.mesh.primitive_plane_add(size=200, location=(total / 2, 10, 0))
    fl = bpy.context.active_object
    fl.data.materials.append(L.get_mat('M_Paper'))
    R.toonify(L.get_mat('M_Paper'))
    mnf, mxf = bounds_of(f)
    right = max(total, mxf.x + 0.5)
    cx = (right - 0.8) / 2
    cam = R.add_camera((cx, -60, 6.9), (cx, 0, 4.0), lens=50, ortho=(right + 0.8) * 1.02)
    # ruler: metres at the left
    bpy.context.view_layer.update()
    write_labels(cam, items, os.path.join(RAW, 'lineup.json'),
                 extra={'ruler': [R.project(cam, [(-0.45, 0, h)])[0][:2] for h in range(0, 11)]})
    R.render(os.path.join(RAW, 'lineup.png'))


def shot_hero():
    """Hero turnaround: front, 3/4, side, back + Kinopio next to it for scale."""
    hide_all_but(['Hero_Bluebird', 'Kinopio'])
    h = root('Hero_Bluebird')
    copies = [h, dup('Hero_Bluebird'), dup('Hero_Bluebird'), dup('Hero_Bluebird')]
    for i, (c, rz) in enumerate(zip(copies, (0, 35, 90, 180))):
        c.location = (i * 1.05, 0, 0)
        c.rotation_euler = (0, 0, math.radians(rz))
    place('Kinopio', 4 * 1.05, 0, 0, -20)
    R.setup_render(res=(2800, 1100), samples=SAMPLES, transparent=True)
    R.prepare_all(outline_scale=0.8)
    light_studio()
    cx = 2.1
    cam = R.add_camera((cx, -30, 3.0), (cx, 0, 0.55), lens=50, ortho=5.6)
    items = [(f'h{i}', t, (i * 1.05, 0, 0)) for i, t in enumerate(('앞', '3/4', '옆', '뒤'))] + [('k', '키노피오(0.8m)', (4.2, 0, 0))]
    write_labels(cam, items, os.path.join(RAW, 'hero.json'))
    R.render(os.path.join(RAW, 'hero.png'))


def grid_shot(names, out, cols, cell, res, labels, cam_dir=(0.55, -1.0, 0.62), ortho_pad=1.0, outline_scale=1.0):
    hide_all_but(names)
    items = []
    rows = (len(names) + cols - 1) // cols
    for i, n in enumerate(names):
        r = root(n)
        cxi, cyi = i % cols, i // cols
        mn, mx = bounds_of(r)
        c = (mn + mx) / 2
        px = cxi * cell
        py = -cyi * cell * 0.0
        pz = 0
        # lay rows out along Y (depth) so the camera sees a grid
        r.location = (px - c.x, cyi * cell * 1.15 - c.y, -mn.z)
        mn2, mx2 = bounds_of(r)
        items.append((n, labels.get(n, n), ((mn2.x + mx2.x) / 2, mn2.y, mn2.z)))
    R.setup_render(res=res, samples=SAMPLES, transparent=True)
    R.prepare_all(outline_scale=outline_scale)
    light_studio()
    cx = (cols - 1) * cell / 2
    cy = (rows - 1) * cell * 1.15 / 2
    d = Vector(cam_dir).normalized()
    cam = R.add_camera(Vector((cx, cy, 0)) + d * 300, (cx, cy, 0), lens=50, ortho=max(cols * cell, rows * cell * 1.15 * res[0] / res[1] * 0.7) * ortho_pad)
    write_labels(cam, items, os.path.join(RAW, out + '.json'))
    R.render(os.path.join(RAW, out + '.png'))


def shot_props():
    names = [n for n, s in STATS.items() if s['group'] == 'props']
    labels = {n: f"{n}" for n in names}
    grid_shot(names, 'props', cols=6, cell=3.2, res=(3200, 2400), labels=labels)


def shot_kit():
    names = [n for n, s in STATS.items() if s['group'] == 'village' and n not in ('LightShaft', 'CeilingHole')]
    big = [n for n in names if max(STATS[n]['size']) > 16]
    small = [n for n in names if n not in big]
    labels = {n: n for n in names}
    grid_shot(small, 'kit', cols=6, cell=14.0, res=(3200, 2400), labels=labels, outline_scale=1.0)


def shot_thumbs():
    """One framed 3/4 render per prop / village asset (transparent), tiled later by compose_previews."""
    names = [n for n, s in STATS.items() if s['group'] in tuple(args.get('groups', 'props,village').split(','))]
    R.setup_render(res=(900, 900), samples=SAMPLES, transparent=True)
    R.prepare_all()
    light_studio()
    d = Vector((0.62, -1.0, 0.6)).normalized()
    cam = R.add_camera((0, -10, 5), (0, 0, 0), lens=50, ortho=5)
    for n in names:
        hide_all_but([n])
        r = root(n)
        r.location = (0, 0, 0)
        r.rotation_euler = (0, 0, 0)
        mn, mx = bounds_of(r)
        c = (mn + mx) / 2
        right = d.cross(Vector((0, 0, 1))).normalized()
        up = right.cross(d).normalized()
        pts = [Vector((x, y, z)) for x in (mn.x, mx.x) for y in (mn.y, mx.y) for z in (mn.z, mx.z)]
        w = max(p.dot(right) for p in pts) - min(p.dot(right) for p in pts)
        h = max(p.dot(up) for p in pts) - min(p.dot(up) for p in pts)
        cam.data.ortho_scale = max(w, h) * 1.12
        cam.location = c + d * 200
        cam.rotation_euler = (-d).to_track_quat('-Z', 'Y').to_euler()
        R.render(os.path.join(RAW, 'thumbs', n + '.png'))


if __name__ == '__main__':
    import village_scene
    shots = {'lineup': shot_lineup, 'hero': shot_hero, 'props': shot_props, 'kit': shot_kit, 'thumbs': shot_thumbs}
    shots.update(village_scene.SHOTS)
    shots[SHOT]()
    print('RENDERED', SHOT)
