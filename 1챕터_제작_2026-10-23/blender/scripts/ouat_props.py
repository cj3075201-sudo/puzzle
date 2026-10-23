# -*- coding: utf-8 -*-
"""Props / puzzle objects / human junk. Blender coords: Z up, front -Y, root origin at the floor centre.
Look: white paper world drawn in ink (M_Paper + M_Ink strokes + M_Hatch on shadow sides);
creature-made things in bare puppet wood; fully drawn plaza things painted; human objects vivid."""
import math, random
import bmesh
from mathutils import Vector, Matrix
import ouat_lib as L
from ouat_lib import (Part, Asset, bm_sphere, bm_tube, bm_blade, bm_box, bm_cyl, bm_lathe, bm_prism, bm_plane_uv,
                      stroke, wobble_line, rot, move, deform, jitter, subdivide, copy_bm, nvec, nval)

V = Vector
PAPER, SHADE, INK, HATCH = 'M_Paper', 'M_PaperShade', 'M_Ink', 'M_Hatch'
PWOOD, PJOINT = 'M_PuppetWood', 'M_PuppetJoint'


# ===================================================================== shared helpers
def tri_ngons(b):
    ng = [f for f in b.faces if len(f.verts) > 4]
    if ng:
        bmesh.ops.triangulate(b, faces=ng, quad_method='BEAUTY', ngon_method='EAR_CLIP')
    return b


def merge(bms):
    out = bmesh.new()
    for b in bms:
        me = L.bpy.data.meshes.new('tmp_merge')
        b.to_mesh(me)
        out.from_mesh(me)
        L.bpy.data.meshes.remove(me)
        b.free()
    return out


def bbox(center, size, bev=0.0, seg=1, angle=40):
    b = bm_box(center, size)
    if bev > 0:
        b = L.bevel(b, bev, seg, angle)
    return b


def ink_poly(pts, r=0.012, closed=False, overshoot=0.0, seed=0.0, amp=0.0):
    """Ink line along a polyline, optional overshoot at both ends (hand-drawn)."""
    pts = [V(p) for p in pts]
    if closed:
        pts = pts + [pts[0]]
    if overshoot > 0 and len(pts) > 1:
        d0 = (pts[0] - pts[1]).normalized()
        d1 = (pts[-1] - pts[-2]).normalized()
        pts = [pts[0] + d0 * overshoot] + pts + [pts[-1] + d1 * overshoot]
    if amp > 0:
        pts = [p + nvec(p, 2.0, seed) * amp for p in pts]
    return stroke(pts, r, seg=3, taper=not closed)


def edge_lines(pts_list, r=0.012, overshoot=0.04, seed=0.0):
    """several open ink lines (list of polylines) merged into one bmesh"""
    return merge([ink_poly(p, r, overshoot=overshoot, seed=seed + i, amp=r * 0.6) for i, p in enumerate(pts_list)])


def hatch_rect(origin, u, v, w, h, n=8, slope=0.7, r=0.01, seed=0.0, mat_off=0.012, normal=None, density=1.0):
    """Diagonal hatch strokes on a rectangle spanned by unit vectors u (along) and v (up) from origin.
    Returns a merged bmesh (use M_Hatch)."""
    o, u, v = V(origin), V(u).normalized(), V(v).normalized()
    nrm = V(normal).normalized() if normal else u.cross(v).normalized()
    rnd = random.Random(int(seed * 1000) + 7)
    out = []
    for i in range(n):
        if rnd.random() > density:
            continue
        s = (i + 0.5) / n * w
        t0 = rnd.uniform(0.0, 0.25) * h
        t1 = rnd.uniform(0.65, 1.0) * h
        a = o + u * s + v * t0 + nrm * mat_off
        b = o + u * min(w, s + (t1 - t0) * slope) + v * t1 + nrm * mat_off
        out.append(stroke([a, a.lerp(b, 0.5), b], r, seg=3))
    return merge(out) if out else None


def arch2d(w, h, n=6):
    r = w / 2.0
    sh = max(0.0, h - r)
    pts = [(-r, 0.0), (-r, sh)]
    for i in range(1, n):
        a = math.pi - math.pi * i / n
        pts.append((r * math.cos(a), sh + r * math.sin(a)))
    pts += [(r, sh), (r, 0.0)]
    return pts


def place_on(b, pos, angle_deg):
    """Local build space: front = -Y. Rotate so -Y faces direction angle_deg (in XY, 0 = +X), move to pos."""
    rot(b, 'Z', angle_deg + 90.0)
    move(b, pos)
    return b


def arch_panel(pos, angle, w, h, depth=0.06):
    b = bm_prism(arch2d(w, h), -depth / 2, depth / 2, axis='Y')
    tri_ngons(b)
    return place_on(b, pos, angle)


def arch_outline(pos, angle, w, h, r=0.02, grow=0.06, seed=0.0, out=0.06):
    pts = [V((x * (1 + grow / max(w, 0.01)), -out, z * (1 + grow * 0.5 / max(h, 0.01)))) for x, z in arch2d(w, h, 8)]
    b = ink_poly(pts, r, overshoot=0.05, seed=seed, amp=r * 0.5)
    return place_on(b, pos, angle)


def drawn_beam(p0, p1, w=0.12, h=0.14, seed=0.0, r=0.018, cross=6):
    """A beam that is DRAWN: paper core + heavy ink contour strokes with overshoot + cross hatching.
    Returns (core_bmesh, ink_bmesh). Beam axis p0->p1, roughly horizontal."""
    p0, p1 = V(p0), V(p1)
    d = (p1 - p0)
    ln = d.length
    ax = d.normalized()
    side = ax.cross(V((0, 0, 1))).normalized()
    up = side.cross(ax).normalized()
    core = bm_tube([p0, p1], [w * 0.5, w * 0.5], seg=4, flat=h / w, up=up, twist=0.0)
    inks = []
    for sy, sz in ((1, 1), (-1, 1), (1, -1), (-1, -1)):
        off = side * (w * 0.52 * sy) + up * (h * 0.52 * sz)
        inks.append(ink_poly([p0 + off, p0 + off + ax * ln * 0.5, p1 + off], r, overshoot=0.12, seed=seed + sy + sz * 3, amp=0.015))
    # end caps drawn
    for pe in (p0, p1):
        sq = [pe + side * w * 0.52 * a + up * h * 0.52 * b2 for a, b2 in ((1, 1), (-1, 1), (-1, -1), (1, -1))]
        inks.append(ink_poly(sq, r * 0.8, closed=True, seed=seed + 9))
    # cross hatching on the front face
    for i in range(cross):
        t = (i + 0.5) / cross
        a = p0 + ax * ln * t - side * w * 0.53 + up * h * 0.45
        b = a + ax * 0.12 - up * h * 0.9
        inks.append(stroke([a, b], r * 0.6, seg=3))
    return core, merge(inks)


def jag_outline(rx, ry, n=12, seed=0.0, rough=0.18, cx=0.0, cy=0.0):
    """irregular CCW polygon around (cx, cy)"""
    rnd = random.Random(int(seed * 100) + 3)
    pts = []
    for i in range(n):
        a = 2 * math.pi * (i + rnd.uniform(-0.25, 0.25)) / n
        k = 1.0 + rnd.uniform(-rough, rough)
        pts.append((cx + math.cos(a) * rx * k, cy + math.sin(a) * ry * k))
    return pts


def poly_ccw(pts):
    a = sum(pts[i][0] * pts[(i + 1) % len(pts)][1] - pts[(i + 1) % len(pts)][0] * pts[i][1] for i in range(len(pts)))
    return pts if a > 0 else list(reversed(pts))


def cliff_part(part, outline, bands, seed=0.0, shadow=(0.6, 0.8), ink_r=0.03, hatch_r=0.018, hatch_density=0.8,
               top_mat=PAPER, side_mat=SHADE, ink_top=True, verticals=4, hatch=True):
    """Stepped rock block like the concept cliffs. outline: 2D polygon (top band, at scale 1).
    bands: list of (z_top, z_bot, scale, (dx, dy)). Adds prisms + ink contour + hatch on shadow-facing sides."""
    outline = poly_ccw(outline)
    sd = V((shadow[0], shadow[1], 0)).normalized()
    rnd = random.Random(int(seed * 100) + 11)
    for bi, (zt, zb, sc, off) in enumerate(bands):
        ol = [(x * sc + off[0], y * sc + off[1]) for x, y in outline]
        b = bm_prism(ol, zb, zt, axis='Z')
        tri_ngons(b)
        jitter(b, 0.04 * (1 + bi), 0.9, seed + bi)
        part.add(b, top_mat, smooth=False, face_mat=lambda c, n: side_mat if n.z < 0.5 else None)
        n = len(ol)
        for i in range(n):
            x0, y0 = ol[i]
            x1, y1 = ol[(i + 1) % n]
            e = V((x1 - x0, y1 - y0, 0))
            ln = e.length
            if ln < 0.3:
                continue
            nrm = V((e.y, -e.x, 0)).normalized()
            if hatch and nrm.dot(sd) > -0.25:
                h = hatch_rect(V((x0, y0, zb + 0.05)), e, V((0, 0, 1)), ln, (zt - zb) * 0.95, n=max(2, int(ln * 2.2)), slope=0.45,
                               r=hatch_r, seed=seed + bi * 10 + i, normal=nrm, mat_off=0.05 + 0.04 * bi, density=hatch_density)
                if h:
                    part.add(h, HATCH, smooth=False)
        if ink_top:
            pts = [V((x, y, zt + 0.02)) + V((x - off[0], y - off[1], 0)).normalized() * 0.04 for x, y in ol]
            # contour broken into 2-3 open strokes (hand drawn, not a closed loop)
            k0 = rnd.randrange(n)
            cut = sorted(rnd.sample(range(1, n), 2))
            segs = [pts[k0:] + pts[:k0]]
            seq = segs[0]
            for a, b2 in ((0, cut[0] + 1), (cut[0], cut[1] + 1), (cut[1], n + 1)):
                sub = (seq + seq[:1])[a:b2]
                if len(sub) >= 2:
                    part.add(ink_poly(sub, ink_r, overshoot=0.15, seed=seed + a, amp=ink_r * 0.4), INK, smooth=False)
        for k in range(verticals if bi == 0 else verticals // 2):
            i = rnd.randrange(n)
            x, y = ol[i]
            p0 = V((x, y, zt)) + V((x - off[0], y - off[1], 0)).normalized() * 0.05
            part.add(ink_poly([p0, p0 + V((0, 0, -(zt - zb) * rnd.uniform(0.4, 1.0)))], ink_r * 0.8, overshoot=0.05, seed=seed + k, amp=0.03), INK, smooth=False)


import ouat_craft as CR

PENCIL, BACK, SMUDGE, FAINT = 'M_Pencil', 'M_PaperBack', 'M_Smudge', 'M_SketchLine'


def rot_pts(pts, axis, deg, pivot=(0, 0, 0)):
    M = Matrix.Rotation(math.radians(deg), 3, axis)
    pv = V(pivot)
    return [M @ (V(p) - pv) + pv for p in pts]


def lines_part(pieces, name='Lines'):
    """collect (bmesh, mat) line pieces into one Part (unlit -> no collider in Unity)."""
    p = Part(name)
    for b, m in pieces:
        if b is not None and len(b.verts):
            p.add(b, m, smooth=False)
    return p


def torn_solid(part, lines, b, field, mat, back=BACK, thick=0.03, zig=0.02, seed=0.0, paint=None, hatch=True,
               hatch_kw=None, smooth=False, back_near=None, ink_r=0.012):
    """cut a closed/open form along field > 0; built shell -> part, torn ink + hatch -> lines list."""
    full = CR.copy(b)
    res = CR.cut_field(b, field, zig=zig, seed=seed)
    if len(res.built.faces):
        part.add(res.built, mat, smooth=smooth, face_mat=paint)
        bk, rim = CR.shell_parts(res.built, thick, near=back_near, torn=res.torn)
        part.add(bk, back, smooth=False)
        part.add(rim, 'M_TornEdge', smooth=False)
    lines.append((CR.torn_ink(res, ink_r, seed), INK))
    if hatch:
        kw = dict(length=(0.04, 0.13), spacing=0.05, r=0.0045, slant=35.0, density=0.75)
        kw.update(hatch_kw or {})
        lines.append((CR.torn_hatch(res, seed=seed, **kw), PENCIL))
    return full, res


def stone_post(part, lines, x, h_built, h_plan, seed, w=0.2):
    """creature-made paper-stone post: built up to h_built (torn top), planned height only in pencil."""
    b = CR.grid_box((x, 0, h_plan / 2), (w, w, h_plan), step=0.1)
    fld = lambda c: h_built + nval(c, 5.0, seed) * 0.12 + nval(c, 14.0, seed + 1) * 0.03 - c.z
    full, res = torn_solid(part, lines, b, fld, PAPER, seed=seed, back_near=0.3, hatch_kw=dict(length=(0.1, 0.4)))
    if h_built < h_plan - 0.05:
        lines.append((CR.wire_drawn(full, lambda c, n: fld(c) > 0, r=0.007, over=0.1, seed=seed), PENCIL))
    # stone courses on the built part (front)
    for k, z in enumerate((0.35, 0.72, 1.05)):
        if z < h_built - 0.1:
            lines.append((CR.line([V((x - w / 2, -w / 2 - 0.006, z)), V((x + w / 2, -w / 2 - 0.006, z + 0.01))], 0.006, over=0.02, seed=seed + k), INK))



# ===================================================================== latch (human, brass)
def latch_pieces(scale=1.0, open_=False):
    """Hasp latch in local space: plate on the -Y face of whatever it's mounted on, hinge at origin (top of hasp).
    Returns (plate_pieces, hasp_pieces) lists of (bmesh, mat)."""
    s = scale
    plate = []
    p = bbox((0, 0, 0.03 * s), (0.11 * s, 0.012 * s, 0.07 * s), 0.004 * s)
    plate.append((p, 'M_Brass'))
    # hinge knuckle
    plate.append((bm_cyl((-0.05 * s, -0.012 * s, 0.05 * s), (0.05 * s, -0.012 * s, 0.05 * s), 0.011 * s, seg=8), 'M_Brass'))
    # staple (loop) lower down, on the other part
    st = bm_tube([V((-0.018, -0.006, -0.12)) * s, V((-0.018, -0.03, -0.12)) * s, V((0.018, -0.03, -0.12)) * s, V((0.018, -0.006, -0.12)) * s],
                 0.006 * s, seg=5, cap=True)
    plate.append((st, 'M_Iron'))
    sp = bbox((0, -0.003 * s, -0.12 * s), (0.07 * s, 0.008 * s, 0.05 * s), 0.003 * s)
    plate.append((sp, 'M_Brass'))
    for x in (-0.035, 0.035):
        plate.append((bm_cyl((x * s, -0.006 * s, 0.025 * s), (x * s, -0.014 * s, 0.025 * s), 0.008 * s, seg=6), 'M_Iron'))
    hasp = []
    outline = [(-0.025, 0.05), (0.025, 0.05), (0.025, -0.145), (0.0, -0.165), (-0.025, -0.145)]
    hb = bm_prism([(u * s, v * s) for u, v in outline], -0.02 * s, -0.008 * s, axis='Y')
    tri_ngons(hb)
    hasp.append((hb, 'M_Brass'))
    slot = bbox((0, -0.021 * s, -0.12 * s), (0.012 * s, 0.004 * s, 0.035 * s))
    hasp.append((slot, INK))
    return plate, hasp


def build_latch():
    A = Asset('Latch')
    plate, hasp = latch_pieces(2.0)
    pp = Part('Plate')
    for b, m in plate:
        pp.add(b, m, smooth=False)
    A.part(pp, pivot=(0, 0, 0), flat_angle=35)
    hp = Part('Hasp')
    for b, m in hasp:
        move(b, (0, 0, 0.1))
        hp.add(b, m, smooth=False)
    A.part(hp, pivot=(0, -0.024, 0.1), parent='Plate', flat_angle=35)
    A.root['ouat_size'] = 0.4
    A.meta['note'] = 'Hasp pivot = hinge axis (local X). Open: rotate Hasp local X ~ -100deg. Mount on a -Y facing surface; root = plate centre bottom.'
    return A


def latch_combined(scale, pos, angle=-90):
    """Single-object latch (plate+hasp) for embedding as a child named 'Latch'."""
    plate, hasp = latch_pieces(scale)
    bms = []
    for b, m in plate + hasp:
        place_on(b, pos, angle)
        bms.append((b, m))
    return bms


# ===================================================================== ladder (human)
def ladder_section(z0, z1, y, w=0.46, rungs=5, seed=0.0):
    bms = []
    for sx in (-1, 1):
        rail = bbox((sx * w / 2, y, (z0 + z1) / 2), (0.065, 0.045, abs(z1 - z0)), 0.014, 1)
        bms.append(rail)
    for i in range(rungs):
        z = z0 + (z1 - z0) * (i + 0.6) / (rungs + 0.2)
        bms.append(bm_tube([V((-w / 2 - 0.02, y, z)), V((-w / 4, y, z)), V((w / 4, y, z)), V((w / 2 + 0.02, y, z))], [0.017, 0.021, 0.021, 0.017], seg=6))
    return bms


def build_ladder():
    A = Asset('Ladder')
    H = 1.6
    base = Part('Base')
    for b in ladder_section(0.0, H, 0.0, seed=1):
        base.add(b, 'M_Wood', smooth=False)
    for sx in (-1, 1):
        base.add(bbox((sx * 0.23, -0.034, H - 0.05), (0.085, 0.012, 0.12), 0.004), 'M_Brass', smooth=False)
        for dz in (-0.09, -0.02):
            base.add(bm_cyl((sx * 0.23, -0.04, H + dz), (sx * 0.23, -0.046, H + dz), 0.009, seg=6), 'M_Iron', smooth=False)
        base.add(bbox((sx * 0.23, 0.0, 0.025), (0.085, 0.075, 0.05), 0.01), 'M_Iron', smooth=False)
        base.add(bbox((sx * 0.23, 0.0, 0.62), (0.075, 0.055, 0.035), 0.006), 'M_Brass', smooth=False)
    # a leather strap wound round the left rail (someone carried it)
    base.add(bm_tube([V((0.2, -0.04, 0.95)), V((0.27, -0.04, 0.98)), V((0.27, 0.04, 1.0)), V((0.19, 0.04, 1.02)), V((0.2, -0.04, 1.04))], 0.012, seg=4), 'M_Leather')
    A.part(base, pivot=(0, 0, 0), flat_angle=35)
    up = Part('Upper')
    yU = -0.065
    for b in ladder_section(H, 0.08, yU, seed=2):
        up.add(b, 'M_Wood', smooth=False)
    for sx in (-1, 1):
        up.add(bm_cyl((sx * 0.23 - 0.045, -0.035, H), (sx * 0.23 + 0.045, -0.035, H), 0.018, seg=8), 'M_Brass', smooth=False)
        up.add(bbox((sx * 0.23, yU, 0.06), (0.08, 0.06, 0.045), 0.008), 'M_Iron', smooth=False)
    A.part(up, pivot=(0, -0.035, H), parent='Base', flat_angle=35)
    lt = Part('Latch')
    for b, m in latch_combined(0.9, (0.23, -0.1, 0.42), angle=-90):
        lt.add(b, m, smooth=False)
    A.part(lt, pivot=(0.23, -0.1, 0.42), parent='Base', flat_angle=35)
    A.root['ouat_size'] = 1.6
    A.meta['note'] = ('Human object: fully finished, original colours (wood, brass hinges, iron feet, leather strap). Folded pose. Upper pivot = hinge '
                      'at top of Base (local X axis). To unfold: rotate Upper local X by 180 deg (~3.1 m). Latch holds Upper to Base near the foot.')
    return A


# ===================================================================== drawn bar + gap (낙하터 first puzzle)
def build_drawn_bar():
    A = Asset('DrawnBar')
    fr = Part('Frame')
    ln = []
    stone_post(fr, ln, -0.75, 1.42, 1.42, 1)
    stone_post(fr, ln, 0.75, 0.78, 1.42, 2)
    for sx, built in ((-1, True), (1, False)):
        x = sx * 0.75
        if built:
            fr.add(bbox((x - sx * 0.02, -0.13, 0.92), (0.24, 0.08, 0.07), 0.01), PAPER, smooth=False)
            ln.append((CR.line([V((x - 0.12, -0.175, 0.89)), V((x + 0.12, -0.175, 0.89))], 0.008, over=0.04), INK))
        else:
            ln.append((CR.box_wire((x - sx * 0.02, -0.13, 0.92), (0.24, 0.08, 0.07), 0.006, 0.06, seed=3), PENCIL))
    ln.append((CR.smudge(V((0.78, -0.12, 1.25)), V((0, -1, 0)), 0.5, 0.35, seed=4), SMUDGE))
    ln.append((CR.guides([((-1.3, -0.12, 1.42), (1.3, -0.12, 1.42))], 0.005, 0.3, seed=5), FAINT))
    A.part(fr, pivot=(0, 0, 0), flat_angle=35)
    A.part(lines_part(ln), pivot=(0, 0, 0), parent='Frame')
    bar = Part('Bar')
    core, inks = drawn_beam(V((-0.95, -0.2, 1.02)), V((0.95, -0.2, 1.02)), w=0.14, h=0.16, seed=3)
    bar.add(core, PAPER, smooth=False)
    bar.add(inks, INK, smooth=False)
    for k in range(3):   # wood grain drawn on the front of the bar
        z = 1.0 + (k - 1) * 0.035
        bar.add(CR.line([V((-0.8 + k * 0.1, -0.275, z)), V((-0.2 + k * 0.15, -0.275, z + 0.01)), V((0.5 + k * 0.08, -0.275, z - 0.008))], 0.005, over=0.0, seed=6 + k), INK, smooth=False)
    A.part(bar, pivot=(0, -0.2, 1.02), parent='Frame')
    A.root['ouat_size'] = 1.8
    A.meta['note'] = ('Left post built, right post built only to ~0.8 m (pencil above, its bracket only drawn). Bar = the drawn bolt (paper core + heavy ink). '
                      'Bar pivot = bar centre. Passage width between posts 1.34 m, passage along Y.')
    return A


def rock_slab(outline, z0, z1, seed, lean=0.0):
    b = bm_prism(outline, z0, z1, axis='Z')
    tri_ngons(b)
    deform(b, lambda c: V((c.x + lean * c.z, c.y, c.z)))
    jitter(b, 0.05, 1.5, seed)
    return b


def build_gap():
    A = Asset('Gap')
    w = Part('Wall')
    left = [(-2.2, -0.55), (-1.4, -0.7), (-0.18, -0.62), (-0.2, -0.2), (-0.16, 0.25), (-0.19, 0.62), (-1.2, 0.72), (-2.1, 0.6), (-2.35, 0.05)]
    right = [(0.18, -0.6), (1.1, -0.72), (2.1, -0.6), (2.3, 0.0), (2.05, 0.62), (1.0, 0.7), (0.18, 0.62), (0.15, 0.22), (0.19, -0.2)]
    cliff_part(w, left, [(3.1, 1.9, 0.95, (-0.05, 0.0)), (1.9, 0.0, 1.0, (0, 0))], seed=1, ink_r=0.022, hatch_r=0.012)
    cliff_part(w, right, [(2.7, 1.5, 0.93, (0.06, 0.02)), (1.5, 0.0, 1.0, (0, 0))], seed=2, ink_r=0.022, hatch_r=0.012)
    lip = bm_prism(jag_outline(0.45, 0.4, 7, 5, 0.2), 2.45, 2.9, axis='Z')
    tri_ngons(lip)
    jitter(lip, 0.05, 1.5, 9)
    w.add(lip, PAPER, smooth=False, face_mat=lambda c, n: SHADE if n.z < 0.5 else None)
    w.add(bbox((0, 0.0, 1.2), (0.3, 1.1, 2.4)), 'M_StoneDark', smooth=False)
    A.part(w, pivot=(0, 0, 0))
    # the rock was planned higher: its upper course exists only as pencil construction
    ln = [(edge_lines([[V((-0.17, -0.66, 0.0)), V((-0.19, -0.66, 1.2)), V((-0.16, -0.64, 2.4))],
                       [V((0.18, -0.64, 0.0)), V((0.2, -0.64, 1.1)), V((0.17, -0.62, 2.3))]], r=0.02, overshoot=0.12, seed=4), INK)]
    for k, (ol, z0, z1, sc) in enumerate(((left, 3.1, 4.1, 0.88), (right, 2.7, 3.6, 0.86))):
        pts = [V((x * sc, y * sc, z1)) for x, y in ol]
        ln.append((CR.line(pts + [pts[0]], 0.008, over=0.15, seed=10 + k, amp=0.02), PENCIL))
        for i in range(0, len(ol), 2):
            x, y = ol[i]
            ln.append((CR.line([V((x * 0.95, y * 0.95, z0)), V((x * sc, y * sc, z1))], 0.007, over=0.12, seed=12 + i), PENCIL))
    ln.append((CR.smudge(V((-1.2, -0.75, 3.5)), V((0, -1, 0)), 1.2, 0.6, seed=14), SMUDGE))
    A.part(lines_part(ln), pivot=(0, 0, 0), parent='Wall')
    A.root['ouat_size'] = 4.0
    A.meta['note'] = ('Slit ~0.33-0.4 m wide at x=0, passage along Y, 2.4 m high under a chock stone. Upper courses of both rocks only drawn (pencil). '
                      'Hero (0.72 m) cannot pass, Kinopio (~0.5 m) squeezes through. Leave a 0.35 m collider gap.')
    return A


# ===================================================================== cart (creature) + human wheel lock
def wheel(cx, r=0.42, w=0.08, spokes=6, seed=0.0):
    bms = []
    pts = [V((cx, math.cos(2 * math.pi * i / 14) * r, math.sin(2 * math.pi * i / 14) * r)) for i in range(15)]
    bms.append(bm_tube(pts, 0.05, seg=4, cap=False, flat=w / 0.1, up=(1, 0, 0)))
    bms.append(bm_cyl((cx - w * 0.9, 0, 0), (cx + w * 0.9, 0, 0), 0.08, seg=8))
    for i in range(spokes):
        a = 2 * math.pi * i / spokes + 0.2
        bms.append(bm_cyl((cx, 0, 0), (cx, math.cos(a) * r * 0.95, math.sin(a) * r * 0.95), 0.024, 0.018, seg=4))
    return bms


def build_cart():
    A = Asset('Cart')
    R = 0.42
    axle_z = R
    fr = Part('Frame')
    ln = []
    # bed (planks drawn)
    fr.add(bbox((0, 0.1, 0.75), (1.1, 1.5, 0.1), 0.02), PWOOD, smooth=False)
    for x in (-0.3, 0.0, 0.28):
        ln.append((CR.line([V((x, -0.66, 0.805)), V((x + 0.01, 0.86, 0.805))], 0.008, over=0.05), INK))
    # left side board built, painted red where the brush reached; the right board only drawn
    lb = CR.grid_box((0.56, 0.1, 0.95), (0.06, 1.5, 0.32), step=0.12)
    fr.add(lb, PWOOD, smooth=False, face_mat=CR.paint_patch((0.6, 0.45, 1.0), 0.45, seed=3, mat='M_PaintRed', amp=0.18))
    ln.append((CR.line([V((0.6, -0.65, 0.95)), V((0.6, 0.85, 0.96))], 0.007, over=0.05), INK))
    ln.append((CR.box_wire((-0.56, 0.1, 0.95), (0.06, 1.5, 0.32), 0.007, 0.12, seed=4, skip=(2, 3, 6, 7)), PENCIL))
    # back board: built from the left, stops half way at a torn edge
    bb = CR.grid_box((0, 0.86, 0.95), (1.18, 0.06, 0.32), step=0.08)
    torn_solid(fr, ln, bb, lambda c: 0.05 + nval(c, 6.0, 5) * 0.08 - (-c.x), PWOOD, back='M_PuppetJoint', thick=0.01, seed=5, back_near=0.25)
    ln.append((CR.line([V((-0.59, 0.83, 0.79)), V((-0.59, 0.83, 1.11)), V((0.0, 0.83, 1.11))], 0.007, over=0.1), PENCIL))
    # axle + under-beam
    fr.add(bm_cyl((-0.62, 0.1, axle_z), (0.62, 0.1, axle_z), 0.04, seg=6), PJOINT, smooth=False)
    fr.add(bbox((0, 0.1, 0.56), (0.9, 0.12, 0.3), 0.02), PWOOD, smooth=False)
    # handles: left built with a ball-joint grip, right only outlined
    fr.add(bm_tube([V((0.42, 0.6, 0.72)), V((0.44, -0.6, 0.72)), V((0.4, -1.45, 0.62))], [0.04, 0.035, 0.03], seg=6), PWOOD)
    fr.add(bm_sphere((0.4, -1.48, 0.62), (0.05,) * 3, seg=8, rings=5), PJOINT)
    for dz in (0.035, -0.035):
        ln.append((CR.line([V((-0.42, 0.6, 0.72 + dz)), V((-0.44, -0.6, 0.72 + dz)), V((-0.4, -1.45, 0.62 + dz * 0.8))], 0.008, over=0.1, seed=6 + dz), PENCIL))
    ln.append((CR.ellipse(V((-0.4, -1.48, 0.62)), 0.05, 0.05, 0.0, turns=1.1, n=10, r=0.005, seed=7, tilt=('Y', 90)), PENCIL))
    fr.add(bm_cyl((0, -0.55, 0.7), (0, -0.6, 0.0), 0.04, 0.035, seg=6), PWOOD, smooth=False)
    h = hatch_rect(V((-0.55, -0.66, 0.4)), V((1, 0, 0)), V((0, 0, 1)), 1.1, 0.3, n=8, r=0.006, seed=3, normal=V((0, -1, 0)))
    ln.append((h, HATCH))
    ln.append((CR.smudge(V((-0.6, 0.0, 1.05)), V((-1, 0, 0.2)), 0.9, 0.35, seed=8), SMUDGE))
    A.part(fr, pivot=(0, 0, 0), flat_angle=35)
    A.part(lines_part(ln), pivot=(0, 0, 0), parent='Frame')
    # near wheel built (WheelL, +X), far wheel only a pencil circle (WheelR, -X)
    wp = Part('WheelL')
    for b in wheel(0.68, R, seed=1):
        move(b, (0, 0.1, axle_z))
        wp.add(b, PWOOD, smooth=False)
    wp.add(CR.ellipse(V((0.73, 0.1, axle_z)), R * 0.98, R * 0.98, 0.0, turns=1.05, n=18, r=0.008, seed=9, tilt=('Y', 90)), INK, smooth=False)
    A.part(wp, pivot=(0.68, 0.1, axle_z), parent='Frame', flat_angle=35)
    wr = Part('WheelR')
    c = V((-0.68, 0.1, axle_z))
    for k, (rr, wd) in enumerate(((R + 0.04, 0.009), (R - 0.03, 0.007), (0.08, 0.007))):
        wr.add(CR.ellipse(c, rr, rr, 0.0, turns=1.08, n=20 if rr > 0.1 else 8, r=wd, seed=10 + k, tilt=('Y', 90)), PENCIL, smooth=False)
    for i in range(6):
        a = 2 * math.pi * i / 6 + 0.2
        wr.add(CR.line([c + V((0, math.cos(a) * 0.08, math.sin(a) * 0.08)), c + V((0, math.cos(a) * R * 0.96, math.sin(a) * R * 0.96))], 0.006, over=0.05, seed=14 + i), PENCIL, smooth=False)
    wr.add(CR.smudge(c + V((-0.03, 0, 0)), V((-1, 0, 0)), 0.8, 0.8, seed=20, lift=0.0), SMUDGE, smooth=False)
    A.part(wr, pivot=tuple(c), parent='Frame')
    lk = Part('WheelLock')
    c2 = V((0.68, -0.25, 0.45))
    lk.add(bm_tube([V((0.6, 0.05, 0.62)), V((0.6, -0.25, 0.62)), V((0.6, -0.33, 0.5))], 0.025, seg=5), 'M_Iron')
    clamp = [V((0.6, -0.33, 0.5)), V((0.6, -0.36, 0.38)), V((0.68, -0.38, 0.33)), V((0.77, -0.36, 0.38)), V((0.77, -0.33, 0.5))]
    lk.add(bm_tube(clamp, 0.03, seg=5, flat=0.6, up=(0, 1, 0)), 'M_Iron')
    lk.add(bm_cyl((0.55, -0.33, 0.5), (0.82, -0.33, 0.5), 0.018, seg=6), 'M_Iron')
    lk.add(bm_sphere((0.84, -0.33, 0.5), (0.03, 0.03, 0.03), seg=6, rings=4), 'M_Brass')
    lk.add(bbox((0.68, -0.37, 0.43), (0.05, 0.03, 0.06), 0.005), 'M_Brass', smooth=False)
    A.part(lk, pivot=c2, parent='Frame', flat_angle=35)
    A.root['ouat_size'] = 2.5
    A.meta['note'] = ('Front (-Y Blender / +Z Unity) = handles. Near wheel WheelL built; far wheel WheelR exists only as a pencil circle (line materials, '
                      'still spins with its pivot). Right board and right handle only drawn, back board stops half way. WheelLock = human iron clamp on WheelL.')
    return A


# ===================================================================== chair (creature)
def build_chair():
    A = Asset('Chair')
    ch = Part('Chair')
    ln = []
    seat_z = 0.5
    seat = bbox((0, 0.02, seat_z - 0.04), (0.62, 0.58, 0.08), 0.02)
    jitter(seat, 0.006, 4, 1)
    ch.add(seat, PWOOD, smooth=False)
    for x in (-0.1, 0.1):
        ln.append((CR.line([V((x, -0.27, seat_z + 0.002)), V((x + 0.01, 0.3, seat_z + 0.002))], 0.006, over=0.03, seed=x), INK))
    legs = [(-0.26, -0.22, 0.0), (0.27, -0.24, 0.02), (-0.27, 0.27, -0.01), (0.25, 0.26, 0.0)]
    for i, (x, y, dz) in enumerate(legs):
        pts = [V((x, y, seat_z - 0.08)), V((x * 1.05, y * 1.05, 0.25)), V((x * 1.12, y * 1.1, dz))]
        if i == 3:    # back-right leg only drawn
            for s in (-1, 1):
                ln.append((CR.line([p + V((0.032 * s, 0, 0)) for p in pts], 0.008, over=0.06, seed=20 + s), PENCIL))
            ln.append((CR.ellipse(pts[-1], 0.04, 0.04, 0.0, turns=1.1, n=10, r=0.005, seed=22), PENCIL))
        else:
            ch.add(bm_tube(pts, [0.035, 0.03, 0.038], seg=6), PWOOD)
            ch.add(bm_sphere(pts[0] + V((0, 0, -0.03)), (0.042,) * 3, seg=6, rings=4), PJOINT)
    # backrest: arched slab, its top-right shoulder never built (outline only)
    back_ol = [(x, z + seat_z) for x, z in arch2d(0.6, 0.95, 8)]
    bk = bm_prism(back_ol, 0.26, 0.32, axis='Y')
    bmesh.ops.triangulate(bk, faces=bk.faces[:])
    bmesh.ops.subdivide_edges(bk, edges=bk.edges[:], cuts=2, use_grid_fill=True)
    fld = lambda c: (0.92 + nval(c, 5.0, 3) * 0.06) - ((c.x + 0.05) * 0.9 + (c.z - seat_z) * 0.85)
    for b_ in (bk,):
        rot(b_, 'Y', 4, (0, 0.3, seat_z))
        rot(b_, 'X', -6, (0, 0.3, seat_z))
    torn_solid(ch, ln, bk, fld, PWOOD, back='M_PuppetJoint', thick=0.01, seed=4, back_near=0.25)
    ol3 = rot_pts(rot_pts([V((x, 0.245, z)) for x, z in back_ol], 'Y', 4, (0, 0.3, seat_z)), 'X', -6, (0, 0.3, seat_z))
    ln.append((CR.clipped_lines(ol3, lambda p: fld(p) < 0.02, 0.008, 0.08, 5), PENCIL))
    ch.add(bm_sphere((-0.3, 0.29, seat_z + 0.66), (0.045,) * 3, seg=8, rings=5), PJOINT)
    ln.append((CR.ellipse(V((0.3, 0.29, seat_z + 0.66)), 0.045, 0.045, 0.0, turns=1.1, n=10, r=0.005, seed=6, tilt=('X', 90)), PENCIL))
    ln.append((CR.line([V((-0.31, -0.27, seat_z)), V((0.31, -0.27, seat_z))], 0.008, over=0.05), INK))
    A.part(ch, pivot=(0, 0, 0), flat_angle=35)
    A.part(lines_part(ln), pivot=(0, 0, 0), parent='Chair')
    fc = Part('Face')
    f = bm_plane_uv((0, 0.245, seat_z + 0.6), (0.44, 0.44), '-Y')
    rot(f, 'Y', 4, (0, 0.3, seat_z))
    rot(f, 'X', -6, (0, 0.3, seat_z))
    fc.add(f, PWOOD, smooth=False)
    A.part(fc, pivot=(0, 0.245, seat_z + 0.6), parent='Chair')
    A.root['ouat_size'] = 1.2
    A.meta['note'] = ('Seat top z=0.5 (Unity y). Lump sits at seat centre. Back-right leg and the backrest\'s top-right shoulder exist only in pencil. '
                      'Face = UV quad on the backrest front for the inscription glyph texture.')
    return A


# ===================================================================== stage (painted, plaza)
def curtain(x0, x1, z_top, z_bot, y, tie_z, tie_side, folds=5, seed=0.0):
    """Gathered drape. Returns bmesh (solidified)."""
    b = bmesh.new()
    cols, rows = 9, 7
    grid = []
    for j in range(rows):
        t = j / (rows - 1)
        z = z_top + (z_bot - z_top) * t
        # gather towards the tie side around tie_z
        g = math.exp(-((z - tie_z) / 0.55) ** 2)
        row = []
        for i in range(cols):
            s = i / (cols - 1)
            xa = x0 + (x1 - x0) * s
            xt = tie_side + (xa - tie_side) * (1 - 0.72 * g)
            yy = y + 0.07 * math.sin(s * folds * math.pi + seed) * (0.6 + 0.6 * (1 - g))
            row.append(b.verts.new((xt, yy, z)))
        grid.append(row)
    for j in range(rows - 1):
        for i in range(cols - 1):
            b.faces.new((grid[j][i], grid[j][i + 1], grid[j + 1][i + 1], grid[j + 1][i]))
    bmesh.ops.recalc_face_normals(b, faces=b.faces)
    for f in b.faces:
        if f.normal.y > 0:
            f.normal_flip()
    bmesh.ops.solidify(b, geom=b.faces[:], thickness=0.04)
    return b


def build_stage():
    A = Asset('Stage')
    W, D, H = 6.0, 4.0, 0.8
    st = Part('Stage')
    plat = bbox((0, 0, H / 2), (W, D, H), 0.04, 1)
    st.add(plat, 'M_StageWood', smooth=False, face_mat=lambda c, n: 'M_Terracotta' if n.z < 0.5 and c.z < H - 0.08 else None)
    # trim along the top edge
    st.add(bbox((0, -D / 2 - 0.02, H - 0.05), (W + 0.06, 0.08, 0.1), 0.015), 'M_TerracottaDark', smooth=False)
    # front steps (centre)
    for i in range(3):
        sh = H * (i + 1) / 4
        st.add(bbox((0, -D / 2 - 0.3 * (3 - i) + 0.15, sh / 2), (1.7, 0.3, sh), 0.02), 'M_StageWood', smooth=False)
    # pillars + arch (proscenium) at the back
    yb = D / 2 - 0.35
    for sx in (-1, 1):
        x = sx * (W / 2 - 0.35)
        st.add(bm_lathe([(0.32, H), (0.28, H + 0.2), (0.24, H + 0.3), (0.24, H + 2.6), (0.3, H + 2.75), (0.3, H + 2.9)], seg=10, center=(x, yb, 0)), 'M_Terracotta', smooth=False)
    arch_outer = [(-W / 2 + 0.05, 0.0), (W / 2 - 0.05, 0.0), (W / 2 - 0.05, 1.3), (-W / 2 + 0.05, 1.3)]
    # arch band: an inverted U drawn as a thick prism along the top with a curved underside
    ol = [(-W / 2 + 0.05, 0.0), (-W / 2 + 0.6, 0.0)]
    n = 10
    for i in range(1, n):
        a = math.pi - math.pi * i / n
        ol.append((math.cos(a) * (W / 2 - 0.6), 0.55 * math.sin(a)))
    ol += [(W / 2 - 0.6, 0.0), (W / 2 - 0.05, 0.0), (W / 2 - 0.05, 1.0), (-W / 2 + 0.05, 1.0)]
    ab = bm_prism([(x, z + H + 2.9) for x, z in ol], yb - 0.25, yb + 0.25, axis='Y')
    tri_ngons(ab)
    st.add(ab, 'M_Terracotta', smooth=False)
    st.add(bbox((0, yb, H + 2.9 + 1.05), (W + 0.1, 0.6, 0.12), 0.02), 'M_TerracottaDark', smooth=False)
    # navy backdrop with a pale moon and a drawn village of lit windows
    by = D / 2 - 0.1
    st.add(bbox((0, by, H + 1.9), (W - 0.6, 0.06, 3.8), 0.01), 'M_BackdropNavy', smooth=False)
    moon = bm_cyl((0.9, by - 0.05, H + 3.0), (0.9, by - 0.08, H + 3.0), 0.32, seg=14)
    st.add(moon, 'M_Paper', smooth=False)
    houses = [(-2.1, 0.5, 1.0), (-1.4, 0.4, 0.75), (-0.6, 0.55, 1.2), (0.3, 0.45, 0.8), (1.6, 0.5, 1.05), (2.2, 0.35, 0.7)]
    for k, (x, w, h) in enumerate(houses):
        ol = [(-w / 2, 0), (w / 2, 0), (w / 2, h)] + [(math.cos(a) * w / 2, h + math.sin(a) * w * 0.45) for a in (0.6, 1.2, 1.9, 2.5)] + [(-w / 2, h)]
        hb = bm_prism([(x + u, H + v) for u, v in ol], by - 0.09, by - 0.05, axis='Y')
        tri_ngons(hb)
        st.add(hb, INK, smooth=False)
        st.add(bbox((x + 0.08 * (k % 2 * 2 - 1), by - 0.1, H + h * 0.55), (0.08, 0.02, 0.1)), 'M_LampGlow', smooth=False)
    # side curtains (gathered) + valance
    for sx in (-1, 1):
        x_out = sx * (W / 2 - 0.55)
        x_in = sx * 1.6
        c = curtain(min(x_out, x_in), max(x_out, x_in), H + 3.35, H + 0.02, yb - 0.32, H + 1.4, x_out, seed=sx)
        st.add(c, 'M_CurtainRed', smooth=True)
    val = [(-W / 2 + 0.5, 0.0)]
    for i in range(13):
        x = -W / 2 + 0.5 + (W - 1.0) * (i + 0.5) / 13
        val.append((x, -0.32 if i % 2 == 0 else -0.12))
    val += [(W / 2 - 0.5, 0.0), (W / 2 - 0.5, 0.35), (-W / 2 + 0.5, 0.35)]
    vb = bm_prism([(x, z + H + 3.45) for x, z in val], yb - 0.42, yb - 0.34, axis='Y')
    tri_ngons(vb)
    st.add(vb, 'M_CurtainRed', smooth=False)
    # lamps along the front edge
    for x in (-2.6, -1.2, 1.2, 2.6):
        st.add(bm_cyl((x, -D / 2 + 0.15, H), (x, -D / 2 + 0.15, H + 0.35), 0.03, seg=5), 'M_Iron', smooth=False)
        st.add(bbox((x, -D / 2 + 0.15, H + 0.45), (0.14, 0.14, 0.2), 0.01), 'M_LampGlow', smooth=False)
        st.add(bm_cyl((x, -D / 2 + 0.15, H + 0.55), (x, -D / 2 + 0.15, H + 0.64), 0.11, 0.02, seg=6), 'M_Iron', smooth=False)
    # the seat of the "inner body" (puppet seat) at back centre
    sy0 = 0.6  # PuppetSpot y (seat-front floor)
    seat_top = H + 0.47
    st.add(bbox((0, sy0 + 0.2, seat_top - 0.05), (0.62, 0.5, 0.1), 0.02), 'M_StageWood', smooth=False)
    st.add(bbox((0, sy0 + 0.2, seat_top + 0.01), (0.56, 0.44, 0.05), 0.015), 'M_CurtainRed', smooth=False)
    for sx in (-1, 1):
        for yy in (sy0 + 0.0, sy0 + 0.4):
            st.add(bm_cyl((sx * 0.26, yy, H), (sx * 0.26, yy, seat_top - 0.1), 0.035, seg=6), 'M_StageWood', smooth=False)
    back = bm_prism([(x, z + seat_top) for x, z in arch2d(0.64, 1.25, 6)], sy0 + 0.42, sy0 + 0.5, axis='Y')
    tri_ngons(back)
    st.add(back, 'M_StageWood', smooth=False)
    st.add(bm_cyl((0, sy0 + 0.41, seat_top + 0.95), (0, sy0 + 0.4, seat_top + 0.95), 0.12, seg=10), 'M_TerracottaDark', smooth=False)
    # ink: platform edges, step noses, board lines
    lines = [[V((-W / 2, -D / 2 - 0.03, H)), V((W / 2, -D / 2 - 0.03, H))],
             [V((-W / 2, -D / 2 - 0.03, 0.02)), V((-0.9, -D / 2 - 0.03, 0.02))], [V((0.9, -D / 2 - 0.03, 0.02)), V((W / 2, -D / 2 - 0.03, 0.02))]]
    for x in (-2.0, -1.0, 1.0, 2.0):
        lines.append([V((x, -D / 2, H + 0.005)), V((x, D / 2 - 0.2, H + 0.005))])
    for i in range(3):
        sh = H * (i + 1) / 4
        yy = -D / 2 - 0.3 * (3 - i)
        lines.append([V((-0.85, yy, sh + 0.004)), V((0.85, yy, sh + 0.004))])
    st.add(edge_lines(lines, r=0.012, overshoot=0.05, seed=5), INK, smooth=False)
    A.part(st, pivot=(0, 0, 0), flat_angle=35)
    # StageProp (받침대) with a human latch fixing it to the floor
    sp = Part('StageProp')
    pc = V((2.2, -0.9, H))
    sp.add(bbox(pc + V((0, 0, 0.35)), (0.55, 0.55, 0.7), 0.03), 'M_StageWood', smooth=False)
    sp.add(bbox(pc + V((0, 0, 0.72)), (0.65, 0.65, 0.06), 0.015), 'M_TerracottaDark', smooth=False)
    sp.add(edge_lines([[pc + V((-0.28, -0.28, 0.05)), pc + V((-0.28, -0.28, 0.66))], [pc + V((0.28, -0.28, 0.05)), pc + V((0.28, -0.28, 0.66))]], r=0.01, seed=7), INK, smooth=False)
    A.part(sp, pivot=pc, parent='Stage', flat_angle=35)
    lt = Part('Latch')
    lp = pc + V((0, -0.29, 0.18))
    for b, m in latch_combined(1.0, lp, angle=-90):
        lt.add(b, m, smooth=False)
    A.part(lt, pivot=lp, parent='StageProp', flat_angle=35)
    fc = Part('Face')
    fc.add(bm_plane_uv((-1.95, -D / 2 - 0.045, H * 0.5), (1.9, 0.5), '-Y'), 'M_Terracotta', smooth=False)
    A.part(fc, pivot=(-1.95, -D / 2 - 0.045, H * 0.5), parent='Stage')
    A.empty('PuppetSpot', (0, sy0, H), parent='Stage')
    A.root['ouat_size'] = 6.0
    A.meta['note'] = ('Platform top 0.8 m. PuppetSpot empty = seat-front floor (seat top 0.47 above it, seat back +0.42..+0.5 m behind). '
                      'StageProp = movable stand, child Latch (brass) pins it. Face = UV quad on the front skirt (left of the steps) for the engraved line. '
                      'Lamps: 4 x M_LampGlow boxes on the front edge at local (+-2.6/+-1.2, y=-1.85, z=1.25) - put small warm point lights there.')
    return A


# ===================================================================== boards
def build_picture_board():
    A = Asset('PictureBoard')
    pb = Part('Board')
    w, h, z0 = 2.4, 1.6, 0.9
    for sx in (-1, 1):
        pb.add(bbox((sx * (w / 2 + 0.05), 0.05, (z0 + h + 0.2) / 2), (0.12, 0.12, z0 + h + 0.2), 0.02), 'M_StageWood', smooth=False)
    # frame
    pb.add(bbox((0, 0.06, z0 - 0.04), (w + 0.2, 0.1, 0.1), 0.02), 'M_Terracotta', smooth=False)
    pb.add(bbox((0, 0.06, z0 + h + 0.04), (w + 0.2, 0.1, 0.1), 0.02), 'M_Terracotta', smooth=False)
    pb.add(bbox((0, 0.08, z0 + h / 2), (w, 0.04, h), 0.005), 'M_PageWhite', smooth=False)
    # brush emblem on top: handle + ink-dipped tip, in a terracotta disc
    cz = z0 + h + 0.42
    pb.add(bm_cyl((0, 0.07, cz), (0, 0.03, cz), 0.3, seg=14), 'M_Terracotta', smooth=False)
    pb.add(bm_tube([V((-0.18, 0.0, cz + 0.16)), V((0.06, 0.0, cz - 0.04))], [0.025, 0.03], seg=6), 'M_StageWood')
    pb.add(bm_tube([V((0.06, 0.0, cz - 0.04)), V((0.12, -0.0, cz - 0.1)), V((0.2, 0.0, cz - 0.2))], [0.05, 0.045, 0.004], seg=7), INK)
    pb.add(edge_lines([[V((-w / 2 - 0.1, -0.0, z0 - 0.1)), V((w / 2 + 0.1, -0.0, z0 - 0.1))]], r=0.012, seed=2), INK, smooth=False)
    A.part(pb, pivot=(0, 0, 0), flat_angle=35)
    fc = Part('Face')
    fc.add(bm_plane_uv((0, 0.055, z0 + h / 2), (w - 0.08, h - 0.08), '-Y'), 'M_PageWhite', smooth=False)
    A.part(fc, pivot=(0, 0.055, z0 + h / 2), parent='Board')
    A.root['ouat_size'] = 3.0
    A.meta['note'] = 'Face = 2.32 x 1.52 m UV quad (picture + five lines of glyphs as a texture). Painted (fully drawn, the king\'s board).'
    return A


def build_stone_tablet():
    A = Asset('StoneTablet')
    t = Part('Tablet')
    ln = []
    ol = [(-0.62, 0.0), (0.6, 0.0), (0.64, 1.1), (0.5, 1.5), (0.1, 1.68), (-0.4, 1.6), (-0.6, 1.25)]
    b = bm_prism(ol, -0.13, 0.13, axis='Y')
    bmesh.ops.triangulate(b, faces=b.faces[:])
    bmesh.ops.subdivide_edges(b, edges=b.edges[:], cuts=3, use_grid_fill=True)
    jitter(b, 0.012, 3, 2)
    rot(b, 'X', -6)
    corner = V((0.62, 0, 1.62))
    fld = lambda c: (V((c.x, 0, c.z)) - corner).length - 0.62 - nval(c, 3.0, 5) * 0.1 - nval(c, 11.0, 6) * 0.03
    full, res = torn_solid(t, ln, b, fld, PAPER, back=SHADE, thick=0.04, zig=0.03, seed=1, back_near=0.4, hatch_kw=dict(length=(0.06, 0.2), spacing=0.06))
    # the planned top contour continues as pencil
    top = rot_pts([V((p[0], -0.15, p[1])) for p in ((0.64, 1.1), (0.5, 1.5), (0.1, 1.68), (-0.05, 1.68))], 'X', -6)
    ln.append((CR.line(top, 0.008, over=0.12, seed=2, amp=0.01), PENCIL))
    lines = [rot_pts([V(p) for p in ((-0.63, -0.14, 0.02), (-0.6, -0.14, 1.25), (-0.4, -0.14, 1.6), (0.05, -0.14, 1.68))], 'X', -6)]
    ln.append((edge_lines(lines, r=0.014, overshoot=0.06, seed=1), INK))
    # plinth: built under the left half, drawn under the right
    t.add(bbox((-0.4, 0, 0.06), (0.75, 0.6, 0.14), 0.03), SHADE, smooth=False)
    ln.append((CR.box_wire((0.36, 0, 0.07), (0.78, 0.6, 0.14), 0.006, 0.1, seed=3), PENCIL))
    h = hatch_rect(V((0.62, -0.12, 0.05)), V((0, 1, 0)), V((0, 0, 1)), 0.26, 0.9, n=4, r=0.008, seed=3, normal=V((1, 0, 0)))
    ln.append((h, HATCH))
    ln.append((CR.smudge(V((0.55, -0.2, 1.5)), V((0, -1, 0.1)), 0.6, 0.4, seed=4), SMUDGE))
    A.part(t, pivot=(0, 0, 0))
    A.part(lines_part(ln), pivot=(0, 0, 0), parent='Tablet')
    fc = Part('Face')
    f = bm_plane_uv((0, -0.142, 0.78), (1.0, 1.1), '-Y')
    rot(f, 'X', -6)
    fc.add(f, PAPER, smooth=False)
    A.part(fc, pivot=(0, -0.142, 0.78), parent='Tablet')
    A.root['ouat_size'] = 1.7
    A.meta['note'] = 'Top-right shoulder of the slab never carved (torn stone + pencil contour); plinth half drawn. Face = 1.0 x 1.1 m UV quad for the glyph line.'
    return A


def build_signpost():
    A = Asset('Signpost')
    s = Part('Post')
    ln = []
    s.add(bm_tube([V((0, 0.05, 0)), V((0.02, 0.05, 0.9)), V((-0.01, 0.05, 1.85))], [0.065, 0.055, 0.05], seg=7), PWOOD)
    s.add(bm_sphere((0, 0.05, 1.88), (0.075,) * 3, seg=8, rings=5), PJOINT)
    # arrow board: body built (under the Face), the arrow tip only drawn
    ol = [(-0.62, -0.25), (0.6, -0.25), (0.6, 0.25), (-0.62, 0.25)]
    bd = bm_prism(ol, -0.03, 0.03, axis='Y')
    tri_ngons(bd)
    move(bd, (0, 0, 1.45))
    rot(bd, 'Y', -3, (0, 0, 1.45))
    s.add(bd, PWOOD, smooth=False)
    tip = rot_pts([V((0.6, -0.035, 1.2)), V((0.95, -0.035, 1.45)), V((0.6, -0.035, 1.7))], 'Y', -3, (0, 0, 1.45))
    ln.append((CR.line(tip, 0.01, over=0.08, seed=1), INK))
    ln.append((CR.line([tip[0] + V((0.02, 0.07, 0)), tip[1] + V((0.0, 0.07, 0)), tip[2] + V((0.02, 0.07, 0))], 0.006, over=0.05, seed=2), PENCIL))
    # a second board planned lower: pencil only
    ln.append((CR.box_wire((-0.1, 0.0, 0.88), (0.9, 0.06, 0.3), 0.006, 0.1, seed=3, rot_z=2), PENCIL))
    ln.append((CR.smudge(V((-0.1, -0.06, 0.88)), V((0, -1, 0)), 0.9, 0.35, seed=4), SMUDGE))
    ln.append((edge_lines([[V((-0.62, -0.035, 1.21)), V((0.6, -0.035, 1.18))], [V((-0.6, -0.035, 1.72)), V((0.6, -0.035, 1.69))]], r=0.01, seed=4), INK))
    A.part(s, pivot=(0, 0, 0), flat_angle=35)
    A.part(lines_part(ln), pivot=(0, 0, 0), parent='Post')
    # paint brushed over the left of the board; the brush stops mid-board (contour-cut ragged edge)
    pb = CR.grid_quad(V((-0.6, -0.037, 1.2)), V((1.2, 0, 0)), V((0, 0, 0.5)), 30, 10)
    bmesh.ops.reverse_faces(pb, faces=pb.faces)
    pfld = lambda c: -(c.x + 0.02 + nval(c, 4.0, 9) * 0.14 + nval(c * V((1, 1, 5)), 2.5, 2) * 0.1)
    pres = CR.cut_field(pb, pfld, zig=0.015, seed=9)
    rot(pres.built, 'Y', -3, (0, 0, 1.45))
    pp = Part('Paint')
    pp.add(pres.built, 'M_PaintRed', smooth=False)
    A.part(pp, pivot=(0, 0, 0), parent='Post')
    fc = Part('Face')
    f = bm_plane_uv((0, -0.034, 1.45), (1.1, 0.45), '-Y')
    rot(f, 'Y', -3, (0, 0, 1.45))
    fc.add(f, PWOOD, smooth=False)
    A.part(fc, pivot=(0, -0.034, 1.45), parent='Post')
    A.root['ouat_size'] = 1.9
    A.meta['note'] = ('Face = 1.1 x 0.45 m UV quad (two lines of glyphs); a red brush shape lies 3 mm in front of it on the left half, stopping mid-board. Arrow tip and a second lower '
                      'board only drawn in pencil.')
    return A


# ===================================================================== fence with drawn bolt
def build_fence_drawn_bar():
    A = Asset('Fence_DrawnBar')
    f = Part('Fence')
    ln = []
    posts = [-3.0, -2.0, -1.0, -0.85, 0.85, 2.0, 2.4, 3.0]
    for i, x in enumerate(posts):
        hh = 1.45 + 0.08 * math.sin(i * 2.1)
        if x >= 2.9:
            for s_ in (-1, 1):
                ln.append((CR.line([V((x + 0.06 * s_, 0, 0)), V((x + 0.05 * s_, 0, hh))], 0.007, over=0.12, seed=i + s_), PENCIL))
            ln.append((CR.ellipse(V((x, 0, hh + 0.03)), 0.07, 0.07, 0.0, n=10, r=0.005, seed=i), PENCIL))
            continue
        f.add(bm_tube([V((x, 0, 0)), V((x + 0.02, 0, hh * 0.5)), V((x - 0.01, 0, hh))], [0.075, 0.065, 0.06], seg=7), PWOOD)
        f.add(bm_sphere((x - 0.01, 0, hh + 0.03), (0.075,) * 3, seg=8, rings=5), PJOINT)
        if x < -0.9:
            f.add(bbox((x, 0.0, 0.05), (0.2, 0.2, 0.1), 0.02), PJOINT, smooth=False)
    for z in (0.45, 1.1):
        for a, b2, built in ((-3.0, -0.85, True), (0.85, 2.0, True), (2.4, 3.0, False)):
            if built:
                f.add(bbox(((a + b2) / 2, -0.07, z), (b2 - a, 0.05, 0.1), 0.012), PWOOD, smooth=False)
            else:
                ln.append((CR.box_wire(((a + b2) / 2, -0.07, z), (b2 - a, 0.05, 0.1), 0.006, 0.15, seed=z, skip=(1, 3, 5, 7, 9, 11)), PENCIL))
    pick = []
    for x in [-2.75, -2.5, -2.25, -1.75, -1.5, -1.25, 1.1, 1.35, 1.6, 1.85, 2.65]:
        pick.append([V((x, -0.1, 0.05)), V((x + 0.02, -0.1, 1.25))])
    ln.append((edge_lines(pick, r=0.008, overshoot=0.06, seed=3), INK))
    ln.append((CR.smudge(V((2.7, -0.12, 0.8)), V((0, -1, 0)), 0.8, 0.9, seed=4), SMUDGE))
    A.part(f, pivot=(0, 0, 0), flat_angle=35)
    A.part(lines_part(ln), pivot=(0, 0, 0), parent='Fence')
    g = Part('Gate')
    for z in (0.35, 0.8, 1.2):
        g.add(bbox((0.0, -0.05, z), (1.55, 0.05, 0.12), 0.012), PWOOD, smooth=False)
    for x in (-0.65, -0.2, 0.2, 0.65):
        g.add(bbox((x, -0.08, 0.75), (0.12, 0.04, 1.1), 0.012), PWOOD, smooth=False)
    br = bbox((0.0, -0.09, 0.78), (1.4, 0.035, 0.08), 0.008)
    rot(br, 'Y', 33, (0, 0, 0.78))
    g.add(br, PWOOD, smooth=False)
    A.part(g, pivot=V((-0.8, -0.05, 0)), parent='Fence', flat_angle=35)
    bar = Part('Bar')
    core, inks = drawn_beam(V((-1.0, -0.22, 0.95)), V((1.0, -0.22, 0.95)), w=0.12, h=0.14, seed=6)
    bar.add(core, PAPER, smooth=False)
    bar.add(inks, INK, smooth=False)
    for x in (-0.85, 0.85):
        bar.add(ink_poly([V((x - 0.08, -0.32, 0.86)), V((x - 0.08, -0.32, 1.06)), V((x + 0.08, -0.32, 1.06)), V((x + 0.08, -0.32, 0.86))], 0.014, seed=x), INK, smooth=False)
    A.part(bar, pivot=(0, -0.22, 0.95), parent='Fence')
    A.root['ouat_size'] = 6.0
    A.meta['note'] = ('Gate 1.6 m between x=-0.85..0.85, hinge at x=-0.8 (Gate local Z axis). Bar (drawn bolt) on the -Y side, lift it up. '
                      'Kid-size opening 0.33 m between posts x=2.0 and 2.4. Last post and the last rail section exist only in pencil.')
    return A


# ===================================================================== fish prop (stage play)
def build_fish_prop():
    A = Asset('FishProp')
    fp = Part('Prop')
    # upper jaw arc board
    up_ol = [(-1.15, 1.25), (-0.9, 1.15), (-0.5, 1.3), (0.0, 1.38), (0.5, 1.3), (0.9, 1.15), (1.15, 1.25),
             (1.1, 1.7), (0.8, 2.1), (0.3, 2.3), (-0.3, 2.3), (-0.8, 2.1), (-1.1, 1.7)]
    ub = bm_prism(up_ol, -0.05, 0.05, axis='Y')
    tri_ngons(ub)
    fp.add(ub, 'M_Fish', smooth=False)
    lo_ol = [(-1.1, 0.0), (1.1, 0.0), (1.15, 0.25), (0.7, 0.42), (0.0, 0.48), (-0.7, 0.42), (-1.15, 0.25)]
    lb = bm_prism(lo_ol, -0.05, 0.05, axis='Y')
    tri_ngons(lb)
    fp.add(lb, 'M_Fish', smooth=False)
    # side posts that hold it (stage carpentry, painted)
    for sx in (-1, 1):
        fp.add(bbox((sx * 1.2, 0.12, 1.15), (0.1, 0.1, 2.3), 0.015), 'M_StageWood', smooth=False)
    # teeth: paper triangles
    for i in range(9):
        x = -0.9 + 1.8 * i / 8
        z = 1.38 - 0.25 * abs(x) / 1.1 - 0.05
        tb = bm_prism([(x - 0.08, z + 0.05), (x + 0.08, z + 0.05), (x, z - 0.22)], -0.07, -0.04, axis='Y')
        fp.add(tb, PAPER, smooth=False)
    for i in range(7):
        x = -0.75 + 1.5 * i / 6
        z = 0.46 - 0.2 * abs(x) / 1.1
        tb = bm_prism([(x - 0.08, z - 0.04), (x + 0.08, z - 0.04), (x, z + 0.18)], -0.07, -0.04, axis='Y')
        fp.add(tb, PAPER, smooth=False)
    # eyes + drawn scales
    for sx in (-1, 1):
        fp.add(bm_cyl((sx * 0.62, -0.06, 1.85), (sx * 0.62, -0.09, 1.85), 0.13, seg=10), 'M_FishEye', smooth=False)
        fp.add(bm_cyl((sx * 0.62, -0.09, 1.85), (sx * 0.62, -0.1, 1.85), 0.05, seg=8), INK, smooth=False)
    lines = []
    for k in range(4):
        x = -0.45 + 0.3 * k
        lines.append([V((x - 0.12, -0.06, 2.0)), V((x, -0.06, 2.12)), V((x + 0.12, -0.06, 2.0))])
    lines.append([V(p) for p in ((-1.15, -0.06, 1.25), (-1.1, -0.06, 1.7), (-0.8, -0.06, 2.1), (-0.3, -0.06, 2.3), (0.3, -0.06, 2.3), (0.8, -0.06, 2.1), (1.1, -0.06, 1.7), (1.15, -0.06, 1.25))])
    fp.add(edge_lines(lines, r=0.016, overshoot=0.05, seed=2), INK, smooth=False)
    A.part(fp, pivot=(0, 0, 0), flat_angle=35)
    A.root['ouat_size'] = 2.4
    A.meta['note'] = 'Flat cut-out fish head facing -Y (Unity +Z); an actor stands at (0,0,0) inside the open mouth (mouth opening 0.48..1.25 m high, ~2 m wide).'
    return A


# ===================================================================== human junk (vivid)
def junk_book(color='M_BookRed', s=1.0):
    w, d, t = 0.28 * s, 0.36 * s, 0.07 * s
    out = []
    out.append((bbox((0, 0, t / 2), (w, d, t), 0.008 * s), color))
    out.append((bbox((0.012 * s, 0, t / 2), (w - 0.012 * s, d - 0.02 * s, t - 0.016 * s), 0.002), 'M_PageWhite'))
    out.append((bm_cyl((-w / 2, -d / 2, t / 2), (-w / 2, d / 2, t / 2), t / 2, seg=6), color))
    out.append((bbox((0.04 * s, 0, t + 0.001), (0.12 * s, 0.08 * s, 0.003 * s)), 'M_Brass'))
    for k in (-1, 1):   # spine bands
        out.append((bm_cyl((-w / 2, k * d * 0.3 - 0.008 * s, t / 2), (-w / 2, k * d * 0.3 + 0.008 * s, t / 2), t / 2 + 0.004 * s, seg=6), 'M_Brass'))
    out.append((bm_blade([V((0.03, d / 2 - 0.02, t * 0.6)) * 1, V((0.05, d / 2 + 0.05, t * 0.3)), V((0.06, d / 2 + 0.09, 0.004))],
                         [0.008 * s, 0.008 * s, 0.006 * s], thick=0.002, up=(0, 0, 1)), 'M_Rope'))
    return out


def junk_umbrella(s=1.0):
    out = []
    tip = V((0, -0.52, 0.07)) * s
    n = 8
    b = bmesh.new()
    apex = b.verts.new(tip)
    mid = []
    rim = []
    for i in range(n):
        a = 2 * math.pi * i / n
        r1 = (0.075 if i % 2 == 0 else 0.05) * s
        r2 = (0.13 if i % 2 == 0 else 0.085) * s
        mid.append(b.verts.new(V((math.cos(a) * r1, -0.15 * s, 0.13 * s + math.sin(a) * r1))))
        rim.append(b.verts.new(V((math.cos(a) * r2, 0.2 * s, 0.13 * s + math.sin(a) * r2))))
    for i in range(n):
        j = (i + 1) % n
        b.faces.new((apex, mid[i], mid[j]))
        b.faces.new((mid[i], rim[i], rim[j], mid[j]))
    bmesh.ops.recalc_face_normals(b, faces=b.faces)
    bmesh.ops.solidify(b, geom=b.faces[:], thickness=0.006 * s)
    out.append((b, 'M_BookRed'))
    out.append((bm_cyl(tip + V((0, -0.07, 0)) * s, V((0, 0.42, 0.13)) * s, 0.011 * s, seg=6), 'M_Iron'))
    out.append((bm_sphere(V((0, 0.22, 0.13)) * s, (0.02 * s,) * 3, seg=6, rings=4), 'M_Brass'))
    hook = [V((0, 0.42, 0.13)) * s, V((0, 0.5, 0.125)) * s, V((0, 0.545, 0.08)) * s, V((0, 0.515, 0.035)) * s, V((0, 0.47, 0.045)) * s]
    out.append((bm_tube(hook, 0.022 * s, seg=6), 'M_Wood'))
    out.append((bm_tube([V((0.05, 0.18, 0.2)) * s, V((0.13, 0.31, 0.33)) * s], 0.005 * s, seg=4), 'M_Iron'))
    out.append((bm_tube([V((0.02, 0.1, 0.25)) * s, V((0.03, 0.13, 0.27)) * s], 0.012 * s, seg=5), 'M_Rope'))
    return out


def junk_clock(s=1.0):
    out = []
    c = V((0, 0, 0.14)) * s
    out.append((bm_cyl(c + V((0, 0.04, 0)) * s, c + V((0, -0.04, 0)) * s, 0.12 * s, seg=14), 'M_BookBlue'))
    out.append((bm_cyl(c + V((0, -0.04, 0)) * s, c + V((0, -0.048, 0)) * s, 0.1 * s, seg=14), 'M_Porcelain'))
    out.append((bm_tube([c + V((0, -0.05, 0)) * s, c + V((0.0, -0.05, 0.07)) * s], 0.008 * s, seg=3), INK))
    out.append((bm_tube([c + V((0, -0.05, 0)) * s, c + V((0.05, -0.05, -0.02)) * s], 0.008 * s, seg=3), INK))
    for sx in (-1, 1):
        out.append((bm_sphere(c + V((sx * 0.08, 0, 0.12)) * s, (0.05 * s, 0.05 * s, 0.035 * s), seg=8, rings=5), 'M_Brass'))
        out.append((bm_cyl(c + V((sx * 0.08, 0, -0.1)) * s, c + V((sx * 0.1, 0, -0.14)) * s, 0.015 * s, seg=5), 'M_Brass'))
    out.append((bm_tube([c + V((-0.06, 0, 0.14)) * s, c + V((0, 0, 0.19)) * s, c + V((0.06, 0, 0.14)) * s], 0.01 * s, seg=4), 'M_Brass'))
    return out


def junk_shoe(s=1.0):
    out = []
    sole = bm_lathe([(0.0, 0.0), (0.05, 0.0), (0.055, 0.025), (0.0, 0.03)], seg=10, sx=1.0, sy=2.4)
    move(sole, (0, -0.02, 0))
    out.append((sole, 'M_Iron'))
    body = bm_sphere((0, -0.03 * s, 0.06 * s), (0.055 * s, 0.13 * s, 0.05 * s), seg=10, rings=6)
    deform(body, lambda q: V((q.x, q.y, max(q.z, 0.02 * s))))
    out.append((body, 'M_Leather'))
    shaft = bm_tube([V((0, 0.06, 0.05)) * s, V((0, 0.065, 0.2)) * s], [0.055 * s, 0.05 * s], seg=8)
    out.append((shaft, 'M_Leather'))
    out.append((bm_tube([V((-0.05, 0.03, 0.12)) * s, V((0.05, 0.03, 0.14)) * s], 0.006 * s, seg=4), 'M_BookRed'))
    return out


def junk_teacup(s=1.0):
    out = []
    out.append((bm_lathe([(0.0, 0.0), (0.1, 0.0), (0.11, 0.012), (0.0, 0.014)], seg=12), 'M_Porcelain'))
    cup = bm_lathe([(0.0, 0.012), (0.035, 0.014), (0.05, 0.03), (0.06, 0.07), (0.063, 0.085), (0.055, 0.085), (0.0, 0.075)], seg=12)
    out.append((cup, 'M_Porcelain'))
    out.append((bm_lathe([(0.0605, 0.068), (0.0625, 0.08)], seg=12, cap_top=False, cap_bottom=False), 'M_BookBlue'))
    out.append((bm_tube([V((0.06, 0, 0.07)), V((0.09, 0, 0.065)), V((0.085, 0, 0.035)), V((0.055, 0, 0.032))], 0.008, seg=4, cap=True), 'M_Porcelain'))
    out = [(b if s == 1 else L.xform(b, Matrix.Scale(s, 4)) or b, m) for b, m in out]
    return out


def junk_lantern(s=1.0):
    out = []
    out.append((bm_cyl((0, 0, 0), (0, 0, 0.03 * s), 0.09 * s, seg=8), 'M_Iron'))
    out.append((bm_cyl((0, 0, 0.03 * s), (0, 0, 0.2 * s), 0.065 * s, seg=8), 'M_Porcelain'))
    for i in range(4):
        a = math.pi / 4 + math.pi / 2 * i
        x, y = math.cos(a) * 0.075 * s, math.sin(a) * 0.075 * s
        out.append((bm_cyl((x, y, 0.02 * s), (x, y, 0.21 * s), 0.008 * s, seg=4), 'M_Iron'))
    out.append((bm_cyl((0, 0, 0.2 * s), (0, 0, 0.28 * s), 0.09 * s, 0.03 * s, seg=8), 'M_Brass'))
    out.append((bm_tube([V((-0.05, 0, 0.27)) * s, V((-0.04, 0, 0.36)) * s, V((0.04, 0, 0.36)) * s, V((0.05, 0, 0.27)) * s], 0.007 * s, seg=4), 'M_Iron'))
    return out


def junk_asset(name, pieces, size, note=''):
    A = Asset(name)
    p = Part('Item')
    for b, m in pieces:
        p.add(b, m, smooth=False)
    A.part(p, pivot=(0, 0, 0), flat_angle=35)
    A.root['ouat_size'] = size
    if note:
        A.meta['note'] = note
    return A


def build_junk_book():
    return junk_asset('Junk_Book', junk_book('M_BookRed'), 0.4, 'Red hardcover. For green/blue variants tint M_BookGreen/M_BookBlue in Unity or use ItemPile.')


def build_junk_umbrella():
    return junk_asset('Junk_Umbrella', junk_umbrella(), 1.0)


def build_junk_clock():
    return junk_asset('Junk_Clock', junk_clock(), 0.4)


def build_junk_shoe():
    return junk_asset('Junk_Shoe', junk_shoe(), 0.35)


def build_junk_teacup():
    return junk_asset('Junk_Teacup', junk_teacup(), 0.25)


def build_junk_lantern():
    return junk_asset('Junk_Lantern', junk_lantern(), 0.4, 'Unlit fallen lantern (glass = M_Porcelain).')


def placed(pieces, pos, rz=0.0, rx=0.0, ry=0.0):
    out = []
    for b, m in pieces:
        if rx:
            rot(b, 'X', rx)
        if ry:
            rot(b, 'Y', ry)
        rot(b, 'Z', rz)
        move(b, pos)
        out.append((b, m))
    return out


def build_item_pile():
    A = Asset('ItemPile')
    p = Part('Pile')
    H0, R0 = 0.38, 1.05

    def hgt(x, y):
        r = math.sqrt(x * x + (y / 0.8) ** 2) / R0
        return max(0.0, H0 * (1 - r * r))
    mound = bm_lathe([(0.0, 0.0), (R0, 0.0)] + [(R0 * math.sqrt(1 - t), H0 * t) for t in (0.3, 0.6, 0.85)] + [(0.0, H0)], seg=12, sy=0.8)
    jitter(mound, 0.04, 2.0, 3)
    deform(mound, lambda c: V((c.x, c.y, max(0.0, c.z))))
    p.add(mound, PAPER, smooth=False, face_mat=lambda c, n: SHADE if (n.x * 0.6 + n.y * 0.8) > 0.35 else None)
    items = []

    def put(pcs, x, y, dz=0.0, **kw):
        items.extend(placed(pcs, V((x, y, hgt(x, y) + dz)), **kw))
    put(junk_book('M_BookRed'), 0.25, -0.3, -0.02, rz=20, rx=-12)
    put(junk_book('M_BookGreen'), -0.35, -0.2, -0.02, rz=-35, ry=14)
    put(junk_book('M_BookBlue'), 0.0, 0.05, 0.0, rz=70, rx=6)
    put(junk_book('M_BookRed', 0.9), 0.02, 0.02, 0.07, rz=55, ry=-8)
    put(junk_book('M_BookGreen', 0.85), 0.75, 0.15, 0.0, rz=10, ry=-12)
    put(junk_book('M_BookBlue', 0.9), -0.8, -0.1, 0.0, rz=-15, ry=10)
    put(junk_clock(), -0.15, -0.55, -0.02, rz=15, rx=-25)
    put(junk_umbrella(), 0.45, 0.3, 0.0, rz=-60, ry=10)
    put(junk_teacup(), -0.6, 0.25, 0.0, ry=25)
    put(junk_shoe(), 0.6, -0.5, 0.0, rz=-30)
    put(junk_lantern(), -0.35, 0.45, 0.02, rx=70)
    for b, m in items:
        p.add(b, m, smooth=False)
    p.add(edge_lines([[V((-0.9, -0.62, 0.05)), V((-0.3, -0.84, 0.03)), V((0.4, -0.8, 0.04))]], r=0.012, seed=7), INK, smooth=False)
    A.part(p, pivot=(0, 0, 0), flat_angle=35)
    A.root['ouat_size'] = 2.2
    return A


def build_pinocchio_page():
    A = Asset('PinocchioPage')
    w, h = 0.45, 0.6
    nx, ny = 6, 8

    def curl(x, y):
        # lifted, curled corner (+x,+y) and a gentle sag
        k = max(0.0, (x / w + y / h) - 0.9)
        return 0.006 + 0.12 * k * k + 0.01 * math.sin(x * 9)

    def torn(j):
        # torn left edge (x offset per row)
        return 0.025 * math.sin(j * 2.7) + 0.02 * ((j * 37) % 5) / 5.0

    pg = Part('Page')
    b = bmesh.new()
    grid = []
    for j in range(ny + 1):
        row = []
        for i in range(nx + 1):
            x = (i / nx) * w - w / 2
            if i == 0:
                x += torn(j)
            y = (j / ny) * h - h / 2
            row.append(b.verts.new(V((x, y, curl(x + w / 2, y + h / 2)))))
        grid.append(row)
    for j in range(ny):
        for i in range(nx):
            b.faces.new((grid[j][i], grid[j][i + 1], grid[j + 1][i + 1], grid[j + 1][i]))
    bmesh.ops.recalc_face_normals(b, faces=b.faces)
    for f in b.faces:
        if f.normal.z < 0:
            f.normal_flip()
    bmesh.ops.solidify(b, geom=b.faces[:], thickness=0.004)
    pg.add(b, 'M_PageWhite', smooth=True)
    A.part(pg, pivot=(0, 0, 0))
    fc = Part('Face')
    f = bmesh.new()
    uv = f.loops.layers.uv.new('UVMap')
    m = 0.03
    grid = []
    for j in range(ny + 1):
        row = []
        for i in range(nx + 1):
            u, v = i / nx, j / ny
            x = -w / 2 + m + 0.02 + u * (w - 2 * m - 0.02)
            y = -h / 2 + m + v * (h - 2 * m)
            row.append(f.verts.new(V((x, y, curl(x + w / 2, y + h / 2) + 0.003))))
        grid.append(row)
    for j in range(ny):
        for i in range(nx):
            face = f.faces.new((grid[j][i], grid[j][i + 1], grid[j + 1][i + 1], grid[j + 1][i]))
            for loop, (di, dj) in zip(face.loops, ((0, 0), (1, 0), (1, 1), (0, 1))):
                loop[uv].uv = ((i + di) / nx, (j + dj) / ny)
    fc.add(f, 'M_PageWhite', smooth=True)
    A.part(fc, pivot=(0, 0, 0.003), parent='Page')
    A.root['ouat_size'] = 0.6
    A.meta['note'] = 'Lies flat on the ground, top = Unity +Y. Face = curled UV grid (0..1) for the page picture (Pinocchio plate 3) + text. Torn edge on the left (-X Blender / +X Unity).'
    return A


def build_mound():
    A = Asset('Mound')
    p = Part('Mound')
    L_, W_, H_ = 6.0, 1.5, 0.6

    def hgt(x, y):
        t = max(0.0, 1 - (2 * y / W_) ** 2)
        e = max(0.0, 1 - (2 * x / L_) ** 4)
        return H_ * t * e + 0.03 * math.sin(x * 1.7 + y)
    b = bmesh.new()
    nx, ny = 14, 6
    grid = []
    for j in range(ny + 1):
        row = []
        for i in range(nx + 1):
            x = -L_ / 2 + L_ * i / nx
            y = -W_ / 2 + W_ * j / ny
            row.append(b.verts.new(V((x, y, max(0.0, hgt(x, y))))))
        grid.append(row)
    for j in range(ny):
        for i in range(nx):
            b.faces.new((grid[j][i], grid[j][i + 1], grid[j + 1][i + 1], grid[j + 1][i]))
    bmesh.ops.recalc_face_normals(b, faces=b.faces)
    for f in b.faces:
        if f.normal.z < 0:
            f.normal_flip()
    p.add(b, PAPER, smooth=True, face_mat=lambda c, n: SHADE if n.y > 0.45 else None)
    lines = []
    for k, yy in enumerate((-0.3, 0.02, 0.3)):
        x0, x1 = -2.5 + 0.25 * k, 2.4 - 0.3 * k
        lines.append([V((x0 + (x1 - x0) * t, yy, hgt(x0 + (x1 - x0) * t, yy) + 0.02)) for t in (0, 0.2, 0.4, 0.6, 0.8, 1.0)])
    p.add(edge_lines(lines, r=0.011, overshoot=0.08, seed=2), INK, smooth=False)
    hl = []
    for i in range(16):
        x = -2.3 + 4.6 * i / 15
        y0, y1 = 0.25, 0.68
        hl.append(stroke([V((x, y0, hgt(x, y0) + 0.02)), V((x + 0.18, y1, hgt(x + 0.18, y1) + 0.02))], 0.01, seg=3))
    p.add(merge(hl), HATCH, smooth=False)
    for b2, m in placed(junk_book('M_BookBlue', 0.8), V((1.4, -0.35, hgt(1.4, -0.35) - 0.05)), rz=30, rx=-50):
        p.add(b2, m, smooth=False)
    for b2, m in placed(junk_teacup(), V((-1.6, -0.4, hgt(-1.6, -0.4) - 0.02)), rx=-35):
        p.add(b2, m, smooth=False)
    A.part(p, pivot=(0, 0, 0))
    A.root['ouat_size'] = 6.0
    return A


def build_lamp_post():
    A = Asset('LampPost')
    p = Part('Post')
    p.add(bm_lathe([(0.17, 0.0), (0.17, 0.08), (0.13, 0.12), (0.12, 0.22), (0.07, 0.3), (0.05, 0.6), (0.045, 2.55), (0.065, 2.62), (0.05, 2.7), (0.0, 2.72)], seg=10), 'M_Iron', smooth=False)
    for z in (0.62, 1.4):
        p.add(bm_lathe([(0.04, z - 0.03), (0.07, z), (0.04, z + 0.03)], seg=10, cap_top=False, cap_bottom=False), 'M_Brass', smooth=False)
    arm = [V((0, 0, 2.55)), V((0.1, 0, 2.8)), V((0.28, 0, 2.92)), V((0.4, 0, 2.9))]
    p.add(bm_tube(arm, 0.022, seg=6), 'M_Iron')
    scroll = [V((0.02, 0, 2.45)), V((0.14, 0, 2.5)), V((0.2, 0, 2.62)), V((0.14, 0, 2.7)), V((0.09, 0, 2.63))]
    p.add(bm_tube(scroll, 0.012, seg=5), 'M_Iron')
    lc = V((0.38, 0, 2.62))
    p.add(bm_cyl(lc + V((0, 0, 0.28)), lc + V((0, 0, 0.18)), 0.012, seg=5), 'M_Iron', smooth=False)
    p.add(bm_cyl(lc + V((0, 0, 0.1)), lc + V((0, 0, 0.2)), 0.16, 0.03, seg=6), 'M_Iron', smooth=False)
    p.add(bm_sphere(lc + V((0, 0, 0.22)), (0.025,) * 3, seg=6, rings=4), 'M_Brass')
    p.add(bm_cyl(lc + V((0, 0, -0.14)), lc + V((0, 0, 0.1)), 0.085, 0.11, seg=6), 'M_LampGlow', smooth=False)
    for i in range(6):
        a = 2 * math.pi * i / 6 + math.pi / 6
        p.add(bm_cyl(lc + V((math.cos(a) * 0.092, math.sin(a) * 0.092, -0.15)), lc + V((math.cos(a) * 0.118, math.sin(a) * 0.118, 0.1)), 0.008, seg=4), 'M_Iron', smooth=False)
    p.add(bm_cyl(lc + V((0, 0, -0.2)), lc + V((0, 0, -0.14)), 0.1, seg=6), 'M_Iron', smooth=False)
    p.add(bm_cyl(lc + V((0, 0, -0.26)), lc + V((0, 0, -0.2)), 0.02, 0.07, seg=6), 'M_Brass', smooth=False)
    A.part(p, pivot=(0, 0, 0), flat_angle=35)
    A.root['ouat_size'] = 3.0
    A.meta['note'] = 'Plaza = finished. Lamp glass (M_LampGlow) centre at local (0.38, 2.6 up, 0) Blender x -> Unity -x. Add a warm point light there (range ~6 m).'
    return A
ASSETS = [
    ('Ladder', build_ladder), ('Latch', build_latch), ('DrawnBar', build_drawn_bar), ('Gap', build_gap),
    ('Cart', build_cart), ('Chair', build_chair), ('Stage', build_stage), ('PictureBoard', build_picture_board),
    ('StoneTablet', build_stone_tablet), ('Signpost', build_signpost), ('Fence_DrawnBar', build_fence_drawn_bar),
    ('FishProp', build_fish_prop), ('Junk_Book', build_junk_book), ('Junk_Umbrella', build_junk_umbrella),
    ('Junk_Clock', build_junk_clock), ('Junk_Shoe', build_junk_shoe), ('Junk_Teacup', build_junk_teacup),
    ('Junk_Lantern', build_junk_lantern), ('ItemPile', build_item_pile), ('PinocchioPage', build_pinocchio_page),
    ('Mound', build_mound), ('LampPost', build_lamp_post),
]
