# -*- coding: utf-8 -*-
"""Chapter-1 story props for the 'stand-in' story (10/23 design: the fish = the king's courier, offerings, red cord).
Blender coords: Z up, front -Y, root = floor centre unless noted. Same rules as ouat_dressing (round 5):
  * human objects (book, spoon, button, clock, bottle, glasses, umbrella...) = finished, original strong colour
  * creature-made things = unfinished in FORM: a built shell that stops at a torn edge, the rest pencil construction
Solid parts carry paper/painted materials only; ink / pencil / smudge live in 'Lines'."""
import math, random
import bmesh
from mathutils import Vector, Matrix
from mathutils.bvhtree import BVHTree
import ouat_lib as L
from ouat_lib import (Part, Asset, bm_sphere, bm_tube, bm_blade, bm_box, bm_cyl, bm_lathe, bm_prism, stroke,
                      wobble_line, rot, move, deform, jitter, nvec, nval)
import ouat_craft as CR
import ouat_props as P
import ouat_dressing as D

V = Vector
PAPER, SHADE, INK, HATCH = 'M_Paper', 'M_PaperShade', 'M_Ink', 'M_Hatch'
PENCIL, BACK, SMUDGE, FAINT = 'M_Pencil', 'M_PaperBack', 'M_Smudge', 'M_SketchLine'
PWOOD, PJOINT, RED, BLUE, NAVY = 'M_PuppetWood', 'M_PuppetJoint', 'M_PaintRed', 'M_PaintBlue', 'M_PaintNavy'
SACK, SACKD, OFFER, OFFERB = 'M_Sackcloth', 'M_SackDark', 'M_OfferRed', 'M_OfferRedBrush'
merge, tri_ngons, line = CR.merge, CR.tri_ngons, D.line


class Kit(D.Kit):
    """D.Kit whose finish() builds parents before children whatever the insertion order."""

    def finish(self, size, note, pivots=None, parents=None):
        parents = parents or {}
        done, order = set(), []

        def visit(n):
            if n in done:
                return
            if parents.get(n) in self.parts:
                visit(parents[n])
            done.add(n)
            order.append(n)
        for n in list(self.order):
            visit(n)
        self.order = order
        return D.Kit.finish(self, size, note, pivots, parents)

L.MATS.update({
    'M_Sackcloth':     ('CFC3A4', '978C76', True,  'paper',   {'hatch': True, 'note': 'collector sack / rag cloth: creature-woven paper cloth (drains with the world)'}),
    'M_SackDark':      ('7F786A', '57524A', True,  'paper',   {'note': 'inside of a sack, twine lashings, rag folds in deep shade'}),
    'M_OfferRed':      ('C8302A', '8C1E1A', True,  'painted', {'keep': True, 'note': "village offering mark: brush-painted red cloth strip (RedCord, cords on lumps / sacks). KEEP saturation: the one creature-made colour that must read at once"}),
    'M_OfferRedBrush': ('C8302A', '8C1E1A', False, 'painted', {'keep': True, 'note': 'dry-brush streaks and frayed threads of the red cord (flush strokes, no outline, keep)'}),
    'M_DecreeBand':    ('E4D9BC', 'ADA184', True,  'paper',   {'note': "the king's interpretation band: creature paper, yellowed. Face plane carries the glyph texture"}),
    'M_KingSeal':      ('5A2240', '391428', True,  'painted', {'keep': True, 'note': "the king's wax seal and tie: deep plum (the king's colour), keep"}),
    'M_BellBronze':    ('8A7347', '5B4A2C', True,  'painted', {'note': 'plaza bell: a creature copy of a fallen bell, painted bronze (drains; NOT human brass)'}),
    'M_BellInner':     ('3E3324', '2A2218', False, 'painted', {'note': 'inside of the bell mouth'}),
    'M_Glass':         ('4F9772', '2F6449', True,  'painted', {'keep': True, 'note': 'human bottle glass (green), keep'}),
    'M_Shaving':       ('F0DBB4', 'C9A87C', True,  'paper',   {'note': 'fresh-cut puppet-wood shavings (paler than M_PuppetWood)'}),
    'M_Whetstone':     ('B3AFA4', '7F7C74', True,  'paper',   {'hatch': True, 'note': 'nose-filing stone (grey paper-stone)'}),
})
# character paint slots (owned by ouat_chars_v2, same values; already in art_materials.json) - only so this module builds alone
for _k, _v in {
    'M_PaintNavy':      ('2A3A78', '1C2752', True, 'painted', {'note': 'brushed-on navy paint (suspenders, trims)'}),
    'M_PaintRedBrush':  ('C23A2E', '8E2A22', False, 'painted', {'note': 'dry-brush streaks running off a red paint edge (flush strokes, NO outline)'}),
    'M_PaintBlueBrush': ('5B86C9', '3D6198', False, 'painted', {'note': 'dry-brush streaks running off a blue paint edge (flush strokes, NO outline)'}),
}.items():
    L.MATS.setdefault(_k, _v)


# ===================================================================== small helpers
def lathe_g(profile, seg=14, cx=0.0, cy=0.0, sy=1.0):
    b = bm_lathe(profile, seg=seg, center=(cx, cy, 0), sy=sy, cap_top=False, cap_bottom=False)
    tri_ngons(b)
    CR.orient_out(b, (cx, cy))
    return b


def xf(b, rx=0.0, ry=0.0, rz=0.0, pos=(0, 0, 0), s=1.0):
    if s != 1.0:
        L.xform(b, Matrix.Scale(s, 4))
    if rx:
        rot(b, 'X', rx)
    if ry:
        rot(b, 'Y', ry)
    if rz:
        rot(b, 'Z', rz)
    move(b, pos)
    return b


def put_pieces(K, part, pieces, pos, rz=0.0, rx=0.0, ry=0.0, s=1.0):
    for b, m in pieces:
        K.add(part, xf(b, rx, ry, rz, pos, s), m, False)


def ray_down(bvh, x, y, z0=5.0):
    hit = bvh.ray_cast(V((x, y, z0)), V((0, 0, -1)))
    return hit[0].z if hit[0] is not None else 0.0


def weave(K, part, bvh, center, dirs, n=6, ln=0.5, step=0.06, r=0.004, seed=0.0, mat=INK, keep=None, lift=0.008):
    """coarse weave strokes projected onto a surface along horizontal ray directions (sack / rag texture)"""
    rnd = random.Random(int(seed * 31) + 3)
    c = V(center)
    for k in range(n):
        a = rnd.uniform(*dirs)
        z = c.z + rnd.uniform(-ln, ln)
        pts = []
        for t in range(6):
            aa = a + (t - 2.5) * step
            d = V((math.cos(aa), math.sin(aa), 0))
            hit = bvh.ray_cast(V((c.x, c.y, z + (t - 2.5) * 0.01)) + d * 3.0, -d)
            if hit[0] is None:
                break
            if keep is not None and not keep(hit[0]):
                break
            pts.append(hit[0] + hit[1] * lift)
        if len(pts) >= 3:
            K.add(part, stroke(pts, r * rnd.uniform(0.8, 1.2), seg=3), mat, False)


# ===================================================================== human objects (finished, vivid)
def junk_spoon(s=1.0):
    bowl = bm_sphere((0, -0.07 * s, 0.012 * s), (0.026 * s, 0.038 * s, 0.012 * s), seg=8, rings=5)
    deform(bowl, lambda q: V((q.x, q.y, max(q.z, 0.004 * s))))
    h = bm_tube([V((0, -0.035, 0.012)) * s, V((0, 0.04, 0.02)) * s, V((0, 0.1, 0.016)) * s], [0.006 * s, 0.006 * s, 0.011 * s], seg=5, flat=0.45, up=(0, 0, 1))
    return [(bowl, 'M_Brass'), (h, 'M_Brass')]


def junk_button(s=1.0, mat='M_BookRed'):
    b = bm_cyl((0, 0, 0), (0, 0, 0.012 * s), 0.032 * s, seg=10)
    out = [(b, mat)]
    for dx, dy in ((-1, -1), (1, -1), (1, 1), (-1, 1)):
        out.append((bm_cyl((dx * 0.008 * s, dy * 0.008 * s, 0.011 * s), (dx * 0.008 * s, dy * 0.008 * s, 0.014 * s), 0.004 * s, seg=4), INK))
    return out


def junk_bottle(s=1.0):
    body = bm_lathe([(0.0, 0.0), (0.045, 0.0), (0.05, 0.02), (0.05, 0.13), (0.03, 0.17), (0.016, 0.19), (0.016, 0.22), (0.0, 0.22)], seg=10)
    cork = bm_cyl((0, 0, 0.215), (0, 0, 0.245), 0.014, 0.017, seg=6)
    lab = bm_lathe([(0.0515, 0.05), (0.0515, 0.1)], seg=10, cap_top=False, cap_bottom=False)
    out = [(body, 'M_Glass'), (cork, 'M_Leather'), (lab, 'M_PageWhite')]
    return [(xf(b, s=s), m) for b, m in out]


def junk_glasses(s=1.0):
    out = []
    for x in (-0.035, 0.035):
        ring = [V((x + math.cos(2 * math.pi * i / 12) * 0.027, 0, 0.03 + math.sin(2 * math.pi * i / 12) * 0.022)) for i in range(13)]
        out.append((bm_tube(ring, 0.0035, seg=4, cap=False), 'M_Iron'))
    out.append((bm_tube([V((-0.009, 0, 0.036)), V((0, 0, 0.04)), V((0.009, 0, 0.036))], 0.003, seg=4), 'M_Iron'))
    for x in (-1, 1):
        out.append((bm_tube([V((x * 0.062, 0, 0.034)), V((x * 0.064, 0.06, 0.03)), V((x * 0.06, 0.1, 0.012))], 0.003, seg=4), 'M_Iron'))
    return [(xf(b, s=s), m) for b, m in out]


def junk_marble(s=1.0, mat='M_BookBlue'):
    return [(bm_sphere((0, 0, 0.022 * s), (0.022 * s,) * 3, seg=8, rings=5), mat)]


# ===================================================================== RedCord (offering mark)
def red_cord_pieces(seed=0.0, s=1.0, with_lines=True):
    """Knot at the origin, ribbon face toward -Y, tails hang down (-Z). Returns (solid [(bm, mat)], lines [(bm, mat)])."""
    rnd = random.Random(int(seed * 7) + 1)
    sol, lin = [], []
    W = 0.024

    def ribbon(pts, widths, mat_fn=None):
        b = bm_blade([V(p) for p in pts], widths, thick=0.004, up=(0, -1, 0.1))
        return b
    # knot: squashed lumpy ball
    k = bm_sphere((0, -0.004, 0), (0.019, 0.013, 0.017), seg=8, rings=5)
    jitter(k, 0.002, 60.0, seed)
    sol.append((k, OFFER))
    # two bow ears
    for sx in (-1, 1):
        ear = [V((0, -0.006, 0.002)), V((sx * 0.03, -0.012, 0.022)), V((sx * 0.062, -0.01, 0.026)), V((sx * 0.07, -0.006, 0.006)),
               V((sx * 0.045, -0.004, -0.008)), V((sx * 0.012, -0.002, -0.004))]
        sol.append((ribbon(ear, [0.01, W * 0.9, W, W * 0.95, W * 0.8, 0.008]), OFFER))
    # tail 1 (painted all the way, cut on a slant)
    t1 = [V((0.004, -0.006, -0.008)), V((0.02, -0.01, -0.06)), V((0.036, -0.008, -0.12)), V((0.04, -0.004, -0.17)), V((0.05, -0.002, -0.2))]
    sol.append((ribbon(t1, [0.012, W, W * 1.02, W * 0.98, W * 0.4]), OFFER))
    # tail 2: the paint stops before the end -> raw paper cloth with a frayed end, the rest only pencil
    t2 = [V((-0.004, -0.006, -0.008)), V((-0.022, -0.009, -0.05)), V((-0.04, -0.007, -0.095)), V((-0.048, -0.004, -0.125))]
    sol.append((ribbon(t2, [0.012, W, W, W * 0.96]), OFFER))
    t2b = [t2[-1] + V((0, 0.0005, 0.004)), V((-0.054, -0.003, -0.15)), V((-0.058, -0.002, -0.165))]
    sol.append((ribbon(t2b, [W * 0.96, W * 0.9, W * 0.85]), 'M_TornEdge'))
    end = V((-0.058, -0.002, -0.165))
    for i in range(6):   # frayed threads
        x = -W * 0.8 + 1.6 * W * i / 5
        a = end + V((x * 0.9, -0.002, 0))
        lin.append((stroke([a, a + V((rnd.uniform(-0.008, 0.008), -0.002, -rnd.uniform(0.012, 0.03)))], 0.0013, seg=3), OFFERB))
    if with_lines:
        # pencil: where the strip was meant to continue + the planned slant cut
        for x in (-W * 0.85, W * 0.85):
            lin.append((CR.line([end + V((x, -0.006, 0.01)), end + V((x - 0.006, -0.006, -0.06))], 0.0012, over=0.012, seed=seed + x), PENCIL))
        lin.append((CR.line([end + V((-W, -0.006, -0.05)), end + V((W, -0.006, -0.075))], 0.0012, over=0.01, seed=seed + 3), PENCIL))
        # ink: crease lines at the knot + one edge line per tail
        lin.append((stroke([V((-0.012, -0.019, 0.008)), V((0.0, -0.02, -0.004)), V((0.013, -0.018, 0.01))], 0.0016, seg=3), INK))
        for tl, sg in ((t1, 1), (t2, -1)):
            lin.append((stroke([p + V((sg * W * 0.9, -0.004, 0)) for p in tl[1:]], 0.0012, seg=3), INK))
    # brush streaks: dry brush running a little past the cloth edge (painted by hand, not dyed)
    for i in range(4):
        tl = t1 if i % 2 == 0 else t2
        o = V((rnd.uniform(-0.6, 0.6) * W, -0.0035, 0))
        pts = [p + o for p in tl[1:]]
        sol.append((bm_blade(pts, [0.004, 0.005, 0.004, 0.002][:len(pts)], thick=0.0015, up=(0, -1, 0)), OFFERB))
    if s != 1.0:
        sol = [(xf(b, s=s), m) for b, m in sol]
        lin = [(xf(b, s=s), m) for b, m in lin]
    return sol, lin


def build_red_cord():
    K = Kit('RedCord')
    sol, lin = red_cord_pieces(seed=1.0)
    for b, m in sol:
        K.add('Cord', b, m, False)
    for b, m in lin:
        K.add('Lines', b, m, False)
    return K.finish(0.25, "Village offering mark: a brush-painted red cloth strip tied in a knot. Pivot = knot (attach to the hero's cape or a lump), "
                          "ribbon faces Unity +Z, tails hang down (-Y). One tail is painted to the end and cut; the other stops in raw cloth + frayed "
                          "threads, its planned length only pencil. M_OfferRed/M_OfferRedBrush are 'keep' (no drain).",
                    parents={'Lines': 'Cord'})


# ===================================================================== Sack (collector's)
def sack_body(h=1.3, r=0.46, seg=16, seed=0.0, neck=0.1, bulge=True):
    prof = [(0.0, 0.02), (r * 0.7, 0.0), (r * 0.93, h * 0.06), (r, h * 0.2), (r * 1.02, h * 0.36), (r * 0.97, h * 0.52),
            (r * 0.84, h * 0.66), (r * 0.6, h * 0.78), (neck * 1.6, h * 0.85), (neck, h * 0.87)]
    b = bm_lathe(prof, seg=seg, sy=0.82, cap_top=False, cap_bottom=True)
    tri_ngons(b)
    CR.orient_out(b, center=(0, 0, h * 0.4))
    if bulge:
        # a body inside: knee + shoulder pushing the cloth, sag at the bottom
        knobs = [(V((0.18, -0.3, h * 0.3)), 0.2, 0.07), (V((-0.2, -0.2, h * 0.58)), 0.22, 0.06), (V((0.05, 0.3, h * 0.45)), 0.25, 0.05)]

        def push(c):
            for kc, kr, ka in knobs:
                d = (c - kc).length
                if d < kr * 2.2:
                    w = math.exp(-(d / kr) ** 2)
                    c = c + (c - V((0, 0, c.z))).normalized() * ka * w if (c.xy.length > 1e-4) else c
            return c
        deform(b, push)
    jitter(b, 0.018 * h, 2.2, seed)
    jitter(b, 0.006 * h, 9.0, seed + 1)
    deform(b, lambda c: V((c.x, c.y, max(0.0, c.z))))
    return b


def build_sack():
    K = Kit('Sack')
    h, r = 1.3, 0.46
    b = sack_body(h, r, seg=18, seed=11)
    bvh = BVHTree.FromBMesh(b)
    # the cloth is not woven all the way: a window on the right shoulder is open (dark inside), its weave only pencil
    hole = lambda c: ((c.x - 0.42) ** 2) / 0.09 + ((c.z - h * 0.62) ** 2) / 0.05 + ((c.y + 0.05) ** 2) / 0.12
    fld = lambda c: hole(c) - 1.0 + nval(c, 5.0, 12) * 0.35
    full, res = K.form('Body', 'Lines', b, fld, SACK, thick=0.02, zig=0.025, seed=12,
                       hatch_kw=dict(spacing=0.05, length=(0.06, 0.16), r=0.0045, slant=30, density=0.8), back_near=0.35, ink_r=0.008)
    # pencil weave continuing across the open window
    for k in range(7):
        t = k / 6
        a = V((0.47 + 0.03 * math.sin(t * 3), -0.24 + 0.36 * t, h * 0.47))
        K.add('Lines', CR.line([a, a + V((-0.03, 0.02, h * 0.3))], 0.0035, over=0.03, seed=13 + k), PENCIL, False)
        z = h * 0.48 + 0.05 * k
        K.add('Lines', CR.line([V((0.47, -0.25, z)), V((0.49, 0.1, z + 0.02))], 0.0035, over=0.03, seed=20 + k), PENCIL, False)
    # a body sitting inside is visible through the hole: just a dark shape (it is the hero/kid, never shown in detail)
    K.add('Body', bm_sphere((0.18, -0.02, h * 0.62), (0.2, 0.18, 0.16), seg=8, rings=5), SACKD, False)
    # seams + coarse weave + a sewn patch
    K.add('Lines', line([V((-0.02, -0.37, 0.04)), V((0.0, -0.39, h * 0.4)), V((-0.03, -0.31, h * 0.7)), V((-0.05, -0.12, h * 0.84))], 0.007, 14, 0.01), INK, False)
    weave(K, 'Lines', bvh, (0, 0, h * 0.35), (math.radians(-170), math.radians(-20)), n=7, ln=0.25, r=0.0035, seed=15, keep=lambda p: fld(p) > 0.05)
    pc = V((-0.24, -0.33, h * 0.32))
    patch = [pc + V((math.cos(a) * 0.11, 0, math.sin(a) * 0.09)) for a in [i * 2 * math.pi / 8 for i in range(9)]]
    for i, p in enumerate(patch):
        hit = bvh.ray_cast(p + V((0, -1, 0)), V((0, 1, 0)))
        if hit[0] is not None:
            patch[i] = hit[0] + hit[1] * 0.01
    K.add('Lines', stroke(patch, 0.004, seg=3, taper=False), INK, False)
    for i in range(0, 8, 2):
        a, c = patch[i], patch[i + 1]
        m = a.lerp(c, 0.5)
        K.add('Lines', stroke([m + (m - pc).normalized() * 0.02, m - (m - pc).normalized() * 0.02], 0.003, seg=3, taper=False), INK, False)
    K.add('Lines', CR.smudge((-0.3, -0.36, h * 0.15), (0, -1, 0), 0.25, 0.14, seed=16, lift=0.02, up=(0, 0, 1)), SMUDGE, False)
    # mouth: gathered neck + twine tie + ruffle (pivot at the neck: hide / swap for the open sack)
    nz = h * 0.87
    ruff = [(0.1, nz - 0.02), (0.13, nz + 0.05), (0.2, nz + 0.13), (0.22, nz + 0.16)]
    rb = lathe_g(ruff, seg=12, sy=0.85)
    deform(rb, lambda c: c + V((0, 0, 0.035 * math.sin(math.atan2(c.y, c.x) * 5))))
    jitter(rb, 0.012, 7.0, 17)
    K.add('Mouth', rb, SACK, False)
    K.add('Mouth', lathe_g([(0.106, nz - 0.03), (0.112, nz + 0.03)], seg=10), SACKD, False)
    for k in range(2):
        tie = CR.ring_pts(0, 0, nz - 0.01 + 0.025 * k, 0.113, 12)
        K.add('Mouth', bm_tube(tie, 0.009, seg=4, cap=False), SACKD, False)
    K.add('Mouth', bm_tube([V((0.1, -0.06, nz)), V((0.15, -0.12, nz - 0.08)), V((0.16, -0.14, nz - 0.2))], [0.009, 0.008, 0.006], seg=4), SACKD, False)
    for k in range(5):
        a = math.radians(-120 + 50 * k)
        K.add('Lines', line([V((math.cos(a) * 0.12, math.sin(a) * 0.1, nz + 0.02)), V((math.cos(a) * 0.2, math.sin(a) * 0.17, nz + 0.14))], 0.004, 18 + k), INK, False)
    return K.finish(1.4, "Collector's sack, closed and full (1.3 m; a child fits inside - the hero is carried in it at the fall). Something "
                         "presses from inside. Unfinished: the weave never closed on the right shoulder (torn window, dark inside, pencil weave "
                         "across). Mouth = gathered neck + twine tie + ruffle, pivot at the neck (hide it / use Sack_Open).",
                    pivots={'Mouth': (0, 0, h * 0.87)}, parents={'Lines': 'Body'})


def build_sack_open():
    K = Kit('Sack_Open')
    h = 0.62
    rim_z, rim_r = 0.52, 0.3
    prof = [(0.0, 0.02), (0.36, 0.0), (0.47, 0.05), (0.5, 0.14), (0.47, 0.28), (0.4, 0.4), (rim_r + 0.02, 0.48), (rim_r, rim_z)]
    b = bm_lathe(prof, seg=18, sy=0.86, cap_top=False, cap_bottom=True)
    tri_ngons(b)
    CR.orient_out(b, center=(0, 0, 0.2))
    # slumped: folds + the rim sags forward
    deform(b, lambda c: c + V((0, 0, -0.06 * math.sin(math.atan2(c.y, c.x) * 3) * max(0.0, c.z / rim_z) - 0.08 * max(0.0, -c.y) * (c.z / rim_z))))
    jitter(b, 0.02, 2.5, 31)
    deform(b, lambda c: V((c.x, c.y, max(0.0, c.z))))
    bvh = BVHTree.FromBMesh(b)
    fld = lambda c: (((c.x + 0.4) ** 2) / 0.05 + ((c.z - 0.25) ** 2) / 0.03 + ((c.y - 0.1) ** 2) / 0.1) - 1.0 + nval(c, 5.0, 32) * 0.35
    full, res = K.form('Body', 'Lines', b, fld, SACK, thick=0.02, zig=0.025, seed=33, back_near=None,
                       hatch_kw=dict(spacing=0.05, length=(0.05, 0.14), r=0.0045, slant=30, density=0.8), ink_r=0.008)
    for k in range(5):
        z = 0.12 + 0.05 * k
        K.add('Lines', CR.line([V((-0.48, -0.1, z)), V((-0.46, 0.25, z + 0.02))], 0.0035, over=0.03, seed=34 + k), PENCIL, False)
    weave(K, 'Lines', bvh, (0, 0, 0.22), (math.radians(-170), math.radians(-10)), n=6, ln=0.12, r=0.0035, seed=36, keep=lambda p: fld(p) > 0.05)
    # mouth rim: rolled hem (tube) + dark inside disc so the empty sack reads open from the game camera
    rim = []
    for i in range(17):
        a = 2 * math.pi * i / 16
        p = V((math.cos(a) * rim_r, math.sin(a) * rim_r * 0.86, rim_z))
        rim.append(V((p.x, p.y, rim_z - 0.06 * math.sin(a * 3) - 0.08 * max(0.0, -p.y) * 1.0)))
    K.add('Mouth', bm_tube(rim, 0.022, seg=5, cap=False), SACK, False)
    inner = bmesh.new()
    cv = inner.verts.new(V((0, 0, rim_z - 0.18)))
    rv = [inner.verts.new(p + V((0, 0, -0.01))) for p in rim[:-1]]
    for i in range(len(rv)):
        inner.faces.new((cv, rv[i], rv[(i + 1) % len(rv)]))
    for f in inner.faces:
        if f.normal.z < 0:
            f.normal_flip()
    K.add('Mouth', inner, SACKD, False)
    K.add('Mouth', bm_tube([rim[3] + V((0, 0, 0.01)), rim[3] + V((0.12, -0.08, -0.05)), V((rim[3].x + 0.2, rim[3].y - 0.16, 0.01))], [0.009, 0.008, 0.007], seg=4), SACKD, False)
    K.add('Lines', stroke([p + V((0, 0, 0.022)) for p in rim[2:9]], 0.004, seg=3), INK, False)
    return K.finish(0.6, "Collector's sack, empty and open (slumped, 0.55 m). Mouth = rolled hem + dark inside + loose twine (pivot = rim centre). "
                         "Unfinished: the weave on the left side is a torn window with pencil weave.", pivots={'Mouth': (0, 0, rim_z)},
                    parents={'Lines': 'Body'})


# ===================================================================== Hook pole (collector's tool)
def build_hook_pole():
    K = Kit('HookPole')
    H = 2.3
    rnd = random.Random(41)
    # puppet-limb pole: wooden segments joined by ball joints (the collectors made it from spare puppet arms)
    segs = [(0.42, 1.05), (1.05, 1.72), (1.72, 2.12)]
    for z0, z1 in segs:
        K.add('Pole', bm_tube([V((0, 0, z0)), V((0.004, 0, (z0 + z1) / 2)), V((0, 0, z1))], [0.032, 0.036, 0.03], seg=7), PWOOD, True)
        K.add('Pole', bm_sphere((0, 0, z1), (0.046,) * 3, seg=8, rings=5), PJOINT, False)
        K.add('Lines', line([V((0.0, -0.028, z0 + 0.04)), V((0.002, -0.03, z1 - 0.05))], 0.0035, 42 + z0, taper=True), INK, False)
    # the lowest 0.42 m is not carved yet: torn end + pencil cylinder down to the floor
    K.add('Pole', bm_sphere((0, 0, 0.42), (0.03, 0.03, 0.02), seg=7, rings=4), 'M_TornEdge', False)
    K.add('Lines', CR.ellipse((0, 0, 0.42), 0.03, 0.03, 0.0, turns=1.1, n=10, r=0.004, seed=43), INK, False)
    for x in (-0.027, 0.027):
        K.add('Lines', CR.line([V((x, 0, 0.44)), V((x * 0.9, 0, 0.0))], 0.0035, over=0.05, seed=44 + x), PENCIL, False)
    K.add('Lines', CR.ellipse((0, 0, 0.0), 0.026, 0.026, 0.0, turns=1.05, n=10, r=0.003, seed=45), PENCIL, False)
    K.add('Lines', CR.smudge((0.0, -0.03, 0.2), (0, -1, 0), 0.08, 0.3, seed=46, lift=0.01), SMUDGE, False)
    # hook head (pivot at the lashing): carved shank + half of the curve; the barb end is only ink + pencil
    j = V((0, 0, 2.12))
    shank = [j, j + V((0, 0, 0.18)), j + V((0.02, 0, 0.34))]
    curve = [j + V((0.02, 0, 0.34)), j + V((0.12, 0, 0.45)), j + V((0.26, 0, 0.44)), j + V((0.34, 0, 0.33))]
    rest = [j + V((0.34, 0, 0.33)), j + V((0.35, 0, 0.19)), j + V((0.3, 0, 0.09)), j + V((0.22, 0, 0.13))]
    K.add('Hook', bm_tube(shank + curve[1:], [0.032, 0.031, 0.029, 0.026, 0.023, 0.02], seg=7), PWOOD, True)
    K.add('Hook', bm_sphere(curve[-1], (0.018, 0.018, 0.018), seg=6, rings=4), 'M_TornEdge', False)
    for k in range(3):   # twine lashing
        K.add('Hook', bm_tube(CR.ring_pts(0, 0, 2.1 + 0.03 * k, 0.03, 8), 0.007, seg=4, cap=False), SACKD, False)
    K.add('Lines', stroke([p + V((0, -0.02, 0)) for p in shank[1:] + curve[1:]], 0.0035, seg=3), INK, False)
    K.add('Lines', CR.line(rest, 0.008, over=0.02, seed=47), INK, False)
    off = [p + V((0.012, 0, 0.012)) for p in rest]
    K.add('Lines', CR.line(off, 0.004, over=0.04, seed=48), PENCIL, False)
    K.add('Lines', CR.line([rest[-1], rest[-1] + V((-0.02, 0, 0.07))], 0.004, over=0.02, seed=49), PENCIL, False)   # barb
    K.add('Lines', CR.ellipse(curve[-1], 0.024, 0.024, 0.0, turns=1.1, n=8, r=0.003, seed=50, tilt=('X', 90)), INK, False)
    A = K.finish(2.5, "Collector's hook pole (2.45 m): three puppet-limb segments with ball joints (made from spare puppet arms). Unfinished: the "
                      "lowest 0.42 m is only pencil, the hook's barb end is ink + pencil (only the shank and half the curve are carved). "
                      "Root = floor end. Grip empty at 1.15 m (hand). Hook pivot = lashing (wiggle).", pivots={'Hook': tuple(j)},
                 parents={'Hook': 'Pole', 'Lines': 'Pole'})
    A.empty('Grip', (0, 0, 1.15), parent='Pole')
    return A


# ===================================================================== Decree (the king's interpretation band)
def build_decree_scroll():
    K = Kit('DecreeScroll')
    Lx, R = 0.46, 0.042
    zc = R
    b = CR.drum_grid(0, 0, -Lx / 2, Lx / 2, R, R, seg=14, step=0.05)
    L.xform(b, Matrix.Rotation(math.radians(90), 4, 'Y'))
    move(b, (0, 0, zc))
    # the right end of the roll stops at a torn edge (not rolled / drawn yet); its outline continues in pencil
    fld = lambda c: 0.13 - c.x + nval(c, 18.0, 51) * 0.03
    full, res = K.form('Scroll', 'Lines', b, fld, 'M_DecreeBand', thick=0.006, zig=0.008, seed=52, back_near=0.1, smooth=True,
                       hatch_kw=dict(spacing=0.02, length=(0.02, 0.06), r=0.0025, slant=30, density=0.7, up_only=False), ink_r=0.004)
    # left end: closed cap + ink spiral of the rolled band
    cap = bm_cyl((-Lx / 2, 0, zc), (-Lx / 2 - 0.002, 0, zc), R, seg=14)
    K.add('Scroll', cap, 'M_DecreeBand', False)
    sp = [V((-Lx / 2 - 0.004, math.cos(a) * R * a / 14.0, zc + math.sin(a) * R * a / 14.0)) for a in [i * 0.45 for i in range(1, 32)]]
    K.add('Lines', stroke(sp, 0.0022, seg=3), INK, False)
    K.add('Lines', stroke([V((-Lx / 2, 0, zc + R + 0.003)), V((0.12, 0, zc + R + 0.004))], 0.002, seg=3), INK, False)
    # pencil: the rest of the roll + its end spiral
    for s in (-1, 1):
        K.add('Lines', CR.line([V((0.1, 0, zc + s * R)), V((Lx / 2, 0, zc + s * R * 0.98))], 0.0025, over=0.03, seed=53 + s), PENCIL, False)
    K.add('Lines', CR.ellipse((Lx / 2, 0, zc), R, R, 0.0, turns=1.15, n=12, r=0.0022, seed=55, tilt=('Y', 90)), PENCIL, False)
    sp2 = [V((Lx / 2 + 0.003, math.cos(a) * R * a / 14.0, zc + math.sin(a) * R * a / 14.0)) for a in [i * 0.7 for i in range(2, 20)]]
    K.add('Lines', stroke(sp2, 0.0016, seg=3), PENCIL, False)
    # the king's tie (plum) + wax seal facing up/front
    for dx in (-0.02, 0.02):
        K.add('Seal', xf(bm_tube([V((math.cos(a) * 0 + 0, math.cos(a) * (R + 0.004), math.sin(a) * (R + 0.004))) for a in [i * 2 * math.pi / 12 for i in range(13)]], 0.006, seg=4, cap=False),
                 pos=(dx - 0.06, 0, zc)), 'M_KingSeal', False)
    sc = V((-0.06, -R * 0.6, zc + R * 0.85))
    sn = V((0, -0.6, 0.8)).normalized()
    seal = bm_cyl(sc - sn * 0.004, sc + sn * 0.012, 0.034, seg=12)
    jitter(seal, 0.003, 40.0, 56)
    K.add('Seal', seal, 'M_KingSeal', False)
    for k in range(3):   # drips of wax
        a = k * 2.1 + 0.4
        q = sc + V((math.cos(a) * 0.035, 0, 0)) + V((0, -0.01, -0.005 * k))
        K.add('Seal', bm_sphere(q, (0.009, 0.008, 0.012), seg=6, rings=4), 'M_KingSeal', False)
    # the king's mark pressed in: a ring with three ticks (crown) - creature glyph
    u = V((1, 0, 0))
    w = sn.cross(u).normalized()
    top = sc + sn * 0.013
    ring = [top + u * math.cos(a) * 0.021 + w * math.sin(a) * 0.021 for a in [i * 2 * math.pi / 12 for i in range(13)]]
    K.add('Lines', stroke(ring, 0.0022, seg=3, taper=False), INK, False)
    for t in (-1, 0, 1):
        K.add('Lines', stroke([top + u * t * 0.009 - w * 0.008, top + u * t * 0.009 + w * (0.012 if t == 0 else 0.008)], 0.002, seg=3), INK, False)
    return K.finish(0.5, "The king's rolled interpretation band (0.46 m), lying on the ground: yellowed creature paper tied with a plum cord, "
                         "plum wax seal with the king's crown glyph on top-front. Unfinished: the right end of the roll stops at a torn edge, "
                         "the rest of the roll and its end spiral only pencil. Spat out by the fish.", parents={'Lines': 'Scroll'})


def curl_end(x0, sgn, W, R=0.032, turns=1.35, n=10, z0=0.0, step_y=0.05):
    """rolled end of the band: grid surface spiralling from x0 outward (sgn = +1 right end, -1 left end)"""
    b = bmesh.new()
    ny = max(2, int(W / step_y))
    rows = []
    for i in range(n + 1):
        a = turns * 2 * math.pi * i / n
        rr = R * (1 - 0.35 * i / n)
        x = x0 + sgn * math.sin(a) * rr
        z = z0 + rr - math.cos(a) * rr
        rows.append([b.verts.new(V((x, -W / 2 + W * j / ny, z))) for j in range(ny + 1)])
    for i in range(n):
        for j in range(ny):
            b.faces.new((rows[i][j], rows[i][j + 1], rows[i + 1][j + 1], rows[i + 1][j]))
    for f in b.faces:
        c = f.calc_center_median()
        o = V((x0 + 0 * sgn, c.y, z0 + R))
        if (c - o).dot(f.normal) < 0:
            f.normal_flip()
    return b


def build_decree_open():
    K = Kit('DecreeOpen')
    Wx, Wy = 0.78, 0.25           # flat band (x = length, y = width)
    z_band, z_text = 0.008, 0.004
    # HumanText (human handwriting underneath): a larger human page, a little rotated, peeking out above / below the band
    tw, th = 0.64, 0.4
    ht = bmesh.new()
    uv = ht.loops.layers.uv.new('UVMap')
    nx, ny = 6, 4
    vs = []
    for j in range(ny + 1):
        vs.append([ht.verts.new(V((-tw / 2 + tw * i / nx, -th / 2 + th * j / ny, z_text + 0.002 * math.sin(i * 1.7 + j)))) for i in range(nx + 1)])
    for j in range(ny):
        for i in range(nx):
            f = ht.faces.new((vs[j][i], vs[j][i + 1], vs[j + 1][i + 1], vs[j + 1][i]))
            for lp, (di, dj) in zip(f.loops, ((0, 0), (1, 0), (1, 1), (0, 1))):
                lp[uv].uv = ((i + di) / nx, (j + dj) / ny)
    xf(ht, rz=-4, pos=(0.05, 0.015, 0))
    K.add('HumanText', ht, 'M_PageWhite', False)
    # Face = the band's top, UV 0..1 over the whole band rectangle; one corner is torn away -> the human page shows through
    fc = bmesh.new()
    uvf = fc.loops.layers.uv.new('UVMap')
    nx, ny = 12, 4
    vs = []
    for j in range(ny + 1):
        vs.append([fc.verts.new(V((-Wx / 2 + Wx * i / nx, -Wy / 2 + Wy * j / ny, z_band + 0.003 * math.sin(i * 0.9)))) for i in range(nx + 1)])
    for j in range(ny):
        for i in range(nx):
            fc.faces.new((vs[j][i], vs[j][i + 1], vs[j + 1][i + 1], vs[j + 1][i]))
    tear = lambda c: ((c.x - 0.18) ** 2) / 0.02 + ((c.y - Wy / 2) ** 2) / 0.017 - 1.0 + nval(c, 22.0, 61) * 0.4
    res = CR.cut_field(fc, tear, zig=0.008, seed=62)
    built = res.built
    uvl = built.loops.layers.uv.new('UVMap')
    for f in built.faces:
        for lp in f.loops:
            lp[uvl].uv = ((lp.vert.co.x + Wx / 2) / Wx, (lp.vert.co.y + Wy / 2) / Wy)
    for f in built.faces:
        if f.normal.z < 0:
            f.normal_flip()
    K.add('Face', built, 'M_DecreeBand', False)
    K.add('Lines', CR.torn_ink(res, 0.0025, 63, lift=0.002), INK, False)
    # torn flap: the peeled corner curls up
    flap = bmesh.new()
    rows = []
    for j in range(6):           # peeled corner: hinged near the tear, curling up and over toward +y
        t = j / 5
        ang = t * math.pi * 0.85
        rr = 0.05
        y = Wy / 2 - 0.02 + math.sin(ang) * rr
        z = z_band + 0.002 + (1 - math.cos(ang)) * rr
        x0, x1 = 0.08 + 0.03 * t, 0.29 - 0.04 * t
        rows.append([flap.verts.new(V((x0 + (x1 - x0) * i / 3, y + 0.01 * math.sin(i * 1.7), z))) for i in range(4)])
    for j in range(5):
        for i in range(3):
            flap.faces.new((rows[j][i], rows[j][i + 1], rows[j + 1][i + 1], rows[j + 1][i]))
    bmesh.ops.recalc_face_normals(flap, faces=flap.faces)
    back = CR.copy(flap)
    for f in back.faces:
        f.normal_flip()
    K.add('Band', flap, 'M_DecreeBand', False)
    K.add('Band', back, 'M_PaperBack', False)
    K.add("Lines", stroke([r_[0].co.copy() + V((0, 0, 0.002)) for r_ in rows], 0.002, seg=3), INK, False)
    K.add("Lines", stroke([r_[-1].co.copy() + V((0, 0, 0.002)) for r_ in rows], 0.002, seg=3), INK, False)
    # underside slab of the band (thickness) so it does not z-fight with the page
    under = CR.copy(built)
    for v in under.verts:
        v.co.z -= 0.0025
    bmesh.ops.reverse_faces(under, faces=under.faces)
    K.add('Band', under, 'M_PaperBack', False)
    # rolled ends: left fully rolled, right rolled only half - the rest of its curl in pencil
    K.add('Band', curl_end(-Wx / 2, -1, Wy, R=0.03, turns=1.3, z0=z_band - 0.001), 'M_DecreeBand', False)
    K.add('Band', curl_end(Wx / 2, 1, Wy, R=0.028, turns=0.55, n=5, z0=z_band - 0.001), 'M_DecreeBand', False)
    for y in (-Wy / 2, 0, Wy / 2):
        K.add('Lines', CR.arc(V((Wx / 2, y, z_band + 0.028)), 0.028, -90, 250, n=12, r=0.0018, plane='XZ', seed=64 + y), PENCIL, False)
    K.add('Lines', stroke([V((-Wx / 2 - 0.004, -Wy / 2, z_band + 0.058)), V((-Wx / 2 - 0.004, Wy / 2, z_band + 0.058))], 0.0025, seg=3), INK, False)
    # broken seal on the left (cracked in two)
    for k, (dx, dy, rz) in enumerate(((-0.33, -0.07, 20), (-0.29, -0.115, -35))):
        half = bm_cyl((0, 0, 0), (0, 0, 0.012), 0.03, seg=10)
        bmesh.ops.bisect_plane(half, geom=half.verts[:] + half.edges[:] + half.faces[:], plane_co=(0.002 * (1 if k else -1), 0, 0),
                               plane_no=(1 if k else -1, 0, 0), clear_inner=True)
        jitter(half, 0.002, 40.0, 65 + k)
        K.add('Seal', xf(half, rz=rz, pos=(dx, dy, z_band + 0.002)), 'M_KingSeal', False)
    K.add('Seal', xf(bm_tube([V((-0.3, -0.13, z_band)), V((-0.36, -0.2, 0.004)), V((-0.42, -0.21, 0.003))], 0.004, seg=4), pos=(0, 0, 0)), 'M_KingSeal', False)
    # band edge lines (creature ruled border; glyphs come from the Face texture)
    for y in (-Wy / 2 + 0.018, Wy / 2 - 0.018):
        pts = [V((-Wx / 2 + 0.03, y, z_band + 0.005)), V((Wx / 2 - 0.03, y + 0.002, z_band + 0.005))]
        K.add('Lines', CR.clipped_lines(CR.dense(pts, 0.03), lambda p: tear(p) > 0.15, 0.0018, 0.0, 66), INK, False)
    return K.finish(0.8, "The king's band unrolled on the ground (0.78 x 0.25 m). Face = the band top, UV 0..1 over the whole band rectangle "
                         "(creature glyph texture); its back-right corner is torn and peeled up, and HumanText = the human page underneath "
                         "(own UV 0..1, rotated -4 deg, larger) shows through the tear and along both long edges. Right roll half drawn "
                         "(pencil), seal broken in two. Hide Face (or animate the flap) to reveal the whole HumanText.",
                    parents={'Face': 'Band', 'HumanText': 'Band', 'Seal': 'Band', 'Lines': 'Band'})


# ===================================================================== lumps (failed bodies)
def melt_mass(h, r, seed, lean=(0.0, 0.0), seg=16, pool=1.25):
    """slumped wooden mass: wide pooled foot, sagging shoulders, drips. Returns bmesh (closed)."""
    prof = [(0.0, 0.0), (r * pool, 0.0), (r * pool * 0.98, h * 0.05), (r * 1.02, h * 0.16), (r * 0.98, h * 0.36), (r * 0.86, h * 0.58),
            (r * 0.66, h * 0.78), (r * 0.36, h * 0.94), (0.0, h)]
    b = bm_lathe(prof, seg=seg, sy=0.85)
    tri_ngons(b)
    CR.orient_out(b, center=(0, 0, h * 0.4))

    def sag(c):
        t = max(0.0, c.z / h)
        c = c + V((lean[0] * t * t, lean[1] * t * t, 0))
        a = math.atan2(c.y, c.x)
        c.z -= h * 0.06 * (0.5 + 0.5 * math.sin(a * 3 + seed)) * (1 - abs(t - 0.5) * 2)   # drooping folds
        return c
    deform(b, sag)
    jitter(b, r * 0.07, 3.0, seed)
    jitter(b, r * 0.025, 9.0, seed + 1)
    deform(b, lambda c: V((c.x, c.y, max(0.0, c.z))))
    return b


def drips_on(K, part, bvh, h_edge, center, n, mat, seed, ln=(0.05, 0.16), w=0.02, arc=(0, 360)):
    rnd = random.Random(int(seed * 13) + 5)
    for k in range(n):
        a = math.radians(arc[0] + (arc[1] - arc[0]) * (k + rnd.uniform(0.1, 0.9)) / n)
        d = V((math.cos(a), math.sin(a), 0))
        l_ = rnd.uniform(*ln)
        pts = []
        for t in range(5):
            z = h_edge - l_ * t / 4
            hit = bvh.ray_cast(V((center[0], center[1], z)) + d * 2.0, -d)
            if hit[0] is None:
                break
            pts.append(hit[0] + hit[1] * 0.004)
        if len(pts) >= 3:
            ww = [w, w * 0.9, w * 0.75, w * 0.6, w * 0.45][:len(pts)]
            ww[-1] = w * 0.15
            K.add(part, bm_blade(pts, ww, thick=0.003, up=(d.x, d.y, 0)), mat, False)


def build_lump_brother():
    K = Kit('Lump_Brother')
    rnd = random.Random(71)
    h, r = 0.5, 0.3
    m = melt_mass(h, r, 71, lean=(0.03, -0.04), seg=16)
    bvh = BVHTree.FromBMesh(m)
    K.add('Body', m, PWOOD, True, lambda c, n: BLUE if (c.z + nval(c, 9.0, 72) * 0.04) > h * 0.5 else (RED if (c.z + nval(c, 9.0, 73) * 0.03) < h * 0.2 else None))
    # head: Kinopio's hex face plank, sunk into the mass and tilted (the brother), lower edge melted into the body
    hc = V((0.02, -0.12, h + 0.05))
    sx, sz, sy = 0.15, 0.115, 0.07
    outline = [(math.cos(math.radians(60 * i)) * sx * (1.0 if i % 3 == 0 else 0.86), math.sin(math.radians(60 * i)) * sz) for i in range(6)]
    hb = L.bm_prism(outline, -sy, sy, center=hc, axis='Y')
    hb = L.bevel(hb, 0.018, 1, 40)
    rot(hb, 'Y', -14, hc)
    rot(hb, 'X', 12, hc)
    deform(hb, lambda c: c + V((0, 0, -0.035 * max(0.0, (hc.z - c.z) / sz) ** 2)))
    jitter(hb, 0.004, 12.0, 75)
    hbv = BVHTree.FromBMesh(hb)
    K.add('Body', hb, PWOOD, False, lambda c, n: BLUE if c.z > hc.z + sz * 0.62 + nval(c, 20.0, 76) * 0.02 else None)
    # eyes (mirror of Kinopio: drawn ring on the LEFT, carved hole on the right); one has melted into a drip
    for x, kind in ((0.07, 'ring'), (-0.055, 'hole')):
        hit = hbv.ray_cast(V((hc.x + x, hc.y - 0.5, hc.z + 0.005)), V((0, 1, 0)))
        if hit[0] is None:
            continue
        c, n = hit[0], hit[1]
        if kind == 'hole':
            e = bm_sphere((0, 0, 0), (0.026, 0.012, 0.032), seg=8, rings=5)
            L.xform(e, n.to_track_quat('-Y', 'Z').to_matrix().to_4x4())
            K.add('Body', move(e, c - n * 0.003), INK, False)
            K.add('Lines', stroke([c + n * 0.003 + V((0, 0, -0.03)), c + n * 0.004 + V((0.004, 0, -0.07)), c + n * 0.003 + V((0.002, 0, -0.1))], 0.004, seg=3), INK, False)
        else:
            ring = [c + n * 0.003 + V((math.cos(a) * 0.03, 0, math.sin(a) * 0.033)) for a in [i * 2 * math.pi / 14 + 0.4 for i in range(15)]]
            K.add('Lines', stroke(ring, 0.004, seg=3, taper=False), INK, False)
            dot = bm_sphere((0, 0, 0), (0.01, 0.004, 0.011), seg=6, rings=4)
            L.xform(dot, n.to_track_quat('-Y', 'Z').to_matrix().to_4x4())
            K.add('Body', move(dot, c + n * 0.002 + V((0.004, 0, -0.004))), INK, False)
    # the nose: Kinopio's sketch-line nose, shorter, drooping toward the ground (translucent pencil)
    hit = hbv.ray_cast(V((hc.x + 0.005, hc.y - 0.5, hc.z - 0.02)), V((0, 1, 0)))
    nb = hit[0] if hit[0] is not None else hc + V((0, -sy, -0.02))
    tip = nb + V((0.02, -0.2, -0.09))
    for k, (dx, dz) in enumerate(((0, 0), (0.012, 0.008), (-0.01, 0.006))):
        pts = [nb + V((dx * 0.5, 0, dz * 0.5)), nb.lerp(tip, 0.5) + V((dx, -0.006, dz - 0.012)), tip + V((dx * 0.3, 0, dz * 0.3))]
        K.add('Nose', stroke(pts, 0.006 - 0.0012 * k, seg=4), 'M_SketchNose', False)
    # cap: a little painted cap (navy) pushed back on the head; its back half only pencil
    cc = hc + V((-0.01, 0.01, sz * 0.92))
    cap = bm_sphere(cc, (0.13, 0.1, 0.06), seg=12, rings=6)
    deform(cap, lambda c: V((c.x, c.y, max(c.z, cc.z - 0.005))))
    rot(cap, 'Y', -14, hc)
    rot(cap, 'X', -10, cc)
    cfld = lambda c: -(c.y - cc.y) + 0.02 + nval(c, 16.0, 77) * 0.03
    K.form('Body', 'Lines', cap, cfld, NAVY, thick=0.008, zig=0.01, seed=78, back_near=None,
           hatch_kw=dict(spacing=0.02, length=(0.02, 0.06), r=0.0025, slant=30, density=0.7), ink_r=0.004)
    brim = bm_blade([cc + V((-0.08, -0.07, -0.01)), cc + V((0.0, -0.12, -0.015)), cc + V((0.08, -0.07, -0.01))], [0.02, 0.045, 0.02], thick=0.008, up=(0, 0.2, 1))
    rot(brim, 'Y', -14, hc)
    K.add('Body', brim, NAVY, False)
    K.add('Lines', CR.ellipse(cc + V((0, 0.02, 0.0)), 0.13, 0.1, 0.0, turns=0.55, n=14, r=0.0025, seed=79, a0=0.2), PENCIL, False)
    K.add('Lines', CR.arc(cc + V((0, 0.03, -0.002)), 0.12, 10, 170, n=10, r=0.0025, plane='XZ', seed=80), PENCIL, False)
    # limbs: a wooden arm stub with a ball joint; the other arm only pencil + ink hand
    sh = V((0.25, -0.05, h * 0.62))
    K.add('Body', bm_sphere(sh, (0.035,) * 3, seg=8, rings=5), PJOINT, False)
    K.add('Body', bm_tube([sh, sh + V((0.06, -0.06, -0.1)), sh + V((0.08, -0.12, -0.2))], [0.03, 0.028, 0.024], seg=7), PWOOD, True)
    K.add('Body', bm_sphere(sh + V((0.08, -0.12, -0.2)), (0.024, 0.024, 0.018), seg=6, rings=4), 'M_TornEdge', False)
    sh2 = V((-0.25, -0.06, h * 0.6))
    for dz in (-0.02, 0.02):
        K.add('Lines', CR.line([sh2 + V((0, 0, dz)), sh2 + V((-0.1, -0.08, -0.12 + dz)), sh2 + V((-0.12, -0.16, -0.26 + dz))], 0.0035, over=0.03, seed=81 + dz), PENCIL, False)
    D_ = (V((-0.02, -0.08, -0.14))).normalized()
    from ouat_creatures import ink_hand

    class _P:
        def add(self, b, mat, smooth=True):
            K.add('Lines', b, mat, False)
    ink_hand(_P(), sh2 + V((-0.12, -0.16, -0.26)), D_, ln=0.09, side=-1, r=0.003)
    # the red cord tied round the neck: same cord as on the hero's cape (pivot at the knot)
    knot = None
    hit = bvh.ray_cast(V((0.1, -1.0, h * 0.78)), V((0, 1, 0)))
    knot = hit[0] + hit[1] * 0.012 if hit[0] is not None else V((0.1, -0.2, h * 0.78))
    band = []
    for i in range(17):
        a = 2 * math.pi * i / 16
        d = V((math.cos(a), math.sin(a) * 0.85, 0))
        q = bvh.ray_cast(V((0, 0, h * 0.8)) + d * 2.0, -d)
        if q[0] is not None:
            band.append(q[0] + q[1] * 0.008)
    if len(band) > 6:
        K.add('Cord', bm_blade(band, [0.012] * len(band), thick=0.004, up=(0, 0, 1)), OFFER, False)
    sol, lin = red_cord_pieces(seed=2.0, s=1.0)
    nrm = (knot - V((0, 0, knot.z))).normalized()
    ang = math.degrees(math.atan2(nrm.x, -nrm.y))
    for b_, m_ in sol:
        K.add('Cord', xf(b_, rz=ang, pos=knot), m_, False)
    for b_, m_ in lin:
        K.add('Lines', xf(b_, rz=ang, pos=knot), m_, False)
    K.add('Lines', CR.smudge((0.0, -0.3, 0.005), (0, 0, 1), 0.5, 0.3, seed=82, lift=0.004), SMUDGE, False)
    return K.finish(0.8, "Kinopio's brother - a failed body returned by the fish, kept on a chair as the 'shell'. A slumped wooden mass in "
                         "Kinopio's colours (blue shirt top, red shorts foot), his hex face plank sunk and tilted (ring eye on the left, "
                         "carved hole on the right = Kinopio mirrored, one eye melted into a drip), a short drooping sketch-line nose "
                         "(Nose, M_SketchNose) and a navy cap whose back half is pencil. The red offering cord is tied round the neck "
                         "(Cord, knot = same cord as the hero's). One arm a stub, the other only pencil + ink hand. Root = seat.",
                    pivots={'Nose': tuple(nb), 'Cord': tuple(knot)}, parents={'Nose': 'Body', 'Cord': 'Body', 'Lines': 'Body'})


def build_lump_4():
    """sitting body whose legs fused into a puddle: one leg still sticks out forward and stops at a tear, egg head fused into the shoulder"""
    K = Kit('Lump_4')
    h, r = 0.62, 0.24
    m = melt_mass(h, r, 91, lean=(0.08, 0.02), seg=16, pool=1.55)
    bvh = BVHTree.FromBMesh(m)
    K.add('Body', m, PWOOD, True, lambda c, n: RED if (c.z + nval(c, 8.0, 92) * 0.04) < h * 0.18 else None)
    drips_on(K, 'Body', bvh, h * 0.18, (0, 0), 6, 'M_PaintRedBrush', 93, ln=(0.03, 0.08), w=0.016, arc=(-180, 0))
    # egg head fused into the right shoulder, one hole eye + one groove eye, crown flattened
    hc = V((0.13, -0.04, h * 0.98))
    head = bm_sphere(hc, (0.11, 0.1, 0.14), seg=12, rings=8)
    deform(head, lambda c: c + V((0, 0, -0.04 * max(0.0, (hc.z - c.z) / 0.14) ** 1.5)))
    rot(head, 'Y', 28, hc)
    jitter(head, 0.006, 8.0, 94)
    hv = BVHTree.FromBMesh(head)
    K.add('Body', head, PWOOD, True, lambda c, n: BLUE if c.z > hc.z + 0.07 + nval(c, 14.0, 95) * 0.02 else None)
    hit = hv.ray_cast(V((hc.x + 0.02, -1, hc.z + 0.02)), V((0, 1, 0)))
    if hit[0] is not None:
        e = bm_sphere((0, 0, 0), (0.022, 0.01, 0.03), seg=8, rings=5)
        L.xform(e, hit[1].to_track_quat('-Y', 'Z').to_matrix().to_4x4())
        K.add('Body', move(e, hit[0] - hit[1] * 0.003), INK, False)
    hit = hv.ray_cast(V((hc.x - 0.05, -1, hc.z + 0.01)), V((0, 1, 0)))
    if hit[0] is not None:
        K.add('Lines', stroke([hit[0] + V((-0.015, -0.004, 0.005)), hit[0] + V((0.015, -0.004, -0.003))], 0.004, seg=3), INK, False)
    # forward leg: carved thigh + knee joint, the shin stops at a torn end, the foot only pencil
    hip = V((-0.1, -0.18, 0.12))
    knee = hip + V((-0.05, -0.28, 0.1))
    K.add('Body', bm_tube([hip, hip.lerp(knee, 0.5), knee], [0.062, 0.058, 0.052], seg=8), PWOOD, True, lambda c, n: RED if c.y > -0.32 else None)
    K.add('Body', bm_sphere(knee, (0.056,) * 3, seg=8, rings=5), PJOINT, False)
    shin_end = knee + V((0.0, -0.08, -0.07))
    full = bm_tube([knee, knee + V((0, -0.06, -0.05)), knee + V((0.0, -0.1, -0.12)), knee + V((0, -0.12, -0.17))], [0.046, 0.044, 0.04, 0.038], seg=8)
    tri_ngons(full)
    K.form('Body', 'Lines', full, lambda c: 0.1 - (c - knee).length + nval(c, 30.0, 96) * 0.02, PWOOD, thick=0.006, zig=0.008, seed=96,
           hatch_kw=dict(spacing=0.015, length=(0.02, 0.05), r=0.0022, slant=30, density=0.7, up_only=False), back_near=None, ink_r=0.003)
    ank = knee + V((0, -0.12, -0.17))
    K.add('Lines', CR.box_wire(ank + V((0, -0.05, -0.02)), (0.07, 0.13, 0.05), r=0.0025, over=0.03, seed=97), PENCIL, False)
    for s in (-1, 1):
        K.add('Lines', CR.line([knee + V((s * 0.033, -0.08, -0.08)), ank + V((s * 0.03, 0, 0))], 0.0025, over=0.03, seed=98 + s), PENCIL, False)
    # left arm only drawn (pencil cylinder + ink hand) hanging down the side
    sh = V((-0.2, -0.02, h * 0.66))
    for dz in (-0.022, 0.022):
        K.add('Lines', CR.line([sh + V((0, 0, dz)), sh + V((-0.08, -0.04, -0.2 + dz)), sh + V((-0.1, -0.06, -0.38 + dz))], 0.0035, over=0.04, seed=99 + dz), PENCIL, False)
    K.add('Lines', CR.ellipse(sh, 0.035, 0.035, 0.0, turns=1.1, n=10, r=0.003, seed=100, tilt=('X', 90)), PENCIL, False)
    K.add('Lines', CR.smudge((0.0, -0.1, 0.004), (0, 0, 1), 0.6, 0.4, seed=101, lift=0.004), SMUDGE, False)
    return K.finish(0.8, "Generic failed body (better replacement for Lump_1/3): a sitting body whose legs fused into a wide red puddle; one leg "
                         "still sticks forward, stops at a torn shin, its foot only a pencil box. Egg head fused into the right shoulder "
                         "(hole eye + groove eye). Left arm only drawn. Root = seat.", parents={'Lines': 'Body'})


def build_lump_5():
    """a body folded double, head resting on its knees; the back is an open shell (hollow inside, pencil ribs)"""
    K = Kit('Lump_5')
    # folded torso: a bent tube (hips -> shoulders bending forward and down)
    pts = [V((0, 0.12, 0.05)), V((0, 0.125, 0.16)), V((0, 0.12, 0.27)), V((0, 0.09, 0.37)), V((0, 0.04, 0.45)), V((0, -0.03, 0.49)),
           V((0, -0.11, 0.48)), V((0, -0.19, 0.43)), V((0, -0.25, 0.36)), V((0, -0.28, 0.29))]
    rr = [0.2, 0.205, 0.2, 0.195, 0.185, 0.175, 0.165, 0.155, 0.14, 0.12]
    b = bm_tube(pts, rr, seg=16, cap=True, flat=0.85, up=(1, 0, 0))
    tri_ngons(b)
    jitter(b, 0.015, 5.0, 111)
    deform(b, lambda c: V((c.x, c.y, max(0.0, c.z))))
    # the back of the shell is open: torn window, hollow inside visible, pencil ribs inside
    K.form('Body', 'Lines', b, lambda c: ((c.y - 0.06) ** 2) / 0.025 + ((c.z - 0.47) ** 2) / 0.01 + (c.x ** 2) / 0.02 - 1.0 + nval(c, 9.0, 112) * 0.4,
           PWOOD, paint=lambda c, n: BLUE if (c.z + nval(c, 8.0, 113) * 0.04) > 0.36 else None, thick=0.02, zig=0.015, seed=114,
           hatch_kw=dict(spacing=0.03, length=(0.04, 0.1), r=0.003, slant=30, density=0.7), back_near=None, ink_r=0.005)
    for k in range(4):
        y = -0.05 + 0.06 * k
        K.add('Lines', CR.line([V((-0.09, y, 0.38)), V((-0.04, y, 0.45)), V((0.04, y, 0.45)), V((0.09, y, 0.38))], 0.003, over=0.02, seed=115 + k), PENCIL, False)
    # knees (two joints) under the bent chest, shins folded back
    for x in (-0.09, 0.09):
        kn = V((x, -0.3, 0.12))
        K.add('Body', bm_sphere(kn, (0.05,) * 3, seg=8, rings=5), PJOINT, False)
        K.add('Body', bm_tube([V((x, 0.08, 0.08)), kn], [0.06, 0.05], seg=8), PWOOD, True)
        K.add('Body', bm_tube([kn, V((x * 1.1, -0.05, 0.04)), V((x * 1.1, 0.1, 0.03))], [0.045, 0.04, 0.035], seg=8), PWOOD, True, lambda c, n: RED)
    # box head resting on the knees, face down-forward; three holes; one side melted
    hc = V((0.0, -0.36, 0.25))
    head = bm_box(hc, (0.2, 0.17, 0.18))
    head = L.bevel(head, 0.03, 1, 40)
    rot(head, 'X', -35, hc)
    rot(head, 'Y', 12, hc)
    deform(head, lambda c: c + V((0, 0, -0.03 * max(0.0, c.x - hc.x) / 0.1)))
    jitter(head, 0.004, 10.0, 116)
    hv = BVHTree.FromBMesh(head)
    K.add('Body', head, PWOOD, False)
    for dx, dz in ((-0.045, 0.02), (0.045, 0.025), (0.0, -0.035)):
        hit = hv.ray_cast(V((hc.x + dx, hc.y - 1, hc.z + dz)), V((0, 1, 0)))
        if hit[0] is not None:
            e = bm_sphere((0, 0, 0), (0.017, 0.009, 0.017), seg=7, rings=4)
            L.xform(e, hit[1].to_track_quat('-Y', 'Z').to_matrix().to_4x4())
            K.add('Body', move(e, hit[0] - hit[1] * 0.002), INK, False)
    # arms: one hanging built arm with a mitten, the other only pencil
    K.add('Body', bm_tube([V((0.17, -0.1, 0.38)), V((0.2, -0.2, 0.22)), V((0.2, -0.25, 0.06))], [0.035, 0.032, 0.03], seg=7), PWOOD, True, lambda c, n: BLUE if c.z > 0.3 else None)
    K.add('Body', bm_sphere((0.2, -0.26, 0.04), (0.04, 0.03, 0.045), seg=7, rings=5), PWOOD, False)
    for dz in (-0.02, 0.02):
        K.add('Lines', CR.line([V((-0.17, -0.1, 0.38 + dz)), V((-0.2, -0.2, 0.22 + dz)), V((-0.21, -0.25, 0.05 + dz))], 0.0035, over=0.04, seed=117 + dz), PENCIL, False)
    K.add('Lines', CR.smudge((0.0, -0.1, 0.004), (0, 0, 1), 0.55, 0.4, seed=118, lift=0.004), SMUDGE, False)
    return K.finish(0.6, "Generic failed body (better replacement for Lump_2): a body folded double, box head (three holes) resting on its "
                         "knees as if bowing forever. Its back is an open shell - hollow inside, pencil ribs where the body was never "
                         "drawn. One arm built, one only pencil. Root = seat.", parents={'Lines': 'Body'})


# ===================================================================== Kinopio's house: nose-file stone + sawdust
def build_nose_file_stone():
    K = Kit('NoseFileStone')
    W, Dp, H = 0.52, 0.32, 0.26
    b = bm_sphere((0, 0, H * 0.45), (W * 0.56, Dp * 0.6, H * 0.62), seg=18, rings=10)
    deform(b, lambda c: V((c.x, c.y, min(max(c.z, 0.0), H + 0.02 * nval(c, 6.0, 120)))))
    tri_ngons(b)
    jitter(b, 0.012, 5.0, 121)
    # top: worn diagonal groove where the nose is rubbed
    gd = V((math.cos(math.radians(20)), math.sin(math.radians(20)), 0))

    def groove(c):
        if c.z < H - 0.04:
            return c
        q = V((c.x, c.y, 0))
        dperp = (q - gd * q.dot(gd)).length
        c.z -= 0.035 * math.exp(-(dperp / 0.045) ** 2) * (1 - min(1.0, abs(q.dot(gd)) / 0.3) ** 4)
        return c
    deform(b, groove)
    fld = lambda c: c.x + 0.12 + nval(c, 7.0, 122) * 0.06
    full, res = K.form('Stone', 'Lines', b, fld, 'M_Whetstone', thick=0.02, zig=0.015, seed=123, back_near=0.2,
                       paint=lambda c, n: 'M_TornEdge' if (n.z > 0.4 and c.z < H - 0.008 and c.z > H - 0.06) else None,
                       hatch_kw=dict(spacing=0.03, length=(0.04, 0.12), r=0.003, slant=35, density=0.8), ink_r=0.005)
    K.add('Lines', CR.wire_drawn(full, lambda c, n: fld(c) > 0, angle=50, r=0.0035, over=0.05, seed=124), PENCIL, False)
    for k in range(3):
        K.add('Lines', CR.ellipse((-0.2, 0, H * 0.45), 0.12, Dp * 0.6, 0.0, turns=0.7, n=10, r=0.003, seed=126 + k, tilt=('Y', 90), a0=k), PENCIL, False)
    # groove ink + scratch strokes along it; graphite (nose) dust in the groove
    for k in range(5):
        o = V((-gd.y, gd.x, 0)) * (k - 2) * 0.012
        K.add('Lines', stroke([o - gd * 0.18 + V((0, 0, H - 0.028)), o + gd * 0.03 + V((0, 0, H - 0.033)), o + gd * 0.2 + V((0, 0, H - 0.02))], 0.0018, seg=3), INK, False)
    K.add('Lines', CR.smudge(V((0.02, 0.01, H - 0.03)), (0, 0, 1), 0.34, 0.08, seed=125, lift=0.006, up=(-gd.y, gd.x, 0)), SMUDGE, False)
    for s_ in (-1, 1):   # ink lips of the worn groove
        o = V((-gd.y, gd.x, 0)) * s_ * 0.05
        K.add('Lines', stroke([o - gd * 0.2 + V((0, 0, H - 0.004)), o + V((0, 0, H + 0.004)), o + gd * 0.22 + V((0, 0, H - 0.004))], 0.004, seg=3), INK, False)
    for k in range(6):
        p = V((0.04 * k - 0.1, -0.02 + 0.01 * k, H - 0.03))
        K.add('Stone', bm_blade([p, p + V((0.01, 0.006, 0.006)), p + V((0.02, 0.0, 0.004))], [0.004, 0.006, 0.002], thick=0.002), 'M_Shaving', False)
    # the shape is a reused stone: old ink chisel marks on the front
    for k in range(4):
        x = 0.0 + 0.05 * k
        K.add('Lines', stroke([V((x, -Dp * 0.6 - 0.004, 0.08 + 0.02 * k)), V((x + 0.03, -Dp * 0.6 - 0.004, 0.11 + 0.02 * k))], 0.003, seg=3), INK, False)
    return K.finish(0.6, "Kinopio's nose-filing stone (0.52 x 0.32 x 0.26 m) in his house: grey paper-stone with a worn diagonal groove on top "
                         "(graphite smudge + shavings in it). Unfinished: the left third of the block is only pencil (torn edge).",
                    parents={'Lines': 'Stone'})


def shaving(p, rnd, s=1.0):
    """curled wood shaving: a twisted blade spiralling once"""
    a0 = rnd.uniform(0, 6.28)
    rr = rnd.uniform(0.015, 0.03) * s
    ln = rnd.uniform(0.04, 0.09) * s
    pts = [V(p) + V((math.cos(a0 + t * 4.0) * rr * (1 - 0.3 * t), math.sin(a0 + t * 4.0) * rr * (1 - 0.3 * t), rr + t * ln * 0.3)) for t in [i / 6 for i in range(7)]]
    M = Matrix.Rotation(rnd.uniform(-1.2, 1.2), 3, 'X') @ Matrix.Rotation(rnd.uniform(0, 6.28), 3, 'Z')
    pts = [V(p) + M @ (q - V(p)) for q in pts]
    for i in range(len(pts)):
        pts[i].z = max(pts[i].z, 0.004)
    return bm_blade(pts, [0.004, 0.009, 0.011, 0.011, 0.01, 0.008, 0.003], thick=0.0015, up=(0, 0, 1))


def build_sawdust_pile():
    K = Kit('SawdustPile')
    rnd = random.Random(131)
    R0, H0 = 0.36, 0.15
    heaps = []
    for (hx, hy, hr, hh, sd) in ((0.0, 0.0, 0.24, 0.16, 1), (0.2, 0.1, 0.16, 0.1, 2), (-0.17, 0.12, 0.14, 0.08, 3), (0.08, -0.18, 0.12, 0.06, 4)):
        hp = bm_lathe([(0.0, 0.0), (hr, 0.0), (hr * 0.75, hh * 0.3), (hr * 0.4, hh * 0.75), (0.0, hh)], seg=12, center=(hx, hy, 0), sy=0.85)
        jitter(hp, hr * 0.08, 9.0, 132 + sd)
        heaps.append(hp)
    mound = merge(heaps)
    deform(mound, lambda c: V((c.x, c.y, max(0.0, c.z))))
    bv = BVHTree.FromBMesh(mound)
    K.add('Pile', mound, 'M_PuppetJoint', True, lambda c, n: 'M_Shaving' if (n.z > 0.55 or nval(c, 14.0, 133) > 0.15) else None)
    for k in range(16):
        a = rnd.uniform(0, 6.28)
        d = rnd.uniform(0, 0.9) ** 0.7 * R0
        x, y = math.cos(a) * d, math.sin(a) * d * 0.8
        K.add('Pile', shaving(V((x, y, ray_down(bv, x, y) - 0.008)), rnd, 1.6), 'M_Shaving', False)
    # stray shavings around
    for k in range(6):
        a = rnd.uniform(0, 6.28)
        d = rnd.uniform(R0 * 1.05, R0 * 1.7)
        K.add('Pile', shaving(V((math.cos(a) * d, math.sin(a) * d * 0.8, 0.0)), rnd, 1.3), 'M_Shaving', False)
    # what was filed off: short pieces of the sketch-line nose lying in the dust (graphite sticks), + graphite smudge
    for k in range(7):
        a = rnd.uniform(0, 6.28)
        d = rnd.uniform(0.0, 0.8) * R0
        x, y = math.cos(a) * d, math.sin(a) * d * 0.8
        z = ray_down(bv, x, y) + 0.004
        ln = rnd.uniform(0.07, 0.15)
        dd = V((math.cos(a + 1.3), math.sin(a + 1.3), rnd.uniform(-0.05, 0.3))).normalized()
        K.add('Pile', stroke([V((x, y, z)), V((x, y, z)) + dd * ln * 0.5, V((x, y, z)) + dd * ln], 0.008, seg=4), 'M_SketchNose', False)
    K.add('Lines', CR.smudge((0.05, -0.02, 0.002), (0, 0, 1), 1.0, 0.7, seed=134, lift=0.003), SMUDGE, False)
    # unfinished: the far side of the pile is only drawn - pencil curls and the planned outline
    for k in range(5):
        c = V((0.15 + 0.06 * k, 0.24 - 0.02 * k, 0.03))
        K.add('Lines', D.loop(c, 0.025, 0.018, n=8, r=0.0022, seed=135 + k), PENCIL, False)
    K.add('Lines', CR.ellipse((0, 0, 0.004), R0 * 1.2, R0 * 0.95, 0.0, turns=0.6, n=20, r=0.0025, seed=140, a0=-0.2), PENCIL, False)
    return K.finish(0.8, "Floor of Kinopio's house: a low pile of wood shavings and dust (0.7 m) - and among them short pieces of his "
                         "translucent sketch-line nose (M_SketchNose), what he files off after each lie. Far side only pencil.",
                    parents={'Lines': 'Pile'})


# ===================================================================== Kinopio's secret den: hidden stash + wall drawing
def build_hidden_stash():
    K = Kit('HiddenStash')
    rnd = random.Random(151)
    # nest of rags: a ring of crumpled cloth (creature rags, a few painted strips), one sector only pencil
    nest = bmesh.new()
    R0, w = 0.4, 0.085
    nu, nv = 16, 6
    vs = []
    for i in range(nu):
        a = 2 * math.pi * i / nu
        row = []
        for j in range(nv):
            b_ = 2 * math.pi * j / nv
            k_ = 1 + 0.45 * math.sin(a * 3 + 1) + 0.25 * math.sin(a * 7 + 2)
            rr = R0 + math.cos(b_) * w * k_
            z = 0.06 + math.sin(b_) * w * 0.8 * k_
            row.append(nest.verts.new(V((math.cos(a) * rr, math.sin(a) * rr * 0.85, max(0.0, z)))))
        vs.append(row)
    for i in range(nu):
        for j in range(nv):
            nest.faces.new((vs[i][j], vs[(i + 1) % nu][j], vs[(i + 1) % nu][(j + 1) % nv], vs[i][(j + 1) % nv]))
    for f in nest.faces:
        c = f.calc_center_median()
        a = math.atan2(c.y / 0.85, c.x)
        ctr = V((math.cos(a) * R0, math.sin(a) * R0 * 0.85, 0.06))
        if (c - ctr).dot(f.normal) < 0:
            f.normal_flip()
    jitter(nest, 0.035, 4.0, 152)
    jitter(nest, 0.015, 11.0, 153)
    deform(nest, lambda c: V((c.x, c.y, max(0.0, c.z))))
    tri_ngons(nest)

    rag_paint = None
    K.form('Nest', 'Lines', nest, lambda c: (abs(((math.atan2(c.y, c.x) - 1.9 + math.pi) % (2 * math.pi)) - math.pi) - 0.5) + nval(c, 6.0, 154) * 0.2,
           SACK, paint=rag_paint, thick=0.012, zig=0.02, seed=155, back_near=None,
           hatch_kw=dict(spacing=0.05, length=(0.04, 0.1), r=0.003, slant=30, density=0.45), ink_r=0.004)
    # rags draped over the ring from the inside floor out onto the ground (crumpled sheets; two once painted)
    for k in range(8):
        a = -2.2 + k * 0.62 + rnd.uniform(-0.12, 0.12)
        if abs(((a - 1.9 + math.pi) % (2 * math.pi)) - math.pi) < 0.6:
            continue
        ca, sa = math.cos(a), math.sin(a) * 0.85
        r_in, r_out = rnd.uniform(0.12, 0.22), rnd.uniform(0.52, 0.62)
        pts = [V((ca * r_in, sa * r_in, 0.02)), V((ca * 0.3, sa * 0.3, 0.1)), V((ca * R0, sa * R0, 0.17 + rnd.uniform(-0.02, 0.03))),
               V((ca * 0.5, sa * 0.5, 0.07)), V((ca * r_out, sa * r_out, 0.012))]
        wd = rnd.uniform(0.08, 0.13)
        sheet = bm_blade(pts, [wd * 0.6, wd, wd * 1.1, wd, wd * 0.7], thick=0.012, up=(0, 0, 1))
        jitter(sheet, 0.012, 14.0, 160 + k)
        mat = (RED, SACK, BLUE, SACKD, SACK, SACK, RED, SACK)[k]
        K.add('Nest', sheet, mat, False)
        K.add('Lines', stroke([p + V((0, 0, 0.016)) for p in pts[1:4]], 0.003, seg=3), INK, False)
    for k in range(4):   # the missing rags drawn as loose pencil loops
        a = 1.9 + (k - 1.5) * 0.25
        K.add('Lines', D.loop(V((math.cos(a) * R0, math.sin(a) * R0 * 0.85, 0.09)), 0.1, 0.06, n=10, r=0.0025, seed=156 + k, tilt=(70, 0, math.degrees(a))), PENCIL, False)
    floor = bm_lathe([(0.0, 0.0), (R0 - 0.02, 0.0)], seg=14, sy=0.85)
    move(floor, (0, 0, 0.012))
    K.add('Nest', floor, SACKD, False)
    # fallen human treasures (finished, vivid)
    T = 'Treasure'
    put_pieces(K, T, P.junk_book('M_BookBlue', 0.75), (-0.08, 0.06, 0.018), rz=-20)
    put_pieces(K, T, P.junk_book('M_BookRed', 0.6), (-0.05, 0.08, 0.072), rz=15, rx=4)
    put_pieces(K, T, junk_spoon(1.4), (0.18, -0.12, 0.02), rz=55)
    put_pieces(K, T, junk_button(1.5, 'M_BookRed'), (0.06, -0.2, 0.014), rx=8)
    put_pieces(K, T, junk_button(1.2, 'M_Porcelain'), (0.13, -0.24, 0.013), rx=-6)
    put_pieces(K, T, P.junk_clock(0.7), (0.2, 0.12, 0.012), rz=-30, rx=-12)
    put_pieces(K, T, junk_bottle(1.1), (-0.22, -0.12, 0.02), rz=70, ry=82)
    put_pieces(K, T, junk_glasses(1.3), (0.0, -0.07, 0.03), rz=10)
    put_pieces(K, T, junk_marble(1.3, 'M_BookGreen'), (-0.12, -0.22, 0.012))
    put_pieces(K, T, P.junk_teacup(1.1), (0.27, -0.02, 0.012), rz=40)
    # a fold of the hero-style red ribbon? no: a plain human hair ribbon (Rope red), human, finished
    K.add(T, bm_blade([V((-0.3, 0.05, 0.03)), V((-0.25, 0.12, 0.04)), V((-0.18, 0.14, 0.03)), V((-0.12, 0.2, 0.05))], [0.012, 0.014, 0.014, 0.01], thick=0.003), 'M_Rope', False)
    return K.finish(1.0, "Kinopio's hidden stash in the secret den (0.95 m): a nest of creature rags (a few painted red/blue strips), one sector "
                         "of the ring only pencil loops. Inside, fallen human things he kept instead of offering them - finished, vivid: blue "
                         "and red books, brass spoon, buttons, small clock, green bottle, spectacles, marbles, a teacup, a hair ribbon.",
                    parents={'Treasure': 'Nest', 'Lines': 'Nest'})


def build_wall_drawing():
    K = Kit('WallDrawing')
    W, H, z0 = 1.0, 0.72, 0.3
    # patch: the wall rubbed clean where the children drew (irregular slab, 1 cm)
    outline = []
    rnd = random.Random(161)
    for i in range(18):
        a = 2 * math.pi * i / 18
        rr = 1.0 + rnd.uniform(-0.05, 0.06)
        outline.append((math.cos(a) * (W / 2 + 0.09) * rr, z0 + H / 2 + math.sin(a) * (H / 2 + 0.08) * rr))
    patch = L.bm_prism(outline, -0.012, 0.0, axis='Y')
    tri_ngons(patch)
    K.add('Patch', patch, 'M_TornEdge', False)
    face = L.bm_plane_uv((0, -0.016, z0 + H / 2), (W, H), normal='-Y')
    K.add('Face', face, 'M_TornEdge', False)
    # stray marks outside the picture: tally marks (days counted), a scribbled spiral, a height mark with two ticks
    for k in range(6):
        x = W / 2 + 0.03 + 0.025 * k
        if k == 5:
            K.add('Lines', stroke([V((W / 2 + 0.02, -0.018, z0 + 0.14)), V((W / 2 + 0.17, -0.018, z0 + 0.06))], 0.004, seg=3), INK, False)
        else:
            K.add('Lines', stroke([V((x, -0.018, z0 + 0.05)), V((x + 0.006, -0.018, z0 + 0.16))], 0.004, seg=3), INK, False)
    sp = [V((-W / 2 - 0.05 + math.cos(t * 1.1) * 0.006 * t, -0.018, z0 + H - 0.05 + math.sin(t * 1.1) * 0.006 * t)) for t in range(1, 18)]
    K.add('Lines', stroke(sp, 0.0035, seg=3), INK, False)
    for k, (z, w_) in enumerate(((0.87, 0.12), (1.05, 0.1))):   # two children's heights marked on the wall
        K.add('Lines', stroke([V((-W / 2 + 0.05, -0.018, z)), V((-W / 2 + 0.05 + w_, -0.018, z + 0.004))], 0.005, seg=3), INK, False)
    return K.finish(1.2, "Children's wall drawing in the secret den. Root = floor at the wall base (wall plane = local y 0, picture faces Unity +Z). "
                         "Face = UV 0..1 quad 1.0 x 0.72 m at 0.30-1.02 m (child height) for the drawing texture (two children and the "
                         "light hole). Patch = the rubbed-clean wall behind it. Lines = tally marks, a scribble and two height marks.",
                    parents={'Face': 'Patch', 'Lines': 'Patch'})


# ===================================================================== plaza bell on a half-built frame
def build_bell():
    K = Kit('Bell')
    Wd, Hb = 1.9, 2.75
    W = 'M_StageWood'
    # left post fully built (painted plaza wood) + brace + foot stone
    K.add('Frame', P.bbox((-Wd / 2, 0, Hb / 2), (0.16, 0.16, Hb), 0.02), W, False)
    K.add('Frame', P.bbox((-Wd / 2, 0, 0.09), (0.36, 0.36, 0.18), 0.02), 'M_TerracottaDark', False)
    K.add('Frame', bm_tube([V((-Wd / 2 + 0.06, 0, 1.6)), V((-Wd / 2 + 0.55, 0, Hb - 0.1))], 0.04, seg=5), W, False)
    # crossbeam built from the left to ~60 %, torn there; the rest pencil
    beam = CR.grid_box((0, 0, Hb), (Wd + 0.3, 0.16, 0.18), step=0.1)
    fld = lambda c: 0.32 - c.x + nval(c, 6.0, 171) * 0.08
    fullb, resb = K.form('Frame', 'Lines', beam, fld, W, thick=0.02, zig=0.02, seed=172, back_near=0.3,
                         hatch_kw=dict(spacing=0.06, length=(0.08, 0.25), r=0.004, slant=30, density=0.55), ink_r=0.007)
    K.add('Lines', CR.wire_drawn(fullb, lambda c, n: fld(c) > 0, r=0.005, over=0.12, seed=173), PENCIL, False)
    # right post: built only to ~0.9 m, the rest planned in pencil (+ plumb line, scaffold)
    post = CR.grid_box((Wd / 2, 0, Hb / 2), (0.16, 0.16, Hb), step=0.1)
    fldp = lambda c: 0.9 + nval(c, 5.0, 174) * 0.12 - c.z
    fullp, resp = K.form('Frame', 'Lines', post, fldp, W, thick=0.02, zig=0.02, seed=175, back_near=0.3,
                         hatch_kw=dict(spacing=0.06, length=(0.1, 0.3), r=0.004, slant=30, density=0.55), ink_r=0.007)
    K.add('Lines', CR.wire_drawn(fullp, lambda c, n: fldp(c) > 0, r=0.005, over=0.15, seed=176), PENCIL, False)
    K.add('Frame', P.bbox((Wd / 2, 0, 0.09), (0.36, 0.36, 0.18), 0.02), 'M_TerracottaDark', False)
    K.add('Lines', CR.guides([(V((Wd / 2 + 0.25, -0.1, 0.1)), V((Wd / 2 + 0.25, -0.1, Hb + 0.4))),
                              (V((-Wd / 2 - 0.4, -0.1, Hb + 0.25)), V((Wd / 2 + 0.6, -0.1, Hb + 0.25)))], r=0.004, over=0.3, seed=177), PENCIL, False)
    for k, z in enumerate((0.5, 1.2, 1.9)):   # ink grain on the built post
        K.add('Lines', line([V((-Wd / 2 - 0.02, -0.083, z)), V((-Wd / 2 + 0.03, -0.083, z + 0.5))], 0.004, 178 + k), INK, False)
    # bell (pivot = yoke): painted bronze, ink bands, crown loops, finished (the plaza's)
    yoke = V((0, 0, Hb - 0.1))
    prof = [(0.07, -0.02), (0.15, -0.04), (0.2, -0.12), (0.22, -0.3), (0.25, -0.5), (0.33, -0.66), (0.37, -0.72)]
    top = Hb - 0.16
    outer = bm_lathe([(r_, top + z) for r_, z in prof], seg=16, cap_top=False, cap_bottom=False)
    tri_ngons(outer)
    CR.orient_out(outer, (0, 0))
    K.add('BellBody', outer, 'M_BellBronze', True)
    inner = bm_lathe([(r_ - 0.03, top + z - 0.02) for r_, z in prof[2:]], seg=16, cap_top=False, cap_bottom=True)
    tri_ngons(inner)
    for f in inner.faces:
        c = f.calc_center_median()
        hz = V((c.x, c.y, 0))
        if (hz.length > 0.05 and hz.dot(f.normal) > 0) or (hz.length <= 0.05 and f.normal.z > 0):
            f.normal_flip()
    K.add('BellBody', inner, 'M_BellInner', False)
    K.add('BellBody', bm_lathe([(0.37, top - 0.72), (0.34, top - 0.72)], seg=16, cap_top=False, cap_bottom=False), 'M_BellBronze', False)
    K.add('BellBody', bm_lathe([(0.0, top - 0.02), (0.07, top - 0.02), (0.06, top + 0.04), (0.0, top + 0.05)], seg=10), 'M_BellBronze', False)
    for x in (-0.04, 0.04):
        K.add('BellBody', bm_tube([V((x, 0, top + 0.03)), V((x, 0, yoke.z + 0.0)), V((x * 0.3, 0, yoke.z + 0.04))], 0.014, seg=5), 'M_TerracottaDark', False)
    K.add('BellBody', bm_tube([V((0, -0.1, yoke.z + 0.02)), V((0, 0.1, yoke.z + 0.02))], 0.025, seg=6), 'M_TerracottaDark', False)
    for z in (-0.18, -0.6):
        r_ = 0.212 if z > -0.3 else 0.3
        K.add('Lines', stroke(CR.ring_pts(0, 0, top + z, r_ + 0.006, 24), 0.005, seg=3, taper=False), INK, False)
    # painted creature glyph band (red, hand-brushed) round the waist, not quite closed
    band = CR.ring_pts(0, 0, top - 0.42, 0.24, 20, a0=-150, a1=160)
    K.add('BellBody', bm_blade(band, [0.03] * len(band), thick=0.004, up=(0, 0, 1)), 'M_PaintRedBrush', False)
    # clapper (pivot = inside the crown) + the pull cord hanging down out of the mouth
    cp = V((0, 0, top - 0.06))
    K.add('Clapper', bm_tube([cp, cp + V((0, 0, -0.5))], 0.018, seg=6), 'M_TerracottaDark', False)
    K.add('Clapper', bm_sphere(cp + V((0, 0, -0.56)), (0.06, 0.06, 0.07), seg=10, rings=6), 'M_BellBronze', False)
    cord = [cp + V((0, 0, -0.62)), cp + V((0.02, -0.02, -0.95)), cp + V((0.0, -0.03, -1.3)), cp + V((0.03, -0.02, -1.62))]
    K.add('Clapper', bm_tube(cord, 0.011, seg=4), SACKD, False)
    K.add('Clapper', bm_sphere(cord[-1], (0.025, 0.025, 0.04), seg=6, rings=4), SACKD, False)
    return K.finish(2.9, "Plaza bell (rung as the offering day nears). Frame half built: left post, brace and 60 % of the beam are painted wood, "
                         "the beam's right part and the right post above 0.9 m are pencil (scaffold guides). Bell = painted bronze with a "
                         "red brushed band (finished, pivot = yoke: swing about local X). Clapper pivot = inside the crown, pull cord to "
                         "1.0 m above the floor.", pivots={'BellBody': tuple(yoke), 'Clapper': tuple(cp)}, parents={'Clapper': 'BellBody', 'Lines': 'Frame'})


# ===================================================================== offering pile for the cart
def build_offering_pile():
    K = Kit('OfferingPile')
    rnd = random.Random(181)
    # base: three small closed sacks (creature) lying on the bed, one with the red offering cord
    sacks = [((-0.24, 0.3, 0.0), 0.0, 0.0, 0.55, 182), ((0.22, 0.38, 0.0), 80.0, 25.0, 0.5, 183), ((0.0, -0.32, 0.0), -70.0, 15.0, 0.48, 184)]
    sack_meshes = []
    for (x, y, z), rz, ry, hh, sd in sacks:
        b = sack_body(hh, hh * 0.38, seg=9, seed=sd, neck=0.04, bulge=False)
        if ry:   # lying on its side
            move(b, (0, 0, -hh * 0.42))
            rot(b, 'Y', 72)
        xf(b, rz=rz, pos=(x, y, 0.0))
        mn = min(v.co.z for v in b.verts)
        move(b, (0, 0, -mn))
        sack_meshes.append(b)
    for i, b in enumerate(sack_meshes):
        K.add('Pile', b, SACK, True)
    # human things heaped on top (finished, vivid)
    T = 'Pile'
    put_pieces(K, T, P.junk_book('M_BookRed'), (-0.08, 0.05, 0.2), rz=20, rx=-14)
    put_pieces(K, T, P.junk_book('M_BookGreen', 0.9), (0.18, -0.05, 0.16), rz=-40, ry=10)
    put_pieces(K, T, P.junk_book('M_BookBlue', 0.85), (0.02, 0.1, 0.27), rz=75, ry=-6)
    put_pieces(K, T, P.junk_umbrella(1.0), (0.05, 0.0, 0.33), rz=-15, ry=6)
    put_pieces(K, T, P.junk_clock(), (-0.28, -0.12, 0.12), rz=25, rx=-18)
    put_pieces(K, T, P.junk_teacup(1.2), (-0.3, 0.45, 0.32), ry=20)
    put_pieces(K, T, P.junk_shoe(1.1), (0.32, -0.42, 0.05), rz=-35)
    put_pieces(K, T, junk_bottle(1.2), (-0.36, -0.42, 0.05), rz=-20, ry=80)
    # red offering cord tied on the top sack's neck (the 'to be offered' mark)
    sol, lin = red_cord_pieces(seed=3.0, s=1.4)
    for b_, m_ in sol:
        K.add('Pile', xf(b_, rz=-15, pos=(-0.22, 0.2, 0.44)), m_, False)
    for b_, m_ in lin:
        K.add('Lines', xf(b_, rz=-15, pos=(-0.22, 0.2, 0.44)), m_, False)
    allb = merge([CR.copy(pc[0]) for pc in K.parts['Pile'].pieces])
    bvhs = [BVHTree.FromBMesh(allb)]
    # a cord net thrown over the heap: knotted on the left, the right half only pencil (net never finished)
    for k in range(3):
        y = -0.4 + 0.4 * k
        pts = [V((x, y + 0.03 * math.sin(x * 9 + k), 0.0)) for x in [-0.5 + 0.1 * i for i in range(11)]]
        hpts = []
        for p in pts:
            zz = max([b.ray_cast(V((p.x, p.y, 3.0)), V((0, 0, -1)))[0].z for b in bvhs if b.ray_cast(V((p.x, p.y, 3.0)), V((0, 0, -1)))[0] is not None] + [0.05])
            hpts.append(V((p.x, p.y, zz + 0.02)))
        left = [p for p in hpts if p.x <= 0.05]
        right = [p for p in hpts if p.x >= 0.0]
        if len(left) > 1:
            K.add('Pile', bm_tube(left, 0.009, seg=3), SACKD, False)
        if len(right) > 1:
            K.add('Lines', CR.line(right, 0.003, over=0.05, seed=185 + k), PENCIL, False)
    for k in range(2):
        x = -0.38 + 0.22 * k
        pts = [V((x, y, 0)) for y in [-0.55 + 0.1 * i for i in range(12)]]
        hpts = []
        for p in pts:
            hs = [b.ray_cast(V((p.x, p.y, 3.0)), V((0, 0, -1)))[0] for b in bvhs]
            zz = max([h.z for h in hs if h is not None] + [0.05])
            hpts.append(V((p.x, p.y, zz + 0.02)))
        K.add('Pile', bm_tube(hpts, 0.009, seg=3), SACKD, False)
    for k in range(3):
        x = 0.15 + 0.13 * k
        K.add('Lines', CR.line([V((x, -0.55, 0.15)), V((x + 0.02, 0.0, 0.35)), V((x, 0.55, 0.2))], 0.003, over=0.05, seed=190 + k), PENCIL, False)
    return K.finish(1.4, "Offerings on the cart (fits the Cart bed 1.1 x 1.5 m, root = bed top centre: Unity Cart-local (0, 0.80, -0.10)). "
                         "Three creature sacks, human things heaped on top (finished: books, umbrella, clock, lantern, teacup, shoe, bottle), the "
                         "red offering cord on the top sack, a cord net knotted on the left half - its right half only pencil.",
                    parents={'Lines': 'Pile'})


ASSETS = [
    ('RedCord', build_red_cord), ('Sack', build_sack), ('Sack_Open', build_sack_open), ('HookPole', build_hook_pole),
    ('DecreeScroll', build_decree_scroll), ('DecreeOpen', build_decree_open), ('Lump_Brother', build_lump_brother),
    ('Lump_4', build_lump_4), ('Lump_5', build_lump_5), ('NoseFileStone', build_nose_file_stone), ('SawdustPile', build_sawdust_pile),
    ('HiddenStash', build_hidden_stash), ('WallDrawing', build_wall_drawing), ('Bell', build_bell), ('OfferingPile', build_offering_pile),
]
