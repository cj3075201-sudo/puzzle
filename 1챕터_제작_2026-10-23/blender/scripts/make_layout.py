# Writes art/layout_dressing.json: dressing placements around the six places (Unity world x, z; yaw deg; scale).
# Run inside Blender (uses ouat_level for roads / mesa / heights):
#   blender -b --factory-startup --python make_layout.py
# Rules: every chapter1.json zone keeps (radius + 2 m) clear, main road and cart road (+1 m) clear, nothing on the
# mesa cliff band / ladder notch / pond, nothing on SceneBuilder's own placements (towers, lamps, houses, chairs, stage,
# boards, mounds) or on the level outcrops. Plaza = denser and painted; outskirts = sparse, intentional unfinished lines.
import sys, os, json, math, random
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from mathutils import Vector as V
import ouat_level as LV
import ouat_areas as AR
import ouat_slice as SL

CH1 = json.load(open(LV.CH1, encoding='utf-8'))
LV.KEEP = LV.load_keepouts()
LV.build_cliff_extras(None, None, None)      # fills LV.OUTCROPS
BLOCK = []
for a in AR.AREAS:
    for p0, p1, st in AR.plan_blockers(a):
        BLOCK.append(((p0 + p1) / 2, (p1 - p0).length / 2 + 1.4))
rnd = random.Random(2026)

FOOT = {'Sketch_Wall_1': 3.0, 'Sketch_Wall_2': 2.6, 'Sketch_Wall_3': 2.8, 'Sketch_Tree_1': 1.4, 'Sketch_Tree_2': 1.6,
        'Sketch_Tree_3': 1.2, 'Sketch_Fence_1': 2.2, 'Sketch_Fence_2': 1.7, 'Sketch_Arch': 2.0, 'Scrap_Paper_1': 0.3,
        'Scrap_Paper_2': 0.5, 'Scrap_Paper_3': 0.5, 'Stair_Sketch': 2.6, 'Bench_Puppet': 1.0, 'Barrel': 0.5, 'Crate': 0.5,
        'Basket': 0.3, 'Lantern_Hanging': 0.7, 'Banner_Unfinished': 0.6, 'Rubble_1': 1.3, 'Rubble_2': 1.9, 'PaintPot': 0.4,
        'Brush_Big': 1.8}

# SceneBuilder placements (BuildDressing / PropObject) as blocking circles (x, z, r)
pl = (0, 10)
SB = [(-17, 28, 5.0), (17, 30, 5.5), (30, 40, 4.5)]
SB += [(-12, 6, 1.0), (-6, 12, 1.0), (6, 12, 1.0), (12, 6, 1.0)]
for i in range(6):
    dx, dz = -10 + i * 4.4, (6.5 if i % 2 == 0 else -6.5)
    SB.append((22 + dx, 26 + dz, 3.0))
    SB.append((22 + dx, 26 + (3.8 if i % 2 == 0 else -3.8), 1.3))
SB += [(-39, 27, 3.5), (-21, 27, 3.5), (31, 13, 3.5), (49, 13, 3.5)]
SB += [(0, 20.4, 4.6), (4, 18, 1.8), (-3, 18, 1.2)]
for i in range(5):
    SB.append((-10 + i, 15 + i, 1.8))
for i in range(6):
    SB.append((32 + (i % 3) * 8, 4 + (i // 3) * 5, 3.2))
SB += [(-55, 30, 3.0), (36, -5, 2.0), (-28, -4, 3.5)]

placed = []


def ok(model, x, z, why=False):
    p = V((x, z))
    if SL.in_footprint((x, z)):          # slice-1 dioramas (a_fall / a_gate) are dressed by ouat_slice.SLICE_DRESSING
        return (False, 'slice') if why else False
    f = FOOT[model]
    for z_ in CH1['zones']:
        if (p - V(z_['pos'])).length < z_.get('radius', 1) + 2.0 + f:
            return (False, z_['id']) if why else False
    for c, r, kid in LV.KEEP:
        if (p - c).length < min(r, 2.5) + f * 0.8:
            return (False, kid) if why else False
    dm, dc = LV.road_d(p)
    if dm < 1.0 + f or dc < 1.0 + f:
        return (False, 'road') if why else False
    rel = p - LV.FALL
    rt = LV.mesa_r_top(math.atan2(rel.y, rel.x))
    if rt - 1.2 - f < rel.length < rt + 1.2 + f:
        return (False, 'cliff') if why else False
    d_n, t_n = LV.notch_param(p)
    if d_n < 2.5 + f and -0.2 < t_n < 1.3:
        return (False, 'ladder') if why else False
    if (p - LV.POND).length < LV.POND_R + 1.8 + f:
        return (False, 'pond') if why else False
    if LV.ell(p) > 0.9:
        return (False, 'edge') if why else False
    for (x2, z2, r2) in SB:
        if (p - V((x2, z2))).length < r2 + f:
            return (False, 'scenebuilder') if why else False
    for (c, r) in LV.OUTCROPS:
        if (p - c).length < r + f:
            return (False, 'outcrop') if why else False
    sdm = min(AR.sd_area(a, p) for a in AR.AREAS)
    if sdm > 6.5:
        return (False, 'off-page') if why else False
    ar = AR.AID[AR.area_of(p)]
    if AR.near_exit(ar, p, 2.6 + f):
        return (False, 'exit') if why else False
    if ar['id'] == 'a_cart' and AR.in_chasm(p):
        return (False, 'chasm') if why else False
    for (c, r) in BLOCK:
        if (p - c).length < r + f * 0.6:
            return (False, 'blocker') if why else False
    for it in placed:
        if (p - V(it['pos'])).length < FOOT[it['model']] * 0.8 + f * 0.8:
            return (False, 'overlap') if why else False
    return (True, '') if why else True


def put(model, x, z, yaw=None, scale=1.0, place='', search=4.0, tag=''):
    yaw = rnd.uniform(0, 360) if yaw is None else yaw
    if not ok(model, x, z):
        best = None
        for k in range(160):
            a = rnd.uniform(0, 2 * math.pi)
            r = search * math.sqrt(rnd.random())
            if ok(model, x + math.cos(a) * r, z + math.sin(a) * r):
                best = (x + math.cos(a) * r, z + math.sin(a) * r)
                break
        if best is None:
            print('SKIP', model, (x, z), ok(model, x, z, True)[1])
            return None
        x, z = best
    it = {'model': model, 'pos': [round(x, 2), round(z, 2)], 'yaw': round(yaw % 360, 1), 'scale': round(scale, 2), 'place': place, 'area': AR.area_of((x, z))}
    if tag:
        it['note'] = tag
    placed.append(it)
    return it


def face(a, b):
    return math.degrees(math.atan2(b[0] - a[0], b[1] - a[1]))


def road_yaw(x, z):
    """yaw so a long piece (local X) runs parallel to the nearest main road segment."""
    best = (1e9, 0)
    for i in range(len(LV.MAIN_ROAD) - 1):
        a, b = LV.MAIN_ROAD[i][0], LV.MAIN_ROAD[i + 1][0]
        d, _ = LV.seg_dist(V((x, z)), a, b)
        if d < best[0]:
            best = (d, math.degrees(math.atan2(b.x - a.x, b.y - a.y)) - 90)
    return best[1]


# ---------------------------------------------------------------- plaza (painted, denser)
P = 'plaza'
put('Brush_Big', -13.5, 21.0, 200, 1.0, P, tag="the fallen brush beside the picture boards")
put('PaintPot', -11.8, 19.6, 30, 1.0, P)
put('PaintPot', -4.6, 24.6, 0, 1.0, P)
for (x, z, yaw) in ((-15.5, 17.0, 120), (15.5, 17.5, 240), (-16.0, 2.5, 60), (16.0, 2.5, 300)):
    put('Banner_Unfinished', x, z, yaw, 1.0, P)
for (x, z, yaw) in ((-6.0, 24.8, 90), (6.0, 24.8, 270), (-14.5, 9.0, 90), (14.5, 9.5, 270), (0.0, -6.5, 0)):
    put('Lantern_Hanging', x, z, yaw, 1.0, P)
for (m, x, z, yaw) in (('Barrel', -7.4, 23.6, 0), ('Crate', -8.3, 22.6, 20), ('Crate', -8.1, 23.6, 5), ('Barrel', 7.2, 23.8, 0),
                       ('Crate', 8.2, 22.9, -15), ('Barrel', 3.8, 25.6, 0), ('Crate', -3.6, 25.8, 10)):
    put(m, x, z, yaw, 1.0, P, search=1.5)
for (x, z) in ((-13.5, 12.5), (13.8, 13.0), (-9.5, -2.0), (9.5, -2.0)):
    put('Bench_Puppet', x, z, face((x, z), (0, 20)) + 180, 1.0, P)
put('Sketch_Arch', 0.0, -8.5, 0, 1.0, P, tag="south entrance arch, drawn only (the cart road passes beside it)")
put('Scrap_Paper_2', 11.0, 1.0, None, 1.0, P)

# ---------------------------------------------------------------- fall + gate: slice-1 dioramas (ouat_slice.SLICE_DRESSING)
for (m, x, z, yaw, sc, area, note) in SL.SLICE_DRESSING:
    it = {'model': m, 'pos': [x, z], 'yaw': yaw, 'scale': sc, 'place': area[2:], 'area': area}
    if note:
        it['note'] = note
    placed.append(it)


# ---------------------------------------------------------------- alley (cramped)
A = 'alley'
for (m, x, z) in (('Barrel', 14.2, 35.6), ('Crate', 18.6, 36.0), ('Barrel', 23.0, 36.2), ('Crate', 27.4, 36.0), ('PaintPot', 31.8, 35.5),
                  ('Crate', 14.2, 16.2), ('Barrel', 18.6, 16.0), ('Basket', 23.0, 16.4), ('Crate', 27.4, 16.0), ('Barrel', 31.8, 16.3)):
    put(m, x, z, None, 1.0, A, search=1.6)
put('Lantern_Hanging', 37.5, 27.5, 270, 1.0, A)
put('Lantern_Hanging', 9.0, 27.0, 90, 1.0, A)
put('Sketch_Fence_1', 22.0, 39.5, 0, 1.0, A)
put('Sketch_Wall_2', 38.5, 33.5, 250, 1.0, A)
put('Sketch_Wall_3', 6.0, 35.0, 100, 1.0, A)

# ---------------------------------------------------------------- field
FI = 'field'
put('Basket', 35.5, 1.5, None, 1.0, FI, tag="kid's basket")
put('Basket', 46.5, 2.0, None, 1.0, FI)
put('Crate', 27.0, 3.0, None, 1.0, FI)
put('Crate', 28.0, 2.0, 30, 1.0, FI)
for (x, z, yaw) in ((26.0, -14.0, 70), (36.0, -16.0, 95), (54.0, 6.0, 40), (54.0, -4.0, 110), (26.0, 10.0, 60)):
    put(rnd.choice(('Sketch_Fence_1', 'Sketch_Fence_2')), x, z, yaw, 1.0, FI)
put('Sketch_Tree_2', 56.0, 10.0, None, 1.0, FI)
put('Sketch_Tree_1', 24.0, -18.0, None, 1.0, FI)
for (x, z) in ((32.0, -9.5), (47.5, -2.0), (42.0, 13.0)):
    put(rnd.choice(('Scrap_Paper_2', 'Scrap_Paper_3')), x, z, None, 1.0, FI, search=2.0)
put('Rubble_1', 52.0, 2.0, None, 1.0, FI)

# ---------------------------------------------------------------- pond
PO = 'pond'
put('Sketch_Tree_3', 66.5, -11.0, None, 1.2, PO)
put('Sketch_Tree_3', 63.5, -28.0, None, 1.0, PO)
put('Sketch_Wall_3', 69.0, -21.0, 260, 1.0, PO)
put('Rubble_2', 47.0, -26.0, None, 1.0, PO)
put('Scrap_Paper_1', 60.0, -9.0, None, 1.0, PO)
put('Scrap_Paper_2', 50.5, -16.5, None, 1.0, PO, search=2.0)

# ---------------------------------------------------------------- outskirts: sparse, intentional unfinished drawing
O = 'margin'
# page margins: unfinished-drawing scenery framing every area just outside its walkable edge
margin_models = ['Sketch_Tree_1', 'Sketch_Tree_2', 'Sketch_Tree_3', 'Sketch_Wall_1', 'Sketch_Wall_2', 'Sketch_Wall_3',
                 'Sketch_Fence_1', 'Sketch_Fence_2', 'Rubble_1', 'Rubble_2', 'Scrap_Paper_2', 'Stair_Sketch', 'Sketch_Arch']
for a in [a_ for a_ in AR.AREAS if a_['id'] not in AR.SLICE_IDS]:
    per = {'a_fall': 4, 'a_gate': 7, 'a_cart': 14, 'a_plaza': 5, 'a_alley': 5, 'a_field': 9}[a['id']]
    nput, tries = 0, 0
    chains = AR.contour_chains(a, 5.2, step=2.0) + AR.contour_chains(a, 7.0, step=2.5)
    flat = [p for ch in chains for p in ch]
    rnd.shuffle(flat)
    for q in flat:
        if nput >= per:
            break
        if a['id'] == 'a_fall' or a['id'] == 'a_cart' and AR.in_chasm(q):
            continue
        m = rnd.choice(margin_models)
        g = AR.grad(a, q)
        yaw = math.degrees(math.atan2(g.x, g.y)) + 180    # face the page
        if ok(m, q.x, q.y) and AR.area_of((q.x, q.y)) == a['id']:
            put(m, q.x, q.y, yaw, rnd.uniform(0.9, 1.15), short_place(a['id']) if False else O)
            nput += 1
quota = {'a_fall': 5, 'a_gate': 6, 'a_cart': 10, 'a_plaza': 4, 'a_alley': 4, 'a_field': 6}
for a in [a_ for a_ in AR.AREAS if a_['id'] not in AR.SLICE_IDS]:
    b = a['bounds']
    n = 0
    for k in range(800):
        if n >= quota[a['id']]:
            break
        x, z = rnd.uniform(b[0] - 7, b[1] + 7), rnd.uniform(b[2] - 7, b[3] + 7)
        sdv = AR.sd_area(a, V((x, z)))
        if sdv < 1.5 or sdv > 6.5 or AR.area_of((x, z)) != a['id']:
            continue
        m = rnd.choice(('Scrap_Paper_1', 'Scrap_Paper_2', 'Scrap_Paper_3', 'Rubble_1', 'Sketch_Tree_3', 'Scrap_Paper_2', 'Rubble_2'))
        if ok(m, x, z):
            put(m, x, z, None, rnd.uniform(0.9, 1.2), O)
            n += 1

out = {'_doc': 'Dressing placements in Unity world coords: pos = [x, z] (place on the ground with a downward raycast), yaw = degrees '
               'around Y (0 = model front +Z), scale = uniform. Models are Assets/Game/Art/Models/<model>.fbx. Generated by '
               'art/blender/make_layout.py; zones (+2 m), roads (+1 m), cart road, mesa cliff, ladder notch, pond and SceneBuilder '
               'placements, page-edge blockers and exit paths are kept clear; area = chapter1.json areas[] id the item belongs to (smallest signed distance). Lantern_Hanging needs a point light at its lamp (local 0.6 m out, 2.45 m up).',
       'count': len(placed), 'items': placed}
p = os.path.join(os.path.dirname(HERE), 'layout_dressing.json')
json.dump(out, open(p, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
from collections import Counter
print('LAYOUT', len(placed), dict(Counter(i['area'] for i in placed)))
