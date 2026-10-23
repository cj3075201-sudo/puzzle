# -*- coding: utf-8 -*-
"""10/23 prop + village review renders: game camera (pitch ~25, ~10 m, fov 32 vertical) under DIM underground
light with one bright warm shaft. Builds the assets fresh from the scripts (no .blend needed).
usage: blender -b --factory-startup --python render_props_review.py -- shot=<name> [samples=24] [res=1600x900]
shots: street, houses, fall, plaza, tiles_props, tiles_village, tiles_dressing
Writes art/renders/raw/17/<shot>*.png (+ tiles json); compose_props_review.py makes art/renders/17_소품_*.png."""
import sys, os, json, math, random
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import bpy
from mathutils import Vector
import ouat_lib as L
import ouat_render as R
import ouat_craft as CR
import ouat_props as P
import ouat_village as VL
import ouat_dressing as D

argv = sys.argv[sys.argv.index('--') + 1:] if '--' in sys.argv else []
args = dict(a.split('=', 1) for a in argv if '=' in a)
SHOT = args.get('shot', 'street')
SAMPLES = int(args.get('samples', 24))
RES = tuple(int(x) for x in args.get('res', '1600x900').split('x'))
ONLY = set(args['only'].split(',')) if 'only' in args else None
ART = os.path.dirname(HERE)
RAW = os.path.join(ART, 'renders', 'raw', '17')
os.makedirs(RAW, exist_ok=True)

BUILDERS = {}
for mod in (P, VL, D):
    for n, f in mod.ASSETS:
        BUILDERS[n] = f

# render-only ground (same values as the level's walkable paper, so contrast is honest)
L.MATS.setdefault('R_Ground', ('F1EEE6', 'C9CCCF', False, 'paper', {'hatch': True}))
L.MATS.setdefault('R_GroundLine', ('8A9099', '8A9099', False, 'line', {}))

AMBIENT = (0.36, 0.37, 0.40)     # engine: dim ambient ~0.3-0.4 linear grey
LIGHT_K = 0.55                   # how much direct light lifts the toon colour
DRAIN = 0.45                     # engine: global desaturation (0.3-0.6 by area) except 'keep' materials
KEEP_KEYS = ('Bluebird', 'Beak', 'CapNavy', 'EyeShine', 'Brass', 'Iron', 'Rope', 'M_Wood', 'Leather', 'Book', 'PageWhite',
             'Porcelain', 'LampGlow', 'Light')


def is_keep(name):
    return L.MATS.get(name, (0, 0, 0, '', {}))[4].get('keep') or any(k in name for k in KEEP_KEYS)


def build(name, loc=(0, 0, 0), rz=0.0):
    A = BUILDERS[name]()
    A.root.location = Vector(loc)
    A.root.rotation_euler = (0, 0, math.radians(rz))
    return A


def dim_toon():
    """Multiply every lit toon material by (ambient + k * light): the Unity change recommended in §12
    (OUATToon currently ignores light intensity, so everything sits at full paper brightness)."""
    for m in bpy.data.materials:
        if m.name not in L.MATS or not m.use_nodes:
            continue
        cat = L.MATS[m.name][3]
        if cat not in ('paper', 'painted'):
            continue
        nt = m.node_tree
        s2r = next((n for n in nt.nodes if n.type in ('SHADERTORGB', 'SHADER_TO_RGB')), None)
        em = next((n for n in nt.nodes if n.type == 'EMISSION'), None)
        if not s2r or not em or not em.inputs['Color'].links:
            continue
        src = em.inputs['Color'].links[0].from_socket
        add = nt.nodes.new('ShaderNodeMix'); add.data_type = 'RGBA'; add.blend_type = 'ADD'
        add.inputs['Factor'].default_value = LIGHT_K
        add.inputs[6].default_value = (*AMBIENT, 1)
        nt.links.new(s2r.outputs['Color'], add.inputs[7])
        mul = nt.nodes.new('ShaderNodeMix'); mul.data_type = 'RGBA'; mul.blend_type = 'MULTIPLY'
        mul.inputs['Factor'].default_value = 1.0
        if not is_keep(m.name) and DRAIN > 0:
            hsv = nt.nodes.new('ShaderNodeHueSaturation')
            hsv.inputs['Saturation'].default_value = 1.0 - DRAIN
            nt.links.new(src, hsv.inputs['Color'])
            src = hsv.outputs['Color']
        nt.links.new(src, mul.inputs[6])
        nt.links.new(add.outputs[2], mul.inputs[7])
        nt.links.new(mul.outputs[2], em.inputs['Color'])
        if L.MATS[m.name][4].get('emission'):
            em.inputs['Strength'].default_value = 1.6


def ground(size=400, z=0.0):
    me = bpy.data.meshes.new('ground')
    s = size / 2
    me.from_pydata([(-s, -s, z), (s, -s, z), (s, s, z), (-s, s, z)], [], [(0, 1, 2, 3)])
    me.materials.append(L.get_mat('R_Ground'))
    ob = bpy.data.objects.new('R_Ground', me)
    bpy.context.scene.collection.objects.link(ob)
    return ob


def game_cam(target, yaw=20.0, pitch=25.0, dist=10.0, fov=32.0):
    """Unity-like follow camera: yaw around Z (0 = looking along +Y in Blender = from the front -Y side)."""
    t = Vector(target)
    p = math.radians(pitch)
    y = math.radians(yaw)
    d = Vector((math.sin(y) * math.cos(p), -math.cos(y) * math.cos(p), math.sin(p)))
    cam = R.add_camera(t + d * dist, t, lens=50)
    cam.data.sensor_fit = 'VERTICAL'
    cam.data.angle_y = math.radians(fov)
    return cam


def lights(shaft_at=None, shaft_power=1.0, lamps=()):
    # dim key from the cave opening direction (weak), cool fill = world
    R.add_sun((50, 0, -30), 1.0, color=(0.86, 0.89, 0.95), angle=8)
    R.world_light(L.hex2rgb('6F757E'), 0.0)
    if shaft_at is not None:
        c = Vector(shaft_at)
        R.add_spot(c + Vector((0.6, 1.0, 26)), c, energy=14000 * shaft_power, size_deg=26, blend=0.85, color=(1.0, 0.92, 0.74), radius=1.5, name='Shaft')
    for p in lamps:
        R.add_point(p, energy=160, color=(1.0, 0.78, 0.45), radius=0.15)


def shaft_mesh(at, h=18):
    """visible light shaft (LightShaft asset) above the fall spot"""
    A = build('LightShaft', at) if 'LightShaft' in BUILDERS else None
    return A


def setup(bg='6A7079'):
    R.setup_render(res=RES, samples=SAMPLES, bg=L.hex2rgb(bg))


def finish(path, outline=1.0):
    R.prepare_all(outline_scale=outline, grain=0.05, hatch_scale=300.0)
    dim_toon()
    R.render(path)


# ------------------------------------------------------------------ shots
def shot_street():
    """A street running from the outskirts (left) to the plaza (right): houses at their completion stages + props."""
    setup()
    ground()
    build('House_1', (-15.0, 6.0, 0), -15)
    build('House_2', (-8.6, 7.4, 0), 10)
    build('House_3', (-1.0, 7.8, 0), 0)
    build('House_4', (6.2, 7.0, 0), -10)
    build('Tower_Dome', (14.5, 9.5, 0), 20)
    for n, x, y, rz in (('Barrel', -11.6, 3.2, 0), ('Crate', -10.6, 3.6, 20), ('Signpost', -5.2, 2.7, 10), ('Cart', -2.6, 1.6, 70),
                        ('Bench_Puppet', 2.6, 3.6, 0), ('Basket', 3.9, 2.9, 0), ('LampPost', 9.5, 3.0, 0), ('Lantern_Hanging', -13.0, 3.3, 30),
                        ('Chair', 4.8, 4.0, 15), ('PaintPot', -6.6, 3.4, 0), ('StoneTablet', 11.8, 4.2, -15)):
        if n in BUILDERS:
            build(n, (x, y, 0), rz)
    lights(shaft_at=(-19, 1, 0), shaft_power=0.6, lamps=[(9.5 + 0.38, 3.0, 2.62)])
    game_cam((-1.0, 4.0, 1.4), yaw=0, pitch=25, dist=34, fov=32)
    finish(os.path.join(RAW, 'street.png'))


def shot_houses_close():
    """two half-built houses at the real game distance (10 m)."""
    setup()
    ground()
    build('House_1', (-2.6, 1.0, 0), -20)
    build('House_2', (3.0, 2.2, 0), 15)
    build('Barrel', (0.6, -1.6, 0))
    build('Crate', (1.5, -1.3, 0), 25)
    build('Signpost', (-0.9, -2.0, 0), 8)
    lights(shaft_at=(-7, -3, 0), shaft_power=0.35)
    game_cam((0.2, 0.0, 1.6), yaw=15, pitch=25, dist=13, fov=32)
    finish(os.path.join(RAW, 'houses_close.png'))


def shot_fall():
    """the fall spot: brightest place, item pile in the shaft, ladder, drawn bar, junk around."""
    setup()
    ground()
    build('ItemPile', (0, 0, 0), 20)
    build('Ladder', (3.2, 1.8, 0), -30)
    build('DrawnBar', (-3.4, 1.4, 0), 25)
    build('Junk_Umbrella', (1.6, -1.6, 0), 40)
    build('Junk_Clock', (-1.4, -1.5, 0), -20)
    build('Junk_Book', (2.1, -0.6, 0), 70)
    build('Junk_Teacup', (-2.0, -0.4, 0), 0)
    build('Junk_Lantern', (0.9, 1.7, 0), 0)
    build('Junk_Shoe', (-0.6, 1.9, 0), 30)
    build('PinocchioPage', (-2.6, -2.0, 0), 25)
    build('House_1', (-5.5, 6.5, 0), -10)
    build('Sketch_Tree_3', (5.5, 5.5, 0), 0) if 'Sketch_Tree_3' in BUILDERS else None
    lights(shaft_at=(0, 0, 0), shaft_power=1.0)
    A = build('LightShaft', (0, 0, 0))
    A.root.scale = (0.42, 0.42, 0.7)
    game_cam((0, 0.5, 0.8), yaw=25, pitch=25, dist=10, fov=32)
    finish(os.path.join(RAW, 'fall.png'))


def shot_plaza():
    setup()
    ground()
    build('Tower_Dome', (-6.5, 9, 0), 15)
    build('House_4', (6.5, 7.5, 0), -20)
    build('PictureBoard', (0.5, 3.8, 0), 0)
    build('LampPost', (-3.2, 1.0, 0), 0)
    build('LampPost', (3.6, 1.2, 0), 0)
    build('Lantern_Hanging', (-1.2, 6.0, 0), 0)
    build('Banner_Unfinished', (2.6, 5.4, 0), 0)
    build('Bench_Puppet', (-4.6, -0.4, 0), 10)
    build('Chair', (4.6, -0.8, 0), -20)
    lights(shaft_at=None, lamps=[(-3.2 + 0.38, 1.0, 2.62), (3.6 + 0.38, 1.2, 2.62), (-0.6, 6.0, 2.45)])
    game_cam((0, 3.0, 1.8), yaw=10, pitch=25, dist=17, fov=32)
    finish(os.path.join(RAW, 'plaza.png'))


TILE_SETS = {
    'tiles_props': ['Ladder', 'Latch', 'DrawnBar', 'Cart', 'Chair', 'Signpost', 'StoneTablet', 'PictureBoard', 'LampPost',
                    'Fence_DrawnBar', 'ItemPile', 'Junk_Book', 'Junk_Umbrella', 'Junk_Clock', 'Junk_Shoe', 'Junk_Teacup', 'Junk_Lantern', 'Gap'],
    'tiles_village': ['House_1', 'House_2', 'House_3', 'House_4', 'Tower_Dome'],
    'tiles_dressing': ['Barrel', 'Crate', 'Basket', 'Bench_Puppet', 'Lantern_Hanging', 'PaintPot', 'Brush_Big', 'Banner_Unfinished',
                       'Sketch_Wall_1', 'Sketch_Wall_2', 'Sketch_Wall_3', 'Sketch_Tree_1', 'Sketch_Tree_2', 'Sketch_Tree_3',
                       'Sketch_Fence_1', 'Sketch_Arch', 'Stair_Sketch', 'Rubble_1'],
}


def shot_tiles(key):
    names = [n for n in TILE_SETS[key] if n in BUILDERS and (ONLY is None or n in ONLY)]
    info = {}
    for n in names:
        L.reset_scene()
        setup()
        A = build(n)
        mn, mx = A.bounds()
        size = max((mx - mn).x, (mx - mn).y, (mx - mn).z)
        g = ground(max(200, size * 30))
        c = (mn + mx) / 2
        lights(shaft_at=(0, 0, 0) if n == 'ItemPile' else None, shaft_power=0.12)
        dist = max(1.4, size * 1.75)
        game_cam(c, yaw=28, pitch=25, dist=dist, fov=32)
        out = os.path.join(RAW, f'{key}__{n}.png')
        finish(out)
        tris, per = A.tris()
        info[n] = dict(tris=tris, size=[round(v, 2) for v in (mx - mn)], parts=sorted(per.keys()))
        print('TILE', n, tris)
    jp = os.path.join(RAW, f'{key}.json')
    old = json.load(open(jp, encoding='utf-8')) if os.path.exists(jp) else {}
    old.update(info)
    json.dump(old, open(jp, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)


L.reset_scene()
if SHOT == 'street':
    shot_street()
elif SHOT == 'houses':
    shot_houses_close()
elif SHOT == 'fall':
    shot_fall()
elif SHOT == 'plaza':
    shot_plaza()
elif SHOT.startswith('tiles_'):
    shot_tiles(SHOT)
print('RENDERED', SHOT)
