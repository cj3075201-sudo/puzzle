# -*- coding: utf-8 -*-
"""10/23 story props review renders (RedCord, Sack, HookPole, Decree, Lumps, Kinopio's house / den, Bell, OfferingPile):
game camera (pitch ~25, fov 32 vertical) under the same DIM underground light as render_props_review.py (17_ sheets).
Characters (Hero, Kinopio, Silhouette) are imported from the exported FBX for scale.
usage: blender -b --factory-startup --python render_offering_review.py -- shot=<tiles|house|den|cart|pond|plaza> [samples=24] [only=A,B]
Writes art/renders/raw/19/*.png (+ tiles.json); compose_offering_review.py makes art/renders/19_소품_*.png."""
import sys, os, json, math
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import bpy
from mathutils import Vector
import ouat_lib as L
import ouat_render as R
import ouat_props as P
import ouat_dressing as D
import ouat_offering as OF
import ouat_offering2 as OF2
try:
    import ouat_chars_v2   # registers the character material slots (M_Skin, M_PaintNavy...) for imported FBX
except Exception as e:
    print('chars_v2 import failed', e)

argv = sys.argv[sys.argv.index('--') + 1:] if '--' in sys.argv else []
args = dict(a.split('=', 1) for a in argv if '=' in a)
SHOT = args.get('shot', 'tiles')
SAMPLES = int(args.get('samples', 24))
RES = tuple(int(x) for x in args.get('res', '1600x900').split('x'))
ONLY = set(args['only'].split(',')) if 'only' in args else None
ART = os.path.dirname(HERE)
PROJ = os.path.dirname(ART)
RAW = os.path.join(ART, 'renders', 'raw', '19')
FBX = os.path.join(ART, 'blend', 'chars_v2', 'fbx')
os.makedirs(RAW, exist_ok=True)

BUILDERS = {}
for mod in (P, D, OF, OF2):
    for n, f in mod.ASSETS:
        BUILDERS[n] = f
L.MATS.setdefault('R_Ground', ('F1EEE6', 'C9CCCF', False, 'paper', {'hatch': False}))   # level ground: shader hatch off (§10-2)
L.MATS.setdefault('R_Wall', ('E2E0DA', '9EA3A8', True, 'paper', {'hatch': True}))
L.MATS.setdefault('R_Pond', ('0B0A09', '050404', False, 'silhouette', {}))

AMBIENT = (0.36, 0.37, 0.40)
LIGHT_K = 0.55
DRAIN = 0.45
KEEP_KEYS = ('Bluebird', 'Beak', 'CapNavy', 'EyeShine', 'Brass', 'Iron', 'Rope', 'M_Wood', 'Leather', 'Book', 'PageWhite',
             'Porcelain', 'LampGlow', 'Light')


def is_keep(name):
    return L.MATS.get(name, (0, 0, 0, '', {}))[4].get('keep') or any(k in name for k in KEEP_KEYS)


def dim_toon():
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


def quad(name, mat, pts):
    me = bpy.data.meshes.new(name)
    me.from_pydata(pts, [], [tuple(range(len(pts)))])
    me.materials.append(L.get_mat(mat))
    ob = bpy.data.objects.new(name, me)
    bpy.context.scene.collection.objects.link(ob)
    return ob


def ground(size=200, z=0.0):
    s = size / 2
    return quad('R_Ground', 'R_Ground', [(-s, -s, z), (s, -s, z), (s, s, z), (-s, s, z)])


def wall(y, x0, x1, h=3.0):
    return quad('R_Wall', 'R_Wall', [(x0, y, 0), (x0, y, h), (x1, y, h), (x1, y, 0)])


def pond(c, r):
    import bmesh
    me = bpy.data.meshes.new('R_Pond')
    pts = [(c[0] + math.cos(a) * r * (1 + 0.04 * math.sin(a * 5)), c[1] + math.sin(a) * r, 0.01) for a in [i * 2 * math.pi / 40 for i in range(40)]]
    me.from_pydata(pts, [], [tuple(range(40))])
    me.materials.append(L.get_mat('R_Pond'))
    ob = bpy.data.objects.new('R_Pond', me)
    bpy.context.scene.collection.objects.link(ob)


def build(name, loc=(0, 0, 0), rz=0.0, rx=0.0, ry=0.0, scale=1.0):
    A = BUILDERS[name]()
    A.root.location = Vector(loc)
    A.root.rotation_euler = (math.radians(rx), math.radians(ry), math.radians(rz))
    A.root.scale = (scale,) * 3
    return A


def char(name, loc=(0, 0, 0), rz=0.0):
    """import an exported character FBX (rest pose) and remap its materials to the toon slots"""
    before = set(bpy.data.objects)
    bpy.ops.import_scene.fbx(filepath=os.path.join(FBX, name + '.fbx'), use_anim=False)
    new = [o for o in bpy.data.objects if o not in before]
    root = next(o for o in new if o.parent is None)
    for o in new:
        if o.type == 'MESH':
            for i, m in enumerate(o.data.materials):
                if m is None:
                    continue
                base = m.name.split('.')[0]
                if base in L.MATS:
                    o.data.materials[i] = L.get_mat(base)
    root.location = Vector(loc)
    root.rotation_euler = (math.radians(90), 0, math.radians(rz))
    root['ouat_size'] = 1.0
    return root


def game_cam(target, yaw=20.0, pitch=25.0, dist=10.0, fov=32.0):
    t = Vector(target)
    p, y = math.radians(pitch), math.radians(yaw)
    d = Vector((math.sin(y) * math.cos(p), -math.cos(y) * math.cos(p), math.sin(p)))
    cam = R.add_camera(t + d * dist, t, lens=50)
    cam.data.sensor_fit = 'VERTICAL'
    cam.data.angle_y = math.radians(fov)
    return cam


def lights(pool_at=None, pool_power=0.5, lamps=(), lamp_energy=160):
    R.add_sun((50, 0, -30), 1.0, color=(0.86, 0.89, 0.95), angle=8)
    R.world_light(L.hex2rgb('6F757E'), 0.0)
    if pool_at is not None:
        c = Vector(pool_at)
        R.add_spot(c + Vector((0.6, 1.0, 26)), c, energy=14000 * pool_power, size_deg=26, blend=0.85, color=(1.0, 0.92, 0.74), radius=1.5, name='Pool')
    for p in lamps:
        R.add_point(p, energy=lamp_energy, color=(1.0, 0.78, 0.45), radius=0.15)


def setup(bg='6A7079'):
    R.setup_render(res=RES, samples=SAMPLES, bg=L.hex2rgb(bg))


PREVIEW_TEX = {'DecreeOpen|Face': 'tex_decree_face.png', 'DecreeOpen|HumanText': 'tex_human_text.png', 'WallDrawing|Face': 'tex_wall_drawing.png'}


def preview_textures():
    """stand-in pictures on the UV planes (preview only; the FBX keeps plain materials)"""
    for ob in bpy.data.objects:
        key = next((k for k in PREVIEW_TEX if ob.name.startswith(k)), None)
        if key is None or ob.type != 'MESH':
            continue
        path = os.path.join(RAW, PREVIEW_TEX[key])
        if not os.path.exists(path):
            continue
        m = bpy.data.materials.new('R_Tex_' + key.replace('|', '_'))
        m.use_nodes = True
        nt = m.node_tree
        nt.nodes.clear()
        out = nt.nodes.new('ShaderNodeOutputMaterial')
        em = nt.nodes.new('ShaderNodeEmission')
        tx = nt.nodes.new('ShaderNodeTexImage')
        tx.image = bpy.data.images.load(path)
        mul = nt.nodes.new('ShaderNodeMix'); mul.data_type = 'RGBA'; mul.blend_type = 'MULTIPLY'
        mul.inputs['Factor'].default_value = 1.0
        mul.inputs[7].default_value = (0.58, 0.58, 0.6, 1)
        nt.links.new(tx.outputs['Color'], mul.inputs[6])
        nt.links.new(mul.outputs[2], em.inputs['Color'])
        nt.links.new(em.outputs[0], out.inputs['Surface'])
        for i in range(len(ob.data.materials)):
            ob.data.materials[i] = m


def finish(path):
    preview_textures()
    R.prepare_all(outline_scale=1.0, grain=0.05, hatch_scale=300.0)
    dim_toon()
    R.render(path)


TILES = ['RedCord', 'Sack', 'Sack_Open', 'HookPole', 'DecreeScroll', 'DecreeOpen', 'Lump_Brother', 'Lump_4', 'Lump_5',
         'NoseFileStone', 'SawdustPile', 'HiddenStash', 'WallDrawing', 'Bell', 'OfferingPile']


TILES2 = ['BarkDoor', 'ClothCover', 'MusicBox', 'MirrorShard', 'SpinTop', 'Torch', 'CordBasket', 'CordHook', 'KidWorkbench', 'SawdustBits']
SET2 = args.get('set') == '2'


def shot_tiles():
    info = {}
    pre = 'tiles2' if SET2 else 'tiles'
    for n in [n for n in (TILES2 if SET2 else TILES) if ONLY is None or n in ONLY]:
        L.reset_scene()
        setup()
        A = build(n)
        mn, mx = A.bounds()
        size = max((mx - mn).x, (mx - mn).y, (mx - mn).z)
        ground(400, min(0.0, mn.z) if n != 'RedCord' else mn.z - 0.01)
        if n in ('WallDrawing', 'CordHook'):
            wall(0.001, -2, 2)
        if n == 'CordHook':
            A.root.location = Vector((0, 0, 1.1))
            mn, mx = A.bounds()
        c = (mn + mx) / 2
        lights()
        dist = max(0.9, size * 1.8) * (2.2 if n == 'CordHook' else 1.0)
        if n == 'Torch':
            lights(lamps=[tuple(c + Vector((0, 0, 0.9)))])
        game_cam(c, yaw=-20 if n in ('WallDrawing', 'CordHook') else 28, pitch=12 if n in ('WallDrawing', 'CordHook') else 25, dist=dist, fov=32)
        finish(os.path.join(RAW, f'{pre}__{n}.png'))
        tris, per = A.tris()
        info[n] = dict(tris=tris, size=[round(v, 2) for v in (mx - mn)], parts=sorted(per.keys()))
        print('TILE', n, tris)
    jp = os.path.join(RAW, pre + '.json')
    old = json.load(open(jp, encoding='utf-8')) if os.path.exists(jp) else {}
    old.update(info)
    json.dump(old, open(jp, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)


def shot_house():
    """Kinopio's house: the brother lump on a chair, sawdust, the nose-file stone; Kinopio and the hero (red cord on the cape)."""
    setup(); ground(); wall(2.2, -6, 6)
    build('Chair', (0.6, 1.2, 0), -15)
    build('Lump_Brother', (0.6, 1.17, 0.5), -15)
    build('SawdustPile', (-0.9, 0.3, 0), 10)
    build('NoseFileStone', (-1.6, 1.0, 0), 25)
    build('Lump_4', (2.4, 1.6, 0), -20)
    char('Kinopio', (-0.5, -0.6, 0), -40)
    char('Hero_Bluebird', (1.5, -0.9, 0), 30)
    build('RedCord', (1.5 - 0.08, -0.9 - 0.16, 0.93), 30)   # approx. where the cape knot sits
    lights(pool_at=(0.2, 0.6, 0), pool_power=0.35)
    game_cam((0.3, 0.4, 0.6), yaw=10, pitch=25, dist=7.5)
    finish(os.path.join(RAW, 'house.png'))


def shot_den():
    setup(); ground(); wall(1.0, -4, 4)
    build('WallDrawing', (0.2, 1.0, 0), 0)
    build('HiddenStash', (-0.8, 0.0, 0), 15)
    build('Sack_Open', (1.6, 0.2, 0), -30)
    char('Kinopio', (0.6, -0.5, 0), -20)
    lights(pool_at=(-0.4, 0.2, 0), pool_power=0.3)
    game_cam((0.0, 0.2, 0.6), yaw=-12, pitch=25, dist=6.5)
    finish(os.path.join(RAW, 'den.png'))


def shot_cart():
    setup(); ground()
    A = build('Cart', (0, 0, 0), 70)
    build('OfferingPile', (0, 0, 0), 70).root.location = Vector((0.1 * math.cos(math.radians(160)), 0.1 * math.sin(math.radians(160)), 0.8))
    build('Sack', (-2.0, 1.0, 0), 10)
    build('Sack_Open', (-2.6, -0.4, 0), -40)
    build('HookPole', (1.9, 0.9, 0), 0, ry=-14)
    char('Silhouette_A', (1.4, 0.2, 0), 60)
    char('Hero_Bluebird', (-0.8, -1.8, 0), -20)
    lights(pool_at=(0, 0, 0), pool_power=0.25)
    game_cam((-0.2, 0.2, 0.7), yaw=15, pitch=25, dist=9.5)
    finish(os.path.join(RAW, 'cart.png'))


def shot_pond():
    setup(); ground(); pond((0, 4.0), 3.2)
    build('DecreeOpen', (-0.6, 0.2, 0), 15)
    build('DecreeScroll', (0.9, 0.6, 0), -30)
    build('Lump_5', (2.2, 1.0, 0), -30)
    build('Lump_Brother', (-2.2, 1.0, 0), 25)
    char('Hero_Bluebird', (1.3, -1.3, 0), 20)
    lights(pool_at=(0, 0.5, 0), pool_power=0.2)
    game_cam((0, 0.6, 0.4), yaw=5, pitch=25, dist=7.0)
    finish(os.path.join(RAW, 'pond.png'))


def shot_plaza():
    setup(); ground()
    build('Bell', (0, 1.5, 0), 0)
    build('LampPost', (-2.6, 0.6, 0), 0)
    build('Bench_Puppet', (2.4, 0.4, 0), -20)
    char('Hero_Bluebird', (0.9, -0.8, 0), 160)
    char('Villager_A', (-1.2, -0.2, 0), 20)
    lights(lamps=[(-2.6 + 0.38, 0.6, 2.62)])
    game_cam((0, 0.8, 1.4), yaw=8, pitch=25, dist=10.0)
    finish(os.path.join(RAW, 'plaza.png'))


def shot_den2():
    """secret den entrance in the old tree: bark door, torch, cord hook on the wall, cord basket, Kinopio"""
    setup(); ground(); wall(1.2, -5, 5)
    A = build('BarkDoor', (0.0, 1.17, 0), 0)
    A.objs['Door'].rotation_euler = (0, 0, math.radians(-55))     # swung open
    build('Torch', (-1.3, 0.6, 0), 0)
    build('CordHook', (1.2, 1.2, 1.15), 0)
    build('CordBasket', (1.4, 0.5, 0), -20)
    build('SawdustBits', (0.3, -0.4, 0), 30)
    char('Kinopio', (0.6, -0.2, 0), -30)
    lights(lamps=[(-1.3, 0.6, 1.8)], lamp_energy=35)
    game_cam((0.0, 0.5, 0.8), yaw=8, pitch=25, dist=7.0)
    finish(os.path.join(RAW, 'den2.png'))


def shot_bench():
    setup(); ground(); wall(1.0, -4, 4)
    build('KidWorkbench', (0.0, 0.55, 0), 0)
    build('NoseFileStone', (-1.2, 0.5, 0), 20)
    for k, (x, y, rz) in enumerate(((0.9, -0.3, 20), (1.5, -0.9, -40), (2.1, -1.6, 70))):
        build('SawdustBits', (x, y, 0), rz)
    char('Kinopio', (-0.5, -0.1, 0), 20)
    char('Hero_Bluebird', (1.1, -0.9, 0), -30)
    lights(pool_at=(0.2, 0.3, 0), pool_power=0.3)
    game_cam((0.2, 0.2, 0.55), yaw=6, pitch=25, dist=5.5)
    finish(os.path.join(RAW, 'bench.png'))


def shot_cloth():
    setup(); ground(); wall(1.6, -4, 4)
    build('Chair', (-0.7, 0.9, 0), -10)
    build('ClothCover', (-0.7, 0.87, 0.5), -10)
    build('Chair', (0.8, 0.9, 0), 10)
    build('Lump_4', (0.8, 0.87, 0.5), 10)
    build('MusicBox', (0.1, -0.4, 0), 25)
    build('MirrorShard', (-0.4, -0.7, 0), -30)
    build('SpinTop', (0.5, -0.8, 0), 0)
    char('Hero_Bluebird', (1.5, -1.0, 0), 150)
    lights(pool_at=(0.0, -0.5, 0), pool_power=0.3)
    game_cam((0.0, 0.0, 0.6), yaw=0, pitch=25, dist=5.5)
    finish(os.path.join(RAW, 'cloth.png'))


def shot_satchel():
    """hero with the new Satchel object (left) and with Satchel hidden (right), from the front 3/4 and back 3/4"""
    setup(); ground()
    for k, (x, rz, hide) in enumerate(((-0.9, 25, False), (-0.3, 155, False), (0.3, 25, True), (0.9, 155, True))):
        r = char('Hero_Bluebird', (x, 0, 0), rz)
        for o in r.children_recursive:
            if o.name.startswith('Satchel') and hide:
                o.hide_render = True
    lights(pool_at=(0, 0, 0), pool_power=0.3)
    game_cam((0, 0, 0.62), yaw=0, pitch=18, dist=4.2)
    finish(os.path.join(RAW, 'satchel.png'))


L.reset_scene()
{'den2': shot_den2, 'bench': shot_bench, 'cloth': shot_cloth, 'satchel': shot_satchel, 'tiles': shot_tiles, 'house': shot_house, 'den': shot_den, 'cart': shot_cart, 'pond': shot_pond, 'plaza': shot_plaza}[SHOT]()
print('RENDERED', SHOT)
