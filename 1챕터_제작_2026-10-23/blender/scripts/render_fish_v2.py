# -*- coding: utf-8 -*-
"""Fish v2 review: re-import the exported Fish.fbx (+ hero and Kinopio FBX for scale), play its takes and render cells
at the game camera (pitch 25, vertical fov 32) under dim underground light, black pond disc.
usage: blender -b --factory-startup --python render_fish_v2.py -- [fbx=<path>] [samples=16] [res=880x500] [only=cellname,..]
writes art/renders/raw/19_fish/<cell>.png + cells.json -> compose_fish_v2.py"""
import sys, os, json, math
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import bpy
from mathutils import Vector
import ouat_lib as L
import ouat_render as RR
import ouat_craft  # noqa: registers craft material slots
import ouat_fish_v2  # noqa: registers fish material slots
try:
    import ouat_chars_v2  # noqa: character material slots
except Exception as e:
    print('WARN chars', e)

argv = sys.argv[sys.argv.index('--') + 1:] if '--' in sys.argv else []
args = dict(a.split('=', 1) for a in argv if '=' in a)
ART = os.path.dirname(HERE)
PROJ = os.path.dirname(ART)
MODELS = os.path.join(PROJ, 'Unity', 'Assets', 'Game', 'Art', 'Models')
FBX = args.get('fbx', os.path.join(ART, 'blend', 'chars_v2', 'fbx', 'Fish.fbx'))
RAW = os.path.join(ART, 'renders', 'raw', '19_fish')
os.makedirs(RAW, exist_ok=True)
SAMPLES = int(args.get('samples', 16))
RES = tuple(int(x) for x in args.get('res', '880x500').split('x'))
ONLY = set(args['only'].split(',')) if 'only' in args else None

L.MATS.setdefault('R_Ground', ('8E9094', '6E7176', False, 'paper', {'hatch': True}))
AMBIENT = (0.36, 0.37, 0.40)
LIGHT_K = 0.55
DRAIN = 0.45
KEEP_KEYS = ('Bluebird', 'CapNavy', 'EyeShine', 'Brass', 'Iron', 'Rope', 'M_Wood', 'Leather', 'Book', 'PageWhite', 'Porcelain',
             'LampGlow', 'Light', 'Skin', 'Hair', 'Hero')

L.reset_scene()
sc = bpy.context.scene
sc.render.fps = 30


def import_fbx(path):
    before = set(bpy.data.objects)
    acts0 = set(bpy.data.actions)
    bpy.ops.import_scene.fbx(filepath=path, use_anim=True, automatic_bone_orientation=False, ignore_leaf_bones=False)
    new = [o for o in bpy.data.objects if o not in before]
    arm = [o for o in new if o.type == 'ARMATURE'][0]
    acts = {a.name.split('|')[-1]: a for a in bpy.data.actions if a not in acts0}
    return arm, new, acts


fish, fish_objs, ACTS = import_fbx(FBX)
fish['ouat_size'] = 12.0
print('TAKES', sorted(ACTS))
print('BONES', [b.name for b in fish.data.bones])
geo = [o for o in fish_objs if o.type == 'MESH'][0]
print('TRIS', sum(len(p.vertices) - 2 for p in geo.data.polygons))

extras = []
for nm, pos in (('Hero_Bluebird', (2.0, -8.2, 0)), ('Kinopio', (0.6, -8.9, 0))):
    p = os.path.join(MODELS, nm + '.fbx')
    if not os.path.exists(p):
        continue
    a, objs, _ = import_fbx(p)
    a.animation_data_create()
    a.animation_data.action = None
    for pb in a.pose.bones:
        pb.rotation_quaternion = (1, 0, 0, 0)
        pb.location = (0, 0, 0)
    a.location = pos
    a.rotation_euler = (a.rotation_euler.x, a.rotation_euler.y, math.radians(180 + (15 if nm == 'Kinopio' else -10)))
    a['ouat_size'] = 1.25
    extras.append(a)

# ground + black pond
def disc(r, z, mat, n=64, name='disc'):
    me = bpy.data.meshes.new(name)
    vs = [(0, 0, z)] + [(math.cos(2 * math.pi * i / n) * r, math.sin(2 * math.pi * i / n) * r, z) for i in range(n)]
    me.from_pydata(vs, [], [(0, i + 1, (i + 1) % n + 1) for i in range(n)])
    me.materials.append(L.get_mat(mat))
    ob = bpy.data.objects.new(name, me)
    sc.collection.objects.link(ob)
    return ob


ground = disc(200, 0.0, 'R_Ground', name='R_GroundDisc')
pond = disc(6.0, 0.012, 'M_Pond', n=48, name='PondSurface')
rim = L.stroke([Vector((math.cos(2 * math.pi * i / 48) * 6.05, math.sin(2 * math.pi * i / 48) * 6.05, 0.03)) for i in range(49)], 0.06, taper=False)
me = bpy.data.meshes.new('rim'); rim.to_mesh(me); me.materials.append(L.get_mat('M_Ink'))
sc.collection.objects.link(bpy.data.objects.new('PondRim', me))

RR.setup_render(res=RES, samples=SAMPLES, bg=L.hex2rgb('5E636B'))
RR.prepare_all(outline_scale=1.0, grain=0.05, hatch_scale=300.0, skip=('R_GroundDisc', 'PondSurface', 'PondRim'))


def is_keep(name):
    return any(k in name for k in KEEP_KEYS)


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


dim_toon()
# dim cool key from high behind-left of the camera (like the level's weak sun), cool world fill
RR.add_sun((52, 0, -35), 1.0, color=(0.86, 0.89, 0.95), angle=8)
RR.world_light(L.hex2rgb('6F757E'), 0.0)
cam = RR.add_camera((0, -20, 10), (0, 0, 2))
cam.data.sensor_fit = 'VERTICAL'


def game_cam(target, yaw=20.0, pitch=25.0, dist=22.0, fov=32.0):
    t = Vector(target)
    p, y = math.radians(pitch), math.radians(yaw)
    d = Vector((math.sin(y) * math.cos(p), -math.cos(y) * math.cos(p), math.sin(p)))
    cam.location = t + d * dist
    cam.rotation_euler = (t - cam.location).to_track_quat('-Z', 'Y').to_euler()
    cam.data.angle_y = math.radians(fov)


def set_frame(clip, f):
    fish.animation_data_create()
    fish.animation_data.action = ACTS[clip]
    try:
        fish.animation_data.action_slot = ACTS[clip].slots[0]
    except Exception:
        pass
    sc.frame_set(int(f))


CELLS = [  # name, clip, frame, yaw, label
    ('hidden', 'Hidden', 0, 22, 'Hidden f0 · 물 밑(보이지 않음)'),
    ('rise_1', 'Rise', 24, 22, 'Rise f24 · 주둥이부터 솟음'),
    ('rise_2', 'Rise', 36, 22, 'Rise f36'),
    ('rise_3', 'Rise', 44, 22, 'Rise f44 · 최고점'),
    ('rise_4', 'Rise', 58, 22, 'Rise f58 · 내려앉음'),
    ('idle_0', 'Idle', 0, 22, 'Idle f0 · 반쯤 나와 떠 있음'),
    ('idle_side', 'Idle', 60, 80, 'Idle f60 · 옆에서'),
    ('idle_far', 'Idle', 30, 200, 'Idle f30 · 뒤에서(덜 그린 몸)'),
    ('open_end', 'OpenMouth', 45, 22, 'OpenMouth f45 · 입 벌린 채'),
    ('open_side', 'OpenMouth', 45, 70, 'OpenMouth f45 · 옆(목구멍)'),
    ('swal_1', 'Swallow', 6, 22, 'Swallow f6 · 탁 닫음'),
    ('swal_2', 'Swallow', 14, 22, 'Swallow f14 · 목 부풂·머리 젖힘'),
    ('swal_3', 'Swallow', 27, 22, 'Swallow f27 · 꿀꺽'),
    ('spit_1', 'Spit', 10, 22, 'Spit f10 · 뒤로 젖힘'),
    ('spit_2', 'Spit', 16, 22, 'Spit f16 · 앞으로 뱉음'),
    ('spit_3', 'Spit', 24, 22, 'Spit f24'),
    ('sink_1', 'Sink', 22, 22, 'Sink f22'),
    ('sink_2', 'Sink', 40, 22, 'Sink f40 · 가라앉음'),
]
out = []
for nm, clip, f, yaw, label in CELLS:
    if ONLY and nm not in ONLY:
        continue
    set_frame(clip, f)
    game_cam((0, -3.0, 2.3), yaw=yaw, pitch=25, dist=20)
    fp = os.path.join(RAW, nm + '.png')
    RR.render(fp)
    out.append(dict(name=nm, clip=clip, frame=f, label=label, path=fp))
    print('CELL', nm)
jp = os.path.join(RAW, 'cells.json')
old = json.load(open(jp, encoding='utf-8')) if os.path.exists(jp) else {}
for c in out:
    old[c['name']] = c
json.dump(old, open(jp, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
print('RENDERED', len(out))
