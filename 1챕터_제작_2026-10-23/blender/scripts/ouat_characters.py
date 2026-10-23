# -*- coding: utf-8 -*-
"""Characters. Blender coords: Z up, front -Y, character's left +X. Root origin = between the feet."""
import math
from mathutils import Vector
from mathutils.bvhtree import BVHTree
import ouat_lib as L
from ouat_lib import (Part, Asset, bm_sphere, bm_tube, bm_blade, bm_box, bm_cyl, bm_lathe, stroke,
                      wobble_line, rot, move, deform, jitter, mirror_x, subdivide, copy_bm, nvec, nval)

V = Vector


def eye_pair(A, head_c, head_r, side_x, up_z, fwd=1.0, size=(0.035, 0.02, 0.045), shine=True, parent='Head',
             mat='M_Ink', names=('EyeL', 'EyeR'), seg=8, rings=6):
    """Places two eyes on a sphere-ish head. side_x, up_z: offsets from head centre (direction gets normalised)."""
    for sgn, nm in ((1, names[0]), (-1, names[1])):
        d = V((side_x * sgn, -fwd, up_z)).normalized()
        c = V(head_c) + d * head_r * 0.97
        p = Part(nm)
        e = bm_sphere((0, 0, 0), size, seg=seg, rings=rings)
        # orient: flatten along the surface normal
        q = d.to_track_quat('Y', 'Z')
        m = q.to_matrix().to_4x4()
        L.xform(e, m)
        move(e, c)
        p.add(e, mat)
        if shine:
            s = bm_sphere((0, 0, 0), (size[0] * 0.33,) * 3, seg=6, rings=4)
            move(s, c + d * size[1] * 0.9 + V((0.012 * sgn * 0.0 + 0.008, 0, size[2] * 0.45)))
            p.add(s, 'M_EyeShine')
        A.part(p, pivot=c, parent=parent)


# =====================================================================================
def build_hero():
    A = Asset('Hero_Bluebird')
    BLUE, BELLY, BEAK = 'M_Bluebird', 'M_BluebirdBelly', 'M_Beak'

    # ---- legs (pivot at hip) ------------------------------------------------------
    for sgn, nm in ((1, 'LegL'), (-1, 'LegR')):
        x = 0.095 * sgn
        p = Part(nm)
        # feathered thigh puff (blue) + thin bird shin (beak colour)
        th = bm_sphere((x, 0.0, 0.25), (0.085, 0.085, 0.075), seg=10, rings=6)
        p.add(th, BLUE)
        shin = bm_tube([(x, 0.0, 0.2), (x * 1.05, -0.005, 0.11), (x * 1.08, -0.01, 0.035)], [0.026, 0.022, 0.02], seg=6)
        p.add(shin, BEAK)
        # 3 toes forward + 1 back
        for a in (-28, 0, 28):
            d = V((math.sin(math.radians(a)) * sgn * -1, -math.cos(math.radians(a)), 0))
            toe = bm_tube([(x * 1.08, -0.01, 0.03), V((x * 1.08, -0.01, 0.022)) + d * 0.06, V((x * 1.08, -0.01, 0.016)) + d * 0.105],
                          [0.019, 0.016, 0.008], seg=5)
            p.add(toe, BEAK)
        heel = bm_tube([(x * 1.08, -0.01, 0.03), (x * 1.08, 0.05, 0.016)], [0.016, 0.008], seg=5)
        p.add(heel, BEAK)
        A.part(p, pivot=(x, 0, 0.27))

    # ---- body (pivot at hips) -----------------------------------------------------
    body = Part('Body')
    b = bm_sphere((0, 0, 0.5), (0.25, 0.235, 0.27), seg=12, rings=8)

    def pear(co):
        t = (co.z - 0.23) / 0.54  # 0 bottom .. 1 top
        k = 1.0 + 0.16 * (1 - t) - 0.1 * t
        co.x *= k
        co.y *= k
        # slight forward belly, back flattening
        if co.y < 0:
            co.y *= 1.06
        return co
    deform(b, pear)
    b = subdivide(b, 1)

    body_b = b
    bvh = BVHTree.FromBMesh(body_b)
    body.add(body_b, BLUE)
    # cream bib: overlay ellipsoid gives a clean patch edge
    bib = bm_sphere((0, -0.085, 0.47), (0.195, 0.185, 0.235), seg=10, rings=8)
    bib = subdivide(bib, 1)
    body.add(bib, BELLY)
    # satchel strap hugging the body (ray-cast onto the body surface)
    strap = []
    cen = V((0, 0, 0.5))
    nrm = V((0.55, 0.0, 1.0)).normalized()   # tilted plane: right shoulder -> left hip
    ax1 = V((0, 1, 0))
    ax2 = nrm.cross(ax1).normalized()
    for i in range(29):
        a = 2 * math.pi * i / 28
        d = (ax1 * math.cos(a) + ax2 * math.sin(a)).normalized()
        hit = bvh.ray_cast(cen + d * 0.6, -d)
        if hit[0] is None:
            continue
        pt = hit[0] + hit[1] * 0.012
        # sit on top of the bib in front
        if pt.y < -0.12:
            pt = pt + V((0, -0.014, 0))
        strap.append(pt)
    sb = bm_tube(strap, 0.018, seg=4, cap=False, flat=0.4, up=(0, 0, 1))
    body.add(sb, 'M_Leather', smooth=False)
    # bag at the left hip (+x side, slightly front)
    bag_c = V((0.255, -0.06, 0.37))
    bag = bm_box((0, 0, 0), (0.07, 0.17, 0.15))
    bag = L.bevel(bag, 0.022, 2, 40)
    rot(bag, 'Z', 14)
    move(bag, bag_c)
    body.add(bag, 'M_Leather', smooth=False)
    flap = bm_box((0, 0, 0), (0.078, 0.175, 0.07))
    flap = L.bevel(flap, 0.015, 1, 40)
    rot(flap, 'Z', 14)
    move(flap, bag_c + V((0.004, 0, 0.05)))
    body.add(flap, 'M_Leather', smooth=False)
    buckle = bm_box((0, 0, 0), (0.02, 0.05, 0.04))
    buckle = L.bevel(buckle, 0.006, 1, 40)
    rot(buckle, 'Z', 14)
    move(buckle, bag_c + V((0.045, -0.01, 0.03)))
    body.add(buckle, 'M_Brass', smooth=False)
    A.part(body, pivot=(0, 0, 0.27))

    # ---- tail (pivot at tail root, back of body) ----------------------------------
    tail = Part('Tail')
    for a, ln, w in ((-26, 0.2, 0.05), (0, 0.24, 0.058), (26, 0.2, 0.05)):
        d = V((math.sin(math.radians(a)), math.cos(math.radians(a)), 0))
        base = V((0, 0.2, 0.33))
        pts = [base, base + d * ln * 0.45 + V((0, 0, -0.04)), base + d * ln + V((0, 0, -0.06))]
        f = bm_blade(pts, [0.03, w, 0.012], thick=0.018, up=(0, 0, 1))
        tail.add(f, BLUE)
    A.part(tail, pivot=(0, 0.2, 0.33), parent='Body')

    # ---- wings as arms (pivot at shoulder) ----------------------------------------
    for sgn, nm in ((1, 'WingL'), (-1, 'WingR')):
        w = Part(nm)
        sh = V((0.235 * sgn, -0.01, 0.62))
        el = V((0.31 * sgn, -0.02, 0.48))
        hd = V((0.33 * sgn, -0.035, 0.37))
        arm = bm_tube([sh + V((-0.02 * sgn, 0, 0.03)), sh, el, hd], [0.03, 0.068, 0.058, 0.048], seg=8, flat=0.55, up=(sgn, 0, 0))
        arm = subdivide(arm, 1)
        w.add(arm, BLUE)
        # three feather fingers fanning (front-back) at the hand
        for i, a in enumerate((-34, 0, 34)):
            d = V((0.12 * sgn, math.sin(math.radians(a)) * 0.75, -1.0)).normalized()
            ln = 0.12 if a else 0.14
            p0 = hd + V((0, math.sin(math.radians(a)) * 0.022, 0.025))
            pts = [p0, p0 + d * ln * 0.45, p0 + d * ln * 0.85, p0 + d * ln]
            f = bm_blade(pts, [0.02, 0.028, 0.02, 0.004], thick=0.018, up=(sgn, 0, 0))
            w.add(f, BLUE)
        A.part(w, pivot=sh, parent='Body')

    # ---- head (pivot at neck) -----------------------------------------------------
    head_c = V((0, -0.025, 0.84))
    hr = 0.205
    head = Part('Head')
    h = bm_sphere(head_c, (hr * 1.04, hr * 0.98, hr * 0.96), seg=12, rings=8)
    h = subdivide(h, 1)

    head.add(h, BLUE)
    # pale throat patch
    thr = bm_sphere(head_c + V((0, -0.07, -0.085)), (0.13, 0.15, 0.11), seg=10, rings=6)
    thr = subdivide(thr, 1)
    head.add(thr, BELLY)
    for sgn in (1, -1):
        d = V((0.42 * sgn, -1.0, 0.08)).normalized()
        c = head_c + d * hr * 0.955
        rg = bm_sphere((0, 0, 0), (0.037, 0.011, 0.047), seg=10, rings=4)
        L.xform(rg, d.to_track_quat('Y', 'Z').to_matrix().to_4x4())
        move(rg, c)
        head.add(rg, BELLY)
    A.part(head, pivot=(0, -0.01, 0.7), parent='Body')

    eye_pair(A, head_c, hr * 1.0, side_x=0.42, up_z=0.08, size=(0.032, 0.018, 0.042))

    # beak (pivot at beak root)
    bk = Part('Beak')
    root = head_c + V((0, -hr * 0.95, -0.035))
    up_b = bm_tube([root + V((0, 0.02, 0.005)), root + V((0, -0.05, -0.005)), root + V((0, -0.1, -0.03))], [0.045, 0.03, 0.002], seg=8, flat=0.7, up=(0, 0, 1))
    bk.add(up_b, BEAK)
    lo_b = bm_tube([root + V((0, 0.015, -0.025)), root + V((0, -0.06, -0.035))], [0.03, 0.002], seg=6, flat=0.6, up=(0, 0, 1))
    bk.add(lo_b, BEAK)
    A.part(bk, pivot=root, parent='Head')

    # small crest tuft poking out at the back, under the cap
    cr = Part('Crest')
    top = head_c + V((0, hr * 0.55, hr * 0.62))
    for i, (sx, ln) in enumerate(((-0.03, 0.07), (0.0, 0.1), (0.03, 0.07))):
        p0 = top + V((sx, 0, 0))
        pts = [p0, p0 + V((sx * 0.4, ln * 0.6, ln * 0.35)), p0 + V((sx * 0.8, ln, ln * 0.3))]
        f = bm_blade(pts, [0.022, 0.026, 0.004], thick=0.016, up=(1, 0, 0))
        cr.add(f, BLUE)
    A.part(cr, pivot=top, parent='Head')

    # hunting cap (flat cap) with a short brim and a tucked blue feather
    cp = Part('Cap')
    tilt = 10  # forward tilt
    capc = head_c + V((0, 0.0, 0.0))
    prof = [(0.0, 0.2), (0.1, 0.198), (0.17, 0.188), (0.215, 0.165), (0.228, 0.14), (0.212, 0.112), (0.198, 0.1)]
    cb = bm_lathe(prof, seg=16, center=capc, sx=1.04, sy=1.08, cap_bottom=False)
    deform(cb, lambda c: c + V((0, -0.035 * max(0, c.z - capc.z - 0.15) / 0.06, 0)))
    rot(cb, 'X', -tilt, capc)
    # give the open bottom a thickness ring
    cp.add(cb, 'M_CapNavy')
    band = bm_tube([capc + V((math.cos(2 * math.pi * i / 16) * 0.207 * 1.04, math.sin(2 * math.pi * i / 16) * 0.207 * 1.08, 0.1)) for i in range(17)], 0.014, seg=4, cap=False)
    rot(band, 'X', -tilt, capc)
    cp.add(band, 'M_CapNavy', smooth=False)
    brim = []
    for i in range(9):
        aa = math.radians(-150 + 120 * i / 8)
        brim.append(V((math.cos(aa) * 0.2, math.sin(aa) * 0.2 - 0.0, 0.1)))
    bb = bm_blade([capc + v for v in brim], [0.012, 0.03, 0.042, 0.05, 0.052, 0.05, 0.042, 0.03, 0.012], thick=0.01, up=(0, 0, 1))
    deform(bb, lambda c: c + V((0, -0.035 * max(0, -(c.y - capc.y) - 0.15) / 0.08, -0.025 * max(0, -(c.y - capc.y) - 0.15) / 0.08)))
    rot(bb, 'X', -tilt, capc)
    cp.add(bb, 'M_CapNavy', smooth=False)
    fe = [capc + V((0.215, 0.04, 0.13)), capc + V((0.23, 0.08, 0.17)), capc + V((0.232, 0.12, 0.2))]
    fb = bm_blade(fe, [0.012, 0.016, 0.003], thick=0.01, up=(1, 0, 0))
    rot(fb, 'X', -tilt, capc)
    cp.add(fb, BLUE, smooth=False)
    A.part(cp, pivot=capc + V((0, 0, 0.1)), parent='Head')

    # short cape over the shoulders (navy outside, cobalt lining), open at the front
    cape_out, cape_in = Part('tmp'), None
    rows = [(0.765, 0.16), (0.725, 0.24), (0.665, 0.3), (0.6, 0.33)]
    cols = 15
    o_b = L.bmesh.new()
    i_b = L.bmesh.new()
    e_b = L.bmesh.new()
    grid_o, grid_i = [], []
    for ri, (z, r) in enumerate(rows):
        ro, rin = [], []
        for j in range(cols + 1):
            a = math.radians(-90 + 58 + (360 - 116) * j / cols)  # around from the front-left edge to front-right edge
            d = V((math.cos(a), math.sin(a), 0))
            back = max(0.0, d.y)   # longer at the back
            zz = z - (0.07 * back if ri == len(rows) - 1 else 0.05 * back * ri / (len(rows) - 1)) + (0.012 * math.sin(j * 1.7) if ri == len(rows) - 1 else 0)
            po = V((0, 0.01, 0)) + d * r * V((1.0, 1.0, 1.0)).x
            po = V((po.x * 1.0, po.y * 0.95, zz))
            pi = po - d * 0.014
            ro.append(o_b.verts.new(po))
            rin.append(i_b.verts.new(pi))
        grid_o.append(ro)
        grid_i.append(rin)
    for ri in range(len(rows) - 1):
        for j in range(cols):
            o_b.faces.new((grid_o[ri][j], grid_o[ri + 1][j], grid_o[ri + 1][j + 1], grid_o[ri][j + 1]))
            i_b.faces.new((grid_i[ri][j], grid_i[ri][j + 1], grid_i[ri + 1][j + 1], grid_i[ri + 1][j]))
    # rim (hem + front edges) in lining blue
    def ev(v):
        return e_b.verts.new(v.co.copy())
    last = len(rows) - 1
    for j in range(cols):
        a0, a1, b0, b1 = grid_o[last][j], grid_o[last][j + 1], grid_i[last][j], grid_i[last][j + 1]
        e_b.faces.new((ev(a0), ev(b0), ev(b1), ev(a1)))
    for ri in range(len(rows) - 1):
        for j in (0, cols):
            a0, a1, b0, b1 = grid_o[ri][j], grid_o[ri + 1][j], grid_i[ri][j], grid_i[ri + 1][j]
            f = e_b.faces.new((ev(a0), ev(a1), ev(b1), ev(b0)))
    for bm_ in (o_b, i_b, e_b):
        L.bmesh.ops.recalc_face_normals(bm_, faces=bm_.faces) if bm_ is e_b else None
    cape = Part('Cape')
    cape.add(o_b, 'M_CapNavy')
    cape.add(i_b, BLUE)
    cape.add(e_b, BLUE, smooth=False)
    # clasp at the throat
    cape.add(bm_sphere(V((0, -0.17, 0.74)), (0.025, 0.015, 0.025), seg=6, rings=4), 'M_Brass')
    A.part(cape, pivot=(0, 0, 0.74), parent='Body')

    A.root['ouat_size'] = 1.1
    return A


#@@CREATURES@@

# =====================================================================================
def build_fish():
    """Huge dark fish under the pond. Root origin = body centre (on the spine axis), front -Y."""
    A = Asset('Fish')
    F, MOUTH = 'M_Fish', 'M_FishMouth'
    body = Part('Body')
    ys = [-2.3, -1.4, -0.3, 0.9, 2.0, 3.0, 3.9]
    rs = [1.55, 1.72, 1.65, 1.4, 1.0, 0.6, 0.34]
    b = bm_tube([V((0, y, 0.05 * math.sin(y))) for y in ys], rs, seg=12, flat=0.72, up=(1, 0, 0))
    b = subdivide(b, 1)
    jitter(b, 0.06, 1.2, 90)
    body.add(b, F)
    # ragged dorsal fin
    outline = []
    n = 9
    for i in range(n + 1):
        t = i / n
        y = -1.6 + 4.6 * t
        top = 1.7 * (1 - abs(t - 0.35) * 1.2) + 0.25
        outline.append((y, 1.25 + (top if i % 2 == 0 else top * 0.55) * (1.0 - 0.6 * t)))
    outline += [(3.0, 0.75), (-1.6, 1.35)]
    df = L.bm_prism([(u, v) for u, v in outline], -0.06, 0.06, axis='X')
    body.add(df, F, smooth=False)
    # ink scale arcs along the flanks
    for side in (1, -1):
        for row, z in enumerate((0.55, -0.1, -0.75)):
            for k in range(5):
                y = -1.4 + k * 0.95 + 0.45 * (row % 2)
                rr = None
                # find radius at y by interpolation
                for j in range(len(ys) - 1):
                    if ys[j] <= y <= ys[j + 1]:
                        t = (y - ys[j]) / (ys[j + 1] - ys[j])
                        rr = rs[j] * (1 - t) + rs[j + 1] * t
                if rr is None or abs(z) > rr * 0.85:
                    continue
                xx = math.sqrt(max(0.0, 1 - (z / rr) ** 2)) * rr * 0.72 + 0.03
                arc = [V((side * xx, y + 0.35 * math.cos(a), z + 0.3 * math.sin(a))) for a in (-1.4, -0.7, 0.0, 0.7, 1.4)]
                body.add(stroke(arc, 0.025), 'M_Ink', smooth=False)
    A.part(body, pivot=(0, 0, 0))

    # tail fin
    tl = Part('Tail')
    tail_outline = [(3.75, 0.3), (4.6, 1.0), (5.5, 1.85), (5.25, 0.8), (5.0, 0.05), (5.25, -0.7), (5.45, -1.6), (4.55, -0.9), (3.75, -0.3)]
    tf = L.bm_prism(tail_outline, -0.09, 0.09, axis='X')
    tl.add(tf, F, smooth=False)
    for k in range(4):
        tl.add(stroke([V((0.1, 3.9, 0.1 * k - 0.15)), V((0.11, 4.8, 0.5 * (k - 1.5))), V((0.1, 5.25, 0.85 * (k - 1.5)))], 0.02), 'M_Ink', smooth=False)
    A.part(tl, pivot=(0, 3.75, 0), parent='Body')

    hinge = V((0, -2.0, -0.35))
    # upper jaw / skull
    ju = Part('JawUpper')
    yy = [-1.9, -2.6, -3.4, -4.1, -4.45]
    rr = [1.62, 1.5, 1.2, 0.75, 0.25]
    u = bm_tube([V((0, y, -0.35)) for y in yy], rr, seg=12, flat=0.72, up=(1, 0, 0))
    u = subdivide(u, 1)
    deform(u, lambda c: V((c.x, c.y, max(c.z, -0.35))))
    jitter(u, 0.04, 1.5, 91)

    def palate(c, n):
        return MOUTH if n.z < -0.6 else None
    ju.add(u, F, face_mat=palate)
    # teeth along the rim, pointing down
    for side in (1, -1):
        for k in range(7):
            t = k / 6
            y = -2.4 - 1.85 * t
            r_at = 1.5 - 0.95 * t
            x = side * r_at * 0.72 * 0.92
            ln = 0.42 - 0.18 * abs(t - 0.4)
            base = V((x, y, -0.33))
            ju.add(bm_tube([base, base + V((-side * 0.03, -0.02, -ln * 0.6)), base + V((-side * 0.05, -0.05, -ln))], [0.09, 0.055, 0.004], seg=5), 'M_Paper', smooth=False)
    A.part(ju, pivot=hinge, parent='Body')

    # eyes (both in one object, child of the upper jaw)
    ey = Part('Eye')
    for side in (1, -1):
        c = V((side * 0.95, -3.0, 0.38))
        e = bm_sphere(c, (0.06, 0.17, 0.15), seg=8, rings=6)
        ey.add(e, 'M_FishEye')
        ey.add(bm_sphere(c + V((side * 0.04, -0.01, 0)), (0.03, 0.03, 0.11), seg=6, rings=4), 'M_Ink')
    A.part(ey, pivot=(0, -3.0, 0.38), parent='JawUpper')

    # lower jaw
    jl = Part('JawLower')
    yy = [-1.9, -2.6, -3.35, -4.0, -4.3]
    rr = [1.45, 1.35, 1.05, 0.6, 0.2]
    lo = bm_tube([V((0, y, -0.38)) for y in yy], rr, seg=12, flat=0.72, up=(1, 0, 0))
    lo = subdivide(lo, 1)
    deform(lo, lambda c: V((c.x, c.y, min(c.z, -0.38))))
    jitter(lo, 0.04, 1.5, 92)

    def floor(c, n):
        return MOUTH if n.z > 0.6 else None
    jl.add(lo, F, face_mat=floor)
    for side in (1, -1):
        for k in range(6):
            t = k / 5
            y = -2.45 - 1.6 * t
            r_at = 1.35 - 0.9 * t
            x = side * r_at * 0.72 * 0.9
            ln = 0.34 - 0.12 * abs(t - 0.5)
            base = V((x, y, -0.4))
            jl.add(bm_tube([base, base + V((-side * 0.03, 0.02, ln * 0.6)), base + V((-side * 0.05, 0.04, ln))], [0.08, 0.05, 0.004], seg=5), 'M_Paper', smooth=False)
    # barbels hanging from the chin
    for side in (1, -1):
        p0 = V((side * 0.4, -3.9, -0.9))
        pts = [p0, p0 + V((side * 0.25, 0.1, -0.5)), p0 + V((side * 0.15, 0.35, -1.0)), p0 + V((side * 0.35, 0.5, -1.45))]
        jl.add(bm_tube(pts, [0.07, 0.05, 0.03, 0.008], seg=5), F)
    A.part(jl, pivot=hinge, parent='Body')

    for sgn, nm in ((1, 'FinL'), (-1, 'FinR')):
        p = Part(nm)
        base = V((1.1 * sgn, -1.0, -0.7))
        pts = [base, base + V((0.55 * sgn, 0.4, -0.35)), base + V((0.95 * sgn, 1.1, -0.65)), base + V((1.05 * sgn, 1.6, -0.8))]
        fb = bm_blade(pts, [0.35, 0.45, 0.32, 0.05], thick=0.07, up=(0.35 * sgn, 0, 1))
        p.add(fb, F, smooth=False)
        for k in range(3):
            p.add(stroke([base + V((0.05 * sgn, 0.05 * k, -0.02)), pts[2] + V((0.0, -0.25 + 0.2 * k, 0.03))], 0.018), 'M_Ink', smooth=False)
        A.part(p, pivot=base, parent='Body')
    A.root['ouat_size'] = 9.0
    return A


