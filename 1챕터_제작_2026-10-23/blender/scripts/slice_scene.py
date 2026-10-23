# Slice-1 previews: a_fall / a_gate rendered from the EXACT game camera (Unity FollowCamera maths) at player positions.
# usage: blender -b art/blend/ouat_ch1_assets.blend --python slice_scene.py -- area=a_fall shots=0,1,2 [samples=24] [tag=]
#        [sun=0.9] [amb=0.35] [shaft=60000]
# Rebuilds Level_Ch1 in-process (ouat_areas + ouat_slice), places props/NPCs/dressing as SceneBuilder would with the
# slice positions, shows only the active area + Global (like AreaSystem), lights = intended Unity setup.
import sys, os, json, math
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import bpy
from mathutils import Vector, Matrix
import ouat_lib as L
import ouat_render as R
import render_previews as RP

argv = sys.argv[sys.argv.index('--') + 1:] if '--' in sys.argv else []
args = dict(a.split('=', 1) for a in argv if '=' in a)
AREA = args.get('area', 'a_fall')
SHOTS = [int(x) for x in args.get('shots', '0,1,2').split(',')]
TAG = args.get('tag', '')
ART = os.path.dirname(HERE)
RAW = os.path.join(ART, 'renders', 'raw')
V = Vector

# ------------------------------------------------------------------ rebuild the level
old = bpy.data.collections.get('Level_Ch1')
if old:
    for o in list(old.objects):
        bpy.data.objects.remove(o, do_unlink=True)
    bpy.data.collections.remove(old)
import ouat_slice as SL
import ouat_areas as AR
LV_ASSET = AR.build_level_areas()
LEVEL = LV_ASSET.root
COLL = LV_ASSET.coll
bpy.context.view_layer.update()


def bare(o):
    return o.name.split('|', 1)[-1].split('#')[0]


COLLIDERS = [o for o in COLL.objects if o.type == 'MESH' and (bare(o).startswith('Ground_Walk') or bare(o).startswith('Cliffs') or bare(o).startswith('Walls_Bound'))]


def ground(x, z):
    """Unity Ground(): ray from y=50 down against collider parts of every area."""
    best = None
    org_w = SL.B(x, z, 50.0)
    for o in COLLIDERS:
        mi = o.matrix_world.inverted()
        org = mi @ org_w
        d = (mi.to_3x3() @ V((0, 0, -1))).normalized()
        hit, loc, nrm, idx = o.ray_cast(org, d, distance=100.0)
        if hit:
            w = o.matrix_world @ loc
            if best is None or w.z > best:
                best = w.z
    return 0.0 if best is None else best


# ------------------------------------------------------------------ placement
USED = set(['Level_Ch1'])
PLACED = []


def put(name, x, z, yaw=0.0, scale=1.0, y=None, lift=0.0):
    r = RP.dup(name)
    USED.add(name)
    yy = ground(x, z) if y is None else y
    r.location = SL.B(x, z, yy + lift)
    r.rotation_euler = (0, 0, math.radians(-yaw))
    r.scale = (scale, scale, scale)
    PLACED.append(r)
    return r


def child(r, part):
    for ob in r.children_recursive:
        if bare(ob) == part:
            return ob
    return None


def sit(r, k=0.25):
    for lg in ('LegL', 'LegR'):
        o = child(r, lg)
        if o:
            o.rotation_euler.x = math.radians(80)
    r.location.z -= k


def bow(r, deg=70, kneel=0.25):
    b = child(r, 'Body')
    if b:
        b.rotation_euler.x = math.radians(deg)
    for lg in ('LegL', 'LegR'):
        o = child(r, lg)
        if o:
            o.rotation_euler.x = math.radians(-85)
    r.location.z -= kneel


def look_up(r, deg=-35):
    h = child(r, 'Head')
    if h:
        h.rotation_euler.x = math.radians(deg)


def ucross(a, b):
    return V((a.y * b.z - a.z * b.y, a.z * b.x - a.x * b.z, a.x * b.y - a.y * b.x))


def u2b(u):
    return V((-u.x, -u.z, u.y))


def place_ladder(unfold=False):
    t, b = SL.RAMP_T, SL.RAMP_B
    top_u = V((t.x, SL.H_LO, t.y))
    bot_u = V((b.x, SL.G0, b.y))
    down = (bot_u - top_u).normalized()
    side = ucross(V((0, 1, 0)), down).normalized()
    fwd = ucross(down, side).normalized()     # NOTE: SceneBuilder uses Cross(side, down) -> front (latch) faces INTO the slope; flipped here
    Zb = u2b(down)
    Yb = -u2b(fwd)
    Xb = Yb.cross(Zb)
    m = Matrix((Xb, Yb, Zb)).transposed()
    span = (bot_u - top_u).length
    sc = span / 3.1
    r = RP.dup('Ladder')
    USED.add('Ladder')
    S = Matrix.Diagonal((1.15, 1.15, sc, 1.0))     # length-only scale (local Unity Y) so the rails stay ladder-thin
    r.matrix_world = Matrix.Translation(SL.B(t.x, t.y, SL.H_LO) + u2b(fwd) * 0.06) @ m.to_4x4() @ S
    if unfold:
        up = child(r, 'Upper')
        if up:
            up.rotation_euler.x = math.radians(180)
    return r


def build_fall(shot):
    P = SL.FALL_PTS
    put('ItemPile', *P['fall_pile'], 20, 1.8)
    # LightShaft.fbx is replaced by Light_fall/beam in the level (the old 10 m cone hazes the whole frame)
    place_ladder(unfold=(shot == 3))
    bar = put('DrawnBar', *P['bolt_fall'], SL.FALL_FACING['bolt_fall'])
    if shot == 3:
        b = child(bar, 'Bar')
        if b:
            b.location.z += 1.4
            b.rotation_euler.y = math.radians(-70)
    for (m, x, z, yaw, s) in SL.FALL_JUNK:
        put(m, x, z, yaw, s)
    for pid, m in (('look_book', 'Junk_Book'), ('look_umbrella', 'Junk_Umbrella'), ('look_clock', 'Junk_Clock')):
        put(m, *P[pid], SL.FALL_FACING[pid], 1.25)
    kid_at = {0: (P['z_kid_pile'], 250), 1: (P['z_kid_pile'], 230), 2: (P['kid_wait_below'], 320), 3: ((-43.6, 22.6), 240)}[shot]
    kid = put('Kinopio', *kid_at[0], kid_at[1])
    if shot == 2:
        look_up(kid, -40)
    if shot == 0:
        bow(kid, 55, 0.12)


def build_gate(shot):
    P = SL.GATE_PTS
    F = SL.GATE_FACING
    put('StoneTablet', *P['gate_stone'], F['gate_stone'])
    put('Chief', *P['chief'], F['chief'])
    sit(put('Villager_A', *P['gate_a'], F['gate_a']))
    sit(put('Villager_B', *P['gate_b'], F['gate_b']))
    c = P['crowd_gate']
    for kk in range(4):
        a = 2 * math.pi * kk / 4 + 0.4
        sil = put('Silhouette_A' if kk % 2 == 0 else 'Silhouette_B', c[0] + math.cos(a) * 1.6, c[1] + math.sin(a) * 1.1, F['crowd_gate'] + (kk - 1.5) * 12)
        sit(sil, 0.3)


def build_dressing():
    lp = os.path.join(ART, 'layout_dressing.json')
    lamps = []
    if not os.path.exists(lp):
        return lamps
    for it in json.load(open(lp, encoding='utf-8'))['items']:
        if it.get('area') != AREA or bpy.data.objects.get(it['model']) is None:
            continue
        put(it['model'], it['pos'][0], it['pos'][1], it.get('yaw', 0), it.get('scale', 1.0))
        if it['model'].startswith('Lantern_Hanging'):
            lamps.append((it['pos'][0], it['pos'][1], it.get('yaw', 0)))
    return lamps


SHOT_POS = {
    'a_fall': [((-57.6, 31.2), 100, 'start · 빛 속에 떨어진 자리'), ((-53.9, 27.6), 120, 'middle · 더미에서 언덕 끝으로'),
               ((-51.4, 23.75), 140, 'exit · 사다리 머리, 아래에 키노피오와 빗장'), ((-45.6, 19.6), 57, 'after · 길이 열린 뒤 사다리 아래')],
    'a_gate': [((-37.6, 24.4), 90, 'start · 다리 위(언덕에서 넘어온 자리)'), ((-30.0, 24.3), 90, 'middle · 앉은 주민들과 새김 돌 사이'),
               ((-23.6, 23.9), 80, 'exit · 촌장 앞, 문 너머 광장')],
}


def hide_others():
    for ch in LEVEL.children:
        nm = bare(ch)
        if nm.startswith('Area_') and nm != f'Area_{AREA}':
            for o in [ch] + list(ch.children_recursive):
                o.hide_render = True


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


def sun_dir(dir_u, strength, color):
    d = u2b(V(dir_u)).normalized()
    ld = bpy.data.lights.new('Key', 'SUN')
    ld.energy = strength
    ld.color = color
    ld.angle = math.radians(3)
    ob = bpy.data.objects.new('Key', ld)
    bpy.context.scene.collection.objects.link(ob)
    ob.rotation_euler = d.to_track_quat('-Z', 'Y').to_euler()


def game_cam(hx, hz, cam):
    a = next(x for x in AR.AREAS if x['id'] == AREA)
    b = a['bounds']
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


def top_map():
    for ch in LEVEL.children:
        nm = bare(ch)
        if nm.startswith('Area_') and nm not in ('Area_a_fall', 'Area_a_gate'):
            for o in [ch] + list(ch.children_recursive):
                o.hide_render = True
        if nm.startswith('Global'):
            for o in [ch] + list(ch.children_recursive):
                o.hide_render = True
    for o in COLL.objects:
        if bare(o).startswith('Vista') or bare(o).startswith('Light_'):
            o.hide_render = True
    build_fall(2)
    build_gate(0)
    lamps = build_dressing_all()
    hero = put('Hero_Bluebird', *SL.FALL_PTS['z_hero_start'], 100)
    RP.hide_all_but(USED)
    R.setup_render(res=(2600, 1300), samples=int(args.get('samples', 16)))
    R.prepare_all(outline_scale=1.0, hatch_scale=300.0)
    world(0.5, L.hex2rgb('8E96A3'), L.hex2rgb('9A9C9C'))
    sun_dir((-0.33, -0.82, 0.47), 1.0, L.hex2rgb('C9CFD8'))
    cx, cz = -43.0, 26.5
    cam = R.add_camera(tuple(SL.B(cx, cz, 120)), tuple(SL.B(cx, cz + 0.001, 0)), lens=50, ortho=54.0)
    cam.rotation_euler = (0, 0, math.radians(180))
    bpy.context.view_layer.update()
    items = []
    P = dict(SL.FALL_PTS); P.update(SL.GATE_PTS)
    for k, v in P.items():
        x, y, _ = R.project(cam, [SL.B(v[0], v[1], ground(*v))])[0]
        items.append({'id': k, 'x': x, 'y': y, 'kind': 'pt'})
    for a in (SL.AREA_FALL, SL.AREA_GATE):
        for e in a['exits']:
            x, y, _ = R.project(cam, [SL.B(e['pos'][0], e['pos'][1], ground(*e['pos']))])[0]
            items.append({'id': f"exit {a['id']}→{e['to']}", 'x': x, 'y': y, 'kind': 'exit', 'r': e['radius']})
        b = a['bounds']
        piv = [R.project(cam, [SL.B(xx, zz, 6.0)])[0][:2] for xx, zz in ((b[0] + 4, b[2] + 4), (b[1] - 4, b[2] + 4), (b[1] - 4, b[3] - 4), (b[0] + 4, b[3] - 4))]
        items.append({'id': f"pivot {a['id']}", 'poly': piv, 'kind': 'pivot'})
    for (t, yv) in ((SL.RAMP_T, SL.H_LO), (SL.RAMP_B, SL.G0)):
        x, y, _ = R.project(cam, [SL.B(t.x, t.y, yv)])[0]
        items.append({'id': 'ladder_top' if yv > 3 else 'ladder_bottom', 'x': x, 'y': y, 'kind': 'ladder'})
    grid = []
    for gx in range(-70, -14, 5):
        a_ = R.project(cam, [SL.B(gx, 10, 0)])[0]; b_ = R.project(cam, [SL.B(gx, 44, 0)])[0]
        grid.append({'v': gx, 'axis': 'x', 'a': a_[:2], 'b': b_[:2]})
    for gz in range(10, 45, 5):
        a_ = R.project(cam, [SL.B(-72, gz, 0)])[0]; b_ = R.project(cam, [SL.B(-14, gz, 0)])[0]
        grid.append({'v': gz, 'axis': 'z', 'a': a_[:2], 'b': b_[:2]})
    out = os.path.join(RAW, f'slice_top{TAG}.png')
    R.render(out)
    json.dump({'res': [2600, 1300], 'items': items, 'grid': grid}, open(out[:-4] + '.json', 'w', encoding='utf-8'), ensure_ascii=False)
    print('RENDERED', out)


def build_dressing_all():
    global AREA
    keep = AREA
    out = []
    for a in ('a_fall', 'a_gate'):
        AREA = a
        out += build_dressing()
    AREA = keep
    return out


def main():
    if AREA == 'top':
        return top_map()
    hide_others()
    lamps = []
    if AREA == 'a_fall':
        build_fall(SHOTS[0])
    else:
        build_gate(SHOTS[0])
    lamps = build_dressing()
    hero_pos, hero_yaw, label = SHOT_POS[AREA][SHOTS[0]]
    hero = put('Hero_Bluebird', *hero_pos, hero_yaw)
    if AREA == 'a_gate':
        put('Kinopio', hero_pos[0] - 1.4, hero_pos[1] + 0.9, hero_yaw)
    if AREA == 'a_fall' and SHOTS[0] == 3:
        pass
    RP.hide_all_but(USED)
    R.setup_render(res=(1920, 1080), samples=int(args.get('samples', 24)))
    R.prepare_all(outline_scale=1.0, hatch_scale=300.0)
    for o in COLL.objects:
        nm = bare(o)
        if nm.startswith('Ground_Lines') or nm.startswith('Light_') or nm.startswith('Vista') or nm in ('Ceiling', 'Backdrop'):
            o.visible_shadow = False
    # intended Unity light (see 아트기준 §10): dim cool key from the south-east, low ambient, one warm shaft on the fall
    amb = float(args.get('amb', 0.3))
    world(amb, L.hex2rgb('8E96A3'), L.hex2rgb(args.get('bg', '9A9C9C')))
    sun_dir((-0.33, -0.82, 0.47), float(args.get('sun', 0.9)), L.hex2rgb('C9CFD8'))
    if AREA == 'a_fall':
        h = SL.HEAP
        R.add_spot(tuple(SL.B(h.x, h.y, 30.0)), tuple(SL.B(h.x, h.y, SL.H)), energy=float(args.get('shaft', 60000)), size_deg=17, blend=0.35,
                   color=L.hex2rgb('FFE9C4'), radius=1.0, name='Shaft')
    for (x, z, yaw) in lamps:
        R.add_point(tuple(SL.B(x + 0.6 * math.sin(math.radians(yaw)), z + 0.6 * math.cos(math.radians(yaw)), ground(x, z) + 2.45)), energy=45, radius=0.15, name='Lamp')
    # the painted plaza beyond: a few warm points so the destination glows a little
    for (x, z, y, e) in ((-1.0, 18.5, 3.5, 900), (-12.0, 6.0, 2.7, 160), (-6.0, 12.0, 2.7, 160)):
        R.add_point(tuple(SL.B(x, z, y)), energy=e, color=L.hex2rgb('FFC27A'), radius=0.4, name='TownGlow')
    for si in SHOTS:
        hp, hy, label = SHOT_POS[AREA][si]
        hero.location = SL.B(hp[0], hp[1], ground(*hp))
        hero.rotation_euler = (0, 0, math.radians(-hy))
        cam = game_cam(hp[0], hp[1], SL.AREA_FALL['camera'] if AREA == 'a_fall' else SL.AREA_GATE['camera'])
        bpy.context.view_layer.update()
        out = os.path.join(RAW, f'slice_{AREA}_{si}{TAG}.png')
        R.render(out)
        json.dump({'label': label, 'hero': R.project(cam, [hero.location + V((0, 0, 0.5))])[0]}, open(out[:-4] + '.json', 'w', encoding='utf-8'), ensure_ascii=False)
        print('RENDERED', out)


main()
