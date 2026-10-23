# -*- coding: utf-8 -*-
"""Creature villagers = half-painted wooden puppets (§3-4). Blender coords: Z up, front -Y, left +X.
Root origin = between the feet. Bare wood, ball joints, faceted heads with hole eyes and no mouth,
red/blue paint brushed on and left unfinished (ragged face-level edges), unfinished parts as ink lines."""
import math
from mathutils import Vector
from mathutils.bvhtree import BVHTree
import ouat_lib as L
from ouat_lib import (Part, Asset, bm_sphere, bm_tube, bm_blade, bm_box, bm_lathe, stroke, wobble_line,
                      rot, move, deform, jitter, subdivide, nval)

V = Vector
WOOD, JOINT, RED, BLUE, INK = 'M_PuppetWood', 'M_PuppetJoint', 'M_PaintRed', 'M_PaintBlue', 'M_Ink'


# ------------------------------------------------------------------ paint functions (world coords)
def paint_above(z, mat, amp=0.04, freq=9.0, seed=0.0):
    return L.ragged(lambda c: c.z, z, mat, amp=amp, freq=freq, seed=seed)


def paint_below(z, mat, amp=0.04, freq=9.0, seed=0.0):
    return L.ragged(lambda c: -c.z, -z, mat, amp=amp, freq=freq, seed=seed)


def paint_band(z0, z1, mat, amp=0.04, freq=9.0, seed=0.0):
    def fn(c, n):
        e = nval(c, freq, seed) * amp
        return mat if (z0 + e) < c.z < (z1 - e * 0.7) else None
    return fn


def streaks(part, b, z_edge, mat, center=(0, 0), n=8, ln=0.08, w=0.02, down=True, seed=0.0, arc=(0, 360)):
    """Brush streaks of paint running along the surface from a paint edge: irregular lengths and widths,
    slightly wandering, like a brush dragged and lifted (concept: unfinished brushed paint)."""
    import random
    rnd = random.Random(int(seed * 1000) + 7)
    bvh = BVHTree.FromBMesh(b)
    cx, cy = center
    for k in range(n):
        a = math.radians(arc[0] + (arc[1] - arc[0]) * (k + rnd.uniform(-0.45, 0.45)) / n)
        L_ = ln * rnd.choice((0.25, 0.4, 0.55, 0.8, 1.1, 1.5))
        wk = w * rnd.uniform(0.55, 1.35)
        drift = rnd.uniform(-0.35, 0.35)
        pts, nrms = [], []
        steps = 6
        for t in range(steps):
            f = t / (steps - 1)
            z = z_edge + (-1 if down else 1) * (L_ * f - 0.012)
            aa = a + drift * f * (L_ / 0.3)
            d = V((math.cos(aa), math.sin(aa), 0))
            hit = bvh.ray_cast(V((cx, cy, z)) + d * 3.0, -d)
            if hit[0] is None:
                break
            pts.append(hit[0] + hit[1] * 0.006)
            nrms.append(hit[1])
        if len(pts) < 3:
            continue
        prof = [1.0, 0.95, 0.8, 0.6, 0.38, 0.08]
        ww = [wk * prof[i] for i in range(len(pts))]
        part.add(bm_blade(pts, ww, thick=0.004, up=tuple(nrms[len(nrms) // 2])), mat, smooth=False)


# ------------------------------------------------------------------ building blocks
def capsule(a, b, r0, r1, seg=7):
    a, b = V(a), V(b)
    return bm_tube([a, a.lerp(b, 0.5), b], [r0, (r0 + r1) * 0.5 * 1.08, r1], seg=seg)


def ball(c, r, seg=8, rings=6):
    return bm_sphere(c, (r, r, r), seg=seg, rings=rings)


def mitten(wrist, d, size, side=1):
    """Blunt wooden hand: rounded block pointing along d."""
    d = V(d).normalized()
    b = bm_box((0, 0, 0), (size * 0.75, size * 0.45, size * 1.1))
    b = L.bevel(b, size * 0.18, 1, 40)
    q = d.to_track_quat('-Z', 'Y')
    L.xform(b, q.to_matrix().to_4x4())
    move(b, V(wrist) + d * size * 0.55)
    return b


def ink_hand(part, wrist, d, ln=0.1, n=3, spread=0.025, side=1, r=0.0045):
    """Unfinished hand: palm outline + finger lines drawn as ink geometry."""
    d = V(d).normalized()
    s = d.cross(V((0, 1, 0)))
    if s.length < 1e-4:
        s = V((1, 0, 0))
    s.normalize()
    w = V(wrist)
    palm = [w + s * spread * 1.4, w + d * ln * 0.45 + s * spread * 1.6, w + d * ln * 0.5 - s * spread * 1.6, w - s * spread * 1.4]
    part.add(stroke(palm, r, taper=False), INK, smooth=False)
    for k in range(n):
        t = (k / (n - 1) - 0.5) * 2 if n > 1 else 0
        base = w + d * ln * 0.48 + s * spread * 1.3 * t
        tip = base + d * ln * (0.75 - 0.15 * abs(t)) + s * spread * 0.6 * t + V((0, -0.01, 0))
        part.add(stroke([base, base.lerp(tip, 0.5) + V((0, -0.006, 0)), tip], r), INK, smooth=False)
    # thumb
    tb = w + d * ln * 0.2 - s * spread * 1.5 * side
    part.add(stroke([tb, tb + d * ln * 0.35 - s * spread * 1.2 * side], r), INK, smooth=False)


def block_foot(ankle, length, width, height):
    a = V(ankle)
    b = bm_box(a + V((0, -length * 0.3, -height * 0.5)), (width, length, height))
    b = L.bevel(b, min(width, height) * 0.25, 1, 40)
    deform(b, lambda c: V((c.x, c.y, max(0.0, c.z))))
    return b


def make_leg(A, side, hip, knee, ankle, r, foot=(0.16, 0.08, 0.06), fm=None, mat=WOOD, jmat=JOINT, ink_shin=False):
    nm = 'LegL' if side > 0 else 'LegR'
    p = Part(nm)
    hip, knee, ankle = V(hip), V(knee), V(ankle)
    p.add(ball(hip, r * 1.15), jmat)
    p.add(capsule(hip, knee, r, r * 0.85), mat, face_mat=fm)
    p.add(ball(knee, r * 0.95), jmat)
    if ink_shin:   # leg drawn only as two lines below the knee
        for dx in (-r * 0.6, r * 0.6):
            p.add(stroke(wobble_line(knee + V((dx, 0, -r)), ankle + V((dx * 0.8, 0, 0)), 4, 0.005, dx * 50), 0.005), INK, smooth=False)
        p.add(stroke([ankle + V((-r, 0, 0)), ankle + V((0, -r * 0.6, -0.01)), ankle + V((r, 0, 0))], 0.005, taper=False), INK, smooth=False)
    else:
        p.add(capsule(knee, ankle, r * 0.85, r * 0.7), mat, face_mat=fm)
        p.add(block_foot(ankle, *foot), mat, smooth=False, face_mat=fm)
    A.part(p, pivot=hip)


def make_arm(A, side, sh, el, wr, r, hand='mitten', fm=None, mat=WOOD, jmat=JOINT, parent='Body', hand_size=None, ink_fore=False):
    nm = 'ArmL' if side > 0 else 'ArmR'
    p = Part(nm)
    sh, el, wr = V(sh), V(el), V(wr)
    p.add(ball(sh, r * 1.2), jmat)
    p.add(capsule(sh, el, r, r * 0.85), mat, face_mat=fm)
    p.add(ball(el, r * 0.95), jmat)
    d = (wr - el).normalized()
    if ink_fore:   # forearm and hand only drawn
        for dx in (-r * 0.55, r * 0.55):
            o = d.cross(V((0, 1, 0))).normalized() * dx
            p.add(stroke(wobble_line(el + o + d * r, wr + o * 0.8, 4, 0.004, dx * 40), 0.0045), INK, smooth=False)
        ink_hand(p, wr, d, ln=(hand_size or r * 4.0), side=side)
    else:
        p.add(capsule(el, wr, r * 0.85, r * 0.7), mat, face_mat=fm)
        if hand == 'mitten':
            p.add(mitten(wr, d, hand_size or r * 2.6, side), mat, smooth=False)
        elif hand == 'ink':
            ink_hand(p, wr, d, ln=(hand_size or r * 4.0), side=side)
    A.part(p, pivot=sh, parent=parent)


def faceted_head(kind, c, size, seed=0.0):
    c = V(c)
    sx, sy, sz = size
    if kind == 'egg':
        b = bm_sphere(c, (sx, sy, sz), seg=8, rings=6)
        deform(b, lambda q: V((q.x * (1 - 0.18 * max(0, (q.z - c.z) / sz)), q.y, q.z)))
        jitter(b, min(size) * 0.05, 4.0, seed)
    elif kind == 'box':
        b = bm_box(c, (sx * 2, sy * 2, sz * 2))
        b = L.bevel(b, min(size) * 0.22, 1, 40)
        jitter(b, min(size) * 0.03, 4.0, seed)
    elif kind == 'hex':   # hexagonal slab facing forward (wide child head)
        pts = [(math.cos(math.radians(30 + 60 * i)) * sx, math.sin(math.radians(30 + 60 * i)) * sz) for i in range(6)]
        b = L.bm_prism(pts, -sy, sy, center=c, axis='Y')
        b = L.bevel(b, min(size) * 0.18, 1, 40)
        jitter(b, min(size) * 0.03, 4.0, seed)
    elif kind == 'bean':
        b = bm_sphere(c, (sx, sy, sz), seg=9, rings=6)
        deform(b, lambda q: V((q.x, q.y + 0.25 * sy * ((q.x - c.x) / sx) ** 2, q.z)))
        jitter(b, min(size) * 0.05, 4.0, seed)
    else:
        raise ValueError(kind)
    return b


def place_on_front(bvh, x, z, y_from=-5.0):
    hit = bvh.ray_cast(V((x, y_from, z)), V((0, 1, 0)))
    return hit[0], hit[1]


def head_with_eyes(A, kind, c, size, eyes, pivot, parent='Body', mat=WOOD, fm=None, seed=0.0, tuft=None, tilt=0.0, extra=None):
    """eyes: list of (name, dx, dz, r, style) style 'hole' | 'ring' | 'slot'. Positions relative to head centre."""
    c = V(c)
    hb = faceted_head(kind, c, size, seed)
    if tilt:
        rot(hb, 'Y', tilt, c)
    bvh = BVHTree.FromBMesh(hb)
    hd = Part('Head')
    hd.add(hb, mat, smooth=False, face_mat=fm)
    if tuft:   # brush-stroke tuft of paint sticking out of the head
        for k, (tm, off, ln) in enumerate(tuft):
            p0 = c + V(off)
            pts = [p0, p0 + V((0.01, 0.02, ln * 0.5)), p0 + V((0.03, 0.05, ln))]
            hd.add(bm_blade(pts, [ln * 0.18, ln * 0.2, ln * 0.04], thick=ln * 0.05, up=(0, 1, 0)), tm, smooth=False)
    if extra:
        for eb, em in extra:
            hd.add(eb, em, smooth=False)
    A.part(hd, pivot=pivot, parent=parent)
    for nm, dx, dz, r, style in eyes:
        hit, nrm = place_on_front(bvh, c.x + dx, c.z + dz)
        if hit is None:
            continue
        p = Part(nm)
        q = nrm.to_track_quat('-Y', 'Z')
        if style in ('hole', 'slot'):
            ry = r * (2.2 if style == 'slot' else 1.0)
            e = bm_sphere((0, 0, 0), (r, r * 0.35, ry), seg=8, rings=5)
            L.xform(e, q.to_matrix().to_4x4())
            move(e, hit - nrm * r * 0.1)
            p.add(e, INK)
        else:  # drawn ring eye (ink circle) with a tiny dot
            ring = []
            sx_ = nrm.cross(V((0, 0, 1))).normalized()
            up_ = sx_.cross(nrm).normalized() * -1
            for i in range(13):
                a = 2 * math.pi * i / 12 + 0.3
                ring.append(hit + nrm * 0.004 + sx_ * math.cos(a) * r * (1 + 0.08 * math.sin(3 * a)) + up_ * math.sin(a) * r)
            p.add(stroke(ring, r * 0.13, taper=False), INK, smooth=False)
            d = bm_sphere((0, 0, 0), (r * 0.3, r * 0.15, r * 0.3), seg=6, rings=4)
            L.xform(d, q.to_matrix().to_4x4())
            move(d, hit + sx_ * r * 0.25)
            p.add(d, INK)
        A.part(p, pivot=hit, parent='Head')
    return bvh


# =====================================================================================
def build_kinopio():
    A = Asset('Kinopio')
    for sgn in (1, -1):
        make_leg(A, sgn, (0.06 * sgn, 0.0, 0.27), (0.065 * sgn, -0.015, 0.16), (0.065 * sgn, 0.0, 0.055), 0.028,
                 foot=(0.11, 0.065, 0.05), fm=None)
    body = Part('Body')
    # shorts (red, brushed) on a round pelvis
    pel = bm_sphere((0, 0, 0.31), (0.115, 0.09, 0.07), seg=10, rings=6)
    pel = subdivide(pel, 1)
    body.add(pel, WOOD, face_mat=paint_above(0.255, RED, amp=0.025, freq=14, seed=1))
    tor = bm_lathe([(0.0, 0.33), (0.085, 0.34), (0.105, 0.4), (0.11, 0.47), (0.095, 0.53), (0.05, 0.555), (0.0, 0.56)], seg=10, sy=0.8)
    tor = subdivide(tor, 1)
    streaks(body, tor, 0.43, BLUE, n=7, ln=0.06, w=0.014, seed=2)
    body.add(tor, WOOD, face_mat=paint_above(0.43, BLUE, amp=0.012, freq=14, seed=2))
    body.add(ball((0, 0, 0.575), 0.03), JOINT)
    A.part(body, pivot=(0, 0, 0.29))
    # mark (hidden by default in Unity): red stripe on the left shoulder
    mk = Part('Mark')
    pts = [V((0.07 + 0.012 * i, -0.06 + 0.02 * i, 0.535 - 0.012 * i)) for i in range(5)]
    mk.add(bm_blade(pts, [0.006, 0.012, 0.014, 0.012, 0.004], thick=0.004, up=(0.5, -0.6, 0.8)), 'M_Mark', smooth=False)
    A.part(mk, pivot=pts[2], parent='Body')
    make_arm(A, 1, (0.115, 0.0, 0.52), (0.145, -0.01, 0.43), (0.15, -0.035, 0.345), 0.024, hand='ink', hand_size=0.075,
             fm=paint_above(0.47, BLUE, amp=0.02, freq=16, seed=3))
    make_arm(A, -1, (-0.115, 0.0, 0.52), (-0.145, -0.01, 0.43), (-0.15, -0.035, 0.345), 0.024, hand='mitten', hand_size=0.06,
             fm=paint_above(0.47, BLUE, amp=0.02, freq=16, seed=4))
    hc = V((0, -0.005, 0.69))
    head_with_eyes(A, 'hex', hc, (0.15, 0.075, 0.12),
                   eyes=[('EyeL', 0.06, 0.01, 0.017, 'hole'), ('EyeR', -0.06, 0.012, 0.026, 'ring')],
                   pivot=(0, 0, 0.58), seed=5, tuft=[(RED, (-0.06, 0.0, 0.1), 0.08), (BLUE, (-0.03, 0.01, 0.11), 0.055)])
    # long nose = translucent pencil line (retraced 3x), barely a cone
    nz = Part('Nose')
    root = hc + V((0.0, -0.085, -0.025))
    tip = root + V((0.012, -0.42, 0.03))
    nz.add(bm_tube([root, root.lerp(tip, 0.5), tip], [0.018, 0.009, 0.002], seg=6), 'M_SketchNose')
    for k, (dx, dz) in enumerate(((0.016, 0.006), (-0.014, 0.004), (0.002, -0.016))):
        p0 = root + V((dx, 0.02, dz))
        p1 = tip + V((dx * 0.2 + 0.006 * k, -0.03 * (k % 2) - 0.01, dz * 0.2))
        nz.add(stroke(wobble_line(p0, p1, 6, 0.007, k * 1.9), 0.004), 'M_SketchNose', smooth=False)
    A.part(nz, pivot=root, parent='Head')
    A.root['ouat_size'] = 0.8
    return A


# =====================================================================================
def build_villager_a():
    """Tall thin puppet with an elongated egg head (one hole eye, one slot)."""
    A = Asset('Villager_A')
    for sgn in (1, -1):
        make_leg(A, sgn, (0.09 * sgn, 0, 0.8), (0.1 * sgn, -0.02, 0.43), (0.1 * sgn, 0, 0.07), 0.042,
                 foot=(0.17, 0.08, 0.07), fm=paint_above(0.6, RED, amp=0.05, freq=10, seed=11))
    body = Part('Body')
    pel = bm_box((0, 0, 0.84), (0.27, 0.17, 0.14))
    pel = L.bevel(pel, 0.04, 2, 40)
    body.add(pel, RED, smooth=False, face_mat=paint_below(0.79, WOOD, amp=0.02, freq=14, seed=12))
    tor = bm_lathe([(0.0, 0.9), (0.11, 0.91), (0.15, 1.0), (0.17, 1.15), (0.16, 1.28), (0.08, 1.34), (0.0, 1.35)], seg=10, sy=0.72)
    tor = subdivide(tor, 1)
    streaks(body, tor, 1.08, BLUE, n=9, ln=0.14, w=0.028, seed=13)
    body.add(tor, WOOD, face_mat=paint_above(1.08, BLUE, amp=0.02, freq=9, seed=13))
    body.add(ball((0, 0, 0.88), 0.05), JOINT)
    body.add(capsule((0, 0, 1.33), (0, -0.03, 1.42), 0.03, 0.028, seg=6), WOOD)
    A.part(body, pivot=(0, 0, 0.84))
    make_arm(A, 1, (0.17, 0.0, 1.27), (0.21, -0.02, 1.0), (0.22, -0.05, 0.74), 0.034, hand='mitten', hand_size=0.08,
             fm=paint_above(1.13, BLUE, amp=0.04, freq=12, seed=14))
    make_arm(A, -1, (-0.17, 0.0, 1.27), (-0.21, -0.02, 1.0), (-0.22, -0.07, 0.75), 0.034, hand='ink', hand_size=0.11,
             fm=paint_above(1.13, BLUE, amp=0.04, freq=12, seed=15))
    head_with_eyes(A, 'egg', (0.0, -0.04, 1.58), (0.1, 0.095, 0.16),
                   eyes=[('EyeL', 0.035, 0.03, 0.022, 'hole'), ('EyeR', -0.04, 0.0, 0.012, 'slot')],
                   pivot=(0, -0.03, 1.42), seed=16, tilt=8, tuft=[(RED, (-0.05, 0.0, 0.12), 0.11), (RED, (-0.02, 0.02, 0.13), 0.08)],
                   fm=paint_above(1.68, BLUE, amp=0.03, freq=12, seed=17))
    A.root['ouat_size'] = 1.7
    return A


def build_villager_b():
    """Squat boxy puppet with a dice-like box head (three holes), overalls."""
    A = Asset('Villager_B')
    for sgn in (1, -1):
        make_leg(A, sgn, (0.13 * sgn, 0, 0.36), (0.14 * sgn, -0.02, 0.2), (0.14 * sgn, 0, 0.06), 0.055,
                 foot=(0.2, 0.13, 0.08), fm=paint_below(0.12, RED, amp=0.03, freq=12, seed=21), ink_shin=(sgn < 0))
    body = Part('Body')
    tor = bm_box((0, 0, 0.6), (0.52, 0.32, 0.44))
    tor = L.bevel(tor, 0.06, 2, 40)
    deform(tor, lambda c: V((c.x * (1 + 0.12 * (c.z - 0.6) / 0.22), c.y, c.z)))
    tor = subdivide(tor, 1)
    streaks(body, tor, 0.72, BLUE, n=10, ln=0.1, w=0.03, seed=23)
    streaks(body, tor, 0.56, RED, n=10, ln=0.09, w=0.03, down=False, seed=22)
    body.add(tor, WOOD, face_mat=L.chain(paint_below(0.56, RED, amp=0.018, freq=10, seed=22), paint_above(0.72, BLUE, amp=0.015, freq=12, seed=23)))
    # suspenders: two blue painted straps down the front
    for sx in (-0.12, 0.12):
        body.add(bm_blade([V((sx, -0.17, 0.81)), V((sx, -0.172, 0.68)), V((sx * 0.9, -0.17, 0.55))], [0.022, 0.022, 0.02], thick=0.006, up=(0, -1, 0)), BLUE, smooth=False)
    body.add(ball((0, 0, 0.86), 0.05), JOINT)
    A.part(body, pivot=(0, 0, 0.4))
    make_arm(A, 1, (0.31, 0.0, 0.74), (0.37, -0.03, 0.56), (0.38, -0.08, 0.4), 0.055, hand='mitten', hand_size=0.12,
             fm=paint_above(0.66, BLUE, amp=0.04, freq=10, seed=24))
    make_arm(A, -1, (-0.31, 0.0, 0.74), (-0.37, -0.03, 0.56), (-0.38, -0.08, 0.4), 0.055, hand='ink', hand_size=0.14,
             fm=paint_above(0.66, BLUE, amp=0.04, freq=10, seed=25))
    head_with_eyes(A, 'box', (0.0, -0.02, 1.02), (0.13, 0.12, 0.12),
                   eyes=[('EyeL', 0.055, 0.04, 0.022, 'hole'), ('EyeR', -0.05, -0.01, 0.026, 'hole')],
                   pivot=(0, 0, 0.88), seed=26, tilt=-7,
                   extra=[(L.move(L.bm_sphere((0, 0, 0), (0.016, 0.006, 0.016), seg=6, rings=4), (0.03, -0.145, 0.95)), INK)],
                   tuft=[(RED, (-0.08, 0.0, 0.11), 0.07)])
    A.root['ouat_size'] = 1.15
    return A


def build_villager_c():
    """Hunched egg-bodied puppet; one long arm drawn only as ink lines down to the ground."""
    A = Asset('Villager_C')
    for sgn in (1, -1):
        make_leg(A, sgn, (0.1 * sgn, 0.02, 0.5), (0.12 * sgn, -0.04, 0.28), (0.12 * sgn, 0, 0.06), 0.045,
                 foot=(0.16, 0.09, 0.07), fm=paint_above(0.32, RED, amp=0.05, freq=10, seed=31))
    body = Part('Body')
    tor = bm_sphere((0, 0.0, 0.85), (0.28, 0.24, 0.36), seg=12, rings=8)
    deform(tor, lambda c: V((c.x, c.y - 0.35 * max(0, c.z - 0.75) ** 1.3, c.z)))
    tor = subdivide(tor, 1)
    jitter(tor, 0.012, 4, 32)
    streaks(body, tor, 0.68, RED, n=10, ln=0.12, w=0.035, down=False, seed=33)
    streaks(body, tor, 1.04, BLUE, n=8, ln=0.1, w=0.03, seed=34, center=(0, -0.1))
    body.add(tor, WOOD, face_mat=L.chain(paint_below(0.68, RED, amp=0.02, freq=8, seed=33), paint_above(1.04, BLUE, amp=0.02, freq=10, seed=34)))
    # a drawn triangle mark on the chest (ink)
    t0 = V((0.06, -0.255, 0.92))
    body.add(stroke([t0, t0 + V((0.05, 0.0, 0.07)), t0 + V((0.1, 0.01, 0.0)), t0], 0.005, taper=False), INK, smooth=False)
    A.part(body, pivot=(0, 0, 0.55))
    make_arm(A, 1, (0.25, -0.12, 1.02), (0.33, -0.2, 0.8), (0.32, -0.26, 0.6), 0.042, hand='mitten', hand_size=0.1,
             fm=paint_above(0.92, BLUE, amp=0.04, freq=10, seed=35))
    make_arm(A, -1, (-0.25, -0.12, 1.0), (-0.32, -0.2, 0.72), (-0.33, -0.3, 0.12), 0.042, ink_fore=True, hand_size=0.13,
             fm=paint_above(0.92, BLUE, amp=0.04, freq=10, seed=36))
    head_with_eyes(A, 'bean', (0.05, -0.32, 1.17), (0.14, 0.11, 0.11),
                   eyes=[('EyeL', 0.05, 0.02, 0.025, 'hole'), ('EyeR', -0.05, 0.01, 0.022, 'ring')],
                   pivot=(0.0, -0.22, 1.08), seed=37, tilt=-14, tuft=[(BLUE, (0.0, 0.02, 0.09), 0.08)])
    A.root['ouat_size'] = 1.35
    return A


def build_silhouette_a():
    A = Asset('Silhouette_A')
    S = 'M_Silhouette'
    for sgn in (1, -1):
        make_leg(A, sgn, (0.09 * sgn, 0, 0.75), (0.1 * sgn, -0.02, 0.4), (0.1 * sgn, 0, 0.07), 0.04, foot=(0.16, 0.08, 0.07), mat=S, jmat=S)
    body = Part('Body')
    tor = bm_lathe([(0.0, 0.8), (0.13, 0.81), (0.2, 0.95), (0.22, 1.15), (0.2, 1.27), (0.1, 1.33), (0.0, 1.34)], seg=10, sy=0.75)
    tor = subdivide(tor, 1)
    body.add(tor, S)
    A.part(body, pivot=(0, 0, 0.8))
    make_arm(A, 1, (0.2, 0, 1.25), (0.25, -0.03, 0.98), (0.26, -0.06, 0.72), 0.035, mat=S, jmat=S, hand_size=0.08)
    make_arm(A, -1, (-0.2, 0, 1.25), (-0.26, -0.06, 1.02), (-0.27, -0.14, 0.8), 0.035, mat=S, jmat=S, hand_size=0.08)
    head_with_eyes(A, 'egg', (0.02, -0.08, 1.53), (0.11, 0.1, 0.15), eyes=[], pivot=(0, -0.02, 1.36), mat=S, seed=41, tilt=-10)
    A.root['ouat_size'] = 1.6
    return A


def build_silhouette_b():
    A = Asset('Silhouette_B')
    S = 'M_Silhouette'
    for sgn in (1, -1):
        make_leg(A, sgn, (0.14 * sgn, 0, 0.34), (0.15 * sgn, -0.02, 0.19), (0.15 * sgn, 0, 0.06), 0.055, foot=(0.2, 0.12, 0.08), mat=S, jmat=S)
    body = Part('Body')
    tor = bm_box((0, 0, 0.6), (0.56, 0.34, 0.46))
    tor = L.bevel(tor, 0.08, 2, 40)
    body.add(tor, S)
    A.part(body, pivot=(0, 0, 0.38))
    make_arm(A, 1, (0.33, 0, 0.76), (0.38, -0.03, 0.56), (0.39, -0.08, 0.38), 0.055, mat=S, jmat=S, hand_size=0.12)
    make_arm(A, -1, (-0.33, 0, 0.76), (-0.38, -0.03, 0.56), (-0.39, -0.08, 0.38), 0.055, mat=S, jmat=S, hand_size=0.12)
    head_with_eyes(A, 'box', (0.03, -0.02, 1.0), (0.14, 0.12, 0.11), eyes=[], pivot=(0, 0, 0.84), mat=S, seed=42, tilt=12)
    A.root['ouat_size'] = 1.1
    return A


# =====================================================================================
def build_mother():
    """Pear-bellied tall puppet (~2 m). Right hand holds a long cloth (child Cloth of ArmR)."""
    A = Asset('Mother')
    for sgn in (1, -1):
        make_leg(A, sgn, (0.15 * sgn, 0.02, 0.38), (0.16 * sgn, -0.02, 0.22), (0.16 * sgn, 0, 0.06), 0.05,
                 foot=(0.18, 0.1, 0.07), fm=paint_above(0.25, RED, amp=0.04, freq=10, seed=51))
    body = Part('Body')
    pear = bm_lathe([(0.0, 0.32), (0.22, 0.34), (0.36, 0.5), (0.4, 0.72), (0.36, 0.95), (0.26, 1.15), (0.17, 1.32), (0.13, 1.45), (0.0, 1.5)], seg=14, sy=0.9)
    deform(pear, lambda c: V((c.x, c.y - 0.16 * math.exp(-((c.z - 0.72) / 0.28) ** 2) * max(0.0, -c.y / 0.36), c.z)))
    pear = subdivide(pear, 1)
    jitter(pear, 0.01, 4, 52)
    streaks(body, pear, 1.05, BLUE, n=12, ln=0.2, w=0.045, seed=53)
    streaks(body, pear, 0.6, RED, n=12, ln=0.22, w=0.05, down=False, seed=54)
    body.add(pear, WOOD, face_mat=L.chain(paint_above(1.05, BLUE, amp=0.025, freq=8, seed=53), paint_below(0.6, RED, amp=0.03, freq=7, seed=54)))
    body.add(ball((0, 0, 1.53), 0.05), JOINT)
    body.add(capsule((0, -0.01, 1.52), (0, -0.06, 1.66), 0.035, 0.03, seg=6), WOOD)
    A.part(body, pivot=(0, 0, 0.4))
    hands = {}
    sh, el, wr = V((0.19, -0.02, 1.38)), V((0.33, -0.12, 1.02)), V((0.3, -0.36, 0.78))
    make_arm(A, 1, sh, el, wr, 0.04, hand='ink', hand_size=0.13, fm=paint_above(1.12, BLUE, amp=0.05, freq=10, seed=55))
    sh2, el2, wr2 = V((-0.19, -0.02, 1.38)), V((-0.36, -0.08, 1.0)), V((-0.4, -0.2, 0.66))
    make_arm(A, -1, sh2, el2, wr2, 0.04, hand='mitten', hand_size=0.1, fm=paint_above(1.12, BLUE, amp=0.05, freq=10, seed=56))
    head_with_eyes(A, 'egg', (0.0, -0.1, 1.8), (0.1, 0.1, 0.15),
                   eyes=[('EyeL', 0.0, 0.03, 0.016, 'slot')],
                   pivot=(0, -0.06, 1.65), seed=57, tilt=0, tuft=[(BLUE, (-0.04, 0.02, 0.12), 0.09)],
                   fm=paint_above(1.9, BLUE, amp=0.03, freq=12, seed=58))
    # cloth hanging from the right hand: unpainted paper with an ink hem
    cl = Part('Cloth')
    h0 = wr2 + (wr2 - el2).normalized() * 0.1
    pts = [h0, h0 + V((-0.03, -0.04, -0.2)), h0 + V((0.01, -0.02, -0.4)), h0 + V((-0.02, 0.03, -0.55)), h0 + V((0.03, 0.0, -0.62))]
    c = bm_blade(pts, [0.06, 0.12, 0.13, 0.12, 0.1], thick=0.012, up=(0, 1, 0.1))
    c = subdivide(c, 1)
    deform(c, lambda q: q + V((0, 0.03 * math.sin((q.z - h0.z) * 9), 0)))
    cl.add(c, 'M_Paper')
    for k in range(3):
        e0 = pts[-1] + V((-0.07 + 0.07 * k, 0, 0.0))
        cl.add(stroke([e0, e0 + V((0.005 * k, 0.0, -0.07 - 0.02 * k))], 0.005), INK, smooth=False)
    A.part(cl, pivot=h0, parent='ArmR')
    A.root['ouat_size'] = 2.0
    return A


# =====================================================================================
def build_chief():
    """Guardian village tree (당산나무형 수호목) built like a puppet: ball joints, root feet, branch arms,
    crown wider toward the top, hole-eyes in the trunk, straw rope (금줄) with paper strips."""
    A = Asset('Chief')
    BARK, LEAF = 'M_Bark', 'M_Leaf'
    for sgn in (1, -1):
        nm = 'LegL' if sgn > 0 else 'LegR'
        p = Part(nm)
        hip = V((0.32 * sgn, 0.0, 0.9))
        knee = V((0.42 * sgn, -0.08, 0.5))
        foot = V((0.48 * sgn, -0.05, 0.14))
        p.add(ball(hip, 0.2), JOINT)
        lg = bm_tube([hip, hip.lerp(knee, 0.5) + V((0.03 * sgn, 0, 0)), knee], [0.17, 0.15, 0.14], seg=8)
        jitter(lg, 0.02, 3, 20 + sgn)
        p.add(lg, BARK)
        p.add(ball(knee, 0.15), JOINT)
        p.add(bm_tube([knee, foot], [0.13, 0.15], seg=8), BARK)
        for k, ang in enumerate((-75, -25, 25, 70, 170)):
            a = math.radians(ang) * sgn
            d = V((math.sin(a) * sgn * -1 if False else math.sin(a), -math.cos(a), 0))
            ln = 0.5 if k < 4 else 0.32
            rt = bm_tube([foot, foot + d * ln * 0.45 + V((0, 0, -0.07)), foot + d * ln + V((0, 0, -0.12))], [0.11, 0.07, 0.025], seg=6)
            jitter(rt, 0.015, 5, k + sgn * 3)
            p.add(rt, BARK)
        A.part(p, pivot=hip)
    body = Part('Body')
    pts = [V((0, 0, 0.85)), V((0.03, 0.0, 1.15)), V((-0.02, 0.02, 1.45)), V((0.02, 0.0, 1.75)), V((0, 0, 2.0))]
    tr = bm_tube(pts, [0.4, 0.34, 0.33, 0.4, 0.5], seg=10, twist=0.35)
    jitter(tr, 0.045, 2.0, 30)
    tr = subdivide(tr, 1)
    body.add(tr, BARK)
    for k in range(4):
        a0 = 2 * math.pi * k / 4 + 0.6
        sp = []
        for i in range(6):
            t = i / 5
            z = 1.0 + 0.85 * t
            r = 0.35 + 0.07 * t + 0.025
            a = a0 + 0.9 * t
            sp.append(V((math.cos(a) * r, math.sin(a) * r, z)))
        body.add(stroke(sp, 0.008), INK, smooth=False)
    rope = [V((math.cos(2 * math.pi * i / 16) * 0.37, math.sin(2 * math.pi * i / 16) * 0.37, 1.42 + 0.03 * math.sin(i))) for i in range(17)]
    body.add(bm_tube(rope, 0.045, seg=6, cap=False, twist=0.9), 'M_PaperShade')
    for k in range(5):
        a = math.radians(-130 + k * 25)
        p0 = V((math.cos(a) * 0.4, math.sin(a) * 0.4, 1.39))
        pr = p0 + V((math.cos(a) * 0.02, math.sin(a) * 0.02, -0.22 - 0.05 * (k % 2)))
        body.add(bm_blade([p0, p0.lerp(pr, 0.5), pr], [0.04, 0.045, 0.035], thick=0.006, up=(math.cos(a), math.sin(a), 0)), 'M_Paper', smooth=False)
    body.add(ball((0, 0, 0.88), 0.3), JOINT)
    A.part(body, pivot=(0, 0, 0.9))

    for sgn in (1, -1):
        nm = 'ArmL' if sgn > 0 else 'ArmR'
        p = Part(nm)
        sh = V((0.5 * sgn, -0.02, 1.88))
        el = V((0.86 * sgn, -0.1, 1.45))
        wr = V((0.92 * sgn, -0.22, 0.95))
        p.add(ball(sh, 0.17), JOINT)
        p.add(bm_tube([sh, sh.lerp(el, 0.5) + V((0.04 * sgn, 0, 0.03)), el], [0.13, 0.11, 0.1], seg=7, twist=0.4), BARK)
        p.add(ball(el, 0.12), JOINT, face_mat=L.ragged(lambda c: c.x * sgn, 0.0, RED, amp=0.05, freq=12, seed=47 + sgn) if sgn > 0 else None)
        p.add(bm_tube([el, el.lerp(wr, 0.5) + V((0.02 * sgn, 0, 0)), wr], [0.1, 0.085, 0.09], seg=7, twist=0.3), BARK)
        for k, d in enumerate((V((0.06 * sgn, -0.07, -0.22)), V((-0.06 * sgn, -0.12, -0.17)), V((0.0, 0.04, -0.2)))):
            p.add(bm_tube([wr, wr + d * 0.6, wr + d], [0.06, 0.04, 0.02], seg=5), BARK)
        tw = [el, el + V((0.2 * sgn, 0.05, 0.25)), el + V((0.27 * sgn, 0.08, 0.42))]
        p.add(bm_tube(tw, [0.04, 0.025, 0.01], seg=5), BARK)
        lf = bm_sphere(tw[-1] + V((0.02 * sgn, 0, 0.05)), (0.17, 0.14, 0.12), seg=6, rings=4)
        jitter(lf, 0.03, 6, 44 + sgn)
        p.add(lf, LEAF, smooth=False)
        A.part(p, pivot=sh, parent='Body')

    head = Part('Head')
    hb = bm_tube([V((0, 0, 1.95)), V((0, 0.0, 2.25)), V((0, 0.03, 2.55))], [0.48, 0.58, 0.72], seg=10, twist=0.2)
    jitter(hb, 0.045, 2.0, 50)
    hb = subdivide(hb, 1)
    head.add(hb, BARK)
    import random
    rnd = random.Random(5)
    tips = []
    for i in range(11):
        a = 2 * math.pi * i / 11 + rnd.uniform(-0.2, 0.2)
        rr = rnd.uniform(1.0, 1.75)
        tips.append(V((math.cos(a) * rr, math.sin(a) * rr * 0.62, rnd.uniform(2.75, 3.3))))
    for i, tp in enumerate(tips):
        st = V((tp.x * 0.18, tp.y * 0.18, 2.42))
        mid = st.lerp(tp, 0.45) + V((0, 0, 0.28))
        br = bm_tube([st, mid, tp], [0.16, 0.1, 0.045], seg=6)
        jitter(br, 0.03, 3, 60 + i)
        head.add(br, BARK)
        if i % 3 == 0:
            head.add(ball(mid, 0.1, seg=6, rings=4), JOINT)
    A.part(head, pivot=(0, 0, 1.95), parent='Body')
    cn = Part('Canopy')
    for i, tp in enumerate(tips):
        for j in range(2 if i % 2 == 0 else 1):
            c = tp + V((rnd.uniform(-0.2, 0.2), rnd.uniform(-0.15, 0.15), 0.04 + 0.1 * j))
            r = (rnd.uniform(0.34, 0.52), rnd.uniform(0.28, 0.4), rnd.uniform(0.13, 0.2))
            cb = bm_sphere(c, r, seg=5, rings=3)
            rot(cb, 'Z', rnd.uniform(0, 180), c)
            rot(cb, 'X', rnd.uniform(-15, 15), c)
            jitter(cb, 0.07, 2.5, 70 + i * 3 + j)
            cn.add(cb, LEAF, smooth=False)
    # a few twigs between: ink lines
    for i, tp in enumerate(tips):
        out = V((tp.x, tp.y, 0)).normalized()
        for j in range(2):
            p0 = tp + V((0, 0, 0.05 * j))
            p1 = p0 + out * rnd.uniform(0.3, 0.55) + V((rnd.uniform(-0.15, 0.15), 0, rnd.uniform(0.15, 0.45)))
            cn.add(stroke(wobble_line(p0, p1, 4, 0.03, i * 2 + j), 0.008), INK, smooth=False)
    A.part(cn, pivot=(0, 0, 2.55), parent='Head')
    for sgn, nm in ((1, 'EyeL'), (-1, 'EyeR')):
        c = V((0.2 * sgn, -0.58, 2.3 + (0.03 if sgn > 0 else -0.02)))
        p = Part(nm)
        s = bm_sphere(c, (0.09, 0.05, 0.075 if sgn > 0 else 0.06), seg=8, rings=5)
        p.add(s, INK)
        A.part(p, pivot=c, parent='Head')
    A.scale_all(0.86)
    A.root['ouat_size'] = 3.2
    return A


# =====================================================================================
def build_lump(variant=1):
    """Failed 'returned' bodies left on chairs: a slumped wooden mass with fused joints, paint smears, ink lines.
    Root origin = bottom centre (sits on the chair seat)."""
    A = Asset(f'Lump_{variant}')
    cfg = {1: dict(h=0.55, r=0.3, lean=0.06, seed=81, paint=BLUE),
           2: dict(h=0.7, r=0.26, lean=0.12, seed=82, paint=RED),
           3: dict(h=0.4, r=0.4, lean=0.0, seed=83, paint=BLUE)}[variant]
    h, r, sd = cfg['h'], cfg['r'], cfg['seed']
    body = Part('Body')
    prof = [(0.0, 0.0), (r * 1.05, 0.0), (r * 1.08, h * 0.12), (r * 0.95, h * 0.4), (r * 0.72, h * 0.72), (r * 0.4, h * 0.93), (0.0, h)]
    b = bm_lathe(prof, seg=12)

    def sag(c):
        t = c.z / h
        c.y -= cfg['lean'] * t * t
        c.x += 0.05 * math.sin(c.z * 7 + sd) * t
        return c
    deform(b, sag)
    b = subdivide(b, 1)
    jitter(b, 0.03, 4.0, sd)
    deform(b, lambda c: V((c.x, c.y, max(0.0, c.z))))
    streaks(body, b, h * 0.62, cfg['paint'], n=6, ln=h * 0.5, w=0.05, seed=sd, arc=(-150, 30))
    body.add(b, WOOD, face_mat=L.ragged(lambda c: c.z / h + 0.25 * (c.x * 0.8 - c.y * 0.6) / r, 0.62, cfg['paint'], amp=0.06, freq=7, seed=sd))
    # fused ball joints sticking out of the mass
    for k in range(3):
        a = 2 * math.pi * k / 3 + sd
        c = V((math.cos(a) * r * 0.85, math.sin(a) * r * 0.85, h * (0.3 + 0.2 * k)))
        body.add(ball(c, 0.05 + 0.015 * k, seg=7, rings=5), JOINT)
    # a stub of a limb, and an arm that is only drawn
    n0 = V((r * 0.75, -r * 0.45, h * 0.5))
    body.add(capsule(n0, n0 + V((0.1, -0.1, -0.08)), 0.045, 0.035, seg=6), WOOD)
    a0 = V((-r * 0.8, -r * 0.3, h * 0.55))
    body.add(stroke(wobble_line(a0, a0 + V((-0.12, -0.08, -0.25)), 4, 0.01, sd), 0.006), INK, smooth=False)
    body.add(stroke(wobble_line(a0 + V((0, 0, -0.05)), a0 + V((-0.09, -0.1, -0.3)), 4, 0.01, sd + 1), 0.006), INK, smooth=False)
    for k in range(3):
        a = 2.2 + 0.5 * k + sd
        p0 = V((math.cos(a) * r * 0.9, math.sin(a) * r * 0.9, h * (0.2 + 0.15 * k)))
        p1 = V((math.cos(a + 0.5) * r * 0.8, math.sin(a + 0.5) * r * 0.8, h * (0.28 + 0.15 * k)))
        body.add(stroke(wobble_line(p0, p1, 4, 0.02, k + sd), 0.007), INK, smooth=False)
    A.part(body, pivot=(0, 0, 0))
    if variant == 2:
        mk = Part('Mark')
        pts = []
        for i in range(7):
            t = i / 6
            a = math.radians(-70 + 70 * t)
            z = h * (0.72 - 0.12 * t)
            rr = r * 0.8 + 0.035
            pts.append(V((math.cos(a) * rr, math.sin(a) * rr - cfg['lean'] * (z / h) ** 2, z)))
        mk.add(bm_blade(pts, [0.012, 0.022, 0.026, 0.026, 0.024, 0.02, 0.008], thick=0.006, up=(1, -1, 0.6)), 'M_Mark', smooth=False)
        A.part(mk, pivot=pts[3], parent='Body')
    A.root['ouat_size'] = 0.6
    return A


def build_lump_1():
    return build_lump(1)


def build_lump_2():
    return build_lump(2)


def build_lump_3():
    return build_lump(3)


# =====================================================================================
def build_puppet():
    """Wooden stage puppet sitting in the inner-body seat (seat top 0.47 above root). ArmR raised, pointing forward.
    Painted blue like a guess at the 'inner body' (the hero), crude crest pegs. Rope = human rope (M_Rope)."""
    A = Asset('Puppet')
    seat = 0.47
    for sgn in (1, -1):
        nm = 'LegL' if sgn > 0 else 'LegR'
        p = Part(nm)
        hip = V((0.1 * sgn, 0.05, seat + 0.06))
        knee = V((0.11 * sgn, -0.28, seat + 0.07))
        ankle = V((0.12 * sgn, -0.32, 0.07))
        p.add(ball(hip, 0.05), JOINT)
        p.add(capsule(hip, knee, 0.05, 0.043), WOOD)
        p.add(ball(knee, 0.045), JOINT)
        p.add(capsule(knee, ankle, 0.04, 0.034), WOOD)
        p.add(block_foot(ankle, 0.15, 0.08, 0.06), WOOD, smooth=False)
        A.part(p, pivot=hip)
    body = Part('Body')
    pel = bm_sphere((0, 0.05, seat + 0.08), (0.15, 0.11, 0.08), seg=10, rings=6)
    body.add(pel, WOOD)
    body.add(ball((0, 0.05, seat + 0.17), 0.055), JOINT)
    tor = bm_lathe([(0.0, seat + 0.2), (0.12, seat + 0.21), (0.15, seat + 0.35), (0.17, seat + 0.48), (0.08, seat + 0.53), (0.0, seat + 0.54)], seg=10, center=(0, 0.06, 0), sy=0.75)
    tor = subdivide(tor, 1)
    streaks(body, tor, seat + 0.32, BLUE, n=7, ln=0.07, w=0.018, seed=91, center=(0, 0.06))
    body.add(tor, WOOD, face_mat=paint_above(seat + 0.32, BLUE, amp=0.015, freq=10, seed=91))
    body.add(capsule((0, 0.06, seat + 0.53), (0, 0.06, seat + 0.6), 0.035, 0.03, seg=6), JOINT)
    A.part(body, pivot=(0, 0.05, seat + 0.08))
    hc = V((0, 0.05, seat + 0.72))
    pegs = []
    for k, sx in enumerate((-0.04, 0.0, 0.04)):
        p0 = hc + V((sx, 0.0, 0.11))
        pegs.append((bm_tube([p0, p0 + V((sx * 0.6, 0.04, 0.09 + 0.03 * (k == 1)))], [0.022, 0.008], seg=5), BLUE))
    head_with_eyes(A, 'egg', hc, (0.12, 0.115, 0.13),
                   eyes=[('EyeL', 0.045, 0.01, 0.017, 'hole'), ('EyeR', -0.045, 0.01, 0.017, 'hole')],
                   pivot=(0, 0.05, seat + 0.58), seed=92, extra=pegs,
                   fm=paint_above(hc.z + 0.03, BLUE, amp=0.03, freq=12, seed=93))
    for sgn in (1, -1):
        sh = V((0.18 * sgn, 0.06, seat + 0.47))
        if sgn > 0:
            el, wr = V((0.21, 0.0, seat + 0.26)), V((0.16, -0.18, seat + 0.17))
        else:
            el, wr = V((-0.24, -0.18, seat + 0.58)), V((-0.26, -0.45, seat + 0.72))
        nm = 'ArmL' if sgn > 0 else 'ArmR'
        p = Part(nm)
        p.add(ball(sh, 0.045), JOINT)
        p.add(capsule(sh, el, 0.04, 0.035), WOOD, face_mat=paint_above(seat + 0.38, BLUE, amp=0.03, freq=14, seed=94 + sgn))
        p.add(ball(el, 0.04), JOINT)
        p.add(capsule(el, wr, 0.035, 0.03), WOOD)
        tip = wr + (wr - el).normalized() * 0.09
        p.add(bm_tube([wr, tip], [0.04, 0.012], seg=6), WOOD)
        A.part(p, pivot=sh, parent='Body')
    rp = Part('Rope')
    for k, z in enumerate((seat + 0.3, seat + 0.42)):
        loop = []
        for i in range(19):
            a = 2 * math.pi * i / 18
            loop.append(V((math.cos(a) * 0.19, 0.11 + math.sin(a) * 0.17, z + 0.015 * math.sin(3 * a + k))))
        rp.add(bm_tube(loop, 0.018, seg=5, cap=False, twist=1.2), 'M_Rope')
    knot = V((0.0, -0.075, seat + 0.36))
    rp.add(bm_sphere(knot, (0.04, 0.03, 0.035), seg=6, rings=4), 'M_Rope')
    rp.add(bm_tube([knot, knot + V((0.03, -0.02, -0.1)), knot + V((0.02, -0.04, -0.2))], [0.016, 0.015, 0.012], seg=5), 'M_Rope')
    rp.add(bm_tube([knot, knot + V((-0.04, -0.02, -0.08)), knot + V((-0.06, -0.03, -0.15))], [0.016, 0.015, 0.012], seg=5), 'M_Rope')
    A.part(rp, pivot=knot)
    # sit back so the rope loops reach the stage seat back (+0.42..0.5 behind Stage/PuppetSpot)
    A.offset_all((0, 0.16, 0))
    A.meta['note'] = 'Root = Stage/PuppetSpot (seat-front floor). Seat top 0.47 above root. Rope = human rope; hide/animate it when untied.'
    A.root['ouat_size'] = 1.0
    return A
