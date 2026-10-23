# -*- coding: utf-8 -*-
"""Key art (title / chapter card / chapter end) rendered from the REAL assets: Level_Ch1 a_fall diorama (rebuilt in-process
like slice_scene.py), the exported character/prop FBX (Unity/Assets/Game/Art/Models) posed from their baked takes,
the same toon + inverted-hull ink + hatch + paper grain look (ouat_render), lit cinematically.
usage:
  blender -b art/blend/ouat_ch1_assets.blend --python render_keyart.py -- shot=title [samples=48] [res=1920x1080] [tag=]
  blender -b --factory-startup --python render_keyart.py -- shot=card|end [samples=48]
  probe overrides: cam=x,z,y look=x,z,y fov=deg (Unity coordinates, y up)
Writes art/renders/raw/keyart/<shot><tag>.png; finish_keyart.py adds grain/vignette and writes the Pictures/ files."""
import sys, os, json, math
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import bpy
from mathutils import Vector, Matrix
import ouat_lib as L
import ouat_render as R
import ouat_craft  # noqa: material slots
import ouat_fish_v2  # noqa
import ouat_offering as OF
try:
    import ouat_chars_v2  # noqa
except Exception as e:
    print('WARN chars', e)

argv = sys.argv[sys.argv.index('--') + 1:] if '--' in sys.argv else []
args = dict(a.split('=', 1) if '=' in a else (a, '1') for a in argv)
SHOT = args.get('shot', 'title')
TAG = args.get('tag', '')
SAMPLES = int(args.get('samples', 48))
RES = tuple(int(x) for x in args.get('res', '1920x1080').split('x'))
ART = os.path.dirname(HERE)
PROJ = os.path.dirname(ART)
MODELS = os.path.join(PROJ, 'Unity', 'Assets', 'Game', 'Art', 'Models')
RAW = os.path.join(ART, 'renders', 'raw', 'keyart')
os.makedirs(RAW, exist_ok=True)
V = Vector
LCLAMP = float(args.get('lclamp', 1.0))
BANDS = [] if args.get('bands') == '0' else [tuple(float(v) for v in b.split(':')) for b in args.get('bands', '0.05:0.22;0.22:0.55;0.55:1.0;0.95:1.25').split(';')]


def fargs(key, default):
    return tuple(float(v) for v in args.get(key, default).split(','))


def B(x, z, y):
    """Unity (x, z, y-up) -> Blender"""
    return V((-x, -z, y))


# ------------------------------------------------------------------ FBX characters / props
def import_fbx(name, anim=True):
    before = set(bpy.data.objects)
    a0 = set(bpy.data.actions)
    vl = bpy.context.view_layer
    vl.active_layer_collection = vl.layer_collection
    bpy.ops.import_scene.fbx(filepath=os.path.join(MODELS, name + '.fbx'), use_anim=anim, automatic_bone_orientation=False,
                             ignore_leaf_bones=False)
    new = [o for o in bpy.data.objects if o not in before]
    root = next(o for o in new if o.parent is None)
    acts = {a.name.split('|')[-1]: a for a in bpy.data.actions if a not in a0}
    for o in new:
        if o.type == 'MESH':
            for i, m in enumerate(o.data.materials):
                if m is None:
                    continue
                base = m.name.split('.')[0]
                if base in L.MATS:
                    o.data.materials[i] = L.get_mat(base)
        if o.name == 'Mark' or o.name.startswith('Mark.'):
            o.hide_render = True
    return root, new, acts


def pose(root, acts, clip, frame):
    root.animation_data_create()
    if clip is None:
        root.animation_data.action = None
        for pb in root.pose.bones:
            pb.location = (0, 0, 0)
            pb.rotation_quaternion = (1, 0, 0, 0)
        return
    root.animation_data.action = acts[clip]
    try:
        root.animation_data.action_slot = acts[clip].slots[0]
    except Exception:
        pass
    bpy.context.scene.frame_set(int(frame))


def bake_pose(root):
    """freeze the evaluated pose into pose bones so several characters can sit on different frames"""
    dg = bpy.context.evaluated_depsgraph_get()
    ev = root.evaluated_get(dg)
    mats = {pb.name: ev.pose.bones[pb.name].matrix_basis.copy() for pb in root.pose.bones}
    root.animation_data.action = None
    for pb in root.pose.bones:
        pb.matrix_basis = mats[pb.name]


def tweak(arm, spec):
    """extra bone rotations on top of the baked take: 'Bone:axis:deg;...' (bone rest rotations are all 0, X = nod)"""
    for it in spec.split(';'):
        if not it:
            continue
        b, ax, d = it.split(':')
        pb = arm.pose.bones.get(b)
        if pb is None:
            continue
        q = pb.rotation_quaternion.copy()
        from mathutils import Quaternion
        axis = {'x': V((1, 0, 0)), 'y': V((0, 1, 0)), 'z': V((0, 0, 1))}[ax]
        pb.rotation_quaternion = q @ Quaternion(axis, math.radians(float(d)))


def thicken(objs, k):
    for o in objs:
        md = o.modifiers.get('ink') if o.type == 'MESH' else None
        if md:
            md.thickness *= k


def place(root, ux, uz, uy, yaw, size):
    root.location = B(ux, uz, uy)
    root.rotation_euler = (math.radians(90), 0, math.radians(-yaw))
    root['ouat_size'] = size


# ------------------------------------------------------------------ look
def light_toon(amb=(0.30, 0.31, 0.34), k=0.95, drain=0.0, keep=()):
    """toon colour * (ambient + k * received light): warm in the shaft, cool and dim elsewhere (render_chars_v2 / dim_toon idea)"""
    for m in bpy.data.materials:
        if m.name not in L.MATS or not m.use_nodes:
            continue
        if L.MATS[m.name][3] not in ('paper', 'painted'):
            continue
        nt = m.node_tree
        s2r = next((n for n in nt.nodes if n.bl_idname == 'ShaderNodeShaderToRGB'), None)
        em = next((n for n in nt.nodes if n.bl_idname == 'ShaderNodeEmission'), None)
        if s2r is None or em is None or not em.inputs['Color'].links:
            continue
        src = em.inputs['Color'].links[0].from_socket
        if drain > 0 and not (L.MATS[m.name][4].get('keep') or any(kk in m.name for kk in keep)):
            hsv = nt.nodes.new('ShaderNodeHueSaturation')
            hsv.inputs['Saturation'].default_value = 1.0 - drain
            nt.links.new(src, hsv.inputs['Color'])
            src = hsv.outputs['Color']
        cl = nt.nodes.new('ShaderNodeVectorMath'); cl.operation = 'MINIMUM'
        nt.links.new(s2r.outputs['Color'], cl.inputs[0])
        cl.inputs[1].default_value = (LCLAMP, LCLAMP, LCLAMP)
        lgt = cl.outputs[0]
        if BANDS:
            # toon-quantise the received light (keeps its colour): light = tint * band(luminance)
            bw = nt.nodes.new('ShaderNodeRGBToBW')
            nt.links.new(cl.outputs[0], bw.inputs[0])
            rp = nt.nodes.new('ShaderNodeValToRGB')
            rp.color_ramp.interpolation = 'CONSTANT'
            el = rp.color_ramp.elements
            el[0].position = 0.0; el[0].color = (0, 0, 0, 1)
            el[1].position = BANDS[0][0]; el[1].color = (BANDS[0][1],) * 3 + (1,)
            for pos, val in BANDS[1:]:
                e = el.new(pos); e.color = (val, val, val, 1)
            nt.links.new(bw.outputs[0], rp.inputs['Fac'])
            mx = nt.nodes.new('ShaderNodeMath'); mx.operation = 'MAXIMUM'; mx.inputs[1].default_value = 0.02
            nt.links.new(bw.outputs[0], mx.inputs[0])
            dv = nt.nodes.new('ShaderNodeVectorMath'); dv.operation = 'DIVIDE'
            nt.links.new(cl.outputs[0], dv.inputs[0]); nt.links.new(mx.outputs[0], dv.inputs[1])
            mn = nt.nodes.new('ShaderNodeVectorMath'); mn.operation = 'MINIMUM'; mn.inputs[1].default_value = (1.6, 1.6, 1.6)
            nt.links.new(dv.outputs[0], mn.inputs[0])
            sc_ = nt.nodes.new('ShaderNodeVectorMath'); sc_.operation = 'MULTIPLY'
            nt.links.new(mn.outputs[0], sc_.inputs[0]); nt.links.new(rp.outputs['Color'], sc_.inputs[1])
            lgt = sc_.outputs[0]
        vm = nt.nodes.new('ShaderNodeVectorMath'); vm.operation = 'MULTIPLY_ADD'
        nt.links.new(lgt, vm.inputs[0])
        vm.inputs[1].default_value = (k, k, k)
        vm.inputs[2].default_value = amb
        mul = nt.nodes.new('ShaderNodeMix'); mul.data_type = 'RGBA'; mul.blend_type = 'MULTIPLY'
        mul.inputs['Factor'].default_value = 1.0
        nt.links.new(src, mul.inputs[6]); nt.links.new(vm.outputs[0], mul.inputs[7])
        nt.links.new(mul.outputs[2], em.inputs['Color'])


def flat_mat(name, rgb, strength=1.0, alpha=1.0):
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    nt = m.node_tree
    nt.nodes.clear()
    out = nt.nodes.new('ShaderNodeOutputMaterial')
    em = nt.nodes.new('ShaderNodeEmission')
    em.inputs['Color'].default_value = (*rgb, 1)
    em.inputs['Strength'].default_value = strength
    if alpha < 1.0:
        tr = nt.nodes.new('ShaderNodeBsdfTransparent')
        mx = nt.nodes.new('ShaderNodeMixShader')
        mx.inputs['Fac'].default_value = alpha
        nt.links.new(tr.outputs[0], mx.inputs[1]); nt.links.new(em.outputs[0], mx.inputs[2])
        nt.links.new(mx.outputs[0], out.inputs['Surface'])
        try:
            m.surface_render_method = 'BLENDED'
        except Exception:
            m.blend_method = 'BLEND'
    else:
        nt.links.new(em.outputs[0], out.inputs['Surface'])
    return m


def pond_mat():
    """black ink: flat black + a faint warm sheen toward the far edge (reflected shaft), unlit"""
    m = bpy.data.materials.new('K_PondInk')
    m.use_nodes = True
    nt = m.node_tree
    nt.nodes.clear()
    out = nt.nodes.new('ShaderNodeOutputMaterial')
    em = nt.nodes.new('ShaderNodeEmission')
    lw = nt.nodes.new('ShaderNodeLayerWeight')
    lw.inputs['Blend'].default_value = 0.85
    mr = nt.nodes.new('ShaderNodeMapRange')
    mr.inputs['From Min'].default_value = 0.55
    mr.inputs['From Max'].default_value = 1.0
    mx = nt.nodes.new('ShaderNodeMix'); mx.data_type = 'RGBA'
    mx.inputs[6].default_value = (*L.hex2rgb('050607'), 1)
    mx.inputs[7].default_value = (*L.hex2rgb(args.get('sheen', '2A2724')), 1)
    nt.links.new(lw.outputs['Fresnel'], mr.inputs['Value'])
    nt.links.new(mr.outputs[0], mx.inputs['Factor'])
    nt.links.new(mx.outputs[2], em.inputs['Color'])
    nt.links.new(em.outputs[0], out.inputs['Surface'])
    return m


def beam_mat():
    """illustrated light shaft: warm unlit glow, densest in the core, soft edges, fading toward the hole"""
    m = bpy.data.materials.new('K_BeamMat')
    m.use_nodes = True
    nt = m.node_tree
    nt.nodes.clear()
    out = nt.nodes.new('ShaderNodeOutputMaterial')
    em = nt.nodes.new('ShaderNodeEmission')
    em.inputs['Color'].default_value = (*L.hex2rgb(args.get('beam_col', 'FFE6B8')), 1)
    em.inputs['Strength'].default_value = 1.0
    tr = nt.nodes.new('ShaderNodeBsdfTransparent')
    add = nt.nodes.new('ShaderNodeAddShader')
    lw = nt.nodes.new('ShaderNodeLayerWeight')
    lw.inputs['Blend'].default_value = 0.5
    inv = nt.nodes.new('ShaderNodeMath'); inv.operation = 'SUBTRACT'; inv.inputs[0].default_value = 1.0
    nt.links.new(lw.outputs['Facing'], inv.inputs[1])
    pw = nt.nodes.new('ShaderNodeMath'); pw.operation = 'POWER'; pw.inputs[1].default_value = float(args.get('beam_p', 2.2))
    nt.links.new(inv.outputs[0], pw.inputs[0])
    tc = nt.nodes.new('ShaderNodeTexCoord')
    sx = nt.nodes.new('ShaderNodeSeparateXYZ')
    nt.links.new(tc.outputs['Generated'], sx.inputs[0])
    mr = nt.nodes.new('ShaderNodeMapRange')
    mr.inputs['From Min'].default_value = 0.0; mr.inputs['From Max'].default_value = 1.0
    mr.inputs['To Min'].default_value = float(args.get('beam_bot', 0.55)); mr.inputs['To Max'].default_value = float(args.get('beam_topk', 1.0))
    nt.links.new(sx.outputs['Z'], mr.inputs['Value'])
    mul = nt.nodes.new('ShaderNodeMath'); mul.operation = 'MULTIPLY'
    nt.links.new(pw.outputs[0], mul.inputs[0]); nt.links.new(mr.outputs[0], mul.inputs[1])
    k = nt.nodes.new('ShaderNodeMath'); k.operation = 'MULTIPLY'; k.inputs[1].default_value = float(args.get('beam_a', 0.22))
    nt.links.new(mul.outputs[0], k.inputs[0])
    # additive: transparent + emission scaled by the alpha mask
    nt.links.new(k.outputs[0], em.inputs['Strength'])
    nt.links.new(tr.outputs[0], add.inputs[0]); nt.links.new(em.outputs[0], add.inputs[1])
    nt.links.new(add.outputs[0], out.inputs['Surface'])
    try:
        m.surface_render_method = 'BLENDED'
    except Exception:
        m.blend_method = 'BLEND'
    m.use_backface_culling = False
    return m


def mesh_obj(name, verts, faces, mat):
    me = bpy.data.meshes.new(name)
    me.from_pydata(verts, [], faces)
    me.materials.append(mat)
    ob = bpy.data.objects.new(name, me)
    bpy.context.scene.collection.objects.link(ob)
    return ob


def disc(name, c, r, z, mat, n=72, wob=0.0, seed=1, sq=1.0, rot=0.0):
    import random
    rnd = random.Random(seed)
    ph = [rnd.uniform(0, 6.28) for _ in range(4)]
    vs = [(c[0], c[1], z)]
    for i in range(n):
        a = 2 * math.pi * i / n
        rr = r * (1 + wob * (0.5 * math.sin(3 * a + ph[0]) + 0.3 * math.sin(5 * a + ph[1]) + 0.2 * math.sin(9 * a + ph[2])))
        x, y = math.cos(a) * rr, math.sin(a) * rr * sq
        cs, sn = math.cos(rot), math.sin(rot)
        vs.append((c[0] + x * cs - y * sn, c[1] + x * sn + y * cs, z))
    fs = [(0, 1 + i, 1 + (i + 1) % n) for i in range(n)]
    return mesh_obj(name, vs, fs, mat)


def ring(name, c, r, w, z, mat, n=96, sq=1.0, rot=0.0, gap=0.0, seed=0):
    import random
    rnd = random.Random(seed)
    vs, fs = [], []
    a0 = rnd.uniform(0, 6.28)
    span = 2 * math.pi * (1 - gap)
    for i in range(n + 1):
        a = a0 + span * i / n
        ww = w * (0.35 + 0.65 * math.sin(math.pi * i / n)) if gap > 0 else w
        for rr in (r - ww / 2, r + ww / 2):
            x, y = math.cos(a) * rr, math.sin(a) * rr * sq
            cs, sn = math.cos(rot), math.sin(rot)
            vs.append((c[0] + x * cs - y * sn, c[1] + x * sn + y * cs, z))
    for i in range(n):
        fs.append((2 * i, 2 * i + 1, 2 * i + 3, 2 * i + 2))
    return mesh_obj(name, vs, fs, mat)


def camera(pos, look, fov_v):
    c = R.add_camera(tuple(pos), tuple(look), lens=50)
    c.data.sensor_fit = 'VERTICAL'
    c.data.angle_y = math.radians(fov_v)
    c.data.clip_start = 0.05
    c.data.clip_end = 600
    return c


def world(amb, amb_col, bg_col):
    w = bpy.context.scene.world
    nt = w.node_tree
    nt.nodes.clear()
    out = nt.nodes.new('ShaderNodeOutputWorld')
    b1 = nt.nodes.new('ShaderNodeBackground'); b1.inputs['Color'].default_value = (*amb_col, 1); b1.inputs['Strength'].default_value = amb
    b2 = nt.nodes.new('ShaderNodeBackground'); b2.inputs['Color'].default_value = (*bg_col, 1); b2.inputs['Strength'].default_value = 1.0
    lp = nt.nodes.new('ShaderNodeLightPath')
    mx = nt.nodes.new('ShaderNodeMixShader')
    nt.links.new(lp.outputs['Is Camera Ray'], mx.inputs['Fac'])
    nt.links.new(b1.outputs[0], mx.inputs[1]); nt.links.new(b2.outputs[0], mx.inputs[2])
    nt.links.new(mx.outputs[0], out.inputs['Surface'])


def sun_dir(dir_b, strength, color, angle=3):
    ld = bpy.data.lights.new('Key', 'SUN')
    ld.energy = strength
    ld.color = color
    ld.angle = math.radians(angle)
    ob = bpy.data.objects.new('Key', ld)
    bpy.context.scene.collection.objects.link(ob)
    ob.rotation_euler = V(dir_b).normalized().to_track_quat('-Z', 'Y').to_euler()
    return ob


def save_meta(path, cam, pts):
    json.dump({k: R.project(cam, [v])[0] for k, v in pts.items()}, open(path[:-4] + '.json', 'w', encoding='utf-8'), indent=1)


# ================================================================== TITLE
def shot_title():
    import render_previews as RP
    import ouat_slice as SL
    import ouat_areas as AR
    old = bpy.data.collections.get('Level_Ch1')
    if old:
        for o in list(old.objects):
            bpy.data.objects.remove(o, do_unlink=True)
        bpy.data.collections.remove(old)
    # only a_fall is shown: skip the slice-2 areas (also keeps this render independent of work-in-progress there)
    import ouat_slice2 as SL2
    SL2.build_slice2 = lambda A: None
    LV_ASSET = AR.build_level_areas()
    LEVEL, COLL = LV_ASSET.root, LV_ASSET.coll
    bpy.context.view_layer.update()

    def bare(o):
        return o.name.split('|', 1)[-1].split('#')[0]

    colliders = [o for o in COLL.objects if o.type == 'MESH' and (bare(o).startswith('Ground_Walk') or bare(o).startswith('Cliffs'))]

    def ground(x, z):
        best = None
        org_w = B(x, z, 50.0)
        for o in colliders:
            mi = o.matrix_world.inverted()
            hit, loc, nrm, idx = o.ray_cast(mi @ org_w, (mi.to_3x3() @ V((0, 0, -1))).normalized(), distance=100.0)
            if hit:
                w = o.matrix_world @ loc
                best = w.z if best is None else max(best, w.z)
        return 0.0 if best is None else best

    for ch in LEVEL.children:
        nm = bare(ch)
        if nm.startswith('Area_') and nm != 'Area_a_fall':
            for o in [ch] + list(ch.children_recursive):
                o.hide_render = True
    used = {'Level_Ch1'}

    def put(name, x, z, yaw=0.0, scale=1.0, lift=0.0):
        r = RP.dup(name)
        used.add(name)
        r.location = B(x, z, ground(x, z) + lift)
        r.rotation_euler = (0, 0, math.radians(-yaw))
        r.scale = (scale,) * 3
        return r

    if 'hgrid' in args:
        for zz in range(36, 22, -1):
            print('HG', zz, ' '.join(f'{ground(xx * 0.5, zz):4.1f}' for xx in range(-126, -100)))
        print('HGX', ' '.join(f'{xx * 0.5:5.1f}' for xx in range(-126, -100)))
        return
    P = SL.FALL_PTS
    put('ItemPile', *P['fall_pile'], 20, 1.8)
    for (m, x, z, yaw, s) in SL.FALL_JUNK:
        put(m, x, z, yaw, s)
    for pid, m in (('look_book', 'Junk_Book'), ('look_umbrella', 'Junk_Umbrella'), ('look_clock', 'Junk_Clock')):
        put(m, *P[pid], SL.FALL_FACING[pid], 1.25)
    # more fallen human things on and around the heap (colour = human objects)
    pile_objs = [o for o in bpy.data.objects if o.name.startswith('ItemPile') and o.type == 'MESH']

    def pile_h(x, z):
        best = ground(x, z)
        org_w = B(x, z, 50.0)
        for o in pile_objs:
            mi = o.matrix_world.inverted()
            hit, loc, nrm, idx = o.ray_cast(mi @ org_w, (mi.to_3x3() @ V((0, 0, -1))).normalized(), distance=100.0)
            if hit:
                best = max(best, (o.matrix_world @ loc).z)
        return best
    bpy.context.view_layer.update()
    import random
    rnd = random.Random(int(args.get('junk_seed', 11)))
    kinds = ['Junk_Book', 'Junk_Book', 'Junk_Book', 'Junk_Shoe', 'Junk_Teacup', 'Junk_Clock', 'Junk_Lantern', 'Junk_Umbrella']
    for i in range(int(args.get('junk_n', 16))):
        a = rnd.uniform(0, 6.283)
        r = rnd.uniform(0.4, 2.3)
        x, z = SL.HEAP.x + math.cos(a) * r, SL.HEAP.y + math.sin(a) * r
        if (V((x, z)) - V(fargs('hero', '-54.15,28.75,235')[:2])).length < 0.8:
            continue
        m = rnd.choice(kinds)
        o = RP.dup(m)
        used.add(m)
        o.location = B(x, z, pile_h(x, z) - 0.03)
        o.rotation_euler = (math.radians(rnd.uniform(-25, 25)), math.radians(rnd.uniform(-25, 25)), rnd.uniform(0, 6.283))
        o.scale = (rnd.uniform(1.0, 1.35),) * 3
    RP.hide_all_but(used)

    # ---- characters (exported FBX, posed from takes)
    hx, hz, hyaw = fargs('hero', '-54.15,28.75,235')
    hy = ground(hx, hz)
    hero, hero_objs, hacts = import_fbx('Hero_Bluebird')
    pose(hero, hacts, args.get('hclip', 'Idle'), float(args.get('hframe', 30)))
    bake_pose(hero)
    tweak(hero, args.get('hbones', ''))
    place(hero, hx, hz, hy, hyaw, 1.0)
    bpy.context.view_layer.update()
    kid, kid_objs, kacts = import_fbx('Kinopio')
    pose(kid, kacts, args.get('kclip', 'TugSleeve'), float(args.get('kframe', 12)))
    bake_pose(kid)
    tweak(kid, args.get('kbones', ''))
    if 'kid' in args:
        kx, kz, kyaw = fargs('kid', '')
    else:
        # stand Kinopio so his TugSleeve grip (root-local Unity (0.07, 0.57, 0.15)) lands on the hero's wrist
        side = args.get('kside', 'R')
        hb = hero.pose.bones['Hand' + side]
        wb = hero.matrix_world @ hb.head
        wu = V((-wb.x, -wb.y))                     # Blender -> Unity x,z
        kyaw = hyaw + float(args.get('kturn', -55 if side == 'R' else 55))
        a = math.radians(kyaw)
        fwd_u, right_u = V((math.sin(a), math.cos(a))), V((math.cos(a), -math.sin(a)))
        kp = wu - right_u * (0.07 if side == 'R' else -0.07) - fwd_u * float(args.get('kreach', 0.15))
        kx, kz = kp.x, kp.y
        print('WRIST', tuple(round(c, 3) for c in wb), 'from hero', round((wb.xy - hero.location.xy).length, 3), 'KID', round(kx, 2), round(kz, 2), round(kyaw, 1))
    place(kid, kx, kz, ground(kx, kz), kyaw, 0.8)
    # red cord knot on the cape: parent to the Body bone at the brass clasp
    cord, cord_objs, _ = import_fbx('RedCord', anim=False)
    bpy.context.view_layer.update()
    geo = next(o for o in hero_objs if o.type == 'MESH')
    dg = bpy.context.evaluated_depsgraph_get()
    ev = geo.evaluated_get(dg)
    me = ev.to_mesh()
    bi = [i for i, m in enumerate(geo.data.materials) if m and m.name.startswith('M_Brass')]
    pts = [geo.matrix_world @ me.vertices[v].co for p in me.polygons if p.material_index in bi for v in p.vertices]
    ev.to_mesh_clear()
    neck = [p for p in pts if hy + 0.78 < p.z < hy + 1.02]       # the cape clasp, not the cap buttons
    top = max(neck, key=lambda p: p.z)
    clasp = [p for p in neck if p.z > top.z - 0.05]
    cpos = sum(clasp, V()) / len(clasp)
    fwd = V((-math.sin(math.radians(hyaw)), -math.cos(math.radians(hyaw)), 0))
    cord['ouat_size'] = 0.35
    cord.location = cpos + fwd * float(args.get('cord_fwd', 0.07)) + V((0, 0, float(args.get('cord_dz', -0.03))))
    cord.rotation_euler = (math.radians(90), 0, math.radians(-hyaw))
    cord.scale = (float(args.get('cord_s', 1.4)),) * 3
    print('CLASP', tuple(round(c, 3) for c in cpos))

    # ---- the ink pond in the foreground with the fish beneath
    if 'patch' in args:
        # foreground lip: lift the mid tier in front of the camera to the hilltop height (one continuous ground with the pond)
        x0, x1, z0, z1 = fargs('patch', '-62.5,-58.3,26.5,32.4') if ',' in args['patch'] else (-62.5, -58.3, 26.5, 32.4)
        py_ = SL.H + 0.005
        mesh_obj('K_Patch', [tuple(B(x0, z0, py_)), tuple(B(x1, z0, py_)), tuple(B(x1, z1, py_)), tuple(B(x0, z1, py_))], [(0, 1, 2, 3)],
                 L.get_mat('M_UnderGround'))
        colliders.append(bpy.data.objects['K_Patch'])
    px, pz, py = fargs('pond', '-60.2,25.2,0')
    pr = float(args.get('pond_r', 2.4))
    pond_y = ground(px, pz) + 0.015 + py
    ink = pond_mat()
    pc = B(px, pz, pond_y)
    disc('K_Pond', pc[:2], pr, pond_y, ink, wob=0.12, seed=4, sq=0.78, rot=0.5)
    rim = flat_mat('K_PondRim', L.hex2rgb('2B2622'))
    ring('K_PondRim', pc[:2], pr * 1.0, 0.05, pond_y + 0.003, rim, sq=0.78, rot=0.5, n=120)
    sheen = flat_mat('K_Ripple', L.hex2rgb(args.get('rip_col', '8C8778')), 1.0, alpha=float(args.get('rip_a', 0.7)))
    rc = B(px + float(args.get('rip_dx', 0.25)), pz + float(args.get('rip_dz', 0.35)), 0)
    for i, (rf, w, g) in enumerate(((0.22, 0.016, 0.45), (0.42, 0.013, 0.62), (0.66, 0.01, 0.78))):
        ring(f'K_Rip{i}', rc[:2], pr * rf, w, pond_y + 0.006, sheen, sq=0.78, rot=0.5, gap=g, seed=i + 3)
    # hollow under the pond so the fish has somewhere to be
    well = flat_mat('K_Well', L.hex2rgb('020203'))
    disc('K_WellFloor', B(px, pz, 0)[:2], pr * 3, pond_y - 9.0, well, sq=1.0)
    fish, fish_objs, facts = import_fbx('Fish')
    fyaw = float(args.get('fish_yaw', 240))
    pose(fish, facts, args.get('fclip', 'Hidden'), float(args.get('fframe', 0)))
    bake_pose(fish)
    place(fish, px, pz, 0.0, fyaw, 12.0)
    fs = float(args.get('fish_scale', 1.0))
    fish.scale = (fs,) * 3
    bpy.context.view_layer.update()
    # put the fish's pale eye just under the ink, centred in the pond (offset fish_off = dx,dz in Unity metres)
    fgeo = next(o for o in fish_objs if o.type == 'MESH')
    ev = fgeo.evaluated_get(bpy.context.evaluated_depsgraph_get())
    me = ev.to_mesh()
    ei = [i for i, m in enumerate(fgeo.data.materials) if m and m.name.startswith('M_FishEye')]
    eye = [fgeo.matrix_world @ me.vertices[v].co for p_ in me.polygons if p_.material_index in ei for v in p_.vertices]
    ev.to_mesh_clear()
    ec = sum(eye, V()) / max(1, len(eye))
    dx, dz = fargs('fish_off', '0,0')
    tgt = B(px + dx, pz + dz, pond_y - float(args.get('fish_depth', 0.6)))
    fish.location += tgt - ec
    print('FISH_EYE', tuple(round(c, 2) for c in ec), '->', tuple(round(c, 2) for c in tgt))

    # ---- render setup
    L.MATS['M_Ceiling'] = (args.get('ceil', '4A4F57'), '3E434B', False, 'line', {})
    pool = L.MATS['M_LightPool']
    L.MATS['M_LightPool'] = (pool[0], pool[1], pool[2], pool[3], dict(pool[4], alpha=float(args.get('pool_a', 0.2))))
    for o in COLL.objects:
        if bare(o).startswith('Light_fall') and 'dust' not in args:
            pass
    R.setup_render(res=RES, samples=SAMPLES)
    R.prepare_all(outline_scale=float(args.get('ol', 0.55)), hatch_scale=float(args.get('hatch', 420)))
    thicken(hero_objs + kid_objs + cord_objs, float(args.get('col', 1.8)))
    for o in COLL.objects:
        nm = bare(o)
        if nm.startswith('Ground_Lines') or nm.startswith('Light_') or nm.startswith('Vista') or nm in ('Ceiling', 'Backdrop'):
            o.visible_shadow = False
    for o in fish_objs:
        o.visible_shadow = False
    # volumetric shaft instead of the flat beam card (the card reads as a grey slab at this distance)
    if 'cardbeam' not in args:
        mb = bpy.data.materials.get('M_Beam')
        if mb:
            nt = mb.node_tree; nt.nodes.clear()
            nt.links.new(nt.nodes.new('ShaderNodeBsdfTransparent').outputs[0], nt.nodes.new('ShaderNodeOutputMaterial').inputs['Surface'])
        h = SL.HEAP
        shx, shz = fargs('shaft_at', f'{h.x},{h.y}')
        top_y = float(args.get('beam_top', 26.0))
        bpy.ops.mesh.primitive_cone_add(vertices=64, radius1=float(args.get('vol_r', 2.2)), radius2=float(args.get('vol_r2', 1.3)),
                                        depth=top_y - SL.H, location=tuple(B(shx, shz, (SL.H + top_y) / 2)), end_fill_type='NOTHING')
        vol = bpy.context.active_object
        vol.name = 'K_Beam'
        for pl in vol.data.polygons:
            pl.use_smooth = True
        vol.data.materials.append(beam_mat())
        vol.visible_shadow = False
        if 'volbeam' in args:
            vm = bpy.data.materials.new('K_Vol')
            vm.use_nodes = True
            nt = vm.node_tree; nt.nodes.clear()
            pv = nt.nodes.new('ShaderNodeVolumePrincipled')
            pv.inputs['Density'].default_value = float(args.get('vol', 0.05))
            nt.links.new(pv.outputs[0], nt.nodes.new('ShaderNodeOutputMaterial').inputs['Volume'])
            vol.data.materials.append(vm)
    nspk = int(args.get('specks', 140))
    if nspk:
        # tiny paper flecks drifting in the shaft (the level's square dust cards read too big this close)
        import random
        rnd = random.Random(5)
        h = SL.HEAP
        shx, shz = fargs('shaft_at', f'{h.x},{h.y}')
        spm = flat_mat('K_Speck', L.hex2rgb('FFF0D0'), float(args.get('speck_s', 1.6)))
        vs, fs = [], []
        for i in range(nspk):
            yy = SL.H + 0.3 + rnd.random() ** 0.7 * 9.0
            rr = (float(args.get('vol_r', 1.7)) * 0.95) * math.sqrt(rnd.random())
            a = rnd.uniform(0, 6.283)
            c = B(shx + math.cos(a) * rr, shz + math.sin(a) * rr, yy)
            sz = rnd.uniform(0.003, 0.011)
            b0 = len(vs)
            vs += [tuple(c + V((-sz, 0, -sz))), tuple(c + V((sz, 0, -sz))), tuple(c + V((sz, 0, sz))), tuple(c + V((-sz, 0, sz))),
                   tuple(c + V((0, -sz, -sz))), tuple(c + V((0, sz, -sz))), tuple(c + V((0, sz, sz))), tuple(c + V((0, -sz, sz)))]
            fs += [(b0, b0 + 1, b0 + 2, b0 + 3), (b0 + 4, b0 + 5, b0 + 6, b0 + 7)]
        sp = mesh_obj('K_Specks', vs, fs, spm)
        sp.visible_shadow = False
    if 'dust' not in args:
        md = bpy.data.materials.get('M_Dust')
        if md:
            nt = md.node_tree; nt.nodes.clear()
            nt.links.new(nt.nodes.new('ShaderNodeBsdfTransparent').outputs[0], nt.nodes.new('ShaderNodeOutputMaterial').inputs['Surface'])
    light_toon(amb=fargs('amb3', '0.22,0.235,0.27'), k=float(args.get('k', 1.0)))
    world(float(args.get('amb', 0.25)), L.hex2rgb('8E96A3'), L.hex2rgb(args.get('bg', '3E434B')))
    if 'cardbeam' not in args:
        wn = bpy.context.scene.world.node_tree
        wv = wn.nodes.new('ShaderNodeVolumePrincipled')
        wv.inputs['Density'].default_value = float(args.get('haze', 0.006))
        wv.inputs['Color'].default_value = (*L.hex2rgb('8E96A3'), 1)
        wo = next(n for n in wn.nodes if n.bl_idname == 'ShaderNodeOutputWorld')
        wn.links.new(wv.outputs[0], wo.inputs['Volume'])
    lp = bpy.data.materials.get('M_LightPool')
    sun_dir(B(-0.33, 0.47, -0.82), float(args.get('sun', 0.55)), L.hex2rgb('B9C3D2'))
    h = SL.HEAP
    shx, shz = fargs('shaft_at', f'{h.x},{h.y}')
    R.add_spot(tuple(B(shx, shz, 30.0)), tuple(B(shx, shz, SL.H)), energy=float(args.get('shaft', 90000)), size_deg=float(args.get('cone', 17)), blend=float(args.get('cblend', 0.35)),
               color=L.hex2rgb('FFE2B0'), radius=1.0, name='Shaft')
    # rim from the shaft side on the pair
    R.add_spot(tuple(B(hx + 1.2, hz + 2.5, hy + 6.0)), tuple(B(hx, hz, hy + 0.8)), energy=float(args.get('rim', 900)), size_deg=14, blend=0.5,
               color=L.hex2rgb('FFD9A0'), radius=0.3, name='Rim')
    cx_, cz_, cy_ = fargs('cam', '-61.6,27.1,6.05')
    R.add_point(tuple(B(cx_ + 0.6, cz_ - 0.8, cy_ + 1.2)), energy=float(args.get('fill', 60)), color=L.hex2rgb('A9B8D0'), radius=1.5, name='Fill')
    for (x, z, y, e) in ((-1.0, 18.5, 3.5, 2500), (-12.0, 6.0, 2.7, 500), (-6.0, 12.0, 2.7, 500), (-20.0, 24.0, 3.0, 400)):
        R.add_point(tuple(B(x, z, y)), energy=e, color=L.hex2rgb('FFC27A'), radius=0.4, name='TownGlow')
    cx, cz, cy = fargs('cam', '-61.6,27.1,6.05')
    lx, lz, ly = fargs('look', '-50.0,28.6,7.4')
    for ob in bpy.data.objects:
        if ob.type == 'LIGHT':
            ob.data.volume_factor = {'Shaft': float(args.get('shaft_vol', 1.0)), 'Key': float(args.get('sun_vol', 0.4))}.get(ob.name.split('.')[0], 0.0)
    cam = camera(B(cx, cz, cy), B(lx, lz, ly), float(args.get('fov', 38)))
    trim = float(args.get('trim', 5.0))
    if trim > 0:
        import bmesh
        cxy = B(cx, cz, 0).xy
        for o in COLL.objects:
            nm = bare(o)
            if o.type != 'MESH' or not (nm.startswith('Ground_Lines') or nm.startswith('Cliffs') or nm.startswith('Margin')):
                continue
            inkset = {i for i, m in enumerate(o.data.materials) if m and m.name.split('.')[0] in ('M_Ink', 'M_HatchDark', 'M_SketchLine', 'M_Smudge', 'M_UnderRoad')}
            bm = bmesh.new(); bm.from_mesh(o.data)
            mw = o.matrix_world
            kill = [f for f in bm.faces if f.material_index in inkset and ((mw @ f.calc_center_median()).xy - cxy).length < trim]
            bmesh.ops.delete(bm, geom=kill, context='FACES')
            bm.to_mesh(o.data); bm.free()
            print('TRIM', nm, len(kill))
    if 'calm' in args:
        # keep the title corner calm: drop thin ink / pencil strokes that land in it (screen x < cx, y < cy)
        import bmesh
        from bpy_extras.object_utils import world_to_camera_view
        qx, qy = fargs('calm', '0.55,0.3')
        bpy.context.view_layer.update()
        for o in COLL.objects:
            if o.type != 'MESH':
                continue
            lineset = {i for i, m in enumerate(o.data.materials) if m and L.MATS.get(m.name.split('.')[0], (0, 0, 0, ''))[3] in ('line', 'sketch')
                       and m.name.split('.')[0] not in ('M_Ceiling',)}
            if not lineset:
                continue
            bm = bmesh.new(); bm.from_mesh(o.data)
            mw = o.matrix_world
            kill = []
            for f in bm.faces:
                if f.material_index not in lineset:
                    continue
                for v in f.verts:
                    co = world_to_camera_view(bpy.context.scene, cam, mw @ v.co)
                    if co.z > 0 and co.x < qx and (1 - co.y) < qy:
                        kill.append(f)
                        break
            if kill:
                bmesh.ops.delete(bm, geom=kill, context='FACES')
                bm.to_mesh(o.data)
                print('CALM', bare(o), len(kill))
            bm.free()
    if 'top' in args:
        tx, tz = fargs('top', '-55,28')
        cam = R.add_camera(tuple(B(tx, tz, 60)), tuple(B(tx, tz + 0.001, 0)), lens=50, ortho=float(args.get('ortho', 30)))
        cam.rotation_euler = (0, 0, math.radians(180))
        for o in COLL.objects:
            if bare(o) in ('Ceiling', 'Backdrop'):
                o.hide_render = True
    bpy.context.view_layer.update()
    out = os.path.join(RAW, f'title{TAG}.png')
    for o in fish_objs:
        o.hide_render = True
    R.render(out)
    if 'nofish' not in args:
        # fish pass (seen only through the ink, composited by finish_keyart.py) + pond mask
        vis = {o: o.hide_render for o in bpy.data.objects}
        for o in bpy.data.objects:
            if o.type in ('MESH', 'CURVE'):
                o.hide_render = o not in fish_objs
        sc = bpy.context.scene
        sc.render.film_transparent = True
        sc.render.image_settings.color_mode = 'RGBA'
        # flat shape pass: body = one dark teal, the pale eye and the fangs lighter, pencil/paper insides gone
        body = flat_mat('K_FishBody', L.hex2rgb(args.get('fish_col', '1C3236')))
        eyem = flat_mat('K_FishEye', L.hex2rgb('C9CDBF'))
        tooth = flat_mat('K_FishTooth', L.hex2rgb('7E8780'))
        gone = flat_mat('K_FishGone', (0, 0, 0), 0.0, alpha=0.0)
        for o in fish_objs:
            if o.type != 'MESH':
                continue
            for md in list(o.modifiers):
                if md.name == 'ink':
                    o.modifiers.remove(md)
            for i, m in enumerate(o.data.materials):
                nm = m.name.split('.')[0] if m else ''
                o.data.materials[i] = (eyem if nm.startswith('M_FishEye') else tooth if nm == 'M_FishTooth'
                                       else gone if nm in ('M_Pencil', 'M_Ink', 'M_FishScratch', 'K_OutlineInk', 'R_OutlineInk') else body)
        R.render(out[:-4] + '_fish.png')
        for o in bpy.data.objects:
            if o.type == 'MESH':
                o.hide_render = not o.name.startswith('K_Pond')
        wm = flat_mat('K_White', (1, 1, 1))
        for o in bpy.data.objects:
            if o.name.startswith('K_Pond') and not o.name.startswith('K_PondRim'):
                o.data.materials[0] = wm
                o.modifiers.clear()
        R.render(out[:-4] + '_mask.png')
    save_meta(out, cam, {'hero_head': B(hx, hz, hy + 1.15), 'hero_feet': B(hx, hz, hy), 'kid': B(kx, kz, ground(kx, kz) + 0.5),
                         'pond': B(px, pz, pond_y), 'heap': B(h.x, h.y, SL.H)})
    print('RENDERED', out)


# ================================================================== CHAPTER CARD
def build_offer(name, loc=(0, 0, 0), rz=0.0, scale=1.0, rx=0.0, ry=0.0):
    f = dict(OF.ASSETS)[name]
    A = f()
    A.root.location = V(loc)
    A.root.rotation_euler = (math.radians(rx), math.radians(ry), math.radians(rz))
    A.root.scale = (scale,) * 3
    return A


def shot_card():
    L.reset_scene()
    import ouat_props as PR
    builders = {}
    for mod in (PR, OF):
        for n, f in mod.ASSETS:
            builders[n] = f
    R.setup_render(res=RES, samples=SAMPLES)
    L.MATS.setdefault('K_Ground', ('B9B3A6', '8C8A86', False, 'paper', {'hatch': False}))
    gr = mesh_obj('K_Ground', [(-60, -60, 0), (60, -60, 0), (60, 60, 0), (-60, 60, 0)], [(0, 1, 2, 3)], L.get_mat('K_Ground'))
    bell = builders['Bell']()
    bell.root.location = V((0, 0, 0))
    bell.root.rotation_euler = (0, 0, math.radians(float(args.get('bell_rz', 8))))
    sack = builders['Sack']()
    sx, sy, srz = fargs('sack', '0.15,-0.55,-25')
    sack.root.location = V((sx, sy, 0))
    sack.root.rotation_euler = (0, 0, math.radians(srz))
    ss = float(args.get('sack_s', 0.62))      # child-sized: 1.33 m sack scaled to ~0.82 m
    sack.root.scale = (ss,) * 3
    bpy.context.view_layer.update()
    # cord knot at the sack neck (Mouth pivot)
    mouth = next((o for o in bpy.data.objects if o.name.startswith('Sack|Mouth')), None)
    cord, cord_objs, _ = import_fbx('RedCord', anim=False)
    mp = mouth.matrix_world.translation if mouth else V((sx, sy, 0.7))
    cord.location = mp + V(fargs('cord_off', '-0.02,-0.11,-0.10'))
    cord.rotation_euler = (math.radians(90 + float(args.get('cord_tilt', -10))), 0, math.radians(float(args.get('cord_rz', -10))))
    cord.scale = (float(args.get('cord_s', 1.25)),) * 3
    cord['ouat_size'] = 0.4
    # a few fallen human things half in the dark
    for (n, x, y, rz, s) in ((('Junk_Book', -0.7, -0.75, 30, 1.0)), ('Junk_Shoe', 0.75, -0.45, 120, 1.0), ('Junk_Teacup', -0.25, -1.1, 0, 1.1)):
        if n in builders:
            a = builders[n]()
            a.root.location = V((x, y, 0)); a.root.rotation_euler = (0, 0, math.radians(rz)); a.root.scale = (s,) * 3
    # the village waiting in the dark: talkless silhouettes at the edge of the light
    import random
    rnd = random.Random(3)
    for spec in args.get('crowd', '-2.6,3.6,10,A;-1.0,4.6,-5,B;3.4,3.4,-20,A;4.6,1.6,-40,B;-3.9,1.8,25,B').split(';'):
        if not spec:
            continue
        x, y, rz, k = spec.split(',')
        r, objs, acts = import_fbx('Silhouette_' + k)
        pose(r, acts, 'Idle', rnd.uniform(0, 60))
        bake_pose(r)
        r.location = (float(x), float(y), 0)
        r.rotation_euler = (math.radians(90), 0, math.radians(float(rz)))
        r['ouat_size'] = 1.4
    R.prepare_all(outline_scale=float(args.get('ol', 0.7)), hatch_scale=float(args.get('hatch', 420)))
    gr.modifiers.clear()
    light_toon(amb=fargs('amb3', '0.16,0.17,0.2'), k=float(args.get('k', 1.0)), drain=0.35, keep=('Offer', 'Brass', 'Book', 'Leather'))
    world(float(args.get('amb', 0.2)), L.hex2rgb('8E96A3'), L.hex2rgb(args.get('bg', '1E2126')))
    sun_dir(V((0.5, 0.7, -0.5)), float(args.get('sun', 0.18)), L.hex2rgb('9FB0C8'))
    lx_, ly_, lz_ = fargs('lamp', '0.35,-1.1,7.5')
    tx_, ty_, tz_ = fargs('lamp_at', '0.1,-0.45,0.5')
    R.add_spot((lx_, ly_, lz_), (tx_, ty_, tz_), energy=float(args.get('spot', 5200)), size_deg=float(args.get('cone', 30)), blend=float(args.get('cblend', 0.6)),
               color=L.hex2rgb('FFE2B0'), radius=float(args.get('lrad', 0.25)), name='Single')
    cx, cy, cz = fargs('cam', '2.2,-6.4,1.35')
    lx, ly, lz = fargs('look', '-0.15,0.0,1.55')
    cam = camera((cx, cy, cz), (lx, ly, lz), float(args.get('fov', 34)))
    out = os.path.join(RAW, f'card{TAG}.png')
    R.render(out)
    print('RENDERED', out)


# ================================================================== CHAPTER END
def shot_end():
    L.reset_scene()
    R.setup_render(res=RES, samples=SAMPLES, transparent=False)
    fish, fobjs, facts = import_fbx('Fish')
    pose(fish, facts, args.get('fclip', 'OpenMouth'), float(args.get('fframe', 44)))
    bake_pose(fish)
    tweak(fish, args.get('jaw', 'JawUpper:x:10;JawLower:x:-16'))
    fish.location = (0, 0, 0)
    # the camera sits where the torn-open body / throat would be: drop those inner shells so the jaws can frame the shot
    clear = flat_mat('K_Clear', (0, 0, 0), 0.0, alpha=0.0)
    drop = args.get('drop', 'M_Paper,M_PaperBack,M_TornEdge,M_Silhouette,M_Pencil').split(',')
    for o in fobjs:
        if o.type == 'MESH':
            for i, m in enumerate(o.data.materials):
                if m and m.name.split('.')[0] in drop:
                    o.data.materials[i] = clear
    fish['ouat_size'] = 12.0
    bpy.context.view_layer.update()
    # silhouettes: human child + Kinopio holding hands, out on the bank in front of the mouth
    sil = flat_mat('K_Sil', L.hex2rgb('0E0C0B'))
    hx, hz, hyaw = fargs('hero', '0.25,9.0,180')
    kx, kz, kyaw = fargs('kid', '-0.35,9.05,180')
    hero, hobjs, hacts = import_fbx('Hero_Bluebird')
    def fish_floor(ux, uz):
        """height of the fish's lower jaw / tongue under a point (ray down onto the posed mesh)"""
        if 'onfish' not in args:
            return float(args.get('bank', 0.0))
        geo = next(o for o in fobjs if o.type == 'MESH')
        dg = bpy.context.evaluated_depsgraph_get()
        ev = geo.evaluated_get(dg)
        mi = geo.matrix_world.inverted()
        org = B(ux, uz, float(args.get('ray_from', 2.4)))
        hit, loc, nrm, idx = ev.ray_cast(mi @ org, (mi.to_3x3() @ V((0, 0, -1))).normalized(), distance=30.0)
        z = (geo.matrix_world @ loc).z if hit else 0.0
        print('FLOOR', ux, uz, round(z, 3), hit)
        return z
    pose(hero, hacts, args.get('hclip', 'Idle'), float(args.get('hframe', 10)))
    bake_pose(hero)
    place(hero, hx, hz, fish_floor(hx, hz), hyaw, 1.0)
    kid, kobjs, kacts = import_fbx('Kinopio')
    pose(kid, kacts, args.get('kclip', 'Idle'), float(args.get('kframe', 10)))
    bake_pose(kid)
    place(kid, kx, kz, fish_floor(kx, kz), kyaw, 0.8)
    for o in hobjs + kobjs:
        if o.type == 'MESH':
            for i in range(len(o.data.materials)):
                o.data.materials[i] = sil
    # hand-holding: rotate the hero's right arm down/outward and Kinopio's left arm up towards it
    def rot_bone(arm, bone, axis, deg):
        pb = arm.pose.bones.get(bone)
        if pb:
            pb.rotation_mode = 'XYZ'
            e = pb.rotation_euler
            setattr(e, axis, getattr(e, axis) + math.radians(deg))
    for spec in args.get('hbones', 'ArmR:z:-14').split(';'):
        if spec:
            b, ax, d = spec.split(':'); rot_bone(hero, b, ax, float(d))
    for spec in args.get('kbones', 'ArmL:z:38;ForeArmL:z:10').split(';'):
        if spec:
            b, ax, d = spec.split(':'); rot_bone(kid, b, ax, float(d))
    # light beyond: bright paper ground + a pale sky plane (the far shaft-light of the surface world)
    L.MATS.setdefault('K_Bank', ('E9DFC9', 'B9B3A6', False, 'paper', {'hatch': False}))
    bz = float(args.get('bank', 0.0))
    bank = mesh_obj('K_Bank', [(-600, -900, bz), (600, -900, bz), (600, -4, bz), (-600, -4, bz)], [(0, 1, 2, 3)],
                    flat_mat('K_BankFlat', L.hex2rgb(args.get('bank_col', 'D9CDB2')), 1.0))
    glow = flat_mat('K_Glow', L.hex2rgb(args.get('glow', 'F3E6C8')), float(args.get('glow_s', 1.0)))
    mesh_obj('K_Sky', [(-800, -700, -5), (800, -700, -5), (800, -700, 600), (-800, -700, 600)], [(0, 1, 2, 3)], glow)
    R.prepare_all(outline_scale=float(args.get('ol', 0.5)), hatch_scale=float(args.get('hatch', 380)))
    bank.modifiers.clear()
    if 'cull' not in args:
        for m in bpy.data.materials:
            m.use_backface_culling = False
    for o in fobjs:                       # inverted-hull outline is seen from inside the head: drop it here
        if o.type == 'MESH' and o.modifiers.get('ink'):
            o.modifiers.remove(o.modifiers['ink'])
    light_toon(amb=fargs('amb3', '0.10,0.10,0.12'), k=float(args.get('k', 1.0)))
    world(float(args.get('amb', 0.12)), L.hex2rgb('8E96A3'), L.hex2rgb(args.get('bg', 'F3E6C8')))
    sun_dir(V(fargs('sundir', '0.1,0.9,-0.35')), float(args.get('sun', 2.2)), L.hex2rgb('FFE7C2'))
    cx, cy, cz = fargs('cam', '0.0,2.6,2.1')
    lx, ly, lz = fargs('look', '0.0,-10.0,1.6')
    cam = camera((cx, cy, cz), (lx, ly, lz), float(args.get('fov', 58)))
    cam.data.shift_y = float(args.get('shift_y', 0.0))     # lens shift: moves the framing (room for the caption) without changing perspective
    out = os.path.join(RAW, f'end{TAG}.png')
    R.render(out)
    print('RENDERED', out)


def shot_fishinfo():
    L.reset_scene()
    fish, fobjs, facts = import_fbx('Fish')
    for fr in [float(x) for x in args.get('frames', '0').split(',')]:
        pose(fish, facts, args.get('fclip', 'OpenMouth'), fr)
        bpy.context.view_layer.update()
        geo = next(o for o in fobjs if o.type == 'MESH')
        ev = geo.evaluated_get(bpy.context.evaluated_depsgraph_get())
        me = ev.to_mesh()
        groups = {}
        for p_ in me.polygons:
            mn = geo.data.materials[p_.material_index].name.split('.')[0]
            for v in p_.vertices:
                groups.setdefault(mn, []).append(geo.matrix_world @ me.vertices[v].co)
        for mn, pts in sorted(groups.items()):
            lo = V((min(p.x for p in pts), min(p.y for p in pts), min(p.z for p in pts)))
            hi = V((max(p.x for p in pts), max(p.y for p in pts), max(p.z for p in pts)))
            print('FI', fr, mn, 'min', tuple(round(c, 2) for c in lo), 'max', tuple(round(c, 2) for c in hi))
        ev.to_mesh_clear()


{'title': shot_title, 'card': shot_card, 'end': shot_end, 'fishinfo': shot_fishinfo}[SHOT]()
