# -*- coding: utf-8 -*-
"""Level_Ch1: the whole chapter-1 terrain as one crafted environment.
All layout is written in UNITY world coords (x, z) on the ground plane, y up; converted to Blender as (-x, -z, y).
The asset root sits at the world origin, so once placed at (0,0,0) in Unity every coordinate matches chapter1.json.

Children: Ground_Walk (all walkable ground), Ground_Lines (ink line decals: hex paving, furrows, cracks, ruts),
Cliffs (non-walkable steep faces: fall mesa, ladder notch walls, gate pass outcrops, alley backs),
Walls_Bound (cave boundary that dissolves into construction lines), Ceiling (with the hole above the fall), Backdrop (spires)."""
import math, random, json, os
import bmesh
from mathutils import Vector
from mathutils.geometry import delaunay_2d_cdt
import ouat_lib as L
from ouat_lib import Part, Asset, nval, nvec, stroke

V = Vector
HERE = os.path.dirname(os.path.abspath(__file__))
CH1 = os.path.join(os.path.dirname(os.path.dirname(HERE)), 'Unity', 'Assets', 'Game', 'Resources', 'Chapter1', 'chapter1.json')

# ground materials (no inverted-hull outline on big ground; lines are geometry)
L.MATS.update({
    'M_Ground':        ('F1EEE6', 'C9CCCF', False, 'paper',   {'hatch': True, 'note': 'unpainted walkable ground (outskirts, fall mesa top)'}),
    'M_GroundRoad':    ('EAE6DC', 'B2B6BB', False, 'paper',   {'hatch': True, 'note': 'roads: a shade darker than paper so paths read from the high camera'}),
    'M_GroundPainted': ('E2CFAA', 'BBA27C', False, 'painted', {'note': 'plaza: the painted theatre square (fully drawn)'}),
    'M_GroundEarth':   ('D2BE9C', 'A8936F', False, 'painted', {'note': 'field: furrowed earth, half painted'}),
    'M_Cliff':         ('E6E4DE', '9EA3A8', True,  'paper',   {'hatch': True, 'note': 'cliff and outcrop faces (shade band hatched)'}),
    'M_WallRock':      ('E9E7E1', 'A3A8AE', False, 'paper',   {'hatch': True, 'note': 'cave boundary walls (solid lower part)'}),
    'M_Ceiling':       ('C6CDD6', 'B4BCC6', False, 'line',    {'note': 'cave ceiling underside: flat unlit pale grey-blue (reads as blank paper sky), mostly out of view. No shadows from it.'}),
    'M_PlazaStone1':   ('EAD9B6', 'C7B08A', False, 'painted', {'note': 'painted hex paving stone, light'}),
    'M_PlazaStone2':   ('DDC49A', 'B79D74', False, 'painted', {'note': 'painted hex paving stone, mid'}),
    'M_PlazaStone3':   ('CFA97C', 'A88660', False, 'painted', {'note': 'painted hex paving stone, warm (near the stage)'}),
})

# ------------------------------------------------------------------ layout (Unity x, z)
FALL = V((-55.0, 30.0))
R_TOP = 11.2            # mesa top radius
MESA_H = 1.5
LADDER_TOP = V((-45.6, 27.4))
LADDER_BOT = V((-41.5, 23.8))
NOTCH_IN, NOTCH_OUT = 0.9, 1.25
GATE, PLAZA, ALLEY, FIELD, POND = V((-30, 18)), V((0, 10)), V((22, 26)), V((40, 0)), V((58, -18))
PLAZA_R = 16.0
FIELD_RX, FIELD_RZ = 15.0, 13.0
POND_R = 6.5
MAIN_ROAD = [(LADDER_BOT, 4.6), (GATE, 5.5), (PLAZA, 5.5), (ALLEY, 5.5), (FIELD, 5.5), (V((53.0, -13.0)), 5.5)]
CART_ROAD = [V((-44, 22)), V((-36, 4)), V((-28, -4)), V((0, -10)), V((30, -8)), V((36, -5))]
CART_W = 3.2
ELL_C, ELL_A, ELL_B = V((0.0, 6.0)), 88.0, 64.0     # boundary ellipse (SceneBuilder walls)


def B(x, z, y=0.0):
    """Unity (x, z, y-up) -> Blender vector."""
    return V((-x, -z, y))


def seg_dist(p, a, b):
    ab = b - a
    t = max(0.0, min(1.0, (p - a).dot(ab) / max(ab.length_squared, 1e-9)))
    return (p - (a + ab * t)).length, t


def smooth(e0, e1, x):
    t = max(0.0, min(1.0, (x - e0) / (e1 - e0)))
    return t * t * (3 - 2 * t)


def ell(p):
    """normalised boundary-ellipse radius (1 = wall line)."""
    return math.sqrt(((p.x - ELL_C.x) / ELL_A) ** 2 + ((p.y - ELL_C.y) / ELL_B) ** 2)


def load_keepouts():
    d = json.load(open(CH1, encoding='utf-8'))
    pts = []
    for z in d['zones']:
        pts.append((V(z['pos']), z.get('radius', 1.0) + 2.0, z['id']))
    for p in d['props']:
        if p['id'] in ('pond', 'light_beam'):
            continue
        pts.append((V(p['pos']), 2.5, p['id']))
    for i in d['inscriptions']:
        pts.append((V(i['pos']), 1.8, i['id']))
    for i in d.get('readables', []):
        pts.append((V(i['pos']), 1.8, i['id']))
    for n in d['npcs']:
        if n['id'] == 'fish':
            continue
        pts.append((V(n['spawn']), 2.0 + (1.5 if n.get('count', 1) > 1 else 0), n['id']))
    for pz in d['puzzles']:
        pts.append((V(pz['pos']), 2.0, pz['id']))
    return pts


KEEP = None


def road_d(p):
    """(distance to main road centre - half width, distance to cart road centre - half width)"""
    dm = 1e9
    for i in range(len(MAIN_ROAD) - 1):
        a, w = MAIN_ROAD[i]
        b = MAIN_ROAD[i + 1][0]
        d, _ = seg_dist(p, a, b)
        dm = min(dm, d - (MAIN_ROAD[i + 1][1] if i else w) / 2)
    dc = 1e9
    for i in range(len(CART_ROAD) - 1):
        d, _ = seg_dist(p, CART_ROAD[i], CART_ROAD[i + 1])
        dc = min(dc, d - CART_W / 2)
    return dm, dc


def in_field(p, rough=True):
    e = math.sqrt(((p.x - FIELD.x) / FIELD_RX) ** 2 + ((p.y - FIELD.y) / FIELD_RZ) ** 2)
    if rough:
        e += nval(V((p.x, p.y, 0)), 0.18, 4) * 0.12
    return e


def flat_mask(p):
    """1 = free to undulate, 0 = must stay flat (zones, props, roads, plaza)."""
    m = 1.0
    for c, r, _ in KEEP:
        d = (p - c).length
        m = min(m, smooth(r, r + 3.0, d))
    dm, dc = road_d(p)
    m = min(m, smooth(0.5, 3.0, dm), smooth(0.3, 2.0, dc))
    m = min(m, smooth(PLAZA_R + 0.5, PLAZA_R + 4.0, (p - PLAZA).length))
    return m


def notch_param(p):
    d, t = seg_dist(p, LADDER_TOP, LADDER_BOT)
    return d, t


_RIM = None


def mesa_r_top(theta):
    """Angular, broken-paper rim: piecewise-linear between ~26 random corners (never below R_TOP near the ladder side)."""
    global _RIM
    if _RIM is None:
        rr = random.Random(77)
        n = 26
        _RIM = [(2 * math.pi * (i + rr.uniform(-0.3, 0.3)) / n, R_TOP + rr.uniform(-0.2, 1.3)) for i in range(n)]
        _RIM.sort()
    th = theta % (2 * math.pi)
    # south-east sector (ladder notch, drawn bolt, cart-road start) stays tight so the cliff foot clears them
    d = math.atan2(math.sin(theta + 0.45), math.cos(theta + 0.45))
    if abs(d) < 0.75:
        return R_TOP - 0.1 + 0.15 * math.sin(theta * 11)
    pts = _RIM + [(_RIM[0][0] + 2 * math.pi, _RIM[0][1])]
    prev = (pts[-2][0] - 2 * math.pi, pts[-2][1])
    for a, r in pts:
        if th <= a:
            t = (th - prev[0]) / max(1e-6, a - prev[0])
            return prev[1] + (r - prev[1]) * t
        prev = (a, r)
    return R_TOP


def height(p):
    """Walkable ground height at Unity (x, z)."""
    # notch corridor overrides
    dn, tn = notch_param(p)
    if dn <= NOTCH_IN + 1e-3 and 0.0 <= tn <= 1.0:
        return MESA_H * (1.0 - tn)
    rel = p - FALL
    r = rel.length
    th = math.atan2(rel.y, rel.x)
    rt = mesa_r_top(th)
    if r < rt:
        hill = 0.75 * (1 - smooth(1.5, 7.5, r))
        flat = min(smooth(1.0, 3.0, (p - V((-58, 33))).length), smooth(3.0, 5.0, (p - V((-52, 28))).length))
        return MESA_H + hill + (0.1 * nval(V((p.x, p.y, 0)), 0.3, 1) + 0.15 * (1 - r / rt)) * flat
    if r < rt + 0.65:
        return MESA_H * (1 - (r - rt) / 0.65)
    h = 0.0
    m = flat_mask(p)
    e = ell(p)
    amp = 0.12 + 0.55 * smooth(0.55, 1.0, e)
    h += m * amp * (nval(V((p.x, p.y, 0)), 0.045, 2) + 0.5 * nval(V((p.x, p.y, 0)), 0.11, 3))
    # field furrows (ridges running roughly east-north-east)
    fe = in_field(p)
    if fe < 1.0:
        dirn = V((0.28, -0.96))
        s = p.dot(dirn)
        fm = smooth(1.0, 0.85, fe)
        fz = 1.0
        for c, r_, _ in KEEP:
            fz = min(fz, smooth(r_ - 1.0, r_ + 0.5, (p - c).length))
        fz = min(fz, smooth(0.0, 1.0, road_d(p)[1]), smooth(0.2, 1.5, road_d(p)[0]))
        h += fm * fz * 0.16 * (0.5 + 0.5 * math.cos(2 * math.pi * s / 2.2))
    # pond: Ground_Walk has a round HOLE (r = POND_R - 0.4) under Pond.fbx; around it a low lip
    dp = (p - POND).length
    if dp < POND_R + 2.0:
        if dp < POND_R + 0.3:
            return 0.0
        lip = 0.1 * math.exp(-((dp - (POND_R + 0.9)) / 0.5) ** 2)
        h = h * smooth(POND_R + 0.3, POND_R + 2.0, dp) + lip
    return h


EXTRA_POLYS = []

# ------------------------------------------------------------------ ground triangulation
def build_ground_points():
    rnd = random.Random(5)
    pts, fixed_h, edges = [], {}, []

    def add(p, h=None):
        pts.append(V((p.x, p.y)))
        if h is not None:
            fixed_h[len(pts) - 1] = h
        return len(pts) - 1

    def ring(center, rfunc, n, h_func, skip=None, closed=True):
        ids = []
        for i in range(n):
            th = 2 * math.pi * i / n
            q = center + V((math.cos(th), math.sin(th))) * rfunc(th)
            if skip and skip(q):
                ids.append(None)
                continue
            ids.append(add(q, h_func(q, th) if h_func else None))
        for i in range(n if closed else n - 1):
            a, b = ids[i], ids[(i + 1) % n]
            if a is not None and b is not None:
                edges.append((a, b))
        return ids

    def in_notch_outer(q):
        d, t = notch_param(q)
        return d < NOTCH_OUT + 0.05 and -0.05 <= t <= 1.08

    # outer boundary (slightly beyond the wall line so the walls stand on ground)
    ring(ELL_C, lambda th: 1.0 / math.sqrt((math.cos(th) / (ELL_A + 3)) ** 2 + (math.sin(th) / (ELL_B + 3)) ** 2), 160, None)
    # mesa rings: rim (top), ledge, foot
    rnd2 = random.Random(9)
    NR = 156
    ring(FALL, lambda th: mesa_r_top(th), NR, lambda q, th: MESA_H, skip=in_notch_outer)
    ring(FALL, lambda th: mesa_r_top(th) + 0.1, NR, lambda q, th: MESA_H * (0.55 + 0.08 * math.sin(th * 9)), skip=in_notch_outer)
    ring(FALL, lambda th: mesa_r_top(th) + 0.42 + 0.06 * math.sin(th * 13), NR, lambda q, th: MESA_H * (0.5 + 0.08 * math.sin(th * 9)), skip=in_notch_outer)
    ring(FALL, lambda th: mesa_r_top(th) + 0.52 + 0.06 * math.sin(th * 13), NR, lambda q, th: 0.0, skip=in_notch_outer)
    # notch corridor: inner floor edges + outer wall-top edges
    ax = (LADDER_BOT - LADDER_TOP).normalized()
    nrm = V((-ax.y, ax.x))
    n_steps = 14
    for side in (-1, 1):
        inner, outer = [], []
        for i in range(n_steps + 1):
            t = i / n_steps
            c = LADDER_TOP.lerp(LADDER_BOT, t)
            inner.append(add(c + nrm * NOTCH_IN * side, MESA_H * (1 - t)))
            qo = c + nrm * NOTCH_OUT * side
            rq = (qo - FALL).length
            th = math.atan2((qo - FALL).y, (qo - FALL).x)
            rt = mesa_r_top(th)
            ho = MESA_H if rq < rt else 0.0
            outer.append(add(qo, ho))
        for i in range(n_steps):
            edges.append((inner[i], inner[i + 1]))
            edges.append((outer[i], outer[i + 1]))
        for i in range(1, n_steps):
            c = LADDER_TOP.lerp(LADDER_BOT, i / n_steps)
    for i in range(n_steps + 1):   # corridor centre line samples
        add(LADDER_TOP.lerp(LADDER_BOT, i / n_steps), MESA_H * (1 - i / n_steps))
    # plaza ring and pond rings (crisp material edges / basin)
    ring(PLAZA, lambda th: PLAZA_R, 72, None)
    ring(POND, lambda th: POND_R - 0.4, 64, None)
    ring(POND, lambda th: POND_R + 0.3, 64, None)
    ring(POND, lambda th: POND_R + 0.9, 48, None)
    # road edges as constraint lines (crisp road material)
    def road_edges(poly, widths):
        for i in range(len(poly) - 1):
            a, b = poly[i], poly[i + 1]
            w = widths[i]
            d = (b - a)
            ln = d.length
            u = d.normalized()
            n = V((-u.y, u.x))
            k = max(2, int(ln / 3.0))
            for side in (-1, 1):
                prev = None
                for j in range(k + 1):
                    q = a + u * (ln * j / k) + n * (w / 2) * side
                    if (q - FALL).length < mesa_r_top(math.atan2((q - FALL).y, (q - FALL).x)) + 1.4:
                        prev = None
                        continue
                    idx = add(q)
                    if prev is not None:
                        edges.append((prev, idx))
                    prev = idx
    road_edges([p for p, _ in MAIN_ROAD], [MAIN_ROAD[i + 1][1] if i else MAIN_ROAD[0][1] for i in range(len(MAIN_ROAD) - 1)])
    road_edges(CART_ROAD, [CART_W] * (len(CART_ROAD) - 1))
    # extra constraint polylines (area boundaries, exit corridors) registered by ouat_areas
    for poly, closed in EXTRA_POLYS:
        ids = []
        for q in poly:
            rel = q - FALL
            rq = rel.length
            rt = mesa_r_top(math.atan2(rel.y, rel.x))
            if rt - 0.4 < rq < rt + 1.0 or in_notch_outer(q):
                ids.append(None)
                continue
            ids.append(add(q))
        n = len(ids)
        for i in range(n if closed else n - 1):
            a, b = ids[i], ids[(i + 1) % n]
            if a is not None and b is not None:
                edges.append((a, b))
    # fill points: base grid, denser in the field, on the mesa and near the pond
    def blocked(q):
        rel = q - FALL
        rq = rel.length
        rt = mesa_r_top(math.atan2(rel.y, rel.x))
        if rt - 0.35 < rq < rt + 1.0:
            return True
        if in_notch_outer(q):
            return True
        if ell(q) > 1.02:
            return True
        return False
    step = 2.6
    x = -ELL_A - 3
    while x < ELL_A + 3:
        z = ELL_C.y - ELL_B - 3
        while z < ELL_C.y + ELL_B + 3:
            q = V((x + rnd.uniform(-0.6, 0.6), z + rnd.uniform(-0.6, 0.6)))
            fe = in_field(q, False)
            dense = fe < 1.15 or (q - FALL).length < R_TOP + 4 or (q - POND).length < POND_R + 4
            if not blocked(q):
                add(q)
            if dense:
                for ox, oz in ((step / 2, 0), (0, step / 2), (step / 2, step / 2)):
                    q2 = V((x + ox + rnd.uniform(-0.3, 0.3), z + oz + rnd.uniform(-0.3, 0.3)))
                    if not blocked(q2):
                        add(q2)
            z += step
        x += step
    return pts, fixed_h, edges


def build_ground():
    pts, fixed_h, edges = build_ground_points()
    vco = [(p.x, p.y) for p in pts]
    res = delaunay_2d_cdt(vco, edges, [], 0, 1e-4, True)
    out_v, out_e, out_f, orig_v = res[0], res[1], res[2], res[3]
    heights = []
    for i, co in enumerate(out_v):
        ov = orig_v[i]
        h = None
        for o in ov:
            if o in fixed_h:
                h = fixed_h[o]
                break
        if h is None:
            h = height(V((co[0], co[1])))
        heights.append(h)
    walk, cliff = [], []
    for f in out_f:
        if len(f) != 3:
            continue
        a, b, c = [V((out_v[i][0], out_v[i][1])) for i in f]
        cen = (a + b + c) / 3
        if ell(cen) > 1.05 or (cen - POND).length < POND_R - 0.4:
            continue
        P = [B(out_v[i][0], out_v[i][1], heights[i]) for i in f]
        n = (P[1] - P[0]).cross(P[2] - P[0])
        if n.length < 1e-9:
            continue
        n.normalize()
        if n.z < 0:
            f = (f[0], f[2], f[1])
            n = -n
        rel = cen - FALL
        rq = rel.length
        rt = mesa_r_top(math.atan2(rel.y, rel.x))
        in_ann = (rt - 0.02 < rq < rt + 0.56) and notch_param(cen)[0] > NOTCH_IN + 0.02
        (cliff if (in_ann or n.z < math.cos(math.radians(42))) else walk).append(f)
    return out_v, heights, walk, cliff


def ground_material(c):
    """c: Unity (x, z) centre of a walkable triangle."""
    if (c - POND).length < POND_R + 0.35:
        return 'M_Cliff'
    if (c - PLAZA).length < PLAZA_R:
        return 'M_GroundPainted'
    rel = c - FALL
    if rel.length < mesa_r_top(math.atan2(rel.y, rel.x)) + 0.2:
        return 'M_Ground'
    dm, dc = road_d(c)
    if dm < 0 or dc < 0:
        return 'M_GroundRoad'
    return 'M_Ground'


def mesh_from_tris(verts, heights, tris, matfn, uv=True):
    bm = bmesh.new()
    vmap = {}
    for f in tris:
        for i in f:
            if i not in vmap:
                vmap[i] = bm.verts.new(B(verts[i][0], verts[i][1], heights[i]))
    uvl = bm.loops.layers.uv.new('UVMap') if uv else None
    mats = []
    for f in tris:
        try:
            face = bm.faces.new([vmap[i] for i in f])
        except ValueError:
            continue
        c = V((sum(verts[i][0] for i in f) / 3, sum(verts[i][1] for i in f) / 3))
        m = matfn(c)
        face.material_index = 0
        face[L.bmesh.types.BMFace] if False else None
        face.smooth = True
        face.tag = False
        face.material_index = (mats.index(m) if m in mats else (mats.append(m) or len(mats) - 1))
        if uv:
            for lp in face.loops:
                lp[uvl].uv = (lp.vert.co.x / 8.0, lp.vert.co.y / 8.0)   # world-space UV (8 m tiling) for paper grain
    bm.normal_update()
    return bm, mats


# ------------------------------------------------------------------ line decals on the ground
def ribbon(bm, pts3, w):
    """flat ink strip on the ground through Blender points (lying flat, facing +Z)."""
    if len(pts3) < 2:
        return
    left, right = [], []
    for i, p in enumerate(pts3):
        a = pts3[max(0, i - 1)]
        b = pts3[min(len(pts3) - 1, i + 1)]
        d = (b - a)
        d.z = 0
        if d.length < 1e-6:
            d = V((1, 0, 0))
        d.normalize()
        n = V((-d.y, d.x, 0))
        taper = 1.0 if 0 < i < len(pts3) - 1 else 0.45
        left.append(bm.verts.new(p + n * w * 0.5 * taper))
        right.append(bm.verts.new(p - n * w * 0.5 * taper))
    for i in range(len(pts3) - 1):
        bm.faces.new((right[i], right[i + 1], left[i + 1], left[i]))


def gp(x, z, lift=0.025):
    return B(x, z, height(V((x, z))) + lift)


SUN = V((0.44, -0.63)).normalized()     # Blender XY direction toward the light (matches preview sun); faces away get hatch


def tick(bm, x, z, ang, ln, w=0.04, lift=0.02):
    p0 = V((x, z))
    p1 = p0 + V((math.cos(ang), math.sin(ang))) * ln
    ribbon(bm, [gp(p0.x, p0.y, lift), gp(p1.x, p1.y, lift)], w)


def build_lines():
    """Returns (ink, hatch, tiles, paint) bmeshes. tiles = painted hex stones (walkable, part of Ground_Walk);
    paint = brushed earth strips in the field (decal)."""
    rnd = random.Random(21)
    bm_ink, bm_hatch, bm_tiles, bm_paint = bmesh.new(), bmesh.new(), bmesh.new(), bmesh.new()
    stage = V((0.0, 20.0))
    # ---- hex paving: painted stones in the plaza, thinning along the roads; outlines fade and break outward
    R = 0.85
    dx, dz = 1.5 * R, math.sqrt(3) * R
    for qi in range(-80, 80):
        for ri in range(-60, 60):
            cx = qi * dx
            cz = ri * dz + (dz / 2 if qi % 2 else 0)
            c = V((cx, cz))
            if abs(cx) > 75 or abs(cz - 6) > 55:
                continue
            dm, dc = road_d(c)
            dpl = (c - PLAZA).length
            if dpl < PLAZA_R - 0.6:
                keep = 0.98 - 0.2 * smooth(PLAZA_R - 4, PLAZA_R, dpl)
                fill = 0.93 - 0.35 * smooth(PLAZA_R - 6, PLAZA_R, dpl)
            elif dm < -0.3:
                far = (c - PLAZA).length
                keep = 0.9 * (1 - smooth(20, 75, far)) + 0.1
                fill = 0.75 * (1 - smooth(PLAZA_R, 34, far))
                if dm > -1.0:
                    keep *= 0.6
            elif dm < 1.0 and rnd.random() < 0.2:
                keep, fill = 0.3, 0.0
            else:
                continue
            rel = c - FALL
            if rel.length < mesa_r_top(math.atan2(rel.y, rel.x)) + 1.0 or (c - POND).length < POND_R + 1.5:
                continue
            if rnd.random() < fill:
                tone = 'M_PlazaStone3' if (c - stage).length < 7 + rnd.uniform(-2, 2) else ('M_PlazaStone2' if nval(V((cx, cz, 0)), 0.35, 6) + rnd.uniform(-0.3, 0.3) > 0.1 else 'M_PlazaStone1')
                hgt = height(c) + 0.02 + rnd.uniform(-0.004, 0.006)
                inset = 0.9
                vs = [bm_tiles.verts.new(B(cx + math.cos(math.radians(60 * k)) * R * inset, cz + math.sin(math.radians(60 * k)) * R * inset, hgt)) for k in range(6)]
                f = bm_tiles.faces.new(list(reversed(vs)))
                f.material_index = {'M_PlazaStone1': 0, 'M_PlazaStone2': 1, 'M_PlazaStone3': 2}[tone]
            for k in range(3):
                if rnd.random() > keep:
                    continue
                a0 = math.radians(60 * k)
                a1 = math.radians(60 * (k + 1))
                p0 = c + V((math.cos(a0), math.sin(a0))) * R
                p1 = c + V((math.cos(a1), math.sin(a1))) * R
                g = 0.06 + rnd.uniform(0, 0.1) * (1 + 2 * (1 - keep))
                q0, q1 = p0.lerp(p1, g), p1.lerp(p0, g * rnd.uniform(0.5, 1.5))
                ribbon(bm_ink, [gp(q0.x, q0.y, 0.035), gp(q1.x, q1.y, 0.035)], 0.075 if dpl < PLAZA_R else 0.065)
    # plaza rim: a confident double circle, the outer one broken into strokes
    for k, rr in enumerate((PLAZA_R, PLAZA_R + 0.4)):
        pts = []
        for i in range(0, 145):
            th = 2 * math.pi * i / 144
            j = 0.05 * math.sin(th * 13 + k)
            pts.append(gp(PLAZA.x + math.cos(th) * (rr + j), PLAZA.y + math.sin(th) * (rr + j), 0.04))
        if k == 0:
            ribbon(bm_ink, pts, 0.14)
        else:
            for st in range(0, 144, 9):
                ribbon(bm_ink, pts[st:st + 7], 0.055)
    # ---- field: brushed earth strips along the furrow crests (half painted) + ink furrow lines
    dirn = V((0.28, -0.96))
    along = V((-dirn.y, dirn.x))
    for k in range(-14, 15):
        s0 = FIELD.dot(dirn) + k * 2.2
        pts = []
        for j in range(-34, 35):
            q = dirn * s0 + along * (FIELD.dot(along) + j * 0.8)
            ok = in_field(q) < 0.97 and flat_mask(q) > 0.05 and road_d(q)[1] > 0.4 and road_d(q)[0] > 0.2
            if ok:
                pts.append(q)
            if (not ok or j == 34) and len(pts) > 2:
                ribbon(bm_ink, [gp(p.x, p.y, 0.03) for p in pts], 0.09)
                # paint strip: brushed on from the west end, stopping at a ragged point
                stop = int(len(pts) * rnd.uniform(0.35, 0.95))
                if stop > 2:
                    ribbon(bm_paint, [gp(p.x + dirn.x * 0.35, p.y + dirn.y * 0.35, 0.022) for p in pts[:stop]], rnd.uniform(0.7, 1.1))
                pts = []
            elif not ok:
                pts = []
    # ---- cart ruts: two dashed wheel tracks
    for side in (-0.55, 0.55):
        for i in range(len(CART_ROAD) - 1):
            a, b = CART_ROAD[i], CART_ROAD[i + 1]
            u = (b - a).normalized()
            n = V((-u.y, u.x))
            ln = (b - a).length
            t = 0.0
            while t < ln:
                d = rnd.uniform(1.5, 3.5)
                q0 = a + u * t + n * side
                q1 = a + u * min(ln, t + d) + n * (side + rnd.uniform(-0.05, 0.05))
                ribbon(bm_ink, [gp(q0.x, q0.y, 0.03), gp((q0.x + q1.x) / 2, (q0.y + q1.y) / 2, 0.03), gp(q1.x, q1.y, 0.03)], 0.08)
                t += d + rnd.uniform(0.2, 1.0)
    # ---- grass ticks: clustered near paths and places, thinning toward the page edge
    centres = [GATE, PLAZA, ALLEY, FIELD, POND, FALL]
    for i in range(2200):
        q = V((rnd.uniform(-84, 84), rnd.uniform(-56, 68)))
        e = ell(q)
        if e > 0.92:
            continue
        dm, dc = road_d(q)
        near = min([(q - c).length for c in centres] + [abs(dm) + 3, abs(dc) + 3])
        dens = (1 - smooth(4, 26, near)) * (1 - smooth(0.6, 0.9, e))
        if rnd.random() > dens or flat_mask(q) < 0.3 or dm < 0.5 or dc < 0.5 or (q - PLAZA).length < PLAZA_R + 0.5 or in_field(q) < 1.0:
            continue
        rel = q - FALL
        if rel.length < mesa_r_top(math.atan2(rel.y, rel.x)) + 1.2:
            continue
        for t in range(rnd.randint(3, 5)):
            ang = math.radians(90 + rnd.uniform(-35, 35))
            ox = rnd.uniform(-0.15, 0.15)
            tick(bm_ink, q.x + ox, q.y, ang, rnd.uniform(0.2, 0.4), 0.05)
    # ---- cracks: a few near the centre, longer and rarer toward the edge
    for i in range(380):
        q = V((rnd.uniform(-84, 84), rnd.uniform(-56, 68)))
        e = ell(q)
        if e > 0.95 or rnd.random() > 0.2 + 0.6 * smooth(0.3, 0.8, e) * (1 - smooth(0.85, 0.95, e)):
            continue
        if flat_mask(q) < 0.6:
            continue
        rel = q - FALL
        if rel.length < mesa_r_top(math.atan2(rel.y, rel.x)) + 1.5:
            continue
        ang = rnd.uniform(0, math.pi)
        ln = rnd.uniform(0.8, 2.0) + 2.5 * e
        pts, cur = [], q
        for j in range(5):
            pts.append(gp(cur.x, cur.y, 0.025))
            ang += rnd.uniform(-0.6, 0.6)
            cur = cur + V((math.cos(ang), math.sin(ang))) * ln / 4
        ribbon(bm_ink, pts, 0.07 + 0.03 * e)
        if rnd.random() < 0.5:   # a branch
            b0 = pts[2]
            br = V((-b0.x, -b0.y)) + V((math.cos(ang + 1.2), math.sin(ang + 1.2))) * ln * 0.35
            ribbon(bm_ink, [b0 + V((0, 0, 0)), gp(br.x, br.y, 0.025)], 0.035)
    # ---- mesa top: scratches and torn-page outlines around the fallen pile (lit by the shaft)
    for i in range(40):
        a = rnd.uniform(0, 2 * math.pi)
        r = rnd.uniform(3.0, 10.0)
        q = FALL + V((math.cos(a), math.sin(a))) * r
        if any((q - kc).length < kr for kc, kr, _ in KEEP if (kc - FALL).length < 13):
            continue
        if notch_param(q)[0] < 1.6:
            continue
        ang = rnd.uniform(0, math.pi)
        ln = rnd.uniform(0.5, 1.4)
        tick(bm_ink, q.x, q.y, ang, ln, 0.04, 0.03)
    # ---- drawn flagstones / cracked paper slabs around the places (designed density falloff)
    places = [(FALL, 11.5, 0.9), (GATE, 11.0, 1.0), (ALLEY, 11.0, 1.0), (POND, 11.0, 0.8), (FIELD, 17.0, 0.35)]
    RS = 1.3
    dxs, dzs = 1.5 * RS, math.sqrt(3) * RS

    def jv(p):
        k = V((round(p.x, 2), round(p.y, 2), 0))
        return p + nvec(k, 0.9, 5).to_2d() * RS * 0.32

    for qi in range(-60, 60):
        for ri in range(-36, 42):
            c = V((qi * dxs, ri * dzs + (dzs / 2 if qi % 2 else 0)))
            w = 0.0
            for pc, rr, k in places:
                w = max(w, k * (1 - smooth(rr * 0.4, rr * 1.15, (c - pc).length)))
            if w <= 0.02:
                continue
            dm, dc = road_d(c)
            if (c - PLAZA).length < PLAZA_R + 1.0 or dm < 0.0 or dc < 0.0 or (c - POND).length < POND_R + 1.2:
                continue
            if in_field(c) < 1.0 and (c - FALL).length > 20:
                w *= 0.3
            for kk in range(3):
                if rnd.random() > w:
                    continue
                a0 = math.radians(60 * kk)
                a1 = math.radians(60 * (kk + 1))
                p0 = jv(c + V((math.cos(a0), math.sin(a0))) * RS)
                p1 = jv(c + V((math.cos(a1), math.sin(a1))) * RS)
                mid = (p0 + p1) / 2
                rel = mid - FALL
                rt = mesa_r_top(math.atan2(rel.y, rel.x))
                if rt - 0.5 < rel.length < rt + 1.2 or notch_param(mid)[0] < 1.6 or road_d(mid)[0] < 0.1:
                    continue
                g = rnd.uniform(0.05, 0.18)
                q0, q1 = p0.lerp(p1, g), p1.lerp(p0, rnd.uniform(0.05, 0.18))
                ribbon(bm_ink, [gp(q0.x, q0.y, 0.03), gp(mid.x + rnd.uniform(-0.05, 0.05), mid.y + rnd.uniform(-0.05, 0.05), 0.03), gp(q1.x, q1.y, 0.03)], 0.05)
    # ---- page vignette: pencil hatching thickens toward the boundary; mesa foot shadow hatching
    for i in range(1500):
        th = rnd.uniform(0, 2 * math.pi)
        e = 0.8 + 0.2 * math.sqrt(rnd.random())
        q = ELL_C + V((math.cos(th) * ELL_A * e, math.sin(th) * ELL_B * e))
        if rnd.random() > smooth(0.8, 0.97, e):
            continue
        if flat_mask(q) < 0.5:
            continue
        ln = rnd.uniform(0.6, 1.4)
        p1 = q + V((0.6, 0.8)) * ln
        ribbon(bm_hatch, [gp(q.x, q.y, 0.025), gp(p1.x, p1.y, 0.025)], 0.04)
    for i in range(160):
        th = rnd.uniform(-1.2, 2.2)
        rq = mesa_r_top(th) + 0.7 + rnd.uniform(0, 1.6)
        q = FALL + V((math.cos(th), math.sin(th))) * rq
        if flat_mask(q) < 0.4 or notch_param(q)[0] < 2.0:
            continue
        p1 = q + V((0.6, 0.8)) * rnd.uniform(0.5, 1.1)
        ribbon(bm_hatch, [gp(q.x, q.y, 0.025), gp(p1.x, p1.y, 0.025)], 0.04)
    return bm_ink, bm_hatch, bm_tiles, bm_paint


# ------------------------------------------------------------------ cliffs extras (ink rim, hatch on faces, outcrops)
def outcrop(bm_solid, bm_ink, bm_hatch, poly, h, seed, tiers=2):
    """Walk-blocking paper-stone outcrop drawn like the concept ledges: stacked jagged tiers, flat paper tops,
    vertical sides, confident ink outlines on every top edge, corner verticals, hatch only on faces away from the light."""
    rnd = random.Random(seed)
    cx = sum(p.x for p in poly) / len(poly)
    cz = sum(p.y for p in poly) / len(poly)
    OUTCROPS.append((V((cx, cz)), max((p - V((cx, cz))).length for p in poly)))
    cur = poly
    z0 = -0.3
    for t in range(tiers):
        ht = h * (0.55 if tiers > 1 and t == 0 else (0.45 if tiers > 1 else 1.0))
        z1 = (h if t == tiers - 1 else z0 + 0.3 + ht) if t else 0.0 + ht
        z1 = h * (t + 1) / tiers + rnd.uniform(-0.15, 0.15)
        n = len(cur)
        bot = [bm_solid.verts.new(B(p.x, p.y, z0)) for p in cur]
        top = [bm_solid.verts.new(B(p.x, p.y, z1)) for p in cur]
        for i in range(n):
            j = (i + 1) % n
            f = bm_solid.faces.new((bot[i], bot[j], top[j], top[i]))
        try:
            bm_solid.faces.new(top)
        except ValueError:
            pass
        # ink: top outline (slightly overshooting), some vertical corners
        pts = [top[i].co + V((0, 0, 0.02)) for i in range(n)] + [top[0].co + V((0, 0, 0.02))]
        rib_vertical(bm_ink, pts, 0.1)
        for i in range(n):
            if rnd.random() < 0.55:
                rib_vertical(bm_ink, [bot[i].co + V((0, 0, 0.32 if t == 0 else 0.02)), top[i].co + V((0, 0, rnd.uniform(0.0, 0.15)))], 0.05)
        # hatch on shadow faces
        for i in range(n):
            j = (i + 1) % n
            a, b = top[i].co, top[j].co
            d = (b - a)
            d.z = 0
            if d.length < 0.2:
                continue
            nrm = V((d.y, -d.x)).normalized()
            if nrm.dot(SUN) > -0.05:
                continue
            cnt = int(d.length / 0.22)
            for k in range(cnt):
                tt = (k + 0.5) / cnt
                p = bot[i].co.lerp(bot[j].co, tt) + V((0, 0, (0.35 if t == 0 else 0.05) + rnd.uniform(0, 0.15)))
                q = p + d.normalized() * 0.28 + V((0, 0, (z1 - z0) * rnd.uniform(0.45, 0.8)))
                off = V((nrm.x, nrm.y, 0)) * 0.015
                rib_vertical(bm_hatch, [p + off, q + off], 0.035)
        # next tier: shrink toward a shifted centre
        sx, sz = cx + rnd.uniform(-0.4, 0.4), cz + rnd.uniform(-0.4, 0.4)
        k = rnd.uniform(0.55, 0.75)
        cur = [V((sx + (p.x - cx) * k + rnd.uniform(-0.15, 0.15), sz + (p.y - cz) * k + rnd.uniform(-0.15, 0.15))) for p in cur]
        z0 = z1 - 0.05


def rib_vertical(bm, pts, w):
    """ribbon facing horizontally (for lines on vertical faces): width along the cross of segment and up."""
    for i in range(len(pts) - 1):
        a, b = pts[i], pts[i + 1]
        d = (b - a)
        if d.length < 1e-6:
            continue
        side = d.cross(V((0, 0, 1)))
        if side.length < 1e-6:
            side = V((1, 0, 0))
        side.normalize()
        o = side * w * 0.5
        v = [bm.verts.new(a - o), bm.verts.new(b - o), bm.verts.new(b + o), bm.verts.new(a + o)]
        bm.faces.new(v)
        # second face rotated 90 deg so it reads from any side
        n2 = d.normalized().cross(side) * w * 0.5
        v2 = [bm.verts.new(a - n2), bm.verts.new(b - n2), bm.verts.new(b + n2), bm.verts.new(a + n2)]
        bm.faces.new(v2)


def jag_poly(center, rx, rz, n, seed, rot=0.0):
    rnd = random.Random(seed)
    out = []
    for i in range(n):
        th = 2 * math.pi * i / n + rnd.uniform(-0.2, 0.2)
        k = rnd.uniform(0.62, 1.2)
        x, z = math.cos(th) * rx * k, math.sin(th) * rz * k
        c, s = math.cos(rot), math.sin(rot)
        out.append(center + V((x * c - z * s, x * s + z * c)))
    return out


OUTCROPS = []


def build_cliff_extras(verts, heights, cliff_tris):
    OUTCROPS.clear()
    bm_ink, bm_hatch, bm_solid = bmesh.new(), bmesh.new(), bmesh.new()
    rnd = random.Random(31)
    # ink line along the mesa rim + ledge, vertical strokes and hatch on the cliff band
    for k, (dr, hk) in enumerate(((0.0, 1.0), (0.42, 0.5))):
        pts = []
        for i in range(0, 241):
            th = 2 * math.pi * i / 240
            q = FALL + V((math.cos(th), math.sin(th))) * (mesa_r_top(th) + dr + (0.06 * math.sin(th * 13) if k else 0))
            if notch_param(q)[0] < NOTCH_OUT + 0.1 and notch_param(q)[1] < 1.05:
                if len(pts) > 1:
                    rib_vertical(bm_ink, pts, 0.11 if k == 0 else 0.07)
                pts = []
                continue
            pts.append(B(q.x, q.y, MESA_H * hk + 0.02))
        if len(pts) > 1:
            rib_vertical(bm_ink, pts, 0.11 if k == 0 else 0.07)
    for i in range(420):
        th = rnd.uniform(0, 2 * math.pi)
        rt = mesa_r_top(th)
        q0 = FALL + V((math.cos(th), math.sin(th))) * (rt + 0.05)
        if notch_param(q0)[0] < NOTCH_OUT + 0.4:
            continue
        q1 = FALL + V((math.cos(th + 0.015), math.sin(th + 0.015))) * (rt + 0.12)
        q2 = FALL + V((math.cos(th + 0.02), math.sin(th + 0.02))) * (rt + 0.55)
        if i % 3 == 0:
            rib_vertical(bm_ink, [B(q0.x, q0.y, MESA_H - 0.05), B(q1.x, q1.y, MESA_H * 0.55)], 0.045)
        else:
            if V((math.cos(th), math.sin(th))).dot(V((-SUN.x, -SUN.y))) < 0.1:
                continue
            rib_vertical(bm_hatch, [B(q0.x, q0.y, MESA_H - 0.1), B(q1.x, q1.y, MESA_H * 0.6)], 0.035)
            rib_vertical(bm_hatch, [B(q2.x - 0.05, q2.y, MESA_H * 0.45), B(q2.x, q2.y + 0.05, 0.08)], 0.035)
    # notch walls: ink edge on both corridor sides
    ax = (LADDER_BOT - LADDER_TOP).normalized()
    nrm = V((-ax.y, ax.x))
    for side in (-1, 1):
        pts = [B(*(LADDER_TOP.lerp(LADDER_BOT, t) + nrm * NOTCH_IN * side), MESA_H * (1 - t) + 0.02) for t in (0, 0.25, 0.5, 0.75, 1.0)]
        rib_vertical(bm_ink, pts, 0.05)
    # gate: a pass framed by two long broken ridges either side of the road
    for (c, along_len, width, hgt, seed) in ((V((-30.5, 28.5)), 5.5, 2.4, 3.6, 41), (V((-38.5, 30.5)), 3.0, 2.0, 2.6, 42),
                                             (V((-27.5, 10.0)), 5.0, 2.2, 3.2, 43), (V((-21.0, 8.0)), 3.0, 1.8, 2.4, 44),
                                             (V((-37.0, 14.5)), 2.2, 1.6, 2.2, 45)):
        rd = (PLAZA - LADDER_BOT).normalized()
        poly = jag_poly(c, along_len, width, 11, seed, rot=math.atan2(rd.y, rd.x))
        bad = [kid for kc, kr, kid in KEEP if min((p - kc).length for p in poly + [c]) < kr + 0.5]
        if bad or min(min(road_d(p)) for p in poly) < 0.8:
            print('OUTCROP skipped', seed, bad)
            continue
        outcrop(bm_solid, bm_ink, bm_hatch, poly, hgt, seed, tiers=2)
    # alley: cramped backs - low broken ridges behind the house rows; field: a couple of earth banks; outskirts rocks
    spots = [(V((14, 40)), 3.0, 1.6, 2.0), (V((24, 41)), 3.5, 1.5, 2.6), (V((34, 38)), 2.8, 1.4, 1.8), (V((8, 37)), 2.2, 1.3, 1.6),
             (V((-12, 38)), 4.0, 2.2, 3.0), (V((-40, 44)), 5.0, 2.5, 3.5), (V((-70, 10)), 4.5, 3.0, 3.2), (V((-62, -14)), 5.0, 3.0, 2.8),
             (V((-20, -28)), 4.5, 2.4, 2.4), (V((10, -30)), 5.5, 2.6, 2.6), (V((70, 20)), 5.0, 3.0, 3.4), (V((62, 36)), 4.0, 2.5, 2.8),
             (V((72, -30)), 4.0, 3.0, 3.0), (V((-50, -30)), 4.0, 2.0, 2.0), (V((30, -30)), 4.0, 2.4, 2.2)]
    for i, (c, rx, rz, h) in enumerate(spots):
        if not (all((c - kc).length > kr + rx + 1.5 for kc, kr, _ in KEEP) and road_d(c)[0] > rx + 1.0 and road_d(c)[1] > rx + 1.0):
            continue
        if ell(c) > 0.93:
            continue
        outcrop(bm_solid, bm_ink, bm_hatch, jag_poly(c, rx, rz, 11, 60 + i, rot=i * 0.7), h, 60 + i, tiers=2 if h > 2.2 else 1)
    return bm_solid, bm_ink, bm_hatch


# ------------------------------------------------------------------ boundary walls
def build_walls():
    """A continuous wall band on the ellipse: solid paper up to a ragged line, then construction lines."""
    rnd = random.Random(51)
    bm_solid, bm_ink, bm_hatch = bmesh.new(), bmesh.new(), bmesh.new()
    n = 180
    cols = []
    for i in range(n):
        th = 2 * math.pi * i / n
        wob = 1.0 + 0.025 * math.sin(th * 7) + 0.02 * nval(V((th * 3, 0, 0)), 1.0, 2)
        x = ELL_C.x + math.cos(th) * ELL_A * wob
        z = ELL_C.y + math.sin(th) * ELL_B * wob
        inward = (ELL_C - V((x, z))).normalized()
        h_plan = 13.0 + 4.0 * (0.5 + 0.5 * math.sin(th * 3 + 1)) + rnd.uniform(-1, 1)
        h_solid = h_plan * (0.35 + 0.25 * (0.5 + 0.5 * math.sin(th * 5 + 2)) + rnd.uniform(-0.08, 0.08))
        cols.append((V((x, z)), inward, h_solid, h_plan))
    rows = 4
    grid = []
    for (p, inw, hs, hp) in cols:
        col = []
        for r in range(rows + 1):
            f = r / rows
            lean = inw * (1.6 * f * f)   # leans inward as it rises
            bulge = inw * (0.5 * math.sin(f * math.pi))
            q = p + lean + bulge
            col.append(bm_solid.verts.new(B(q.x, q.y, -0.3 + (hs + 0.3) * f)))
        grid.append(col)
    for i in range(n):
        j = (i + 1) % n
        for r in range(rows):
            bm_solid.faces.new((grid[i][r], grid[j][r], grid[j][r + 1], grid[i][r + 1]))
    bmesh.ops.recalc_face_normals(bm_solid, faces=bm_solid.faces)
    # make sure faces look inward
    for f in bm_solid.faces:
        c = f.calc_center_median()
        to_c = B(ELL_C.x, ELL_C.y, c.z) - c
        if f.normal.dot(to_c) < 0:
            f.normal_flip()
    # ragged ink top line of the solid part
    top = [grid[i][rows].co + V((0, 0, 0.05)) for i in range(n)] + [grid[0][rows].co + V((0, 0, 0.05))]
    rib_vertical(bm_ink, top, 0.12)
    # construction lines above: posts, courses, braces up to the planned height; dissolving
    for i in range(0, n, 2):
        p, inw, hs, hp = cols[i]
        q = p + inw * 1.6
        base = B(q.x, q.y, hs)
        if rnd.random() < 0.8:
            rib_vertical(bm_ink, [base, B(q.x + inw.x * 0.6, q.y + inw.y * 0.6, hp * rnd.uniform(0.85, 1.05))], 0.08)
        if i % 6 == 0:
            j = (i + 6) % n
            p2, inw2, hs2, hp2 = cols[j]
            q2 = p2 + inw2 * 2.0
            rib_vertical(bm_ink, [B(q.x + inw.x * 0.4, q.y + inw.y * 0.4, hp * 0.75), B(q2.x, q2.y, hp2 * 0.78)], 0.06)
            if rnd.random() < 0.5:
                rib_vertical(bm_ink, [base, B(q2.x, q2.y, hp2 * 0.95)], 0.05)
    # strata strokes and hatch on the solid face
    for i in range(n):
        p, inw, hs, hp = cols[i]
        q = p + inw * 0.6
        for k in range(2):
            z = hs * rnd.uniform(0.2, 0.85)
            j = (i + rnd.randint(1, 3)) % n
            p2, inw2, _, _ = cols[j]
            q2 = p2 + inw2 * 0.6
            rib_vertical(bm_ink if k == 0 and rnd.random() < 0.5 else bm_hatch, [B(q.x, q.y, z), B(q2.x, q2.y, z + rnd.uniform(-0.6, 0.6))], 0.06)
        if rnd.random() < 0.6:
            z = rnd.uniform(0.2, hs * 0.6)
            rib_vertical(bm_hatch, [B(q.x, q.y, z), B(q.x + inw.y * 0.4, q.y - inw.x * 0.4, z + 1.6)], 0.05)
    return bm_solid, bm_ink, bm_hatch


# ------------------------------------------------------------------ ceiling & backdrop
def ceil_h(p):
    e = ell(p)
    h = 14.0 + 24.0 * (1 - min(1.0, e) ** 3.2)
    d = (p - FALL).length
    return h + (30.0 - h) * (1 - smooth(4.0, 16.0, d))


def build_ceiling():
    bm = bmesh.new()
    nr, nt = 14, 72
    rings = []
    for r in range(nr + 1):
        f = r / nr
        ring = []
        for t in range(nt):
            th = 2 * math.pi * t / nt
            q = ELL_C + V((math.cos(th) * ELL_A * 1.03 * f, math.sin(th) * ELL_B * 1.03 * f))
            ring.append(q)
        rings.append(ring)
    vmap = {}

    def v(r, t):
        k = (r, t % nt)
        if k not in vmap:
            q = rings[r][t % nt]
            vmap[k] = bm.verts.new(B(q.x, q.y, ceil_h(q) + (0 if r == nr else nval(V((q.x, q.y, 0)), 0.08, 7) * 1.5)))
        return vmap[k]
    for r in range(nr):
        for t in range(nt):
            q = (rings[r][t] + rings[r + 1][(t + 1) % nt]) * 0.5
            if (q - FALL).length < 4.2:
                continue   # the hole above the fall
            if r == 0:
                bm.faces.new((v(0, 0), v(1, t + 1), v(1, t))) if t == 0 else bm.faces.new((v(0, 0), v(1, t + 1), v(1, t)))
            else:
                bm.faces.new((v(r, t), v(r, t + 1), v(r + 1, t + 1), v(r + 1, t)))
    for f in bm.faces:
        if f.normal.z > 0:
            f.normal_flip()      # faces down
    # hanging rock teeth around the hole
    rnd = random.Random(61)
    teeth = bmesh.new()
    for i in range(14):
        th = 2 * math.pi * i / 14 + rnd.uniform(-0.1, 0.1)
        q = FALL + V((math.cos(th), math.sin(th))) * rnd.uniform(4.6, 7.0)
        h0 = ceil_h(q)
        ln = rnd.uniform(1.5, 4.5)
        r0 = rnd.uniform(0.4, 0.9)
        b = L.bm_tube([B(q.x, q.y, h0 + 0.3), B(q.x, q.y, h0 - ln)], [r0, 0.02], seg=5)
        me = L.bpy.data.meshes.new('t'); b.to_mesh(me); teeth.from_mesh(me); L.bpy.data.meshes.remove(me); b.free()
    return bm, teeth


def build_backdrop():
    rnd = random.Random(71)
    bm = bmesh.new()
    for i in range(34):
        th = 2 * math.pi * i / 34 + rnd.uniform(-0.08, 0.08)
        k = rnd.uniform(1.12, 1.45)
        q = ELL_C + V((math.cos(th) * ELL_A * k, math.sin(th) * ELL_B * k))
        h = rnd.uniform(22, 48)
        r = h * rnd.uniform(0.12, 0.2)
        sides = rnd.choice((4, 5, 6))
        base = []
        for s in range(sides):
            a = 2 * math.pi * s / sides + rnd.uniform(0, 1)
            base.append(bm.verts.new(B(q.x + math.cos(a) * r, q.y + math.sin(a) * r, -1.0)))
        tip = bm.verts.new(B(q.x + rnd.uniform(-1, 1), q.y + rnd.uniform(-1, 1), h))
        for s in range(sides):
            bm.faces.new((base[s], base[(s + 1) % sides], tip))
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    return bm


# ------------------------------------------------------------------ assemble
def build_level():
    global KEEP
    KEEP = load_keepouts()
    A = Asset('Level_Ch1')
    verts, heights, walk, cliff = build_ground()
    bm_walk, mats_walk = mesh_from_tris(verts, heights, walk, ground_material)
    gw = Part('Ground_Walk')
    gw.add(bm_walk, mats_walk[0], True, lambda c, n: ground_material(V((-c.x, -c.y))))
    GW = gw

    ink, hatch, tiles, paint = build_lines()
    tone = ['M_PlazaStone1', 'M_PlazaStone2', 'M_PlazaStone3']
    me = L.bpy.data.meshes.new('tmp_tiles')
    tiles.to_mesh(me)
    idx = [p.material_index for p in me.polygons]
    L.bpy.data.meshes.remove(me)
    tile_c = {}
    for f in tiles.faces:
        c = f.calc_center_median()
        tile_c[(round(c.x, 2), round(c.y, 2))] = tone[f.material_index]
    GW.add(tiles, 'M_PlazaStone1', smooth=False, face_mat=lambda c, n: tile_c.get((round(c.x, 2), round(c.y, 2))))
    A.part(GW, pivot=(0, 0, 0))
    gl = Part('Ground_Lines')
    gl.add(paint, 'M_GroundEarth', smooth=False)
    gl.add(ink, 'M_Ink', smooth=False)
    gl.add(hatch, 'M_Hatch', smooth=False)
    A.part(gl, pivot=(0, 0, 0))

    bm_cliff, _ = mesh_from_tris(verts, heights, cliff, lambda c: 'M_Cliff', uv=False)
    solid, cink, chatch = build_cliff_extras(verts, heights, cliff)
    cl = Part('Cliffs')
    cl.add(bm_cliff, 'M_Cliff', smooth=False)
    cl.add(solid, 'M_Cliff', smooth=False, face_mat=lambda c, n: 'M_Ground' if n.z > 0.7 else None)
    cl.add(cink, 'M_Ink', smooth=False)
    cl.add(chatch, 'M_Hatch', smooth=False)
    A.part(cl, pivot=(0, 0, 0))

    ws, wi, wh = build_walls()
    wb = Part('Walls_Bound')
    wb.add(ws, 'M_WallRock', smooth=False)
    wb.add(wi, 'M_Ink', smooth=False)
    wb.add(wh, 'M_Hatch', smooth=False)
    A.part(wb, pivot=(0, 0, 0))

    cb, teeth = build_ceiling()
    ce = Part('Ceiling')
    ce.add(cb, 'M_Ceiling', smooth=True)
    ce.add(teeth, 'M_Ceiling', smooth=False)
    A.part(ce, pivot=(0, 0, 0))

    bd = Part('Backdrop')
    bd.add(build_backdrop(), 'M_Spire', smooth=False)
    A.part(bd, pivot=(0, 0, 0))
    A.root['ouat_size'] = 1.0
    A.meta['note'] = ('Whole chapter-1 terrain in Unity world coordinates (place the root at 0,0,0). Ground_Walk = all walkable ground '
                      '(fall mesa top y 1.5, ladder notch ramp, roads, plaza, field furrows, pond bowl -0.35). Cliffs/Walls_Bound = '
                      'non-walkable. Ground_Lines/Ceiling/Backdrop = no collider needed.')
    return A


ASSETS = [('Level_Ch1', build_level)]
