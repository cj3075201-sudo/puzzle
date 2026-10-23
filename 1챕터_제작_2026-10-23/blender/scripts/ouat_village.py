# -*- coding: utf-8 -*-
"""Village kit: domed towers (paint level = completion), paving lines, spires, cliffs, cave walls, rocks,
pond, light shaft, ceiling hole. Blender coords: Z up, front -Y, root at floor centre."""
import math, random
import bmesh
from mathutils import Vector
import ouat_lib as L
from ouat_lib import (Part, Asset, bm_sphere, bm_tube, bm_blade, bm_box, bm_cyl, bm_lathe, bm_prism, stroke,
                      wobble_line, rot, move, deform, jitter, subdivide, nvec, nval)
from ouat_props import (tri_ngons, merge, bbox, ink_poly, edge_lines, hatch_rect, arch2d, place_on, arch_panel,
                        arch_outline, jag_outline, cliff_part, PAPER, SHADE, INK, HATCH)

V = Vector
TERRA, TERRA_D = 'M_Terracotta', 'M_TerracottaDark'


# ===================================================================== tower helpers
def paint_fn(thr, amp=0.75, seed=0.0, mat=TERRA):
    """faces above a ragged height threshold are painted (brushed from the top down).
    Two noise octaves: broad wandering edge + short brush streaks."""
    if thr is None:
        return None

    def fn(c, n):
        v = c.z + L.nval(c, 0.9, seed) * amp + L.nval(c * V((3.0, 3.0, 0.4)), 2.5, seed + 7) * amp * 0.6
        return mat if v > thr else None
    return fn


def is_painted(z, thr):
    return thr is not None and z > thr


def drum(part, cx, cy, z0, h, r0, r1, seg=14, ring_step=0.4, thr=None, seed=0.0, lean=0.0, mat=PAPER, wobble=0.04):
    """Cylinder (slightly tapered) built in rings so the ragged paint edge has resolution."""
    n = max(2, int(h / ring_step))
    prof = [(r0 + (r1 - r0) * i / n, z0 + h * i / n) for i in range(n + 1)]
    b = bm_lathe(prof, seg=seg, center=(cx, cy, 0), cap_top=True, cap_bottom=False)
    tri_ngons(b)
    jitter(b, wobble, 1.2, seed)
    if lean:
        deform(b, lambda c: V((c.x + lean * (c.z - z0), c.y, c.z)))
    part.add(b, mat, smooth=True, face_mat=paint_fn(thr, seed=seed))
    return b


def dome(part, cx, cy, z0, r, hk=0.9, seg=14, rings=5, thr=None, seed=0.0, mat=PAPER, a0=0.0, a1=360.0, lean=0.0, z_lean0=0.0):
    """Dome (optionally partial in angle a0..a1 deg -> open, for broken domes)."""
    full = (a1 - a0) >= 359.9
    b = bmesh.new()
    rows = []
    nseg = seg if full else max(3, int(seg * (a1 - a0) / 360.0))
    for j in range(rings + 1):
        t = j / rings
        ang = t * math.pi / 2
        rr = r * math.cos(ang)
        z = z0 + r * hk * math.sin(ang)
        row = []
        cnt = nseg if full else nseg + 1
        for i in range(cnt):
            a = math.radians(a0 + (a1 - a0) * i / nseg)
            row.append(b.verts.new(V((cx + math.cos(a) * rr, cy + math.sin(a) * rr, z))))
        rows.append(row)
    for j in range(rings):
        cnt = len(rows[j])
        rng = range(cnt) if full else range(cnt - 1)
        for i in rng:
            i2 = (i + 1) % cnt
            b.faces.new((rows[j][i], rows[j][i2], rows[j + 1][i2], rows[j + 1][i]))
    bmesh.ops.remove_doubles(b, verts=b.verts, dist=1e-4)
    bmesh.ops.recalc_face_normals(b, faces=b.faces)
    for f in b.faces:
        c = f.calc_center_median()
        if (c - V((cx, cy, z0))).dot(f.normal) < 0:
            f.normal_flip()
    if not full:
        bmesh.ops.solidify(b, geom=b.faces[:], thickness=0.12)
    jitter(b, 0.03, 1.5, seed)
    if lean:
        deform(b, lambda c: V((c.x + lean * (c.z - z_lean0), c.y, c.z)))
    part.add(b, mat, smooth=True, face_mat=paint_fn(thr, seed=seed + 1))
    return b


def chimney(part, x, y, z0, h, r=0.18, thr=None, tilt=(0.0, 0.0), seed=0.0):
    top = V((x + tilt[0], y + tilt[1], z0 + h))
    mat = TERRA if is_painted(z0 + h, thr) else PAPER
    capm = TERRA_D if is_painted(z0 + h, thr) else SHADE
    part.add(bm_tube([V((x, y, z0)), V((x, y, z0)).lerp(top, 0.5), top], [r, r * 0.95, r * 0.9], seg=7), mat)
    part.add(bm_cyl(top - V((0, 0, 0.02)), top + V((0, 0, 0.16)), r * 1.35, r * 1.3, seg=7), capm, smooth=False)
    part.add(bm_cyl(top + V((0, 0, 0.16)), top + V((0, 0, 0.17)), r * 0.85, seg=7), INK, smooth=False)


def merlons(part, cx, cy, z, r, n=12, w=0.22, h=0.32, thr=None, seed=0.0):
    mat = TERRA if is_painted(z, thr) else PAPER
    for i in range(n):
        a = 2 * math.pi * i / n
        b = bbox((0, 0, 0), (w, 0.2, h), 0.02)
        rot(b, 'Z', math.degrees(a) + 90)
        move(b, (cx + math.cos(a) * r, cy + math.sin(a) * r, z + h / 2))
        part.add(b, mat, smooth=False)


def ring_ledge(part, cx, cy, z, r, th=0.14, out=0.15, seg=14, thr=None):
    mat = TERRA_D if is_painted(z, thr) else SHADE
    b = bm_lathe([(r - 0.02, z - th / 2), (r + out, z - th / 2), (r + out, z + th / 2), (r - 0.02, z + th / 2)], seg=seg, center=(cx, cy, 0), cap_top=False, cap_bottom=False)
    part.add(b, mat, smooth=False)


def opening(part, cx, cy, r, ang, z, w, h, thr=None, seed=0.0, drawn_only=False, frame=True):
    """Arched door/window on a drum of radius r at angle ang (deg). Dark inset + ink arch line.
    drawn_only: just the ink outline (a door that is only drawn)."""
    a = math.radians(ang)
    pos = V((cx + math.cos(a) * (r + 0.01), cy + math.sin(a) * (r + 0.01), z))
    if not drawn_only:
        dark = TERRA_D if is_painted(z + h, thr) else 'M_StoneDark'
        part.add(arch_panel(pos, ang, w, h, depth=0.08), 'M_StoneDark' if not is_painted(z + h, thr) else INK, smooth=False)
        if frame and is_painted(z + h, thr):
            fr = arch_panel(pos - V((math.cos(a), math.sin(a), 0)) * 0.03, ang, w + 0.16, h + 0.08, depth=0.04)
            part.add(fr, TERRA_D, smooth=False)
    part.add(arch_outline(pos, ang, w, h, r=0.022, grow=0.12, seed=seed, out=0.07), INK, smooth=False)


def drips(part, cx, cy, r, thr, n=7, seed=0.0, a0=-170, a1=10):
    rnd = random.Random(int(seed * 10) + 2)
    for k in range(n):
        a = math.radians(a0 + (a1 - a0) * k / max(1, n - 1) + rnd.uniform(-8, 8))
        z = thr + rnd.uniform(-0.2, 0.3)
        x = cx + math.cos(a) * (r + 0.03)
        y = cy + math.sin(a) * (r + 0.03)
        ln = rnd.uniform(0.3, 0.9)
        part.add(bm_blade([V((x, y, z)), V((x, y, z - ln * 0.6)), V((x, y, z - ln))], [0.07, 0.05, 0.012], thick=0.02,
                          up=(math.cos(a), math.sin(a), 0)), TERRA, smooth=False)


def tower_lines(part, cx, cy, r, z0, z1, angs, seed=0.0, lean=0.0):
    """vertical ink contour hints + a top rim line"""
    for k, ang in enumerate(angs):
        a = math.radians(ang)
        p0 = V((cx + math.cos(a) * (r + 0.05), cy + math.sin(a) * (r + 0.05), z0 + 0.05))
        p1 = V((cx + math.cos(a) * (r + 0.05) + lean * (z1 - z0), cy + math.sin(a) * (r + 0.05), z1))
        part.add(ink_poly(wobble_line(p0, p1, 4, 0.03, seed + k), 0.022, overshoot=0.12, seed=seed + k), INK, smooth=False)


def tower_hatch(part, cx, cy, r, z0, z1, a0=20, a1=110, n=14, seed=0.0, lean=0.0):
    rnd = random.Random(int(seed * 10) + 1)
    out = []
    for i in range(n):
        a = math.radians(a0 + (a1 - a0) * i / n)
        za = z0 + rnd.uniform(0.0, 0.3) * (z1 - z0)
        zb = za + rnd.uniform(0.35, 0.7) * (z1 - z0)
        da = math.radians(10)
        pts = []
        for t in (0, 0.5, 1):
            aa = a + da * t
            z = za + (zb - za) * t
            pts.append(V((cx + math.cos(aa) * (r + 0.06) + lean * (z - z0), cy + math.sin(aa) * (r + 0.06), z)))
        out.append(stroke(pts, 0.018, seg=3))
    part.add(merge(out), HATCH, smooth=False)


def ground_base(part, cx, cy, r, seed=0.0):
    """small irregular plinth ring (unpainted) so the tower sits in the paper ground"""
    ol = jag_outline(r * 1.12, r * 1.12, 10, seed, 0.06, cx, cy)
    b = bm_prism(ol, -0.1, 0.18, axis='Z')
    tri_ngons(b)
    part.add(b, PAPER, smooth=False, face_mat=lambda c, n: SHADE if n.z < 0.5 else None)


# ===================================================================== houses (10/23 rework: unfinished in FORM)
# Each house = 'House' (built paper/painted shell with thickness; gets the collider) + 'Lines' (ink, pencil wire,
# torn-edge hatching, guides, smudges; unlit, no collider). Completion grows toward the plaza:
# House_1 (outskirts, ~20 % built) < House_2 (~45 %) < House_3 (~70 %) < House_4 (~95 %) < Tower_Dome (100 %).
import ouat_craft as CR

BACK, PENCIL, SMUDGE, FAINT = 'M_PaperBack', 'M_Pencil', 'M_Smudge', 'M_SketchLine'


class HB:
    def __init__(self, name):
        self.A = Asset(name)
        self.S = Part('House')
        self.Ln = Part('Lines')

    def solid(self, b, mat=PAPER, smooth=True, fm=None):
        if b is not None and len(b.faces):
            self.S.add(b, mat, smooth=smooth, face_mat=fm)

    def ink(self, b, mat=INK):
        if b is not None and len(b.verts):
            self.Ln.add(b, mat, smooth=False)

    def form(self, b, field, mat=PAPER, paint=None, thick=0.07, zig=0.05, seed=0.0, hatch=True, hatch_kw=None, smooth=True, torn=True, back_near=None):
        """field(p) > 0 = built. The torn edge follows the zero contour."""
        full = CR.copy(b)
        res = CR.cut_field(b, field, zig=zig, seed=seed)
        if len(res.built.faces):
            self.solid(res.built, mat, smooth, paint)
            back, rim = CR.shell_parts(res.built, thick, near=back_near, torn=res.torn)
            self.solid(back, BACK, False)
            self.solid(rim, 'M_TornEdge', False)
        if torn:
            self.ink(CR.torn_ink(res, 0.02, seed))
        if hatch:
            self.ink(CR.torn_hatch(res, seed=seed, **(hatch_kw or {})), PENCIL)
        return full, res

    def finish(self, size, note, lean=0.0):
        if lean:
            for p in (self.S, self.Ln):
                for pc in p.pieces:
                    deform(pc[0], lambda c: V((c.x + lean * max(0.0, c.z), c.y, c.z)))
        self.A.part(self.S, pivot=(0, 0, 0))
        self.A.part(self.Ln, pivot=(0, 0, 0))
        self.A.root['ouat_size'] = size
        self.A.meta['note'] = note
        return self.A


def plinth(H, cx, cy, r, seed, h=0.24):
    ol = jag_outline(r, r, 12, seed, 0.06, cx, cy)
    b = bm_prism(ol, -0.1, h, axis='Z')
    tri_ngons(b)
    H.solid(b, PAPER, False, lambda c, n: SHADE if n.z < 0.5 else None)
    H.ink(CR.line([V((x, y, h + 0.01)) for x, y in ol[:7]], 0.016, over=0.1, seed=seed))


def drum_r(z, z0, z1, r0, r1):
    return r0 + (r1 - r0) * (z - z0) / max(1e-6, z1 - z0)


def drum_hole(cx, cy, r, ang, w, h, z, lift=0.012):
    pts = CR.on_drum([(x, z + y) for x, y in CR.arch2d(w, h, 7)], cx, cy, r, ang, lift)
    b = bmesh.new()
    b.faces.new([b.verts.new(p) for p in pts])
    tri_ngons(b)
    CR.orient_out(b, (cx, cy))
    return b


def drum_window(H, cx, cy, r, ang, w, h, z, seed, cut=True, glow=False, frame=None, sill=True):
    """cut = real dark opening (+ ink arch + sill); otherwise only sketched on the wall."""
    f = lambda pts: CR.on_drum(pts, cx, cy, r, ang, 0.03)
    if cut:
        if glow:
            H.solid(drum_hole(cx, cy, r, ang, w, h, z), 'M_LampGlow', False)
        else:
            H.ink(drum_hole(cx, cy, r, ang, w, h, z), INK)
        if glow:
            # mullion cross in front of the glow
            H.ink(CR.line(f([(0, z + 0.05), (0, z + h - 0.05)]), 0.012))
            H.ink(CR.line(f([(-w / 2, z + h * 0.5), (w / 2, z + h * 0.5)]), 0.012))
        H.ink(CR.line(f([(x * 1.08, z + y * 1.04) for x, y in CR.arch2d(w, h, 7)]), 0.018, over=0.05, seed=seed, amp=0.004))
        if frame:
            fr = drum_hole(cx, cy, r, ang, w + 0.16, h + 0.1, z - 0.05, lift=0.006)
            H.solid(fr, frame, False)
        if sill:
            a = math.radians(ang)
            sb = bbox((cx + math.cos(a) * (r + 0.05), cy + math.sin(a) * (r + 0.05), z - 0.04), (w + 0.2, 0.12, 0.07), 0.01)
            rot(sb, 'Z', ang - 90, (cx + math.cos(a) * (r + 0.05), cy + math.sin(a) * (r + 0.05), z))
            H.solid(sb, frame or SHADE, False)
    else:
        H.ink(CR.sketched_window(f, w, h, z, seed=seed, r=0.014))


def drum_wire(H, cx, cy, z0, z1, r0, r1, unbuilt, rings=(), merid=(), seed=0.0, r=0.009, mat=PENCIL, over=0.08):
    for k, z in enumerate(rings):
        rr = drum_r(z, z0, z1, r0, r1)
        H.ink(CR.clipped_lines(CR.ring_pts(cx, cy, z, rr, 20, lift=0.015), unbuilt, r, over, seed + k, 0.006), mat)
    for k, a in enumerate(merid):
        ar = math.radians(a)
        pts = [V((cx + math.cos(ar) * (drum_r(z, z0, z1, r0, r1) + 0.015), cy + math.sin(ar) * (drum_r(z, z0, z1, r0, r1) + 0.015), z))
               for z in [z0 + (z1 - z0) * i / 8 for i in range(9)]]
        H.ink(CR.clipped_lines(pts, unbuilt, r, over * 1.6, seed + 20 + k, 0.006), mat)


def dome_pts(cx, cy, z0, r, hk, ang, n=6, lift=0.015):
    a = math.radians(ang)
    return [V((cx + math.cos(a) * (r + lift) * math.cos(t), cy + math.sin(a) * (r + lift) * math.cos(t), z0 + (r + lift) * hk * math.sin(t)))
            for t in [math.pi / 2 * i / n for i in range(n + 1)]]


def dome_wire(H, cx, cy, z0, r, hk, unbuilt=lambda p: True, merid=range(0, 360, 40), lats=(0.35, 0.7), seed=0.0, rr=0.009, mat=PENCIL):
    for k, a in enumerate(merid):
        H.ink(CR.clipped_lines(dome_pts(cx, cy, z0, r, hk, a), unbuilt, rr, 0.12, seed + k, 0.006), mat)
    for k, t in enumerate(lats):
        ang = t * math.pi / 2
        H.ink(CR.clipped_lines(CR.ring_pts(cx, cy, z0 + r * hk * math.sin(ang), r * math.cos(ang), 18, lift=0.015), unbuilt, rr, 0.1, seed + 40 + k), mat)


def chimney_built(H, x, y, z0, h, r, mat=PAPER, cap=SHADE, tilt=(0, 0)):
    top = V((x + tilt[0], y + tilt[1], z0 + h))
    H.solid(bm_tube([V((x, y, z0)), V((x, y, z0)).lerp(top, 0.5), top], [r, r * 0.95, r * 0.9], seg=8), mat, True)
    H.solid(bm_cyl(top - V((0, 0, 0.02)), top + V((0, 0, 0.18)), r * 1.4, r * 1.32, seg=8), cap, False)
    H.ink(bm_cyl(top + V((0, 0, 0.18)), top + V((0, 0, 0.19)), r * 0.9, seg=8))
    H.ink(CR.line([V((x + r * 0.95, y - r * 0.3, z0)), top + V((r * 0.92, -r * 0.3, 0))], 0.012, over=0.05))


def chimney_drawn(H, x, y, z0, h, r, seed=0.0, tilt=(0, 0)):
    top = V((x + tilt[0], y + tilt[1], z0 + h))
    for k, a in enumerate((-60, 30, 120, 210)):
        d = V((math.cos(math.radians(a)) * r, math.sin(math.radians(a)) * r, 0))
        H.ink(CR.line([V((x, y, z0)) + d, top + d], 0.008, over=0.12, seed=seed + k), PENCIL)
    H.ink(CR.ellipse(top, r * 1.35, r * 1.35, 0.0, turns=1.1, n=14, r=0.009, seed=seed), PENCIL)
    H.ink(CR.ellipse(top, r * 1.35, r * 1.35, 0.18, turns=1.05, n=14, r=0.007, seed=seed + 1), PENCIL)


def merlon_ring(H, cx, cy, z, r, n, built_fn, mat_fn, w=0.24, h=0.34, seed=0.0):
    for i in range(n):
        a = 2 * math.pi * i / n
        p = V((cx + math.cos(a) * r, cy + math.sin(a) * r, z + h / 2))
        if built_fn(p):
            b = bbox((0, 0, 0), (w, 0.22, h), 0.02)
            rot(b, 'Z', math.degrees(a) + 90)
            move(b, p)
            H.solid(b, mat_fn(p), False)
        else:
            H.ink(CR.box_wire(p, (w, 0.22, h), 0.007, 0.06, seed + i, math.degrees(a) + 90, skip=(1, 5, 9)), PENCIL)


def angdist(a, b):
    return abs((a - b + math.pi) % (2 * math.pi) - math.pi)


# --------------------------------------------------------------------- House_1 (outskirts, ~20 %)
def build_house_1():
    H = HB('House_1')
    r0, r1, zt = 1.7, 1.55, 3.0
    face = math.radians(-125)

    def hb(c):
        a = math.atan2(c.y, c.x)
        k = max(0.0, math.cos(angdist(a, face))) ** 1.4
        return 0.35 + 1.95 * k + nval(c * V((1, 1, 0.2)), 2.4, 3) * 0.28 + nval(c, 6.5, 4) * 0.08
    fld = lambda c: hb(c) - c.z
    unbuilt = lambda p: fld(p) < 0.02
    plinth(H, 0, 0, r0 * 1.13, 1)
    b = CR.drum_grid(0, 0, 0.0, zt, r0, r1, seg=18, step=0.25)
    CR.orient_out(b, (0, 0))
    H.form(b, fld, seed=1, hatch_kw=dict(length=(0.3, 0.95), spacing=0.12))
    drum_wire(H, 0, 0, 0.0, zt, r0, r1, unbuilt, rings=(1.6,), merid=(-160, -95, -40, 20, 70, 115, 165), seed=2)
    H.ink(CR.ellipse((0, 0, 0), r1 + 0.02, r1 + 0.02, zt, turns=1.12, n=30, r=0.012, seed=3), INK)       # planned top rim (ink)
    H.ink(CR.ellipse((0, 0, 0), r1 + 0.16, r1 + 0.14, zt + 0.12, turns=1.05, n=30, r=0.008, seed=4), PENCIL)
    # dome: only drawn (meridians + latitudes) + an erased first attempt
    dome_wire(H, 0, 0, zt + 0.12, r1 * 0.95, 0.85, merid=range(-160, 200, 36), seed=5)
    H.ink(CR.arc((0, 0, zt + 0.1), r1 * 1.15, 200, 340, z=0.0, n=14, r=0.007, plane='XZ', seed=6), FAINT)
    H.ink(CR.smudge(V((-0.2, -0.6, zt + 1.05)), V((0.1, -1, 0.15)), 1.3, 0.55, seed=7), SMUDGE)
    # front: the ground door is only drawn; a real tiny door sits up in the built wall
    drum_window(H, 0, 0, r0 - 0.03, -100, 0.95, 1.65, 0.24, seed=8, cut=False)
    drum_window(H, 0, 0, drum_r(1.35, 0, zt, r0, r1), -138, 0.36, 0.55, 1.35, seed=9, cut=True, sill=True)
    chimney_drawn(H, 0.55, 0.45, zt + 0.55, 1.2, 0.17, seed=10, tilt=(0.25, 0.05))
    # scaffold guides behind + long plumb / horizon construction lines
    H.ink(CR.scaffold([V((math.cos(math.radians(a)) * 2.15, math.sin(math.radians(a)) * 2.15, 0)) for a in (10, 55, 100)], 4.3, 0.009, seed=11), PENCIL)
    H.ink(CR.guides([((-r0 - 0.02, -0.2, -0.1), (-r1 - 0.02, -0.2, zt + 1.9)), ((r0 + 0.02, -0.25, -0.1), (r1 + 0.02, -0.25, zt + 1.6)),
                     ((-2.6, -0.3, zt), (2.6, -0.3, zt))], 0.006, 0.4, seed=12), FAINT)
    return H.finish(5.0, 'Outskirts (~20 % built). Paper drum built only up to a torn edge (0.4 m at the back, ~2.3 m front-left); '
                         'the rest of the drum, the dome and the chimney exist as pencil construction. Ground door only drawn, real tiny door 1.35 m up. '
                         'House = solid shell (collider), Lines = ink/pencil (unlit, no collider).', lean=0.05)


# --------------------------------------------------------------------- House_2 (~45 %)
def build_house_2():
    H = HB('House_2')
    thr = 3.25
    r0, r1, z1 = 2.0, 1.9, 2.6
    plinth(H, 0, 0, 2.2, 11)
    back = math.radians(40)

    def fld_lo(c):
        a = math.atan2(c.y, c.x)
        return max(1.25 + nval(c, 2.0, 12) * 0.25 + nval(c, 7.0, 3) * 0.06 - c.z, (angdist(a, back) - 0.95 - nval(c, 1.3, 13) * 0.25) * 2.0)
    keep_lo = lambda c, n: fld_lo(c) > 0
    paint = CR.paint_ragged(thr, amp=0.3, seed=14, mat=TERRA)
    b = CR.drum_grid(0, 0, 0.0, z1, r0, r1, seg=20, step=0.3)
    CR.orient_out(b, (0, 0))
    H.form(b, fld_lo, seed=15, paint=paint)
    drum_wire(H, 0, 0, 0.0, z1, r0, r1, lambda p: not keep_lo(p, None), rings=(1.8, z1), merid=range(10, 90, 20), seed=16)
    # ledge: built at the front, drawn at the back
    led = bm_lathe([(r1 - 0.02, z1 - 0.07), (r1 + 0.18, z1 - 0.07), (r1 + 0.18, z1 + 0.07), (r1 - 0.02, z1 + 0.07)], seg=22, cap_top=False, cap_bottom=False)
    ledge_keep = lambda c, n: angdist(math.atan2(c.y, c.x), back) > 1.25
    full = CR.copy(led)
    CR.cut(led, ledge_keep, rag=0.0)
    H.solid(led, SHADE, False)
    H.ink(CR.clipped_lines(CR.ring_pts(0, 0, z1, r1 + 0.19, 44), lambda p: not ledge_keep(p, None), 0.008, 0.12, 17), PENCIL)
    # upper drum: a built wedge facing front-left, the rest drawn
    cx, cy, ru0, ru1, z2 = 0.2, 0.15, 1.45, 1.36, 4.6
    wedge = math.radians(-120)

    def fld_up(c):
        a = math.atan2(c.y - cy, c.x - cx)
        return 1.3 + nval(c, 1.6, 18) * 0.35 + nval(c, 6.0, 5) * 0.05 - max(0.0, c.z - 3.8) * 0.35 - angdist(a, wedge)
    keep_up = lambda c, n: fld_up(c) > 0
    b2 = CR.drum_grid(cx, cy, z1, z2, ru0, ru1, seg=18, step=0.3)
    CR.orient_out(b2, (cx, cy))
    H.form(b2, fld_up, seed=19, paint=paint, hatch_kw=dict(up_only=False, slant=55, length=(0.2, 0.6), spacing=0.14))
    drum_wire(H, cx, cy, z1, z2, ru0, ru1, lambda p: not keep_up(p, None), rings=(3.6, z2), merid=range(-20, 180, 40), seed=20)
    merlon_ring(H, cx, cy, z2, ru1 - 0.05, 10, lambda p: keep_up(p, None), lambda p: TERRA if p.z > thr else PAPER, seed=21)
    # roof drawn only as its outline (cone)
    apex = V((cx + 0.05, cy, z2 + 1.55))
    for k, a in enumerate(range(-150, 210, 45)):
        ar = math.radians(a)
        H.ink(CR.line([V((cx + math.cos(ar) * (ru1 + 0.15), cy + math.sin(ar) * (ru1 + 0.15), z2 + 0.3)), apex], 0.009 if k % 2 else 0.013, over=0.15, seed=22 + k), PENCIL if k % 2 else INK)
    H.ink(CR.ellipse((cx, cy, 0), ru1 + 0.15, ru1 + 0.15, z2 + 0.3, turns=1.1, n=30, r=0.012, seed=23), INK)
    H.ink(CR.smudge(apex + V((0.3, -0.6, -0.6)), V((0.2, -1, 0.3)), 0.9, 0.5, seed=24), SMUDGE)
    # openings: a door too small for anyone (cut), a cut window up in the painted wedge, two sketched windows below
    drum_window(H, 0, 0, r0 - 0.02, -95, 0.55, 0.85, 0.24, seed=25, cut=True)
    drum_window(H, cx, cy, ru0 - 0.05, -115, 0.42, 0.68, 3.35, seed=26, cut=True, frame=TERRA_D)
    drum_window(H, 0, 0, drum_r(1.0, 0, z1, r0, r1), -40, 0.45, 0.7, 1.0, seed=27, cut=False)
    drum_window(H, 0, 0, drum_r(1.1, 0, z1, r0, r1), -150, 0.45, 0.7, 1.1, seed=28, cut=False)
    rnd = random.Random(29)
    pts = []
    for k in range(6):
        a = wedge + rnd.uniform(-0.9, 0.9)
        z = thr - 0.15 + rnd.uniform(-0.1, 0.15)
        rr = drum_r(z, z1, z2, ru0, ru1) + 0.02
        pts.append((V((cx + math.cos(a) * rr, cy + math.sin(a) * rr, z)), V((math.cos(a), math.sin(a), 0))))
    H.solid(CR.drips(pts, TERRA, rnd), TERRA, False)
    chimney_built(H, -0.45, 0.75, 4.2, 1.3, 0.16, PAPER, SHADE)
    chimney_drawn(H, 0.75, 0.6, 4.4, 1.1, 0.16, seed=30)
    H.ink(CR.guides([((-2.4, -0.2, z1), (2.5, -0.2, z1)), ((cx - ru1, cy - 0.3, z1), (cx - ru1, cy - 0.3, z2 + 1.4))], 0.006, 0.45, seed=31), FAINT)
    return H.finish(6.1, '~45 % built. Lower drum built (torn down to 1.2 m at the back), upper drum only a painted wedge facing front-left, '
                         'the rest pencil. Cone roof only as an outline. Ground door 0.55 x 0.85 m (too small for anyone).')


# --------------------------------------------------------------------- House_3 (~70 %): hall + corner tower
def build_house_3():
    H = HB('House_3')
    thr = 1.5
    W, D, Hh = 3.6, 3.0, 2.9
    corner = V((W / 2, -D / 2, Hh))
    paint = CR.paint_ragged(thr, amp=0.3, seed=31, mat=TERRA)

    fld_hall = lambda c: (c - corner).length - 1.55 - nval(c, 1.8, 32) * 0.35 - nval(c, 6.0, 2) * 0.06
    keep_hall = lambda c, n: fld_hall(c) > 0
    plinth_b = bbox((0, 0, 0.06), (W + 0.3, D + 0.3, 0.2), 0.03)
    H.solid(plinth_b, SHADE, False)
    b = CR.grid_box((0, 0, Hh / 2 + 0.1), (W, D, Hh - 0.2), step=0.36)
    full, res = H.form(b, fld_hall, seed=33, paint=paint, smooth=False, back_near=1.2, hatch_kw=dict(up_only=False, length=(0.2, 0.7)))
    H.ink(CR.wire_drawn(full, keep_hall, r=0.012, over=0.2, seed=34), INK)
    # rubble of the missing corner
    for k, (x, y) in enumerate(((2.0, -1.95), (2.4, -1.25), (1.45, -2.15), (2.15, -2.35))):
        rb = bm_sphere((x, y, 0.1), (0.24, 0.2, 0.14), seg=5, rings=3)
        jitter(rb, 0.05, 3, 35 + k)
        H.solid(rb, PAPER, False)
    # pitched roof: drawn only as its outline; a strip of tiles built at the left end
    rz, ry = Hh + 1.25, 0.0
    e0, e1 = Hh - 0.05, -D / 2 - 0.25
    for x in (-W / 2 - 0.2, W / 2 + 0.2):
        H.ink(CR.line([V((x, -D / 2 - 0.25, Hh - 0.05)), V((x, ry, rz)), V((x, D / 2 + 0.25, Hh - 0.05))], 0.018, over=0.18, seed=36 + x), INK)
    H.ink(CR.line([V((-W / 2 - 0.2, ry, rz)), V((W / 2 + 0.2, ry, rz))], 0.016, over=0.35, seed=38), INK)
    H.ink(CR.line([V((-W / 2 - 0.2, -D / 2 - 0.25, Hh - 0.05)), V((W / 2 + 0.2, -D / 2 - 0.25, Hh - 0.05))], 0.01, over=0.3, seed=39), PENCIL)
    for k in range(9):
        x = -W / 2 + 0.25 + k * 0.42
        H.ink(CR.line([V((x, -D / 2 - 0.2, Hh)), V((x + 0.05, ry - 0.05, rz - 0.04))], 0.006, over=0.0, seed=40 + k), PENCIL)
    tiles = bmesh.new()
    slab = bm_prism([(-D / 2 - 0.25, Hh - 0.05), (ry, rz), (D / 2 + 0.25, Hh - 0.05), (D / 2 + 0.25, Hh + 0.07), (ry, rz + 0.12), (-D / 2 - 0.25, Hh + 0.07)],
                    -W / 2 - 0.2, -W / 2 + 0.75, axis='X')
    tri_ngons(slab)
    H.solid(slab, TERRA_D, False)
    for k in range(4):
        z = Hh + 0.2 + k * 0.27
        y = -D / 2 - 0.25 + (z - Hh) / (rz - Hh) * (D / 2 + 0.25)
        H.ink(CR.line([V((-W / 2 - 0.22, y - 0.03, z + 0.06)), V((-W / 2 + 0.77, y - 0.03, z + 0.06))], 0.01, over=0.02, seed=50 + k), INK)
    # front openings: arched door (cut), one window cut, one only sketched
    fy = -D / 2
    front = lambda pts, off=0.025: CR.on_wall(pts, (0, fy, 0), (1, 0, 0), (0, -1, 0), off)
    door = bmesh.new()
    door.faces.new([door.verts.new(p) for p in front([(x - 0.7, y + 0.1) for x, y in CR.arch2d(1.0, 1.8, 7)], 0.012)])
    tri_ngons(door)
    H.ink(door, INK)
    H.ink(CR.line(front([(x * 1.1 - 0.7, y * 1.05 + 0.08) for x, y in CR.arch2d(1.0, 1.8, 7)], 0.03), 0.018, over=0.05, seed=55), INK)
    win = bmesh.new()
    win.faces.new([win.verts.new(p) for p in front([(x - 1.45, y + 1.7) for x, y in CR.arch2d(0.42, 0.65, 7)], 0.012)])
    tri_ngons(win)
    H.ink(win, INK)
    H.solid(bbox((-1.45, fy - 0.05, 1.67), (0.6, 0.12, 0.07), 0.01), TERRA_D, False)
    H.ink(CR.sketched_window(lambda pts: front([(x + 0.25, z) for x, z in pts], 0.03), 0.42, 0.65, 1.7, seed=56, r=0.013))
    # corner drum tower (back-left) fully built, dome 2/3 built
    tx, ty, tr0, tr1, tz = -W / 2 + 0.2, D / 2 - 0.2, 1.05, 0.95, 5.0
    bt = CR.drum_grid(tx, ty, 0.0, tz, tr0, tr1, seg=14, step=0.5, cap_top=False)
    CR.orient_out(bt, (tx, ty))
    H.solid(bt, PAPER, True, paint)
    led = bm_lathe([(tr1 - 0.02, tz - 0.07), (tr1 + 0.16, tz - 0.07), (tr1 + 0.16, tz + 0.07), (tr1 - 0.02, tz + 0.07)], seg=16, center=(tx, ty, 0), cap_top=False, cap_bottom=False)
    H.solid(led, TERRA_D, False)
    dm_fld = lambda c: angdist(math.atan2(c.y - ty, c.x - tx), math.radians(20)) - 1.0 - nval(c, 2.0, 57) * 0.4
    dm_keep = lambda c, n: dm_fld(c) > 0
    bd = CR.dome_grid(tx, ty, tz, tr1, hk=1.0, seg=14, rings=5)
    CR.orient_out(bd, center=(tx, ty, tz))
    H.form(bd, dm_fld, seed=58, paint=lambda c, n: TERRA, hatch=False)
    dome_wire(H, tx, ty, tz, tr1, 1.0, lambda p: not dm_keep(p, None), merid=range(-60, 100, 22), seed=59)
    H.solid(bm_tube([V((tx, ty, tz + 0.9)), V((tx, ty, tz + 1.35))], [0.06, 0.01], seg=6), TERRA_D)
    drum_window(H, tx, ty, drum_r(3.4, 0, tz, tr0, tr1), -120, 0.36, 0.6, 3.4, seed=60, cut=True, frame=TERRA_D)
    drum_window(H, tx, ty, drum_r(2.2, 0, tz, tr0, tr1), -175, 0.34, 0.55, 2.2, seed=61, cut=False)
    chimney_built(H, 0.9, 1.0, Hh + 0.1, 1.1, 0.16, TERRA, TERRA_D)
    H.ink(CR.smudge(corner + V((-0.3, -0.35, 0.4)), V((0.3, -1, 0.2)), 1.2, 0.7, seed=62), SMUDGE)
    H.ink(CR.guides([((W / 2 + 0.02, fy - 0.02, -0.1), (W / 2 + 0.02, fy - 0.02, Hh + 1.6)), ((-W / 2 - 0.6, fy, Hh), (W / 2 + 0.9, fy, Hh))], 0.006, 0.4, seed=63), FAINT)
    return H.finish(6.4, '~70 % built. Hall walls painted above ~1.5 m; the front-right top corner was never built (pencil box edges, torn paper, '
                         'rubble). Pitched roof drawn only as its outline with one strip of tiles built at the left. Corner tower built, dome 2/3.')


# --------------------------------------------------------------------- House_4 (~95 %, next to the plaza)
def build_house_4():
    H = HB('House_4')
    thr = 0.55
    paint = CR.paint_ragged(thr, amp=0.25, seed=51, mat=TERRA)
    plinth(H, 0, 0, 1.95, 51)
    b = CR.drum_grid(0, 0, 0.0, 4.4, 1.75, 1.62, seg=20, step=0.4, cap_top=True)
    CR.orient_out(b, (0, 0))
    H.solid(b, PAPER, True, paint)
    # balcony ledge: built 2/3, the last third only drawn (with its railing)
    led = bm_lathe([(1.64, 2.93), (1.95, 2.93), (1.95, 3.07), (1.64, 3.07)], seg=24, cap_top=False, cap_bottom=False)
    lk = lambda c, n: angdist(math.atan2(c.y, c.x), math.radians(30)) > 1.0
    CR.cut(led, lk, rag=0.0)
    H.solid(led, TERRA_D, False)
    H.ink(CR.clipped_lines(CR.ring_pts(0, 0, 3.0, 1.96, 48), lambda p: not lk(p, None), 0.009, 0.15, 52), PENCIL)
    for k, a in enumerate(range(-170, 190, 20)):
        ar = math.radians(a)
        p0 = V((math.cos(ar) * 1.88, math.sin(ar) * 1.88, 3.07))
        if lk(p0, None):
            H.solid(bm_cyl(p0, p0 + V((0, 0, 0.42)), 0.025, seg=5), TERRA_D, False)
        else:
            H.ink(CR.line([p0, p0 + V((0, 0, 0.45))], 0.007, over=0.06, seed=53 + k), PENCIL)
    H.solid(bm_tube([V((math.cos(math.radians(a)) * 1.88, math.sin(math.radians(a)) * 1.88, 3.5)) for a in range(-150, 31, 15)], 0.03, seg=5), TERRA_D)
    H.ink(CR.clipped_lines(CR.ring_pts(0, 0, 3.5, 1.88, 40), lambda p: not lk(p, None), 0.008, 0.1, 54), PENCIL)
    led2 = bm_lathe([(1.6, 4.33), (1.78, 4.33), (1.78, 4.47), (1.6, 4.47)], seg=20, cap_top=False, cap_bottom=False)
    H.solid(led2, TERRA_D, False)
    b2 = CR.drum_grid(0, 0, 4.4, 5.7, 1.3, 1.2, seg=18, step=0.45, cap_top=True)
    CR.orient_out(b2, (0, 0))
    H.solid(b2, TERRA, True)
    merlon_ring(H, 0, 0, 5.7, 1.18, 10, lambda p: True, lambda p: TERRA, w=0.2, h=0.26)
    bd = CR.dome_grid(0, 0, 5.7, 1.0, hk=0.95, seg=18, rings=6)
    CR.orient_out(bd, center=(0, 0, 5.7))
    H.solid(bd, TERRA, True)
    H.solid(bm_tube([V((0, 0, 6.6)), V((0, 0, 7.05))], [0.06, 0.01], seg=6), TERRA_D)
    drum_window(H, 0, 0, 1.74, -90, 0.95, 1.8, 0.24, seed=55, cut=True, frame=TERRA_D, sill=False)
    for k, (ang, z, cutw) in enumerate(((-40, 1.7, True), (-140, 1.9, True), (-90, 3.55, True), (-30, 4.75, True), (-150, 4.75, False))):
        rr = drum_r(z, 0, 4.4, 1.75, 1.62) if z < 4.4 else drum_r(z, 4.4, 5.7, 1.3, 1.2)
        drum_window(H, 0, 0, rr, ang, 0.4, 0.7, z, seed=56 + k, cut=cutw, frame=TERRA_D, glow=(k == 2))
    chimney_built(H, 0.75, 0.55, 5.5, 1.3, 0.17, TERRA, TERRA_D)
    chimney_built(H, -0.6, 0.7, 5.5, 0.9, 0.15, TERRA, TERRA_D, tilt=(-0.12, 0.04))
    chimney_drawn(H, 0.1, -0.75, 5.7, 0.6, 0.12, seed=61)
    rnd = random.Random(62)
    pts = [(V((math.cos(a) * 1.77, math.sin(a) * 1.77, thr + rnd.uniform(0.0, 0.25))), V((math.cos(a), math.sin(a), 0))) for a in [math.radians(-170 + 30 * k) for k in range(7)]]
    H.solid(CR.drips(pts, TERRA, rnd, ln=(0.12, 0.4)), TERRA, False)
    for k, a in enumerate((-125, -55)):
        ar = math.radians(a)
        H.ink(CR.line([V((math.cos(ar) * 1.78, math.sin(ar) * 1.78, 0.25)), V((math.cos(ar) * 1.65, math.sin(ar) * 1.65, 4.4))], 0.016, over=0.1, seed=63 + k), INK)
    return H.finish(7.1, '~95 % built, next to the plaza: painted except the ragged foot. Last third of the balcony + railing, one chimney and '
                         'one upper window are still only drawn.')


# --------------------------------------------------------------------- Tower_Dome (plaza, finished)
def build_tower_dome():
    H = HB('Tower_Dome')
    plinth(H, 0, 0, 3.3, 71, h=0.3)
    b = CR.drum_grid(0, 0, 0.0, 3.6, 3.0, 2.9, seg=24, step=0.6, cap_top=True)
    CR.orient_out(b, (0, 0))
    H.solid(b, TERRA, True)
    for z, r, o in ((0.32, 3.0, 0.12), (3.6, 2.9, 0.3), (6.2, 2.1, 0.18)):
        H.solid(bm_lathe([(r - 0.02, z - 0.08), (r + o, z - 0.08), (r + o, z + 0.08), (r - 0.02, z + 0.08)], seg=24, cap_top=False, cap_bottom=False), TERRA_D, False)
    merlon_ring(H, 0, 0, 3.7, 2.85, 16, lambda p: True, lambda p: TERRA)
    for k in range(6):
        ang = -90 + 60 * k
        if k == 0:
            drum_window(H, 0, 0, 2.98, ang, 1.15, 2.25, 0.32, seed=72, cut=True, frame=TERRA_D, sill=False)
        else:
            drum_window(H, 0, 0, 2.95, ang, 0.8, 1.45, 1.0, seed=72 + k, cut=True, frame=TERRA_D, glow=(k in (1, 4)))
    b2 = CR.drum_grid(0, 0, 3.6, 6.2, 2.2, 2.1, seg=20, step=0.65, cap_top=True)
    CR.orient_out(b2, (0, 0))
    H.solid(b2, TERRA, True)
    for k in range(5):
        drum_window(H, 0, 0, 2.15, -90 + 72 * k + 36, 0.45, 0.85, 4.4, seed=79 + k, cut=True, frame=TERRA_D, glow=(k % 2 == 0))
    bd = CR.dome_grid(0, 0, 6.2, 2.1, hk=0.9, seg=20, rings=7)
    CR.orient_out(bd, center=(0, 0, 6.2))
    H.solid(bd, TERRA, True)
    for k, a in enumerate(range(0, 360, 45)):
        H.ink(CR.line(dome_pts(0, 0, 6.2, 2.1, 0.9, a, 8, 0.02)[:-2], 0.012, over=0.0, seed=90 + k), INK)
    H.solid(bm_tube([V((0, 0, 8.05)), V((0, 0, 8.65))], [0.15, 0.02], seg=6), TERRA_D)
    H.solid(bm_sphere((0, 0, 8.1), (0.2, 0.2, 0.2), seg=8, rings=5), TERRA_D)
    chimney_built(H, 1.4, 0.8, 6.6, 1.6, 0.2, TERRA, TERRA_D)
    chimney_built(H, -1.2, 1.0, 6.7, 1.3, 0.18, TERRA, TERRA_D)
    chimney_built(H, 0.2, 1.6, 6.4, 1.9, 0.2, TERRA, TERRA_D, tilt=(0.1, 0.05))
    for k, a in enumerate((-130, -50, 150)):
        ar = math.radians(a)
        H.ink(CR.line([V((math.cos(ar) * 3.02, math.sin(ar) * 3.02, 0.4)), V((math.cos(ar) * 2.93, math.sin(ar) * 2.93, 3.5))], 0.02, over=0.06, seed=96 + k), INK)
    return H.finish(9.0, 'Big plaza tower: fully built and painted (the finished world). Some windows glow (M_LampGlow) - put warm point lights inside. '
                         'Ground arch door faces -Y (Unity +Z).')


# ===================================================================== paving lines
def hex_ring(cx, cy, r, gap_edges=(), jit=0.03, w=0.03, rnd=None, z=0.01):
    """flat ink strips for the edges of one hexagon (stone), slightly hand-drawn."""
    b = bmesh.new()
    corners = []
    for i in range(6):
        a = math.radians(60 * i + 30)
        k = 1 + (rnd.uniform(-jit, jit) if rnd else 0)
        corners.append(V((cx + math.cos(a) * r * k, cy + math.sin(a) * r * k, z)))
    for i in range(6):
        if i in gap_edges:
            continue
        p0, p1 = corners[i], corners[(i + 1) % 6]
        d = (p1 - p0)
        nrm = V((-d.y, d.x, 0)).normalized() * (w / 2)
        p0e = p0 - d * 0.04
        p1e = p1 + d * 0.04
        vs = [b.verts.new(p0e - nrm), b.verts.new(p1e - nrm), b.verts.new(p1e + nrm), b.verts.new(p0e + nrm)]
        b.faces.new(vs)
    return b


def paving(name, size=8.0, r=0.42, gap=0.07, keep=1.0, broken=0.1, fade=False, seed=0.0):
    A = Asset(name)
    p = Part('Lines')
    rnd = random.Random(int(seed * 100) + 5)
    dx = math.sqrt(3) * (r + gap)
    dy = 1.5 * (r + gap)
    rows = int(size / dy) + 1
    cols = int(size / dx) + 1
    pieces = []
    for j in range(rows):
        for i in range(cols):
            x = -size / 2 + i * dx + (dx / 2 if j % 2 else 0) + rnd.uniform(-0.04, 0.04)
            y = -size / 2 + j * dy + rnd.uniform(-0.04, 0.04)
            if abs(x) > size / 2 - r * 0.6 or abs(y) > size / 2 - r * 0.6:
                continue
            k = keep
            if fade:
                d = max(abs(x), abs(y)) / (size / 2)
                k = keep * (1.0 - 0.85 * d * d)
            if rnd.random() > k:
                continue
            gaps = tuple(e for e in range(6) if rnd.random() < broken)
            rr = r * rnd.uniform(0.85, 1.05)
            pieces.append(hex_ring(x, y, rr, gaps, rnd=rnd, w=0.032 if not fade else 0.028))
    p.add(merge(pieces), INK, smooth=False)
    A.part(p, pivot=(0, 0, 0))
    A.root['ouat_size'] = size
    A.meta['note'] = f'{size} x {size} m decal of hex stone outlines (flat M_Ink strips 1 cm above ground). Tile it; rotate 0/60/120 deg to hide repetition. Double-sided not needed (faces up).'
    return A


def build_paving_hex():
    return paving('Paving_Hex', keep=0.97, broken=0.06, seed=1)


def build_paving_hex_broken():
    return paving('Paving_HexBroken', keep=0.75, broken=0.3, fade=True, seed=2)


# ===================================================================== spires (background)
def spire(name, h, r, sides=6, seed=0.0, twin=None):
    A = Asset(name)
    p = Part('Spire')
    rnd = random.Random(int(seed * 10) + 3)

    def cone(cx, cy, hh, rr, s2):
        b = bmesh.new()
        base = []
        for i in range(sides):
            a = 2 * math.pi * i / sides + rnd.uniform(-0.15, 0.15)
            base.append(b.verts.new(V((cx + math.cos(a) * rr * rnd.uniform(0.85, 1.1), cy + math.sin(a) * rr * rnd.uniform(0.85, 1.1), -1.0))))
        mid = []
        for i in range(sides):
            c = base[i].co
            mid.append(b.verts.new(V((cx + (c.x - cx) * 0.45 + rnd.uniform(-0.2, 0.2), cy + (c.y - cy) * 0.45, hh * 0.55))))
        apex = b.verts.new(V((cx + rnd.uniform(-0.3, 0.3) * rr * 0.1, cy, hh)))
        for i in range(sides):
            i2 = (i + 1) % sides
            b.faces.new((base[i], base[i2], mid[i2], mid[i]))
            b.faces.new((mid[i], mid[i2], apex))
        bmesh.ops.recalc_face_normals(b, faces=b.faces)
        p.add(b, 'M_Spire', smooth=False)
        # pale ridge lines (drawn), only on some ridges
        for i in range(sides):
            if rnd.random() < 0.5:
                p.add(ink_poly([base[i].co + V((0, 0, 1.0)), mid[i].co, apex.co], 0.06 * max(1.0, hh / 25), overshoot=0.3, seed=seed + i), HATCH, smooth=False)
    cone(0, 0, h, r, sides)
    if twin:
        cone(twin[0], twin[1], twin[2], twin[3], sides)
    A.part(p, pivot=(0, 0, 0))
    A.root['ouat_size'] = h
    A.meta['note'] = 'Background silhouette spire (no outline material). Base sinks 1 m below ground.'
    return A


def build_spire_1():
    return spire('Spire_1', 18.0, 3.5, 5, seed=1)


def build_spire_2():
    return spire('Spire_2', 28.0, 5.0, 6, seed=2, twin=(4.5, 2.0, 16.0, 3.0))


def build_spire_3():
    return spire('Spire_3', 40.0, 7.0, 7, seed=3)


# ===================================================================== cliffs / ledges (concept style)
def cliff(name, rx, ry, bands, seed, notch=None):
    A = Asset(name)
    p = Part('Cliff')
    ol = jag_outline(rx, ry, 11, seed, 0.12)
    if notch:
        # pull some points in to make a bay
        ol = [(x * (0.65 if (x * notch[0] + y * notch[1]) > 0.6 * max(rx, ry) else 1.0),
               y * (0.65 if (x * notch[0] + y * notch[1]) > 0.6 * max(rx, ry) else 1.0)) for x, y in ol]
    cliff_part(p, ol, bands, seed=seed, ink_r=0.04, hatch_r=0.025, hatch_density=0.85)
    A.part(p, pivot=(0, 0, 0))
    A.root['ouat_size'] = 2 * max(rx, ry)
    A.meta['note'] = 'Walkable top at local 0 (root = top-surface centre). Stepped sides go down; place so tops meet the walk level.'
    return A


def build_cliff_1():
    return cliff('Cliff_1', 4.0, 3.0, [(0.0, -1.6, 1.0, (0, 0)), (-1.6, -3.4, 0.95, (0.15, 0.1)), (-3.4, -6.0, 0.88, (0.3, 0.2))], seed=1)


def build_cliff_2():
    return cliff('Cliff_2', 5.0, 3.5, [(0.0, -1.2, 1.0, (0, 0)), (-1.2, -2.0, 1.04, (-0.1, 0.05)), (-2.0, -4.5, 0.96, (0.2, 0.1)), (-4.5, -8.0, 0.86, (0.4, 0.3))], seed=2, notch=(0.0, -1.0))


def build_cliff_3():
    return cliff('Cliff_3', 3.0, 2.0, [(0.0, -2.2, 1.0, (0, 0)), (-2.2, -5.0, 0.9, (0.1, -0.1))], seed=3)


# ===================================================================== cave walls
def cave_wall(name, kind, seed):
    """Built straight (front faces -Y), then bent for the concave corner (kind 3)."""
    A = Asset(name)
    p = Part('Wall')
    W, H = 12.0, 13.0
    nx, nz = 12, 9
    rnd = random.Random(int(seed * 10) + 9)

    def depth(u, z):
        d = nval(V((u, 0, z)), 0.35, seed) * 0.9 + nval(V((u, 0, z)), 1.1, seed + 5) * 0.3
        d += 0.8 * (1 - z / H) - 0.6 * (z / H) ** 2
        if kind == 2:
            d += 1.6 * math.exp(-((u - 1.5) / 1.6) ** 2) * (0.6 + 0.4 * (1 - z / H))
        return d

    def surf(u, z, off=0.0):
        return V((u, -(depth(u, z) + off), z))

    tops = [H - rnd.uniform(0.0, 2.2) - (1.2 if i % 4 == 1 else 0.0) for i in range(nx + 1)]
    b = bmesh.new()
    grid = []
    for j in range(nz + 1):
        row = []
        for i in range(nx + 1):
            u = -W / 2 + W * i / nx
            z = tops[i] * j / nz
            row.append(b.verts.new(surf(u, z)))
        grid.append(row)
    for j in range(nz):
        for i in range(nx):
            b.faces.new((grid[j][i], grid[j][i + 1], grid[j + 1][i + 1], grid[j + 1][i]))
    bmesh.ops.recalc_face_normals(b, faces=b.faces)
    for f in b.faces:
        if f.normal.y > 0:
            f.normal_flip()
    bmesh.ops.solidify(b, geom=b.faces[:], thickness=0.6)
    pieces = [(b, PAPER, lambda c, n: SHADE if n.z < -0.25 or c.z < 2.2 else None)]
    # ink: broken strata lines
    lines = []
    for k, z in enumerate((2.4, 5.1, 8.0)):
        u0 = rnd.uniform(-W / 2, -1)
        u1 = rnd.uniform(1, W / 2)
        lines.append([surf(u0 + (u1 - u0) * t / 5, z + 0.3 * math.sin(t), 0.08) for t in range(6)])
    pieces.append((edge_lines(lines, r=0.05, overshoot=0.4, seed=seed), INK, None))
    # unfinished top edge: contour drawn in pieces + loose strokes rising past the surface
    cont = [surf(-W / 2 + W * i / nx, tops[i], 0.05) for i in range(nx + 1)]
    for a0 in range(0, nx, 4):
        pieces.append((ink_poly(cont[a0:a0 + 5], 0.05, overshoot=0.3, seed=seed + a0, amp=0.03), INK, None))
    tl = []
    for i in range(nx + 1):
        if rnd.random() < 0.35:
            continue
        u = -W / 2 + W * i / nx + rnd.uniform(-0.3, 0.3)
        zt = tops[i]
        b0 = surf(u, zt - rnd.uniform(0.8, 2.0), 0.15)
        tl.append(stroke([b0, b0 + V((rnd.uniform(-0.6, 0.6), 0, rnd.uniform(1.4, 3.2)))], 0.045, seg=3))
    pieces.append((merge(tl), INK, None))
    hl = []
    for i in range(24):
        u = rnd.uniform(-W / 2 + 0.5, W / 2 - 0.5)
        z = rnd.uniform(0.3, 6.5)
        p0 = surf(u, z, 0.12)
        hl.append(stroke([p0, surf(u + 0.6, z + 1.1, 0.12)], 0.03, seg=3))
    pieces.append((merge(hl), HATCH, None))
    if kind == 3:
        R = 2 * W / math.pi

        def bend(c):
            a = (c.x + W / 2) / W * (math.pi / 2) - math.pi / 4
            rad = R + c.y      # -y = forward = toward the centre of the bend
            return V((math.sin(a) * rad, -R + math.cos(a) * rad, c.z))
        for bm_, m, fm in pieces:
            deform(bm_, bend)
    for bm_, m, fm in pieces:
        p.add(bm_, m, smooth=False, face_mat=fm)
    A.part(p, pivot=(0, 0, 0))
    A.root['ouat_size'] = 13.0
    A.meta['note'] = {1: 'Straight 12 m segment, front faces -Y (Unity +Z = toward the village). Ragged top edge finished by loose ink strokes.',
                      2: 'Straight 12 m segment with a buttress bulge (x=+1.5).',
                      3: 'Concave corner: 90 deg arc of radius 7.6 m, centre at (0,-7.6) i.e. in front; ends at about (+-5.4, -2.2) facing the centre.'}[kind]
    return A


def build_cave_wall_1():
    return cave_wall('CaveWall_1', 1, 1.0)


def build_cave_wall_2():
    return cave_wall('CaveWall_2', 2, 2.0)


def build_cave_wall_3():
    return cave_wall('CaveWall_3', 3, 3.0)


# ===================================================================== rocks
def rock(name, rx, ry, rz, seed, seg=7):
    A = Asset(name)
    p = Part('Rock')
    b = bm_sphere((0, 0, rz * 0.6), (rx, ry, rz), seg=seg, rings=4)
    rnd = random.Random(seed)
    for v in b.verts:
        k = rnd.uniform(0.75, 1.15)
        v.co = V((v.co.x * k, v.co.y * k, v.co.z))
    jitter(b, max(rx, rz) * 0.12, 0.9 / max(rx, rz), seed)
    # flat-cut top and planar facets (paper-craft rock)
    deform(b, lambda c: V((c.x, c.y, min(max(c.z, 0.0), rz * 1.25))))
    b = L.decimate(b, 0.7)
    p.add(b, PAPER, smooth=False, face_mat=lambda c, n: SHADE if (n.x * 0.6 + n.y * 0.8) > 0.4 else None)
    lines = [[V((rx * 0.2, -ry * 1.0, rz * 1.2)), V((rx * 0.35, -ry * 0.95, rz * 0.8)), V((rx * 0.25, -ry * 0.9, rz * 0.4))]]
    p.add(edge_lines(lines, r=0.02 * max(1, rz), overshoot=0.05, seed=seed), INK, smooth=False)
    h = hatch_rect(V((rx * 0.5, ry * 0.55, 0.05)), V((-0.5, 0.8, 0)), V((0, 0, 1)), ry * 0.9, rz * 1.1, n=6, r=0.015 * max(1, rz), seed=seed, normal=V((0.6, 0.8, 0.2)), mat_off=rz * 0.2)
    if h:
        p.add(h, HATCH, smooth=False)
    A.part(p, pivot=(0, 0, 0))
    A.root['ouat_size'] = 2 * max(rx, ry, rz)
    return A


def build_rock_1():
    return rock('Rock_1', 0.7, 0.55, 0.5, 1, seg=6)


def build_rock_2():
    return rock('Rock_2', 1.4, 1.0, 1.1, 2)


def build_rock_3():
    return rock('Rock_3', 2.4, 1.8, 2.2, 3, seg=7)


# ===================================================================== pond (fish home)
def build_pond():
    A = Asset('Pond')
    R = 6.5
    rnd = random.Random(41)
    ol = jag_outline(R, R * 0.85, 22, 4, 0.08)
    s = Part('Surface')
    b = bmesh.new()
    cv = b.verts.new(V((0, 0, 0.02)))
    vs = [b.verts.new(V((x, y, 0.02))) for x, y in ol]
    for i in range(len(vs)):
        b.faces.new((cv, vs[i], vs[(i + 1) % len(vs)]))
    bmesh.ops.recalc_face_normals(b, faces=b.faces)
    for f in b.faces:
        if f.normal.z < 0:
            f.normal_flip()
    s.add(b, 'M_Pond', smooth=False)
    # faint grey ripple rings on the black water
    rings = []
    for k, rr in enumerate((1.6, 3.0, 4.4)):
        pts = [V((math.cos(a) * rr, math.sin(a) * rr * 0.85, 0.04)) for a in [k * 2.1 + 0.35 * i for i in range(8)]]
        rings.append(stroke(pts, 0.03, seg=3))
    s.add(merge(rings), HATCH, smooth=False)
    A.part(s, pivot=(0, 0, 0))
    rm = Part('Rim')
    # low paper lip + flat stones
    lip = bmesh.new()
    inner = [lip.verts.new(V((x, y, 0.0))) for x, y in ol]
    outer = [lip.verts.new(V((x * 1.12, y * 1.12, 0.12 + 0.05 * math.sin(i)))) for i, (x, y) in enumerate(ol)]
    outer2 = [lip.verts.new(V((x * 1.22, y * 1.22, 0.0))) for x, y in ol]
    n = len(ol)
    for i in range(n):
        j = (i + 1) % n
        lip.faces.new((inner[i], inner[j], outer[j], outer[i]))
        lip.faces.new((outer[i], outer[j], outer2[j], outer2[i]))
    bmesh.ops.recalc_face_normals(lip, faces=lip.faces)
    for f in lip.faces:
        if f.normal.z < 0:
            f.normal_flip()
    rm.add(lip, PAPER, smooth=False, face_mat=lambda c, n: SHADE if (c.x * n.x + c.y * n.y) < 0 else None)
    for k in range(14):
        a = 2 * math.pi * k / 14 + rnd.uniform(-0.1, 0.1)
        rr = R * 1.15
        st = bm_sphere((math.cos(a) * rr, math.sin(a) * rr * 0.85, 0.12), (0.5, 0.35, 0.18), seg=6, rings=3)
        rot(st, 'Z', math.degrees(a))
        jitter(st, 0.06, 2, k)
        rm.add(st, PAPER, smooth=False)
    edge = [V((x * 1.0, y * 1.0, 0.05)) for x, y in ol]
    rm.add(ink_poly(edge[:12], 0.04, overshoot=0.2, seed=1), INK, smooth=False)
    rm.add(ink_poly(edge[11:] + edge[:2], 0.04, overshoot=0.2, seed=2), INK, smooth=False)
    A.part(rm, pivot=(0, 0, 0))
    A.root['ouat_size'] = 14.0
    A.meta['note'] = 'Black pond radius ~6.5 m. Surface is a separate child (hide/animate when the Fish bursts up). Rim = paper lip + stones.'
    return A


# ===================================================================== light shaft + ceiling hole
def build_light_shaft():
    A = Asset('LightShaft')
    p = Part('Shaft')
    H = 28.0
    for k, (rb, rt) in enumerate(((5.0, 3.0), (3.8, 2.4))):
        b = bmesh.new()
        uv = b.loops.layers.uv.new('UVMap')
        seg = 20
        rows = []
        for j, (z, r) in enumerate(((0.0, rb), (H * 0.5, (rb + rt) / 2 * 1.02), (H, rt))):
            rows.append([b.verts.new(V((math.cos(2 * math.pi * i / seg) * r, math.sin(2 * math.pi * i / seg) * r, z))) for i in range(seg)])
        vv = (0.0, 0.5, 1.0)
        for j in range(2):
            for i in range(seg):
                i2 = (i + 1) % seg
                f = b.faces.new((rows[j][i], rows[j][i2], rows[j + 1][i2], rows[j + 1][i]))
                for loop, (u, v) in zip(f.loops, ((i / seg, vv[j]), ((i + 1) / seg, vv[j]), ((i + 1) / seg, vv[j + 1]), (i / seg, vv[j + 1]))):
                    loop[uv].uv = (u, v)
        p.add(b, 'M_Light', smooth=True)
    A.part(p, pivot=(0, 0, 0))
    A.root['ouat_size'] = 28.0
    A.meta['note'] = 'Two nested open cones (bottom r 5 / 3.8, top r 3 / 2.4, height 28). UV v = 0 at the floor .. 1 at the ceiling for a fade. Pivot = bottom centre.'
    return A


def build_ceiling_hole():
    A = Asset('CeilingHole')
    p = Part('Ceiling')
    rnd = random.Random(51)
    seg = 24
    R_in, R_out, T = 3.5, 14.0, 2.5
    b = bmesh.new()
    rings_r = [None, 6.0, 10.0, R_out]
    bot, top = [], []
    for j, rr in enumerate(rings_r):
        rb, rt = [], []
        for i in range(seg):
            a = 2 * math.pi * i / seg
            r = rr if rr else R_in * (1 + rnd.uniform(-0.18, 0.22))
            zj = rnd.uniform(-0.25, 0.25) if j > 0 else rnd.uniform(-0.6, 0.0)
            rb.append(b.verts.new(V((math.cos(a) * r, math.sin(a) * r, zj))))
            rt.append(b.verts.new(V((math.cos(a) * r, math.sin(a) * r, T + rnd.uniform(-0.3, 0.3)))))
        bot.append(rb)
        top.append(rt)
    for j in range(len(rings_r) - 1):
        for i in range(seg):
            i2 = (i + 1) % seg
            b.faces.new((bot[j][i], bot[j + 1][i], bot[j + 1][i2], bot[j][i2]))
            b.faces.new((top[j][i], top[j][i2], top[j + 1][i2], top[j + 1][i]))
    for i in range(seg):
        i2 = (i + 1) % seg
        b.faces.new((bot[0][i], bot[0][i2], top[0][i2], top[0][i]))
        b.faces.new((bot[-1][i], top[-1][i], top[-1][i2], bot[-1][i2]))
    bmesh.ops.recalc_face_normals(b, faces=b.faces)
    p.add(b, 'M_StoneDark', smooth=False, face_mat=lambda c, n: PAPER if (n.z > 0.5) or (math.hypot(c.x, c.y) < 4.5 and n.z > -0.5) else None)
    # stalactites + hanging roots near the hole, and the hole rim drawn in ink
    for k in range(10):
        a = 2 * math.pi * k / 10 + rnd.uniform(-0.2, 0.2)
        r = rnd.uniform(4.2, 7.5)
        c = V((math.cos(a) * r, math.sin(a) * r, 0.0))
        ln = rnd.uniform(0.8, 2.2)
        p.add(bm_cyl(c + V((0, 0, 0.1)), c - V((0, 0, ln)), rnd.uniform(0.25, 0.45), 0.02, seg=5), 'M_StoneDark', smooth=False)
    roots = []
    for k in range(9):
        a = 2 * math.pi * k / 9 + 0.3
        r = R_in * 1.05
        c = V((math.cos(a) * r, math.sin(a) * r, -0.2))
        roots.append(stroke(wobble_line(c, c + V((rnd.uniform(-0.4, 0.4), rnd.uniform(-0.4, 0.4), -rnd.uniform(1.0, 2.8))), 5, 0.15, k), 0.035, seg=3))
    p.add(merge(roots), INK, smooth=False)
    rim = [V((v.co.x, v.co.y, v.co.z - 0.05)) for v in bot[0]]
    p.add(ink_poly(rim[:13], 0.06, overshoot=0.3, seed=3), INK, smooth=False)
    p.add(ink_poly(rim[12:] + rim[:2], 0.06, overshoot=0.3, seed=4), INK, smooth=False)
    A.part(p, pivot=(0, 0, 0))
    A.root['ouat_size'] = 28.0
    A.meta['note'] = 'Ring slab (outer r 14, jagged hole r ~3.5, 2.5 m thick). Pivot = centre of the hole on the slab underside; place at ceiling height above LightShaft.'
    return A


ASSETS = [
    ('House_1', build_house_1), ('House_2', build_house_2), ('House_3', build_house_3), ('House_4', build_house_4),
    ('Tower_Dome', build_tower_dome), ('Paving_Hex', build_paving_hex), ('Paving_HexBroken', build_paving_hex_broken),
    ('Spire_1', build_spire_1), ('Spire_2', build_spire_2), ('Spire_3', build_spire_3),
    ('Cliff_1', build_cliff_1), ('Cliff_2', build_cliff_2), ('Cliff_3', build_cliff_3),
    ('CaveWall_1', build_cave_wall_1), ('CaveWall_2', build_cave_wall_2), ('CaveWall_3', build_cave_wall_3),
    ('Rock_1', build_rock_1), ('Rock_2', build_rock_2), ('Rock_3', build_rock_3),
    ('Pond', build_pond), ('LightShaft', build_light_shaft), ('CeilingHole', build_ceiling_hole),
]
