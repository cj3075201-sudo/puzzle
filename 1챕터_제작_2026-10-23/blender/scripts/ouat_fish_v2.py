# -*- coding: utf-8 -*-
"""Giant Fish v2 (10/23): the king's courier. Rigged + baked clips (Legacy takes), replaces the old part-hierarchy Fish.fbx.

Design: a drawn-ink storybook monster rearing out of the black ink pond. The head is a dark, painted, finished shell
(huge underbite jaw, crooked paper teeth, small pale eyes under angry ink brows, catfish barbels, paper throat with
ink pleats). Behind the head the form stops being built: the paint runs out to bare paper, the skin is torn open
(paper back + torn rim + ink), and the body continues only as pencil construction rings / contour lines, pencil
dorsal spines and a pencil tail. One pectoral fin is built, the other only drawn. A few teeth are only ink outlines.
No self-glow anywhere.

Space: modelled in a horizontal 'fish local' frame (front -Y, Z up, mouth line z = 0, jaw hinge at y = HINGE_Y),
then rotated snout-up by PITCH and moved so the rest pose = the Idle pose (rearing half out of the water).
World (build) origin = pond surface centre; Unity y = 0 = water surface.
"""
import math, random
import bmesh
from mathutils import Vector, Matrix
import ouat_lib as L
import ouat_craft as CR
from ouat_lib import stroke, bm_tube, bm_blade, bm_sphere, nval, jitter
from ouat_rig import RigChar, E, FPS, Keys
import ouat_rig as RG

V = Vector
INK, PENCIL, HATCH = 'M_Ink', 'M_Pencil', 'M_Hatch'
SKIN, SCR, TOOTH, EYE, MOUTH, GUL, PAPER = 'M_FishSkin', 'M_FishScratch', 'M_FishTooth', 'M_FishEyePale', 'M_FishGum', 'M_Silhouette', 'M_Paper'

NEW_MATS = {
    'M_FishSkin':    ('3F5D63', '22363B', True,  'painted', {'note': 'Fish v2: dark ink-teal paint on the head and nape (stops behind the head -> bare paper)'}),
    'M_FishScratch': ('6F8C8E', '6F8C8E', False, 'line',    {'note': 'Fish v2: scratched light lines on the dark paint (scale arcs, skull plates). unlit, no outline'}),
    'M_FishTooth':   ('EEE6D2', 'B4AA92', True,  'paper',   {'note': 'Fish v2: paper teeth (unpainted)'}),
    'M_FishGum':     ('7E2E2A', '4C1B19', True,  'painted', {'note': 'Fish v2: inside of the mouth (palate, tongue, gullet rim), a dark red that still reads under dim light'}),
    'M_FishEyePale': ('D8D1B6', 'A39B82', False, 'painted', {'note': 'Fish v2: small pale eye. NOT emissive (no self-glow)'}),
}
L.MATS.update(NEW_MATS)

PITCH = 22.0                 # snout-up angle of the rest (= Idle) pose
HINGE_Y = -1.2               # fish-local jaw hinge (mouth corner) y
HINGE_W = V((0.0, -1.2, 2.0))   # where the hinge sits in the world (build space) in the Idle pose
HIDE_Y = -10.0               # Body bone height when hidden (top of the snout ~3.5 m under the surface)
HIDE_PITCH = -22.0           # Body pitch when hidden (more vertical, so the snout leads the breach)

R_LOC = Matrix.Rotation(math.radians(-PITCH), 4, 'X')
T_LOC = Matrix.Translation(HINGE_W - (R_LOC @ V((0, HINGE_Y, 0))))
M = T_LOC @ R_LOC
MINV = M.inverted()
R3 = R_LOC.to_3x3()
R3I = R3.inverted()


def W(p):
    return M @ V(p)


def smooth(x):
    x = max(0.0, min(1.0, x))
    return x * x * (3 - 2 * x)


# ===================================================================== loft (superellipse sections along y)
class Loft:
    """sections: (y, zc, w, ht, hb). ring point at angle a: x = w*spow(cos a), z = zc + (ht|hb)*spow(sin a)."""

    def __init__(self, secs, e=0.82):
        self.s = sorted(secs, key=lambda s: s[0])
        self.e = e

    def sec(self, y):
        s = self.s
        if y <= s[0][0]:
            return s[0][1:]
        if y >= s[-1][0]:
            return s[-1][1:]
        i = max(k for k in range(len(s) - 1) if s[k][0] <= y)
        u = (y - s[i][0]) / (s[i + 1][0] - s[i][0])
        p0, p1, p2, p3 = s[max(0, i - 1)], s[i], s[i + 1], s[min(len(s) - 1, i + 2)]
        out = []
        for k in range(1, 5):
            a, b, c, d = p0[k], p1[k], p2[k], p3[k]
            v = 0.5 * ((2 * b) + (-a + c) * u + (2 * a - 5 * b + 4 * c - d) * u * u + (-a + 3 * b - 3 * c + d) * u ** 3)
            out.append(v)
        out[1] = max(out[1], 0.0)
        out[2] = max(out[2], 0.0)
        out[3] = max(out[3], 0.0)
        return out

    def pt(self, y, a):
        zc, w, ht, hb = self.sec(y)
        c, s = math.cos(a), math.sin(a)
        sp = lambda v: math.copysign(abs(v) ** self.e, v)
        return V((w * sp(c), y, zc + (ht if s >= 0 else hb) * sp(s)))

    def center(self, y):
        zc, w, ht, hb = self.sec(y)
        return V((0, y, zc + (ht - hb) / 2))

    def normal(self, y, a, h=0.02):
        dy = self.pt(y + h, a) - self.pt(y - h, a)
        da = self.pt(y, a + h) - self.pt(y, a - h)
        n = da.cross(dy)
        if n.length < 1e-9:
            n = self.pt(y, a) - self.center(y)
        n.normalize()
        if n.dot(self.pt(y, a) - self.center(y)) < 0:
            n = -n
        return n

    def mesh(self, y0, y1, rows, seg, cap0=True, cap1=True):
        b = bmesh.new()
        ys = [y0 + (y1 - y0) * i / rows for i in range(rows + 1)]
        R_ = [[b.verts.new(self.pt(y, 2 * math.pi * k / seg + math.pi / seg)) for k in range(seg)] for y in ys]
        for i in range(rows):
            for k in range(seg):
                k2 = (k + 1) % seg
                f = b.faces.new((R_[i][k], R_[i][k2], R_[i + 1][k2], R_[i + 1][k]))
                c = f.calc_center_median()
                f.normal_update()
                if f.normal.dot(c - self.center(c.y)) < 0:
                    f.normal_flip()
        for cap, yy, ring, sgn in ((cap0, ys[0], R_[0], -1), (cap1, ys[-1], R_[-1], 1)):
            if not cap:
                continue
            cv = b.verts.new(self.center(yy) + V((0, sgn * 0.05, 0)))
            for k in range(seg):
                f = b.faces.new((cv, ring[k], ring[(k + 1) % seg]))
                f.normal_update()
                if f.normal.y * sgn < 0:
                    f.normal_flip()
        bmesh.ops.remove_doubles(b, verts=b.verts, dist=1e-5)
        return b


# ===================================================================== shapes (fish local)
SKULL = Loft([(0.8, 0, 2.6, 2.3, 0), (-0.4, 0, 2.95, 2.85, 0), (-1.6, 0, 3.0, 3.0, 0), (-2.8, 0, 2.88, 2.8, 0),
              (-4.0, 0, 2.55, 2.3, 0), (-5.0, 0, 2.05, 1.75, 0), (-5.8, 0, 1.45, 1.15, 0), (-6.45, 0, 0.6, 0.5, 0)])
def jaw_shift(y):
    """asymmetric underbite: the front of the lower jaw drifts to the char-left (+x)"""
    t = max(0.0, min(1.0, (-y - 3.0) / 4.4))
    return 0.42 * t * t * (3 - 2 * t)


class ShiftLoft(Loft):
    def pt(self, y, a):
        return Loft.pt(self, y, a) + V((jaw_shift(y), 0, 0))

    def center(self, y):
        return Loft.center(self, y) + V((jaw_shift(y), 0, 0))


JAW = ShiftLoft([(0.8, -0.04, 2.55, 0, 1.55), (-0.4, -0.04, 2.9, 0, 2.0), (-1.6, -0.04, 2.98, 0, 2.15), (-2.8, -0.02, 2.9, 0, 2.05),
                 (-4.0, 0.06, 2.75, 0, 1.85), (-5.2, 0.2, 2.45, 0, 1.55), (-6.3, 0.42, 2.0, 0, 1.15), (-7.1, 0.62, 1.45, 0, 0.75),
                 (-7.6, 0.75, 0.75, 0, 0.42)])
BODY = Loft([(-1.0, 0, 2.6, 2.4, 1.7), (0.5, 0.0, 2.85, 2.6, 2.0), (2.0, -0.12, 2.7, 2.5, 2.0), (3.5, -0.5, 2.45, 2.25, 1.85),
             (5.0, -1.15, 2.1, 1.95, 1.6), (6.5, -2.0, 1.7, 1.6, 1.3), (8.0, -3.0, 1.25, 1.2, 1.0), (9.5, -4.1, 0.8, 0.8, 0.7),
             (10.6, -5.0, 0.45, 0.5, 0.45)])


def zrel(p):
    return p.z - BODY.sec(p.y)[0]


def tear_field(p):
    """> 0 where the body skin is built. Tear runs diagonally: further forward on the back, further back on the belly."""
    return (2.25 - p.y - 0.5 * zrel(p)) + 0.55 * nval(p, 0.45, 3.0) + 0.22 * nval(p, 1.7, 5.0)


def paint_field(p):
    """> 0 where the dark paint covers the skin (paint runs out before the tear -> a bare paper band)."""
    return (1.05 - p.y - 0.45 * zrel(p)) + 0.45 * nval(p, 0.8, 11.0) + 0.2 * nval(p * V((1, 3, 1)), 2.2, 12.0)


# ===================================================================== skinning weights (fish local)
def w_body(p):
    y = p.y
    steps = [(0.2, 1.8, 'Head', 'Body'), (3.6, 5.6, 'Body', 'Spine1'), (6.6, 8.6, 'Spine1', 'Spine2'), (9.6, 11.0, 'Spine2', 'Tail')]
    if y < steps[0][0]:
        return {'Head': 1.0}
    for i, (a, b, b0, b1) in enumerate(steps):
        if y < a:
            return {b0: 1.0}
        if y < b:
            t = smooth((y - a) / (b - a))
            return {b0: 1 - t, b1: t}
    return {'Tail': 1.0}


# ===================================================================== builder
class FishBuild:
    def __init__(self):
        self.items = []    # (target, bm (local), mat, smooth, face_mat_local)

    def add(self, tgt, b, mat, smooth=True, fm=None):
        if b is not None:
            self.items.append((tgt, b, mat, smooth, fm))

    def finish(self, R):
        for tgt, b, mat, sm, fm in self.items:
            L.xform(b, M)
            b.normal_update()
            wfm = None
            if fm is not None:
                wfm = (lambda f: (lambda c, n: f(MINV @ c, R3I @ n)))(fm)
            wt = tgt if isinstance(tgt, str) else (lambda f: (lambda co: f(MINV @ co)))(tgt)
            R.add(wt, b, mat, smooth=sm, face_mat=wfm)


def lip_line(lf, a, y0, y1, n, lift=0.04, zoff=0.0):
    pts = []
    for i in range(n + 1):
        y = y0 + (y1 - y0) * i / n
        p = lf.pt(y, a)
        pts.append(p + lf.normal(y, a) * lift + V((0, 0, zoff)))
    return pts


def build_fish():
    R = RigChar('Fish')
    rnd = random.Random(23)
    F = FishBuild()
    # ---------------- bones (world positions = build space; every rest rotation identity)
    R.bone('Body', None, (0, 0, 0), 0.8)
    R.bone('Head', 'Body', W((0, 0.6, 0.4)), 0.6)
    R.bone('JawUpper', 'Head', W((0, HINGE_Y, 0.0)), 0.5)
    R.bone('JawLower', 'Head', W((0, HINGE_Y, -0.02)), 0.5)
    R.bone('FinL', 'Body', W((2.7, 1.0, 0.55)), 0.4)
    R.bone('FinR', 'Body', W((-2.7, 1.0, 0.55)), 0.4)
    R.bone('Spine1', 'Body', W((0, 4.6, -0.8)), 0.5)
    R.bone('Spine2', 'Spine1', W((0, 7.6, -2.6)), 0.5)
    R.bone('Tail', 'Spine2', W((0, 10.4, -4.8)), 0.5)

    # ================= upper jaw / skull (JawUpper) =================
    sk = SKULL.mesh(0.8, -6.45, 14, 24, cap0=True, cap1=True)
    jitter(sk, 0.05, 0.7, 31)

    def skull_mat(c, n):
        if n.z < -0.55 and c.z < 0.15:
            return MOUTH
        return None
    F.add('JawUpper', sk, SKIN, fm=skull_mat)
    # lip line (the grin, readable when the mouth is shut) + skull plate scratches + centre guide (pencil)
    for a in (0.02, math.pi - 0.02):
        pts = lip_line(SKULL, a, -1.0, -6.3, 12, lift=0.05, zoff=0.06)
        F.add('JawUpper', CR.line(pts, 0.06, over=0.0, seed=a, amp=0.03), INK, smooth=False)
    for k, (y0, y1, a) in enumerate(((-0.4, -3.0, 1.15), (-0.6, -2.6, 1.95), (-3.6, -5.3, 1.35), (-3.4, -5.0, 1.8), (0.4, -1.2, 0.75), (0.4, -1.2, 2.4))):
        pts = lip_line(SKULL, a, y0, y1, 6, lift=0.03)
        F.add('JawUpper', CR.line(pts, 0.03, over=0.0, seed=k + 3, amp=0.06), SCR, smooth=False)
    cl = lip_line(SKULL, math.pi / 2, 0.8, -6.4, 14, lift=0.05)
    cl = [cl[0] + (cl[0] - cl[1]).normalized() * 0.4] + cl + [cl[-1] + (cl[-1] - cl[-2]).normalized() * 1.2]
    F.add('JawUpper', CR.line(cl, 0.022, over=0.0, seed=7), PENCIL, smooth=False)

    # eyes: small, pale, inset in sockets low on the sides of the face (just above the lip line); nothing round on top.
    # A sharp, overhanging ink-edged brow ridge above each eye is what breaks the head outline (char left = +x).
    for side in (1, -1):
        A = lambda deg: math.radians(deg if side > 0 else 180 - deg)
        y = -3.9
        p, n = SKULL.pt(y, A(20)), SKULL.normal(y, A(20))
        c = p - n * 0.16
        look = (n + V((0, -1.1, -0.15))).normalized()
        u = n.cross(V((0, 1, 0))).normalized()
        v = n.cross(u).normalized()
        F.add('JawUpper', bm_sphere(c, (0.42, 0.42, 0.42), seg=12, rings=8), EYE)
        F.add('JawUpper', bm_sphere(c + look * 0.41, (0.07, 0.07, 0.07), seg=6, rings=4), INK)
        # socket: dark ink rim around the inset eye
        ring = [p + n * 0.03 + (u * math.cos(t) + v * math.sin(t)) * 0.4 * (1 + 0.1 * math.sin(3 * t + side)) for t in [2 * math.pi * i / 16 for i in range(17)]]
        F.add('JawUpper', stroke(ring, 0.06, taper=False), INK, smooth=False)
        # brow ridge: triangular (seg 3) wedge from the snout side, low, sweeping up and back into a sharp spike
        pts, rad = [], [0.08, 0.3, 0.32, 0.2, 0.012]
        for (dy, deg, out) in ((-1.1, 27, 0.08), (-0.4, 33, 0.4), (0.35, 39, 0.52), (1.15, 45, 0.5), (2.1, 50, 0.5)):
            pts.append(SKULL.pt(y + dy, A(deg)) + SKULL.normal(y + dy, A(deg)) * out)
        F.add('JawUpper', bm_tube(pts, rad, seg=3, cap=True, up=tuple(n)), SKIN, smooth=False)
        und = [q - SKULL.normal(y, A(30)) * 0.0 + V((0, 0, -rr * 0.6)) for q, rr in zip(pts, rad)]
        F.add('JawUpper', CR.line(und[:4], 0.07, over=0.12, seed=side), INK, smooth=False)
        F.add('JawUpper', CR.line([pts[1] + V((0, 0, rad[1] * 0.7)), pts[3] + V((0, 0, rad[3] * 0.7)), pts[4]], 0.04, over=0.0, seed=side + 4), INK, smooth=False)
        if side < 0:
            # unfinished: construction circle + cross guides around the char-right eye (pencil)
            g = [p + n * 0.08 + (u * math.cos(t) + v * math.sin(t)) * 0.85 for t in [2 * math.pi * i / 22 + 0.4 for i in range(24)]]
            F.add('JawUpper', stroke(g, 0.02, taper=True), PENCIL, smooth=False)
            for d in (u, v):
                F.add('JawUpper', CR.line([p + n * 0.08 - d * 1.25, p + n * 0.08 + d * 1.25], 0.016, over=0.2, seed=2), PENCIL, smooth=False)

    # upper teeth (pointing down), some only drawn
    def tooth(base, d, ln, r, side_n, tgt, drawn=False):
        d = d.normalized()
        if drawn:
            q = side_n.cross(d).normalized()
            pts = [base + q * r * 1.1, base + d * ln, base - q * r * 1.1]
            F.add(tgt, CR.line(pts, 0.035, over=0.12, seed=ln * 9), INK, smooth=False)
            return
        mid = base + d * ln * 0.5 + V((rnd.uniform(-0.04, 0.04), rnd.uniform(-0.04, 0.04), 0))
        F.add(tgt, bm_tube([base - d * 0.1, mid, base + d * ln], [r, r * 0.62, 0.012], seg=5), TOOTH, smooth=False)

    n_up = 0
    for side in (1, -1):
        for k in range(9):
            y = -1.75 - 0.5 * k - rnd.uniform(-0.08, 0.08)
            zc, w, ht, hb = SKULL.sec(y)
            base = V((side * (w - 0.22), y, -0.02))
            ln = rnd.uniform(0.45, 0.9) * (1.7 if k in (5, 6) and (k + (side > 0)) % 2 == 0 else 1.0)
            d = V((-side * rnd.uniform(0.05, 0.25), rnd.uniform(-0.2, 0.15), -1))
            drawn = (k in (2, 7) and side > 0) or (k == 4 and side < 0)
            tooth(base, d, ln, 0.13 + 0.06 * ln, V((side, 0, 0)), 'JawUpper', drawn)
            n_up += 1
    for x in (-0.35, 0.3):
        tooth(V((x, -6.2, -0.02)), V((x * 0.3, -0.25, -1)), 0.75, 0.16, V((0, -1, 0)), 'JawUpper')
    for side, y, ln in ((1, -3.1, 1.55), (-1, -4.3, 1.25), (-1, -2.5, 0.95)):
        zc, w, ht, hb = SKULL.sec(y)
        tooth(V((side * (w - 0.04), y, 0.12)), V((side * 0.32, -0.12, -1)), ln, 0.22, V((side, 0, 0)), 'JawUpper')

    # barbels (catfish whiskers) from the upper lip corners: long, sagging (in world, they hang towards the water)
    for side in (1, -1):
        p0 = SKULL.pt(-4.9, 0.12 if side > 0 else math.pi - 0.12) + V((0, 0, 0.1))
        pw = W(p0)
        pts_w = []
        for i in range(10):
            t = i / 9
            # out sideways, sag, then the tip curls back up and in (a whisker, not a leg)
            ang = 2.6 * t
            pts_w.append(pw + V((side * (0.6 + 0.9 * t) * t ** 0.7, -0.9 * t + 0.5 * t ** 3, -1.5 * t ** 1.3 + 0.55 * t ** 3)))
        pts = [MINV @ q for q in pts_w]
        F.add('JawUpper', bm_tube(pts, [0.15, 0.13, 0.11, 0.095, 0.08, 0.065, 0.05, 0.038, 0.025, 0.01], seg=5, cap=True), SKIN)
        F.add('JawUpper', stroke([q + V((0, 0, 0.1)) for q in pts[1:]], 0.025), INK, smooth=False)

    # ================= lower jaw (JawLower) =================
    jw = JAW.mesh(0.8, -7.6, 15, 24, cap0=True, cap1=True)
    jitter(jw, 0.05, 0.7, 41)

    def jaw_mat(c, n):
        if n.z > 0.55 and c.z > -0.2 and c.z < 0.6 and c.y > -6.2:
            return MOUTH
        # throat underside = bare paper (unpainted), ragged edge
        if n.z + 0.22 * nval(c, 0.9, 4) + 0.1 * nval(c, 3.0, 6) < -0.42:
            return PAPER
        return None
    F.add('JawLower', jw, SKIN, fm=jaw_mat)
    # throat pleats (ink on paper) + jaw lip line
    for k in range(9):
        a = math.radians(222 + 12 * k)
        pts = lip_line(JAW, a, -0.6 - 0.15 * abs(k - 4), -6.8 + 0.3 * abs(k - 4), 10, lift=0.04)
        F.add('JawLower', CR.line(pts, 0.035, over=0.0, seed=k + 20, amp=0.05), INK, smooth=False)
    for a in (0.0, math.pi):
        pts = lip_line(JAW, a, -0.9, -7.5, 13, lift=0.05, zoff=-0.05)
        F.add('JawLower', CR.line(pts, 0.055, over=0.0, seed=a + 30, amp=0.03), INK, smooth=False)
    # tongue
    tg = bm_sphere((0, -2.7, -0.05), (1.25, 2.2, 0.38), seg=12, rings=6)
    for v in tg.verts:
        v.co.z = max(v.co.z, -0.04)
    F.add('JawLower', tg, MOUTH)
    # lower teeth (pointing up) + two jutting fangs outside the upper lip (underbite)
    for side in (1, -1):
        for k in range(8):
            y = -1.9 - 0.52 * k + rnd.uniform(-0.08, 0.08)
            zc, w, ht, hb = JAW.sec(y)
            base = V((side * (w - 0.25) + jaw_shift(y), y, zc + 0.02))
            ln = rnd.uniform(0.4, 0.75) * (1.5 if k >= 6 else 1.0)
            d = V((-side * rnd.uniform(0.0, 0.2), rnd.uniform(-0.15, 0.15), 1))
            drawn = (k == 3 and side > 0) or (k in (1, 6) and side < 0)
            tooth(base, d, ln, 0.12 + 0.06 * ln, V((side, 0, 0)), 'JawLower', drawn)
        # jutting underbite fangs (uneven: the char-left one is bigger)
        base = V((side * (0.85 if side > 0 else 0.7) + jaw_shift(-7.1), -7.05, 0.62))
        tooth(base, V((side * 0.3, -0.45, 1)), 1.45 if side > 0 else 1.0, 0.3 if side > 0 else 0.24, V((side, 0, 0)), 'JawLower')

    # ================= gullet (Head): black hole framed by a fleshy ring
    gc = V((0, -0.85, 0.15))
    disc = bmesh.new()
    cv = disc.verts.new(gc + V((0, 0.35, 0)))
    ring = [disc.verts.new(gc + V((math.cos(t) * 1.75, 0, math.sin(t) * 1.35))) for t in [2 * math.pi * i / 16 for i in range(16)]]
    for i in range(16):
        f = disc.faces.new((cv, ring[i], ring[(i + 1) % 16]))
        f.normal_update()
        if f.normal.y > 0:
            f.normal_flip()
    F.add('Head', disc, GUL, smooth=False)
    lip = [gc + V((math.cos(t) * 1.8, -0.05, math.sin(t) * 1.4)) for t in [2 * math.pi * i / 16 for i in range(17)]]
    F.add('Head', bm_tube(lip, 0.22, seg=6, cap=False), MOUTH)

    # ================= body (Head -> Body -> Spine1 -> Spine2 -> Tail), torn behind the head
    bd = BODY.mesh(-1.0, 10.6, 22, 22, cap0=False, cap1=True)
    jitter(bd, 0.06, 0.6, 51)
    cut = CR.cut_field(bd, tear_field, zig=0.09, seed=4)
    built = cut.built

    def body_mat(c, n):
        return SKIN if paint_field(c) > 0 and n.z > -0.55 else PAPER
    back, rim = CR.shell_parts(built, thick=0.14, near=None, torn=None)
    F.add(w_body, built, SKIN, fm=body_mat)
    F.add(w_body, back, 'M_PaperBack')
    F.add(w_body, rim, 'M_TornEdge', smooth=False)
    F.add(w_body, CR.torn_ink(cut, r=0.05, seed=2, lift=0.03), INK, smooth=False)
    F.add(w_body, CR.torn_hatch(cut, spacing=0.32, length=(0.5, 1.4), slant=26, r=0.022, density=0.8, seed=3, lift=0.04), PENCIL, smooth=False)
    # gill slits (ink)
    for side in (1, -1):
        for k, y in enumerate((0.0, 0.45, 0.9)):
            pts = []
            for i in range(7):
                t = -0.7 + 1.4 * i / 6
                a = t if side > 0 else math.pi - t
                yy = y + 0.25 * (1 - t * t)
                pts.append(BODY.pt(yy, a) + BODY.normal(yy, a) * 0.05)
            F.add(w_body, CR.line(pts, 0.06 - 0.008 * k, over=0.0, seed=k + side), INK, smooth=False)
    # scratched scale arcs on the painted skin (light lines on the dark paint)
    for yi in range(8):
        y0 = -0.2 + 0.45 * yi
        for ai in range(16):
            a0 = math.radians(-58 + 19.5 * ai + (9.7 if yi % 2 else 0))
            pc = BODY.pt(y0, a0)
            if tear_field(pc) < 0.35 or paint_field(pc) < 0.25 or BODY.normal(y0, a0).z < -0.3:
                continue
            pts = []
            for i in range(5):
                t = -math.pi / 2 + math.pi * i / 4
                yy, aa = y0 + 0.28 * math.cos(t), a0 + 0.14 * math.sin(t)
                pts.append(BODY.pt(yy, aa) + BODY.normal(yy, aa) * 0.035)
            F.add(w_body, stroke(pts, 0.024), SCR, smooth=False)
    # pencil construction rings + contour lines where the body is not built
    for k, y in enumerate((2.3, 3.5, 4.8, 6.1, 7.5, 8.9)):
        pts = [BODY.pt(y, 2 * math.pi * i / 30) * 1.0 + BODY.normal(y, 2 * math.pi * i / 30) * 0.03 for i in range(33)]
        F.add(w_body, CR.clipped_lines(pts, lambda p: tear_field(p) < 0.05, r=0.025, over=0.15, seed=k, amp=0.03), PENCIL, smooth=False)
    for k, (a, mat, r) in enumerate(((math.pi / 2, INK, 0.05), (0.0, PENCIL, 0.025), (math.pi, PENCIL, 0.025), (math.pi * 1.5, PENCIL, 0.025),
                                     (math.pi * 0.25, PENCIL, 0.02), (math.pi * 0.75, PENCIL, 0.02))):
        pts = [BODY.pt(y, a) + BODY.normal(y, a) * 0.03 for y in [0.0 + 10.6 * i / 26 for i in range(27)]]
        F.add(w_body, CR.clipped_lines(pts, lambda p: tear_field(p) < 0.05, r=r, over=0.3, seed=k + 10, amp=0.04), mat, smooth=False)
    # pencil spine axis running out of the back
    F.add(w_body, CR.line([BODY.center(y) for y in [1.5 + 1.0 * i for i in range(11)]], 0.018, over=0.6, seed=1), PENCIL, smooth=False)

    # dorsal crest: first spines built (with a torn membrane), the rest only pencil
    ys = [0.15, 0.75, 1.35, 2.0, 2.75, 3.5, 4.3, 5.1]
    tips = []
    for i, y in enumerate(ys):
        base = BODY.pt(y, math.pi / 2) - V((0, 0, 0.12))
        ln = [1.9, 2.4, 2.0, 1.8, 1.6, 1.4, 1.2, 1.0][i]
        d = V((rnd.uniform(-0.08, 0.08), 0.62, 1)).normalized()
        tip = base + d * ln
        tips.append((base, tip))
        if i < 3:
            F.add(w_body, bm_tube([base, base + d * ln * 0.55, tip], [0.16, 0.1, 0.012], seg=5), SKIN, smooth=False)
            F.add(w_body, stroke([base + d * 0.3 + V((0.12, 0, 0)), tip + V((0.05, 0, -0.05))], 0.03), INK, smooth=False)
        else:
            F.add(w_body, CR.line([base - d * 0.2, tip], 0.026, over=0.25, seed=i), PENCIL, smooth=False)
    mem = bmesh.new()
    for i in range(2):
        (b0, t0), (b1, t1) = tips[i], tips[i + 1]
        m0, m1 = b0.lerp(t0, 0.8 - 0.1 * i), b1.lerp(t1, 0.62 if i == 1 else 0.8)
        for off in (0.025, -0.025):
            vs = [mem.verts.new(q + V((off, 0, 0))) for q in (b0, m0, m1, b1)]
            f = mem.faces.new(vs)
            f.normal_update()
            if f.normal.x * off < 0:
                f.normal_flip()
    F.add(w_body, mem, SKIN, smooth=False)
    F.add(w_body, CR.line([tips[1][0].lerp(tips[1][1], 0.8), tips[2][0].lerp(tips[2][1], 0.62)], 0.035, seed=4), INK, smooth=False)
    F.add(w_body, CR.line([q[1] for q in tips[2:]], 0.02, over=0.3, seed=6, amp=0.08), PENCIL, smooth=False)

    # pectoral fins: char-left built, char-right only drawn
    for side, nm in ((1, 'FinL'), (-1, 'FinR')):
        root = V((side * 2.6, 1.0, 0.55))
        pts = [root, root + V((side * 1.0, 0.85, -0.2)), root + V((side * 2.0, 1.9, -0.45)), root + V((side * 2.45, 2.85, -0.6))]
        wd = [0.5, 0.95, 0.8, 0.12]
        fr = L._frames(pts, (side * 0.3, 0, 1))
        edge_a = [p + fr[i][2] * wd[i] for i, p in enumerate(pts)]
        edge_b = [p - fr[i][2] * wd[i] for i, p in enumerate(pts)]
        if side > 0:
            fb = bm_blade(pts, wd, thick=0.1, up=(side * 0.3, 0, 1))
            jitter(fb, 0.06, 1.5, 7)
            F.add(nm, fb, SKIN, smooth=False)
            for k in range(4):
                t = 0.25 + 0.25 * k
                e = edge_a[3].lerp(edge_b[3], t) if k < 3 else edge_b[2]
                F.add(nm, stroke([root + V((0, 0, 0.1)), (root.lerp(e, 0.5)) + V((0, 0, 0.14)), e + V((0, 0, 0.1))], 0.03), SCR, smooth=False)
        else:
            outline = edge_a + [pts[-1] + (pts[-1] - pts[-2]).normalized() * 0.15] + list(reversed(edge_b))
            F.add(nm, CR.line(outline, 0.026, over=0.25, seed=9, amp=0.05), PENCIL, smooth=False)
            for k in range(4):
                e = edge_a[3].lerp(edge_b[3], 0.2 + 0.25 * k)
                F.add(nm, CR.line([root, e], 0.03, over=0.0, seed=k), INK, smooth=False)

    # tail: pencil only (under water most of the time)
    tl = [V((0, 10.3, -4.5)), V((0, 11.6, -3.9)), V((0, 13.0, -3.6)), V((0, 12.6, -5.4)), V((0, 13.4, -7.4)), V((0, 11.6, -6.3)), V((0, 10.3, -5.4))]
    F.add('Tail', CR.line(tl, 0.03, over=0.3, seed=2, amp=0.1), PENCIL, smooth=False)
    for k in range(3):
        F.add('Tail', CR.line([V((0, 10.5, -5.0)), tl[2 + k]], 0.02, over=0.1, seed=k), PENCIL, smooth=False)

    F.finish(R)
    R.meta['height'] = 6.5
    return R


# ===================================================================== clips
def c(**kw):
    """channel dict from keyword names like Body_x=.., Body_py=.."""
    return {k.replace('_', '.'): v for k, v in kw.items()}


def keys(base, ks, loop=False):
    return Keys(base, [(t, c(**d), o) for t, d, o in ks], loop=loop)


HID = c(Body_py=HIDE_Y, Body_x=HIDE_PITCH)


def sn(t, period, amp, ph=0.0):
    return amp * math.sin(2 * math.pi * t / period + ph)


def clip_hidden(t):
    ch = dict(HID)
    ch['Body.y'] = sn(t, 3.0, 3.0)
    ch['Spine1.y'] = sn(t, 3.0, 5.0, 0.0)
    ch['Spine2.y'] = sn(t, 3.0, 7.0, 0.0)
    ch['Tail.y'] = sn(t, 3.0, 12.0, 0.0)
    ch['Body.py'] = HIDE_Y + sn(t, 3.0, 0.15)
    return ch


K_RISE = keys(HID, [(0.0, {}, ''),
                    (0.35, dict(Body_py=-9.4, Body_x=-24.0, Tail_y=-14.0), ''),
                    (1.05, dict(Body_py=-2.5, Body_x=-27.0, JawLower_x=8.0, FinL_z=20.0, FinR_z=-20.0, Tail_y=12.0), ''),
                    (1.45, dict(Body_py=1.25, Body_x=-15.0, JawLower_x=20.0, JawUpper_x=-6.0, Head_x=-6.0, FinL_z=28.0, FinR_z=-28.0, Tail_y=-8.0), ''),
                    (1.95, dict(Body_py=-0.45, Body_x=5.0, JawLower_x=6.0, JawUpper_x=0.0, Head_x=3.0, FinL_z=-6.0, FinR_z=6.0, Tail_y=4.0), ''),
                    (2.5, dict(Body_py=0.0, Body_x=0.0, JawLower_x=0.0, Head_x=0.0, FinL_z=0.0, FinR_z=0.0, Tail_y=0.0), 'hold')])


def clip_rise(t):
    return K_RISE(t)


def idle_layer(t, k=1.0):
    ch = {}
    ch['Body.py'] = sn(t, 4.0, 0.16) * k
    ch['Body.x'] = sn(t, 4.0, 1.4, 0.0) * k
    ch['Body.z'] = sn(t, 8.0, 1.2) * k
    ch['Head.x'] = sn(t, 4.0, -1.2) * k
    ch['JawLower.x'] = (2.5 - 2.5 * math.cos(2 * math.pi * t / 4.0)) * k
    ch['JawUpper.x'] = -(0.8 - 0.8 * math.cos(2 * math.pi * t / 4.0)) * k
    ch['FinL.z'] = sn(t, 2.0, 11.0) * k
    ch['FinR.z'] = -sn(t, 2.0, 11.0, 0.5) * k
    ch['FinL.y'] = sn(t, 2.0, 6.0, 1.2) * k
    ch['FinR.y'] = -sn(t, 2.0, 6.0, 1.7) * k
    ch['Spine1.y'] = sn(t, 4.0, 3.0) * k
    ch['Spine2.y'] = sn(t, 4.0, 5.0, -0.6) * k
    ch['Tail.y'] = sn(t, 4.0, 9.0, -1.2) * k
    return ch


def clip_idle(t):
    return idle_layer(t)


def env(t, T, a=0.25):
    """0 at both ends of a clip, 1 in the middle (lets the breathing layer run inside one-shot clips)."""
    return smooth(t / a) * smooth((T - t) / a)


K_OPEN = keys({}, [(0.0, {}, ''),
                   (0.3, dict(Body_x=2.0, JawLower_x=-2.0, JawUpper_x=1.0, Head_x=2.0), ''),
                   (0.62, dict(Body_x=-7.0, Head_x=-5.0, JawLower_x=30.0, JawUpper_x=-18.0, FinL_z=16.0, FinR_z=-16.0), ''),
                   (0.95, dict(Body_x=-5.0, Head_x=-4.0, JawLower_x=42.0, JawUpper_x=-25.0, FinL_z=20.0, FinR_z=-20.0), ''),
                   (1.5, dict(Body_x=-4.0, Head_x=-4.0, JawLower_x=40.0, JawUpper_x=-24.0, FinL_z=18.0, FinR_z=-18.0), 'hold')])
OPEN_END = K_OPEN(1.5)


def clip_open(t):
    ch = K_OPEN(t)
    if t > 0.95:   # a slight tremble while holding the jaw wide
        k = smooth((t - 0.95) / 0.2) * smooth((1.5 - t) / 0.25)
        ch['JawLower.x'] = ch.get('JawLower.x', 0) + 1.2 * math.sin(t * 40) * k
    return ch


K_SWAL = keys(OPEN_END, [(0.0, {}, ''),
                         (0.17, dict(JawLower_x=-3.0, JawUpper_x=1.5, Head_x=-8.0, Body_x=-6.0), 'snap'),
                         (0.45, dict(JawLower_x=0.0, JawUpper_x=0.0, Head_x=-15.0, Body_x=-9.0, Body_py=0.45, JawLower_sx=1.1, JawLower_sy=1.22,
                                     Spine1_x=-4.0, FinL_z=5.0, FinR_z=-5.0), ''),
                         (0.85, dict(Head_x=7.0, Body_x=3.5, Body_py=-0.55, JawLower_sx=1.0, JawLower_sy=1.0, Spine1_x=5.0, FinL_z=-8.0, FinR_z=8.0), ''),
                         (1.08, dict(Head_x=2.0, Body_x=0.5, Body_py=-0.15, JawLower_sx=1.04, JawLower_sy=1.09, Spine1_x=1.0), ''),
                         (1.5, dict(Head_x=0.0, Body_x=0.0, Body_py=0.0, JawLower_sx=1.0, JawLower_sy=1.0, Spine1_x=0.0, FinL_z=0.0, FinR_z=0.0), 'hold')])


def clip_swallow(t):
    return K_SWAL(t)


K_SPIT = keys({}, [(0.0, {}, ''),
                   (0.33, dict(Body_x=-11.0, Head_x=-9.0, Body_py=0.25, JawLower_x=6.0, JawLower_sx=1.08, JawLower_sy=1.15, FinL_z=14.0, FinR_z=-14.0), ''),
                   (0.5, dict(Body_x=6.0, Head_x=3.0, Body_py=-0.2, JawLower_x=42.0, JawUpper_x=-26.0, JawLower_sx=0.96, JawLower_sy=0.92, FinL_z=-10.0, FinR_z=10.0), 'snap'),
                   (0.75, dict(Body_x=4.0, Head_x=2.0, JawLower_x=32.0, JawUpper_x=-18.0, JawLower_sx=1.0, JawLower_sy=1.0), ''),
                   (1.02, dict(Body_x=-1.5, Head_x=-1.0, Body_py=0.05, JawLower_x=2.0, JawUpper_x=0.0, FinL_z=2.0, FinR_z=-2.0), ''),
                   (1.2, dict(Body_x=0.0, Head_x=0.0, Body_py=0.0, JawLower_x=0.0, FinL_z=0.0, FinR_z=0.0), 'hold')])


def clip_spit(t):
    return K_SPIT(t)


K_SINK = keys({}, [(0.0, {}, ''),
                   (0.45, dict(Body_py=0.35, Body_x=-9.0, Head_x=-4.0, JawLower_x=5.0, FinL_z=15.0, FinR_z=-15.0), ''),
                   (0.95, dict(Body_py=-2.2, Body_x=-16.0, Head_x=-2.0, JawLower_x=0.0, FinL_z=-10.0, FinR_z=10.0, Tail_y=10.0), ''),
                   (1.5, dict(Body_py=-7.2, Body_x=-21.0, Head_x=0.0, FinL_z=4.0, FinR_z=-4.0, Tail_y=-8.0), ''),
                   (2.0, dict(Body_py=HIDE_Y, Body_x=HIDE_PITCH, FinL_z=0.0, FinR_z=0.0, Tail_y=0.0), 'hold')])


def clip_sink(t):
    return K_SINK(t)


# name, frames (30 fps), fn, loop
CLIPS = [('Hidden', 90, clip_hidden, True), ('Rise', 75, clip_rise, False), ('Idle', 120, clip_idle, True),
         ('OpenMouth', 45, clip_open, False), ('Swallow', 45, clip_swallow, False), ('Spit', 36, clip_spit, False),
         ('Sink', 60, clip_sink, False)]


def bake(R, report):
    import bpy
    from mathutils import Quaternion
    ob = R.arm
    ob.animation_data_create()
    pbs = ob.pose.bones
    for pb in pbs:
        pb.rotation_mode = 'QUATERNION'
    for name, frames, fn, loop in CLIPS:
        act = bpy.data.actions.new(name)
        act.use_fake_user = True
        ob.animation_data.action = act
        prevq = {}
        ys = []
        for f in range(frames + 1):
            t = f / FPS
            if loop and f == frames:
                t = 0.0
            ch = fn(t)
            for b in R.order:
                pb = pbs[b]
                q = E(ch.get(b + '.x', 0.0), ch.get(b + '.y', 0.0), ch.get(b + '.z', 0.0))
                if b in prevq and prevq[b].dot(q) < 0:
                    q = -q
                prevq[b] = q
                pb.rotation_quaternion = q
                pb.keyframe_insert('rotation_quaternion', frame=f, group=b)
            py = ch.get('Body.py', 0.0)
            ys.append(py)
            pbs['Body'].location = (0.0, py, 0.0)
            pbs['Body'].keyframe_insert('location', frame=f, group='Body')
            pbs['JawLower'].scale = (ch.get('JawLower.sx', 1.0), ch.get('JawLower.sy', 1.0), 1.0)
            pbs['JawLower'].keyframe_insert('scale', frame=f, group='JawLower')
        report.append(dict(clip=name, frames=frames, seconds=round(frames / FPS, 3), loop=loop,
                           body_y=[round(min(ys), 2), round(max(ys), 2)], body_y_start=round(ys[0], 2), body_y_end=round(ys[-1], 2)))
        act.frame_range = (0, frames)
        ob.animation_data.action = None
        tr = ob.animation_data.nla_tracks.new()
        tr.name = name
        st = tr.strips.new(name, 0, act)
        st.name = name
        st.frame_end = frames
    for pb in pbs:
        pb.rotation_quaternion = Quaternion()
        pb.location = (0, 0, 0)
        pb.scale = (1, 1, 1)
