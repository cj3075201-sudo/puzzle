# -*- coding: utf-8 -*-
"""Round-4 characters: redesigned for the close game camera (pitch 25, 10 m, fov 32), skinned to an armature,
with baked clips. Build space: Z up, front -Y, character's left +X, root = between the feet."""
import math, random
from mathutils import Vector
from mathutils.bvhtree import BVHTree
import ouat_lib as L
from ouat_lib import (bm_sphere, bm_tube, bm_blade, bm_box, bm_lathe, stroke, wobble_line,
                      rot, move, deform, jitter, subdivide, nval, copy_bm, mirror_x)
import ouat_creatures as CR
from ouat_creatures import paint_above, paint_below, capsule, ball, mitten, ink_hand, faceted_head
from ouat_rig import RigChar
import ouat_anim as A

V = Vector
WOOD, JOINT, RED, BLUE, INK = 'M_PuppetWood', 'M_PuppetJoint', 'M_PaintRed', 'M_PaintBlue', 'M_Ink'

# new material slots (same fields as ouat_lib.MATS; merged into art_materials.json by build_chars_v2.py)
NEW_MATS = {
    'M_BluebirdDeep': ('1E3A96', '13265F', True, 'painted', {'note': 'hero: wing primaries, tail, cap feather shade'}),
    'M_PaintWhite':   ('F4EFE2', 'C8C0AC', True, 'painted', {'note': 'brushed-on white paint (Kinopio collar)'}),
    'M_PaintNavy':    ('2A3A78', '1C2752', True, 'painted', {'note': 'brushed-on navy paint (suspenders, trims)'}),
    'M_PencilBody':   ('5A5551', '5A5551', False, 'sketch', {'alpha': 0.55, 'note': 'graphite construction lines where a creature body is not finished yet (unlit, transparent, double-sided, no shadow)'}),
    'M_PaintRedBrush':  ('C23A2E', '8E2A22', False, 'painted', {'note': 'dry-brush streaks running off a red paint edge (flush strokes, NO outline)'}),
    'M_PaintBlueBrush': ('5B86C9', '3D6198', False, 'painted', {'note': 'dry-brush streaks running off a blue paint edge (flush strokes, NO outline)'}),
}
BRUSH = {RED: 'M_PaintRedBrush', BLUE: 'M_PaintBlueBrush'}
L.MATS.update(NEW_MATS)


class To:
    """Adapter so the old Part-style helpers (streaks, ink_hand) can add pieces to a bone."""
    def __init__(self, rig, target, obj='Geo'):
        self.rig, self.target, self.obj = rig, target, obj

    def add(self, b, mat, smooth=True, face_mat=None):
        self.rig.add(self.target, b, mat, smooth, face_mat, self.obj)
        return self


def blend_w(axis_fn, b0, b1, x0, x1):
    """Weight fn: bone b0 below x0, b1 above x1, smooth between (axis_fn(co) gives the coordinate)."""
    def fn(co):
        t = A.smooth((axis_fn(co) - x0) / (x1 - x0))
        return {b0: 1 - t, b1: t}
    return fn


def oriented_eye(c, nrm, size):
    e = bm_sphere((0, 0, 0), size, seg=10, rings=6)
    q = nrm.to_track_quat('-Y', 'Z')
    L.xform(e, q.to_matrix().to_4x4())
    move(e, c)
    return e


def humanoid_contacts(rig, sole_y, toe, heel, knee_r, hand_r, head_c, head_r, body_c, body_r, hips_r):
    """Ground-contact probes (rig space offsets) for the auto-ground channel."""
    c = {}
    for s in 'LR':
        f = rig.b('Foot' + s)
        c['toe' + s] = (f, V((0, -sole_y, toe)), 0.0)
        c['heel' + s] = (f, V((0, -sole_y, -heel)), 0.0)
        c['knee' + s] = (rig.b('Shin' + s), V((0, 0, 0)), knee_r)
        c['hand' + s] = (rig.b('Hand' + s), V((0, -hand_r, 0)), hand_r)
    c['head'] = ('Head', V(head_c), head_r)
    c['body'] = ('Body', V(body_c), body_r)
    c['hips'] = ('Hips', V((0, 0, 0)), hips_r)
    rig.contacts = {k: (b, o, r) for k, (b, o, r) in c.items()}


# patch Poser.lowest to understand (bone, offset, radius) contacts
import ouat_rig as _R


def _lowest(self, W):
    ys = []
    for nm, val in self.rig.contacts.items():
        bn, off = val[0], val[1]
        rad = val[2] if len(val) > 2 else 0.0
        if bn in W:
            p, r = W[bn]
            ys.append((p + r @ off).y - rad)
    return min(ys) if ys else 0.0


_R.Poser.lowest = _lowest


# =====================================================================================  HERO
def build_hero():
    R = RigChar('Hero_Bluebird')
    BLUE_, BELLY, BEAK, DEEP, NAVY = 'M_Bluebird', 'M_BluebirdBelly', 'M_Beak', 'M_BluebirdDeep', 'M_CapNavy'
    # ---------------- skeleton
    R.bone('Hips', None, (0, 0, 0.44))
    R.bone('Body', 'Hips', (0, 0, 0.50))
    R.bone('Head', 'Body', (0, -0.005, 0.71))
    R.bone('Cape', 'Body', (0, 0.06, 0.73))
    R.bone('Tail', 'Hips', (0, 0.15, 0.40))
    for s, x in (('L', 1), ('R', -1)):
        R.bone('Leg' + s, 'Hips', (0.085 * x, 0, 0.42))
        R.bone('Shin' + s, 'Leg' + s, (0.09 * x, 0, 0.25))
        R.bone('Foot' + s, 'Shin' + s, (0.09 * x, 0, 0.075))
        R.bone('Wing' + s, 'Body', (0.185 * x, 0, 0.655))
        R.bone('WingTip' + s, 'Wing' + s, (0.205 * x, 0, 0.53))
        R.bone('Hand' + s, 'WingTip' + s, (0.215 * x, 0, 0.42))
    R.alias = {'ArmL': 'WingL', 'ArmR': 'WingR', 'ForeArmL': 'WingTipL', 'ForeArmR': 'WingTipR'}
    hipsw = blend_w(lambda c: c.z, 'Hips', 'Body', 0.47, 0.58)

    # ---------------- body: plump egg, pale belly
    bc = V((0, 0, 0.545))
    b = bm_sphere(bc, (0.195, 0.18, 0.205), seg=16, rings=10)

    def pear(co):
        t = (co.z - 0.34) / 0.41
        k = 1.0 + 0.12 * (1 - t) - 0.08 * t
        co.x *= k
        co.y *= k
        return co
    deform(b, pear)
    bb = BVHTree.FromBMesh(b)
    R.add(hipsw, b, BLUE_)
    bib = bm_sphere(bc + V((0, -0.07, -0.02)), (0.15, 0.135, 0.17), seg=14, rings=8)
    R.add(hipsw, bib, BELLY)
    # strap hugging the body: right shoulder -> left hip
    strap = []
    cen = V((0, 0, 0.55))
    nrm = V((0.6, 0.0, 1.0)).normalized()
    ax1 = V((0, 1, 0))
    ax2 = nrm.cross(ax1).normalized()
    bib_bvh = BVHTree.FromBMesh(bib)
    for i in range(33):
        a = 2 * math.pi * i / 32
        d = (ax1 * math.cos(a) + ax2 * math.sin(a)).normalized()
        h1 = bb.ray_cast(cen + d * 0.6, -d)
        h2 = bib_bvh.ray_cast(cen + d * 0.6, -d)
        hs = [h for h in (h1, h2) if h[0] is not None]
        if not hs:
            continue
        h = max(hs, key=lambda h: (h[0] - cen).length)
        strap.append(h[0] + h[1] * 0.011)
    R.add(hipsw, bm_tube(strap, 0.017, seg=4, cap=False, flat=0.35, up=(0, 0, 1)), 'M_Leather', smooth=False)
    # satchel on the left hip
    bag_c = V((0.2, -0.07, 0.405))
    for sz, off, m in (((0.065, 0.15, 0.13), (0, 0, 0), 'M_Leather'), ((0.072, 0.155, 0.065), (0.004, 0, 0.045), 'M_Leather'),
                       ((0.018, 0.045, 0.036), (0.04, -0.005, 0.03), 'M_Brass')):
        bx = bm_box((0, 0, 0), sz)
        bx = L.bevel(bx, min(sz) * 0.3, 2, 40)
        rot(bx, 'Z', 16)
        move(bx, bag_c + V(off))
        R.add('Hips', bx, m, smooth=False)

    # ---------------- tail: three long feathers, darker, under the cape
    for a, ln, w in ((-22, 0.22, 0.045), (0, 0.27, 0.052), (22, 0.22, 0.045)):
        d = V((math.sin(math.radians(a)), math.cos(math.radians(a)), 0))
        base = V((0, 0.15, 0.4))
        pts = [base, base + d * ln * 0.4 + V((0, 0, -0.05)), base + d * ln + V((0, 0, -0.1))]
        R.add('Tail', bm_blade(pts, [0.026, w, 0.01], thick=0.016, up=(0, 0, 1)), DEEP)

    # ---------------- legs: blue thigh puff, thin black bird shin, brown boots
    for s, x in (('L', 1), ('R', -1)):
        xx = 0.088 * x
        th = bm_sphere((xx, 0.0, 0.365), (0.078, 0.078, 0.085), seg=12, rings=8)
        R.add('Leg' + s, th, BLUE_)
        R.add('Shin' + s, bm_tube([(xx, 0, 0.28), (xx, 0, 0.2), (xx, 0, 0.12)], [0.022, 0.02, 0.019], seg=7), BEAK)
        cuff = bm_lathe([(0.04, 0.085), (0.045, 0.1), (0.048, 0.145), (0.042, 0.152)], seg=10, center=(xx, 0.002, 0))
        R.add('Shin' + s, cuff, 'M_Leather', smooth=False)
        foot = bm_box((0, 0, 0), (0.088, 0.175, 0.07))
        foot = L.bevel(foot, 0.028, 2, 40)

        def toe_round(co):
            t = max(0.0, (-co.y - 0.03) / 0.06)
            co.z -= 0.012 * t * (co.z > 0)
            return co
        deform(foot, toe_round)
        move(foot, (xx, -0.04, 0.042))
        R.add('Foot' + s, foot, 'M_Leather', smooth=True)
        sole = bm_box((xx, -0.04, 0.008), (0.092, 0.18, 0.016))
        sole = L.bevel(sole, 0.006, 1, 40)
        R.add('Foot' + s, sole, BEAK, smooth=False)
        bk = bm_box((xx + 0.045 * x, -0.03, 0.06), (0.008, 0.03, 0.026))
        R.add('Foot' + s, bk, 'M_Brass', smooth=False)

    # ---------------- wings as arms
    for s, x in (('L', 1), ('R', -1)):
        sh = V((0.185 * x, 0, 0.655))
        el = V((0.205 * x, 0, 0.53))
        wr = V((0.215 * x, 0, 0.42))
        up = bm_tube([sh + V((-0.03 * x, 0, 0.03)), sh, sh.lerp(el, 0.6), el], [0.035, 0.06, 0.055, 0.046], seg=9, flat=0.6, up=(x, 0, 0))
        R.add('Wing' + s, up, BLUE_)
        lo = bm_tube([el + V((0, 0, 0.02)), el.lerp(wr, 0.5), wr], [0.045, 0.042, 0.036], seg=8, flat=0.6, up=(x, 0, 0))
        R.add('WingTip' + s, lo, BLUE_)
        for i, a in enumerate((-30, 0, 30)):
            d = V((0.1 * x, math.sin(math.radians(a)) * 0.7, -1.0)).normalized()
            ln = 0.085 if a else 0.1
            p0 = wr + V((0, math.sin(math.radians(a)) * 0.02, 0.02))
            pts = [p0, p0 + d * ln * 0.45, p0 + d * ln]
            R.add('Hand' + s, bm_blade(pts, [0.02, 0.024, 0.005], thick=0.016, up=(x, 0, 0)), DEEP)

    # ---------------- head (bigger, pale heart-shaped face so the eyes read in dim light)
    hc = V((0, -0.02, 0.855))
    hr = (0.222, 0.205, 0.196)
    h = bm_sphere(hc, hr, seg=18, rings=12)
    R.add('Head', h, BLUE_)
    face = bm_sphere(hc + V((0, -0.062, -0.022)), (0.178, 0.16, 0.158), seg=18, rings=10)

    def heart(co):
        # notch the top centre (heart shape) and pull the bottom into a soft point under the beak
        dx = co.x - hc.x
        top = co.z - (hc.z + 0.04)
        if top > 0:
            co.z -= top * 0.9 * math.exp(-(dx / 0.045) ** 2)
        return co
    deform(face, heart)
    fb_ = BVHTree.FromBMesh(face)
    R.add('Head', face, BELLY)
    for x in (1, -1):
        d = V((0.36 * x, -1.0, 0.1)).normalized()
        hit = fb_.ray_cast(hc + d * 0.6, -d)
        c, n = hit[0], hit[1]
        R.add('Head', oriented_eye(c - n * 0.006, n, (0.047, 0.02, 0.062)), INK)
        tang = n.cross(V((0, 0, 1))).normalized()
        sp = bm_sphere((0, 0, 0), (0.015, 0.007, 0.017), seg=6, rings=4)
        move(sp, c + n * 0.012 + V((0, 0, 0.022)) - tang * 0.012 * x)
        R.add('Head', sp, 'M_EyeShine')
        sp2 = bm_sphere((0, 0, 0), (0.006, 0.004, 0.006), seg=5, rings=3)
        move(sp2, c + n * 0.012 + V((0, 0, -0.024)) + tang * 0.014 * x)
        R.add('Head', sp2, 'M_EyeShine')
        # short determined brow feather above each eye (cobalt deep), slightly angled
        b0 = c + V((-0.035 * x, -0.004, 0.058))
        b1 = c + V((0.03 * x, 0.0, 0.07))
        R.add('Head', bm_blade([b0, b0.lerp(b1, 0.5) + V((0, -0.004, 0.006)), b1], [0.007, 0.011, 0.004], thick=0.008, up=tuple(n)), DEEP, smooth=False)
    hb = BVHTree.FromBMesh(h)
    # beak
    root = hc + V((0, -0.205, -0.03))
    R.add('Head', bm_tube([root + V((0, 0.03, 0.006)), root + V((0, -0.035, -0.002)), root + V((0, -0.085, -0.022))],
                         [0.04, 0.028, 0.003], seg=9, flat=0.7, up=(0, 0, 1)), BEAK)
    R.add('Head', bm_tube([root + V((0, 0.02, -0.022)), root + V((0, -0.05, -0.03))], [0.026, 0.003], seg=7, flat=0.6, up=(0, 0, 1)), BEAK)
    # crest tuft at the back of the head
    top = hc + V((0, 0.12, 0.13))
    for sx, ln in ((-0.028, 0.075), (0.0, 0.1), (0.028, 0.075)):
        p0 = top + V((sx, 0, 0))
        pts = [p0, p0 + V((sx * 0.5, ln * 0.6, ln * 0.25)), p0 + V((sx, ln, ln * 0.15))]
        R.add('Head', bm_blade(pts, [0.02, 0.024, 0.004], thick=0.016, up=(1, 0, 0)), DEEP)
    # hunting cap: soft crown tilted back, short stiff brim, brass button, blue feather
    capc = hc + V((0.012, 0.018, 0.13))
    tilt = -10
    prof = [(0.0, 0.085), (0.08, 0.083), (0.15, 0.072), (0.19, 0.05), (0.198, 0.028), (0.185, 0.008), (0.172, 0.0)]
    crown = bm_lathe(prof, seg=20, center=capc, sx=1.0, sy=1.05, cap_bottom=True)
    deform(crown, lambda co: co + V((0, -0.02 * max(0, co.z - capc.z - 0.05) / 0.035, 0)))
    rot(crown, 'X', tilt, capc)
    R.add('Head', crown, NAVY)
    band = bm_tube([capc + V((math.cos(2 * math.pi * i / 20) * 0.176, math.sin(2 * math.pi * i / 20) * 0.184, 0.004)) for i in range(21)],
                   0.012, seg=5, cap=False)
    rot(band, 'X', tilt, capc)
    R.add('Head', band, NAVY, smooth=False)
    brim = []
    for i in range(9):
        aa = math.radians(-145 + 110 * i / 8)
        brim.append(capc + V((math.cos(aa) * 0.18, math.sin(aa) * 0.18, 0.0)))
    bw = [0.01, 0.03, 0.043, 0.05, 0.052, 0.05, 0.043, 0.03, 0.01]
    br = bm_blade(brim, bw, thick=0.009, up=(0, 0, 1))
    deform(br, lambda co: co + V((0, -0.025 * max(0, -(co.y - capc.y) - 0.15) / 0.06, -0.018 * max(0, -(co.y - capc.y) - 0.15) / 0.06)))
    rot(br, 'X', tilt, capc)
    R.add('Head', br, NAVY, smooth=False)
    btn = bm_sphere(capc + V((0, 0, 0.088)), (0.016, 0.016, 0.009), seg=8, rings=4)
    rot(btn, 'X', tilt, capc)
    R.add('Head', btn, 'M_Brass')
    sbtn = bm_sphere(capc + V((0.17, -0.07, 0.02)), (0.012, 0.012, 0.012), seg=6, rings=4)
    rot(sbtn, 'X', tilt, capc)
    R.add('Head', sbtn, 'M_Brass')
    for k, (dz, ln, m) in enumerate(((0.0, 0.11, BLUE_), (0.012, 0.085, 'M_BluebirdBelly'))):
        p0 = capc + V((0.175, -0.06, 0.03 + dz))
        pts = [p0, p0 + V((0.025, 0.04, ln * 0.55)), p0 + V((0.03, 0.08, ln))]
        fb = bm_blade(pts, [0.012, 0.018, 0.003], thick=0.008, up=(1, 0, 0))
        rot(fb, 'X', tilt, capc)
        R.add('Head', fb, m, smooth=False)

    # ---------------- short shoulder cape: navy outside, cobalt lining, open in front, brass clasp
    rows = [(0.705, 0.13), (0.69, 0.175), (0.665, 0.212), (0.635, 0.232), (0.603, 0.24)]
    cols = 22
    o_b = L.bmesh.new()
    gso, gsi = [], []
    for ri, (z, r) in enumerate(rows):
        ro, rin = [], []
        for j in range(cols + 1):
            a = math.radians(-90 + 36 + (360 - 72) * j / cols)
            d = V((math.cos(a), math.sin(a), 0))
            back = max(0.0, d.y)
            zz = z - (0.035 * back * (ri / (len(rows) - 1)) ** 1.2)
            if ri == len(rows) - 1:
                zz += 0.012 * math.sin(j * 1.7)   # wavy hem
            rr = r * (1.0 + 0.05 * back)
            p = V((d.x * rr * 1.08, d.y * rr * 0.98, zz))
            ro.append(o_b.verts.new(p))
            rin.append(o_b.verts.new(p - V((d.x, d.y, 0.0)) * 0.007 + V((0, 0, 0.002))))
        gso.append(ro)
        gsi.append(rin)
    lin_faces = []
    for ri in range(len(rows) - 1):
        for j in range(cols):
            o_b.faces.new((gso[ri][j], gso[ri][j + 1], gso[ri + 1][j + 1], gso[ri + 1][j]))
            lin_faces.append(o_b.faces.new((gsi[ri][j], gsi[ri + 1][j], gsi[ri + 1][j + 1], gsi[ri][j + 1])))
    for j in range(cols):   # hem rim + collar rim
        o_b.faces.new((gso[-1][j], gso[-1][j + 1], gsi[-1][j + 1], gsi[-1][j]))
        o_b.faces.new((gso[0][j + 1], gso[0][j], gsi[0][j], gsi[0][j + 1]))
    for ri in range(len(rows) - 1):   # front opening edges
        o_b.faces.new((gso[ri][0], gso[ri + 1][0], gsi[ri + 1][0], gsi[ri][0]))
        o_b.faces.new((gso[ri + 1][-1], gso[ri][-1], gsi[ri][-1], gsi[ri + 1][-1]))
    o_b.normal_update()
    lining_centers = [f.calc_center_median().copy() for f in lin_faces]
    o_b = subdivide(o_b, 1)
    L.bmesh.ops.recalc_face_normals(o_b, faces=o_b.faces)

    def cape_mat(c, n):
        rad = V((c.x, c.y, 0))
        if rad.length > 1e-6 and n.dot(rad.normalized()) < -0.2:
            return BLUE_
        return None
    capew = blend_w(lambda c: -c.z, 'Body', 'Cape', -0.69, -0.63)
    R.add(capew, o_b, NAVY, smooth=True, face_mat=cape_mat)
    clasp = bm_sphere((0.0, -0.165, 0.672), (0.018, 0.011, 0.018), seg=8, rings=5)
    R.add('Body', clasp, 'M_Brass')

    # ---------------- meta + contacts
    R.meta.update(height=1.07, kind='bird', toe=0.12, heel=0.045, head_r=0.19, knee_r=0.022,
                  head_c=tuple(hc - V((0, -0.005, 0.71))), arm_out=7.0)
    from ouat_rig import to_rig
    R.meta['head_c'] = tuple(to_rig(hc - V((0, -0.005, 0.71))))
    R.meta['height'] = 1.08
    R.meta['rest_pose'] = {'B.ArmL.z': 7.0, 'B.ArmR.z': -7.0, 'B.ForeArmL.x': -8.0, 'B.ForeArmR.x': -8.0}
    humanoid_contacts(R, sole_y=0.075, toe=0.125, heel=0.045, knee_r=0.03, hand_r=0.03,
                      head_c=R.meta['head_c'], head_r=0.19, body_c=tuple(to_rig(V((0, 0, 0.05)))), body_r=0.2, hips_r=0.15)
    hero_clips(R)
    return R


def hero_clips(R):
    D = A.Dims(R)

    def bird_walk_extra(ch, t, ph, cL, b_):
        ch['B.Tail.x'] = -6 + 10 * b_
        ch['B.Tail.y'] = 8 * cL
        ch['B.Cape.x'] = 10 + 6 * b_
        return ch

    def bird_run_extra(ch, t, ph, cL, b_):
        ch['B.Tail.x'] = -18 + 12 * b_
        ch['B.Tail.y'] = 10 * cL
        ch['B.Cape.x'] = 28 + 8 * b_
        for s in 'LR':
            ch[f'B.Arm{s}.z'] = A.sgn(s) * (22 + 6 * b_)
        return ch
    # walk = brisk trot: 3.2 m/s for a 1.07 m bird is beyond a walk -> short flight phase, 4 steps/s
    R.clips.append(('Idle',) + A.c_idle(R, D, 2.8))
    R.clips.append(('Walk',) + A.locomotion(R, D, 3.2, 15, stance=0.32, lift=0.07, bob=0.028, lean=8, arm=22, yaw=7,
                                            roll=3, elbow=12, crouch=0.06, extra=bird_walk_extra))
    R.clips.append(('Run',) + A.locomotion(R, D, 5.0, 12, stance=0.26, lift=0.1, bob=0.04, lean=18, arm=30, yaw=8,
                                           roll=3, elbow=35, crouch=0.09, th_off=35, extra=bird_run_extra))
    R.meta['speeds'] = {'Walk': 3.2, 'Run': 5.0}
    common_gestures(R, D, beckon=False, lookback=False, gather=False, sit=False)
    R.clips.append(('Push',) + A.c_push(R, D))
    R.clips.append(('FallTumble',) + A.c_falltumble(R, D))
    R.clips.append(('LieDown',) + A.c_liedown(R, D))
    R.clips.append(('GetUp',) + A.c_getup(R, D))
    R.clips.append(('LookAround',) + A.c_lookaround(R, D))
    R.clips.append(('Kneel',) + A.c_kneel(R, D))


def common_gestures(R, D, beckon=True, lookback=False, gather=True, sit=True, reach=True, kneel=False):
    m = A.mirrored if R.meta.get('hand') == 'L' else (lambda c: c)   # gesture with the finished hand
    R.clips.append(('Talk',) + m(A.c_talk(R, D)))
    R.clips.append(('Bow',) + A.c_bow(R, D))
    R.clips.append(('BowHold',) + A.c_bowhold(R, D))
    R.clips.append(('Rise',) + A.c_rise(R, D))
    R.clips.append(('Point',) + m(A.c_point(R, D)))
    R.clips.append(('PointUp',) + m(A.c_point(R, D, up=True)))
    R.clips.append(('LookUp',) + A.c_lookup(R, D))
    if beckon:
        R.clips.append(('Beckon',) + m(A.c_beckon(R, D)))
    if lookback:
        R.clips.append(('LookBack',) + A.c_lookback(R, D))
    R.clips.append(('Nod',) + A.c_nod(R, D))
    R.clips.append(('HeadTilt',) + A.c_headtilt(R, D))
    if reach:
        R.clips.append(('Reach',) + m(A.c_reach(R, D)))
    if gather:
        R.clips.append(('Gather',) + A.c_gather(R, D))
    if sit:
        R.clips.append(('SitIdle',) + A.c_sitidle(R, D))
    R.clips.append(('Cower',) + A.c_cower(R, D))
    if kneel:
        R.clips.append(('Kneel',) + A.c_kneel(R, D))


# =====================================================================================  puppet parts
def puppet_limbs(R, dims, mat=WOOD, jmat=JOINT, arm_fm=None, leg_fm=None, hands=('mitten', 'mitten'),
                 ink_fore=(False, False), ink_shin=(False, False), foot=(0.12, 0.07, 0.05), sleeve=None, shorts=None, skip_fore=(False, False)):
    """dims: dict hip, knee, ankle, sh, el, wr (left side, build space), r_leg, r_arm, hand."""
    for s, x in (('L', 1), ('R', -1)):
        i = 0 if s == 'L' else 1
        hip, knee, ank = [V((p[0] * x, p[1], p[2])) for p in (dims['hip'], dims['knee'], dims['ankle'])]
        sh, el, wr = [V((p[0] * x, p[1], p[2])) for p in (dims['sh'], dims['el'], dims['wr'])]
        rl, ra = dims['r_leg'], dims['r_arm']
        # legs
        R.add('Leg' + s, ball(hip, rl * 1.12, seg=10, rings=7), jmat)
        R.add('Leg' + s, capsule(hip, knee + V((0, 0, rl * 0.6)), rl, rl * 0.86, seg=8), mat, face_mat=leg_fm)
        R.add('Shin' + s, ball(knee, rl * 0.95, seg=10, rings=7), jmat)
        if ink_shin[i] == 'skip':
            pass
        elif ink_shin[i]:
            for dx in (-rl * 0.6, rl * 0.6):
                R.add('Shin' + s, stroke(wobble_line(knee + V((dx, 0, -rl)), ank + V((dx * 0.8, 0, 0)), 4, 0.004, dx * 50), max(0.004, rl * 0.12)), INK, smooth=False)
        else:
            R.add('Shin' + s, capsule(knee - V((0, 0, rl * 0.5)), ank + V((0, 0, rl * 0.2)), rl * 0.85, rl * 0.7, seg=8), mat, face_mat=leg_fm)
        fl, fw, fh = foot
        fb = bm_box(ank + V((0, -fl * 0.28, -ank.z + fh * 0.5)), (fw, fl, fh))
        fb = L.bevel(fb, min(fw, fh) * 0.28, 1, 40)
        R.add('Foot' + s, fb, mat, smooth=False, face_mat=leg_fm)
        R.add('Foot' + s, ball(ank, rl * 0.68, seg=8, rings=6), jmat)
        if shorts:
            sm, z0, z1, rr = shorts
            sh_ = capsule(hip + V((0, 0, 0.0)), hip.lerp(knee, z1), rl * rr, rl * rr * 0.95, seg=10)
            sfn = paint_above(hip.lerp(knee, z1 * 0.85).z, sm, amp=rl * 0.5, freq=14 / max(0.3, dims['scale']), seed=3 + i)
            R.add('Leg' + s, sh_, WOOD, smooth=False, face_mat=sfn)
            brush(R, 'Leg' + s, sh_, hip.lerp(knee, z1 * 0.85).z, sm, center=(hip.x, hip.y), n=6, ln=rl * 1.8, w=rl * 0.5, seed=9 + i)
        # arms
        R.add('Arm' + s, ball(sh, ra * 1.18, seg=10, rings=7), jmat)
        R.add('Arm' + s, capsule(sh - V((0, 0, ra * 0.3)), el + V((0, 0, ra * 0.4)), ra, ra * 0.88, seg=8), mat, face_mat=arm_fm)
        R.add('ForeArm' + s, ball(el, ra * 0.95, seg=8, rings=6), jmat)
        d = (wr - el).normalized()
        if skip_fore[i]:
            pass
        elif ink_fore[i]:
            for dx in (-ra * 0.55, ra * 0.55):
                o = V((dx, 0, 0))
                R.add('ForeArm' + s, stroke(wobble_line(el + o + d * ra, wr + o * 0.8, 4, 0.004, dx * 40), max(0.004, ra * 0.13)), INK, smooth=False)
            ink_hand(To(R, 'Hand' + s), wr, d, ln=dims['hand'] * 1.3, side=x, r=max(0.004, ra * 0.14))
        else:
            R.add('ForeArm' + s, capsule(el - V((0, 0, ra * 0.4)), wr + V((0, 0, ra * 0.3)), ra * 0.86, ra * 0.72, seg=8), mat, face_mat=arm_fm)
            if hands[i] == 'mitten':
                R.add('Hand' + s, ball(wr, ra * 0.75, seg=8, rings=5), jmat)
                R.add('Hand' + s, mitten(wr, d, dims['hand'], x), mat, smooth=False)
                # thumb nub
                th = bm_box((0, 0, 0), (dims['hand'] * 0.22, dims['hand'] * 0.22, dims['hand'] * 0.45))
                th = L.bevel(th, dims['hand'] * 0.07, 1, 40)
                move(th, wr + d * dims['hand'] * 0.35 + V((0, -dims['hand'] * 0.3, 0)))
                R.add('Hand' + s, th, mat, smooth=False)
            elif hands[i] == 'ink':
                ink_hand(To(R, 'Hand' + s), wr, d, ln=dims['hand'] * 1.3, side=x, r=max(0.004, ra * 0.14))
        if sleeve:
            sm, frac, rr = sleeve
            sv = capsule(sh - V((0, 0, ra * 0.2)), sh.lerp(el, frac), ra * rr, ra * rr * 0.95, seg=10)
            R.add('Arm' + s, sv, WOOD, smooth=False, face_mat=paint_above(sh.lerp(el, frac * 0.8).z, sm, amp=ra * 0.5, freq=16, seed=5 + i))
            brush(R, 'Arm' + s, sv, sh.lerp(el, frac * 0.8).z, sm, center=(sh.x, sh.y), n=5, ln=ra * 1.7, w=ra * 0.5, seed=21 + i)


def puppet_bones(R, dims, head_pivot, waist, hips):
    R.bone('Hips', None, hips)
    R.bone('Body', 'Hips', waist)
    R.bone('Head', 'Body', head_pivot)
    for s, x in (('L', 1), ('R', -1)):
        R.bone('Leg' + s, 'Hips', V((dims['hip'][0] * x, dims['hip'][1], dims['hip'][2])))
        R.bone('Shin' + s, 'Leg' + s, V((dims['knee'][0] * x, dims['knee'][1], dims['knee'][2])))
        R.bone('Foot' + s, 'Shin' + s, V((dims['ankle'][0] * x, dims['ankle'][1], dims['ankle'][2])))
    for s, x in (('L', 1), ('R', -1)):
        R.bone('Arm' + s, 'Body', V((dims['sh'][0] * x, dims['sh'][1], dims['sh'][2])))
        R.bone('ForeArm' + s, 'Arm' + s, V((dims['el'][0] * x, dims['el'][1], dims['el'][2])))
        R.bone('Hand' + s, 'ForeArm' + s, V((dims['wr'][0] * x, dims['wr'][1], dims['wr'][2])))


def puppet_meta(R, dims, height, head_c_world, head_r, body_c_world, body_r, kind='puppet', foot=(0.12, 0.07, 0.05)):
    from ouat_rig import to_rig
    hp = R.bones['Head'][1]
    R.meta.update(height=height, kind=kind, toe=foot[0] * 0.62, heel=foot[0] * 0.3, head_r=head_r, knee_r=dims['r_leg'],
                  head_c=tuple(to_rig(V(head_c_world) - hp)), arm_out=5.0)
    R.meta.setdefault('rest_pose', {'B.ArmL.z': 5.0, 'B.ArmR.z': -5.0, 'B.ForeArmL.x': -10.0, 'B.ForeArmR.x': -10.0})
    bp = R.bones['Body'][1]
    humanoid_contacts(R, sole_y=dims['ankle'][2], toe=foot[0] * 0.7, heel=foot[0] * 0.32, knee_r=dims['r_leg'],
                      hand_r=dims['hand'] * 0.4, head_c=R.meta['head_c'], head_r=head_r,
                      body_c=tuple(to_rig(V(body_c_world) - bp)), body_r=body_r, hips_r=dims['r_leg'] * 2)


# =====================================================================================  unfinished-form helpers
PENCIL = 'M_PencilBody'


def brush(R, target, b, z_edge, mat, center=(0, 0), n=7, ln=0.06, w=0.014, down=True, seed=0.0, arc=(0, 360)):
    """Dry-brush streaks running off a paint edge: flush to the surface (no outline material), tapered, uneven."""
    rnd = random.Random(int(seed * 1000) + 11)
    bvh = BVHTree.FromBMesh(b)
    cx, cy = center
    for k in range(n):
        a = math.radians(arc[0] + (arc[1] - arc[0]) * (k + rnd.uniform(-0.4, 0.4)) / n)
        Ln = ln * rnd.choice((0.35, 0.55, 0.8, 1.0, 1.3))
        wk = w * rnd.uniform(0.5, 1.2)
        drift = rnd.uniform(-0.25, 0.25)
        pts, nrms = [], []
        for t in range(7):
            f = t / 6
            z = z_edge + (-1 if down else 1) * (Ln * f - 0.006)
            aa = a + drift * f * (Ln / 0.3)
            d = V((math.cos(aa), math.sin(aa), 0))
            hit = bvh.ray_cast(V((cx, cy, z)) + d * 3.0, -d)
            if hit[0] is None:
                break
            pts.append(hit[0] + hit[1] * 0.0022)
            nrms.append(hit[1])
        if len(pts) < 3:
            continue
        prof = [1.0, 0.95, 0.85, 0.7, 0.5, 0.3, 0.06]
        ww = [wk * prof[i] for i in range(len(pts))]
        R.add(target, bm_blade(pts, ww, thick=0.0015, up=tuple(nrms[len(nrms) // 2])), BRUSH.get(mat, mat), smooth=False)


def ring_pts(c, axis, r, n=12, wob=0.0, seed=0.0, start=0.0, sweep=1.0):
    axis = V(axis).normalized()
    u = axis.orthogonal().normalized()
    v = axis.cross(u).normalized()
    out = []
    for i in range(n + 1):
        a = start + 2 * math.pi * sweep * i / n
        rr = r * (1 + wob * math.sin(3 * a + seed))
        out.append(V(c) + u * math.cos(a) * rr + v * math.sin(a) * rr)
    return out


def sketch_cyl(R, target, p0, p1, r0, r1, lw=0.004, rings=3, longs=4, seed=0.0, mat=PENCIL, overshoot=0.15):
    """Construction-line cylinder: cross-section ellipses + longitudinal lines that overshoot like a pencil sketch."""
    p0, p1 = V(p0), V(p1)
    ax = p1 - p0
    rnd = random.Random(int(seed * 97) + 3)
    for k in range(rings):
        t = k / max(1, rings - 1)
        c = p0.lerp(p1, t)
        r = r0 + (r1 - r0) * t
        pts = ring_pts(c, ax, r * rnd.uniform(0.95, 1.08), 14, 0.05, seed + k, rnd.uniform(0, 6), rnd.uniform(0.85, 1.08))
        R.add(target, stroke(pts, lw, taper=True), mat, smooth=False)
    u = ax.orthogonal().normalized()
    v = ax.normalized().cross(u)
    for k in range(longs):
        a = 2 * math.pi * (k + 0.5) / longs + rnd.uniform(-0.2, 0.2)
        d = u * math.cos(a) + v * math.sin(a)
        q0 = p0 - ax * overshoot * rnd.uniform(0.2, 1.0) + d * r0
        q1 = p1 + ax * overshoot * rnd.uniform(0.0, 0.8) + d * r1
        R.add(target, stroke(wobble_line(q0, q1, 5, lw * 1.5, seed + k), lw, taper=True), mat, smooth=False)


def torn_tube(p0, p1, r0, r1, seg=9, tear=0.6, seed=0.0, steps=4):
    """Solid tube whose far end is torn off like paper: jagged rim, capped. Returns (bmesh, rim points)."""
    p0, p1 = V(p0), V(p1)
    pts = [p0.lerp(p1, i / steps) for i in range(steps + 1)]
    rad = [r0 + (r1 - r0) * i / steps for i in range(steps + 1)]
    b = bm_tube(pts, rad, seg=seg, cap=True)
    ax = (p1 - p0).normalized()
    L_ = (p1 - p0).length
    rnd = random.Random(int(seed * 131) + 5)
    rim = []
    jag = [rnd.uniform(-1, 1) * (1 if i % 2 else 0.4) for i in range(seg)]
    for v in b.verts:
        t = (v.co - p0).dot(ax) / L_
        if t > 0.999:
            rel = v.co - p1
            if rel.length < 1e-6:
                v.co += ax * (-tear * r1 * 0.2)
                continue
            u = ax.orthogonal().normalized()
            ang = math.atan2(rel.dot(ax.cross(u)), rel.dot(u))
            k = int(((ang + math.pi) / (2 * math.pi)) * seg) % seg
            v.co += ax * (jag[k] * tear * r1)
    # rim = verts at t>~1 after the jag; rebuild an ink line from the jagged ring
    ring = sorted([v.co.copy() for v in b.verts if (v.co - p0).dot(ax) / L_ > 1 - tear * r1 / L_ * 1.2 and ((v.co - p0) - ax * (v.co - p0).dot(ax)).length > r1 * 0.6],
                  key=lambda c: math.atan2((c - p1).dot(ax.cross(ax.orthogonal().normalized())), (c - p1).dot(ax.orthogonal().normalized())))
    if ring:
        ring.append(ring[0])
    return b, ring


def torn_limb(R, solid_bone, sketch_bone, p0, p1, r0, r1, frac=0.55, mat=WOOD, lw=0.004, seed=0.0, fm=None):
    """Solid wood up to frac of the segment (torn rim + ink edge), then pencil construction lines to p1."""
    p0, p1 = V(p0), V(p1)
    pm = p0.lerp(p1, frac)
    rm = r0 + (r1 - r0) * frac
    b, rim = torn_tube(p0, pm, r0, rm, seg=10, tear=0.9, seed=seed)
    R.add(solid_bone, b, mat, smooth=False, face_mat=fm)
    if len(rim) > 3:
        R.add(solid_bone, stroke(rim, lw * 0.9, taper=False), INK, smooth=False)
    sketch_cyl(R, sketch_bone, pm - (p1 - p0) * 0.05, p1, rm, r1, lw=lw, rings=2, longs=4, seed=seed)


# =====================================================================================  KINOPIO
def build_kinopio():
    R = RigChar('Kinopio')
    # longer legs than round 1 (leg 0.32 m) so 2.2 m/s reads as a quick child's trot, not a crouch
    dims = dict(hip=(0.055, 0, 0.36), knee=(0.057, -0.004, 0.205), ankle=(0.058, 0, 0.052),
                sh=(0.1, 0, 0.535), el=(0.11, 0.0, 0.445), wr=(0.115, 0, 0.36), r_leg=0.025, r_arm=0.021, hand=0.06, scale=0.8)
    puppet_bones(R, dims, head_pivot=(0, 0, 0.575), waist=(0, 0, 0.385), hips=(0, 0, 0.375))
    R.bone('Nose', 'Head', (0, -0.075, 0.69))
    # ---- pelvis (red shorts) + torso (blue shirt, white collar, navy suspenders)
    pel = bm_sphere((0, 0, 0.38), (0.092, 0.074, 0.056), seg=14, rings=8)
    R.add('Hips', pel, RED, face_mat=paint_below(0.35, WOOD, amp=0.01, freq=22, seed=1))
    tor = bm_lathe([(0.0, 0.395), (0.078, 0.4), (0.093, 0.44), (0.098, 0.49), (0.09, 0.53), (0.056, 0.556), (0.0, 0.56)], seg=14, sy=0.78)
    tor = subdivide(tor, 2)
    brush(R, 'Body', tor, 0.462, BLUE, n=8, ln=0.045, w=0.012, seed=2)
    R.add('Body', tor, WOOD, face_mat=paint_above(0.462, BLUE, amp=0.008, freq=26, seed=2))
    R.add('Body', ball((0, 0, 0.388), 0.031, seg=10, rings=7), JOINT)
    for x in (1, -1):
        p0 = V((0.01 * x, -0.058, 0.555))
        R.add('Body', bm_blade([p0, p0 + V((0.028 * x, -0.012, -0.02)), p0 + V((0.047 * x, -0.004, -0.028))], [0.013, 0.017, 0.004],
                               thick=0.006, up=(0, -1, 0.4)), 'M_PaintWhite', smooth=False)
    bvh = BVHTree.FromBMesh(tor)
    for x in (1, -1):
        sp = []
        for i in range(8):
            z = 0.553 - i * 0.021
            xx = (0.048 - 0.006 * i / 7) * x
            hit = bvh.ray_cast(V((xx, -0.5, z)), V((0, 1, 0)))
            if hit[0] is not None:
                sp.append(hit[0] + hit[1] * 0.003)
        R.add('Body', bm_tube(sp, 0.0085, seg=4, cap=False, flat=0.35, up=(0, -1, 0)), 'M_PaintNavy', smooth=False)
        R.add('Body', bm_sphere(sp[-1] + V((0, -0.005, 0.0)), (0.009, 0.006, 0.009), seg=6, rings=4), 'M_Brass')
    # ---- limbs: left arm finished, right forearm torn off mid-way and continued as pencil construction
    puppet_limbs(R, dims, hands=('mitten', 'none'), foot=(0.105, 0.06, 0.044), sleeve=(BLUE, 0.55, 1.35),
                 shorts=(RED, 0, 0.42, 1.42), skip_fore=(False, True))
    el, wr = V((-0.11, 0.0, 0.445)), V((-0.115, 0, 0.36))
    torn_limb(R, 'ForeArmR', 'ForeArmR', el - V((0, 0, 0.012)), wr, 0.018, 0.015, frac=0.5, lw=0.0032, seed=4)
    ink_hand(To(R, 'HandR'), wr, (wr - el).normalized(), ln=0.07, side=-1, r=0.0028)
    # ---- head: carved face plank (solid, front) + the rest of the hex head still a pencil construction
    hc = V((0, -0.005, 0.71))
    sx, sy, sz = 0.165, 0.078, 0.125
    outline = [(math.cos(math.radians(60 * i)) * sx * (1.0 if i % 3 == 0 else 0.86), math.sin(math.radians(60 * i)) * sz) for i in range(6)]
    front_d = 0.112   # solid depth from the face (back ~30 % still a pencil construction)
    hb = L.bm_prism(outline, -sy, -sy + front_d, center=hc, axis='Y')
    hb = L.bevel(hb, 0.02, 1, 40)
    # torn back edge: push the back face verts by noise so the cut is ragged
    for v in hb.verts:
        if v.co.y > hc.y - sy + front_d - 0.025:
            v.co.y += 0.018 * nval(v.co, 30.0, 7) + 0.006 * math.sin(v.co.x * 90)
    jitter(hb, 0.0025, 4.0, 5)
    hbv = BVHTree.FromBMesh(hb)
    R.add('Head', hb, WOOD, smooth=False, face_mat=paint_above(0.81, BLUE, amp=0.008, freq=24, seed=6))
    # ink along the ragged back rim (the edge where carving stopped)
    rim = []
    for i in range(25):
        a = 2 * math.pi * i / 24
        d = V((math.cos(a) * sx * 1.2, 0, math.sin(a) * sz * 1.2))
        hit = hbv.ray_cast(hc + V((0, -sy + front_d - 0.012, 0)) + d * 2.0, -d.normalized())
        if hit[0] is not None:
            rim.append(hit[0] + hit[1] * 0.002)
    if len(rim) > 4:
        rim.append(rim[0])
        R.add('Head', stroke(rim, 0.0035, taper=False), INK, smooth=False)
    # pencil construction of the unfinished back half: back hex outline + connecting edges, overshooting
    yb = hc.y + sy
    yf = hc.y - sy + front_d - 0.01
    corners = [V((hc.x + u, 0, hc.z + w)) for u, w in outline]
    rnd = random.Random(8)
    back = [V((c.x, yb, c.z)) for c in corners] + [V((corners[0].x, yb, corners[0].z))]
    R.add('Head', stroke([p + V((rnd.uniform(-0.004, 0.004), 0, rnd.uniform(-0.004, 0.004))) for p in back], 0.0022, taper=False), PENCIL, smooth=False)
    for c in corners:
        q0 = V((c.x, yf - 0.006, c.z))
        q1 = V((c.x, yb + 0.018, c.z))
        R.add('Head', stroke(wobble_line(q0, q1, 4, 0.003, c.x * 30), 0.002), PENCIL, smooth=False)
    R.add('Head', capsule((0, 0, 0.568), (0, -0.004, 0.605), 0.019, 0.019, seg=7), WOOD)
    R.add('Head', ball((0, 0, 0.575), 0.023, seg=8, rings=6), JOINT)
    # eyes (char left = deep hole, char right = drawn ring with a dot)
    hit = hbv.ray_cast(V((0.064, -0.5, 0.72)), V((0, 1, 0)))
    R.add('Head', oriented_eye(hit[0] - hit[1] * 0.003, hit[1], (0.031, 0.012, 0.038)), INK)
    hit = hbv.ray_cast(V((-0.064, -0.5, 0.722)), V((0, 1, 0)))
    c, n = hit[0], hit[1]
    ring = []
    for i in range(15):
        a = 2 * math.pi * i / 14 + 0.3
        ring.append(c + n * 0.003 + V((math.cos(a) * 0.034 * (1 + 0.07 * math.sin(3 * a)), 0, math.sin(a) * 0.036)))
    R.add('Head', stroke(ring, 0.0045, taper=False), INK, smooth=False)
    R.add('Head', oriented_eye(c + n * 0.002 + V((0.006, 0, 0.002)), n, (0.012, 0.005, 0.013)), INK)
    # paint tufts (brush chips) on top
    for k, (m, off, ln, ang) in enumerate(((RED, (-0.05, -0.02, 0.11), 0.085, 12), (BLUE, (-0.022, -0.01, 0.115), 0.065, -6),
                                           (RED, (0.07, -0.03, 0.105), 0.05, -25))):
        p0 = hc + V(off)
        d = V((math.sin(math.radians(ang)), 0.0, math.cos(math.radians(ang))))
        pts = [p0, p0 + d * ln * 0.5 + V((0, 0.01, 0)), p0 + d * ln + V((0.0, 0.025, 0))]
        R.add('Head', bm_blade(pts, [ln * 0.18, ln * 0.21, ln * 0.05], thick=ln * 0.06, up=(0, 1, 0)), m, smooth=False)
    # ---- nose = translucent pencil line (retraced), on its own bone (kept level by the 'post' hook)
    root = V((0, -0.075, 0.69))
    tip = root + V((0.01, -0.32, 0.03))
    R.add('Nose', bm_tube([root, root.lerp(tip, 0.5), tip], [0.012, 0.006, 0.0015], seg=6), 'M_SketchNose')
    for k, (dx, dz) in enumerate(((0.012, 0.004), (-0.01, 0.003), (0.002, -0.012))):
        p0 = root + V((dx, 0.012, dz))
        p1 = tip + V((dx * 0.2 + 0.006 * k, -0.03 * (k % 2) - 0.01, dz * 0.2))
        R.add('Nose', stroke(wobble_line(p0, p1, 6, 0.005, k * 1.9), 0.0032), 'M_SketchNose', smooth=False)
    # ---- Mark (separate object, hidden by default in Unity)
    mk = [V((0.064 + 0.011 * i, -0.052 + 0.018 * i, 0.545 - 0.011 * i)) for i in range(5)]
    R.add('Body', bm_blade(mk, [0.006, 0.012, 0.014, 0.012, 0.004], thick=0.004, up=(0.5, -0.6, 0.8)), 'M_Mark', smooth=False, obj='Mark')
    puppet_meta(R, dims, 0.87, hc, 0.14, (0, 0, 0.47), 0.1, foot=(0.105, 0.06, 0.044))
    R.meta['rest_pose'] = {'B.ArmL.z': 6.0, 'B.ArmR.z': -6.0, 'B.ForeArmL.x': -12.0, 'B.ForeArmR.x': -12.0, 'B.Head.x': -3}

    def level_nose(ch):
        pitch = ch.get('hips.x', 0) + ch.get('B.Body.x', 0) + ch.get('B.Head.x', 0)
        ch['B.Nose.x'] = ch.get('B.Nose.x', 0) - max(-30.0, min(95.0, pitch)) * 0.9
        return ch
    R.meta['post'] = level_nose
    R.meta['hand'] = 'L'   # right forearm is unfinished -> gestures with the left
    kinopio_clips(R)
    return R


def kinopio_clips(R):
    D = A.Dims(R)

    def puppet_extra(ch, t, ph, cL, b_):
        ch['B.Nose.x'] = 2 * b_
        ch['B.Head.z'] = ch.get('B.Head.z', 0) + 3 * cL   # wooden head wobble
        return ch
    R.clips.append(('Idle',) + A.c_idle(R, D, 2.8))
    R.clips.append(('Walk',) + A.locomotion(R, D, 2.2, 10, stance=0.3, lift=0.05, bob=0.016, lean=5, arm=24, yaw=8,
                                            roll=4, elbow=14, crouch=0.0, extra=puppet_extra))
    R.clips.append(('Run',) + A.locomotion(R, D, 4.0, 9, stance=0.23, lift=0.075, bob=0.026, lean=14, arm=36, yaw=9,
                                           roll=4, elbow=55, crouch=0.02, th_off=35, extra=puppet_extra))
    R.meta['speeds'] = {'Walk': 2.2, 'Run': 4.0}
    common_gestures(R, D, beckon=True, lookback=True, gather=True, sit=True, kneel=True)
    R.clips.append(('Push',) + A.c_push(R, D))


# =====================================================================================  CHIEF
def leaf_rosette(R, bone, c, rnd, n=6, size=0.3, out=V((0, 0, 1))):
    """Clump of pointed paper leaf cards fanning out (reads as leaves, keeps gaps)."""
    out = V(out).normalized()
    u = out.orthogonal().normalized()
    w = out.cross(u)
    for k in range(n):
        a = 2 * math.pi * k / n + rnd.uniform(-0.3, 0.3)
        d = (u * math.cos(a) + w * math.sin(a)) * 0.85 + out * 0.55
        d.normalize()
        ln = size * rnd.uniform(0.75, 1.15)
        p0 = c + d * size * 0.12
        pts = [p0, p0 + d * ln * 0.45 + V((0, 0, 0.03)), p0 + d * ln]
        nrm = d.cross(u * -math.sin(a) + w * math.cos(a)).normalized()
        b = bm_blade(pts, [ln * 0.08, ln * 0.24, ln * 0.015], thick=0.012, up=tuple(nrm))
        R.add(bone, b, 'M_Leaf', smooth=False)
        # midrib ink line on every other leaf
        if k % 2 == 0:
            R.add(bone, stroke([p0 + nrm * 0.014, p0 + d * ln * 0.85 + nrm * 0.014], 0.005), INK, smooth=False)


def build_chief():
    """Chief: walking dangsan tree elder (~3 m), wide crown with gaps, root legs, branch arms."""
    R = RigChar('Chief')
    BARK, LEAF = 'M_Bark', 'M_Leaf'
    rnd = random.Random(31)
    dims = dict(hip=(0.3, 0, 1.02), knee=(0.36, -0.05, 0.56), ankle=(0.38, 0, 0.16),
                sh=(0.56, 0.0, 1.86), el=(0.8, -0.04, 1.36), wr=(0.86, -0.08, 0.9), r_leg=0.16, r_arm=0.11, hand=0.2, scale=3.0)
    puppet_bones(R, dims, head_pivot=(0, 0, 1.95), waist=(0, 0, 1.08), hips=(0, 0, 1.04))
    R.bone('Canopy', 'Head', (0, 0.05, 2.45))
    # ---- legs: bark thighs, puppet knee balls, shins flaring into spreading root feet
    for s, x in (('L', 1), ('R', -1)):
        hip, knee, ank = [V((p[0] * x, p[1], p[2])) for p in (dims['hip'], dims['knee'], dims['ankle'])]
        R.add('Leg' + s, ball(hip, 0.2, seg=10, rings=7), JOINT)
        th = bm_tube([hip, hip.lerp(knee, 0.5) + V((0.03 * x, 0, 0)), knee + V((0, 0, 0.08))], [0.17, 0.155, 0.14], seg=10, twist=0.3)
        jitter(th, 0.018, 3, 20 + x)
        R.add('Leg' + s, th, BARK, face_mat=paint_below(0.72, RED, amp=0.04, freq=8, seed=3 + x))
        R.add('Shin' + s, ball(knee, 0.15, seg=10, rings=7), JOINT, face_mat=L.ragged(lambda c: -c.z, -0.6, RED, amp=0.05, freq=10, seed=7 + x))
        sh_ = bm_tube([knee - V((0, 0, 0.06)), knee.lerp(ank, 0.6), ank + V((0, 0, 0.02))], [0.13, 0.135, 0.16], seg=10, twist=0.4)
        jitter(sh_, 0.015, 3, 30 + x)
        R.add('Shin' + s, sh_, BARK)
        for k, ang in enumerate((-70, -30, 5, 40, 75, 160)):
            a = math.radians(ang) * x
            d = V((math.sin(a), -math.cos(a), 0))
            ln = (0.42 if k < 5 else 0.28) * rnd.uniform(0.85, 1.15)
            p0 = ank + V((0, 0, 0.02))
            pts = [p0, p0 + d * ln * 0.45 + V((0, 0, -0.08)), p0 + d * ln + V((0, 0, -0.15))]
            rt = bm_tube(pts, [0.1, 0.065, 0.022], seg=6)
            jitter(rt, 0.012, 5, k + x * 3)
            R.add('Foot' + s, rt, BARK)
            if k in (1, 4):   # an unfinished root continuing as ink
                tip = pts[-1]
                R.add('Foot' + s, stroke(wobble_line(tip, tip + d * 0.22 + V((0, 0, -0.005)), 4, 0.02, k), 0.008), INK, smooth=False)
    # ---- trunk body: gnarled, widening upward (wide shoulders), twisted ink bark lines
    tpts = [V((0, 0, 0.98)), V((0.03, 0.01, 1.2)), V((-0.02, 0.02, 1.45)), V((0.02, 0.0, 1.7)), V((0, 0.0, 1.92))]
    tr = bm_tube(tpts, [0.36, 0.33, 0.36, 0.46, 0.58], seg=14, twist=0.3, flat=0.82, up=(0, 1, 0))
    jitter(tr, 0.04, 2.2, 30)
    tr = subdivide(tr, 1)
    brush(R, 'Body', tr, 1.6, BLUE, n=6, ln=0.22, w=0.05, seed=41, arc=(-20, 200))
    _pb = paint_above(1.6, BLUE, amp=0.04, freq=7, seed=41)
    R.add('Body', tr, BARK, face_mat=lambda c, n: _pb(c, n) if c.y > -0.12 else None)   # paint on the back/sides, bare under the beard
    R.add('Hips', ball((0, 0, 1.0), 0.3, seg=12, rings=8), JOINT)
    for k in range(5):
        a0 = 2 * math.pi * k / 5 + 0.4
        sp = []
        for i in range(7):
            t = i / 6
            z = 1.0 + 0.85 * t
            r = (0.34 + 0.2 * t ** 2) * (0.82 if math.sin(a0 + 1.1 * t) > 0 else 1.0) + 0.03
            a = a0 + 1.1 * t
            sp.append(V((math.cos(a) * r, math.sin(a) * r * 0.85, z)))
        R.add('Body', stroke(sp, 0.012), INK, smooth=False)
    # 금줄: twisted straw rope + white paper strips
    rope = [V((math.cos(2 * math.pi * i / 20) * 0.38, math.sin(2 * math.pi * i / 20) * 0.33, 1.2 + 0.035 * math.sin(i * 1.3))) for i in range(21)]
    R.add('Body', bm_tube(rope, 0.045, seg=6, cap=False, twist=1.1), 'M_PaperShade')
    for k in range(7):
        a = math.radians(-160 + k * 23)
        p0 = V((math.cos(a) * 0.42, math.sin(a) * 0.37, 1.17))
        pr = p0 + V((math.cos(a) * 0.02, math.sin(a) * 0.02, -0.26 - 0.06 * (k % 2)))
        zz = [p0, p0.lerp(pr, 0.33) + V((math.cos(a) * 0.03, math.sin(a) * 0.03, 0)), p0.lerp(pr, 0.66) - V((math.cos(a) * 0.02, math.sin(a) * 0.02, 0)), pr]
        R.add('Body', bm_blade(zz, [0.04, 0.045, 0.045, 0.035], thick=0.006, up=(math.cos(a), math.sin(a), 0)), 'M_PageWhite', smooth=False)
    # ---- arms: long branch arms with ball joints, twig fingers, cloth ties (red / blue)
    for s, x in (('L', 1), ('R', -1)):
        sh, el, wr = [V((p[0] * x, p[1], p[2])) for p in (dims['sh'], dims['el'], dims['wr'])]
        R.add('Arm' + s, ball(sh, 0.16, seg=10, rings=7), JOINT)
        ua = bm_tube([sh, sh.lerp(el, 0.5) + V((0.04 * x, 0, 0.03)), el], [0.13, 0.11, 0.1], seg=8, twist=0.4)
        jitter(ua, 0.012, 4, 50 + x)
        R.add('Arm' + s, ua, BARK)
        R.add('ForeArm' + s, ball(el, 0.11, seg=8, rings=6), JOINT)
        fa = bm_tube([el, el.lerp(wr, 0.5) + V((0.02 * x, 0, 0)), wr], [0.095, 0.08, 0.085], seg=8, twist=0.3)
        jitter(fa, 0.01, 4, 60 + x)
        R.add('ForeArm' + s, fa, BARK)
        for k, d in enumerate((V((0.07 * x, -0.08, -0.26)), V((-0.05 * x, -0.13, -0.22)), V((0.0, 0.05, -0.25)), V((0.1 * x, 0.02, -0.18)))):
            tw = bm_tube([wr, wr + d * 0.55, wr + d], [0.055, 0.035, 0.015], seg=5)
            R.add('Hand' + s, tw, BARK)
        # twig sprouting from the elbow with a small leaf clump; on the right arm only drawn in pencil
        tw = [el, el + V((0.2 * x, 0.06, 0.26)), el + V((0.26 * x, 0.1, 0.45))]
        if s == 'L':
            R.add('ForeArm' + s, bm_tube(tw, [0.04, 0.025, 0.01], seg=5), BARK)
            leaf_rosette(R, 'ForeArm' + s, tw[-1] + V((0.02 * x, 0, 0.03)), rnd, n=4, size=0.16, out=V((x, 0, 1)).normalized())
        else:
            R.add('ForeArm' + s, stroke(wobble_line(tw[0], tw[-1], 5, 0.02, 3), 0.01), INK, smooth=False)
            R.add('ForeArm' + s, stroke(ring_pts(tw[-1] + V((0, 0, 0.05)), (0.2, -1, 0.3), 0.15, 12, 0.12, 2), 0.006), PENCIL, smooth=False)
        # 오방색-like cloth ties (painted accent), ragged ends
        cm = RED if s == 'L' else BLUE
        cc = sh.lerp(el, 0.55)
        ring = ring_pts(cc, el - sh, 0.13, 12)
        R.add('Arm' + s, bm_tube(ring, 0.025, seg=5, cap=False, flat=0.5), cm, smooth=False)
        for k in range(2):
            p0 = cc + V((0.1 * x, -0.06, 0.0))
            pts = [p0, p0 + V((0.04 * x, -0.04 - 0.03 * k, -0.15)), p0 + V((0.02 * x, -0.03 - 0.05 * k, -0.32 + 0.06 * k))]
            R.add('Arm' + s, bm_blade(pts, [0.035, 0.038, 0.02], thick=0.006, up=(x, -1, 0)), cm, smooth=False)
    # ---- head: trunk top with heavy brow, deep hole eyes, hanging-root beard
    hb = bm_tube([V((0, 0, 1.9)), V((0, 0.0, 2.15)), V((0, 0.04, 2.42))], [0.56, 0.6, 0.52], seg=14, twist=0.2, flat=0.8, up=(0, 1, 0))
    jitter(hb, 0.03, 2.0, 50)
    hb = subdivide(hb, 1)
    hbv = BVHTree.FromBMesh(hb)
    R.add('Head', hb, BARK)
    for x in (1, -1):
        hit = hbv.ray_cast(V((0.21 * x, -2, 2.2)), V((0, 1, 0)))
        c, n = hit[0], hit[1]
        R.add('Head', oriented_eye(c - n * 0.02, n, (0.105, 0.06, 0.09)), INK)
        brow = [c + V((-0.16 * x, -0.02, 0.06)), c + V((0.0, -0.07, 0.12)), c + V((0.15 * x, -0.03, 0.09))]
        R.add('Head', bm_tube(brow, [0.05, 0.075, 0.04], seg=7), BARK)
    # beard of hanging roots from under the face, ends turn into ink lines
    for k in range(9):
        xx = -0.3 + 0.6 * k / 8 + rnd.uniform(-0.03, 0.03)
        hit = hbv.ray_cast(V((xx, -2, 2.04)), V((0, 1, 0)))
        if hit[0] is None:
            continue
        p0 = hit[0] + V((0, 0.02, 0))
        ln = rnd.uniform(0.22, 0.42) * (1.2 - abs(xx))
        pts = [p0, p0 + V((xx * 0.1, -0.06, -ln * 0.5)), p0 + V((xx * 0.15, -0.05, -ln))]
        R.add('Head', bm_tube(pts, [0.035, 0.025, 0.012], seg=5), BARK)
        R.add('Head', stroke(wobble_line(pts[-1], pts[-1] + V((0, 0, -0.18)), 4, 0.015, k), 0.006), INK, smooth=False)
    # ---- crown: thick branches spreading up and out (wide on top, gaps between clumps)
    tips = []
    for i in range(10):
        a = 2 * math.pi * i / 10 + rnd.uniform(-0.15, 0.15)
        rr = rnd.uniform(0.95, 1.45)
        tips.append(V((math.cos(a) * rr, math.sin(a) * rr * 0.7 + 0.08, rnd.uniform(2.65, 3.0))))
    for i, tp in enumerate(tips):
        st = V((tp.x * 0.2, tp.y * 0.2 + 0.04, 2.35))
        mid = st.lerp(tp, 0.5) + V((0, 0, 0.18))
        unfinished = i in (2, 7)
        if unfinished:   # solid stub, then the branch continues as pencil construction
            torn_limb(R, 'Canopy', 'Canopy', st, tp, 0.14, 0.05, frac=0.45, mat=BARK, lw=0.009, seed=i)
            R.add('Canopy', stroke(ring_pts(tp + V((0, 0, 0.12)), (0.2, 0.1, 1), 0.38, 14, 0.15, i), 0.008), PENCIL, smooth=False)
            R.add('Canopy', stroke(ring_pts(tp + V((0.08, 0, 0.16)), (0.3, -0.2, 1), 0.3, 12, 0.2, i + 3), 0.007), PENCIL, smooth=False)
            continue
        br = bm_tube([st, mid, tp], [0.15, 0.1, 0.045], seg=7)
        jitter(br, 0.025, 3, 60 + i)
        R.add('Canopy', br, BARK)
        if i % 3 == 0:
            R.add('Canopy', ball(mid, 0.09, seg=6, rings=4), JOINT)
        leaf_rosette(R, 'Canopy', tp + V((0, 0, 0.04)), rnd, n=7, size=0.3, out=V((tp.x, tp.y, 0.6)).normalized())
        out = V((tp.x, tp.y, 0)).normalized()
        for j in range(2):
            p0 = tp + V((0, 0, 0.05 * j))
            p1 = p0 + out * rnd.uniform(0.25, 0.45) + V((rnd.uniform(-0.12, 0.12), 0, rnd.uniform(0.12, 0.35)))
            R.add('Canopy', stroke(wobble_line(p0, p1, 4, 0.025, i * 2 + j), 0.008), INK, smooth=False)
    puppet_meta(R, dims, 3.0, (0, -0.02, 2.15), 0.55, (0, 0, 1.45), 0.42, kind='tree', foot=(0.5, 0.4, 0.15))
    R.meta['rest_pose'] = {'B.ArmL.z': 8.0, 'B.ArmR.z': -8.0, 'B.ForeArmL.x': -12.0, 'B.ForeArmR.x': -12.0, 'B.Body.x': 4.0, 'B.Head.x': 3.0}
    R.meta['toe'] = 0.3
    R.meta['heel'] = 0.15
    D = A.Dims(R)
    R.clips.append(('Idle',) + A.c_idle(R, D, 4.0))
    R.clips.append(('Walk',) + A.locomotion(R, D, 2.2, 24, stance=0.55, lift=0.12, bob=0.05, lean=5, arm=14, yaw=6,
                                            roll=4, elbow=10, crouch=0.04, th_strike=0.0, th_off=0.0, head_bob=1.5))
    R.meta['speeds'] = {'Walk': 2.2}
    common_gestures(R, D, beckon=False, lookback=False, gather=False, sit=False, reach=False, kneel=True)
    R.clips.append(('Greet',) + A.c_greet(R, D))
    R.clips.append(('StandSway',) + A.c_standsway(R, D))
    return R


# =====================================================================================  VILLAGERS (one shared body) + SILHOUETTES
VDIMS = dict(hip=(0.085, 0, 0.64), knee=(0.09, -0.008, 0.37), ankle=(0.092, 0, 0.068),
             sh=(0.165, 0, 1.0), el=(0.19, 0.0, 0.8), wr=(0.2, 0, 0.61), r_leg=0.038, r_arm=0.032, hand=0.085, scale=1.3)


def villager(name, head, paint, unfinished, sil=False):
    R = RigChar(name)
    d = VDIMS
    puppet_bones(R, d, head_pivot=(0, 0, 1.075), waist=(0, 0, 0.7), hips=(0, 0, 0.665))
    W = 'M_Silhouette' if sil else WOOD
    J = 'M_Silhouette' if sil else JOINT
    top, bot = paint if not sil else (None, None)
    # pelvis block + barrel torso
    pel = bm_box((0, 0, 0.665), (0.25, 0.16, 0.13))
    pel = L.bevel(pel, 0.04, 2, 40)
    R.add('Hips', pel, bot or W, smooth=False, face_mat=None if sil else paint_below(0.62, WOOD, amp=0.015, freq=16, seed=1))
    tor = bm_lathe([(0.0, 0.72), (0.13, 0.725), (0.17, 0.8), (0.185, 0.9), (0.178, 0.98), (0.13, 1.035), (0.0, 1.045)], seg=14, sy=0.74)
    tor = subdivide(tor, 2 if not sil else 1)
    if sil:
        R.add('Body', tor, W)
    else:
        edge = 0.86
        if unfinished == 'torso':   # front plate carved, back half of the barrel still a pencil construction
            pass
        brush(R, 'Body', tor, edge, top, n=7, ln=0.1, w=0.014, seed=2)
        R.add('Body', tor, WOOD, face_mat=paint_above(edge, top, amp=0.012, freq=16, seed=2))
        if bot:
            brush(R, 'Hips', bm_box((0, 0, 0.665), (0.25, 0.16, 0.13)), 0.62, bot, n=6, ln=0.05, w=0.02, seed=3)
    R.add('Body', ball((0, 0, 0.705), 0.045, seg=10, rings=7), J)
    R.add('Head', capsule((0, 0, 1.04), (0, -0.005, 1.1), 0.026, 0.024, seg=7), W)
    R.add('Head', ball((0, 0, 1.075), 0.03, seg=8, rings=6), J)
    # limbs (shared), with per-variant unfinished parts
    skip_fore = (unfinished == 'forearmL', unfinished == 'armR')
    puppet_limbs(R, d, mat=W, jmat=J, hands=('mitten', 'mitten'), foot=(0.15, 0.08, 0.06),
                 sleeve=None if sil else (top, 0.5, 1.3), shorts=None if sil else (bot, 0, 0.55, 1.35),
                 skip_fore=skip_fore, ink_shin=(False, 'skip' if unfinished == 'shinR' else False))
    if unfinished == 'forearmL':
        el, wr = V((0.19, 0, 0.8)), V((0.2, 0, 0.61))
        torn_limb(R, 'ForeArmL', 'ForeArmL', el - V((0, 0, 0.02)), wr, 0.028, 0.023, frac=0.45, lw=0.004, seed=11)
        ink_hand(To(R, 'HandL'), wr, (wr - el).normalized(), ln=0.1, side=1, r=0.0035)
    if unfinished == 'armR':   # whole forearm + hand only drawn; upper arm torn at the elbow
        el, wr = V((-0.19, 0, 0.8)), V((-0.2, 0, 0.61))
        sketch_cyl(R, 'ForeArmR', el, wr, 0.028, 0.023, lw=0.004, rings=3, longs=4, seed=13)
        ink_hand(To(R, 'HandR'), wr, (wr - el).normalized(), ln=0.1, side=-1, r=0.0035)
    if unfinished == 'shinR':   # shin torn below the knee, the rest only drawn; the foot is solid again
        kn, an = V((-0.09, -0.008, 0.37)), V((-0.092, 0, 0.068))
        torn_limb(R, 'ShinR', 'ShinR', kn - V((0, 0, 0.02)), an + V((0, 0, 0.01)), 0.033, 0.027, frac=0.38, lw=0.004, seed=21)
    # heads
    hp = V((0, 0, 1.075))
    if head == 'egg':
        hc = V((0, -0.01, 1.255))
        hc = V((0, -0.012, 1.285))
        hb = faceted_head('egg', hc, (0.14, 0.125, 0.2), seed=16)
        eyes = [(0.05, 0.035, 0.034, 'hole'), (-0.052, 0.0, 0.018, 'slot')]
        tuft = [(RED, (-0.05, 0.0, 0.14), 0.11), (BLUE, (-0.02, 0.02, 0.15), 0.08)]
        hr = 0.15
    elif head == 'box':
        hc = V((0, -0.012, 1.225))
        hb = faceted_head('box', hc, (0.16, 0.14, 0.135), seed=26)
        rot(hb, 'Y', -8, hc)
        eyes = [(0.068, 0.04, 0.032, 'hole'), (-0.058, -0.014, 0.038, 'hole'), (0.024, -0.07, 0.019, 'hole')]
        tuft = [(RED, (-0.08, 0.0, 0.11), 0.08)]
        hr = 0.14
    else:   # bean, tilted, drawn ring eye
        hc = V((0.01, -0.03, 1.22))
        hb = faceted_head('bean', hc, (0.18, 0.13, 0.135), seed=37)
        rot(hb, 'Y', -14, hc)
        eyes = [(0.06, 0.022, 0.034, 'hole'), (-0.06, 0.014, 0.036, 'ring')]
        tuft = [(BLUE, (0.0, 0.02, 0.1), 0.09)]
        hr = 0.14
    hbv = BVHTree.FromBMesh(hb)
    R.add('Head', hb, W, smooth=False, face_mat=None if sil else paint_above(hc.z + 0.07, top, amp=0.02, freq=14, seed=17))
    if not sil:
        for nm, (dx, dz, r, st) in zip(('a', 'b', 'c'), eyes):
            hit = hbv.ray_cast(V((hc.x + dx, -3, hc.z + dz)), V((0, 1, 0)))
            if hit[0] is None:
                continue
            c, n = hit[0], hit[1]
            if st == 'ring':
                ring = [c + n * 0.003 + V((math.cos(2 * math.pi * i / 14) * r, 0, math.sin(2 * math.pi * i / 14) * r * 1.05)) for i in range(15)]
                R.add('Head', stroke(ring, 0.005, taper=False), INK, smooth=False)
                R.add('Head', oriented_eye(c + n * 0.002, n, (r * 0.3, 0.004, r * 0.32)), INK)
            else:
                R.add('Head', oriented_eye(c - n * 0.004, n, (r, 0.012, r * (2.0 if st == 'slot' else 1.15))), INK)
        for k, (m, off, ln) in enumerate(tuft):
            p0 = hc + V(off)
            pts = [p0, p0 + V((0.01, 0.02, ln * 0.5)), p0 + V((0.03, 0.05, ln))]
            R.add('Head', bm_blade(pts, [ln * 0.18, ln * 0.2, ln * 0.04], thick=ln * 0.05, up=(0, 1, 0)), m, smooth=False)
        if unfinished == 'headback':
            pass
    puppet_meta(R, d, 1.48 if head == 'egg' else 1.37, hc, hr * 1.18, (0, 0, 0.88), 0.18, foot=(0.15, 0.08, 0.06))
    if unfinished == 'armR':
        R.meta['hand'] = 'L'
    if unfinished == 'shinR':   # stooped elder posture is part of the rest pose of every clip
        R.meta['rest_pose'] = {'B.ArmL.z': 5.0, 'B.ArmR.z': -5.0, 'B.ForeArmL.x': -18.0, 'B.ForeArmR.x': -14.0,
                               'B.Body.x': 16.0, 'B.Head.x': -12.0, 'B.ArmL.x': -8.0, 'B.ArmR.x': -6.0}
    villager_clips(R)
    return R


def villager_clips(R):
    D = A.Dims(R)

    def wobble(ch, t, ph, cL, b_):
        ch['B.Head.z'] = ch.get('B.Head.z', 0) + 3 * cL
        return ch
    R.clips.append(('Idle',) + A.c_idle(R, D, 3.2))
    R.clips.append(('Walk',) + A.locomotion(R, D, 2.2, 16, stance=0.34, lift=0.07, bob=0.025, lean=5, arm=20, yaw=7,
                                            roll=4, elbow=14, crouch=0.0, extra=wobble))
    R.meta['speeds'] = {'Walk': 2.2}
    common_gestures(R, D, beckon=True, lookback=False, gather=True, sit=True, reach=True, kneel=True)


def build_villager_a():
    return villager('Villager_A', 'egg', (BLUE, RED), 'forearmL')


def build_villager_b():
    return villager('Villager_B', 'box', (RED, BLUE), 'armR')


def build_villager_c():
    return villager('Villager_C', 'bean', (BLUE, RED), 'shinR')


def build_silhouette_a():
    return villager('Silhouette_A', 'egg', (None, None), None, sil=True)


def build_silhouette_b():
    return villager('Silhouette_B', 'box', (None, None), None, sil=True)


# =====================================================================================  MOTHER
def build_mother():
    """Mother: tall pear-bellied puppet (~2 m), small head with one slot eye, long cloth in the right hand."""
    R = RigChar('Mother')
    d = dict(hip=(0.13, 0.0, 0.5), knee=(0.14, -0.01, 0.28), ankle=(0.145, 0, 0.065),
             sh=(0.19, 0, 1.42), el=(0.29, -0.03, 1.1), wr=(0.31, -0.05, 0.8), r_leg=0.045, r_arm=0.036, hand=0.1, scale=2.0)
    puppet_bones(R, d, head_pivot=(0, -0.02, 1.6), waist=(0, 0, 0.6), hips=(0, 0, 0.52))
    R.bone('Cloth', 'HandR', (-0.32, -0.06, 0.75))
    # pear body: soft-skinned between Hips (bottom) and Body (top)
    pear = bm_lathe([(0.0, 0.42), (0.2, 0.44), (0.33, 0.58), (0.37, 0.78), (0.335, 1.0), (0.25, 1.2), (0.17, 1.38), (0.12, 1.5), (0.0, 1.56)], seg=18, sy=0.88)
    deform(pear, lambda c: V((c.x, c.y - 0.13 * math.exp(-((c.z - 0.8) / 0.26) ** 2) * max(0.0, -c.y / 0.33), c.z)))
    pear = subdivide(pear, 1)
    jitter(pear, 0.008, 4, 52)
    pw = blend_w(lambda c: c.z, 'Hips', 'Body', 0.58, 0.8)
    for mat, z, down, sd in ((BLUE, 1.08, True, 53), (RED, 0.66, False, 54)):
        rnd = random.Random(sd)
        bvh = BVHTree.FromBMesh(pear)
        for k in range(10):
            a = 2 * math.pi * (k + rnd.uniform(-0.4, 0.4)) / 10
            ln = rnd.choice((0.08, 0.13, 0.18, 0.25))
            pts, nr = [], []
            for t in range(7):
                zz = z + (-1 if down else 1) * (ln * t / 6 - 0.008)
                dd = V((math.cos(a), math.sin(a), 0))
                hit = bvh.ray_cast(V((0, 0, zz)) + dd * 3, -dd)
                if hit[0] is None:
                    break
                pts.append(hit[0] + hit[1] * 0.0025)
                nr.append(hit[1])
            if len(pts) > 2:
                ww = [0.045 * f for f in (1, 0.95, 0.85, 0.7, 0.5, 0.3, 0.06)][:len(pts)]
                R.add(pw, bm_blade(pts, ww, thick=0.0015, up=tuple(nr[len(nr) // 2])), BRUSH[mat], smooth=False)
    R.add(pw, pear, WOOD, face_mat=L.chain(paint_above(1.08, BLUE, amp=0.02, freq=9, seed=53), paint_below(0.66, RED, amp=0.025, freq=8, seed=54)))
    # the back of the belly was never finished: a ragged pencil-drawn hatch zone (construction ellipses) on the back
    for k, (z, r) in enumerate(((0.62, 0.34), (0.8, 0.37), (0.98, 0.33))):
        pts = ring_pts(V((0, 0.02, z)), (0, 0, 1), r * 1.04, 16, 0.03, k, math.radians(20), 0.38)
        R.add('Body' if z > 0.75 else 'Hips', stroke(pts, 0.004), PENCIL, smooth=False)
    R.add('Body', ball((0, 0, 1.58), 0.045, seg=8, rings=6), JOINT)
    R.add('Head', capsule((0, -0.01, 1.55), (0, -0.04, 1.66), 0.032, 0.028, seg=7), WOOD)
    puppet_limbs(R, d, hands=('none', 'mitten'), foot=(0.17, 0.095, 0.065), sleeve=(BLUE, 0.5, 1.3), skip_fore=(True, False))
    # left forearm torn off and continued as pencil, ink hand
    el, wr = V((0.29, -0.03, 1.1)), V((0.31, -0.05, 0.8))
    torn_limb(R, 'ForeArmL', 'ForeArmL', el - V((0, 0, 0.02)), wr, 0.031, 0.026, frac=0.5, lw=0.0045, seed=61)
    ink_hand(To(R, 'HandL'), wr, (wr - el).normalized(), ln=0.13, side=1, r=0.004)
    # head: small tall egg, one long slot eye, blue paint cap + tuft
    hc = V((0, -0.06, 1.8))
    hb = faceted_head('egg', hc, (0.11, 0.105, 0.16), seed=57)
    hbv = BVHTree.FromBMesh(hb)
    R.add('Head', hb, WOOD, smooth=False, face_mat=paint_above(1.88, BLUE, amp=0.02, freq=14, seed=58))
    hit = hbv.ray_cast(V((0.0, -3, 1.82)), V((0, 1, 0)))
    R.add('Head', oriented_eye(hit[0] - hit[1] * 0.004, hit[1], (0.02, 0.012, 0.05)), INK)
    for m, off, ln in ((BLUE, (-0.04, 0.02, 0.13), 0.1), (RED, (-0.01, 0.03, 0.14), 0.07)):
        p0 = hc + V(off)
        pts = [p0, p0 + V((0.01, 0.02, ln * 0.5)), p0 + V((0.03, 0.05, ln))]
        R.add('Head', bm_blade(pts, [ln * 0.18, ln * 0.2, ln * 0.04], thick=ln * 0.05, up=(0, 1, 0)), m, smooth=False)
    # cloth hanging from the right hand (own bone, sways)
    h0 = V((-0.32, -0.06, 0.75))
    pts = [h0, h0 + V((0.03, -0.04, -0.2)), h0 + V((-0.01, -0.02, -0.4)), h0 + V((0.02, 0.03, -0.55)), h0 + V((-0.03, 0.0, -0.62))]
    c = bm_blade(pts, [0.06, 0.12, 0.13, 0.12, 0.1], thick=0.012, up=(0, 1, 0.1))
    c = subdivide(c, 1)
    deform(c, lambda q: q + V((0, 0.03 * math.sin((q.z - h0.z) * 9), 0)))
    R.add('Cloth', c, 'M_Paper')
    for k in range(3):
        e0 = pts[-1] + V((-0.07 + 0.07 * k, 0, 0.0))
        R.add('Cloth', stroke([e0, e0 + V((0.005 * k, 0.0, -0.07 - 0.02 * k))], 0.005), INK, smooth=False)
    puppet_meta(R, d, 2.0, hc, 0.16, (0, 0, 0.85), 0.37, foot=(0.17, 0.095, 0.065))
    R.meta['rest_pose'] = {'B.ArmL.z': 8.0, 'B.ArmR.z': -8.0, 'B.ForeArmL.x': -14.0, 'B.ForeArmR.x': -20.0, 'B.Head.x': 6.0}
    D = A.Dims(R)

    def sway(ch, t, ph, cL, b_):
        ch['B.Cloth.x'] = 8 + 10 * b_
        ch['B.Cloth.z'] = 6 * cL
        ch['B.Body.z'] = ch.get('B.Body.z', 0) + 3 * cL   # pear waddle
        return ch
    R.clips.append(('Idle',) + A.c_idle(R, D, 3.4))
    R.clips.append(('Walk',) + A.locomotion(R, D, 2.2, 14, stance=0.32, lift=0.06, bob=0.03, lean=4, arm=16, yaw=6,
                                            roll=6, elbow=16, crouch=0.02, extra=sway))
    R.meta['speeds'] = {'Walk': 2.2}
    common_gestures(R, D, beckon=True, lookback=False, gather=True, sit=True, reach=True, kneel=True)
    return R


# =====================================================================================  HERO (human child traveler, bluebird concept)
L.MATS.update({
    'M_Skin':         ('F1C7A2', 'C9946F', True, 'painted', {'note': 'hero skin (the only fully coloured being)'}),
    'M_Hair':         ('2A3157', '171C37', True, 'painted', {'note': 'hero hair: blue-black like the bluebird head'}),
    'M_HeroShirt':    ('E8EBF1', 'B1B9CA', True, 'painted', {'note': 'hero loose shirt: grey-white like the bluebird belly'}),
    'M_HeroTrousers': ('343A52', '1F2438', True, 'painted', {'note': 'hero dark trousers'}),
})
NEW_MATS.update({k: L.MATS[k] for k in ('M_Skin', 'M_Hair', 'M_HeroShirt', 'M_HeroTrousers')})


def seg_w(a, b, bone_a, bone_b, blend):
    """Weights along a limb: bone_a before joint b, bone_b after it, blended over +-blend metres."""
    a, b = V(a), V(b)
    d = (b - a).normalized()

    def fn(co):
        t = (co - b).dot(d)
        w = A.smooth((t + blend) / (2 * blend))
        return {bone_a: 1 - w, bone_b: w}
    return fn


def build_hero():
    R = RigChar('Hero_Bluebird')
    SKIN, HAIR, SHIRT, TROU, NAVY, COB = 'M_Skin', 'M_Hair', 'M_HeroShirt', 'M_HeroTrousers', 'M_CapNavy', 'M_Bluebird'
    d = dict(hip=(0.085, 0, 0.6), knee=(0.09, -0.012, 0.335), ankle=(0.095, 0, 0.078),
             sh=(0.155, 0.0, 0.845), el=(0.18, 0.005, 0.67), wr=(0.19, -0.01, 0.51), r_leg=0.055, r_arm=0.045, hand=0.07, scale=1.25)
    puppet_bones(R, d, head_pivot=(0, 0, 0.885), waist=(0, 0, 0.66), hips=(0, 0, 0.62))
    R.bone('Cape', 'Body', (0, 0.06, 0.89))
    rnd = random.Random(5)
    bw = blend_w(lambda c: c.z, 'Hips', 'Body', 0.63, 0.72)

    # ---------------- torso: loose white shirt, belt, trousers seat
    shirt = bm_lathe([(0.0, 0.6), (0.13, 0.61), (0.15, 0.66), (0.148, 0.72), (0.152, 0.78), (0.15, 0.83), (0.11, 0.875), (0.05, 0.895), (0.0, 0.9)],
                     seg=18, sy=0.78)
    deform(shirt, lambda c: c + V((0, -0.012 * math.exp(-((c.z - 0.7) / 0.06) ** 2), 0)))   # slight blouse over the belt
    R.add(bw, shirt, SHIRT)
    # collar points + placket
    for x in (1, -1):
        p0 = V((0.012 * x, -0.1, 0.885))
        R.add('Body', bm_blade([p0, p0 + V((0.03 * x, -0.012, -0.03)), p0 + V((0.045 * x, -0.0, -0.045))], [0.014, 0.018, 0.004],
                               thick=0.006, up=(0, -1, 0.3)), SHIRT, smooth=False)
    belt = bm_tube(ring_pts(V((0, 0, 0.635)), (0, 0, 1), 0.142, 18), 0.02, seg=4, cap=False, flat=0.45, up=(0, 0, 1))
    deform(belt, lambda c: V((c.x, c.y * 0.8, c.z)))
    R.add('Hips', belt, 'M_Leather', smooth=False)
    bk = bm_box((0, -0.115, 0.635), (0.035, 0.012, 0.03))
    R.add('Hips', L.bevel(bk, 0.005, 1, 40), 'M_Brass', smooth=False)
    seat = bm_sphere((0, 0.005, 0.59), (0.135, 0.105, 0.075), seg=14, rings=8)
    R.add('Hips', seat, TROU)
    # satchel strap: right shoulder -> left hip, bag on the left hip
    sb = BVHTree.FromBMesh(shirt)
    strap = []
    cen = V((0, 0, 0.75))
    nrm = V((0.62, 0.0, 1.0)).normalized()
    ax1 = V((0, 1, 0))
    ax2 = nrm.cross(ax1).normalized()
    for i in range(33):
        a = 2 * math.pi * i / 32
        dd = (ax1 * math.cos(a) + ax2 * math.sin(a)).normalized()
        h = sb.ray_cast(cen + dd * 0.6, -dd)
        if h[0] is not None:
            strap.append(h[0] + h[1] * 0.01)
    R.add(bw, bm_tube(strap, 0.016, seg=4, cap=False, flat=0.35, up=(0, 0, 1)), 'M_Leather', smooth=False)
    bag_c = V((0.175, -0.07, 0.6))
    for sz, off, m in (((0.06, 0.17, 0.15), (0, 0, 0), 'M_Leather'), ((0.068, 0.175, 0.075), (0.004, 0, 0.05), 'M_Leather'),
                       ((0.012, 0.035, 0.04), (0.04, -0.01, 0.03), 'M_Brass')):
        bx = bm_box((0, 0, 0), sz)
        bx = L.bevel(bx, min(sz) * 0.3, 2, 40)
        rot(bx, 'Z', 18)
        move(bx, bag_c + V(off))
        R.add('Hips', bx, m, smooth=False)

    # ---------------- legs: loose dark trousers tucked into chunky boots
    for s, x in (('L', 1), ('R', -1)):
        hip, knee, ank = [V((p[0] * x, p[1], p[2])) for p in (d['hip'], d['knee'], d['ankle'])]
        tr = bm_tube([hip + V((0, 0, 0.03)), hip.lerp(knee, 0.5), knee, knee.lerp(ank, 0.45)], [0.068, 0.064, 0.056, 0.058], seg=12)
        R.add(seg_w(hip, knee, 'Leg' + s, 'Shin' + s, 0.04), tr, TROU)
        shaft = bm_lathe([(0.052, 0.07), (0.058, 0.1), (0.062, 0.2), (0.066, 0.215), (0.06, 0.222)], seg=12, center=(ank.x, ank.y + 0.004, 0))
        R.add('Shin' + s, shaft, 'M_Leather', smooth=False)
        foot = bm_box((0, 0, 0), (0.1, 0.2, 0.085))
        foot = L.bevel(foot, 0.032, 2, 40)
        deform(foot, lambda c: c + V((0, 0, -0.012 * max(0.0, (-c.y - 0.04) / 0.06) * (c.z > 0))))
        move(foot, (ank.x, -0.045, 0.05))
        R.add('Foot' + s, foot, 'M_Leather')
        sole = bm_box((ank.x, -0.045, 0.011), (0.106, 0.205, 0.022))
        R.add('Foot' + s, L.bevel(sole, 0.007, 1, 40), 'M_Beak', smooth=False)
        R.add('Foot' + s, L.bevel(bm_box((ank.x + 0.05 * x, -0.03, 0.075), (0.008, 0.03, 0.026)), 0.003, 1, 40), 'M_Brass', smooth=False)
        R.add('Shin' + s, bm_tube(ring_pts(V((ank.x, ank.y + 0.004, 0.2)), (0, 0, 1), 0.064, 12), 0.008, seg=4, cap=False), 'M_Leather', smooth=False)

    # ---------------- arms: puffy sleeves with cuffs, skin hands with thumbs
    for s, x in (('L', 1), ('R', -1)):
        sh, el, wr = [V((p[0] * x, p[1], p[2])) for p in (d['sh'], d['el'], d['wr'])]
        sl = bm_tube([sh + V((-0.02 * x, 0, 0.02)), sh.lerp(el, 0.5), el, el.lerp(wr, 0.55), wr + (wr - el).normalized() * 0.01],
                     [0.052, 0.048, 0.045, 0.054, 0.04], seg=12)
        R.add(seg_w(sh, el, 'Arm' + s, 'ForeArm' + s, 0.035), sl, SHIRT)
        cuff = bm_tube(ring_pts(wr, el - wr, 0.04, 12), 0.009, seg=4, cap=False)
        R.add('ForeArm' + s, cuff, SHIRT, smooth=False)
        dd = (wr - el).normalized()
        palm = bm_sphere((0, 0, 0), (0.026, 0.036, 0.046), seg=10, rings=7)
        L.xform(palm, dd.to_track_quat('-Z', 'Y').to_matrix().to_4x4())
        move(palm, wr + dd * 0.045)
        R.add('Hand' + s, palm, SKIN)
        th = bm_tube([wr + dd * 0.02 + V((0, -0.02, 0)), wr + dd * 0.045 + V((0, -0.04, 0))], [0.012, 0.01], seg=6)
        R.add('Hand' + s, th, SKIN)

    # ---------------- neck + head (big, readable face, cap pushed up)
    R.add(blend_w(lambda c: c.z, 'Body', 'Head', 0.875, 0.9), bm_tube([V((0, 0, 0.84)), V((0, -0.005, 0.93))], [0.042, 0.04], seg=10), SKIN)
    hc = V((0, -0.012, 1.035))
    hr = (0.142, 0.135, 0.152)
    h = bm_sphere(hc, hr, seg=20, rings=14)
    deform(h, lambda c: c + V((0, 0, 0)) if c.z > hc.z else V((c.x * (1 - 0.18 * ((hc.z - c.z) / hr[2]) ** 2), c.y, c.z)))   # softer jaw
    hb = BVHTree.FromBMesh(h)
    R.add('Head', h, SKIN)
    for x in (1, -1):   # ears
        e = bm_sphere(hc + V((0.138 * x, 0.01, -0.01)), (0.018, 0.026, 0.034), seg=8, rings=5)
        R.add('Head', e, SKIN)
    # hair shell: blue-black, forehead line high so the eyes stay clear, longer at the back, crest tuft
    hs = bm_sphere(hc, (hr[0] * 1.07, hr[1] * 1.08, hr[2] * 1.06), seg=20, rings=14)

    def hairline(c):
        rel = c - hc
        front = max(0.0, -rel.y / hr[1])            # 1 at the face
        side = abs(rel.x) / hr[0]
        line = 0.055 * front - 0.03 * side * (1 - front) - 0.11 * (1 - front) * (rel.y > 0)
        return rel.z > line + 0.012 * math.sin(c.x * 60)
    dead = [f for f in hs.faces if not hairline(f.calc_center_median())]
    L.bmesh.ops.delete(hs, geom=dead, context='FACES')
    R.add('Head', hs, HAIR)
    for k, (fx, ln, ang) in enumerate(((-0.06, 0.05, 20), (-0.015, 0.06, 5), (0.035, 0.055, -15), (0.075, 0.045, -28))):
        p0 = hc + V((fx, -0.11, 0.1))
        dd = V((math.sin(math.radians(ang)) * 0.6, -0.45, -0.75)).normalized()
        R.add('Head', bm_blade([p0, p0 + dd * ln * 0.5, p0 + dd * ln], [0.022, 0.02, 0.003], thick=0.012, up=(0, -1, 0.2)), HAIR, smooth=False)
    for k, (sx, ln) in enumerate(((-0.03, 0.08), (0.0, 0.1), (0.03, 0.075))):   # bluebird crest tuft at the back
        p0 = hc + V((sx, 0.11, 0.08))
        R.add('Head', bm_blade([p0, p0 + V((sx * 0.4, 0.06, 0.04)), p0 + V((sx, ln, 0.02))], [0.018, 0.02, 0.003], thick=0.012, up=(1, 0, 0)), HAIR, smooth=False)
    # face: big dark eyes with highlights, small brows, button nose, small mouth
    for x in (1, -1):
        dd = V((0.38 * x, -1.0, -0.06)).normalized()
        hit = hb.ray_cast(hc + dd * 0.5, -dd)
        c, n = hit[0], hit[1]
        R.add('Head', oriented_eye(c - n * 0.004, n, (0.024, 0.012, 0.034)), INK)
        tang = n.cross(V((0, 0, 1))).normalized()
        sp = bm_sphere((0, 0, 0), (0.008, 0.005, 0.009), seg=6, rings=4)
        move(sp, c + n * 0.008 + V((0, 0, 0.012)) - tang * 0.007 * x)
        R.add('Head', sp, 'M_EyeShine')
        b0 = c + V((-0.022 * x, -0.004, 0.05))
        b1 = c + V((0.024 * x, 0.004, 0.054))
        R.add('Head', bm_blade([b0, b0.lerp(b1, 0.5) + V((0, -0.003, 0.004)), b1], [0.004, 0.006, 0.002], thick=0.006, up=tuple(n)), HAIR, smooth=False)
    hit = hb.ray_cast(hc + V((0, -0.5, -0.03)), V((0, 1, 0)))
    R.add('Head', bm_sphere(hit[0] + V((0, -0.006, 0)), (0.014, 0.012, 0.012), seg=8, rings=5), SKIN)
    hit = hb.ray_cast(hc + V((0, -0.5, -0.075)), V((0, 1, 0)))
    m0 = hit[0] + hit[1] * 0.002
    R.add('Head', stroke([m0 + V((-0.02, 0.004, 0.004)), m0 + V((0, 0, -0.002)), m0 + V((0.02, 0.004, 0.004))], 0.0035, taper=True), INK, smooth=False)
    # newsboy cap pushed up and back: face fully visible, brim tipped up, brass button, blue feather + tuft
    capc = hc + V((0.008, 0.028, 0.088))
    tilt = -17
    prof = [(0.0, 0.1), (0.07, 0.098), (0.13, 0.088), (0.172, 0.064), (0.182, 0.034), (0.168, 0.008), (0.15, 0.0)]
    crown = bm_lathe(prof, seg=22, center=capc, sx=1.0, sy=1.06, cap_bottom=True)
    deform(crown, lambda co: co + V((0, -0.03 * max(0, co.z - capc.z - 0.05) / 0.05, 0)))
    rot(crown, 'X', tilt, capc)
    R.add('Head', crown, NAVY)
    band = bm_tube([capc + V((math.cos(2 * math.pi * i / 20) * 0.176, math.sin(2 * math.pi * i / 20) * 0.184, 0.004)) for i in range(21)],
                   0.012, seg=5, cap=False)
    rot(band, 'X', tilt, capc)
    R.add('Head', band, NAVY, smooth=False)
    brim = []
    for i in range(9):
        aa = math.radians(-145 + 110 * i / 8)
        brim.append(capc + V((math.cos(aa) * 0.18, math.sin(aa) * 0.18, 0.0)))
    bw = [0.01, 0.03, 0.043, 0.05, 0.052, 0.05, 0.043, 0.03, 0.01]
    br = bm_blade(brim, bw, thick=0.009, up=(0, 0, 1))
    deform(br, lambda co: co + V((0, -0.025 * max(0, -(co.y - capc.y) - 0.15) / 0.06, -0.018 * max(0, -(co.y - capc.y) - 0.15) / 0.06)))
    rot(br, 'X', tilt, capc)
    R.add('Head', br, NAVY, smooth=False)
    btn = bm_sphere(capc + V((0, 0, 0.088)), (0.016, 0.016, 0.009), seg=8, rings=4)
    rot(btn, 'X', tilt, capc)
    R.add('Head', btn, 'M_Brass')
    sbtn = bm_sphere(capc + V((0.17, -0.07, 0.02)), (0.012, 0.012, 0.012), seg=6, rings=4)
    rot(sbtn, 'X', tilt, capc)
    R.add('Head', sbtn, 'M_Brass')
    for k, (dz, ln, m) in enumerate(((0.0, 0.11, BLUE_), (0.012, 0.085, 'M_BluebirdBelly'))):
        p0 = capc + V((0.175, -0.06, 0.03 + dz))
        pts = [p0, p0 + V((0.025, 0.04, ln * 0.55)), p0 + V((0.03, 0.08, ln))]
        fb = bm_blade(pts, [0.012, 0.018, 0.003], thick=0.008, up=(1, 0, 0))
        rot(fb, 'X', tilt, capc)
        R.add('Head', fb, m, smooth=False)

    # ---------------- short shoulder cape: navy outside, cobalt lining, open in front, brass clasp
    rows = [(0.705, 0.13), (0.69, 0.175), (0.665, 0.212), (0.635, 0.232), (0.603, 0.24)]
    cols = 22
    o_b = L.bmesh.new()
    gso, gsi = [], []
    for ri, (z, r) in enumerate(rows):
        ro, rin = [], []
        for j in range(cols + 1):
            a = math.radians(-90 + 36 + (360 - 72) * j / cols)
            d = V((math.cos(a), math.sin(a), 0))
            back = max(0.0, d.y)
            zz = z - (0.035 * back * (ri / (len(rows) - 1)) ** 1.2)
            if ri == len(rows) - 1:
                zz += 0.012 * math.sin(j * 1.7)   # wavy hem
            rr = r * (1.0 + 0.05 * back)
            p = V((d.x * rr * 1.08, d.y * rr * 0.98, zz))
            ro.append(o_b.verts.new(p))
            rin.append(o_b.verts.new(p - V((d.x, d.y, 0.0)) * 0.007 + V((0, 0, 0.002))))
        gso.append(ro)
        gsi.append(rin)
    lin_faces = []
    for ri in range(len(rows) - 1):
        for j in range(cols):
            o_b.faces.new((gso[ri][j], gso[ri][j + 1], gso[ri + 1][j + 1], gso[ri + 1][j]))
            lin_faces.append(o_b.faces.new((gsi[ri][j], gsi[ri + 1][j], gsi[ri + 1][j + 1], gsi[ri][j + 1])))
    for j in range(cols):   # hem rim + collar rim
        o_b.faces.new((gso[-1][j], gso[-1][j + 1], gsi[-1][j + 1], gsi[-1][j]))
        o_b.faces.new((gso[0][j + 1], gso[0][j], gsi[0][j], gsi[0][j + 1]))
    for ri in range(len(rows) - 1):   # front opening edges
        o_b.faces.new((gso[ri][0], gso[ri + 1][0], gsi[ri + 1][0], gsi[ri][0]))
        o_b.faces.new((gso[ri + 1][-1], gso[ri][-1], gsi[ri][-1], gsi[ri + 1][-1]))
    o_b.normal_update()
    lining_centers = [f.calc_center_median().copy() for f in lin_faces]
    o_b = subdivide(o_b, 1)
    L.bmesh.ops.recalc_face_normals(o_b, faces=o_b.faces)

    def cape_mat(c, n):
        rad = V((c.x, c.y, 0))
        if rad.length > 1e-6 and n.dot(rad.normalized()) < -0.2:
            return BLUE_
        return None
    capew = blend_w(lambda c: -c.z, 'Body', 'Cape', -0.69, -0.63)
    R.add(capew, o_b, NAVY, smooth=True, face_mat=cape_mat)
    clasp = bm_sphere((0.0, -0.165, 0.672), (0.018, 0.011, 0.018), seg=8, rings=5)
    R.add('Body', clasp, 'M_Brass')

    # ---------------- meta + contacts
    R.meta.update(height=1.07, kind='bird', toe=0.12, heel=0.045, head_r=0.19, knee_r=0.022,
                  head_c=tuple(hc - V((0, -0.005, 0.71))), arm_out=7.0)
    from ouat_rig import to_rig
    R.meta['head_c'] = tuple(to_rig(hc - V((0, -0.005, 0.71))))
    R.meta['height'] = 1.08
    R.meta['rest_pose'] = {'B.ArmL.z': 7.0, 'B.ArmR.z': -7.0, 'B.ForeArmL.x': -8.0, 'B.ForeArmR.x': -8.0}
    humanoid_contacts(R, sole_y=0.075, toe=0.125, heel=0.045, knee_r=0.03, hand_r=0.03,
                      head_c=R.meta['head_c'], head_r=0.19, body_c=tuple(to_rig(V((0, 0, 0.05)))), body_r=0.2, hips_r=0.15)
    hero_clips(R)
    return R


def hero_clips(R):
    D = A.Dims(R)

    def bird_walk_extra(ch, t, ph, cL, b_):
        ch['B.Tail.x'] = -6 + 10 * b_
        ch['B.Tail.y'] = 8 * cL
        ch['B.Cape.x'] = 10 + 6 * b_
        return ch

    def bird_run_extra(ch, t, ph, cL, b_):
        ch['B.Tail.x'] = -18 + 12 * b_
        ch['B.Tail.y'] = 10 * cL
        ch['B.Cape.x'] = 28 + 8 * b_
        for s in 'LR':
            ch[f'B.Arm{s}.z'] = A.sgn(s) * (22 + 6 * b_)
        return ch
    # walk = brisk trot: 3.2 m/s for a 1.07 m bird is beyond a walk -> short flight phase, 4 steps/s
    R.clips.append(('Idle',) + A.c_idle(R, D, 2.8))
    R.clips.append(('Walk',) + A.locomotion(R, D, 3.2, 15, stance=0.32, lift=0.07, bob=0.028, lean=8, arm=22, yaw=7,
                                            roll=3, elbow=12, crouch=0.06, extra=bird_walk_extra))
    R.clips.append(('Run',) + A.locomotion(R, D, 5.0, 12, stance=0.26, lift=0.1, bob=0.04, lean=18, arm=30, yaw=8,
                                           roll=3, elbow=35, crouch=0.09, th_off=35, extra=bird_run_extra))
    R.meta['speeds'] = {'Walk': 3.2, 'Run': 5.0}
    common_gestures(R, D, beckon=False, lookback=False, gather=False, sit=False)
    R.clips.append(('Push',) + A.c_push(R, D))
    R.clips.append(('FallTumble',) + A.c_falltumble(R, D))
    R.clips.append(('LieDown',) + A.c_liedown(R, D))
    R.clips.append(('GetUp',) + A.c_getup(R, D))
    R.clips.append(('LookAround',) + A.c_lookaround(R, D))
    R.clips.append(('Kneel',) + A.c_kneel(R, D))


def common_gestures(R, D, beckon=True, lookback=False, gather=True, sit=True, reach=True, kneel=False):
    m = A.mirrored if R.meta.get('hand') == 'L' else (lambda c: c)   # gesture with the finished hand
    R.clips.append(('Talk',) + m(A.c_talk(R, D)))
    R.clips.append(('Bow',) + A.c_bow(R, D))
    R.clips.append(('BowHold',) + A.c_bowhold(R, D))
    R.clips.append(('Rise',) + A.c_rise(R, D))
    R.clips.append(('Point',) + m(A.c_point(R, D)))
    R.clips.append(('PointUp',) + m(A.c_point(R, D, up=True)))
    R.clips.append(('LookUp',) + A.c_lookup(R, D))
    if beckon:
        R.clips.append(('Beckon',) + m(A.c_beckon(R, D)))
    if lookback:
        R.clips.append(('LookBack',) + A.c_lookback(R, D))
    R.clips.append(('Nod',) + A.c_nod(R, D))
    R.clips.append(('HeadTilt',) + A.c_headtilt(R, D))
    if reach:
        R.clips.append(('Reach',) + m(A.c_reach(R, D)))
    if gather:
        R.clips.append(('Gather',) + A.c_gather(R, D))
    if sit:
        R.clips.append(('SitIdle',) + A.c_sitidle(R, D))
    R.clips.append(('Cower',) + A.c_cower(R, D))
    if kneel:
        R.clips.append(('Kneel',) + A.c_kneel(R, D))


# =====================================================================================  puppet parts
def puppet_limbs(R, dims, mat=WOOD, jmat=JOINT, arm_fm=None, leg_fm=None, hands=('mitten', 'mitten'),
                 ink_fore=(False, False), ink_shin=(False, False), foot=(0.12, 0.07, 0.05), sleeve=None, shorts=None, skip_fore=(False, False)):
    """dims: dict hip, knee, ankle, sh, el, wr (left side, build space), r_leg, r_arm, hand."""
    for s, x in (('L', 1), ('R', -1)):
        i = 0 if s == 'L' else 1
        hip, knee, ank = [V((p[0] * x, p[1], p[2])) for p in (dims['hip'], dims['knee'], dims['ankle'])]
        sh, el, wr = [V((p[0] * x, p[1], p[2])) for p in (dims['sh'], dims['el'], dims['wr'])]
        rl, ra = dims['r_leg'], dims['r_arm']
        # legs
        R.add('Leg' + s, ball(hip, rl * 1.12, seg=10, rings=7), jmat)
        R.add('Leg' + s, capsule(hip, knee + V((0, 0, rl * 0.6)), rl, rl * 0.86, seg=8), mat, face_mat=leg_fm)
        R.add('Shin' + s, ball(knee, rl * 0.95, seg=10, rings=7), jmat)
        if ink_shin[i] == 'skip':
            pass
        elif ink_shin[i]:
            for dx in (-rl * 0.6, rl * 0.6):
                R.add('Shin' + s, stroke(wobble_line(knee + V((dx, 0, -rl)), ank + V((dx * 0.8, 0, 0)), 4, 0.004, dx * 50), max(0.004, rl * 0.12)), INK, smooth=False)
        else:
            R.add('Shin' + s, capsule(knee - V((0, 0, rl * 0.5)), ank + V((0, 0, rl * 0.2)), rl * 0.85, rl * 0.7, seg=8), mat, face_mat=leg_fm)
        fl, fw, fh = foot
        fb = bm_box(ank + V((0, -fl * 0.28, -ank.z + fh * 0.5)), (fw, fl, fh))
        fb = L.bevel(fb, min(fw, fh) * 0.28, 1, 40)
        R.add('Foot' + s, fb, mat, smooth=False, face_mat=leg_fm)
        R.add('Foot' + s, ball(ank, rl * 0.68, seg=8, rings=6), jmat)
        if shorts:
            sm, z0, z1, rr = shorts
            sh_ = capsule(hip + V((0, 0, 0.0)), hip.lerp(knee, z1), rl * rr, rl * rr * 0.95, seg=10)
            sfn = paint_above(hip.lerp(knee, z1 * 0.85).z, sm, amp=rl * 0.5, freq=14 / max(0.3, dims['scale']), seed=3 + i)
            R.add('Leg' + s, sh_, WOOD, smooth=False, face_mat=sfn)
            brush(R, 'Leg' + s, sh_, hip.lerp(knee, z1 * 0.85).z, sm, center=(hip.x, hip.y), n=6, ln=rl * 1.8, w=rl * 0.5, seed=9 + i)
        # arms
        R.add('Arm' + s, ball(sh, ra * 1.18, seg=10, rings=7), jmat)
        R.add('Arm' + s, capsule(sh - V((0, 0, ra * 0.3)), el + V((0, 0, ra * 0.4)), ra, ra * 0.88, seg=8), mat, face_mat=arm_fm)
        R.add('ForeArm' + s, ball(el, ra * 0.95, seg=8, rings=6), jmat)
        d = (wr - el).normalized()
        if skip_fore[i]:
            pass
        elif ink_fore[i]:
            for dx in (-ra * 0.55, ra * 0.55):
                o = V((dx, 0, 0))
                R.add('ForeArm' + s, stroke(wobble_line(el + o + d * ra, wr + o * 0.8, 4, 0.004, dx * 40), max(0.004, ra * 0.13)), INK, smooth=False)
            ink_hand(To(R, 'Hand' + s), wr, d, ln=dims['hand'] * 1.3, side=x, r=max(0.004, ra * 0.14))
        else:
            R.add('ForeArm' + s, capsule(el - V((0, 0, ra * 0.4)), wr + V((0, 0, ra * 0.3)), ra * 0.86, ra * 0.72, seg=8), mat, face_mat=arm_fm)
            if hands[i] == 'mitten':
                R.add('Hand' + s, ball(wr, ra * 0.75, seg=8, rings=5), jmat)
                R.add('Hand' + s, mitten(wr, d, dims['hand'], x), mat, smooth=False)
                # thumb nub
                th = bm_box((0, 0, 0), (dims['hand'] * 0.22, dims['hand'] * 0.22, dims['hand'] * 0.45))
                th = L.bevel(th, dims['hand'] * 0.07, 1, 40)
                move(th, wr + d * dims['hand'] * 0.35 + V((0, -dims['hand'] * 0.3, 0)))
                R.add('Hand' + s, th, mat, smooth=False)
            elif hands[i] == 'ink':
                ink_hand(To(R, 'Hand' + s), wr, d, ln=dims['hand'] * 1.3, side=x, r=max(0.004, ra * 0.14))
        if sleeve:
            sm, frac, rr = sleeve
            sv = capsule(sh - V((0, 0, ra * 0.2)), sh.lerp(el, frac), ra * rr, ra * rr * 0.95, seg=10)
            R.add('Arm' + s, sv, WOOD, smooth=False, face_mat=paint_above(sh.lerp(el, frac * 0.8).z, sm, amp=ra * 0.5, freq=16, seed=5 + i))
            brush(R, 'Arm' + s, sv, sh.lerp(el, frac * 0.8).z, sm, center=(sh.x, sh.y), n=5, ln=ra * 1.7, w=ra * 0.5, seed=21 + i)


def puppet_bones(R, dims, head_pivot, waist, hips):
    R.bone('Hips', None, hips)
    R.bone('Body', 'Hips', waist)
    R.bone('Head', 'Body', head_pivot)
    for s, x in (('L', 1), ('R', -1)):
        R.bone('Leg' + s, 'Hips', V((dims['hip'][0] * x, dims['hip'][1], dims['hip'][2])))
        R.bone('Shin' + s, 'Leg' + s, V((dims['knee'][0] * x, dims['knee'][1], dims['knee'][2])))
        R.bone('Foot' + s, 'Shin' + s, V((dims['ankle'][0] * x, dims['ankle'][1], dims['ankle'][2])))
    for s, x in (('L', 1), ('R', -1)):
        R.bone('Arm' + s, 'Body', V((dims['sh'][0] * x, dims['sh'][1], dims['sh'][2])))
        R.bone('ForeArm' + s, 'Arm' + s, V((dims['el'][0] * x, dims['el'][1], dims['el'][2])))
        R.bone('Hand' + s, 'ForeArm' + s, V((dims['wr'][0] * x, dims['wr'][1], dims['wr'][2])))


def puppet_meta(R, dims, height, head_c_world, head_r, body_c_world, body_r, kind='puppet', foot=(0.12, 0.07, 0.05)):
    from ouat_rig import to_rig
    hp = R.bones['Head'][1]
    R.meta.update(height=height, kind=kind, toe=foot[0] * 0.62, heel=foot[0] * 0.3, head_r=head_r, knee_r=dims['r_leg'],
                  head_c=tuple(to_rig(V(head_c_world) - hp)), arm_out=5.0)
    R.meta.setdefault('rest_pose', {'B.ArmL.z': 5.0, 'B.ArmR.z': -5.0, 'B.ForeArmL.x': -10.0, 'B.ForeArmR.x': -10.0})
    bp = R.bones['Body'][1]
    humanoid_contacts(R, sole_y=dims['ankle'][2], toe=foot[0] * 0.7, heel=foot[0] * 0.32, knee_r=dims['r_leg'],
                      hand_r=dims['hand'] * 0.4, head_c=R.meta['head_c'], head_r=head_r,
                      body_c=tuple(to_rig(V(body_c_world) - bp)), body_r=body_r, hips_r=dims['r_leg'] * 2)


# =====================================================================================  unfinished-form helpers
PENCIL = 'M_PencilBody'


def brush(R, target, b, z_edge, mat, center=(0, 0), n=7, ln=0.06, w=0.014, down=True, seed=0.0, arc=(0, 360)):
    """Dry-brush streaks running off a paint edge: flush to the surface (no outline material), tapered, uneven."""
    rnd = random.Random(int(seed * 1000) + 11)
    bvh = BVHTree.FromBMesh(b)
    cx, cy = center
    for k in range(n):
        a = math.radians(arc[0] + (arc[1] - arc[0]) * (k + rnd.uniform(-0.4, 0.4)) / n)
        Ln = ln * rnd.choice((0.35, 0.55, 0.8, 1.0, 1.3))
        wk = w * rnd.uniform(0.5, 1.2)
        drift = rnd.uniform(-0.25, 0.25)
        pts, nrms = [], []
        for t in range(7):
            f = t / 6
            z = z_edge + (-1 if down else 1) * (Ln * f - 0.006)
            aa = a + drift * f * (Ln / 0.3)
            d = V((math.cos(aa), math.sin(aa), 0))
            hit = bvh.ray_cast(V((cx, cy, z)) + d * 3.0, -d)
            if hit[0] is None:
                break
            pts.append(hit[0] + hit[1] * 0.0022)
            nrms.append(hit[1])
        if len(pts) < 3:
            continue
        prof = [1.0, 0.95, 0.85, 0.7, 0.5, 0.3, 0.06]
        ww = [wk * prof[i] for i in range(len(pts))]
        R.add(target, bm_blade(pts, ww, thick=0.0015, up=tuple(nrms[len(nrms) // 2])), BRUSH.get(mat, mat), smooth=False)


def ring_pts(c, axis, r, n=12, wob=0.0, seed=0.0, start=0.0, sweep=1.0):
    axis = V(axis).normalized()
    u = axis.orthogonal().normalized()
    v = axis.cross(u).normalized()
    out = []
    for i in range(n + 1):
        a = start + 2 * math.pi * sweep * i / n
        rr = r * (1 + wob * math.sin(3 * a + seed))
        out.append(V(c) + u * math.cos(a) * rr + v * math.sin(a) * rr)
    return out


def sketch_cyl(R, target, p0, p1, r0, r1, lw=0.004, rings=3, longs=4, seed=0.0, mat=PENCIL, overshoot=0.15):
    """Construction-line cylinder: cross-section ellipses + longitudinal lines that overshoot like a pencil sketch."""
    p0, p1 = V(p0), V(p1)
    ax = p1 - p0
    rnd = random.Random(int(seed * 97) + 3)
    for k in range(rings):
        t = k / max(1, rings - 1)
        c = p0.lerp(p1, t)
        r = r0 + (r1 - r0) * t
        pts = ring_pts(c, ax, r * rnd.uniform(0.95, 1.08), 14, 0.05, seed + k, rnd.uniform(0, 6), rnd.uniform(0.85, 1.08))
        R.add(target, stroke(pts, lw, taper=True), mat, smooth=False)
    u = ax.orthogonal().normalized()
    v = ax.normalized().cross(u)
    for k in range(longs):
        a = 2 * math.pi * (k + 0.5) / longs + rnd.uniform(-0.2, 0.2)
        d = u * math.cos(a) + v * math.sin(a)
        q0 = p0 - ax * overshoot * rnd.uniform(0.2, 1.0) + d * r0
        q1 = p1 + ax * overshoot * rnd.uniform(0.0, 0.8) + d * r1
        R.add(target, stroke(wobble_line(q0, q1, 5, lw * 1.5, seed + k), lw, taper=True), mat, smooth=False)


def torn_tube(p0, p1, r0, r1, seg=9, tear=0.6, seed=0.0, steps=4):
    """Solid tube whose far end is torn off like paper: jagged rim, capped. Returns (bmesh, rim points)."""
    p0, p1 = V(p0), V(p1)
    pts = [p0.lerp(p1, i / steps) for i in range(steps + 1)]
    rad = [r0 + (r1 - r0) * i / steps for i in range(steps + 1)]
    b = bm_tube(pts, rad, seg=seg, cap=True)
    ax = (p1 - p0).normalized()
    L_ = (p1 - p0).length
    rnd = random.Random(int(seed * 131) + 5)
    rim = []
    jag = [rnd.uniform(-1, 1) * (1 if i % 2 else 0.4) for i in range(seg)]
    for v in b.verts:
        t = (v.co - p0).dot(ax) / L_
        if t > 0.999:
            rel = v.co - p1
            if rel.length < 1e-6:
                v.co += ax * (-tear * r1 * 0.2)
                continue
            u = ax.orthogonal().normalized()
            ang = math.atan2(rel.dot(ax.cross(u)), rel.dot(u))
            k = int(((ang + math.pi) / (2 * math.pi)) * seg) % seg
            v.co += ax * (jag[k] * tear * r1)
    # rim = verts at t>~1 after the jag; rebuild an ink line from the jagged ring
    ring = sorted([v.co.copy() for v in b.verts if (v.co - p0).dot(ax) / L_ > 1 - tear * r1 / L_ * 1.2 and ((v.co - p0) - ax * (v.co - p0).dot(ax)).length > r1 * 0.6],
                  key=lambda c: math.atan2((c - p1).dot(ax.cross(ax.orthogonal().normalized())), (c - p1).dot(ax.orthogonal().normalized())))
    if ring:
        ring.append(ring[0])
    return b, ring


def torn_limb(R, solid_bone, sketch_bone, p0, p1, r0, r1, frac=0.55, mat=WOOD, lw=0.004, seed=0.0, fm=None):
    """Solid wood up to frac of the segment (torn rim + ink edge), then pencil construction lines to p1."""
    p0, p1 = V(p0), V(p1)
    pm = p0.lerp(p1, frac)
    rm = r0 + (r1 - r0) * frac
    b, rim = torn_tube(p0, pm, r0, rm, seg=10, tear=0.9, seed=seed)
    R.add(solid_bone, b, mat, smooth=False, face_mat=fm)
    if len(rim) > 3:
        R.add(solid_bone, stroke(rim, lw * 0.9, taper=False), INK, smooth=False)
    sketch_cyl(R, sketch_bone, pm - (p1 - p0) * 0.05, p1, rm, r1, lw=lw, rings=2, longs=4, seed=seed)


# =====================================================================================  KINOPIO
def build_kinopio():
    R = RigChar('Kinopio')
    # longer legs than round 1 (leg 0.32 m) so 2.2 m/s reads as a quick child's trot, not a crouch
    dims = dict(hip=(0.055, 0, 0.36), knee=(0.057, -0.004, 0.205), ankle=(0.058, 0, 0.052),
                sh=(0.1, 0, 0.535), el=(0.11, 0.0, 0.445), wr=(0.115, 0, 0.36), r_leg=0.025, r_arm=0.021, hand=0.06, scale=0.8)
    puppet_bones(R, dims, head_pivot=(0, 0, 0.575), waist=(0, 0, 0.385), hips=(0, 0, 0.375))
    R.bone('Nose', 'Head', (0, -0.075, 0.69))
    # ---- pelvis (red shorts) + torso (blue shirt, white collar, navy suspenders)
    pel = bm_sphere((0, 0, 0.38), (0.092, 0.074, 0.056), seg=14, rings=8)
    R.add('Hips', pel, RED, face_mat=paint_below(0.35, WOOD, amp=0.01, freq=22, seed=1))
    tor = bm_lathe([(0.0, 0.395), (0.078, 0.4), (0.093, 0.44), (0.098, 0.49), (0.09, 0.53), (0.056, 0.556), (0.0, 0.56)], seg=14, sy=0.78)
    tor = subdivide(tor, 2)
    brush(R, 'Body', tor, 0.462, BLUE, n=8, ln=0.045, w=0.012, seed=2)
    R.add('Body', tor, WOOD, face_mat=paint_above(0.462, BLUE, amp=0.008, freq=26, seed=2))
    R.add('Body', ball((0, 0, 0.388), 0.031, seg=10, rings=7), JOINT)
    for x in (1, -1):
        p0 = V((0.01 * x, -0.058, 0.555))
        R.add('Body', bm_blade([p0, p0 + V((0.028 * x, -0.012, -0.02)), p0 + V((0.047 * x, -0.004, -0.028))], [0.013, 0.017, 0.004],
                               thick=0.006, up=(0, -1, 0.4)), 'M_PaintWhite', smooth=False)
    bvh = BVHTree.FromBMesh(tor)
    for x in (1, -1):
        sp = []
        for i in range(8):
            z = 0.553 - i * 0.021
            xx = (0.048 - 0.006 * i / 7) * x
            hit = bvh.ray_cast(V((xx, -0.5, z)), V((0, 1, 0)))
            if hit[0] is not None:
                sp.append(hit[0] + hit[1] * 0.003)
        R.add('Body', bm_tube(sp, 0.0085, seg=4, cap=False, flat=0.35, up=(0, -1, 0)), 'M_PaintNavy', smooth=False)
        R.add('Body', bm_sphere(sp[-1] + V((0, -0.005, 0.0)), (0.009, 0.006, 0.009), seg=6, rings=4), 'M_Brass')
    # ---- limbs: left arm finished, right forearm torn off mid-way and continued as pencil construction
    puppet_limbs(R, dims, hands=('mitten', 'none'), foot=(0.105, 0.06, 0.044), sleeve=(BLUE, 0.55, 1.35),
                 shorts=(RED, 0, 0.42, 1.42), skip_fore=(False, True))
    el, wr = V((-0.11, 0.0, 0.445)), V((-0.115, 0, 0.36))
    torn_limb(R, 'ForeArmR', 'ForeArmR', el - V((0, 0, 0.012)), wr, 0.018, 0.015, frac=0.5, lw=0.0032, seed=4)
    ink_hand(To(R, 'HandR'), wr, (wr - el).normalized(), ln=0.07, side=-1, r=0.0028)
    # ---- head: carved face plank (solid, front) + the rest of the hex head still a pencil construction
    hc = V((0, -0.005, 0.71))
    sx, sy, sz = 0.165, 0.078, 0.125
    outline = [(math.cos(math.radians(60 * i)) * sx * (1.0 if i % 3 == 0 else 0.86), math.sin(math.radians(60 * i)) * sz) for i in range(6)]
    front_d = 0.112   # solid depth from the face (back ~30 % still a pencil construction)
    hb = L.bm_prism(outline, -sy, -sy + front_d, center=hc, axis='Y')
    hb = L.bevel(hb, 0.02, 1, 40)
    # torn back edge: push the back face verts by noise so the cut is ragged
    for v in hb.verts:
        if v.co.y > hc.y - sy + front_d - 0.025:
            v.co.y += 0.018 * nval(v.co, 30.0, 7) + 0.006 * math.sin(v.co.x * 90)
    jitter(hb, 0.0025, 4.0, 5)
    hbv = BVHTree.FromBMesh(hb)
    R.add('Head', hb, WOOD, smooth=False, face_mat=paint_above(0.81, BLUE, amp=0.008, freq=24, seed=6))
    # ink along the ragged back rim (the edge where carving stopped)
    rim = []
    for i in range(25):
        a = 2 * math.pi * i / 24
        d = V((math.cos(a) * sx * 1.2, 0, math.sin(a) * sz * 1.2))
        hit = hbv.ray_cast(hc + V((0, -sy + front_d - 0.012, 0)) + d * 2.0, -d.normalized())
        if hit[0] is not None:
            rim.append(hit[0] + hit[1] * 0.002)
    if len(rim) > 4:
        rim.append(rim[0])
        R.add('Head', stroke(rim, 0.0035, taper=False), INK, smooth=False)
    # pencil construction of the unfinished back half: back hex outline + connecting edges, overshooting
    yb = hc.y + sy
    yf = hc.y - sy + front_d - 0.01
    corners = [V((hc.x + u, 0, hc.z + w)) for u, w in outline]
    rnd = random.Random(8)
    back = [V((c.x, yb, c.z)) for c in corners] + [V((corners[0].x, yb, corners[0].z))]
    R.add('Head', stroke([p + V((rnd.uniform(-0.004, 0.004), 0, rnd.uniform(-0.004, 0.004))) for p in back], 0.0022, taper=False), PENCIL, smooth=False)
    for c in corners:
        q0 = V((c.x, yf - 0.006, c.z))
        q1 = V((c.x, yb + 0.018, c.z))
        R.add('Head', stroke(wobble_line(q0, q1, 4, 0.003, c.x * 30), 0.002), PENCIL, smooth=False)
    R.add('Head', capsule((0, 0, 0.568), (0, -0.004, 0.605), 0.019, 0.019, seg=7), WOOD)
    R.add('Head', ball((0, 0, 0.575), 0.023, seg=8, rings=6), JOINT)
    # eyes (char left = deep hole, char right = drawn ring with a dot)
    hit = hbv.ray_cast(V((0.064, -0.5, 0.72)), V((0, 1, 0)))
    R.add('Head', oriented_eye(hit[0] - hit[1] * 0.003, hit[1], (0.031, 0.012, 0.038)), INK)
    hit = hbv.ray_cast(V((-0.064, -0.5, 0.722)), V((0, 1, 0)))
    c, n = hit[0], hit[1]
    ring = []
    for i in range(15):
        a = 2 * math.pi * i / 14 + 0.3
        ring.append(c + n * 0.003 + V((math.cos(a) * 0.034 * (1 + 0.07 * math.sin(3 * a)), 0, math.sin(a) * 0.036)))
    R.add('Head', stroke(ring, 0.0045, taper=False), INK, smooth=False)
    R.add('Head', oriented_eye(c + n * 0.002 + V((0.006, 0, 0.002)), n, (0.012, 0.005, 0.013)), INK)
    # paint tufts (brush chips) on top
    for k, (m, off, ln, ang) in enumerate(((RED, (-0.05, -0.02, 0.11), 0.085, 12), (BLUE, (-0.022, -0.01, 0.115), 0.065, -6),
                                           (RED, (0.07, -0.03, 0.105), 0.05, -25))):
        p0 = hc + V(off)
        d = V((math.sin(math.radians(ang)), 0.0, math.cos(math.radians(ang))))
        pts = [p0, p0 + d * ln * 0.5 + V((0, 0.01, 0)), p0 + d * ln + V((0.0, 0.025, 0))]
        R.add('Head', bm_blade(pts, [ln * 0.18, ln * 0.21, ln * 0.05], thick=ln * 0.06, up=(0, 1, 0)), m, smooth=False)
    # ---- nose = translucent pencil line (retraced), on its own bone (kept level by the 'post' hook)
    root = V((0, -0.075, 0.69))
    tip = root + V((0.01, -0.32, 0.03))
    R.add('Nose', bm_tube([root, root.lerp(tip, 0.5), tip], [0.012, 0.006, 0.0015], seg=6), 'M_SketchNose')
    for k, (dx, dz) in enumerate(((0.012, 0.004), (-0.01, 0.003), (0.002, -0.012))):
        p0 = root + V((dx, 0.012, dz))
        p1 = tip + V((dx * 0.2 + 0.006 * k, -0.03 * (k % 2) - 0.01, dz * 0.2))
        R.add('Nose', stroke(wobble_line(p0, p1, 6, 0.005, k * 1.9), 0.0032), 'M_SketchNose', smooth=False)
    # ---- Mark (separate object, hidden by default in Unity)
    mk = [V((0.064 + 0.011 * i, -0.052 + 0.018 * i, 0.545 - 0.011 * i)) for i in range(5)]
    R.add('Body', bm_blade(mk, [0.006, 0.012, 0.014, 0.012, 0.004], thick=0.004, up=(0.5, -0.6, 0.8)), 'M_Mark', smooth=False, obj='Mark')
    puppet_meta(R, dims, 0.87, hc, 0.14, (0, 0, 0.47), 0.1, foot=(0.105, 0.06, 0.044))
    R.meta['rest_pose'] = {'B.ArmL.z': 6.0, 'B.ArmR.z': -6.0, 'B.ForeArmL.x': -12.0, 'B.ForeArmR.x': -12.0, 'B.Head.x': -3}

    def level_nose(ch):
        pitch = ch.get('hips.x', 0) + ch.get('B.Body.x', 0) + ch.get('B.Head.x', 0)
        ch['B.Nose.x'] = ch.get('B.Nose.x', 0) - max(-30.0, min(95.0, pitch)) * 0.9
        return ch
    R.meta['post'] = level_nose
    R.meta['hand'] = 'L'   # right forearm is unfinished -> gestures with the left
    kinopio_clips(R)
    return R


def kinopio_clips(R):
    D = A.Dims(R)

    def puppet_extra(ch, t, ph, cL, b_):
        ch['B.Nose.x'] = 2 * b_
        ch['B.Head.z'] = ch.get('B.Head.z', 0) + 3 * cL   # wooden head wobble
        return ch
    R.clips.append(('Idle',) + A.c_idle(R, D, 2.8))
    R.clips.append(('Walk',) + A.locomotion(R, D, 2.2, 10, stance=0.3, lift=0.05, bob=0.016, lean=5, arm=24, yaw=8,
                                            roll=4, elbow=14, crouch=0.0, extra=puppet_extra))
    R.clips.append(('Run',) + A.locomotion(R, D, 4.0, 9, stance=0.23, lift=0.075, bob=0.026, lean=14, arm=36, yaw=9,
                                           roll=4, elbow=55, crouch=0.02, th_off=35, extra=puppet_extra))
    R.meta['speeds'] = {'Walk': 2.2, 'Run': 4.0}
    common_gestures(R, D, beckon=True, lookback=True, gather=True, sit=True, kneel=True)
    R.clips.append(('Push',) + A.c_push(R, D))


# =====================================================================================  CHIEF
def leaf_rosette(R, bone, c, rnd, n=6, size=0.3, out=V((0, 0, 1))):
    """Clump of pointed paper leaf cards fanning out (reads as leaves, keeps gaps)."""
    out = V(out).normalized()
    u = out.orthogonal().normalized()
    w = out.cross(u)
    for k in range(n):
        a = 2 * math.pi * k / n + rnd.uniform(-0.3, 0.3)
        d = (u * math.cos(a) + w * math.sin(a)) * 0.85 + out * 0.55
        d.normalize()
        ln = size * rnd.uniform(0.75, 1.15)
        p0 = c + d * size * 0.12
        pts = [p0, p0 + d * ln * 0.45 + V((0, 0, 0.03)), p0 + d * ln]
        nrm = d.cross(u * -math.sin(a) + w * math.cos(a)).normalized()
        b = bm_blade(pts, [ln * 0.08, ln * 0.24, ln * 0.015], thick=0.012, up=tuple(nrm))
        R.add(bone, b, 'M_Leaf', smooth=False)
        # midrib ink line on every other leaf
        if k % 2 == 0:
            R.add(bone, stroke([p0 + nrm * 0.014, p0 + d * ln * 0.85 + nrm * 0.014], 0.005), INK, smooth=False)


def build_chief():
    """Chief: walking dangsan tree elder (~3 m), wide crown with gaps, root legs, branch arms."""
    R = RigChar('Chief')
    BARK, LEAF = 'M_Bark', 'M_Leaf'
    rnd = random.Random(31)
    dims = dict(hip=(0.3, 0, 1.02), knee=(0.36, -0.05, 0.56), ankle=(0.38, 0, 0.16),
                sh=(0.56, 0.0, 1.86), el=(0.8, -0.04, 1.36), wr=(0.86, -0.08, 0.9), r_leg=0.16, r_arm=0.11, hand=0.2, scale=3.0)
    puppet_bones(R, dims, head_pivot=(0, 0, 1.95), waist=(0, 0, 1.08), hips=(0, 0, 1.04))
    R.bone('Canopy', 'Head', (0, 0.05, 2.45))
    # ---- legs: bark thighs, puppet knee balls, shins flaring into spreading root feet
    for s, x in (('L', 1), ('R', -1)):
        hip, knee, ank = [V((p[0] * x, p[1], p[2])) for p in (dims['hip'], dims['knee'], dims['ankle'])]
        R.add('Leg' + s, ball(hip, 0.2, seg=10, rings=7), JOINT)
        th = bm_tube([hip, hip.lerp(knee, 0.5) + V((0.03 * x, 0, 0)), knee + V((0, 0, 0.08))], [0.17, 0.155, 0.14], seg=10, twist=0.3)
        jitter(th, 0.018, 3, 20 + x)
        R.add('Leg' + s, th, BARK, face_mat=paint_below(0.72, RED, amp=0.04, freq=8, seed=3 + x))
        R.add('Shin' + s, ball(knee, 0.15, seg=10, rings=7), JOINT, face_mat=L.ragged(lambda c: -c.z, -0.6, RED, amp=0.05, freq=10, seed=7 + x))
        sh_ = bm_tube([knee - V((0, 0, 0.06)), knee.lerp(ank, 0.6), ank + V((0, 0, 0.02))], [0.13, 0.135, 0.16], seg=10, twist=0.4)
        jitter(sh_, 0.015, 3, 30 + x)
        R.add('Shin' + s, sh_, BARK)
        for k, ang in enumerate((-70, -30, 5, 40, 75, 160)):
            a = math.radians(ang) * x
            d = V((math.sin(a), -math.cos(a), 0))
            ln = (0.42 if k < 5 else 0.28) * rnd.uniform(0.85, 1.15)
            p0 = ank + V((0, 0, 0.02))
            pts = [p0, p0 + d * ln * 0.45 + V((0, 0, -0.08)), p0 + d * ln + V((0, 0, -0.15))]
            rt = bm_tube(pts, [0.1, 0.065, 0.022], seg=6)
            jitter(rt, 0.012, 5, k + x * 3)
            R.add('Foot' + s, rt, BARK)
            if k in (1, 4):   # an unfinished root continuing as ink
                tip = pts[-1]
                R.add('Foot' + s, stroke(wobble_line(tip, tip + d * 0.22 + V((0, 0, -0.005)), 4, 0.02, k), 0.008), INK, smooth=False)
    # ---- trunk body: gnarled, widening upward (wide shoulders), twisted ink bark lines
    tpts = [V((0, 0, 0.98)), V((0.03, 0.01, 1.2)), V((-0.02, 0.02, 1.45)), V((0.02, 0.0, 1.7)), V((0, 0.0, 1.92))]
    tr = bm_tube(tpts, [0.36, 0.33, 0.36, 0.46, 0.58], seg=14, twist=0.3, flat=0.82, up=(0, 1, 0))
    jitter(tr, 0.04, 2.2, 30)
    tr = subdivide(tr, 1)
    brush(R, 'Body', tr, 1.6, BLUE, n=6, ln=0.22, w=0.05, seed=41, arc=(-20, 200))
    _pb = paint_above(1.6, BLUE, amp=0.04, freq=7, seed=41)
    R.add('Body', tr, BARK, face_mat=lambda c, n: _pb(c, n) if c.y > -0.12 else None)   # paint on the back/sides, bare under the beard
    R.add('Hips', ball((0, 0, 1.0), 0.3, seg=12, rings=8), JOINT)
    for k in range(5):
        a0 = 2 * math.pi * k / 5 + 0.4
        sp = []
        for i in range(7):
            t = i / 6
            z = 1.0 + 0.85 * t
            r = (0.34 + 0.2 * t ** 2) * (0.82 if math.sin(a0 + 1.1 * t) > 0 else 1.0) + 0.03
            a = a0 + 1.1 * t
            sp.append(V((math.cos(a) * r, math.sin(a) * r * 0.85, z)))
        R.add('Body', stroke(sp, 0.012), INK, smooth=False)
    # 금줄: twisted straw rope + white paper strips
    rope = [V((math.cos(2 * math.pi * i / 20) * 0.38, math.sin(2 * math.pi * i / 20) * 0.33, 1.2 + 0.035 * math.sin(i * 1.3))) for i in range(21)]
    R.add('Body', bm_tube(rope, 0.045, seg=6, cap=False, twist=1.1), 'M_PaperShade')
    for k in range(7):
        a = math.radians(-160 + k * 23)
        p0 = V((math.cos(a) * 0.42, math.sin(a) * 0.37, 1.17))
        pr = p0 + V((math.cos(a) * 0.02, math.sin(a) * 0.02, -0.26 - 0.06 * (k % 2)))
        zz = [p0, p0.lerp(pr, 0.33) + V((math.cos(a) * 0.03, math.sin(a) * 0.03, 0)), p0.lerp(pr, 0.66) - V((math.cos(a) * 0.02, math.sin(a) * 0.02, 0)), pr]
        R.add('Body', bm_blade(zz, [0.04, 0.045, 0.045, 0.035], thick=0.006, up=(math.cos(a), math.sin(a), 0)), 'M_PageWhite', smooth=False)
    # ---- arms: long branch arms with ball joints, twig fingers, cloth ties (red / blue)
    for s, x in (('L', 1), ('R', -1)):
        sh, el, wr = [V((p[0] * x, p[1], p[2])) for p in (dims['sh'], dims['el'], dims['wr'])]
        R.add('Arm' + s, ball(sh, 0.16, seg=10, rings=7), JOINT)
        ua = bm_tube([sh, sh.lerp(el, 0.5) + V((0.04 * x, 0, 0.03)), el], [0.13, 0.11, 0.1], seg=8, twist=0.4)
        jitter(ua, 0.012, 4, 50 + x)
        R.add('Arm' + s, ua, BARK)
        R.add('ForeArm' + s, ball(el, 0.11, seg=8, rings=6), JOINT)
        fa = bm_tube([el, el.lerp(wr, 0.5) + V((0.02 * x, 0, 0)), wr], [0.095, 0.08, 0.085], seg=8, twist=0.3)
        jitter(fa, 0.01, 4, 60 + x)
        R.add('ForeArm' + s, fa, BARK)
        for k, d in enumerate((V((0.07 * x, -0.08, -0.26)), V((-0.05 * x, -0.13, -0.22)), V((0.0, 0.05, -0.25)), V((0.1 * x, 0.02, -0.18)))):
            tw = bm_tube([wr, wr + d * 0.55, wr + d], [0.055, 0.035, 0.015], seg=5)
            R.add('Hand' + s, tw, BARK)
        # twig sprouting from the elbow with a small leaf clump; on the right arm only drawn in pencil
        tw = [el, el + V((0.2 * x, 0.06, 0.26)), el + V((0.26 * x, 0.1, 0.45))]
        if s == 'L':
            R.add('ForeArm' + s, bm_tube(tw, [0.04, 0.025, 0.01], seg=5), BARK)
            leaf_rosette(R, 'ForeArm' + s, tw[-1] + V((0.02 * x, 0, 0.03)), rnd, n=4, size=0.16, out=V((x, 0, 1)).normalized())
        else:
            R.add('ForeArm' + s, stroke(wobble_line(tw[0], tw[-1], 5, 0.02, 3), 0.01), INK, smooth=False)
            R.add('ForeArm' + s, stroke(ring_pts(tw[-1] + V((0, 0, 0.05)), (0.2, -1, 0.3), 0.15, 12, 0.12, 2), 0.006), PENCIL, smooth=False)
        # 오방색-like cloth ties (painted accent), ragged ends
        cm = RED if s == 'L' else BLUE
        cc = sh.lerp(el, 0.55)
        ring = ring_pts(cc, el - sh, 0.13, 12)
        R.add('Arm' + s, bm_tube(ring, 0.025, seg=5, cap=False, flat=0.5), cm, smooth=False)
        for k in range(2):
            p0 = cc + V((0.1 * x, -0.06, 0.0))
            pts = [p0, p0 + V((0.04 * x, -0.04 - 0.03 * k, -0.15)), p0 + V((0.02 * x, -0.03 - 0.05 * k, -0.32 + 0.06 * k))]
            R.add('Arm' + s, bm_blade(pts, [0.035, 0.038, 0.02], thick=0.006, up=(x, -1, 0)), cm, smooth=False)
    # ---- head: trunk top with heavy brow, deep hole eyes, hanging-root beard
    hb = bm_tube([V((0, 0, 1.9)), V((0, 0.0, 2.15)), V((0, 0.04, 2.42))], [0.56, 0.6, 0.52], seg=14, twist=0.2, flat=0.8, up=(0, 1, 0))
    jitter(hb, 0.03, 2.0, 50)
    hb = subdivide(hb, 1)
    hbv = BVHTree.FromBMesh(hb)
    R.add('Head', hb, BARK)
    for x in (1, -1):
        hit = hbv.ray_cast(V((0.21 * x, -2, 2.2)), V((0, 1, 0)))
        c, n = hit[0], hit[1]
        R.add('Head', oriented_eye(c - n * 0.02, n, (0.105, 0.06, 0.09)), INK)
        brow = [c + V((-0.16 * x, -0.02, 0.06)), c + V((0.0, -0.07, 0.12)), c + V((0.15 * x, -0.03, 0.09))]
        R.add('Head', bm_tube(brow, [0.05, 0.075, 0.04], seg=7), BARK)
    # beard of hanging roots from under the face, ends turn into ink lines
    for k in range(9):
        xx = -0.3 + 0.6 * k / 8 + rnd.uniform(-0.03, 0.03)
        hit = hbv.ray_cast(V((xx, -2, 2.04)), V((0, 1, 0)))
        if hit[0] is None:
            continue
        p0 = hit[0] + V((0, 0.02, 0))
        ln = rnd.uniform(0.22, 0.42) * (1.2 - abs(xx))
        pts = [p0, p0 + V((xx * 0.1, -0.06, -ln * 0.5)), p0 + V((xx * 0.15, -0.05, -ln))]
        R.add('Head', bm_tube(pts, [0.035, 0.025, 0.012], seg=5), BARK)
        R.add('Head', stroke(wobble_line(pts[-1], pts[-1] + V((0, 0, -0.18)), 4, 0.015, k), 0.006), INK, smooth=False)
    # ---- crown: thick branches spreading up and out (wide on top, gaps between clumps)
    tips = []
    for i in range(10):
        a = 2 * math.pi * i / 10 + rnd.uniform(-0.15, 0.15)
        rr = rnd.uniform(0.95, 1.45)
        tips.append(V((math.cos(a) * rr, math.sin(a) * rr * 0.7 + 0.08, rnd.uniform(2.65, 3.0))))
    for i, tp in enumerate(tips):
        st = V((tp.x * 0.2, tp.y * 0.2 + 0.04, 2.35))
        mid = st.lerp(tp, 0.5) + V((0, 0, 0.18))
        unfinished = i in (2, 7)
        if unfinished:   # solid stub, then the branch continues as pencil construction
            torn_limb(R, 'Canopy', 'Canopy', st, tp, 0.14, 0.05, frac=0.45, mat=BARK, lw=0.009, seed=i)
            R.add('Canopy', stroke(ring_pts(tp + V((0, 0, 0.12)), (0.2, 0.1, 1), 0.38, 14, 0.15, i), 0.008), PENCIL, smooth=False)
            R.add('Canopy', stroke(ring_pts(tp + V((0.08, 0, 0.16)), (0.3, -0.2, 1), 0.3, 12, 0.2, i + 3), 0.007), PENCIL, smooth=False)
            continue
        br = bm_tube([st, mid, tp], [0.15, 0.1, 0.045], seg=7)
        jitter(br, 0.025, 3, 60 + i)
        R.add('Canopy', br, BARK)
        if i % 3 == 0:
            R.add('Canopy', ball(mid, 0.09, seg=6, rings=4), JOINT)
        leaf_rosette(R, 'Canopy', tp + V((0, 0, 0.04)), rnd, n=7, size=0.3, out=V((tp.x, tp.y, 0.6)).normalized())
        out = V((tp.x, tp.y, 0)).normalized()
        for j in range(2):
            p0 = tp + V((0, 0, 0.05 * j))
            p1 = p0 + out * rnd.uniform(0.25, 0.45) + V((rnd.uniform(-0.12, 0.12), 0, rnd.uniform(0.12, 0.35)))
            R.add('Canopy', stroke(wobble_line(p0, p1, 4, 0.025, i * 2 + j), 0.008), INK, smooth=False)
    puppet_meta(R, dims, 3.0, (0, -0.02, 2.15), 0.55, (0, 0, 1.45), 0.42, kind='tree', foot=(0.5, 0.4, 0.15))
    R.meta['rest_pose'] = {'B.ArmL.z': 8.0, 'B.ArmR.z': -8.0, 'B.ForeArmL.x': -12.0, 'B.ForeArmR.x': -12.0, 'B.Body.x': 4.0, 'B.Head.x': 3.0}
    R.meta['toe'] = 0.3
    R.meta['heel'] = 0.15
    D = A.Dims(R)
    R.clips.append(('Idle',) + A.c_idle(R, D, 4.0))
    R.clips.append(('Walk',) + A.locomotion(R, D, 2.2, 24, stance=0.55, lift=0.12, bob=0.05, lean=5, arm=14, yaw=6,
                                            roll=4, elbow=10, crouch=0.04, th_strike=0.0, th_off=0.0, head_bob=1.5))
    R.meta['speeds'] = {'Walk': 2.2}
    common_gestures(R, D, beckon=False, lookback=False, gather=False, sit=False, reach=False, kneel=True)
    R.clips.append(('Greet',) + A.c_greet(R, D))
    R.clips.append(('StandSway',) + A.c_standsway(R, D))
    return R


# =====================================================================================  VILLAGERS (one shared body) + SILHOUETTES
VDIMS = dict(hip=(0.085, 0, 0.64), knee=(0.09, -0.008, 0.37), ankle=(0.092, 0, 0.068),
             sh=(0.165, 0, 1.0), el=(0.19, 0.0, 0.8), wr=(0.2, 0, 0.61), r_leg=0.038, r_arm=0.032, hand=0.085, scale=1.3)


def villager(name, head, paint, unfinished, sil=False):
    R = RigChar(name)
    d = VDIMS
    puppet_bones(R, d, head_pivot=(0, 0, 1.075), waist=(0, 0, 0.7), hips=(0, 0, 0.665))
    W = 'M_Silhouette' if sil else WOOD
    J = 'M_Silhouette' if sil else JOINT
    top, bot = paint if not sil else (None, None)
    # pelvis block + barrel torso
    pel = bm_box((0, 0, 0.665), (0.25, 0.16, 0.13))
    pel = L.bevel(pel, 0.04, 2, 40)
    R.add('Hips', pel, bot or W, smooth=False, face_mat=None if sil else paint_below(0.62, WOOD, amp=0.015, freq=16, seed=1))
    tor = bm_lathe([(0.0, 0.72), (0.13, 0.725), (0.17, 0.8), (0.185, 0.9), (0.178, 0.98), (0.13, 1.035), (0.0, 1.045)], seg=14, sy=0.74)
    tor = subdivide(tor, 2 if not sil else 1)
    if sil:
        R.add('Body', tor, W)
    else:
        edge = 0.86
        if unfinished == 'torso':   # front plate carved, back half of the barrel still a pencil construction
            pass
        brush(R, 'Body', tor, edge, top, n=7, ln=0.1, w=0.014, seed=2)
        R.add('Body', tor, WOOD, face_mat=paint_above(edge, top, amp=0.012, freq=16, seed=2))
        if bot:
            brush(R, 'Hips', bm_box((0, 0, 0.665), (0.25, 0.16, 0.13)), 0.62, bot, n=6, ln=0.05, w=0.02, seed=3)
    R.add('Body', ball((0, 0, 0.705), 0.045, seg=10, rings=7), J)
    R.add('Head', capsule((0, 0, 1.04), (0, -0.005, 1.1), 0.026, 0.024, seg=7), W)
    R.add('Head', ball((0, 0, 1.075), 0.03, seg=8, rings=6), J)
    # limbs (shared), with per-variant unfinished parts
    skip_fore = (unfinished == 'forearmL', unfinished == 'armR')
    puppet_limbs(R, d, mat=W, jmat=J, hands=('mitten', 'mitten'), foot=(0.15, 0.08, 0.06),
                 sleeve=None if sil else (top, 0.5, 1.3), shorts=None if sil else (bot, 0, 0.55, 1.35),
                 skip_fore=skip_fore, ink_shin=(False, 'skip' if unfinished == 'shinR' else False))
    if unfinished == 'forearmL':
        el, wr = V((0.19, 0, 0.8)), V((0.2, 0, 0.61))
        torn_limb(R, 'ForeArmL', 'ForeArmL', el - V((0, 0, 0.02)), wr, 0.028, 0.023, frac=0.45, lw=0.004, seed=11)
        ink_hand(To(R, 'HandL'), wr, (wr - el).normalized(), ln=0.1, side=1, r=0.0035)
    if unfinished == 'armR':   # whole forearm + hand only drawn; upper arm torn at the elbow
        el, wr = V((-0.19, 0, 0.8)), V((-0.2, 0, 0.61))
        sketch_cyl(R, 'ForeArmR', el, wr, 0.028, 0.023, lw=0.004, rings=3, longs=4, seed=13)
        ink_hand(To(R, 'HandR'), wr, (wr - el).normalized(), ln=0.1, side=-1, r=0.0035)
    if unfinished == 'shinR':   # shin torn below the knee, the rest only drawn; the foot is solid again
        kn, an = V((-0.09, -0.008, 0.37)), V((-0.092, 0, 0.068))
        torn_limb(R, 'ShinR', 'ShinR', kn - V((0, 0, 0.02)), an + V((0, 0, 0.01)), 0.033, 0.027, frac=0.38, lw=0.004, seed=21)
    # heads
    hp = V((0, 0, 1.075))
    if head == 'egg':
        hc = V((0, -0.01, 1.255))
        hc = V((0, -0.012, 1.285))
        hb = faceted_head('egg', hc, (0.14, 0.125, 0.2), seed=16)
        eyes = [(0.05, 0.035, 0.034, 'hole'), (-0.052, 0.0, 0.018, 'slot')]
        tuft = [(RED, (-0.05, 0.0, 0.14), 0.11), (BLUE, (-0.02, 0.02, 0.15), 0.08)]
        hr = 0.15
    elif head == 'box':
        hc = V((0, -0.012, 1.225))
        hb = faceted_head('box', hc, (0.16, 0.14, 0.135), seed=26)
        rot(hb, 'Y', -8, hc)
        eyes = [(0.068, 0.04, 0.032, 'hole'), (-0.058, -0.014, 0.038, 'hole'), (0.024, -0.07, 0.019, 'hole')]
        tuft = [(RED, (-0.08, 0.0, 0.11), 0.08)]
        hr = 0.14
    else:   # bean, tilted, drawn ring eye
        hc = V((0.01, -0.03, 1.22))
        hb = faceted_head('bean', hc, (0.18, 0.13, 0.135), seed=37)
        rot(hb, 'Y', -14, hc)
        eyes = [(0.06, 0.022, 0.034, 'hole'), (-0.06, 0.014, 0.036, 'ring')]
        tuft = [(BLUE, (0.0, 0.02, 0.1), 0.09)]
        hr = 0.14
    hbv = BVHTree.FromBMesh(hb)
    R.add('Head', hb, W, smooth=False, face_mat=None if sil else paint_above(hc.z + 0.07, top, amp=0.02, freq=14, seed=17))
    if not sil:
        for nm, (dx, dz, r, st) in zip(('a', 'b', 'c'), eyes):
            hit = hbv.ray_cast(V((hc.x + dx, -3, hc.z + dz)), V((0, 1, 0)))
            if hit[0] is None:
                continue
            c, n = hit[0], hit[1]
            if st == 'ring':
                ring = [c + n * 0.003 + V((math.cos(2 * math.pi * i / 14) * r, 0, math.sin(2 * math.pi * i / 14) * r * 1.05)) for i in range(15)]
                R.add('Head', stroke(ring, 0.005, taper=False), INK, smooth=False)
                R.add('Head', oriented_eye(c + n * 0.002, n, (r * 0.3, 0.004, r * 0.32)), INK)
            else:
                R.add('Head', oriented_eye(c - n * 0.004, n, (r, 0.012, r * (2.0 if st == 'slot' else 1.15))), INK)
        for k, (m, off, ln) in enumerate(tuft):
            p0 = hc + V(off)
            pts = [p0, p0 + V((0.01, 0.02, ln * 0.5)), p0 + V((0.03, 0.05, ln))]
            R.add('Head', bm_blade(pts, [ln * 0.18, ln * 0.2, ln * 0.04], thick=ln * 0.05, up=(0, 1, 0)), m, smooth=False)
        if unfinished == 'headback':
            pass
    puppet_meta(R, d, 1.48 if head == 'egg' else 1.37, hc, hr * 1.18, (0, 0, 0.88), 0.18, foot=(0.15, 0.08, 0.06))
    if unfinished == 'armR':
        R.meta['hand'] = 'L'
    if unfinished == 'shinR':   # stooped elder posture is part of the rest pose of every clip
        R.meta['rest_pose'] = {'B.ArmL.z': 5.0, 'B.ArmR.z': -5.0, 'B.ForeArmL.x': -18.0, 'B.ForeArmR.x': -14.0,
                               'B.Body.x': 16.0, 'B.Head.x': -12.0, 'B.ArmL.x': -8.0, 'B.ArmR.x': -6.0}
    villager_clips(R)
    return R


def villager_clips(R):
    D = A.Dims(R)

    def wobble(ch, t, ph, cL, b_):
        ch['B.Head.z'] = ch.get('B.Head.z', 0) + 3 * cL
        return ch
    R.clips.append(('Idle',) + A.c_idle(R, D, 3.2))
    R.clips.append(('Walk',) + A.locomotion(R, D, 2.2, 16, stance=0.34, lift=0.07, bob=0.025, lean=5, arm=20, yaw=7,
                                            roll=4, elbow=14, crouch=0.0, extra=wobble))
    R.meta['speeds'] = {'Walk': 2.2}
    common_gestures(R, D, beckon=True, lookback=False, gather=True, sit=True, reach=True, kneel=True)


def build_villager_a():
    return villager('Villager_A', 'egg', (BLUE, RED), 'forearmL')


def build_villager_b():
    return villager('Villager_B', 'box', (RED, BLUE), 'armR')


def build_villager_c():
    return villager('Villager_C', 'bean', (BLUE, RED), 'shinR')


def build_silhouette_a():
    return villager('Silhouette_A', 'egg', (None, None), None, sil=True)


def build_silhouette_b():
    return villager('Silhouette_B', 'box', (None, None), None, sil=True)


# =====================================================================================  MOTHER
def build_mother():
    """Mother: tall pear-bellied puppet (~2 m), small head with one slot eye, long cloth in the right hand."""
    R = RigChar('Mother')
    d = dict(hip=(0.13, 0.0, 0.5), knee=(0.14, -0.01, 0.28), ankle=(0.145, 0, 0.065),
             sh=(0.19, 0, 1.42), el=(0.29, -0.03, 1.1), wr=(0.31, -0.05, 0.8), r_leg=0.045, r_arm=0.036, hand=0.1, scale=2.0)
    puppet_bones(R, d, head_pivot=(0, -0.02, 1.6), waist=(0, 0, 0.6), hips=(0, 0, 0.52))
    R.bone('Cloth', 'HandR', (-0.32, -0.06, 0.75))
    # pear body: soft-skinned between Hips (bottom) and Body (top)
    pear = bm_lathe([(0.0, 0.42), (0.2, 0.44), (0.33, 0.58), (0.37, 0.78), (0.335, 1.0), (0.25, 1.2), (0.17, 1.38), (0.12, 1.5), (0.0, 1.56)], seg=18, sy=0.88)
    deform(pear, lambda c: V((c.x, c.y - 0.13 * math.exp(-((c.z - 0.8) / 0.26) ** 2) * max(0.0, -c.y / 0.33), c.z)))
    pear = subdivide(pear, 1)
    jitter(pear, 0.008, 4, 52)
    pw = blend_w(lambda c: c.z, 'Hips', 'Body', 0.58, 0.8)
    for mat, z, down, sd in ((BLUE, 1.08, True, 53), (RED, 0.66, False, 54)):
        rnd = random.Random(sd)
        bvh = BVHTree.FromBMesh(pear)
        for k in range(10):
            a = 2 * math.pi * (k + rnd.uniform(-0.4, 0.4)) / 10
            ln = rnd.choice((0.08, 0.13, 0.18, 0.25))
            pts, nr = [], []
            for t in range(7):
                zz = z + (-1 if down else 1) * (ln * t / 6 - 0.008)
                dd = V((math.cos(a), math.sin(a), 0))
                hit = bvh.ray_cast(V((0, 0, zz)) + dd * 3, -dd)
                if hit[0] is None:
                    break
                pts.append(hit[0] + hit[1] * 0.0025)
                nr.append(hit[1])
            if len(pts) > 2:
                ww = [0.045 * f for f in (1, 0.95, 0.85, 0.7, 0.5, 0.3, 0.06)][:len(pts)]
                R.add(pw, bm_blade(pts, ww, thick=0.0015, up=tuple(nr[len(nr) // 2])), BRUSH[mat], smooth=False)
    R.add(pw, pear, WOOD, face_mat=L.chain(paint_above(1.08, BLUE, amp=0.02, freq=9, seed=53), paint_below(0.66, RED, amp=0.025, freq=8, seed=54)))
    # the back of the belly was never finished: a ragged pencil-drawn hatch zone (construction ellipses) on the back
    for k, (z, r) in enumerate(((0.62, 0.34), (0.8, 0.37), (0.98, 0.33))):
        pts = ring_pts(V((0, 0.02, z)), (0, 0, 1), r * 1.04, 16, 0.03, k, math.radians(20), 0.38)
        R.add('Body' if z > 0.75 else 'Hips', stroke(pts, 0.004), PENCIL, smooth=False)
    R.add('Body', ball((0, 0, 1.58), 0.045, seg=8, rings=6), JOINT)
    R.add('Head', capsule((0, -0.01, 1.55), (0, -0.04, 1.66), 0.032, 0.028, seg=7), WOOD)
    puppet_limbs(R, d, hands=('none', 'mitten'), foot=(0.17, 0.095, 0.065), sleeve=(BLUE, 0.5, 1.3), skip_fore=(True, False))
    # left forearm torn off and continued as pencil, ink hand
    el, wr = V((0.29, -0.03, 1.1)), V((0.31, -0.05, 0.8))
    torn_limb(R, 'ForeArmL', 'ForeArmL', el - V((0, 0, 0.02)), wr, 0.031, 0.026, frac=0.5, lw=0.0045, seed=61)
    ink_hand(To(R, 'HandL'), wr, (wr - el).normalized(), ln=0.13, side=1, r=0.004)
    # head: small tall egg, one long slot eye, blue paint cap + tuft
    hc = V((0, -0.06, 1.8))
    hb = faceted_head('egg', hc, (0.11, 0.105, 0.16), seed=57)
    hbv = BVHTree.FromBMesh(hb)
    R.add('Head', hb, WOOD, smooth=False, face_mat=paint_above(1.88, BLUE, amp=0.02, freq=14, seed=58))
    hit = hbv.ray_cast(V((0.0, -3, 1.82)), V((0, 1, 0)))
    R.add('Head', oriented_eye(hit[0] - hit[1] * 0.004, hit[1], (0.02, 0.012, 0.05)), INK)
    for m, off, ln in ((BLUE, (-0.04, 0.02, 0.13), 0.1), (RED, (-0.01, 0.03, 0.14), 0.07)):
        p0 = hc + V(off)
        pts = [p0, p0 + V((0.01, 0.02, ln * 0.5)), p0 + V((0.03, 0.05, ln))]
        R.add('Head', bm_blade(pts, [ln * 0.18, ln * 0.2, ln * 0.04], thick=ln * 0.05, up=(0, 1, 0)), m, smooth=False)
    # cloth hanging from the right hand (own bone, sways)
    h0 = V((-0.32, -0.06, 0.75))
    pts = [h0, h0 + V((0.03, -0.04, -0.2)), h0 + V((-0.01, -0.02, -0.4)), h0 + V((0.02, 0.03, -0.55)), h0 + V((-0.03, 0.0, -0.62))]
    c = bm_blade(pts, [0.06, 0.12, 0.13, 0.12, 0.1], thick=0.012, up=(0, 1, 0.1))
    c = subdivide(c, 1)
    deform(c, lambda q: q + V((0, 0.03 * math.sin((q.z - h0.z) * 9), 0)))
    R.add('Cloth', c, 'M_Paper')
    for k in range(3):
        e0 = pts[-1] + V((-0.07 + 0.07 * k, 0, 0.0))
        R.add('Cloth', stroke([e0, e0 + V((0.005 * k, 0.0, -0.07 - 0.02 * k))], 0.005), INK, smooth=False)
    puppet_meta(R, d, 2.0, hc, 0.16, (0, 0, 0.85), 0.37, foot=(0.17, 0.095, 0.065))
    R.meta['rest_pose'] = {'B.ArmL.z': 8.0, 'B.ArmR.z': -8.0, 'B.ForeArmL.x': -14.0, 'B.ForeArmR.x': -20.0, 'B.Head.x': 6.0}
    D = A.Dims(R)

    def sway(ch, t, ph, cL, b_):
        ch['B.Cloth.x'] = 8 + 10 * b_
        ch['B.Cloth.z'] = 6 * cL
        ch['B.Body.z'] = ch.get('B.Body.z', 0) + 3 * cL   # pear waddle
        return ch
    R.clips.append(('Idle',) + A.c_idle(R, D, 3.4))
    R.clips.append(('Walk',) + A.locomotion(R, D, 2.2, 14, stance=0.32, lift=0.06, bob=0.03, lean=4, arm=16, yaw=6,
                                            roll=6, elbow=16, crouch=0.02, extra=sway))
    R.meta['speeds'] = {'Walk': 2.2}
    common_gestures(R, D, beckon=True, lookback=False, gather=True, sit=True, reach=True, kneel=True)
    return R


# =====================================================================================  HERO (human child traveler, bluebird concept)
L.MATS.update({
    'M_Skin':         ('F1C7A2', 'C9946F', True, 'painted', {'note': 'hero skin (the only fully coloured being)'}),
    'M_Hair':         ('2A3157', '171C37', True, 'painted', {'note': 'hero hair: blue-black like the bluebird head'}),
    'M_HeroShirt':    ('E8EBF1', 'B1B9CA', True, 'painted', {'note': 'hero loose shirt: grey-white like the bluebird belly'}),
    'M_HeroTrousers': ('343A52', '1F2438', True, 'painted', {'note': 'hero dark trousers'}),
})
L.MATS.update({
    'M_Hair':          ('1C2138', '0E1120', True, 'painted', {'note': 'hero hair: blue-black, darker than the navy cap so cap and hair read apart'}),
    'M_HeroEyeWhite':  ('F6F3EC', 'D9D4CA', False, 'painted', {'note': 'hero eye whites (flush decal, no outline)'}),
    'M_HeroIris':      ('2E5BB8', '1D3C80', False, 'painted', {'note': 'hero iris: cobalt (bluebird), no outline'}),
    'M_Blush':         ('EDB09A', 'D99A84', False, 'painted', {'note': 'hero cheek blush decal, no outline'}),
    'M_SkinLine':      ('B97A5E', 'B97A5E', False, 'line', {'note': 'soft skin-tone line (lower lid, nose side, ear curl)'}),
    'M_SkinSoft':      ('F1C7A2', 'C9946F', False, 'painted', {'note': 'hero skin WITHOUT outline (nose: an ink ring around it reads as a clown nose)'}),
    'M_HairIn':        ('1C2138', '0E1120', False, 'painted', {'note': 'inside of the hair shell, no outline'}),
    'M_HairLine':      ('3B4A7A', '3B4A7A', False, 'line', {'note': 'thin cobalt-grey strand lines drawn on the hair mass'}),
})
NEW_MATS.update({k: L.MATS[k] for k in ('M_Skin', 'M_Hair', 'M_HeroShirt', 'M_HeroTrousers', 'M_HeroEyeWhite', 'M_HeroIris', 'M_Blush', 'M_SkinLine', 'M_SkinSoft', 'M_HairIn', 'M_HairLine')})


def seg_w(a, b, bone_a, bone_b, blend):
    """Weights along a limb: bone_a before joint b, bone_b after it, blended over +-blend metres."""
    a, b = V(a), V(b)
    d = (b - a).normalized()

    def fn(co):
        t = (co - b).dot(d)
        w = A.smooth((t + blend) / (2 * blend))
        return {bone_a: 1 - w, bone_b: w}
    return fn


def build_hero():
    R = RigChar('Hero_Bluebird')
    SKIN, HAIR, SHIRT, TROU, NAVY, COB = 'M_Skin', 'M_Hair', 'M_HeroShirt', 'M_HeroTrousers', 'M_CapNavy', 'M_Bluebird'
    d = dict(hip=(0.085, 0, 0.6), knee=(0.09, -0.012, 0.335), ankle=(0.095, 0, 0.078),
             sh=(0.155, 0.0, 0.845), el=(0.18, 0.005, 0.67), wr=(0.19, -0.01, 0.51), r_leg=0.055, r_arm=0.045, hand=0.07, scale=1.25)
    puppet_bones(R, d, head_pivot=(0, 0, 0.885), waist=(0, 0, 0.66), hips=(0, 0, 0.62))
    R.bone('Cape', 'Body', (0, 0.06, 0.89))
    rnd = random.Random(5)
    bw = blend_w(lambda c: c.z, 'Hips', 'Body', 0.63, 0.72)

    # ---------------- torso: loose white shirt, belt, trousers seat
    shirt = bm_lathe([(0.0, 0.6), (0.13, 0.61), (0.15, 0.66), (0.148, 0.72), (0.152, 0.78), (0.15, 0.83), (0.11, 0.875), (0.05, 0.895), (0.0, 0.9)],
                     seg=18, sy=0.78)
    deform(shirt, lambda c: c + V((0, -0.012 * math.exp(-((c.z - 0.7) / 0.06) ** 2), 0)))   # slight blouse over the belt
    R.add(bw, shirt, SHIRT)
    # collar points + placket
    for x in (1, -1):
        p0 = V((0.012 * x, -0.1, 0.885))
        R.add('Body', bm_blade([p0, p0 + V((0.03 * x, -0.012, -0.03)), p0 + V((0.045 * x, -0.0, -0.045))], [0.014, 0.018, 0.004],
                               thick=0.006, up=(0, -1, 0.3)), SHIRT, smooth=False)
    belt = bm_tube(ring_pts(V((0, 0, 0.635)), (0, 0, 1), 0.142, 18), 0.02, seg=4, cap=False, flat=0.45, up=(0, 0, 1))
    deform(belt, lambda c: V((c.x, c.y * 0.8, c.z)))
    R.add('Hips', belt, 'M_Leather', smooth=False)
    bk = bm_box((0, -0.115, 0.635), (0.035, 0.012, 0.03))
    R.add('Hips', L.bevel(bk, 0.005, 1, 40), 'M_Brass', smooth=False)
    seat = bm_sphere((0, 0.005, 0.59), (0.135, 0.105, 0.075), seg=14, rings=8)
    R.add('Hips', seat, TROU)
    # satchel strap: right shoulder -> left hip, bag on the left hip
    sb = BVHTree.FromBMesh(shirt)
    strap = []
    cen = V((0, 0, 0.75))
    nrm = V((0.62, 0.0, 1.0)).normalized()
    ax1 = V((0, 1, 0))
    ax2 = nrm.cross(ax1).normalized()
    for i in range(33):
        a = 2 * math.pi * i / 32
        dd = (ax1 * math.cos(a) + ax2 * math.sin(a)).normalized()
        h = sb.ray_cast(cen + dd * 0.6, -dd)
        if h[0] is not None:
            strap.append(h[0] + h[1] * 0.01)
    # 10/23: satchel + strap are their own skinned object `Satchel` (code can hide / swap the bag; same weights as before)
    R.add(bw, bm_tube(strap, 0.016, seg=4, cap=False, flat=0.35, up=(0, 0, 1)), 'M_Leather', smooth=False, obj='Satchel')
    bag_c = V((0.175, -0.07, 0.6))
    for sz, off, m in (((0.06, 0.17, 0.15), (0, 0, 0), 'M_Leather'), ((0.068, 0.175, 0.075), (0.004, 0, 0.05), 'M_Leather'),
                       ((0.012, 0.035, 0.04), (0.04, -0.01, 0.03), 'M_Brass')):
        bx = bm_box((0, 0, 0), sz)
        bx = L.bevel(bx, min(sz) * 0.3, 2, 40)
        rot(bx, 'Z', 18)
        move(bx, bag_c + V(off))
        R.add('Hips', bx, m, smooth=False, obj='Satchel')

    # ---------------- legs: loose dark trousers tucked into chunky boots
    for s, x in (('L', 1), ('R', -1)):
        hip, knee, ank = [V((p[0] * x, p[1], p[2])) for p in (d['hip'], d['knee'], d['ankle'])]
        tr = bm_tube([hip + V((0, 0, 0.03)), hip.lerp(knee, 0.5), knee, knee.lerp(ank, 0.45)], [0.068, 0.064, 0.056, 0.058], seg=12)
        R.add(seg_w(hip, knee, 'Leg' + s, 'Shin' + s, 0.04), tr, TROU)
        shaft = bm_lathe([(0.052, 0.07), (0.058, 0.1), (0.062, 0.2), (0.066, 0.215), (0.06, 0.222)], seg=12, center=(ank.x, ank.y + 0.004, 0))
        R.add('Shin' + s, shaft, 'M_Leather', smooth=False)
        foot = bm_box((0, 0, 0), (0.1, 0.2, 0.085))
        foot = L.bevel(foot, 0.032, 2, 40)
        deform(foot, lambda c: c + V((0, 0, -0.012 * max(0.0, (-c.y - 0.04) / 0.06) * (c.z > 0))))
        move(foot, (ank.x, -0.045, 0.05))
        R.add('Foot' + s, foot, 'M_Leather')
        sole = bm_box((ank.x, -0.045, 0.011), (0.106, 0.205, 0.022))
        R.add('Foot' + s, L.bevel(sole, 0.007, 1, 40), 'M_Beak', smooth=False)
        R.add('Foot' + s, L.bevel(bm_box((ank.x + 0.05 * x, -0.03, 0.075), (0.008, 0.03, 0.026)), 0.003, 1, 40), 'M_Brass', smooth=False)
        R.add('Shin' + s, bm_tube(ring_pts(V((ank.x, ank.y + 0.004, 0.2)), (0, 0, 1), 0.064, 12), 0.008, seg=4, cap=False), 'M_Leather', smooth=False)

    # ---------------- arms: puffy sleeves with cuffs, skin hands with thumbs
    for s, x in (('L', 1), ('R', -1)):
        sh, el, wr = [V((p[0] * x, p[1], p[2])) for p in (d['sh'], d['el'], d['wr'])]
        sl = bm_tube([sh + V((-0.02 * x, 0, 0.02)), sh.lerp(el, 0.5), el, el.lerp(wr, 0.55), wr + (wr - el).normalized() * 0.01],
                     [0.052, 0.048, 0.045, 0.054, 0.04], seg=12)
        R.add(seg_w(sh, el, 'Arm' + s, 'ForeArm' + s, 0.035), sl, SHIRT)
        cuff = bm_tube(ring_pts(wr, el - wr, 0.04, 12), 0.009, seg=4, cap=False)
        R.add('ForeArm' + s, cuff, SHIRT, smooth=False)
        dd = (wr - el).normalized()
        palm = bm_sphere((0, 0, 0), (0.026, 0.036, 0.046), seg=10, rings=7)
        L.xform(palm, dd.to_track_quat('-Z', 'Y').to_matrix().to_4x4())
        move(palm, wr + dd * 0.045)
        R.add('Hand' + s, palm, SKIN)
        th = bm_tube([wr + dd * 0.02 + V((0, -0.02, 0)), wr + dd * 0.045 + V((0, -0.04, 0))], [0.012, 0.01], seg=6)
        R.add('Hand' + s, th, SKIN)

    # ---------------- neck + head v3 (10/23 face pass: storybook face, designed hair, proper cap)
    R.add(blend_w(lambda c: c.z, 'Body', 'Head', 0.875, 0.9), bm_tube([V((0, 0, 0.84)), V((0, -0.005, 0.93))], [0.042, 0.04], seg=12), SKIN)
    hc = V((0, -0.012, 1.035))
    hr = (0.138, 0.134, 0.15)
    h = bm_sphere(hc, hr, seg=36, rings=24)

    def sculpt(c):
        rel = c - hc
        zn = rel.z / hr[2]
        if zn < 0:   # jaw tapers to a soft rounded chin
            k = 1 - 0.2 * zn * zn
            c.x = hc.x + rel.x * k
            c.y = hc.y + rel.y * (1 - 0.08 * zn * zn)
        if rel.y < 0:   # face plane a little flatter, cheeks full just below the eyes
            fwd = -rel.y / hr[1]
            c.y = hc.y + rel.y * (1 - 0.06 * fwd)
            cheek = math.exp(-((zn + 0.28) / 0.22) ** 2) * math.exp(-((abs(rel.x) / hr[0] - 0.55) / 0.3) ** 2)
            c += V((math.copysign(0.006, rel.x), -0.004, 0)) * cheek
        if rel.y > 0 and zn > -0.2:   # cranium a touch fuller at the back
            c.y += 0.01 * (rel.y / hr[1]) * (1 + zn) * 0.5
        return c
    deform(h, sculpt)
    hb = BVHTree.FromBMesh(h)
    R.add('Head', h, SKIN)

    def on_head(p, lift=0.0015, bvh=None):
        bvh = bvh or hb
        d = (p - hc).normalized()
        hit = bvh.ray_cast(hc + d * 0.4, -d)
        return (hit[0] + hit[1] * lift, hit[1]) if hit[0] is not None else (p, d)

    def disc(c, t, b, rx, ry, lift, seg=18, squash_top=0.0):
        """Small ellipse decal conformed to the head surface."""
        bm_ = L.bmesh.new()
        cen, _ = on_head(c, lift)
        cv = bm_.verts.new(cen)
        ring = []
        for i in range(seg):
            a = 2 * math.pi * i / seg
            yy = math.sin(a) * ry * (1 - squash_top * max(0.0, math.sin(a)))
            p, _ = on_head(c + t * math.cos(a) * rx + b * yy, lift)
            ring.append(bm_.verts.new(p))
        for i in range(seg):
            bm_.faces.new((cv, ring[i], ring[(i + 1) % seg]))
        L.bmesh.ops.recalc_face_normals(bm_, faces=bm_.faces)
        for f in bm_.faces:   # face outward
            if f.normal.dot(f.calc_center_median() - hc) < 0:
                f.normal_flip()
        return bm_

    # ears (with an inner curl line)
    for x in (1, -1):
        ec = hc + V((0.133 * x, 0.012, -0.012))
        e = bm_sphere(ec, (0.016, 0.026, 0.033), seg=12, rings=8)
        R.add('Head', e, SKIN)
        R.add('Head', stroke([ec + V((0.012 * x, -0.008, 0.016)), ec + V((0.015 * x, -0.012, 0.0)), ec + V((0.013 * x, -0.004, -0.016))], 0.0018), 'M_Skin', smooth=False)
    # eyes: almond whites, cobalt iris, pupil, highlight, upper lid line with an outer flick
    for x in (1, -1):
        ec = hc + V((0.05 * x, -0.13, -0.008))
        ec, n = on_head(ec, 0.0)
        t = V((0, 0, 1)).cross(n).normalized() * (-1)
        if t.x * x < 0:
            t = -t
        b = n.cross(t).normalized()
        if b.z < 0:
            b = -b
        rx, ry = 0.02, 0.0155
        R.add('Head', disc(ec, t, b, rx, ry, 0.0012, squash_top=0.12), 'M_HeroEyeWhite', smooth=False)
        ic = ec - t * 0.003 * x * 0 + b * 0.001 - t * 0.0025 * x   # look slightly inward/forward
        R.add('Head', disc(ic, t, b, 0.0115, 0.0128, 0.0021), 'M_HeroIris', smooth=False)
        R.add('Head', disc(ic, t, b, 0.0062, 0.0068, 0.0028), INK, smooth=False)
        R.add('Head', disc(ic + t * 0.0045 * x + b * 0.0055, t, b, 0.0032, 0.0034, 0.0034, seg=10), 'M_EyeShine', smooth=False)
        lid = []
        for i in range(9):
            a = math.pi * (0.04 + 0.92 * i / 8)
            p = ec + t * (-math.cos(a) * rx * 1.06) * x + b * (math.sin(a) * ry * 1.05 - 0.001)
            lid.append(on_head(p, 0.0034)[0])
        lid.append(on_head(ec + t * (rx * 1.28) * x + b * (ry * 0.55), 0.0034)[0])   # outer flick
        R.add('Head', stroke(lid, 0.0021, taper=True), INK, smooth=False)
        low = [on_head(ec + t * (-math.cos(a) * rx * 0.9) * x - b * (math.sin(a) * ry * 0.95), 0.0024)[0]
               for a in (math.pi * (0.3 + 0.4 * i / 4) for i in range(5))]
        R.add('Head', stroke(low, 0.0011, taper=True), 'M_SkinLine', smooth=False)
        # brow: slim arched stroke, the left one raised a touch (curious)
        br_ = [on_head(ec + t * (u * 0.024) * x + b * (0.031 + 0.005 * math.cos(u * 1.4) + (0.004 if x > 0 else 0.0)), 0.0035)[0]
               for u in (-1.0, -0.4, 0.2, 0.8, 1.15)]
        R.add('Head', stroke(br_, 0.0021, taper=True), 'M_HairIn', smooth=False)
        # soft blush
        R.add('Head', disc(hc + V((0.075 * x, -0.115, -0.052)), V((1, 0, 0)), V((0, 0, 1)), 0.02, 0.012, 0.0009), 'M_Blush', smooth=False)
    # nose: small defined wedge + a shadow line on one side; mouth: short curious line, one corner up
    nb, nn_ = on_head(hc + V((0, -0.13, -0.045)), 0.0)
    nb = nb - nn_ * 0.004
    nose = bm_sphere(nb + V((0, -0.004, 0.0)), (0.011, 0.011, 0.014), seg=14, rings=10)
    deform(nose, lambda c: c + V((0, -0.006 * max(0.0, (nb.z + 0.004 - c.z) / 0.02), 0)))
    R.add('Head', nose, 'M_SkinSoft')
    R.add('Head', stroke([nb + V((0.011, -0.009, 0.004)), nb + V((0.012, -0.012, -0.008)), nb + V((0.005, -0.016, -0.014))], 0.0014), 'M_SkinLine', smooth=False)
    m0 = on_head(hc + V((0, -0.13, -0.088)), 0.0025)[0]
    R.add('Head', stroke([on_head(m0 + V((-0.019, 0.003, 0.0)), 0.0025)[0], on_head(m0 + V((-0.006, 0, -0.002)), 0.0025)[0],
                          on_head(m0 + V((0.008, 0, -0.0015)), 0.0025)[0], on_head(m0 + V((0.02, 0.003, 0.004)), 0.0025)[0]], 0.0018, taper=True),
          INK, smooth=False)
    # hair: one smooth blue-black mass whose edge is DESIGNED: three pointed bangs sweeping to the right,
    # sideburn points in front of the ears, two points at the nape; smooth crest locks at the back (bluebird)
    def hair_line(rel):
        front = max(0.0, -rel.y / hr[1])
        side = abs(rel.x) / hr[0]
        line = 0.072 * front - 0.03 * side * (1 - front) - 0.112 * (1 - front) * (rel.y > 0)
        for xb, wb, db in ((-0.062, 0.03, 0.04), (-0.018, 0.033, 0.05), (0.03, 0.03, 0.042)):   # bangs
            u = (rel.x - xb + 0.55 * (rel.z - 0.07)) / wb
            line -= db * front ** 1.5 * max(0.0, 1 - abs(u)) ** 1.3
        for sx in (1, -1):   # sideburns
            u = math.hypot((rel.x - 0.118 * sx) / 0.03, (rel.y + 0.03) / 0.035)
            line -= 0.05 * max(0.0, 1 - u)
        if rel.y > 0:   # nape points
            for xb in (-0.03, 0.035):
                line -= 0.03 * max(0.0, 1 - abs(rel.x - xb) / 0.03) * min(1.0, rel.y / hr[1] * 1.5)
        return line
    hcen = hc + V((0, 0.006, 0.004))
    HR = (hr[0] * 1.075, hr[1] * 1.09, hr[2] * 1.06)

    def ell(th, ph, k=1.0):
        return V((HR[0] * k * math.sin(th) * math.cos(ph), HR[1] * k * math.sin(th) * math.sin(ph), HR[2] * k * math.cos(th)))

    def edge_theta(ph):
        lo, hi = 0.05, 2.6          # f(lo) > 0 (above the line) ... f(hi) < 0
        for _ in range(40):
            mid = (lo + hi) / 2
            rel = hcen + ell(mid, ph) - hc
            if rel.z - hair_line(rel) > 0:
                lo = mid
            else:
                hi = mid
        return (lo + hi) / 2
    NA, NR = 112, 9
    edges = [edge_theta(2 * math.pi * j / NA) for j in range(NA)]
    for k_, flip in ((1.0, False), (0.985, True)):
        hm = L.bmesh.new()
        top = hm.verts.new(hcen + ell(0.0, 0.0, k_))
        grid = []
        for j in range(NA):
            ph = 2 * math.pi * j / NA
            col = []
            for r in range(1, NR + 1):
                th = edges[j] * (r / NR) ** 0.9
                col.append(hm.verts.new(hcen + ell(th, ph, k_)))
            grid.append(col)
        for j in range(NA):
            j2 = (j + 1) % NA
            hm.faces.new((top, grid[j][0], grid[j2][0]))
            for r in range(NR - 1):
                hm.faces.new((grid[j][r], grid[j][r + 1], grid[j2][r + 1], grid[j2][r]))
        L.bmesh.ops.recalc_face_normals(hm, faces=hm.faces)
        for f in hm.faces:
            if f.normal.dot(f.calc_center_median() - hcen) < 0:
                f.normal_flip()
        if flip:
            L.bmesh.ops.reverse_faces(hm, faces=hm.faces)
        R.add('Head', hm, HAIR if not flip else 'M_HairIn', smooth=True)
    # a few drawn strand lines in the mass (ink, thin) so it reads as hair, not a helmet
    for k, (ph0, ln) in enumerate(((-1.95, 0.7), (-1.6, 0.8), (-1.25, 0.7), (-2.4, 0.5), (-0.8, 0.5))):
        ptsl = []
        for i in range(6):
            th = 0.35 + (edge_theta(ph0 + 0.25 * i / 5) - 0.42) * (i / 5) * ln
            ptsl.append(hcen + ell(th, ph0 + 0.25 * i / 5, 1.004))
        R.add('Head', stroke(ptsl, 0.0012, taper=True), 'M_HairLine', smooth=False)
    for k, (sx, up, ln) in enumerate(((-0.035, 0.5, 0.075), (0.0, 0.8, 0.1), (0.035, 0.55, 0.08))):   # crest locks
        p0 = hc + V((sx, 0.12, 0.065))
        pts = [p0, p0 + V((sx * 0.3, ln * 0.45, ln * up * 0.6)), p0 + V((sx * 0.7, ln * 0.85, ln * up)), p0 + V((sx * 1.1, ln * 1.05, ln * up * 0.75))]
        R.add('Head', bm_tube(pts, [0.016, 0.014, 0.008, 0.0015], seg=8, flat=0.5, up=(1, 0, 0)), HAIR, smooth=True)
    # newsboy cap pushed back: 8-panel puffy crown with seams, cobalt band (separates cap from hair), stiff curved brim
    capc = hc + V((0.006, 0.03, 0.09))
    tilt = -18
    prof = [(0.0, 0.118), (0.06, 0.116), (0.108, 0.106), (0.142, 0.088), (0.158, 0.062), (0.156, 0.036), (0.143, 0.012), (0.132, 0.0)]
    crown = bm_lathe(prof, seg=32, center=capc, sx=1.0, sy=1.06, cap_bottom=True)
    deform(crown, lambda co: co + V((0, -0.045 * max(0, co.z - capc.z - 0.03) / 0.07, 0)))
    crb = BVHTree.FromBMesh(crown)
    for ri in range(8):
        a = 2 * math.pi * (ri + 0.5) / 8
        sp = []
        for r_, z_ in prof[1:6]:
            pp = capc + V((math.cos(a) * r_, math.sin(a) * r_ * 1.06, z_))
            pp = pp + V((0, -0.045 * max(0, pp.z - capc.z - 0.03) / 0.07, 0))
            dd = (pp - (capc + V((0, 0, 0.02)))).normalized()
            hit = crb.ray_cast(pp + dd * 0.05, -dd)
            if hit[0] is not None:
                sp.append(hit[0] + hit[1] * 0.0006)
        if len(sp) > 2:
            sb_ = stroke(sp, 0.001, taper=True)
            rot(sb_, 'X', tilt, capc)
            R.add('Head', sb_, INK, smooth=False)
    rot(crown, 'X', tilt, capc)
    R.add('Head', crown, NAVY)
    band = bm_tube([capc + V((math.cos(2 * math.pi * i / 32) * 0.134, math.sin(2 * math.pi * i / 32) * 0.142, 0.006)) for i in range(33)], 0.008,
                   seg=6, cap=False, flat=1.6, up=(0, 0, 1))
    rot(band, 'X', tilt, capc)
    R.add('Head', band, COB, smooth=True)
    # brim: crescent shell in front, 5 mm thick, curving down at the edge
    brm = L.bmesh.new()
    top_i, top_o, bot_i, bot_o = [], [], [], []
    for i in range(17):
        a = math.radians(-152 + 124 * i / 16)
        r0 = 0.13
        ext = 0.052 * math.sin(math.pi * i / 16) ** 0.7 + 0.004
        z_o = -0.012 * math.sin(math.pi * i / 16)
        pi_ = capc + V((math.cos(a) * r0, math.sin(a) * r0 * 1.06, 0.003))
        po_ = capc + V((math.cos(a) * (r0 + ext), math.sin(a) * (r0 + ext) * 1.06, 0.003 + z_o))
        top_i.append(brm.verts.new(pi_))
        top_o.append(brm.verts.new(po_))
        bot_i.append(brm.verts.new(pi_ - V((0, 0, 0.005))))
        bot_o.append(brm.verts.new(po_ - V((0, 0, 0.005))))
    for i in range(16):
        brm.faces.new((top_i[i], top_o[i], top_o[i + 1], top_i[i + 1]))
        brm.faces.new((bot_i[i + 1], bot_o[i + 1], bot_o[i], bot_i[i]))
        brm.faces.new((top_o[i], bot_o[i], bot_o[i + 1], top_o[i + 1]))
        brm.faces.new((bot_i[i], top_i[i], top_i[i + 1], bot_i[i + 1]))
    brm.faces.new((top_i[0], bot_i[0], bot_o[0], top_o[0]))
    brm.faces.new((top_o[-1], bot_o[-1], bot_i[-1], top_i[-1]))
    L.bmesh.ops.recalc_face_normals(brm, faces=brm.faces)
    rot(brm, 'X', tilt, capc)
    R.add('Head', brm, NAVY, smooth=False)
    edge = [capc + V((math.cos(math.radians(-152 + 124 * i / 16)) * (0.13 + 0.052 * math.sin(math.pi * i / 16) ** 0.7 + 0.004),
                      math.sin(math.radians(-152 + 124 * i / 16)) * (0.13 + 0.052 * math.sin(math.pi * i / 16) ** 0.7 + 0.004) * 1.06,
                      0.0035 - 0.012 * math.sin(math.pi * i / 16))) for i in range(17)]
    es = stroke(edge, 0.0018, taper=False)
    rot(es, 'X', tilt, capc)
    R.add('Head', es, INK, smooth=False)
    for cc, rr in ((capc + V((0, -0.04, 0.116)), (0.013, 0.013, 0.007)), (capc + V((0.13, -0.06, 0.026)), (0.009, 0.009, 0.009))):
        bt = bm_sphere(cc, rr, seg=10, rings=6)
        rot(bt, 'X', tilt, capc)
        R.add('Head', bt, 'M_Brass')
    # feather tucked in the band at the left: cobalt vane + grey-white under-feather, ink quill
    for k, (dz, ln, wv, m) in enumerate(((0.0, 0.12, 0.016, COB), (0.008, 0.085, 0.012, 'M_BluebirdBelly'))):
        p0 = capc + V((0.13, -0.046 + 0.01 * k, 0.032 + dz))
        pts = [p0, p0 + V((0.012, 0.035, ln * 0.45)), p0 + V((0.02, 0.07, ln * 0.85)), p0 + V((0.02, 0.09, ln))]
        fb = bm_blade(pts, [0.004, wv, wv * 0.8, 0.002], thick=0.004, up=(1, 0, 0))
        rot(fb, 'X', tilt, capc)
        R.add('Head', fb, m, smooth=False)
        if k == 0:
            qs = stroke([p + V((0.003, 0, 0)) for p in pts], 0.0012, taper=True)
            rot(qs, 'X', tilt, capc)
            R.add('Head', qs, INK, smooth=False)

    # ---------------- short hooded cape: navy outside, cobalt lining, hem cut like folded wing feathers
    rows = [(0.905, 0.075), (0.885, 0.135), (0.855, 0.19), (0.81, 0.225), (0.76, 0.242), (0.71, 0.25)]
    cols = 30
    o_b = L.bmesh.new()
    gso, gsi = [], []
    for ri, (z, r) in enumerate(rows):
        ro, rin = [], []
        for j in range(cols + 1):
            a = math.radians(-90 + 34 + (360 - 68) * j / cols)
            dd = V((math.cos(a), math.sin(a), 0))
            back = max(0.0, dd.y)
            zz = z - 0.07 * back * (ri / (len(rows) - 1)) ** 1.3
            if ri == len(rows) - 1:   # feather tabs: long point every other column
                zz -= (0.05 if j % 2 == 0 else 0.0) * (0.6 + 0.4 * back)
            rr = r * (1.0 + 0.06 * back)
            p = V((dd.x * rr * 1.1, dd.y * rr * 0.95, zz))
            ro.append(o_b.verts.new(p))
            rin.append(o_b.verts.new(p - V((dd.x, dd.y, 0.0)) * 0.007 + V((0, 0, 0.002))))
        gso.append(ro)
        gsi.append(rin)
    for ri in range(len(rows) - 1):
        for j in range(cols):
            o_b.faces.new((gso[ri][j], gso[ri][j + 1], gso[ri + 1][j + 1], gso[ri + 1][j]))
            o_b.faces.new((gsi[ri][j], gsi[ri + 1][j], gsi[ri + 1][j + 1], gsi[ri][j + 1]))
    for j in range(cols):
        o_b.faces.new((gso[-1][j], gso[-1][j + 1], gsi[-1][j + 1], gsi[-1][j]))
        o_b.faces.new((gso[0][j + 1], gso[0][j], gsi[0][j], gsi[0][j + 1]))
    for ri in range(len(rows) - 1):
        o_b.faces.new((gso[ri][0], gso[ri + 1][0], gsi[ri + 1][0], gsi[ri][0]))
        o_b.faces.new((gso[ri + 1][-1], gso[ri][-1], gsi[ri][-1], gsi[ri + 1][-1]))
    L.bmesh.ops.recalc_face_normals(o_b, faces=o_b.faces)

    def cape_mat(c, n):
        rad = V((c.x, c.y, 0))
        if rad.length > 1e-6 and n.dot(rad.normalized()) < -0.2:
            return COB
        if n.z < -0.6 and c.z < 0.75:      # hem rim shows the bright lining
            return COB
        return None

    def cape_w(co):
        t = A.smooth((0.86 - co.z) / 0.12)           # 0 at the collar -> 1 at the hem
        side = A.smooth((abs(co.x) - 0.11) / 0.1) * A.smooth((0.03 - co.y) / 0.1)   # front-side panels follow the arm
        arm = ('ArmL' if co.x > 0 else 'ArmR')
        wa = 0.5 * side * t
        wc = (1 - wa) * t * (1.0 if co.y > -0.05 else 0.4)
        return {'Body': max(0.0, 1 - wa - wc), 'Cape': wc, arm: wa}
    R.add(cape_w, o_b, NAVY, smooth=True, face_mat=cape_mat)
    # hood lying on the back (down, never over the head) with a cobalt rim
    hood = bm_sphere(V((0, 0.115, 0.855)), (0.13, 0.055, 0.075), seg=14, rings=8)
    deform(hood, lambda c: c + V((0, 0, -0.03 * max(0.0, (c.y - 0.12) / 0.05))))
    R.add('Body', hood, NAVY)
    R.add('Body', bm_tube(ring_pts(V((0, 0.07, 0.885)), (0, 0.3, 1), 0.11, 16, 0.0, 0.0, math.radians(200), 0.45), 0.014, seg=5, cap=False), COB, smooth=False)
    R.add('Body', bm_sphere((0, -0.098, 0.885), (0.017, 0.01, 0.017), seg=8, rings=5), 'M_Brass')
    # turned-back front edges (lapels) show the cobalt lining from the game camera
    for x in (1, -1):
        lap = []
        for ri, (z, r) in enumerate(rows):
            a = math.radians(-90 + 34 * x) if x > 0 else math.radians(-90 - 34)
            a = math.radians(-90 + 34) if x > 0 else math.radians(270 - 34)
            dd = V((math.cos(a), math.sin(a), 0))
            lap.append(V((dd.x * r * 1.1, dd.y * r * 0.95, z)) + V((0.012 * -x, -0.006, 0)))
        ww = [0.012, 0.02, 0.026, 0.03, 0.03, 0.026]
        R.add(cape_w, bm_blade(lap, ww, thick=0.004, up=(0, -1, 0.2)), COB, smooth=False)

    # ---------------- meta, contacts, clips
    from ouat_rig import to_rig
    hp = R.bones['Head'][1]
    R.meta.update(height=1.25, kind='human', toe=0.13, heel=0.05, head_r=0.15, knee_r=0.05, arm_out=5.0,
                  head_c=tuple(to_rig(hc - hp)), mouth=tuple(to_rig(hc + V((0, -0.14, -0.075)) - hp)))
    R.meta['rest_pose'] = {'B.ArmL.z': 5.0, 'B.ArmR.z': -5.0, 'B.ForeArmL.x': -10.0, 'B.ForeArmR.x': -10.0}
    humanoid_contacts(R, sole_y=d['ankle'][2], toe=0.15, heel=0.06, knee_r=0.06, hand_r=0.035,
                      head_c=R.meta['head_c'], head_r=0.15, body_c=tuple(to_rig(V((0, 0, 0.1)))), body_r=0.15, hips_r=0.12)
    D = A.Dims(R)

    def walk_extra(ch, t, ph, cL, b_):
        ch['B.Cape.x'] = 6 + 5 * b_
        return ch

    def run_extra(ch, t, ph, cL, b_):
        ch['B.Cape.x'] = 22 + 8 * b_
        return ch
    R.clips.append(('Idle',) + A.c_idle(R, D, 2.8))
    # a planted brisk walk for a 1.25 m child tops out near 1.8 m/s; the current game speed 3.2 m/s = Run
    R.clips.append(('Walk',) + A.locomotion(R, D, 1.8, 18, stance=0.55, lift=0.06, bob=0.022, lean=4, arm=24, yaw=7,
                                            roll=3, elbow=14, crouch=-0.04, extra=walk_extra))
    R.clips.append(('Run',) + A.locomotion(R, D, 3.2, 14, stance=0.3, lift=0.1, bob=0.035, lean=12, arm=34, yaw=8,
                                           roll=3, elbow=60, crouch=0.0, th_off=32, extra=run_extra))
    R.meta['speeds'] = {'Walk': 1.8, 'Run': 3.2}
    common_gestures(R, D, beckon=False, lookback=False, gather=False, sit=False)
    R.clips.append(('Push',) + A.c_push(R, D))
    R.clips.append(('FallTumble',) + A.c_falltumble(R, D))
    R.clips.append(('LieDown',) + A.c_liedown(R, D))
    R.clips.append(('GetUp',) + A.c_getup(R, D))
    R.clips.append(('LookAround',) + A.c_lookaround(R, D))
    R.clips.append(('Kneel',) + A.c_kneel(R, D))
    R.clips.append(('Shout',) + A.c_shout(R, D))
    R.clips.append(('Shrug',) + A.c_shrug(R, D))
    return R
