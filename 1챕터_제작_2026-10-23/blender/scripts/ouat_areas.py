# -*- coding: utf-8 -*-
"""Level_Ch1 split into page-like AREAS (chapter1.json areas[]), Chants-of-Sennaar style.
Every area = one picture-book page: walkable ground inside its shape, a paper margin where the drawing
thins out into blank paper and loose sketch lines, natural blockers along the edge, and drawn exits.

Hierarchy (Unity names; FindPart-style prefix match works):
  Level_Ch1
    Area_<id>            (empty)  e.g. Area_a_fall
      Ground_Walk_<s>    walkable (MeshCollider + NavMesh)          s = id without 'a_'
      Margin_<s>         paper margin, not walkable (no collider needed, or a non-walkable layer)
      Ground_Lines_<s>   ink/hatch/paint decals (no collider, no shadow)
      Cliffs_<s>         blockers: cliffs, ridges, banks, walls (collider / NavMesh obstacle)
      Exit_<s>_<t>       drawn exit marker (arch/sign + ink arrow + path running off the page)
    Global (empty): Ceiling, Backdrop, Walls_Bound
All coordinates = Unity world (same as before), root at origin."""
import math, random, json, os
import bmesh
from mathutils import Vector
from mathutils.geometry import delaunay_2d_cdt
import ouat_lib as L
import ouat_level as LV
from ouat_lib import Part, Asset, nval

V = Vector
import ouat_slice as SL
import ouat_slice2 as SL2
CH1 = json.load(open(LV.CH1, encoding='utf-8'))
AREAS = SL2.patch_areas(SL.patch_areas(CH1['areas']))   # slice 1 (10/23): a_fall / a_gate (ouat_slice.py); slice 2: all the rest + a_hideout (ouat_slice2.py)
AID = {a['id']: a for a in AREAS}
SLICE_IDS = ('a_fall', 'a_gate') + SL2.NEW_IDS
MARGIN = 8.0           # paper margin drawn around each page (m)


def short(aid):
    return aid[2:] if aid.startswith('a_') else aid


# ------------------------------------------------------------------ shapes
def sd_shape(sh, p):
    if 'c' in sh:
        return (p - V(sh['c'])).length - sh['r']
    pts = [V(q) for q in sh['line']]
    d = min(LV.seg_dist(p, pts[i], pts[i + 1])[0] for i in range(len(pts) - 1))
    return d - sh['w']


def sd_area(a, p):
    return min(sd_shape(sh, p) for sh in a['shape'])


def area_center(a):
    b = a['bounds']
    return V(((b[0] + b[1]) / 2, (b[2] + b[3]) / 2))


def grad(a, p, e=0.3):
    g = V((sd_area(a, p + V((e, 0))) - sd_area(a, p - V((e, 0))), sd_area(a, p + V((0, e))) - sd_area(a, p - V((0, e)))))
    return g.normalized() if g.length > 1e-6 else V((1, 0))


def exit_dir(a, ex):
    pos = V(ex['pos'])
    g = grad(a, pos)
    dc = (area_center(AID[ex['to']]) - pos).normalized()
    sp = (V(ex['spawn']) - pos)
    d = g * 0.45 + dc * 0.35 + (sp.normalized() * 0.2 if sp.length > 0.1 else V((0, 0)))
    if a['id'] == 'a_fall':
        d = (LV.LADDER_BOT - LV.LADDER_TOP).normalized()
    return d.normalized()


def exit_segment(a, ex):
    pos = V(ex['pos'])
    d = exit_dir(a, ex)
    return pos - d * 1.0, pos + d * 3.2, d


def in_exit_walk(a, p):
    for ex in a['exits']:
        s0, s1, d = exit_segment(a, ex)
        if LV.seg_dist(p, s0, s1)[0] <= 1.35:
            return True
    return False


def near_exit(a, p, r=4.2):
    for ex in a['exits']:
        s0, s1, d = exit_segment(a, ex)
        if LV.seg_dist(p, s0, s1 + d * 3.0)[0] < r:
            return True
    return False


def on_mesa_top(p):
    rel = p - LV.FALL
    rt = LV.mesa_r_top(math.atan2(rel.y, rel.x))
    return rel.length < rt - 0.02


def in_notch(p):
    d, t = LV.notch_param(p)
    return d <= LV.NOTCH_IN + 0.02 and -0.02 <= t <= 1.02


def walkable(a, c):
    if a['id'] == 'a_fall':
        return on_mesa_top(c) or in_notch(c) or in_exit_walk(a, c)
    return sd_area(a, c) <= 0.0 or in_exit_walk(a, c)


# cart road: the chasm runs along the south (right-hand) side, away from the ends
CART = next((sh for sh in AID['a_cart']['shape'] if 'line' in sh), None) or \
    {'line': [[-40, 10], [-36, 4], [-28, -4], [0, -10], [30, -8], [34, -6]], 'w': 5}   # (old road; only used by the legacy global path)
CART_PTS = [V(q) for q in CART['line']]
CART_W = CART['w']


def cart_side_t(p):
    """(side, arclength t, total) relative to the cart polyline; side < 0 = south/right of travel."""
    best = (1e9, 0, 0.0)
    acc = 0.0
    for i in range(len(CART_PTS) - 1):
        a, b = CART_PTS[i], CART_PTS[i + 1]
        d, t = LV.seg_dist(p, a, b)
        if d < best[0]:
            u = (b - a)
            q = p - (a + u * t)
            side = u.x * q.y - u.y * q.x
            best = (d, side, acc + u.length * t)
        acc += (b - a).length
    return best[1], best[2], acc


def in_chasm(p):
    side, t, tot = cart_side_t(p)
    sdv = sd_shape(CART, p)
    return side < 0 and sdv > 0.25 and 7.0 < t < tot - 7.0 and min(sd_area(o, p) for o in AREAS if o['id'] != 'a_cart') > 1.0


# ------------------------------------------------------------------ constraint polylines (crisp page edges, exit corridors)
def contour_chains(a, off=0.0, step=1.1):
    """Points on the union boundary (sd = off), as chains following each primitive."""
    chains = []
    for sh in a['shape']:
        raw = []
        if 'c' in sh:
            c, r = V(sh['c']), sh['r'] + off
            n = max(24, int(2 * math.pi * r / step))
            for i in range(n + 1):
                th = 2 * math.pi * i / n
                raw.append(c + V((math.cos(th), math.sin(th))) * r)
        else:
            pts = [V(q) for q in sh['line']]
            w = sh['w'] + off
            for side in (1, -1):
                ch = []
                for i in range(len(pts) - 1):
                    a_, b_ = pts[i], pts[i + 1]
                    u = (b_ - a_).normalized()
                    nrm = V((-u.y, u.x)) * side
                    k = max(2, int((b_ - a_).length / step))
                    for j in range(k):
                        ch.append(a_ + (b_ - a_) * (j / k) + nrm * w)
                ch.append(pts[-1] + V((-(pts[-1] - pts[-2]).normalized().y, (pts[-1] - pts[-2]).normalized().x)) * w * side)
                raw.extend(ch)
                raw.append(None)
            # end caps
            for end, nxt in ((pts[0], pts[1]), (pts[-1], pts[-2])):
                u = (end - nxt).normalized()
                base = math.atan2(u.y, u.x)
                for j in range(9):
                    th = base - math.pi / 2 + math.pi * j / 8
                    raw.append(end + V((math.cos(th), math.sin(th))) * w)
                raw.append(None)
        cur = []
        for q in raw:
            if q is None or abs(sd_area(a, q) - off) > 0.2:
                if len(cur) > 1:
                    chains.append(cur)
                cur = []
            else:
                cur.append(q)
        if len(cur) > 1:
            chains.append(cur)
    return chains


def register_constraints():
    LV.EXTRA_POLYS.clear()
    for a in AREAS:
        if a['id'] != 'a_fall':
            for ch in contour_chains(a, 0.0):
                LV.EXTRA_POLYS.append((ch, False))
        for ex in a['exits']:
            s0, s1, d = exit_segment(a, ex)
            n = V((-d.y, d.x)) * 1.35
            LV.EXTRA_POLYS.append(([s0 + n, s1 + n, s1 - n, s0 - n], True))


# ------------------------------------------------------------------ helpers: island split / copy
def islands(bm):
    bm.faces.ensure_lookup_table()
    bm.faces.index_update()
    seen = set()
    out = []
    for f in bm.faces:
        if f.index in seen:
            continue
        stack = [f]
        comp = []
        seen.add(f.index)
        while stack:
            g = stack.pop()
            comp.append(g)
            for v in g.verts:
                for h in v.link_faces:
                    if h.index not in seen:
                        seen.add(h.index)
                        stack.append(h)
        out.append(comp)
    return out


def copy_faces(faces, dst, keep_mat=True):
    vm = {}
    for f in faces:
        vs = []
        for v in f.verts:
            if v not in vm:
                vm[v] = dst.verts.new(v.co)
            vs.append(vm[v])
        try:
            nf = dst.faces.new(vs)
            if keep_mat:
                nf.material_index = f.material_index
            nf.smooth = f.smooth
        except ValueError:
            pass


def U2(co):
    """Blender co -> Unity (x, z)."""
    return V((-co.x, -co.y))


def hash01(p, salt=0.0):
    return (math.sin(p.x * 12.9898 + p.y * 78.233 + salt * 3.1) * 43758.5453) % 1.0


def keep_prob(sdv):
    if sdv <= 0:
        return 1.0
    return max(0.0, 1.0 - sdv / MARGIN) ** 1.6


# ------------------------------------------------------------------ blockers along the page edge
STYLE = {'a_gate': None, 'a_plaza': 'wall', 'a_alley': 'crooked', 'a_field': 'bank', 'a_cart': 'rock', 'a_fall': None}
SB_HOUSES = []
for i in range(6):
    SB_HOUSES.append(V((22 - 10 + i * 4.4, 26 + (6.5 if i % 2 == 0 else -6.5))))
SB_HOUSES += [V((-17, 28)), V((17, 30)), V((30, 40)), V((-39, 27)), V((-21, 27)), V((31, 13)), V((49, 13))]


def plan_blockers(a):
    """Returns list of (p0, p1, style) edge segments (Unity xz) just outside the walkable edge."""
    st = STYLE[a['id']]
    if not st:
        return []
    segs = []
    for ch in contour_chains(a, 1.25, step=1.0):
        i = 0
        while i < len(ch) - 1:
            j = min(len(ch) - 1, i + 4)
            p0, p1 = ch[i], ch[j]
            mid = (p0 + p1) / 2
            skip = near_exit(a, mid, 3.6) or near_exit(a, p0, 3.0) or near_exit(a, p1, 3.0)
            if a['id'] == 'a_cart':
                side, t, tot = cart_side_t(mid)
                if side < 0 and 7.0 < t < tot - 7.0:
                    skip = True        # the chasm closes this side
            if any((mid - h).length < 4.2 for h in SB_HOUSES) and a['id'] == 'a_alley':
                skip = True
            if not skip:
                segs.append((p0, p1, st))
            i += 3
    return segs


def seg_poly(p0, p1, width, seed, jag=0.25):
    rnd = random.Random(seed)
    u = (p1 - p0)
    ln = u.length
    u.normalize()
    n = V((-u.y, u.x))
    pts = []
    k = 4
    for i in range(k + 1):
        t = i / k
        pts.append(p0 - u * 0.5 + u * (ln + 1.0) * t + n * width * 0.5 * (1 + rnd.uniform(-jag, jag)))
    for i in range(k, -1, -1):
        t = i / k
        pts.append(p0 - u * 0.5 + u * (ln + 1.0) * t - n * width * 0.5 * (1 + rnd.uniform(-jag, jag)))
    # CCW in xz
    area = sum(pts[i].x * pts[(i + 1) % len(pts)].y - pts[(i + 1) % len(pts)].x * pts[i].y for i in range(len(pts)))
    return pts if area > 0 else list(reversed(pts))


def painted_wall(bm_w, bm_ink, p0, p1, seed):
    """Low painted terracotta balustrade segment (plaza edge = fully drawn)."""
    rnd = random.Random(seed)
    u = (p1 - p0)
    ln = u.length
    u.normalize()
    n = V((-u.y, u.x))
    h = 0.85
    t = 0.32
    a, b = p0 - u * 0.4, p1 + u * 0.4
    y0 = min(LV.height(a), LV.height(b)) - 0.2
    corners = [a + n * t, b + n * t, b - n * t, a - n * t]
    bot = [bm_w.verts.new(LV.B(c.x, c.y, y0)) for c in corners]
    top = [bm_w.verts.new(LV.B(c.x, c.y, y0 + 0.2 + h)) for c in corners]
    for i in range(4):
        j = (i + 1) % 4
        bm_w.faces.new((bot[i], bot[j], top[j], top[i]))
    bm_w.faces.new(top)
    cap = [a + n * (t + 0.07) - u * 0.05, b + n * (t + 0.07) + u * 0.05, b - n * (t + 0.07) + u * 0.05, a - n * (t + 0.07) - u * 0.05]
    cb = [bm_w.verts.new(LV.B(c.x, c.y, y0 + 0.2 + h)) for c in cap]
    ct = [bm_w.verts.new(LV.B(c.x, c.y, y0 + 0.2 + h + 0.12)) for c in cap]
    for i in range(4):
        j = (i + 1) % 4
        f = bm_w.faces.new((cb[i], cb[j], ct[j], ct[i]))
        f.material_index = 1
    f = bm_w.faces.new(ct)
    f.material_index = 1
    for c in (a, b):
        LV.rib_vertical(bm_ink, [LV.B(c.x + n.x * t, c.y + n.y * t, y0 + 0.25), LV.B(c.x + n.x * t, c.y + n.y * t, y0 + 0.2 + h + 0.12)], 0.06)
    LV.rib_vertical(bm_ink, [LV.B(*(a + n * (t + 0.08)), y0 + 0.2 + h + 0.13), LV.B(*(b + n * (t + 0.08)), y0 + 0.2 + h + 0.13)], 0.07)
    LV.rib_vertical(bm_ink, [LV.B(*(a - n * (t + 0.08)), y0 + 0.2 + h + 0.13), LV.B(*(b - n * (t + 0.08)), y0 + 0.2 + h + 0.13)], 0.07)
    # balusters drawn on the inner face
    k = int(ln / 0.45)
    for i in range(1, k):
        c = a + (b - a) * (i / k) - n * (t + 0.012) * (1 if rnd.random() < 2 else 1)
        LV.rib_vertical(bm_ink, [LV.B(c.x, c.y, y0 + 0.35), LV.B(c.x, c.y, y0 + 0.2 + h - 0.08)], 0.03)


def build_blockers(a, solid, ink, hatch, wall, bank):
    rnd = random.Random(hash(a['id']) % 1000)
    for k, (p0, p1, st) in enumerate(plan_blockers(a)):
        seed = 500 + k * 7 + len(a['id'])
        if st == 'wall':
            painted_wall(wall, ink, p0, p1, seed)
        elif st == 'rock':
            LV.outcrop(solid, ink, hatch, seg_poly(p0, p1, rnd.uniform(1.8, 2.6), seed, 0.35), rnd.uniform(1.6, 2.8), seed, tiers=2 if rnd.random() < 0.6 else 1)
        elif st == 'crooked':
            LV.outcrop(solid, ink, hatch, seg_poly(p0, p1, 0.7, seed, 0.15), rnd.uniform(1.5, 2.3), seed, tiers=1)
        elif st == 'bank':
            LV.outcrop(bank, ink, hatch, seg_poly(p0, p1, 2.2, seed, 0.3), rnd.uniform(0.7, 1.0), seed, tiers=1)
            # a drawn fence along the bank top
            u = (p1 - p0)
            for i in range(4):
                c = p0 + u * (i / 3)
                y = LV.height(c) + 0.9
                LV.rib_vertical(ink, [LV.B(c.x, c.y, y), LV.B(c.x, c.y, y + 1.0)], 0.05)
            LV.rib_vertical(ink, [LV.B(p0.x, p0.y, LV.height(p0) + 1.6), LV.B(p1.x, p1.y, LV.height(p1) + 1.55)], 0.045)


def build_chasm(solid, ink, hatch, floor):
    """South edge of the cart road: the ground breaks off into a drawn drop (concept: ledges over blank depth)."""
    side_n = []
    acc = 0.0
    tot = sum((CART_PTS[i + 1] - CART_PTS[i]).length for i in range(len(CART_PTS) - 1))
    tops, bots, outs = [], [], []
    rnd = random.Random(88)
    t = 7.0
    while t < tot - 7.0:
        # point at arclength t
        acc = 0.0
        for i in range(len(CART_PTS) - 1):
            a_, b_ = CART_PTS[i], CART_PTS[i + 1]
            ln = (b_ - a_).length
            if acc + ln >= t:
                u = (b_ - a_).normalized()
                c = a_ + u * (t - acc)
                break
            acc += ln
        right = V((u.y, -u.x))    # south / right-hand side
        jag = 0.35 * math.sin(t * 0.9) + rnd.uniform(-0.25, 0.25)
        p_top = c + right * (CART_W + 0.35 + jag)
        p_bot = c + right * (CART_W + 0.75 + jag * 1.4)
        p_out = c + right * (CART_W + MARGIN + 4)
        tops.append(p_top)
        bots.append(p_bot)
        outs.append(p_out)
        t += 1.2
    depth = -4.5
    vt = [solid.verts.new(LV.B(p.x, p.y, LV.height(p))) for p in tops]
    vm = [solid.verts.new(LV.B(p.x, p.y, LV.height(p) - 1.8 + 0.3 * math.sin(i))) for i, p in enumerate(bots)]
    vb = [solid.verts.new(LV.B(p.x + 0.0, p.y, depth)) for p in bots]
    for i in range(len(tops) - 1):
        solid.faces.new((vt[i], vt[i + 1], vm[i + 1], vm[i]))
        solid.faces.new((vm[i], vm[i + 1], vb[i + 1], vb[i]))
    fb = [floor.verts.new(LV.B(p.x, p.y, depth)) for p in bots]
    fo = [floor.verts.new(LV.B(p.x, p.y, depth)) for p in outs]
    for i in range(len(tops) - 1):
        floor.faces.new((fb[i], fb[i + 1], fo[i + 1], fo[i]))
    for f in solid.faces:
        f.normal_update()
    # ink: top edge, broken lower edge; hatch on the face
    LV.rib_vertical(ink, [v.co + V((0, 0, 0.02)) for v in vt], 0.1)
    for i in range(0, len(vm) - 1, 3):
        LV.rib_vertical(ink, [vm[i].co, vm[min(len(vm) - 1, i + 2)].co], 0.06)
    for i in range(0, len(vt) - 1):
        if rnd.random() < 0.7:
            a = vt[i].co.lerp(vt[i + 1].co, rnd.random()) + V((0, 0, -0.15))
            LV.rib_vertical(hatch, [a, a + (vb[i].co - vt[i].co) * rnd.uniform(0.5, 0.85) + V((0.15, 0.1, 0))], 0.035)
        if i % 4 == 0:
            LV.rib_vertical(ink, [vt[i].co, vb[i].co + V((0, 0, 0.5))], 0.05)


# ------------------------------------------------------------------ page edge sketch lines
def page_edge_lines(a, ink, hatch):
    """Loose pencil strokes following the page edge in the margin, and hatching that thins outward."""
    rnd = random.Random(len(a['id']) * 31)
    for off in (2.2, 3.6, 5.5):
        for ch in contour_chains(a, off, step=1.4):
            i = 0
            while i < len(ch) - 2:
                ln = rnd.randint(2, 6)
                seg = ch[i:i + ln]
                if len(seg) > 1 and rnd.random() < (0.75 if off < 3 else 0.4) and not near_exit(a, seg[0], 2.5):
                    if not (a['id'] == 'a_cart' and in_chasm(seg[0])):
                        LV.ribbon(ink, [LV.gp(p.x + rnd.uniform(-0.2, 0.2), p.y + rnd.uniform(-0.2, 0.2), 0.03) for p in seg], 0.035 if off > 3 else 0.05)
                i += ln + rnd.randint(1, 4)
    for ch in contour_chains(a, 1.8, step=0.7):
        for p in ch:
            if rnd.random() < 0.55 and not near_exit(a, p, 3.0) and not (a['id'] == 'a_cart' and in_chasm(p)):
                q = p + grad(a, p) * rnd.uniform(0.2, 2.5)
                LV.ribbon(hatch, [LV.gp(q.x, q.y, 0.028), LV.gp(q.x + 0.55, q.y + 0.75, 0.028)], 0.035)


# ------------------------------------------------------------------ exits
def build_exit(a, ex, solid, ink, paint_mat):
    pos = V(ex['pos'])
    d = exit_dir(a, ex)
    n = V((-d.y, d.x))
    rnd = random.Random(int(abs(pos.x * 13 + pos.y * 7)))
    # path edges running off the page, breaking up
    for side in (1, -1):
        t = 0.0
        while t < 9.0:
            ln = max(0.25, 1.3 - t * 0.1)
            if rnd.random() < 1.0 - t / 11.0:
                p0 = pos + d * t + n * 1.3 * side
                p1 = pos + d * (t + ln) + n * (1.3 + 0.05 * t) * side
                LV.ribbon(ink, [LV.gp(p0.x, p0.y, 0.035), LV.gp(p1.x, p1.y, 0.035)], 0.07 - t * 0.004)
            t += ln + 0.3 + t * 0.12
    # brush arrow on the ground pointing out of the page
    c = pos + d * 0.6
    LV.ribbon(ink, [LV.gp(*(c - d * 1.3), 0.04), LV.gp(*(c - d * 0.3 + n * 0.04), 0.04), LV.gp(*(c + d * 0.35), 0.04)], 0.16)
    LV.ribbon(ink, [LV.gp(*(c + d * 0.6 + n * 0.0), 0.045), LV.gp(*(c - d * 0.05 + n * 0.55), 0.045)], 0.15)
    LV.ribbon(ink, [LV.gp(*(c + d * 0.6 - n * 0.0), 0.045), LV.gp(*(c - d * 0.05 - n * 0.55), 0.045)], 0.15)
    # a small drawn gateway: two solid stumps + the arch/lintel drawn in ink
    g = pos + d * 2.5
    hw = 1.55
    for side in (1, -1):
        q = g + n * hw * side
        y = LV.height(q)
        s = 0.32
        bot = [solid.verts.new(LV.B(q.x + dx, q.y + dz, y - 0.2)) for dx, dz in ((-s, -s), (s, -s), (s, s), (-s, s))]
        top = [solid.verts.new(LV.B(q.x + dx * 0.85, q.y + dz * 0.85, y + 0.75 + rnd.uniform(0, 0.25))) for dx, dz in ((-s, -s), (s, -s), (s, s), (-s, s))]
        for i in range(4):
            j = (i + 1) % 4
            solid.faces.new((bot[i], bot[j], top[j], top[i]))
        solid.faces.new(top)
        LV.rib_vertical(ink, [v.co + V((0, 0, 0.02)) for v in top] + [top[0].co + V((0, 0, 0.02))], 0.06)
        LV.rib_vertical(ink, [LV.B(q.x, q.y, y + 0.9), LV.B(q.x, q.y, y + 2.3)], 0.06)
    yg = LV.height(g)
    arch = []
    for i in range(11):
        th = math.pi * i / 10
        q = g + n * math.cos(th) * hw
        arch.append(LV.B(q.x, q.y, yg + 2.3 + math.sin(th) * 0.8))
    LV.rib_vertical(ink, arch, 0.07)
    arch2 = [v + V((0, 0, 0.18)) for v in arch]
    LV.rib_vertical(ink, arch2[1:-1], 0.04)
    # a little painted pennant on the arch (paint = the way onward is 'more drawn')
    top_c = LV.B(g.x, g.y, yg + 3.1)
    fl = [solid.verts.new(top_c), solid.verts.new(top_c + V((0, 0, 0.45))), solid.verts.new(top_c + LV.B(d.x * 0.6, d.y * 0.6, 0.3) - LV.B(0, 0, 0))]
    f = solid.faces.new(fl)
    f.material_index = 1
    LV.rib_vertical(ink, [top_c - V((0, 0, 0.1)), top_c + V((0, 0, 0.5))], 0.03)


# ------------------------------------------------------------------ build
def build_level_areas():
    A = Asset('Level_Ch1')
    if all(a['id'] in SLICE_IDS for a in AREAS):
        # every page is a hand-built diorama now (slice 1 + slice 2): the old global-ground path is not needed
        SL.build_slice(A)
        SL2.build_slice2(A)
        return _build_global(A)
    LV.KEEP = LV.load_keepouts()
    register_constraints()
    verts, heights, walk_g, cliff_g = LV.build_ground()
    ink_g, hatch_g, tiles_g, paint_g = LV.build_lines()
    csolid_g, cink_g, chatch_g = LV.build_cliff_extras(None, None, None)
    # global ground cliff band (mesa) as bmesh for per-face splitting
    bm_cliff_g, _ = LV.mesh_from_tris(verts, heights, cliff_g, lambda c: 'M_Cliff', uv=False)
    all_tris = walk_g + cliff_g
    tri_c = {}
    for f in all_tris:
        tri_c[tuple(f)] = V((sum(verts[i][0] for i in f) / 3, sum(verts[i][1] for i in f) / 3))
    isl = {}
    for name, bm in (('ink', ink_g), ('hatch', hatch_g), ('tiles', tiles_g), ('paint', paint_g),
                     ('csolid', csolid_g), ('cink', cink_g), ('chatch', chatch_g)):
        isl[name] = (bm, [(comp, U2(sum((f.calc_center_median() for f in comp), V((0, 0, 0))) / len(comp))) for comp in islands(bm)])

    tone = ['M_PlazaStone1', 'M_PlazaStone2', 'M_PlazaStone3']
    fp = lambda c: SL.in_footprint((c.x, c.y))      # other pages keep no colliders/lines inside the slice dioramas
    for a in AREAS:
        if a['id'] in SLICE_IDS:
            continue
        s = short(a['id'])
        A.empty(f'Area_{a["id"]}', (0, 0, 0))
        parent = f'Area_{a["id"]}'
        sdf = lambda p, a=a: sd_area(a, p)
        # --- walkable + margin from the global triangulation
        walk_t, margin_t = [], []
        for f in walk_g:
            c = tri_c[tuple(f)]
            if fp(c):
                continue
            if walkable(a, c):
                walk_t.append(f)
            elif sdf(c) <= MARGIN:
                if a['id'] == 'a_cart' and in_chasm(c):
                    continue
                margin_t.append(f)
        cliff_t = [f for f in cliff_g if sdf(tri_c[tuple(f)]) <= MARGIN + 2 and not fp(tri_c[tuple(f)])]
        if a['id'] != 'a_fall':
            # the mesa cliff band shows up as scenery only near its own page
            cliff_t = [f for f in cliff_t if sdf(tri_c[tuple(f)]) <= 4.0]
        bm_walk, _ = LV.mesh_from_tris(verts, heights, walk_t, LV.ground_material)
        gw = Part(f'Ground_Walk_{s}')
        gw.add(bm_walk, 'M_Ground', True, lambda c, n: LV.ground_material(V((-c.x, -c.y))))
        tiles = bmesh.new()
        for comp, cc in isl['tiles'][1]:
            if sdf(cc) <= 0.6 or (walkable(a, cc)):
                copy_faces(comp, tiles)
        if len(tiles.faces):
            gw.add(tiles, 'M_PlazaStone1', smooth=False, face_mat=lambda c, n, tiles=tiles: None)
            # restore tone by matching material_index (kept in copy) -> handled below
        A.part(gw, pivot=(0, 0, 0), parent=parent)
        me = A.objs[f'Ground_Walk_{s}'].data
        if 'M_PlazaStone1' in [m.name for m in me.materials]:
            for t in tone[1:]:
                if t not in [m.name for m in me.materials]:
                    me.materials.append(L.get_mat(t))
        if margin_t:
            bm_m, _ = LV.mesh_from_tris(verts, heights, margin_t, lambda c: 'M_Ground')
            mg = Part(f'Margin_{s}')
            mg.add(bm_m, 'M_Ground', True)
            if a['id'] == 'a_cart':
                fl = bmesh.new()
                chs, chi, chh = bmesh.new(), bmesh.new(), bmesh.new()
                build_chasm(chs, chi, chh, fl)
                mg.add(fl, 'M_Ground', smooth=False)
            A.part(mg, pivot=(0, 0, 0), parent=parent)
        # --- lines (thinning into the margin)
        gl = Part(f'Ground_Lines_{s}')
        for key, mat in (('paint', 'M_GroundEarth'), ('ink', 'M_Ink'), ('hatch', 'M_Hatch')):
            out = bmesh.new()
            for comp, cc in isl[key][1]:
                if fp(cc):
                    continue
                sv = sdf(cc)
                if a['id'] == 'a_fall' and not (on_mesa_top(cc) or in_notch(cc) or in_exit_walk(a, cc)):
                    sv = max(sv, 0.5) + 2.0
                if sv > MARGIN or (a['id'] == 'a_cart' and in_chasm(cc)):
                    continue
                if hash01(cc, len(key)) < keep_prob(sv):
                    copy_faces(comp, out)
            if key == 'ink':
                page_edge_lines(a, out, out)
            if len(out.faces):
                gl.add(out, mat, smooth=False)
        A.part(gl, pivot=(0, 0, 0), parent=parent)
        # --- cliffs: mesa band, global outcrops nearby, page-edge blockers
        cl = Part(f'Cliffs_{s}')
        if cliff_t:
            bm_c, _ = LV.mesh_from_tris(verts, heights, cliff_t, lambda c: 'M_Cliff', uv=False)
            cl.add(bm_c, 'M_Cliff', smooth=False)
        cs, ci, ch = bmesh.new(), bmesh.new(), bmesh.new()
        for key, dst in (('csolid', cs), ('cink', ci), ('chatch', ch)):
            for comp, cc in isl[key][1]:
                lim = MARGIN + 2 if a['id'] == 'a_fall' else 5.0
                if sdf(cc) <= lim and not walkable(a, cc) and not fp(cc):
                    copy_faces(comp, dst)
        wall, bank = bmesh.new(), bmesh.new()
        build_blockers(a, cs, ci, ch, wall, bank)
        if a['id'] == 'a_cart':
            build_chasm(cs, ci, ch, bmesh.new())
        if len(cs.faces):
            cl.add(cs, 'M_Cliff', smooth=False, face_mat=lambda c, n: 'M_Ground' if n.z > 0.7 else None)
        if len(wall.faces):
            cl.add(wall, 'M_Terracotta', smooth=False, face_mat=lambda c, n: 'M_TerracottaDark' if c.z > 0.9 + LV.height(V((-c.x, -c.y))) - 0.1 else None)
        if len(bank.faces):
            cl.add(bank, 'M_Cliff', smooth=False, face_mat=lambda c, n: 'M_GroundEarth' if n.z > 0.7 else None)
        if len(ci.faces):
            cl.add(ci, 'M_Ink', smooth=False)
        if len(ch.faces):
            cl.add(ch, 'M_Hatch', smooth=False)
        if cl.pieces:
            A.part(cl, pivot=(0, 0, 0), parent=parent)
        # --- exits
        for ex in a['exits']:
            ep = Part(f'Exit_{s}_{short(ex["to"])}')
            es, ei = bmesh.new(), bmesh.new()
            build_exit(a, ex, es, ei, None)
            pm = 'M_PaintRed' if a['id'] in ('a_plaza', 'a_alley') else 'M_PaintBlue'
            ep.add(es, 'M_Cliff', smooth=False, face_mat=lambda c, n, es=es, pm=pm: None)
            ep.add(ei, 'M_Ink', smooth=False)
            pos = V(ex['pos'])
            A.part(ep, pivot=tuple(LV.B(pos.x, pos.y, LV.height(pos))), parent=parent)
            # pennant faces (material_index 1 in es) -> paint colour
            ob = A.objs[ep.name]
            me = ob.data
            if pm not in [m.name for m in me.materials]:
                me.materials.append(L.get_mat(pm))
            pi = [m.name for m in me.materials].index(pm)
            for poly in me.polygons:
                if len(poly.vertices) == 3 and poly.material_index == 0:
                    poly.material_index = pi
    SL.build_slice(A)
    SL2.build_slice2(A)
    # tile tone fix: re-colour Ground_Walk tile faces by a hash of their centre (same look as the global plaza)
    for a in AREAS:
        if a['id'] in SLICE_IDS:
            continue
        ob = A.objs[f'Ground_Walk_{short(a["id"])}']
        me = ob.data
        names = [m.name for m in me.materials]
        if 'M_PlazaStone1' not in names:
            continue
        i1 = names.index('M_PlazaStone1')
        idx = {t: names.index(t) for t in tone}
        for poly in me.polygons:
            if poly.material_index == i1 and len(poly.vertices) == 6:
                u = U2(poly.center)
                if (u - V((0, 20))).length < 7 + 2 * (hash01(u, 3) - 0.5) * 2:
                    poly.material_index = idx['M_PlazaStone3']
                elif nval(V((u.x, u.y, 0)), 0.35, 6) + (hash01(u, 5) - 0.5) * 0.6 > 0.1:
                    poly.material_index = idx['M_PlazaStone2']
    return _build_global(A)


def _build_global(A):
    A.empty('Global', (0, 0, 0))
    ws, wi, wh = LV.build_walls()
    wb = Part('Walls_Bound')
    wb.add(ws, 'M_WallRock', smooth=False)
    wb.add(wi, 'M_Ink', smooth=False)
    wb.add(wh, 'M_Hatch', smooth=False)
    A.part(wb, pivot=(0, 0, 0), parent='Global')
    cb, teeth = LV.build_ceiling()
    ce = Part('Ceiling')
    ce.add(cb, 'M_Ceiling', smooth=True)
    ce.add(teeth, 'M_Ceiling', smooth=False)
    A.part(ce, pivot=(0, 0, 0), parent='Global')
    bd = Part('Backdrop')
    bd.add(LV.build_backdrop(), 'M_Spire', smooth=False)
    A.part(bd, pivot=(0, 0, 0), parent='Global')
    A.root['ouat_size'] = 1.0
    A.meta['note'] = 'Chapter-1 level split into page areas (chapter1.json areas[]). Root at world origin.'
    return A


def area_of(p):
    """Area id a world point belongs to (smallest signed distance)."""
    p = V(p)
    return min(AREAS, key=lambda a: sd_area(a, p))['id']


ASSETS = [('Level_Ch1', build_level_areas)]
