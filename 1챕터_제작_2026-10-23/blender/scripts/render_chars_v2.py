# Re-import a round-4 character FBX, list its takes, check foot sliding, render contact-sheet cells at the game camera angle.
# usage: blender -b --factory-startup --python render_chars_v2.py -- fbx=<path> name=<Name> [cells=6] [only=Walk,Run] [noslip]
import sys, os, json, math
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import bpy
from mathutils import Vector
import ouat_lib as L
import ouat_render as RR
try:
    import ouat_chars_v2   # registers the new material slots for toonify
except Exception as e:
    print('WARN chars import', e)

args = dict(a.split('=', 1) for a in sys.argv[sys.argv.index('--') + 1:] if '=' in a)
flags = set(a for a in sys.argv[sys.argv.index('--') + 1:] if '=' not in a)
FBX = args['fbx']
NAME = args['name']
NC = int(args.get('cells', 6))
ONLY = set(args['only'].split(',')) if 'only' in args else None
ART = os.path.dirname(HERE)
RAW = os.path.join(ART, 'renders', 'raw', 'chars_v2', NAME + args.get('tag', ''))   # tag=_r6 keeps the round-4 cells
os.makedirs(RAW, exist_ok=True)
REP = json.load(open(os.path.join(ART, 'blend', 'chars_v2', 'report.json'), encoding='utf-8')).get(NAME, {})
H = REP.get('height') or 1.0
if 'height' in args:
    H = float(args['height'])

L.reset_scene()
sc = bpy.context.scene
sc.render.fps = 30
bpy.ops.import_scene.fbx(filepath=FBX, use_anim=True, automatic_bone_orientation=False, ignore_leaf_bones=False)
arm = [o for o in sc.objects if o.type == 'ARMATURE'][0]
meshes = [o for o in sc.objects if o.type == 'MESH']
root = arm
while root.parent:
    root = root.parent
print('ROOT', root.name, root.type, 'rot', tuple(round(math.degrees(a), 2) for a in root.rotation_euler), 'scale', tuple(root.scale))
print('BONES', [b.name for b in arm.data.bones])
print('MESHES', [(m.name, len(m.data.polygons)) for m in meshes])
acts = {}
for a in bpy.data.actions:
    nm = a.name.split('|')[-1]
    acts[nm] = a
    print('TAKE', a.name, 'range', tuple(a.frame_range))
ver = {'root': root.name, 'bones': [b.name for b in arm.data.bones], 'takes': {k: list(map(float, a.frame_range)) for k, a in acts.items()}}

# ---------------------------------------------------------------- foot slide check (planted flat foot must move back at v)
speeds = REP.get('speeds', {})
slip = {}
if 'noslip' not in flags:
    for clip, v in speeds.items():
        if clip not in acts:
            continue
        arm.animation_data.action = acts[clip]
        try:
            arm.animation_data.action_slot = acts[clip].slots[0]
        except Exception:
            pass
        f0, f1 = map(int, acts[clip].frame_range)
        geo = max(meshes, key=lambda m: len(m.data.vertices))
        idx = {}
        for sd in 'LR':
            gi = geo.vertex_groups['Foot' + sd].index
            idx[sd] = [v.index for v in geo.data.vertices if any(g.group == gi and g.weight > 0.5 for g in v.groups)]
        frames_pos = []
        for f in range(f0, f1 + 1):
            sc.frame_set(f)
            dg = bpy.context.evaluated_depsgraph_get()
            ev = geo.evaluated_get(dg)
            me_ = ev.to_mesh()
            mw = geo.matrix_world
            frames_pos.append({sd: [mw @ me_.vertices[i].co for i in idx[sd]] for sd in 'LR'})
            ev.to_mesh_clear()
        worst = 0.0
        n = 0
        gz = min(p.z for fp_ in frames_pos for sd in 'LR' for p in fp_[sd]) + 0.004
        for i in range(1, len(frames_pos)):
            for sd in 'LR':
                for pa, pb_ in zip(frames_pos[i - 1][sd], frames_pos[i][sd]):
                    if pa.z < gz and pb_.z < gz:     # sole vertex on the ground in both frames
                        vy = (pb_.y - pa.y) * 30.0           # Blender +Y = backwards
                        vx = (pb_.x - pa.x) * 30.0
                        worst = max(worst, math.hypot(vy - v, vx))
                        n += 1
        slip[clip] = dict(speed=v, planted_samples=n, max_slip_mps=round(worst, 3), max_slip_cm_per_frame=round(worst / 30 * 100, 2))
        print('SLIP', clip, slip[clip])
ver['slip'] = slip
json.dump(ver, open(os.path.join(RAW, 'verify.json'), 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
if 'verifyonly' in flags:
    sys.exit(0)

# ---------------------------------------------------------------- render setup (toon look + game camera)
root['ouat_size'] = max(0.9, H * 0.9)
RR.setup_render(res=(300, 340), samples=24, bg=L.hex2rgb('8F9196'))
sc.view_settings.view_transform = 'Standard'
gp = L.bmesh.new()
L.bmesh.ops.create_grid(gp, x_segments=1, y_segments=1, size=200)
me = bpy.data.meshes.new('Ground')
gp.to_mesh(me)
me.materials.append(L.get_mat('M_Paper'))
g = bpy.data.objects.new('Ground', me)
sc.collection.objects.link(g)
RR.prepare_all(outline_scale=float(args.get('ol', 0.6)), skip=('Ground',))
g.modifiers.clear()
# make the toon colour respond to light intensity/colour (dim world, warm pool): col *= 0.36 + 0.8 * light
for m in bpy.data.materials:
    if m.name not in L.MATS or not m.node_tree:
        continue
    nt = m.node_tree
    s2r = next((n for n in nt.nodes if n.bl_idname == 'ShaderNodeShaderToRGB'), None)
    em = next((n for n in nt.nodes if n.bl_idname == 'ShaderNodeEmission'), None)
    if s2r is None or em is None or not em.inputs['Color'].links:
        continue
    src = em.inputs['Color'].links[0].from_socket
    vm = nt.nodes.new('ShaderNodeVectorMath'); vm.operation = 'MULTIPLY_ADD'
    nt.links.new(s2r.outputs['Color'], vm.inputs[0])
    vm.inputs[1].default_value = (0.8, 0.8, 0.8)
    vm.inputs[2].default_value = (0.36, 0.36, 0.38)
    mul = nt.nodes.new('ShaderNodeMix'); mul.data_type = 'RGBA'; mul.blend_type = 'MULTIPLY'
    mul.inputs['Factor'].default_value = 1.0
    nt.links.new(src, mul.inputs[6]); nt.links.new(vm.outputs[0], mul.inputs[7])
    nt.links.new(mul.outputs[2], em.inputs['Color'])
# dim, drained underground light + one warm overhead pool (the light-shaft mood), per 10/23 direction
d = Vector((-0.44, 0.63, -0.64)).normalized()
sun = RR.add_sun((0, 0, 0), float(args.get('sun', 0.32)), color=(0.80, 0.84, 0.90))
sun.rotation_euler = d.to_track_quat('-Z', 'Y').to_euler()
RR.world_light(L.hex2rgb('A9ABAE'), float(args.get('amb', 0.42)))
sp = RR.add_spot((0.35, -0.45, 7.5), (0, 0, 0.0), energy=float(args.get('spot', 1500)), size_deg=float(args.get('pool', 15)), blend=0.6,
                 color=(1.0, 0.84, 0.6), radius=0.3)


def pool(on):
    sp.hide_render = not on

cam = RR.add_camera((0, -10, 5), (0, 0, 0.5))
cam.data.sensor_fit = 'VERTICAL'


def place_cam(az, extent, cy, pitch=25.0, dist=10.0, cx=0.0, cyy=0.0):
    p = math.radians(pitch)
    a = math.radians(az)
    tgt = Vector((cx, cyy, cy))
    pos = tgt + Vector((math.sin(a) * math.cos(p), -math.cos(a) * math.cos(p), math.sin(p))) * dist
    cam.location = pos
    cam.rotation_euler = (tgt - pos).to_track_quat('-Z', 'Y').to_euler()
    cam.data.angle_y = 2 * math.atan(extent / 2 / dist)


def set_frame(clip, f):
    if clip is None:
        arm.animation_data_create()
        arm.animation_data.action = None
        for pb in arm.pose.bones:
            pb.location = (0, 0, 0)
            pb.rotation_quaternion = (1, 0, 0, 0)
            pb.rotation_euler = (0, 0, 0)
        sc.frame_set(0)
        return
    arm.animation_data.action = acts[clip]
    try:
        arm.animation_data.action_slot = acts[clip].slots[0]
    except Exception:
        pass
    sc.frame_set(int(f))


if 'face' in flags:   # close-ups of the head (eye level + game pitch), dim light + warm pool
    hz = float(args.get('headz', H * 0.83))
    cells = []
    sc.render.resolution_x, sc.render.resolution_y = 520, 520
    clipf = args.get('faceclip', 'Idle')
    for i, (az, pitch, ext, lit, fr) in enumerate(((0, 6, 0.5, True, 0), (35, 8, 0.5, True, 0), (-35, 8, 0.5, True, 0), (90, 4, 0.5, True, 0),
                                                    (30, 25, 0.62, True, 0), (30, 25, 0.62, False, 0), (20, -12, 0.55, True, 40), (150, 15, 0.55, True, 0))):
        pool(lit)
        set_frame('LookUp' if fr == 40 else clipf, fr)
        place_cam(az, ext, hz, pitch=pitch, dist=3.0)
        fp = os.path.join(RAW, f'face_{i}.png')
        RR.render(fp)
        cells.append(fp)
    json.dump(cells, open(os.path.join(RAW, 'face.json'), 'w'))
    print('RENDERED', len(cells))
    sys.exit(0)
EXT = float(args.get('extent', H * 1.55))
CY = H * 0.48
cells = []
# turnaround (rest pose of Idle frame 0) + game-scale cell
for i, az in ([] if 'noturn' in flags else enumerate((0, 40, 90, 140, 180, -40))):
    pool(i < 5)
    set_frame('Idle' if 'Idle' in acts else None, 0)
    place_cam(az, EXT, CY)
    fp = os.path.join(RAW, f'turn_{i}.png')
    RR.render(fp)
    cells.append(('turn', i, az, fp))
# true game scale: 1080p frame covers 2*10*tan(16deg) = 5.73 m vertically -> 340 px cell = 1.80 m
set_frame('Idle' if 'Idle' in acts else None, 0)
pool(False)
if 'noturn' not in flags:
  place_cam(35, max(340 / 1080 * 2 * 10 * math.tan(math.radians(16)), H * 1.15), CY)
  fp = os.path.join(RAW, 'turn_game.png')
  RR.render(fp)
  cells.append(('turn', 'game', 35, fp))

pool(True)
order = REP.get('clips') and [c['clip'] for c in REP['clips']] or sorted(acts)
for clip in order:
    if clip not in acts or (ONLY and clip not in ONLY):
        continue
    f0, f1 = map(int, acts[clip].frame_range)
    loop = any(c['clip'] == clip and c['loop'] for c in REP.get('clips', []))
    if loop:
        fr = [f0 + (f1 - f0) * k / NC for k in range(NC)]
    else:
        fr = [f0 + (f1 - f0) * k / (NC - 1) for k in range(NC)]
    az = 70 if clip in ('Walk', 'Run', 'RunAway', 'Carry', 'Squeeze', 'Startle', 'TugSleeve', 'TieCord', 'FileNose', 'Sulk', 'Grab', 'Offer', 'Recoil', 'Push', 'Bow', 'BowHold', 'Rise', 'Reach', 'Gather', 'FallTumble', 'LieDown', 'GetUp', 'SitIdle', 'Kneel', 'Greet', 'Cower') else 35
    for k, f in enumerate(fr):
        set_frame(clip, round(f))
        place_cam(az, EXT, CY)
        fp = os.path.join(RAW, f'{clip}_{k}.png')
        RR.render(fp)
        cells.append((clip, k, round(f), fp))
json.dump(dict(cells=cells, extent=EXT, height=H), open(os.path.join(RAW, 'cells.json'), 'w', encoding='utf-8'), ensure_ascii=False, indent=0)
print('RENDERED', len(cells))
