# Round-2 preview: the level as the game builds it (Level_Ch1 + SceneBuilder placements + layout_dressing.json),
# rendered from the game's follow-camera views and from straight above with the zones overlaid.
# usage: blender -b art/blend/ouat_ch1_assets.blend --python game_scene.py -- shot=cam_fall|cam_gate|cam_plaza|cam_field|cam_pond|top [dressing=1] [samples=32] [tag=]
import sys, os, json, math, random
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import bpy
from mathutils import Vector
import ouat_lib as L
import ouat_render as R
import ouat_level as LV
import render_previews as RP
import ouat_areas as AR
import ouat_slice as SL

argv = sys.argv[sys.argv.index('--') + 1:] if '--' in sys.argv else []
args = dict(a.split('=', 1) for a in argv if '=' in a)
SHOT = args.get('shot', 'top')
DRESS = args.get('dressing', '1') == '1'
TAG = args.get('tag', '')
ART = os.path.dirname(HERE)
CH1 = SL.patch_ch1(json.load(open(LV.CH1, encoding='utf-8')))   # slice-1 positions for a_fall / a_gate
LV.KEEP = LV.load_keepouts()
rnd = random.Random(3)
USED = set()
V = Vector


def gy(x, z):
    return LV.height(V((x, z)))


PLACED = []


def put(name, x, z, yaw=0.0, scale=1.0, y=None, new=True, area=None):
    r = RP.dup(name) if new else RP.root(name)
    USED.add(name)
    r.location = LV.B(x, z, gy(x, z) if y is None else y)
    r.rotation_euler = (0, 0, math.radians(-yaw))
    r.scale = (scale, scale, scale)
    PLACED.append((r, (x, z), area))
    return r


def yaw_to(a, b):
    return math.degrees(math.atan2(b[0] - a[0], b[1] - a[1]))


def C(pid):
    for p in CH1['places']:
        if p['id'] == pid:
            return p['center']


def build():
    for c in bpy.data.collections:
        r = bpy.data.objects.get(c.name)
        if r is not None:
            r.location = (0, 0, -500)
    lv = put('Level_Ch1', 0, 0, 0, y=0.0, new=False)
    for o in lv.children:
        if o.name.endswith('|Ceiling') or o.name.endswith('|Backdrop') or o.name.endswith('|Ground_Lines'):
            o.visible_shadow = False
    # --- SceneBuilder BuildDressing
    pl = C('plaza')
    put('Tower_Dome', pl[0] - 17, pl[1] + 18, 160, 1.1)
    put('Tower_Dome', pl[0] + 17, pl[1] + 20, 200, 1.25)
    put('Tower_Dome', pl[0] + 30, pl[1] + 30, 220, 0.9)
    lamps = []
    for i in range(5):
        if i == 2:
            continue
        x, z = pl[0] - 12 + i * 6, pl[1] + (-4 if i % 2 == 0 else 2)
        put('LampPost', x, z, 0)
        lamps.append((x - 0.38, z))
    al = C('alley')
    for i in range(6):
        dx, dz = -10 + i * 4.4, (6.5 if i % 2 == 0 else -6.5)
        put(f'House_{1 + i % 4}', al[0] + dx, al[1] + dz, 180 if dz > 0 else 0)
    for i, pid in enumerate(('gate', 'gate', 'field', 'field')):
        if pid == 'gate':
            continue          # slice 1: the gate diorama has its own unfinished house
        c = C(pid)
        put(f'House_{1 + (i + 2) % 4}', c[0] + (-9 if i % 2 == 0 else 9), c[1] + (9 if i < 2 else 13), rnd.uniform(0, 360))
    for (m, x, z, yaw, sc) in SL.FALL_JUNK:
        put(m, x, z, yaw, sc)
    # --- props
    P = {p['id']: p['pos'] for p in CH1['props']}
    put('ItemPile', *P['fall_pile'], 20, 1.8)
    put('Ladder', SL.RAMP_T.x, SL.RAMP_T.y, yaw_to(tuple(SL.RAMP_T), tuple(SL.RAMP_B)), y=SL.H_LO)    # rough; slice_scene.py places it on the ramp
    put('DrawnBar', *P['bolt_fall'], SL.FALL_FACING['bolt_fall'])
    put('StoneTablet', *P['gate_stone'], SL.GATE_FACING['gate_stone'])
    st = put('Stage', P['stage'][0], P['stage'][1] + 2.4, 180)
    bpy.context.view_layer.update()
    spot = [o for o in st.children_recursive if o.name.split('|')[-1].split('#')[0] == 'PuppetSpot'][0]
    pp = RP.root('Puppet'); USED.add('Puppet')
    pp.parent = spot; pp.matrix_parent_inverse.identity(); pp.location = (0, 0, 0); pp.rotation_euler = (0, 0, 0)
    put('FishProp', *P['fish_prop'], 180, y=gy(*P['fish_prop']) + 0.9)
    put('Chair', *P['lump_prop'], 180); put('Lump_1', *P['lump_prop'], 180, y=gy(*P['lump_prop']) + 0.5)
    for ins in CH1['inscriptions']:
        if ins['id'].startswith('ins_board'):
            put('PictureBoard', *ins['pos'], yaw_to(ins['pos'], pl))
    for i in range(6):
        dx, dz = -10 + i * 4.4, (3.8 if i % 2 == 0 else -3.8)
        x, z = al[0] + dx, al[1] + dz
        if math.hypot(x - 25, z - 29) < 2.5:
            continue
        put('Chair', x, z, 180 if dz > 0 else 0); put(f'Lump_{1 + i % 3}', x, z, rnd.uniform(0, 360), y=gy(x, z) + 0.5)
    put('Chair', *P['mother_lump'], 200); put('Lump_2', *P['mother_lump'], 200, y=gy(*P['mother_lump']) + 0.5)
    fd = C('field')
    for i in range(6):
        put('Mound', fd[0] - 8 + (i % 3) * 8, fd[1] + 4 + (i // 3) * 5, 0)
    put('Cart', *P['cart'], yaw_to(P['cart'], (54, -15)))
    put('Signpost', *P['sign'], yaw_to(P['sign'], fd) + 180)
    put('PinocchioPage', *P['page'], 25, y=gy(*P['page']) + 0.02)
    put('Pond', *P['pond'], 0, 0.9, y=gy(*P['pond']) - 0.05)
    put('StoneTablet', *P['pond_stone'], yaw_to(P['pond_stone'], fd) + 180, 1.15)
    put('Fence_DrawnBar', *P['fence'], yaw_to((-36, 4), (-28, -4)) + 90)
    # --- npcs
    vil = ['Villager_A', 'Villager_B', 'Villager_C']
    vi = 0
    for n in CH1['npcs']:
        m = n['model']
        if m == 'Fish':
            continue
        cnt = n.get('count', 1)
        for k in range(cnt):
            x, z = n['spawn']
            if cnt > 1:
                a = 2 * math.pi * k / cnt
                x, z = x + math.cos(a) * 1.6, z + math.sin(a) * 1.2
            if m == 'Villager':
                name = vil[vi % 3]; vi += 1
            elif m == 'Silhouette':
                name = 'Silhouette_A' if k % 2 == 0 else 'Silhouette_B'
            else:
                name = m
            put(name, x, z, n.get('facing', 0))
    hz = [z for z in CH1['zones'] if z['id'] == 'z_hero_start'][0]['pos']
    put('Hero_Bluebird', hz[0], hz[1], 120)
    # --- dressing layout
    if DRESS:
        lp = os.path.join(ART, 'layout_dressing.json')
        if os.path.exists(lp):
            for it in json.load(open(lp, encoding='utf-8'))['items']:
                if bpy.data.objects.get(it['model']) is None:
                    continue
                r = put(it['model'], it['pos'][0], it['pos'][1], it.get('yaw', 0), it.get('scale', 1.0), area=it.get('area'))
                if it['model'].startswith('Lantern_Hanging'):
                    lamps.append((it['pos'][0], it['pos'][1]))
    RP.hide_all_but(USED)
    return lamps


VIEWS = {  # SceneBuilder FollowCamera views (yaw, pitch, distance, fov, target y offset)
    'cam_fall': ('fall', 30, 40, 15, 32, 1.5 + 0.6),
    'cam_gate': ('gate', 40, 36, 15, 32, 0.6),
    'cam_plaza': ('plaza', 15, 32, 19, 34, 1.2),
    'cam_alley': ('alley', 50, 42, 14, 32, 0.6),
    'cam_field': ('field', 35, 44, 18, 34, 0.6),
    'cam_pond': ('pond', 25, 34, 18, 34, 0.8),
}


def game_camera(place, yaw, pitch, dist, fov, yoff, zoff=0.0):
    c = C(place)
    tgt = V((c[0], yoff, c[1] + zoff))
    fwd = V((math.sin(math.radians(yaw)) * math.cos(math.radians(pitch)), -math.sin(math.radians(pitch)), math.cos(math.radians(yaw)) * math.cos(math.radians(pitch))))
    pos = tgt - fwd * dist
    cam = R.add_camera(tuple(LV.B(pos.x, pos.z, pos.y)), tuple(LV.B(tgt.x, tgt.z, tgt.y)), lens=50)
    cam.data.sensor_fit = 'VERTICAL'
    cam.data.angle_y = math.radians(fov)
    return cam


SUN_E = float(args.get('sun', 2.4))


def lights(lamps):
    R.world_light(L.hex2rgb('D5D9DE'), 0.3)
    R.add_sun((50, 0, 35), SUN_E, color=(1.0, 0.98, 0.95), angle=3, name='Key')
    f = C('fall')
    R.add_spot(tuple(LV.B(f[0], f[1], 30)), tuple(LV.B(f[0], f[1], 1.5)), energy=70000, size_deg=34, blend=0.5, radius=2.5, name='Shaft')
    for (x, z) in lamps:
        R.add_point(tuple(LV.B(x, z, 2.7)), energy=380, radius=0.15, name='Lamp')
    st = [p for p in CH1['props'] if p['id'] == 'stage'][0]['pos']
    R.add_point(tuple(LV.B(st[0], st[1] + 1, 4.0)), energy=1200, color=(1, 0.85, 0.6), radius=0.5, name='StageFill')


def top():
    lamps = build()
    R.setup_render(res=(3200, 2400), samples=int(args.get('samples', 24)), bg=L.hex2rgb('F1EEE6'))
    R.prepare_all(outline_scale=1.4, hatch_scale=520.0, skip=())
    # hide ceiling + backdrop for the map view
    for o in RP.root('Level_Ch1').children_recursive:
        nm = o.name.split('|')[-1]
        if nm in ('Ceiling', 'Backdrop') or nm.startswith('Margin_'):
            o.hide_render = True
    lights(lamps)
    cam = R.add_camera(tuple(LV.B(0, 6, 200)), tuple(LV.B(0, 6.001, 0)), lens=50, ortho=200)
    cam.rotation_euler = (0, 0, math.radians(180))   # Unity +X right, +Z up in the image
    bpy.context.view_layer.update()
    items = []
    for z in CH1['zones']:
        x, y, _ = R.project(cam, [LV.B(z['pos'][0], z['pos'][1], 0)])[0]
        xr, _, _ = R.project(cam, [LV.B(z['pos'][0] + z.get('radius', 1), z['pos'][1], 0)])[0]
        items.append({'id': z['id'], 'x': x, 'y': y, 'r': abs(xr - x), 'kind': 'zone'})
    for p in CH1['places']:
        x, y, _ = R.project(cam, [LV.B(p['center'][0], p['center'][1], 0)])[0]
        xr, _, _ = R.project(cam, [LV.B(p['center'][0] + p['radius'], p['center'][1], 0)])[0]
        items.append({'id': p['name'], 'x': x, 'y': y, 'r': abs(xr - x), 'kind': 'place'})
    for p in CH1['props']:
        x, y, _ = R.project(cam, [LV.B(p['pos'][0], p['pos'][1], 0)])[0]
        items.append({'id': p['id'], 'x': x, 'y': y, 'r': 0, 'kind': 'prop'})
    grid = []
    for gx in range(-80, 81, 20):
        a = R.project(cam, [LV.B(gx, -60, 0)])[0]; b = R.project(cam, [LV.B(gx, 72, 0)])[0]
        grid.append({'v': gx, 'axis': 'x', 'a': a[:2], 'b': b[:2]})
    for gz in range(-60, 73, 20):
        a = R.project(cam, [LV.B(-90, gz, 0)])[0]; b = R.project(cam, [LV.B(90, gz, 0)])[0]
        grid.append({'v': gz, 'axis': 'z', 'a': a[:2], 'b': b[:2]})
    json.dump({'res': [3200, 2400], 'items': items, 'grid': grid}, open(os.path.join(ART, 'renders', 'raw', 'level_top.json'), 'w', encoding='utf-8'), ensure_ascii=False)
    R.render(os.path.join(ART, 'renders', 'raw', f'level_top{TAG}.png'))


def view(shot):
    lamps = build()
    R.setup_render(res=(1920, 1080), samples=int(args.get('samples', 24)), bg=L.hex2rgb('D5D9DE'))
    R.prepare_all(outline_scale=1.0, hatch_scale=300.0)
    lights(lamps)
    game_camera(*VIEWS[shot])
    R.render(os.path.join(ART, 'renders', 'raw', f'{shot}{TAG}.png'))


def area_page(aid):
    lamps = build()
    a = AR.AID[aid]
    keep_lamps = [l for l in lamps if AR.area_of(l) == aid]
    for r, (x, z), area in PLACED:
        if r.name == 'Level_Ch1':
            continue
        ar = area or AR.area_of((x, z))
        if ar != aid:
            for o in [r] + list(r.children_recursive):
                o.hide_render = True
    lv = RP.root('Level_Ch1')
    for ch in lv.children:
        nm = ch.name.split('|')[-1]
        if nm.startswith('Area_') and nm != f'Area_{aid}':
            for o in [ch] + list(ch.children_recursive):
                o.hide_render = True
        if nm == 'Global':
            for o in ch.children_recursive:
                if not o.name.endswith('Backdrop'):
                    o.hide_render = True
    R.setup_render(res=(1920, 1080), samples=int(args.get('samples', 24)), transparent=True)
    R.prepare_all(outline_scale=1.0, hatch_scale=300.0)
    lights(keep_lamps)
    cam = a['camera']
    c = AR.area_center(a)
    if aid == 'a_cart':
        c = V((-28.0, -4.0))      # the drawn fence, centrepiece of the corridor
    yoff = 2.5 if aid == 'a_fall' else 1.0
    tgt = V((c.x, yoff, c.y))
    yaw, pitch, dist, fov = cam['yaw'], cam['pitch'], cam['distance'], cam['fov']
    fwd = V((math.sin(math.radians(yaw)) * math.cos(math.radians(pitch)), -math.sin(math.radians(pitch)), math.cos(math.radians(yaw)) * math.cos(math.radians(pitch))))
    pos = tgt - fwd * dist
    cm = R.add_camera(tuple(LV.B(pos.x, pos.z, pos.y)), tuple(LV.B(tgt.x, tgt.z, tgt.y)), lens=50)
    cm.data.sensor_fit = 'VERTICAL'
    cm.data.angle_y = math.radians(fov)
    R.render(os.path.join(ART, 'renders', 'raw', f'page_{aid}{TAG}.png'))
    # also a wider framing so the whole page and its margin are visible
    cm.location = LV.B(*(V((tgt.x, tgt.z)) - V((fwd.x, fwd.z)) * dist * 1.9), tgt.y + (-fwd.y) * dist * 1.9)
    R.render(os.path.join(ART, 'renders', 'raw', f'page_{aid}_wide{TAG}.png'))


EYE = {'eye_plaza': ((-3.5, 1.55, 3.0), (1.0, 2.0, 20.0), 30), 'eye_gate': ((-37.5, 1.6, 22.5), (-12.0, 2.2, 13.0), 30)}


def eye(shot):
    lamps = build()
    R.setup_render(res=(1920, 1080), samples=int(args.get('samples', 24)), bg=L.hex2rgb('D5D9DE'))
    R.prepare_all(outline_scale=1.0, hatch_scale=300.0)
    lights(lamps)
    (px, py, pz), (tx, ty, tz), lens = EYE[shot]
    R.add_camera(tuple(LV.B(px, pz, py)), tuple(LV.B(tx, tz, ty)), lens=lens)
    R.render(os.path.join(ART, 'renders', 'raw', f'{shot}{TAG}.png'))


if __name__ == '__main__':
    if SHOT == 'top':
        top()
        bpy.ops.wm.save_as_mainfile(filepath=os.path.join(ART, 'blend', 'Level_Ch1_scene.blend'), copy=True)
    elif SHOT.startswith('a_'):
        area_page(SHOT)
    elif SHOT in EYE:
        eye(SHOT)
    else:
        view(SHOT)
    print('RENDERED', SHOT)
