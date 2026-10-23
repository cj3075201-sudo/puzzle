# -*- coding: utf-8 -*-
"""Collector (수거꾼): villager body (same skeleton as Villager_A/B/C, VDIMS) in a sack-cloth hood + poncho with a
Korean A-frame carrier (지게) on the back, hunched. Faceless-ish (dark recessed face, two pale eye points) but a talking
creature, not a silhouette. Build space: Z up, front -Y, left +X (as ouat_chars_v2)."""
import math, random
from mathutils import Vector
from mathutils.bvhtree import BVHTree
import ouat_lib as L
from ouat_lib import bm_sphere, bm_tube, bm_blade, bm_box, bm_lathe, stroke, wobble_line, rot, move, deform, jitter, subdivide, nval
from ouat_creatures import paint_above, capsule, ball
from ouat_rig import RigChar
import ouat_anim as A
import ouat_chars_v2 as CH
import ouat_clips_r6 as R6

V = Vector
WOOD, JOINT, INK, PENCIL = 'M_PuppetWood', 'M_PuppetJoint', 'M_Ink', 'M_PencilBody'
SACK, SACK_D, HOODIN, BARK = 'M_Sackcloth', 'M_SackDark', 'M_HoodInner', 'M_Bark'

# M_Sackcloth / M_SackDark are owned by ouat_offering.py (collector sacks); same values here only so this module builds alone.
L.MATS.setdefault('M_Sackcloth', ('CFC3A4', '978C76', True, 'paper', {'hatch': True, 'note': 'collector sack / rag cloth: creature-woven paper cloth (drains with the world)'}))
L.MATS.setdefault('M_SackDark', ('7F786A', '57524A', True, 'paper', {'note': 'inside of a sack, twine lashings, rag folds in deep shade'}))
NEW_MATS = {   # merged into art_materials.json by build_chars_v2.py publish
    'M_HoodInner':     ('6B5D4F', '4A4038', False, 'paper', {'note': 'Collector: dim recessed face inside the hood (a carved face in shadow, not black)'}),
}
L.MATS.update(NEW_MATS)


def build_collector():
    R = RigChar('Collector')
    d = CH.VDIMS
    CH.puppet_bones(R, d, head_pivot=(0, 0, 1.075), waist=(0, 0, 0.7), hips=(0, 0, 0.665))
    rnd = random.Random(77)
    # ---- wooden body (mostly hidden by the poncho)
    pel = L.bevel(bm_box((0, 0, 0.665), (0.25, 0.16, 0.13)), 0.04, 2, 40)
    R.add('Hips', pel, WOOD, smooth=False)
    tor = bm_lathe([(0.0, 0.72), (0.13, 0.725), (0.17, 0.8), (0.185, 0.9), (0.178, 0.98), (0.13, 1.035), (0.0, 1.045)], seg=12, sy=0.74)
    R.add('Body', tor, WOOD)
    R.add('Body', ball((0, 0, 0.705), 0.045, seg=10, rings=7), JOINT)
    R.add('Head', capsule((0, 0, 1.04), (0, -0.005, 1.1), 0.026, 0.024, seg=7), WOOD)
    CH.puppet_limbs(R, d, mat=WOOD, jmat=JOINT, hands=('mitten', 'mitten'), foot=(0.15, 0.08, 0.06))
    # cloth leg wraps (ink bands) on the shins
    for s, x in (('L', 1), ('R', -1)):
        for k in range(4):
            z = 0.14 + 0.055 * k
            c = V((0.091 * x, -0.004, z))
            ring = CH.ring_pts(c + V((0, 0, 0.012 * (k % 2))), (0, 0.15 * (1 if k % 2 else -1), 1), 0.036, 10)
            R.add('Shin' + s, stroke(ring, 0.0035, taper=False), INK, smooth=False)
    # ---- poncho (sack cloth): shoulders -> just above the knees, ragged hem that turns into pencil lines
    bw = CH.blend_w(lambda c: c.z, 'Hips', 'Body', 0.62, 0.8)
    prof = [(0.06, 1.1), (0.15, 1.07), (0.215, 1.0), (0.225, 0.9), (0.23, 0.78), (0.245, 0.66), (0.26, 0.56)]
    po = bm_lathe(prof, seg=20, sy=0.8, cap_top=False, cap_bottom=False)
    po = subdivide(po, 1)

    def rag(c):
        if c.z < 0.6:
            a = math.atan2(c.y, c.x)
            c = c + V((0, 0, 0.035 * math.sin(a * 7 + 1.3) + 0.02 * nval(c, 9, 3)))
        return c + V((0, 0.01 * max(0.0, (0.75 - c.z)), 0))   # hangs a little back (over the frame straps)
    deform(po, rag)
    jitter(po, 0.006, 6, 4)

    def po_mat(c, n):
        # two darker patches + the back side darker where the frame rubs
        if (c - V((0.12, -0.16, 0.8))).length < 0.07 or (c - V((-0.15, 0.1, 0.68))).length < 0.06:
            return SACK_D
        return None
    R.add(bw, po, SACK, smooth=True, face_mat=po_mat)
    # stitched seams (ink) down the front and the sides
    pv = BVHTree.FromBMesh(po)
    for ang in (-90, -60, -125, 0, 180):
        a = math.radians(ang)
        dd = V((math.cos(a), math.sin(a) * 0.8, 0)).normalized()
        pts = []
        for z in (1.0, 0.9, 0.8, 0.7, 0.62):
            h = pv.ray_cast(V((0, 0, z)) + dd * 2, -dd)
            if h[0] is not None:
                pts.append(h[0] + h[1] * 0.003)
        if len(pts) > 2:
            R.add(bw, stroke(pts, 0.0028, taper=True), INK, smooth=False)
            for p in pts[1:-1]:   # cross stitches
                t = V((-dd.y, dd.x, 0)) * 0.012
                R.add(bw, stroke([p - t + V((0, 0, 0.01)), p + t - V((0, 0, 0.01))], 0.0022, taper=False), INK, smooth=False)
    # rope belt
    belt = bm_tube(CH.ring_pts(V((0, 0, 0.74)), (0, 0, 1), 0.232, 20), 0.012, seg=5, cap=False)
    deform(belt, lambda c: V((c.x, c.y * 0.82, c.z + 0.01 * math.sin(math.atan2(c.y, c.x) * 3))))
    R.add(bw, belt, SACK_D, smooth=False)
    # unfinished: on the back-right the hem continues as a few pencil construction strokes (not a full ring)
    for k in range(2):
        z = 0.53 - 0.06 * k
        ring = CH.ring_pts(V((0, 0.0, z)), (0.0, 0.04, 1), 0.27 + 0.012 * k, 10, 0.05, k * 1.7, math.radians(15 + 20 * k), 0.3)
        R.add('Hips', stroke([V((p.x, p.y * 0.8, p.z)) for p in ring], 0.0028, taper=True), PENCIL, smooth=False)
    for k in range(3):
        a = math.radians(30 + 28 * k)
        p0 = V((math.cos(a) * 0.255, math.sin(a) * 0.205, 0.57))
        R.add('Hips', stroke(wobble_line(p0, p0 + V((math.cos(a) * 0.015, math.sin(a) * 0.015, -0.12)), 4, 0.008, k), 0.0028), PENCIL, smooth=False)

    # ---- hood: soft sack cowl close over the head, the peak flops back, deep oval face opening
    hc = V((0, -0.012, 1.27))
    hood = bm_sphere(hc + V((0, 0.025, 0.015)), (0.15, 0.165, 0.19), seg=18, rings=12)
    OX, OZ, OC = 0.088, 0.118, -0.015     # opening half-width, half-height, centre z offset

    def recess(c):
        q = c - hc
        e = (q.x / OX) ** 2 + ((q.z - OC) / OZ) ** 2
        if q.y < -0.04 and e < 1.0:
            c = c + V((0, 0.075 * (1 - e) ** 0.5, 0))
        if q.z > 0.06 and q.y > -0.05:      # crown sags back into the peak
            k = (q.z - 0.06) / 0.15
            c = c + V((0, 0.05 * k * k, -0.015 * k))
        if q.z < -0.1:                       # cowl flares onto the shoulders
            c = c + V((q.x * 0.25, q.y * 0.15, 0)) * min(1.0, (-0.1 - q.z) / 0.08)
        return c
    deform(hood, recess)
    jitter(hood, 0.005, 5, 9)

    def hood_mat(c, n):
        q = c - hc
        e = (q.x / (OX * 0.97)) ** 2 + ((q.z - OC) / (OZ * 0.97)) ** 2
        return HOODIN if (q.y < -0.03 and e < 1.0) else None
    R.add('Head', hood, SACK, smooth=True, face_mat=hood_mat)
    hv = BVHTree.FromBMesh(hood)
    rim = []
    for i in range(25):
        a = 2 * math.pi * i / 24
        x, z = math.cos(a) * OX * 1.04, OC + math.sin(a) * OZ * 1.04
        h = hv.ray_cast(hc + V((x, -1.0, z)), V((0, 1, 0)))
        rim.append((h[0] if h[0] is not None else hc + V((x, -0.15, z))) + V((0, 0.004, 0)))
    R.add('Head', bm_tube(rim, 0.016, seg=6, cap=False), SACK_D, smooth=True)
    # floppy peak hanging down the back
    pk = [hc + V((0, 0.06, 0.16)), hc + V((0, 0.16, 0.19)), hc + V((0.015, 0.24, 0.13)), hc + V((0.03, 0.27, 0.04)), hc + V((0.035, 0.26, -0.03))]
    R.add('Head', bm_tube(pk, [0.07, 0.055, 0.035, 0.02, 0.008], seg=8), SACK)
    # face in the shadow: carved dim face plate is the recess itself; two pale eye points + an ink brow line, no mouth
    for x in (0.034, -0.036):
        h = hv.ray_cast(hc + V((x, -1.0, OC + 0.025)), V((0, 1, 0)))
        c = (h[0] if h[0] is not None else hc + V((x, -0.1, 0.01))) + V((0, -0.006, 0))
        R.add('Head', bm_sphere(c, (0.017, 0.008, 0.02), seg=8, rings=5), 'M_FishEye')
    # capelet over the shoulders (part of the hood)
    cap = bm_lathe([(0.07, 1.15), (0.17, 1.11), (0.25, 1.03), (0.27, 0.96)], seg=18, sy=0.82, cap_top=False, cap_bottom=False)
    deform(cap, lambda c: c + (V((0, 0, 0.018 * math.sin(math.atan2(c.y, c.x) * 6))) if c.z < 1.0 else V((0, 0, 0))))
    R.add('Body', cap, SACK)

    # ---- A-frame carrier (지게) on the back (+Y), rides with Body
    poles = {}
    for x in (1, -1):
        p0 = V((0.13 * x, 0.2, 0.44))
        p1 = V((0.105 * x, 0.25, 1.58))
        poles[x] = (p0, p1)
        if x == -1:   # unfinished: the right pole's top half is only drawn
            CH.torn_limb(R, 'Body', 'Body', p0, p1, 0.022, 0.017, frac=0.6, mat=BARK, lw=0.004, seed=5)
        else:
            pb = bm_tube([p0, p0.lerp(p1, 0.5) + V((0.005, 0.01, 0)), p1], [0.022, 0.02, 0.017], seg=7)
            jitter(pb, 0.003, 5, x)
            R.add('Body', pb, BARK)
            R.add('Body', stroke([p1, p1 + V((0.01, 0.01, 0.04))], 0.004), INK, smooth=False)
    for z, solid in ((0.55, True), (0.9, True), (1.3, False), (1.52, False)):
        a = poles[1][0].lerp(poles[1][1], (z - 0.44) / 1.14)
        b = poles[-1][0].lerp(poles[-1][1], (z - 0.44) / 1.14)
        if solid:
            R.add('Body', bm_tube([a, a.lerp(b, 0.5) + V((0, 0.01, 0)), b], [0.014, 0.015, 0.014], seg=6), BARK)
        else:
            CH.sketch_cyl(R, 'Body', a, b, 0.014, 0.014, lw=0.0035, rings=2, longs=3, seed=z * 10)
    # forked prongs (지겟가지) sticking back and up, holding the load
    for x in (1, -1):
        p0 = V((0.13 * x, 0.21, 0.66))
        R.add('Body', bm_tube([p0, p0 + V((0.01 * x, 0.14, 0.12)), p0 + V((0.015 * x, 0.25, 0.3))], [0.018, 0.014, 0.01], seg=6), BARK)
    # the load: an open woven basket on the prongs, full of fallen human things (the only colour on him)
    bc = V((0, 0.37, 0.84))
    bk = bm_lathe([(0.0, -0.02), (0.15, 0.0), (0.18, 0.12), (0.2, 0.26)], seg=14, center=bc, sx=1.0, sy=0.75, cap_top=False)
    jitter(bk, 0.006, 5, 12)
    R.add('Body', bk, BARK, face_mat=lambda c, n: SACK_D if n.z > 0.5 else None)
    for k in range(3):   # weave bands (ink)
        z = bc.z + 0.04 + 0.08 * k
        r = 0.155 + 0.017 * k
        ring = CH.ring_pts(V((bc.x, bc.y, z)), (0, 0, 1), r * 1.02, 16, 0.03, k)
        R.add('Body', stroke([V((p.x, bc.y + (p.y - bc.y) * 0.75, p.z)) for p in ring], 0.0035, taper=False), INK, smooth=False)
    R.add('Body', L.bevel(bm_box(bc + V((0.07, 0.0, 0.29)), (0.13, 0.04, 0.17)), 0.01, 1, 40), 'M_BookRed', smooth=False)   # red book
    rot_b = L.bevel(bm_box(bc + V((-0.07, 0.03, 0.27)), (0.1, 0.035, 0.14)), 0.01, 1, 40)
    rot(rot_b, 'Y', 25, bc + V((-0.07, 0.03, 0.27)))
    R.add('Body', rot_b, 'M_BookBlue', smooth=False)
    R.add('Body', bm_lathe([(0.0, 0.0), (0.05, 0.01), (0.055, 0.08), (0.03, 0.11), (0.0, 0.12)], seg=10, center=bc + V((0.0, -0.06, 0.24))), 'M_Brass')   # lantern
    R.add('Body', bm_tube([bc + V((-0.02, 0.06, 0.2)), bc + V((-0.05, 0.08, 0.45)), bc + V((-0.03, 0.09, 0.5))], 0.012, seg=6), 'M_Leather')   # umbrella handle
    R.add('Body', bm_tube(CH.ring_pts(bc + V((0, 0, 0.26)), (0, 0, 1), 0.2, 16), 0.012, seg=5, cap=False), BARK, smooth=False)   # basket rim

    # shoulder straps (멜빵): pole top -> over the shoulder -> down the chest -> under the arm -> pole bottom
    for x in (1, -1):
        pts = [V((0.12 * x, 0.2, 1.02)), V((0.13 * x, 0.06, 1.09)), V((0.12 * x, -0.12, 1.03)), V((0.12 * x, -0.17, 0.9)),
               V((0.15 * x, -0.15, 0.78)), V((0.2 * x, 0.02, 0.74)), V((0.14 * x, 0.2, 0.62))]
        R.add('Body', bm_tube(pts, 0.016, seg=5, cap=True, flat=0.45, up=(x, 0, 0)), SACK_D, smooth=False)

    # ---- meta (egg-head proportions under the hood, hunched rest pose)
    CH.puppet_meta(R, d, 1.5, hc, 0.2, (0, 0, 0.88), 0.2, foot=(0.15, 0.08, 0.06))
    R.meta['rest_pose'] = {'B.ArmL.z': 7.0, 'B.ArmR.z': -7.0, 'B.ForeArmL.x': -16.0, 'B.ForeArmR.x': -16.0,
                           'B.Body.x': 18.0, 'B.Head.x': -14.0, 'B.ArmL.x': -10.0, 'B.ArmR.x': -10.0}
    collector_clips(R)
    return R


def collector_clips(R):
    D = A.Dims(R)

    def wob(ch, t, ph, cL, b_):
        ch['B.Head.z'] = ch.get('B.Head.z', 0) + 2 * cL
        return ch
    R.clips.append(('Idle',) + A.c_idle(R, D, 3.4))
    R.clips.append(('Walk',) + A.locomotion(R, D, 2.2, 16, stance=0.36, lift=0.06, bob=0.028, lean=6, arm=16, yaw=6,
                                            roll=4, elbow=16, crouch=0.02, extra=wob))
    R.meta['speeds'] = {'Walk': 2.2, 'Carry': 2.2}
    R.clips.append(('Carry',) + R6.collector_carry(R, D))
    R.clips.append(('Grab',) + R6.collector_grab(R, D))
    R.clips.append(('Bow',) + A.c_bow(R, D))
    R.clips.append(('BowHold',) + A.c_bowhold(R, D))
    R.clips.append(('Rise',) + A.c_rise(R, D))
    R.clips.append(('Recoil',) + R6.v_recoil(R, D))
    R.clips.append(('Point',) + A.c_point(R, D))
    R.clips.append(('Talk',) + A.c_talk(R, D))
