# -*- coding: utf-8 -*-
"""Slice-2 previews: a_plaza / a_alley / a_hideout / a_cart / a_field from the EXACT game camera (Unity FollowCamera maths)
at three player positions each. Level rebuilt in-process (ouat_areas -> slice 1 + slice 2); props built fresh from the
current scripts (ouat_props / ouat_village / ouat_dressing / creatures); the round-4 characters imported from their FBX
and posed with their baked takes. Only the active area + Global is shown (AreaSystem); lights = intended Unity mood.
usage: blender -b --factory-startup --python slice2_scene.py -- area=a_plaza shots=0,1,2 [samples=24] [tag=]"""
import sys, os, json, math, random
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import bpy
from mathutils import Vector, Matrix
import ouat_lib as L
import ouat_render as R

argv = sys.argv[sys.argv.index('--') + 1:] if '--' in sys.argv else []
args = dict(a.split('=', 1) for a in argv if '=' in a)
AREA = args.get('area', 'a_plaza')
SHOTS = [int(x) for x in args.get('shots', '0,1,2').split(',')]
TAG = args.get('tag', '')
ART = os.path.dirname(HERE)
PROJ = os.path.dirname(ART)
MODELS = os.path.join(PROJ, 'Unity', 'Assets', 'Game', 'Art', 'Models')
RAW = os.path.join(ART, 'renders', 'raw', '18')
os.makedirs(RAW, exist_ok=True)
V = Vector

L.reset_scene()
import ouat_slice as SL
import ouat_slice2 as S2
import ouat_areas as AR
LV_ASSET = AR.build_level_areas()
LEVEL = LV_ASSET.root
COLL = LV_ASSET.coll
bpy.context.view_layer.update()

import ouat_props as P
import ouat_village as VL
import ouat_dressing as D
import ouat_creatures as CRE
import ouat_characters as CH
BUILDERS = {}
for mod in (P, VL, D):
    for n, f in mod.ASSETS:
        BUILDERS[n] = f
try:
    import ouat_offering as OFF
    for n, f in OFF.ASSETS:
        BUILDERS[n] = f
except Exception as e:
    print('no offering props', e)
BUILDERS.update({'Lump_1': CRE.build_lump_1, 'Lump_2': CRE.build_lump_2, 'Lump_3': CRE.build_lump_3, 'Fish': CH.build_fish})
SRC = {}


def bare(o):
    return o.name.split('|', 1)[-1].split('#')[0]


COLLIDERS = [o for o in COLL.objects if o.type == 'MESH' and (bare(o).startswith('Ground_Walk') or bare(o).startswith('Cliffs'))]


def ground(x, z):
    best = None
    org_w = SL.B(x, z, 50.0)
    for o in COLLIDERS:
        if o.hide_render:
            continue
        mi = o.matrix_world.inverted()
        org = mi @ org_w
        d = (mi.to_3x3() @ V((0, 0, -1))).normalized()
        hit, loc, nrm, idx = o.ray_cast(org, d, distance=100.0)
        if hit:
            w = o.matrix_world @ loc
            if best is None or w.z > best:
                best = w.z
    return 0.0 if best is None else best


# ------------------------------------------------------------------ sources: props (built) and characters (FBX, baked poses)
def src_prop(name):
    if name in SRC:
        return SRC[name]
    A = BUILDERS[name]()
    for ob in A.all_objects():
        ob.hide_render = True
    SRC[name] = [A.root]
    return SRC[name]


def fix_mats(objs):
    for ob in objs:
        if ob.type != 'MESH':
            continue
        for i, m in enumerate(ob.data.materials):
            if m is None:
                continue
            base = m.name.split('.')[0]
            if base in L.MATS and m.name != base:
                ob.data.materials[i] = L.get_mat(base)


CHAR_FBX = {}


def load_char(name):
    if name in CHAR_FBX:
        return CHAR_FBX[name]
    before = set(bpy.data.objects)
    acts0 = set(bpy.data.actions)
    bpy.ops.import_scene.fbx(filepath=os.path.join(MODELS, name + '.fbx'), use_anim=True, automatic_bone_orientation=False, ignore_leaf_bones=False)
    new = [o for o in bpy.data.objects if o not in before]
    acts = {a.name.split('|')[-1]: a for a in bpy.data.actions if a not in acts0}
    arm = next(o for o in new if o.type == 'ARMATURE')
    meshes = [o for o in new if o.type == 'MESH']
    fix_mats(meshes)
    for o in new:
        o.hide_render = True
    CHAR_FBX[name] = (arm, meshes, acts, new)
    return CHAR_FBX[name]


POSES = {}


def posed(name, take='Idle', frame=0):
    """static meshes of a character in one pose (world space with the root at the origin), cached."""
    key = (name, take, frame)
    if key in POSES:
        return POSES[key]
    arm, meshes, acts, new = load_char(name)
    act = acts.get(take) or acts.get('Idle')
    if arm.animation_data is None:
        arm.animation_data_create()
    arm.animation_data.action = act
    try:
        arm.animation_data.action_slot = act.slots[0]
    except Exception:
        pass
    sc = bpy.context.scene
    f0 = int(act.frame_range[0])
    sc.frame_set(f0 + frame)
    dg = bpy.context.evaluated_depsgraph_get()
    out = []
    for m in meshes:
        if m.name.split('.')[0] == 'Mark':
            continue
        ev = m.evaluated_get(dg)
        me = bpy.data.meshes.new_from_object(ev, depsgraph=dg)
        me.transform(m.matrix_world)
        for i, mat in enumerate(m.data.materials):
            if i < len(me.materials):
                me.materials[i] = mat
        ob = bpy.data.objects.new(f'{name}_{take}_{frame}_{m.name}', me)
        bpy.context.scene.collection.objects.link(ob)
        ob.hide_render = True
        out.append(ob)
    POSES[key] = out
    return out


INST = []


def put(name, x, z, yaw=0.0, scale=1.0, y=None, lift=0.0, take=None, frame=0):
    """place an instance (Unity x, z, yaw). Props: built asset hierarchy; characters: baked pose meshes."""
    inst = bpy.data.objects.new(f'inst_{name}_{len(INST)}', None)
    bpy.context.scene.collection.objects.link(inst)
    yy = ground(x, z) if y is None else y
    inst.location = SL.B(x, z, yy + lift)
    inst.rotation_euler = (0, 0, math.radians(-yaw))
    inst.scale = (scale, scale, scale)
    if take is not None:
        for src in posed(name, take, frame):
            c = bpy.data.objects.new(src.name + '#', src.data)
            bpy.context.scene.collection.objects.link(c)
            c.parent = inst
            c.hide_render = False
    else:
        roots = src_prop(name)
        mapping = {}

        def cp(ob, parent):
            n = ob.copy()
            bpy.context.scene.collection.objects.link(n)
            n.hide_render = False
            n.parent = parent
            if parent is inst:
                n.matrix_parent_inverse = Matrix.Identity(4)
            else:
                n.matrix_parent_inverse = ob.matrix_parent_inverse.copy()
            for ch in ob.children:
                cp(ch, n)
            return n
        for r in roots:
            cp(r, inst)
    INST.append(inst)
    return inst


def child(inst, part):
    for ob in inst.children_recursive:
        if bare(ob).split('.')[0] == part:
            return ob
    return None


# ------------------------------------------------------------------ scene content per area
def stage_and_boards():
    put('Stage', S2.ST_C.x, S2.ST_C.y, S2.ST_YAW)
    for b in S2.BOARDS:
        put('PictureBoard', b.x, b.y, S2.ST_YAW)


def dressing(area):
    lamps = []
    for it in json.load(open(os.path.join(ART, 'layout_dressing.json'), encoding='utf-8'))['items']:
        if it.get('area') != area or it['model'] not in BUILDERS:
            continue
        put(it['model'], it['pos'][0], it['pos'][1], it.get('yaw', 0), it.get('scale', 1.0))
        if it['model'].startswith('Lantern_Hanging'):
            lamps.append((it['pos'][0], it['pos'][1], it.get('yaw', 0), 'hang'))
        if it['model'] == 'LampPost':
            lamps.append((it['pos'][0], it['pos'][1], it.get('yaw', 0), 'post'))
    return lamps


def ring(c, r, n, a0=0.0):
    return [(c[0] + math.cos(a0 + 2 * math.pi * i / n) * r, c[1] + math.sin(a0 + 2 * math.pi * i / n) * r) for i in range(n)]


def face_to(p, q):
    return math.degrees(math.atan2(q[0] - p[0], q[1] - p[1]))


def build_plaza(shot):
    stage_and_boards()
    put('Chief', *S2.PLAZA_PTS['z_chief_seat'], S2.ST_YAW + 30, take='Idle')
    for i, (nm, kk) in enumerate((('Villager_A', 'actor_a'), ('Villager_B', 'actor_b'), ('Villager_C', 'actor_c'))):
        p = S2.PLAZA_PTS[kk]
        put(nm, p.x, p.y, S2.ST_YAW, take='Talk' if i != 1 else 'Point', frame=12 + i * 7)
    # audience: silhouettes seated in the drawn rings facing the stage
    c = (-5.5, 12.5)
    for i, (x, z) in enumerate(ring(c, 4.2, 9, math.radians(150))):
        if (V((x, z)) - V((-5.5, 12.5))).length < 1 or not (-1.4 < math.atan2(z - 12.5, x + 5.5) < 2.6) and i % 2:
            continue
        put('Silhouette_A' if i % 2 else 'Silhouette_B', x, z, face_to((x, z), S2.ST_C) + random.Random(i).uniform(-12, 12), take='Kneel', frame=20)
    if shot == 1:
        # villagers crowding the guest with food (comedy): baskets, bowing, reaching
        hx, hz = SHOT_POS['a_plaza'][1][0]
        for i, (x, z) in enumerate(ring((hx, hz), 1.7, 6, 0.3)):
            nm = ('Villager_A', 'Villager_B', 'Villager_C')[i % 3]
            take = ('BowHold', 'Reach', 'Gather', 'Point', 'BowHold', 'Reach')[i]
            put(nm, x, z, face_to((x, z), (hx, hz)), take=take, frame=20)
        put('Basket', hx + 1.0, hz - 0.8, 30)
        put('Basket', hx - 0.9, hz + 1.1, 200, 0.9)
    else:
        for i, (x, z, yaw) in enumerate(((-9.6, 20.6, 120), (-7.6, 19.0, 300))):
            put(('Villager_A', 'Villager_C')[i], x, z, yaw, take='Gather', frame=30)
    pz = S2.PLAZA_PTS['z_porridge']
    pg = pz + S2.PORRIDGE_OFF - S2.fwd(S2.PORRIDGE_YAW) * 0.75
    put('Villager_B', pg.x, pg.y, S2.PORRIDGE_YAW, take='Gather', frame=40)          # the porridge giver behind the counter
    put('Silhouette_A', pz.x - 0.6, pz.y + 0.4, 120, take='Idle')


def seated_lump(c, yaw, lump):
    put('Chair', c[0], c[1], yaw)
    put(lump, c[0], c[1], yaw, y=ground(c[0], c[1]) + S2.CHAIR_SEAT)


def build_alley(shot):
    for d in S2.ALLEY_SEATED:
        seated_lump(d['chair'], d['yaw'], d['lump'])
    kc = S2.KID_CHAIR
    seated_lump(kc['chair'], kc['yaw'], kc['lump'])
    m = S2.ALLEY_PTS['mother']
    put('Mother', m.x, m.y, 205, take='Idle')
    for i, (x, z, yaw, nm, take) in enumerate(((20.8, 18.4, 30, 'Villager_B', 'BowHold'), (18.6, 17.6, 60, 'Silhouette_A', 'Idle'),
                                               (27.6, 23.0, 215, 'Silhouette_B', 'Idle'))):
        put(nm, x, z, yaw, take=take, frame=15)


def build_hideout(shot):
    for it in S2.hideout_stash_list():
        if it['model'] in BUILDERS:
            put(it['model'], it['pos'][0], it['pos'][1], it.get('yaw', 0), it.get('scale', 1.0), y=it['y'])


def build_cart(shot):
    c = S2.CART_PTS['cart']
    cart = put('Cart', c.x, c.y, 90)
    put('ItemPile', c.x, c.y, 0, 0.55, y=ground(c.x, c.y) + 0.7)
    boss = S2.CART_PTS['collector_boss']
    put('Silhouette_B', boss.x, boss.y, 300, take='Idle')
    for i, (x, z, yaw, take) in enumerate(((15.8, -4.4, 200, 'Gather'), (16.8, -5.2, 240, 'Push'), (11.6, -9.8, 30, 'Gather'))):
        put('Silhouette_A' if i % 2 else 'Silhouette_B', x, z, yaw, take=take, frame=24)


def build_field(shot):
    put('Pond', S2.POND_C.x, S2.POND_C.y, 0, 0.9, y=S2.YPOND - 0.02)
    st = S2.FIELD_PTS['pond_stone']
    put('StoneTablet', st.x, st.y, 25)
    pg = S2.FIELD_PTS['page']
    put('Signpost', S2.FIELD_PTS['sign'].x, S2.FIELD_PTS['sign'].y, 120)
    put('PinocchioPage', pg.x, pg.y, 120)
    # procession: villagers pushing the two carts
    for (x, z, yaw) in ((37.6, -5.0, 120), (42.6, -7.8, 125)):
        back = V((x, z)) - V((math.sin(math.radians(yaw)), math.cos(math.radians(yaw)))) * 1.9
        put('Villager_A', back.x - 0.3, back.y, yaw, take='Push', frame=20)
        put('Silhouette_B', back.x + 0.5, back.y + 0.4, yaw, take='Push', frame=26)
    stn = S2.FIELD_PTS['z_field_stone']
    rd = (S2.POND_C - stn).normalized()
    if 'NoseFileStone' in BUILDERS:
        q = stn - rd * 0.35
        put('NoseFileStone', q.x, q.y, math.degrees(math.atan2(rd.x, rd.y)))
    # lined-up villagers on the apron facing the pond (offering day): 16 in two rows
    for i, d in enumerate(S2.LINEUP):
        if shot == 0 and i % 2:
            continue
        nm = ('Silhouette_A', 'Silhouette_B', 'Villager_C', 'Silhouette_A')[i % 4]
        put(nm, d.x, d.y, face_to((d.x, d.y), (S2.POND_C.x, S2.POND_C.y)), take='BowHold' if shot == 2 else 'Kneel', frame=20)
    b = S2.FIELD_PTS['z_pond_bank']
    put('Lump_3', b.x, b.y, 300)
    if shot == 2:
        f = put('Fish', S2.POND_C.x, S2.POND_C.y, 300, 1.0, y=S2.YPOND + 1.4)
        f.rotation_euler = (math.radians(-55), 0, math.radians(-300))
        f.rotation_mode = 'ZXY'
        put('FX_Splash', S2.POND_C.x, S2.POND_C.y, 0, 2.2, y=S2.YPOND)


SHOT_POS = {
    'a_plaza': [((-12.0, 23.6), 105, 'start · 길목 계단 아래, 무대가 정면'), ((-5.6, 15.4), 70, 'middle · 먹을 것을 들고 몰려드는 주민들'),
                ((3.6, 3.2), 135, 'exit · 종탑 옆 계단, 아래 창고와 수레 길'), ((-8.6, 9.4), 140, 'porridge · 죽 가게(z_porridge)')],
    'a_alley': [((15.6, 16.8), 70, 'start · 광장에서 들어온 자리, 의자마다 덩어리'), ((24.4, 20.4), 72, 'middle · 덜 지어진 집들 사이'),
                ((31.0, 21.4), 75, 'exit · 키노피오 집 앞(안이 보임), 옆 바위 틈')],
    'a_hideout': [((39.6, 28.3), 60, 'start · 뿌리 굴로 비집고 들어온 자리'), ((42.0, 28.6), 40, 'middle · 형과 그린 벽 낙서 앞'),
                  ((43.6, 29.6), 55, 'stash · 숨겨 둔 사람 물건 선반')],
    'a_cart': [((11.0, -4.0), 115, 'start · 광장 계단 아래, 수거꾼 창고'), ((13.2, -5.0), 160, 'middle · 바칠 수레와 사람 고정쇠'),
               ((22.6, -4.8), 95, 'exit · 동쪽 수레 길 끝, 밭과 웅덩이가 보임')],
    'a_field': [((32.6, -4.6), 110, 'start · 수레 길에서 들어선 밭, 끝에 검은 웅덩이'), ((46.4, -9.0), 130, 'middle · 웅덩이가 보이는 밭 끝, 줄 선 주민'),
                ((49.4, -11.6), 135, 'climax · 물고기가 솟음(덩어리가 둑에)')],
}
KID = {'a_plaza': [(-12.8, 22.4, 100), (-7.2, 15.9, 60), (2.6, 3.9, 140), (-9.4, 10.4, 120)],
       'a_alley': [(14.4, 17.4, 60), (23.0, 21.0, 80), (30.2, 24.5, 60)],
       'a_hideout': [(40.6, 30.6, 160), (43.0, 30.2, 40), (42.2, 28.2, 60)],
       'a_cart': [(9.8, -4.4, 120), (12.0, -5.2, 120), (21.4, -4.0, 100)],
       'a_field': [(31.6, -3.6, 110), (45.4, -8.0, 140), None]}
KID_TAKE = {'a_hideout': ['Idle', 'Point', 'Talk'], 'a_alley': ['Idle', 'Idle', 'LookBack']}

# AreaSystem.Moods (Unity, linear): ambient rgb, key rgb, key intensity, drain, background (sRGB 0-1). a_hideout = proposed.
MOOD = {
    'a_plaza': ((0.40, 0.37, 0.34), (0.80, 0.70, 0.58), 0.42, 0.28, (0.33, 0.31, 0.29)),
    'a_alley': ((0.33, 0.32, 0.33), (0.66, 0.64, 0.66), 0.34, 0.45, (0.30, 0.29, 0.29)),
    'a_hideout': ((0.42, 0.36, 0.30), (0.85, 0.70, 0.52), 0.38, 0.30, (0.20, 0.17, 0.15)),
    'a_cart': ((0.32, 0.32, 0.35), (0.60, 0.64, 0.72), 0.32, 0.62, (0.30, 0.30, 0.32)),
    'a_field': ((0.30, 0.30, 0.32), (0.58, 0.62, 0.70), 0.30, 0.62, (0.27, 0.27, 0.29)),
}
KEEP_KEYS = ('Bluebird', 'Beak', 'CapNavy', 'EyeShine', 'Brass', 'Iron', 'Rope', 'M_Wood', 'Leather', 'Book', 'PageWhite', 'Porcelain',
             'LampGlow', 'Light', 'Skin', 'Hair', 'HeroShirt', 'HeroTrousers')   # SceneBuilder.KeepByName (+ hero v2 slots)


def mood_toon(amb, key, kint, drain):
    """OUATToon in game: col = toon(shade/base by NdotL) * (ambient + key*lit + lamps), then lerp to luminance by drain
    (except 'keep' materials). Bands come from a unit-strength sun (NdotL), the level from the same lighting scaled."""
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
        sub = nt.nodes.new('ShaderNodeMix'); sub.data_type = 'RGBA'; sub.blend_type = 'SUBTRACT'
        sub.inputs['Factor'].default_value = 1.0
        nt.links.new(s2r.outputs['Color'], sub.inputs[6]); sub.inputs[7].default_value = (WORLD_AMB, WORLD_AMB, WORLD_AMB, 1)
        kl = nt.nodes.new('ShaderNodeMix'); kl.data_type = 'RGBA'; kl.blend_type = 'MULTIPLY'
        kl.inputs['Factor'].default_value = 1.0
        nt.links.new(sub.outputs[2], kl.inputs[6]); kl.inputs[7].default_value = (key[0] * kint, key[1] * kint, key[2] * kint, 1)
        add = nt.nodes.new('ShaderNodeMix'); add.data_type = 'RGBA'; add.blend_type = 'ADD'
        add.inputs['Factor'].default_value = 1.0
        add.inputs[6].default_value = (*amb, 1)
        nt.links.new(kl.outputs[2], add.inputs[7])
        mul = nt.nodes.new('ShaderNodeMix'); mul.data_type = 'RGBA'; mul.blend_type = 'MULTIPLY'
        mul.inputs['Factor'].default_value = 1.0
        nt.links.new(src, mul.inputs[6]); nt.links.new(add.outputs[2], mul.inputs[7])
        out = mul.outputs[2]
        keep = any(kk in m.name for kk in KEEP_KEYS)
        if not keep and drain > 0:
            hsv = nt.nodes.new('ShaderNodeHueSaturation')
            hsv.inputs['Saturation'].default_value = 1.0 - drain
            nt.links.new(out, hsv.inputs['Color'])
            out = hsv.outputs['Color']
        nt.links.new(out, em.inputs['Color'])


WORLD_AMB = 0.16


def hide_others():
    for ch in LEVEL.children:
        nm = bare(ch)
        if nm.startswith('Area_') and nm != f'Area_{AREA}':
            for o in [ch] + list(ch.children_recursive):
                o.hide_render = True
    global COLLIDERS
    COLLIDERS = [o for o in COLLIDERS if not o.hide_render]


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


def u2b(u):
    return V((-u.x, -u.z, u.y))


def sun_dir(dir_u, strength, color):
    d = u2b(V(dir_u)).normalized()
    ld = bpy.data.lights.new('Key', 'SUN')
    ld.energy = strength
    ld.color = color
    ld.angle = math.radians(3)
    ob = bpy.data.objects.new('Key', ld)
    bpy.context.scene.collection.objects.link(ob)
    ob.rotation_euler = d.to_track_quat('-Z', 'Y').to_euler()


def game_cam(hx, hz, cam, bounds):
    b = bounds
    m = 4.0
    px = min(max(hx, b[0] + m), max(b[0] + m, b[1] - m))
    pz = min(max(hz, b[2] + m), max(b[2] + m, b[3] - m))
    py = ground(hx, hz)
    look = V((px, py + 0.6, pz))
    yaw, pitch = math.radians(cam['yaw']), math.radians(cam['pitch'])
    f = V((math.sin(yaw) * math.cos(pitch), -math.sin(pitch), math.cos(yaw) * math.cos(pitch)))
    pos = look - f * cam['distance']
    c = R.add_camera(tuple(SL.B(pos.x, pos.z, pos.y)), tuple(SL.B(look.x, look.z, look.y)), lens=50)
    c.data.sensor_fit = 'VERTICAL'
    c.data.angle_y = math.radians(cam['fov'])
    c.data.clip_start = 0.3
    c.data.clip_end = 420
    return c


def lights(lamps):
    pt = lambda x, z, y, e, col='FFC27A', r=0.3: R.add_point(tuple(SL.B(x, z, y)), energy=e, color=L.hex2rgb(col), radius=r, name='Lamp')
    for (x, z, yaw, kind) in lamps:
        if kind == 'hang':
            pt(x + 0.6 * math.sin(math.radians(yaw)), z + 0.6 * math.cos(math.radians(yaw)), ground(x, z) + 2.45, 60)
        else:
            dx = -0.38 * math.cos(math.radians(yaw))
            dz = 0.38 * math.sin(math.radians(yaw))
            pt(x + dx, z + dz, ground(x, z) + 2.6, 110)
    if AREA == 'a_plaza':
        for p in (S2.SP(3.95, 0.0), S2.SP(-3.95, 0.0)):
            pt(p.x, p.y, 4.2, 260)
        q = S2.SP(0, 4.5)
        R.add_spot(tuple(SL.B(q.x, q.y, 8.0)), tuple(SL.B(S2.ST_C.x, S2.ST_C.y, 1.0)), energy=2600, size_deg=48, blend=0.6, color=L.hex2rgb('FFC27A'), radius=0.5, name='StageSpot')
        for ka in (10.4, 6.6, -6.6):
            p = S2.SP(ka, 0.2)
            pt(p.x, p.y, 3.3, 60)
    if AREA == 'a_plaza':
        q = S2.PLAZA_PTS['z_porridge'] + S2.PORRIDGE_OFF - S2.fwd(S2.PORRIDGE_YAW) * 0.25
        pt(q.x, q.y, 1.2, 45, 'FFB866', 0.15)
    if AREA == 'a_alley':
        pt(29.1, 25.9, 1.3, 30, 'FFC870', 0.1)
    if AREA == 'a_hideout':
        c = S2.H_C + V((0.3, 0.4))
        R.add_spot(tuple(SL.B(c.x, c.y, S2.YH + 9.0)), tuple(SL.B(c.x, c.y, S2.YH)), energy=2400, size_deg=22, blend=0.5, color=L.hex2rgb('FFDDA8'), radius=0.3, name='Knot')
        lp = S2.HIDE_PTS['hideout_lantern']
        pt(lp.x, lp.y, S2.YH + 0.6, 90, 'FFB866', 0.15)
    if AREA == 'a_cart':
        pass


def main():
    random.seed(7)
    hide_others()
    {'a_plaza': build_plaza, 'a_alley': build_alley, 'a_hideout': build_hideout, 'a_cart': build_cart, 'a_field': build_field}[AREA](SHOTS[0])
    lamps = dressing(AREA)
    hp, hy, label = SHOT_POS[AREA][SHOTS[0]]
    hero = put('Hero_Bluebird', hp[0], hp[1], hy, take='Idle', frame=10)
    kd = KID[AREA][SHOTS[0]]
    if AREA == 'a_cart' and SHOTS[0] == 0:
        b = S2.CART_PTS['z_depot_barrel']
        put('Kinopio', b.x, b.y, 120, take='Idle', frame=20, y=S2.YC + 0.72)       # dancing on the open barrel
        kd = None
    if kd:
        kt = (KID_TAKE.get(AREA, []) + ['Idle'] * 4)[SHOTS[0]]
        put('Kinopio', kd[0], kd[1], kd[2], take=kt, frame=20)
    R.setup_render(res=(1920, 1080), samples=int(args.get('samples', 24)))
    R.prepare_all(outline_scale=1.0, hatch_scale=300.0)
    for o in bpy.data.objects:
        nm = bare(o)
        if nm.startswith('Ground_Lines') or nm.startswith('Light_') or nm.startswith('Vista') or nm in ('Ceiling', 'Backdrop'):
            o.visible_shadow = False
    amb, key, kint, drain, bg = MOOD[AREA]
    ov = next((a for a in S2.NEW_AREAS if a['id'] == AREA), {}).get('mood', {})
    amb = tuple(c * ov.get('ambient', 1.0) for c in amb)
    kint = float(args.get('kint', ov.get('keyIntensity', kint)))
    drain = ov.get('drain', drain)
    if AREA == 'a_hideout':
        amb, kint = (0.36, 0.31, 0.26), 0.30
    mood_toon(amb, key, kint, float(args.get('drain', drain)))
    srgb2lin = lambda c: c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4
    world(WORLD_AMB, (1.0, 1.0, 1.0), tuple(srgb2lin(c) for c in bg))
    sun_dir((-0.33, -0.82, 0.47), 1.0, (1.0, 1.0, 1.0))
    lights(lamps)
    cam_v, piv = S2.GAME_CAM2[AREA]
    bounds = [piv[0] - 4, piv[1] + 4, piv[2] - 4, piv[3] + 4]
    for si in SHOTS:
        hp, hy, label = SHOT_POS[AREA][si]
        cam = game_cam(hp[0], hp[1], cam_v, bounds)
        bpy.context.view_layer.update()
        out = os.path.join(RAW, f'{AREA}_{si}{TAG}.png')
        R.render(out)
        json.dump({'label': label, 'hero': list(R.project(cam, [hero.location + V((0, 0, 0.5))])[0])}, open(out[:-4] + '.json', 'w', encoding='utf-8'), ensure_ascii=False)
        print('RENDERED', out)


main()
