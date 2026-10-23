# -*- coding: utf-8 -*-
"""Dressing kit + FX meshes (10/23 rework: unfinished in FORM, not only in paint).
Blender coords: Z up, front -Y, root origin = floor centre.
Every asset = a designed silhouette with one deliberate unfinished feature: part of the form is a BUILT paper /
puppet-wood shell (with thickness, torn where it stops), the rest exists only as pencil construction (overshooting
corners, hatching running on past the torn edge, erased smudges). Solid parts carry paper/painted materials only
(Unity puts colliders on them); ink / pencil / hatch / smudge live in separate line parts ('Lines', 'Hatch').
Human objects (book, spoon) stay fully finished in vivid colour."""
import math, random
import bmesh
from mathutils import Vector
import ouat_lib as L
from ouat_lib import (Part, Asset, bm_sphere, bm_tube, bm_blade, bm_box, bm_lathe, bm_prism, stroke, wobble_line,
                      rot, move, deform, jitter, subdivide, nvec, nval)
import ouat_craft as CR

V = Vector
PAPER, SHADE, INK, HATCH = 'M_Paper', 'M_PaperShade', 'M_Ink', 'M_Hatch'
PENCIL, BACK, SMUDGE, FAINT = 'M_Pencil', 'M_PaperBack', 'M_Smudge', 'M_SketchLine'
PWOOD, PJOINT, RED, BLUE = 'M_PuppetWood', 'M_PuppetJoint', 'M_PaintRed', 'M_PaintBlue'
merge, tri_ngons = CR.merge, CR.tri_ngons


# ===================================================================== local helpers
def bbox(center, size, bev=0.0, seg=1, angle=40):
    b = bm_box(center, size)
    if bev > 0:
        b = L.bevel(b, bev, seg, angle)
    return b


def jag_outline(rx, ry, n=12, seed=0.0, rough=0.18, cx=0.0, cy=0.0):
    rnd = random.Random(int(seed * 100) + 3)
    pts = []
    for i in range(n):
        a = 2 * math.pi * (i + rnd.uniform(-0.25, 0.25)) / n
        k = 1.0 + rnd.uniform(-rough, rough)
        pts.append((cx + math.cos(a) * rx * k, cy + math.sin(a) * ry * k))
    return pts


def line(pts, r=0.012, seed=0.0, amp=0.0, over=0.0, taper=True):
    return CR.line(pts, r, over=over, seed=seed, amp=amp, taper=taper)


def loop(c, rx, ry, n=10, r=0.012, seed=0.0, tilt=(0, 0, 0), wob=0.18, turns=1.15):
    """A loose scribble loop (slightly more than one turn, wobbly radius)."""
    rnd = random.Random(int(seed * 97) + 1)
    pts = []
    steps = int(n * turns)
    for i in range(steps + 1):
        a = 2 * math.pi * i / n
        k = 1 + rnd.uniform(-wob, wob)
        pts.append(V((math.cos(a) * rx * k, math.sin(a) * ry * k, rnd.uniform(-0.04, 0.04) * rx)))
    b = stroke(pts, r, seg=3, taper=True)
    for ax, deg in zip('XYZ', tilt):
        if deg:
            rot(b, ax, deg)
    return move(b, c)


def angdist(a, b):
    return abs((a - b + math.pi) % (2 * math.pi) - math.pi)


def lathe_grid(profile, seg=16, cx=0.0, cy=0.0, cap_bottom=False, cap_top=False):
    b = bm_lathe(profile, seg=seg, center=(cx, cy, 0), cap_top=cap_top, cap_bottom=cap_bottom)
    tri_ngons(b)
    CR.orient_out(b, (cx, cy))
    return b


def prof_r(profile, z):
    for (r0, z0), (r1, z1) in zip(profile[:-1], profile[1:]):
        if z0 <= z <= z1:
            return r0 + (r1 - r0) * (z - z0) / max(1e-6, z1 - z0)
    return profile[-1][0] if z > profile[-1][1] else profile[0][0]


class Kit:
    """Named parts; solid ones get paper/painted only, line parts get ink/pencil."""

    def __init__(self, name):
        self.A = Asset(name)
        self.parts, self.order = {}, []

    def add(self, nm, b, mat, smooth=True, fm=None):
        if b is None or not len(b.verts):
            return
        if nm not in self.parts:
            self.parts[nm] = Part(nm)
            self.order.append(nm)
        self.parts[nm].add(b, mat, smooth=smooth, face_mat=fm)

    def form(self, solid, lines, b, field, mat, paint=None, thick=0.03, zig=0.02, seed=0.0, hatch=True, hatch_part=None,
             hatch_kw=None, back=True, back_near=None, smooth=True, ink_r=0.011):
        """Contour-cut a form: field > 0 = built shell (+ inside face), torn edge inked, hatching runs on past it."""
        full = CR.copy(b)
        res = CR.cut_field(b, field, zig=zig, seed=seed)
        self.add(solid, res.built, mat, smooth, paint)
        if back and len(res.built.faces):
            bk, rim = CR.shell_parts(res.built, thick, near=back_near, torn=res.torn)
            self.add(solid, bk, BACK, False)
            self.add(solid, rim, 'M_TornEdge', False)
        self.add(lines, CR.torn_ink(res, ink_r, seed, lift=0.006), INK, False)
        if hatch:
            self.add(hatch_part or lines, CR.torn_hatch(res, seed=seed, **(hatch_kw or {})), PENCIL, False)
        return full, res

    def finish(self, size, note, pivots=None, parents=None):
        pivots, parents = pivots or {}, parents or {}
        for nm in self.order:
            self.A.part(self.parts[nm], pivot=pivots.get(nm, (0, 0, 0)), parent=parents.get(nm))
        self.A.root['ouat_size'] = size
        self.A.meta['note'] = note
        return self.A


def fin(A, parts, size, note=''):
    """parts: list of (Part, pivot)."""
    for p, pv in parts:
        A.part(p, pivot=pv)
    A.root['ouat_size'] = size
    A.meta['note'] = note
    return A


SMALL_HATCH = dict(spacing=0.05, length=(0.04, 0.13), r=0.0045, slant=35, density=0.75)


# ===================================================================== Sketch walls
def sketch_wall(name, length, h_solid, h_plan, seed, kind='straight'):
    """Paper-stone wall built up to a torn, wandering top; above it the planned wall exists only as construction:
    pencil posts + courses + a brace, hatching running on past the torn edge, a smudge where a course was erased."""
    rnd = random.Random(seed)
    K = Kit(name)
    t = 0.42
    segs = [(V((-length / 2, 0, 0)), V((length / 2, 0, 0)))]
    if kind == 'corner':
        segs = [(V((-length / 2, 0, 0)), V((length / 4, 0, 0))), (V((length / 4, 0, 0)), V((length / 4, length * 0.55, 0)))]
    for si, (a, b) in enumerate(segs):
        d = b - a
        ln = d.length
        ax = d.normalized()
        nrm = V((ax.y, -ax.x, 0))          # front side (faces -Y for the first segment)
        mid = (a + b) / 2 - nrm * 0.0
        # wall block as a grid box in local frame, rotated into place
        box = CR.grid_box((0, 0, h_plan * 0.5), (ln + (t if kind == 'corner' and si == 0 else 0), t, h_plan), step=0.38,
                          faces='xyXYz')
        ang = math.degrees(math.atan2(ax.y, ax.x))
        rot(box, 'Z', ang)
        move(box, mid + (ax * t / 2 if kind == 'corner' and si == 0 else V((0, 0, 0))))
        o = a.copy()

        def top(p, a=a, ax=ax, ln=ln, si=si):
            u = (p - a).dot(ax) / max(ln, 1e-6)
            return (h_solid * (0.62 + 0.38 * abs(math.sin(u * 3.4 + seed + si)))
                    + nval(p * V((1, 1, 0.3)), 1.6, seed) * 0.22 + nval(p, 6.0, seed + 3) * 0.05)
        fld = lambda p, top=top: top(p) - p.z
        CR.orient_out(box, center=mid + V((0, 0, h_plan * 0.5)))
        K.form('Solid', 'Lines', box, fld, PAPER, paint=lambda c, n: SHADE if c.z < 0.3 else None, thick=0.05, zig=0.035,
               seed=seed + si, hatch_part='Hatch', hatch_kw=dict(spacing=0.16 if len(segs) == 1 else 0.24, length=(0.12, 0.4), r=0.0065, density=0.65, slant=42), back_near=0.6, smooth=False)
        # stone courses (ink) on the built front, stopping under the torn edge
        front = lambda x, z, a=a, ax=ax, nrm=nrm: a + ax * x + V((0, 0, z)) + nrm * (t / 2 + 0.012)
        for row in range(1, 5 if len(segs) == 1 else 3):
            z = row * 0.36
            pts = [front(ln * i / 8, z + rnd.uniform(-0.02, 0.02)) for i in range(9)]
            K.add('Lines', CR.clipped_lines(pts, lambda p, fld=fld: fld(p) > 0.08, 0.009, 0.02, seed + row, 0.006), INK, False)
            for i in range(int(ln / 0.8)):
                x = (i + 0.5 * (row % 2) + rnd.uniform(-0.1, 0.1)) * 0.8
                p0, p1 = front(x, z - 0.36), front(x, z)
                if fld(p1) > 0.05 and x < ln:
                    K.add('Lines', line([p0, p1], 0.007, seed + i, taper=False), INK, False)
        # planned wall above: pencil posts, two courses, a diagonal brace (construction), faint plumb guides
        for i in range(0, 5, 1 if len(segs) == 1 else 2):
            x = ln * i / 4
            p = front(x, 0)
            zt = top(p + V((0, 0, h_solid)))
            K.add('Lines', line([p + V((0, 0, max(0.3, zt - 0.1))), p + V((0, 0, h_plan * rnd.uniform(0.93, 1.04)))], 0.008, seed + i, over=0.18, taper=False), PENCIL, False)
        for k, z in enumerate((h_plan * 0.72, h_plan)):
            K.add('Lines', line([front(-0.25, z), front(ln + 0.3, z * rnd.uniform(0.97, 1.02))], 0.008, seed + 40 + k, over=0.2, taper=False), PENCIL, False)
        K.add('Lines', line([front(0.1, h_solid * 0.9), front(ln * 0.55, h_plan)], 0.007, seed + 50, over=0.15, taper=False), PENCIL, False)
        if kind == 'window' and si == 0:
            # arched window: its lower part cut into the built wall (dark), the arch only drawn in the plan above
            w, hh = 0.9, 1.45
            fx = lambda pts: [front(ln / 2 + x, z) for x, z in pts]
            K.add('Lines', CR.line(fx([(x, h_solid * 0.55 + z) for x, z in CR.arch2d(w, hh, 8)]), 0.014, over=0.08, seed=seed + 60, amp=0.006), INK, False)
            K.add('Lines', CR.line(fx([(x * 1.15, h_solid * 0.55 + z * 1.07) for x, z in CR.arch2d(w, hh, 8)]), 0.007, over=0.12, seed=seed + 61), PENCIL, False)
            hole = bmesh.new()
            pts = fx([(-w / 2, h_solid * 0.55), (w / 2, h_solid * 0.55), (w / 2, h_solid * 0.95), (-w / 2, h_solid * 0.95)])
            hole.faces.new([hole.verts.new(p + nrm * 0.004) for p in pts])
            K.add('Lines', hole, INK, False)
        if si == 0:
            K.add('Lines', CR.smudge(front(ln * 0.7, h_plan * 0.82), nrm, 0.9, 0.45, seed=seed + 70, lift=0.0), SMUDGE, False)
    size = max(length, h_plan)
    return K.finish(size, 'Built only up to a torn, wandering paper top (inside face visible through the tear); the planned wall above '
                          'is pencil construction (posts, courses, brace) with hatching running on past the torn edge. Front faces -Y (Unity +Z). '
                          'Solid = collider, Lines/Hatch = unlit.')


def build_sketch_wall_1():
    return sketch_wall('Sketch_Wall_1', 5.0, 1.55, 3.4, 11)


def build_sketch_wall_2():
    return sketch_wall('Sketch_Wall_2', 4.2, 1.35, 3.8, 12, kind='window')


def build_sketch_wall_3():
    return sketch_wall('Sketch_Wall_3', 5.0, 1.15, 3.0, 13, kind='corner')


# ===================================================================== Sketch trees
def sketch_tree(name, h, seed, crown='loops', solid_frac=0.45):
    rnd = random.Random(seed)
    K = Kit(name)
    lean = V((rnd.uniform(-0.15, 0.15), rnd.uniform(-0.1, 0.1), 0))
    spine = [V((0, 0, 0)), V((0, 0, h * 0.2)) + lean * 0.3, V((0, 0, h * 0.45)) + lean * 0.7, V((0, 0, h * 0.62)) + lean]
    radii = [0.3, 0.2, 0.16, 0.13]
    zcut = h * solid_frac
    # trunk as a full tube, then torn at a slanted wandering height (bark shell with an inside)
    pts = []
    rr = []
    for i in range(len(spine) - 1):
        for k in range(3):
            tt = k / 3
            pts.append(spine[i].lerp(spine[i + 1], tt))
            rr.append(radii[i] + (radii[i + 1] - radii[i]) * tt)
    pts.append(spine[-1]); rr.append(radii[-1])
    tb = bm_tube(pts, rr, seg=8, cap=False)
    CR.orient_out(tb, (0, 0))
    jitter(tb, 0.012, 4, seed)
    fld = lambda p: zcut + (p.x * 0.7 - p.y * 0.4) * 0.8 + nval(p, 3.0, seed) * 0.25 + nval(p, 9.0, seed + 1) * 0.05 - p.z
    K.form('Trunk', 'Lines', tb, fld, PAPER, paint=lambda c, n: SHADE if (n.x > 0.45 or c.z < 0.2) else None, thick=0.03, zig=0.03,
           seed=seed, hatch_kw=dict(spacing=0.05, length=(0.12, 0.4), r=0.005, up_only=True))
    for k in range(4):
        a = 2 * math.pi * k / 4 + seed
        d = V((math.cos(a), math.sin(a), 0))
        K.add('Trunk', bm_tube([d * 0.15 + V((0, 0, 0.18)), d * 0.45 + V((0, 0, 0.03)), d * 0.72 + V((0, 0, -0.02))], [0.1, 0.06, 0.02], seg=5), PAPER)
    # bark strokes on the built part
    for k in range(3):
        a = 2 * math.pi * k / 3 + 0.4
        p0 = V((math.cos(a) * 0.21, math.sin(a) * 0.21, 0.25))
        p1 = V((math.cos(a + 0.2) * 0.18, math.sin(a + 0.2) * 0.18, zcut * 0.85))
        K.add('Lines', CR.clipped_lines(CR.dense([p0, p1], 0.15), lambda p: fld(p) > 0.05, 0.009, 0.0, seed + k), INK, False)
    # upper trunk: two contour lines + pencil rings where it should be
    top = spine[-1]
    for s in (-1, 1):
        K.add('Lines', line([V((0.17 * s, 0, zcut * 0.8)), V((0.15 * s, 0, h * 0.5)) + lean * 0.8, top + V((0.12 * s, 0, 0))], 0.013, seed + 5 + s, 0.015, over=0.12), INK, False)
    for k, z in enumerate((h * 0.5, h * 0.58)):
        c = spine[2].lerp(spine[3], (z - h * 0.45) / (h * 0.17))
        K.add('Lines', CR.ellipse(c, 0.16, 0.13, 0.0, turns=1.05, n=12, r=0.005, seed=seed + 8 + k), PENCIL, False)
    tips = []
    for k in range(5):
        a = 2 * math.pi * k / 5 + rnd.uniform(-0.3, 0.3)
        d = V((math.cos(a), math.sin(a) * 0.8, 0))
        p0 = top + V((0, 0, -0.2 * k / 5))
        p1 = p0 + d * h * 0.18 + V((0, 0, h * 0.12))
        p2 = p1 + d * h * 0.12 + V((0, 0, h * 0.1))
        K.add('Lines', line([p0, p1, p2], 0.012, seed + 10 + k, 0.03, over=0.05), INK, False)
        tips.append(p2)
    cc = top + V((0, 0, h * 0.22))
    if crown == 'loops':
        for k in range(6):
            c = cc + V((rnd.uniform(-1, 1) * h * 0.2, rnd.uniform(-1, 1) * h * 0.15, rnd.uniform(-0.6, 1) * h * 0.12))
            K.add('Crown', loop(c, h * rnd.uniform(0.08, 0.15), h * rnd.uniform(0.06, 0.11), 8, 0.011, seed + k,
                                tilt=(rnd.uniform(-60, 60), rnd.uniform(-40, 40), rnd.uniform(0, 180))), INK, False)
        # one paper clump that did get built - torn open on its far side
        cb = bm_sphere(cc + V((h * 0.08, 0, h * 0.02)), (h * 0.15, h * 0.12, h * 0.09), seg=8, rings=6)
        jitter(cb, h * 0.015, 3, seed)
        c0 = cc + V((h * 0.08, 0, h * 0.02))
        CR.orient_out(cb, center=c0)
        K.form('Crown', 'Crown', cb, lambda p: -(p - c0).dot(V((0.8, 0.5, 0.2)).normalized()) + 0.02 + nval(p, 3.0, seed) * 0.12,
               'M_Leaf', thick=0.02, zig=0.03, seed=seed + 3, hatch=False, ink_r=0.01)
    elif crown == 'clumps':
        for k, tp in enumerate(tips):
            c0 = tp + V((0, 0, 0.1))
            cb = bm_sphere(c0, (h * 0.12, h * 0.1, h * 0.075), seg=6, rings=4)
            jitter(cb, h * 0.015, 3, seed + k)
            CR.orient_out(cb, center=c0)
            if k % 2 == 0:
                K.add('Crown', cb, 'M_Leaf', False)
            else:
                # half-built clump: lower half paper, upper half a pencil scribble
                K.form('Crown', 'Crown', cb, lambda p, c0=c0: c0.z + nval(p, 4.0, seed + k) * 0.08 - p.z, 'M_Leaf', thick=0.02, zig=0.02,
                       seed=seed + k, hatch=False, ink_r=0.009)
                K.add('Crown', loop(c0 + V((0, 0, h * 0.03)), h * 0.12, h * 0.1, 9, 0.007, seed + 30 + k, tilt=(70, 0, 20)), PENCIL, False)
        for k in range(2):
            c = cc + V((rnd.uniform(-1, 1) * h * 0.25, rnd.uniform(-1, 1) * h * 0.15, rnd.uniform(0, 1) * h * 0.12))
            K.add('Crown', loop(c, h * 0.1, h * 0.07, 9, 0.01, seed + 20 + k, tilt=(rnd.uniform(-50, 50), 0, rnd.uniform(0, 180))), INK, False)
    else:  # dead: twigs only, a few in pencil (not yet inked)
        for k, tp in enumerate(tips):
            for j in range(2):
                d = V((rnd.uniform(-1, 1), rnd.uniform(-1, 1), 1.2)).normalized()
                K.add('Crown', line([tp, tp + d * h * 0.09, tp + d * h * 0.14 + V((rnd.uniform(-0.1, 0.1), 0, 0))], 0.009 if j == 0 else 0.006,
                                    seed + 30 + k * 2 + j, 0.01, over=0.03), INK if j == 0 else PENCIL, False)
    K.add('Lines', CR.smudge(top + V((0.3, -0.25, -h * 0.1)), V((0.2, -1, 0.1)), h * 0.18, h * 0.1, seed=seed + 50), SMUDGE, False)
    return K.finish(h, 'Trunk built as a bark shell only up to a slanted torn edge (inside visible); upper trunk = two ink contours + pencil '
                       'rings, branches ink, crown ink scribble with one paper clump torn open. Crown pivot = crown centre (sway).',
                    pivots={'Crown': tuple(cc)})


def build_sketch_tree_1():
    return sketch_tree('Sketch_Tree_1', 5.5, 21, 'loops')


def build_sketch_tree_2():
    return sketch_tree('Sketch_Tree_2', 4.5, 22, 'clumps', 0.55)


def build_sketch_tree_3():
    return sketch_tree('Sketch_Tree_3', 4.0, 23, 'dead', 0.35)


# ===================================================================== Sketch fences
def sketch_fence(name, length, seed, posts=6):
    rnd = random.Random(seed)
    K = Kit(name)
    built = 2 if posts <= 5 else 3
    xb = -length / 2 + length * (built - 0.55) / (posts - 1)          # where the rails stop being wood
    for i in range(posts):
        x = -length / 2 + length * i / (posts - 1)
        h = rnd.uniform(1.05, 1.3)
        if i < built:
            pb = bm_tube([V((x, 0, 0)), V((x + rnd.uniform(-0.03, 0.03), 0, h))], [0.065, 0.055], seg=6)
            K.add('Solid', pb, PWOOD)
            K.add('Solid', bm_sphere((x, 0, h + 0.05), (0.075,) * 3, seg=6, rings=4), PJOINT)
            K.add('Lines', line([V((x - 0.06, -0.06, 0.08)), V((x - 0.055, -0.06, h * 0.9))], 0.007, seed + i, taper=False), INK, False)
        else:
            # drawn post: two contour lines + a joint circle, getting fainter
            m = PENCIL if i < posts - 1 else FAINT
            for s in (-1, 1):
                K.add('Lines', line([V((x + 0.06 * s, -0.04, 0.0)), V((x + 0.06 * s, -0.04, h + rnd.uniform(-0.1, 0.15)))], 0.008, seed + i * 3 + s, 0.01, over=0.12, taper=False), m, False)
            K.add('Lines', CR.ellipse((x, -0.04, h + 0.05), 0.08, 0.08, 0.0, turns=1.1, n=10, r=0.006, seed=seed + i, tilt=('X', 90)), m, False)
    for k, z in enumerate((0.45, 0.85)):
        rb = CR.grid_box(((xb - length / 2 - 0.12) / 2, -0.08, z), (xb + length / 2 + 0.12, 0.06, 0.1), step=0.12)
        jitter(rb, 0.006, 3, seed + k)
        fld = lambda p, k=k: xb + nval(p, 5.0, seed + k) * 0.08 - p.x
        K.form('Solid', 'Lines', rb, fld, PWOOD, thick=0.012, zig=0.015, seed=seed + k, hatch=False, ink_r=0.008, smooth=False)
        K.add('Lines', line([V((xb - 0.05, -0.08, z)), V((length / 2 + 0.2, -0.08, z + rnd.uniform(-0.12, 0.08)))], 0.008, seed + 40 + k, 0.03, over=0.18, taper=False), PENCIL, False)
        K.add('Lines', line([V((xb + 0.3, -0.08, z + 0.07)), V((length / 2 - 0.3, -0.08, z + 0.05))], 0.006, seed + 50 + k, 0.03, over=0.05, taper=False), PENCIL, False)
    K.add('Lines', CR.smudge(V((length * 0.3, -0.1, 0.65)), V((0, -1, 0)), 0.8, 0.4, seed=seed + 60, lift=0.0), SMUDGE, False)
    return K.finish(length, 'First posts are real puppet wood (ball-joint tops), rails torn off where the wood stops; the rest of the fence is '
                            'pencil posts/rails fading out. Runs along local X.')


def build_sketch_fence_1():
    return sketch_fence('Sketch_Fence_1', 4.0, 31, 6)


def build_sketch_fence_2():
    return sketch_fence('Sketch_Fence_2', 3.0, 32, 5)


# ===================================================================== Sketch arch
def build_sketch_arch():
    K = Kit('Sketch_Arch')
    w, h = 2.6, 3.4
    sh = h - w / 2
    rnd = random.Random(40)
    # piers: left pier fully stacked, right pier only its two base stones
    for s in (-1, 1):
        n = 4 if s < 0 else 2
        for k in range(n):
            hh = sh / 4
            b = bbox((s * (w / 2 + 0.25), 0, hh * (k + 0.5)), (0.5 - k * 0.02, 0.55, hh * 0.94), 0.03)
            jitter(b, 0.015, 3, 40 + k + s)
            K.add('Solid', b, PAPER, False, lambda c, n, s=s: SHADE if n.x * s < -0.4 else None)
        if s > 0:
            for k in range(2, 4):
                K.add('Lines', CR.box_wire((s * (w / 2 + 0.25), 0, sh / 4 * (k + 0.5)), (0.5, 0.55, sh / 4 * 0.94), 0.007, 0.08, 41 + k, skip=(1, 5)), PENCIL, False)
    # voussoirs: built on the left half of the arch, then only the outline + ticks
    c = V((0, 0, sh))
    nv = 9
    for i in range(nv):
        a0 = math.pi - math.pi * i / nv
        a1 = math.pi - math.pi * (i + 1) / nv
        r0, r1 = w / 2, w / 2 + 0.5
        quad = [(math.cos(a0) * r0, math.sin(a0) * r0), (math.cos(a0) * r1, math.sin(a0) * r1),
                (math.cos(a1) * r1, math.sin(a1) * r1), (math.cos(a1) * r0, math.sin(a1) * r0)]
        if i < 4:
            g = 0.012
            cq = V((sum(q[0] for q in quad) / 4, sum(q[1] for q in quad) / 4, 0))
            ql = [(cq.x + (x - cq.x) * (1 - g * 4), cq.y + (z - cq.y) * (1 - g * 4)) for x, z in quad]
            b = bm_prism([(x, z + sh) for x, z in ql], -0.27, 0.27, axis='Y')
            tri_ngons(b)
            jitter(b, 0.01, 4, 50 + i)
            K.add('Solid', b, PAPER, False, lambda c_, n: SHADE if n.z < -0.3 else None)
        else:
            m = INK if i == 4 else PENCIL
            K.add('Lines', line([c + V((quad[0][0], -0.28, quad[0][1])), c + V((quad[1][0], -0.28, quad[1][1]))], 0.008, 51 + i, taper=False, over=0.05), m, False)
    for k, (rr, m, r_) in enumerate(((w / 2, INK, 0.016), (w / 2 + 0.5, INK, 0.013), (w / 2 + 0.62, PENCIL, 0.007))):
        pts = [c + V((math.cos(a) * rr, -0.28, math.sin(a) * rr)) for a in [math.pi * j / 12 for j in range(0, 8 if k < 2 else 13)]]
        K.add('Lines', line(pts, r_, 60 + k, 0.01, over=0.15), m, False)
    # depth construction lines going back + the keystone outline floating
    for s in (-1, 1):
        K.add('Lines', line([V((s * (w / 2 + 0.5), -0.28, sh)), V((s * (w / 2 + 0.5), 0.35, sh + 0.05))], 0.007, 42 + s, over=0.1, taper=False), PENCIL, False)
    K.add('Lines', CR.guides([((-w / 2 - 1.0, -0.28, sh), (w / 2 + 1.0, -0.28, sh)), ((0, -0.28, -0.1), (0, -0.28, h + 1.0))], 0.005, 0.3, seed=70), FAINT, False)
    K.add('Lines', CR.smudge(V((0.9, -0.3, h - 0.3)), V((0, -1, 0)), 0.9, 0.5, seed=71, lift=0.0), SMUDGE, False)
    return K.finish(h + 0.6, 'Arch: left pier and the left half of the voussoirs are built paper stone; the right pier stops after two stones '
                             '(rest = pencil boxes) and the right half of the arch exists only as ink/pencil outline. Opening 2.6 m wide, faces -Y.')


# ===================================================================== paper scraps
def build_scrap(variant):
    p = Part('Scrap')
    rnd = random.Random(60 + variant)
    if variant == 1:   # crumpled ball
        b = bm_sphere((0, 0, 0.16), (0.2, 0.18, 0.16), seg=8, rings=6)
        jitter(b, 0.05, 6, 61)
        p.add(b, 'M_Paper', smooth=False)
        p.add(line([V((-0.1, -0.17, 0.2)), V((0.0, -0.19, 0.12)), V((0.12, -0.15, 0.2))], 0.008, 62, 0.01), INK, smooth=False)
        p.add(line([V((-0.05, -0.12, 0.3)), V((0.08, -0.1, 0.27))], 0.005, 63), PENCIL, smooth=False)
        size = 0.4
    else:              # flat torn sheet with scribbles (2 = flat, 3 = folded)
        pts = jag_outline(0.45, 0.32, 14, seed=63 + variant, rough=0.2)
        b = bm_prism(pts, 0.0, 0.008)
        tri_ngons(b)
        if variant == 3:
            deform(b, lambda c: V((c.x, c.y, c.z + max(0.0, c.x) * 0.45)))
        else:
            deform(b, lambda c: V((c.x, c.y, c.z + 0.03 * math.sin(c.x * 6) + 0.02)))
        p.add(b, 'M_Paper', smooth=False)
        zf = (lambda x: max(0.0, x) * 0.45) if variant == 3 else (lambda x: 0.03 * math.sin(x * 6) + 0.02)
        for k in range(4):
            y = -0.15 + 0.1 * k
            x0, x1 = -0.3, rnd.uniform(-0.05, 0.25)
            pts2 = [V((x0 + (x1 - x0) * t, y + 0.02 * math.sin(t * 9 + k), 0.035 + zf(x0 + (x1 - x0) * t))) for t in (0, 0.25, 0.5, 0.75, 1.0)]
            p.add(stroke(pts2, 0.007, seg=3), INK if k < 2 else PENCIL, smooth=False)
        # inked torn edge along part of the outline
        p.add(line([V((x, y, 0.012 + zf(x))) for x, y in pts[:6]], 0.006, 64), INK, smooth=False)
        size = 0.9
    A = Asset(f'Scrap_Paper_{variant}')
    return fin(A, [(p, (0, 0, 0))], size, 'Paper scrap on the ground (no collider needed).')


def build_scrap_paper_1():
    return build_scrap(1)


def build_scrap_paper_2():
    return build_scrap(2)


def build_scrap_paper_3():
    return build_scrap(3)


# ===================================================================== stairs going nowhere
def build_stair_sketch():
    K = Kit('Stair_Sketch')
    w, rise, run, n_total = 1.4, 0.25, 0.38, 10
    # three solid steps + the 4th step torn half-way across, then only lines
    for i in range(3):
        b = bbox((0, i * run + run / 2, rise * (i + 0.5)), (w, run * 1.05, rise), 0.02)
        jitter(b, 0.012, 3, 70 + i)
        K.add('Solid', b, PAPER, False, lambda c, n: SHADE if abs(n.x) > 0.5 or n.y < -0.5 else None)
        K.add('Lines', line([V((-w / 2, i * run - 0.01, rise * (i + 1))), V((w / 2, i * run - 0.01, rise * (i + 1)))], 0.009, 80 + i, over=0.06), INK, False)
    # stair body under the steps (side stringer wall) - built only on the left
    sw = bm_prism([(0, 0), (3 * run, 0), (3 * run, 3 * rise), (0, rise * 0.4)], -w / 2 - 0.08, -w / 2, axis='X')
    tri_ngons(sw)
    K.add('Solid', sw, SHADE, False)
    st = CR.grid_box((0, 3 * run + run / 2, rise * 3.5), (w, run, rise), step=0.12)
    fld = lambda p: 0.0 - p.x + nval(p, 5.0, 74) * 0.18
    K.form('Solid', 'Lines', st, fld, PAPER, thick=0.03, zig=0.03, seed=74, hatch_kw=dict(spacing=0.05, length=(0.08, 0.25), r=0.004, up_only=False), back_near=0.5, smooth=False)
    for i in range(3, n_total):
        y0, z0 = i * run, rise * i
        m = PENCIL if i < 7 else FAINT
        for s in (-1, 1):
            x = s * w / 2
            K.add('Lines', line([V((x, y0, z0)), V((x, y0, z0 + rise)), V((x, y0 + run, z0 + rise))], 0.009, 71 + i * 2 + s, 0.006, over=0.03), m, False)
        K.add('Lines', line([V((-w / 2, y0, z0 + rise)), V((w / 2, y0, z0 + rise))], 0.008, 90 + i, 0.01, over=0.06, taper=False), m, False)
    for s in (-1, 1):
        K.add('Lines', line([V((s * w / 2, 0, 0)), V((s * w / 2, n_total * run + 0.6, n_total * rise + 0.4))], 0.007, 95 + s, 0.02, over=0.25, taper=False), PENCIL, False)
    K.add('Lines', CR.smudge(V((0.2, 6 * run, 6 * rise + 0.15)), V((0, -0.55, 0.85)), 1.0, 0.5, seed=97, lift=0.0), SMUDGE, False)
    return K.finish(4.0, 'Three solid steps, the 4th torn half-way across, then stairs drawn only as lines climbing toward +Y (Unity -Z) into '
                         'nothing. Not walkable beyond the solid steps.')


# ===================================================================== creature furniture & containers
def build_bench_puppet():
    K = Kit('Bench_Puppet')
    L_, W_, H_ = 1.8, 0.45, 0.45
    # seat plank: built from the left end, torn at ~70 %, the rest only a pencil box
    sb = CR.grid_box((0, 0, H_), (L_, W_, 0.09), step=0.1)
    xt = L_ * 0.22
    fld = lambda p: xt + nval(p, 4.0, 81) * 0.12 + nval(p, 12.0, 82) * 0.02 - p.x
    K.form('Seat', 'Lines', sb, fld, PWOOD, paint=CR.paint_ragged(-0.35, axis_fn=lambda c: -c.x, amp=0.12, seed=83, mat=BLUE),
           thick=0.015, zig=0.02, seed=81, hatch_kw=dict(SMALL_HATCH, up_only=False), back_near=0.4, smooth=False)
    K.add('Lines', CR.box_wire((xt + (L_ / 2 - xt) / 2 + 0.05, 0, H_), (L_ / 2 - xt + 0.1, W_, 0.09), 0.007, 0.06, 84, skip=(1, 5, 9)), PENCIL, False)
    for k in range(3):
        x = -L_ / 2 + 0.3 + k * 0.4
        K.add('Lines', line([V((x, -W_ / 2 - 0.004, H_ - 0.04)), V((x + 0.25, -W_ / 2 - 0.004, H_ + 0.03))], 0.005, 85 + k, taper=False), INK, False)
    for s in (-1, 1):
        for t in (-1, 1):
            p = V((s * (L_ / 2 - 0.15), t * 0.14, H_ - 0.04))
            if s < 0:
                K.add('Legs', bm_sphere(p, (0.055,) * 3, seg=8, rings=5), PJOINT)
                K.add('Legs', bm_tube([p, p + V((s * 0.05, t * 0.03, -H_ * 0.5)), p + V((s * 0.07, t * 0.04, -H_ + 0.02))], [0.04, 0.035, 0.04], seg=6), PWOOD)
            else:
                # leg only drawn: two contour lines + joint circle
                for e in (-1, 1):
                    q = V((0.035 * e, 0, 0))
                    K.add('Lines', line([p + q, p + q + V((s * 0.05, t * 0.03, -H_ * 0.5)), p + q + V((s * 0.07, t * 0.04, -H_ + 0.02))], 0.007, 86 + e + t, over=0.06, taper=False), PENCIL, False)
                K.add('Lines', CR.ellipse(p, 0.055, 0.055, 0.0, turns=1.1, n=10, r=0.005, seed=88 + t, tilt=('X', 90)), PENCIL, False)
    # backrest only drawn
    K.add('Lines', line([V((-L_ / 2, W_ / 2 - 0.05, H_ + 0.05)), V((-L_ / 2 + 0.05, W_ / 2, H_ + 0.55)), V((L_ / 2, W_ / 2 + 0.02, H_ + 0.5))], 0.011, 82, 0.02, over=0.1), INK, False)
    for k in range(4):
        x = -L_ / 2 + 0.35 + k * 0.4
        K.add('Lines', line([V((x, W_ / 2, H_ + 0.05)), V((x + 0.02, W_ / 2 + 0.01, H_ + 0.52))], 0.006, 90 + k, over=0.05, taper=False), PENCIL, False)
    return K.finish(1.8, 'Creature bench (seat 0.45 m). Left end built (puppet wood, blue paint brushed on, ball-jointed legs); the plank is torn '
                         'at ~70 % and the right end + its two legs exist only in pencil. Backrest only drawn.')


def build_barrel():
    K = Kit('Barrel')
    prof = [(0.3, 0.0), (0.345, 0.15), (0.375, 0.32), (0.385, 0.45), (0.375, 0.58), (0.345, 0.75), (0.3, 0.9)]
    n_st = 16
    b = lathe_grid([(r, z) for r, z in [(prof_r(prof, z), z) for z in [0.9 * i / 9 for i in range(10)]]], seg=n_st)
    rnd = random.Random(91)
    front = math.radians(-125)
    # staves built one by one: the ones facing front-left exist (some shorter, being added), the rest only drawn
    heights = {}
    for k in range(n_st):
        a = 2 * math.pi * (k + 0.5) / n_st
        d = angdist(a, front)
        heights[k] = 0.9 if d < 1.45 else (rnd.choice((0.38, 0.55, 0.7)) if d < 1.95 else -1.0)

    def stave(c):
        a = math.atan2(c.y, c.x) % (2 * math.pi)
        return int(a / (2 * math.pi / n_st)) % n_st
    keep = lambda c, n: c.z < heights[stave(c)]
    full = CR.copy(b)
    res = CR.cut(b, keep, rag=0.0)
    paint = CR.paint_ragged(0.6, amp=0.05, seed=92, mat=RED)
    K.add('Barrel', res.built, PWOOD, True, paint)
    bk, rim = CR.shell_parts(res.built, 0.025)
    K.add('Barrel', bk, BACK, False)
    K.add('Barrel', rim, 'M_TornEdge', False)
    K.add('Lines', CR.torn_ink(res, 0.008, 93, lift=0.004), INK, False)
    # bottom disc (so it stands)
    bot = bm_lathe([(0.0, 0.03), (0.29, 0.03)], seg=n_st, cap_top=False, cap_bottom=False)
    K.add('Barrel', bot, PWOOD, False)
    # stave seams: ink on built staves, pencil on the drawn ones (continuing past the top)
    for k in range(n_st):
        a = 2 * math.pi * k / n_st
        built = heights[k] > 0 or heights[(k - 1) % n_st] > 0
        top = max(heights[k], heights[(k - 1) % n_st]) if built else 0.9
        pts = [V((math.cos(a) * (prof_r(prof, z) + 0.006), math.sin(a) * (prof_r(prof, z) + 0.006), z)) for z in [top * i / 3 for i in range(4)]]
        if built:
            K.add('Lines', line(pts, 0.007, 94 + k, taper=False), INK, False)
        elif k % 2 == 0:
            K.add('Lines', line(pts, 0.007, 94 + k, over=0.05), PENCIL, False)
    # hoops: inked bands across the built staves, continuing all the way round as pencil ellipses
    for j, z in enumerate((0.12, 0.3, 0.6, 0.78)):
        r = prof_r(prof, z) + 0.012
        ring = CR.ring_pts(0, 0, z, r, 24)
        K.add('Lines', CR.clipped_lines(ring, lambda p: heights[stave(p)] > z, 0.011, 0.0, 95 + j), INK, False)
        if j in (0, 3):
            K.add('Lines', CR.clipped_lines(ring, lambda p: heights[stave(p)] <= z, 0.007, 0.06, 96 + j), PENCIL, False)
    # planned rim + lid only drawn; the actual lid leans on the floor against the barrel
    K.add('Lines', CR.ellipse((0, 0, 0.905), 0.3, 0.3, 0.0, turns=1.08, n=16, r=0.007, seed=97), PENCIL, False)
    lid = bm_lathe([(0.0, 0.0), (0.27, 0.0), (0.27, 0.035), (0.0, 0.035)], seg=14)
    rot(lid, 'X', 70)
    move(lid, (0.56, 0.3, 0.26))
    K.add('Barrel', lid, PWOOD, False)
    # plank seams on the lid face (lid face normal = rot X 70 of +Z -> (0, -sin70, cos70))
    ln_ = V((0, -math.sin(math.radians(70)), math.cos(math.radians(70))))
    up_ = V((0, math.cos(math.radians(70)), math.sin(math.radians(70))))
    lc = V((0.56, 0.3, 0.26)) + ln_ * 0.04
    for k in (-1, 1):
        K.add('Lines', line([lc + V((k * 0.09, 0, 0)) - up_ * 0.24, lc + V((k * 0.09, 0, 0)) + up_ * 0.24], 0.007, 98 + k, taper=False), INK, False)
    K.add('Lines', CR.smudge(V((0.25, 0.22, 0.75)), V((0.7, 0.7, 0)), 0.3, 0.2, seed=99, lift=0.0), SMUDGE, False)
    return K.finish(0.9, 'Creature barrel built stave by stave: the front-left staves exist (bare wood, red brushed on the top band, '
                         'some still short), the back staves and the rim are pencil; inked hoops run on as pencil ellipses. Lid leans on the floor.')


def build_crate():
    K = Kit('Crate')
    s, th = 0.6, 0.03
    # built: bottom, back (+Y) and left (-X) walls of separate planks; front + right + top = pencil edges -> the inside shows
    for k in range(3):
        z = th / 2
        K.add('Crate', bbox((0, -s / 2 + s * (k + 0.5) / 3, z), (s, s / 3 - 0.012, th), 0.004), PWOOD, False)
    for k in range(3):
        z = s * (k + 0.5) / 3
        K.add('Crate', bbox((0, s / 2 - th / 2, z), (s, th, s / 3 - 0.014), 0.004), PWOOD, False, lambda c, n: SHADE if n.y < -0.5 else None)
        if k < 2 or True:
            hgt = s / 3 - 0.014
            ln = s if k < 2 else s * 0.62     # top plank of the left wall is short (still being added)
            K.add('Crate', bbox((-s / 2 + th / 2, s / 2 - ln / 2, z), (th, ln, hgt), 0.004), PWOOD, False, lambda c, n: SHADE if n.x > 0.5 else None)
    # corner posts on the built corner + a diagonal brace on the left wall
    K.add('Crate', bbox((-s / 2 + 0.03, s / 2 - 0.03, s / 2), (0.06, 0.06, s), 0.006), PJOINT, False)
    br = bm_tube([V((-s / 2 - 0.006, -s / 2 + 0.06, 0.06)), V((-s / 2 - 0.006, s / 2 - 0.06, s - 0.06))], 0.016, seg=4)
    K.add('Crate', br, PJOINT, False)
    # one front plank started (bottom), torn half-way along
    fp = CR.grid_box((0, -s / 2 + th / 2, s / 6), (s, th, s / 3 - 0.014), step=0.05)
    K.form('Crate', 'Lines', fp, lambda p: -0.02 - p.x + nval(p, 9.0, 101) * 0.06, PWOOD, thick=0.008, zig=0.012, seed=101, hatch=False, ink_r=0.006, smooth=False)
    # pencil edges of the missing faces (overshooting)
    K.add('Lines', CR.box_wire((0, 0, s / 2), (s, s, s), 0.007, 0.07, 102, skip=(0, 6)), PENCIL, False)
    for k in range(1, 3):
        z = s * k / 3
        K.add('Lines', line([V((-s / 2, -s / 2, z)), V((s / 2, -s / 2, z))], 0.004, 103 + k, over=0.04, taper=False), PENCIL, False)
        K.add('Lines', line([V((s / 2, -s / 2, z)), V((s / 2, s / 2, z))], 0.004, 105 + k, over=0.04, taper=False), PENCIL, False)
    K.add('Lines', line([V((s / 2 + 0.005, -s / 2 + 0.05, 0.05)), V((s / 2 + 0.005, s / 2 - 0.05, s - 0.05))], 0.004, 107, over=0.05, taper=False), PENCIL, False)
    # ink plank seams on the built walls
    for k in range(1, 3):
        z = s * k / 3
        K.add('Lines', line([V((-s / 2 + 0.03, s / 2 - th - 0.003, z)), V((s / 2, s / 2 - th - 0.003, z))], 0.005, 108 + k, taper=False), INK, False)
        K.add('Lines', line([V((-s / 2 - 0.004, -s / 2 + 0.02, z)), V((-s / 2 - 0.004, s / 2, z))], 0.005, 110 + k, taper=False), INK, False)
    K.add('Lines', CR.smudge(V((s / 2 + 0.01, 0.0, 0.4)), V((1, 0, 0)), 0.3, 0.2, seed=112, lift=0.0), SMUDGE, False)
    return K.finish(0.6, 'Creature crate 0.6 m: bottom, back and left walls built from separate planks (inside visible), one front plank '
                         'torn half-way; the front, right and lid exist only as pencil edges.')


def build_basket():
    K = Kit('Basket')
    prof = [(0.13, 0.0), (0.16, 0.06), (0.185, 0.14), (0.19, 0.2)]
    b = lathe_grid([(prof_r(prof, z), z) for z in [0.2 * i / 5 for i in range(6)]], seg=14)
    # the rim is not finished: the weave stops at a wandering height on the right side
    fld = lambda p: 0.2 - max(0.0, math.cos(math.atan2(p.y, p.x) - math.radians(20))) * 0.07 + nval(p, 12.0, 121) * 0.012 - p.z
    K.form('Basket', 'Lines', b, fld, PWOOD, thick=0.012, zig=0.008, seed=121, hatch_kw=dict(spacing=0.04, length=(0.03, 0.08), r=0.004, density=0.75), ink_r=0.006)
    K.add('Basket', bm_lathe([(0.0, 0.004), (0.13, 0.004)], seg=14, cap_top=False, cap_bottom=False), PWOOD, False)
    # weave: ink rings + diagonal ticks on the built part, pencil above the tear
    for z in (0.04, 0.08, 0.12, 0.16):
        ring = CR.ring_pts(0, 0, z, prof_r(prof, z) + 0.006, 24)
        K.add('Lines', CR.clipped_lines(ring, lambda p: fld(p) > 0.004, 0.006, 0.0, 122 + z * 10), INK, False)
    for i in range(0, 14, 2):
        a = 2 * math.pi * (i + 0.5) / 14
        for j, z in enumerate((0.06, 0.14)):
            p0 = V((math.cos(a) * (prof_r(prof, z - 0.03) + 0.006), math.sin(a) * (prof_r(prof, z - 0.03) + 0.006), z - 0.03))
            p1 = V((math.cos(a + 0.18) * (prof_r(prof, z + 0.03) + 0.006), math.sin(a + 0.18) * (prof_r(prof, z + 0.03) + 0.006), z + 0.03))
            if fld(p1) > 0:
                K.add('Lines', stroke([p0, p1], 0.005, seg=3, taper=False), INK, False)
    K.add('Lines', CR.ellipse((0, 0, 0.205), 0.19, 0.19, 0.0, turns=1.08, n=14, r=0.006, seed=125), PENCIL, False)
    # handle: built from the left rim to the top, then only a pencil arc down to the right rim
    hp = [V((-0.18, 0, 0.19)), V((-0.14, 0, 0.33)), V((-0.06, 0, 0.41)), V((0.0, 0, 0.42))]
    K.add('Basket', bm_tube(hp, [0.016, 0.015, 0.014, 0.012], seg=6), PWOOD)
    K.add('Lines', line([p + V((0, -0.016, 0)) for p in hp], 0.003, 126, taper=False), INK, False)
    K.add('Lines', line([V((0.0, 0, 0.42)), V((0.07, 0, 0.405)), V((0.14, 0, 0.33)), V((0.18, 0, 0.19))], 0.007, 127, over=0.04), PENCIL, False)
    K.add('Lines', line([V((0.01, 0.01, 0.43)), V((0.09, 0.01, 0.41)), V((0.16, 0.01, 0.31))], 0.005, 128, over=0.03), PENCIL, False)
    # human things picked up inside - fully finished, vivid
    K.add('Basket', bbox((0.03, 0.02, 0.15), (0.15, 0.11, 0.05), 0.008), 'M_BookRed', False)
    K.add('Basket', bbox((0.035, 0.02, 0.15), (0.13, 0.1, 0.035), 0.002), 'M_PageWhite', False)
    K.add('Basket', bm_tube([V((-0.08, -0.04, 0.12)), V((-0.02, 0.03, 0.27))], [0.008, 0.008], seg=5), 'M_Brass')
    K.add('Basket', bm_sphere((-0.085, -0.05, 0.11), (0.022, 0.015, 0.028), seg=6, rings=4), 'M_Brass')
    return K.finish(0.45, "Kinopio's gathering basket (0.42 m with handle): weave stops at a torn rim on the right, handle half built / "
                          "half a pencil arc. Inside: a red book and a brass spoon (human, finished). Hand point = handle top (local z 0.42).")


def build_lantern_hanging():
    K = Kit('Lantern_Hanging')
    W = 'M_StageWood'
    # plaza = finished: carved post on a stepped foot, a curled arm with a brace, the lamp hangs from a hook
    K.add('Post', bbox((0, 0, 0.07), (0.36, 0.36, 0.14), 0.03), 'M_TerracottaDark', False)
    K.add('Post', bbox((0, 0, 0.18), (0.26, 0.26, 0.1), 0.02), W, False)
    K.add('Post', bm_lathe([(0.075, 0.2), (0.06, 0.6), (0.05, 2.6), (0.06, 2.7), (0.045, 2.75)], seg=8), W, True)
    for z in (0.62, 2.58):
        K.add('Post', bm_lathe([(0.04, z - 0.03), (0.085, z), (0.04, z + 0.03)], seg=8, cap_top=False, cap_bottom=False), 'M_TerracottaDark', False)
    arm = [V((0, 0, 2.62)), V((0.05, 0, 2.86)), V((0.22, 0, 2.98)), V((0.45, 0, 3.0)), V((0.62, 0, 2.99))]
    K.add('Post', bm_tube(arm, [0.045, 0.04, 0.035, 0.03, 0.028], seg=6), W)
    K.add('Post', bm_tube([V((0.0, 0, 2.3)), V((0.12, 0, 2.6)), V((0.3, 0, 2.95))], [0.022, 0.02, 0.018], seg=5), W)
    curl = [V((0.62, 0, 2.99)), V((0.7, 0, 3.02)), V((0.73, 0, 3.08)), V((0.68, 0, 3.12)), V((0.63, 0, 3.08))]
    K.add('Post', bm_tube(curl, 0.018, seg=5), W)
    K.add('Lines', line([V((0.06, -0.075, 0.25)), V((0.05, -0.055, 2.55))], 0.007, 131, taper=False), INK, False)
    hook = V((0.6, 0, 2.98))
    piv = hook + V((0, 0, -0.25))
    K.add('Lamp', stroke([hook, hook + V((0, 0, -0.22))], 0.008, seg=4, taper=False), 'M_Iron', False)
    c = hook + V((0, 0, -0.5))
    # cage lantern: cap + glass + 4 frame bars + base, a small finial below
    K.add('Lamp', bm_lathe([(0.0, 0.2), (0.04, 0.2), (0.15, 0.13), (0.13, 0.11)], seg=8, center=c), 'M_TerracottaDark', False)
    K.add('Lamp', bm_lathe([(0.1, -0.13), (0.11, 0.0), (0.1, 0.11)], seg=8, center=c, cap_top=True, cap_bottom=True), 'M_LampGlow', False)
    for i in range(4):
        a = math.pi / 4 + i * math.pi / 2
        q = V((math.cos(a), math.sin(a), 0))
        K.add('Lamp', bm_tube([c + q * 0.105 + V((0, 0, -0.14)), c + q * 0.118 + V((0, 0, 0.0)), c + q * 0.105 + V((0, 0, 0.12))], 0.012, seg=4), 'M_TerracottaDark')
    K.add('Lamp', bm_lathe([(0.12, -0.16), (0.12, -0.13), (0.0, -0.13)], seg=8, center=c, cap_bottom=True), 'M_TerracottaDark', False)
    K.add('Lamp', bm_tube([c + V((0, 0, -0.16)), c + V((0, 0, -0.24))], [0.025, 0.004], seg=5), 'M_TerracottaDark')
    return K.finish(3.1, 'Plaza lamp (finished/painted): carved post on a stepped foot, curled arm with a brace, cage lantern hanging from a '
                         'hook. Lamp pivot = hook (swing). Glow at local (0.6, 2.48 up). Add a small warm point light there in Unity.',
                    pivots={'Lamp': tuple(piv)})


def build_banner_unfinished():
    K = Kit('Banner_Unfinished')
    H = 4.4
    K.add('Pole', bm_tube([V((0, 0, 0)), V((0, 0, H))], [0.05, 0.04], seg=6), 'M_StageWood')
    K.add('Pole', bm_sphere((0, 0, H + 0.06), (0.08,) * 3, seg=6, rings=4), 'M_TerracottaDark')
    K.add('Pole', bm_tube([V((0, 0, H - 0.15)), V((0.9, 0, H - 0.18))], [0.025, 0.02], seg=5), 'M_StageWood')
    K.add('Pole', bbox((0, 0, 0.08), (0.28, 0.28, 0.16), 0.02), 'M_TerracottaDark', False)
    # cloth: painted from the top, the brush stops mid-cloth; below that the cloth itself is not made yet (torn edge,
    # pencil outline + swallowtail continue)
    bm = bmesh.new()
    nx, nz = 8, 14
    w, hgt = 0.85, 2.3
    vs = []
    for j in range(nz + 1):
        row = []
        for i in range(nx + 1):
            x = 0.05 + w * i / nx
            z = H - 0.2 - hgt * j / nz
            y = 0.04 * math.sin(i * 1.3 + j * 0.7)
            if j == nz:
                z -= 0.18 * (1 - abs(i / nx - 0.5) * 2)
            row.append(bm.verts.new((x, y, z)))
        vs.append(row)
    for j in range(nz):
        for i in range(nx):
            bm.faces.new((vs[j][i], vs[j][i + 1], vs[j + 1][i + 1], vs[j + 1][i]))
    for f in bm.faces:
        if f.normal.y > 0:
            f.normal_flip()
    zc = H - 0.2 - hgt * 0.55
    zcut = H - 0.2 - hgt * 0.78
    fld = lambda p: p.z - zcut + nval(p, 5.0, 112) * 0.15 + (p.x - 0.4) * 0.25

    def paint(c, n):
        e = nval(c, 6, 3) * 0.2
        if c.z > zc + e:
            return 'M_CurtainRed' if c.z < H - 0.6 or c.x > 0.35 else 'M_BackdropNavy'
        return None
    K.form('Cloth', 'Cloth', bm, fld, 'M_Paper', paint=paint, thick=0.01, zig=0.03, seed=113,
           hatch_kw=dict(spacing=0.06, length=(0.1, 0.35), r=0.004, up_only=False, slant=10), smooth=False, ink_r=0.008)
    for k in range(5):
        x = 0.12 + 0.17 * k
        ln = random.Random(k).uniform(0.15, 0.45)
        K.add('Cloth', bm_blade([V((x, -0.05, zc + 0.05)), V((x + 0.01, -0.05, zc - ln * 0.5)), V((x, -0.05, zc - ln))], [0.035, 0.025, 0.004], thick=0.003, up=(0, -1, 0)), 'M_CurtainRed', False)
    # planned lower cloth: pencil outline down to the swallowtail
    K.add('Cloth', line([V((0.05, -0.04, zcut + 0.1)), V((0.05, -0.04, H - 0.2 - hgt)), V((0.475, -0.04, H - 0.2 - hgt - 0.18)), V((0.9, -0.04, H - 0.2 - hgt)), V((0.9, -0.04, zcut + 0.25))], 0.006, 114, 0.01, over=0.08), PENCIL, False)
    K.add('Cloth', line([V((0.05, -0.045, H - 0.2)), V((0.05, -0.045, zcut + 0.25))], 0.009, 115, taper=False), INK, False)
    K.add('Cloth', line([V((0.9, -0.045, H - 0.2)), V((0.9, -0.045, zcut + 0.4))], 0.008, 116, taper=False), INK, False)
    return K.finish(H, 'Banner near the plaza: top half painted red with a navy corner, the brush stops mid-cloth; below a torn edge the cloth '
                       'is not made yet - only its pencil outline and swallowtail. Cloth pivot = top edge (sway).',
                    pivots={'Cloth': (0.05, 0, H - 0.2)})


def build_rubble(variant):
    K = Kit(f'Rubble_{variant}')
    rnd = random.Random(120 + variant)
    n = 6 if variant == 1 else 9
    spread = 1.0 if variant == 1 else 1.6
    # broken paper-stone blocks (faceted, flat-cut) lying where a wall was; above them the wall's outline still stands in pencil
    for k in range(n):
        c = V((rnd.uniform(-1, 1) * spread, rnd.uniform(-1, 1) * spread * 0.6, 0))
        s = rnd.uniform(0.18, 0.42) * (1.4 if k == 0 else 1)
        b = bbox(c + V((0, 0, s * 0.35)), (s * 1.3, s, s * 0.7), 0.0)
        rot(b, 'Z', rnd.uniform(0, 90), c)
        rot(b, 'X', rnd.uniform(-20, 20), c)
        jitter(b, s * 0.12, 2, 120 + k)
        deform(b, lambda q: V((q.x, q.y, max(0.0, q.z))))
        K.add('Rubble', b, PAPER, False, lambda q, nn: SHADE if nn.x > 0.45 or nn.z < -0.2 else None)
    wl = spread * 1.6
    K.add('Lines', CR.box_wire((0, 0.1, 0.8), (wl, 0.4, 1.6), 0.006, 0.12, 125 + variant, skip=(1, 3, 5, 7)), PENCIL, False)
    for k in range(3):
        z = 0.4 * (k + 1)
        K.add('Lines', line([V((-wl / 2, -0.1, z)), V((wl / 2 * rnd.uniform(0.3, 0.9), -0.1, z))], 0.005, 126 + k, over=0.08, taper=False), PENCIL, False)
    for k in range(3):
        c = V((rnd.uniform(-1, 1) * spread, rnd.uniform(-1, 1) * spread * 0.6, 0.02))
        w = rnd.uniform(0.4, 0.7)
        pts = [c + V((-w / 2, 0, 0)), c + V((-w / 2, 0, w * 0.6)), c + V((w / 2, 0, w * 0.6)), c + V((w / 2, 0, 0.15))]
        K.add('Lines', line(pts, 0.009, 125 + k, 0.015, over=0.05), INK, False)
    K.add('Lines', CR.smudge(V((0.2, -0.12, 1.0)), V((0, -1, 0)), wl * 0.5, 0.5, seed=127 + variant, lift=0.0), SMUDGE, False)
    return K.finish(spread * 2, 'Paper-stone rubble; the wall it came from still stands as a pencil outline above it (with an erased smudge).')


def build_rubble_1():
    return build_rubble(1)


def build_rubble_2():
    return build_rubble(2)


def build_paint_pot():
    K = Kit('PaintPot')
    prof = [(0.16, 0.0), (0.19, 0.08), (0.2, 0.26), (0.22, 0.3)]
    b = lathe_grid([(prof_r(prof, z), z) for z in [0.3 * i / 6 for i in range(7)]], seg=14)
    # the pot wall is unfinished: it stops at a torn line, highest at the back; the rim is only a pencil ellipse
    fld = lambda p: 0.24 + math.sin(math.atan2(p.y, p.x)) * 0.05 + nval(p, 10.0, 131) * 0.015 - p.z
    paint = lambda c, n: RED if (c.z > 0.17 and nval(c, 14, 2) > -0.15) else None
    K.form('Pot', 'Lines', b, fld, PWOOD, paint=paint, thick=0.015, zig=0.01, seed=131, hatch_kw=dict(SMALL_HATCH), ink_r=0.007)
    K.add('Pot', bm_lathe([(0.0, 0.004), (0.16, 0.004)], seg=14, cap_top=False, cap_bottom=False), PWOOD, False)
    K.add('Pot', bm_lathe([(0.0, 0.17), (0.19, 0.17)], seg=14, cap_top=False, cap_bottom=False), RED, False)
    K.add('Lines', CR.ellipse((0, 0, 0.305), 0.22, 0.22, 0.0, turns=1.1, n=16, r=0.007, seed=132), PENCIL, False)
    K.add('Lines', CR.ellipse((0, 0, 0.285), 0.2, 0.2, 0.0, turns=1.05, n=16, r=0.005, seed=133), PENCIL, False)
    for k in range(4):
        a = 2 * math.pi * k / 4 + 0.4
        ln = 0.06 + 0.05 * (k % 2)
        p0 = V((math.cos(a) * 0.205, math.sin(a) * 0.205, 0.19))
        K.add('Pot', bm_blade([p0, p0 + V((math.cos(a) * 0.01, math.sin(a) * 0.01, -ln * 0.5)), p0 + V((math.cos(a) * 0.012, math.sin(a) * 0.012, -ln))], [0.025, 0.02, 0.004], thick=0.004, up=(math.cos(a), math.sin(a), 0)), RED, False)
    # brush leaning in the pot: lower half built, upper half pencil
    bp0, bp1 = V((0.05, 0.02, 0.1)), V((-0.14, -0.06, 0.66))
    mid = bp0.lerp(bp1, 0.55)
    K.add('Pot', bm_tube([bp0, mid], [0.014, 0.014], seg=6), PWOOD)
    K.add('Pot', bm_tube([bp0, bp0 + V((0.012, 0.005, -0.08))], [0.03, 0.005], seg=5), RED)
    for e in (-1, 1):
        q = V((0.012 * e, 0.0, 0.0))
        K.add('Lines', line([mid + q, bp1 + q], 0.006, 134 + e, over=0.04, taper=False), PENCIL, False)
    K.add('Lines', CR.ellipse(bp1, 0.016, 0.016, 0.0, turns=1.1, n=8, r=0.005, seed=136), PENCIL, False)
    K.add('Pot', CR.merge([bm_prism(jag_outline(0.18, 0.12, 9, seed=131, rough=0.3, cx=0.3, cy=-0.12), 0.0, 0.006)]), RED, False)
    return K.finish(0.7, "Creature paint pot (red) with a brush, for the 'prepare' pose. The pot wall stops at a torn line (rim = pencil), "
                         "the brush handle's upper half is pencil.")


def build_brush_big():
    K = Kit('Brush_Big')
    base = V((0, 0, -0.3))
    d = V((0.25, 0.35, 1.0)).normalized()
    top = base + d * 5.2
    ferr = base + d * 1.3
    # handle: built from the ferrule up to ~60 %, then torn; the rest only drawn (contours + rings + the end knob)
    pts = [ferr.lerp(top, t / 8) for t in range(9)]
    hb = bm_tube(pts, [0.17 - 0.04 * t / 8 for t in range(9)], seg=12, cap=False)
    for f in hb.faces:
        c = f.calc_center_median()
        axp = ferr + d * (c - ferr).dot(d)
        if (c - axp).dot(f.normal) < 0:
            f.normal_flip()
    hb.normal_update()
    tcut = 0.58
    fld = lambda p: tcut * 3.9 - (p - ferr).dot(d) + nval(p, 3.0, 141) * 0.25
    K.form('Handle', 'Lines', hb, fld, 'M_StageWood', thick=0.03, zig=0.04, seed=141, hatch_kw=dict(spacing=0.06, length=(0.12, 0.4), r=0.006, up_only=False))
    side = d.cross(V((0, 0, 1))).normalized()
    for e in (-1, 1):
        q0 = ferr.lerp(top, tcut - 0.05) + side * 0.15 * e
        K.add('Lines', line([q0, top + side * 0.13 * e], 0.008, 142 + e, 0.01, over=0.2, taper=False), PENCIL, False)
    for k, t in enumerate((0.75, 0.9)):
        c = ferr.lerp(top, t)
        K.add('Lines', CR.line([c + (side * math.cos(a) + d.cross(side) * math.sin(a)) * 0.14 for a in [2 * math.pi * i / 12 for i in range(14)]], 0.005, seed=143 + k), PENCIL, False)
    K.add('Lines', CR.line([top + d * 0.08 + (side * math.cos(a) + d.cross(side) * math.sin(a)) * 0.15 for a in [2 * math.pi * i / 12 for i in range(14)]], 0.006, seed=145), PENCIL, False)
    K.add('Handle', bm_tube([ferr - d * 0.05, ferr + d * 0.45], [0.26, 0.2], seg=12), 'M_TerracottaDark')
    for k in range(3):
        c = ferr + d * (0.15 + k * 0.12)
        K.add('Lines', CR.line([c + (side * math.cos(a) + d.cross(side) * math.sin(a)) * 0.24 for a in [2 * math.pi * i / 14 for i in range(15)]], 0.01, seed=146 + k, taper=False), INK, False)
    # bristles plunge into the ground; the visible part flares out
    K.add('Bristles', bm_tube([ferr, ferr - d * 0.6, base - d * 0.4], [0.26, 0.36, 0.2], seg=10), INK)
    K.add('InkPool', bm_prism(jag_outline(1.3, 0.9, 16, seed=141, rough=0.3), 0.0, 0.012), INK, smooth=False)
    rnd = random.Random(142)
    for k in range(7):
        a = 2 * math.pi * k / 7
        p0 = V((math.cos(a) * 1.2, math.sin(a) * 0.85, 0.01))
        p1 = p0 + V((math.cos(a) * rnd.uniform(0.6, 1.4), math.sin(a) * rnd.uniform(0.4, 1.0), 0))
        K.add('InkPool', stroke([p0, p0.lerp(p1, 0.5) + V((0.05, 0.05, 0)), p1], 0.02, seg=3), INK, smooth=False)
    return K.finish(5.5, "Relic: a giant drawing brush stuck in the ground, leaning ~20 deg, ink pooled around it. The handle is built only "
                         "~60 % up (torn, inside visible), the rest is pencil contour + rings + the end knob outline. Not a human object.")


# ===================================================================== FX
def build_fx_ink_ring():
    p = Part('Ring')
    bm = bmesh.new()
    uv = bm.loops.layers.uv.new('UVMap')
    n = 40
    rin, rout = 0.85, 1.0
    vi, vo = [], []
    for i in range(n):
        a = 2 * math.pi * i / n
        wob = 1 + 0.04 * math.sin(a * 5) + 0.03 * math.sin(a * 11 + 1)
        vi.append(bm.verts.new((math.cos(a) * rin * wob, math.sin(a) * rin * wob, 0.0)))
        vo.append(bm.verts.new((math.cos(a) * rout * wob * (1 + 0.04 * math.sin(a * 7)), math.sin(a) * rout * wob, 0.0)))
    for i in range(n):
        j = (i + 1) % n
        f = bm.faces.new((vi[i], vi[j], vo[j], vo[i]))
        for lp, (u, v) in zip(f.loops, ((i / n, 0), ((i + 1) / n, 0), ((i + 1) / n, 1), (i / n, 1))):
            lp[uv].uv = (u, v)
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    for f in bm.faces:
        if f.normal.z < 0:
            f.normal_flip()
    p.add(bm, INK, smooth=False)
    A = Asset('FX_InkRing')
    return fin(A, [(p, (0, 0, 0))], 2.0, 'Flat ink ring decal, outer radius 1 m, 0.15 m thick band; faces up. UV u = around, v = inner(0)->outer(1). Scale up and fade for pond ripples; lay 1-2 cm above the pond surface.')


def build_fx_splash():
    parts = []
    rnd = random.Random(151)
    base = Part('Base')
    base.add(bm_prism(jag_outline(1.0, 1.0, 18, seed=152, rough=0.35), 0.0, 0.02), INK, smooth=False)
    parts.append((base, (0, 0, 0)))
    crown = Part('Crown')
    for k in range(12):
        a = 2 * math.pi * k / 12 + rnd.uniform(-0.1, 0.1)
        d = V((math.cos(a), math.sin(a), 0))
        h = rnd.uniform(0.6, 1.3)
        p0 = d * 0.75
        pts = [p0, p0 + d * 0.15 + V((0, 0, h * 0.5)), p0 + d * 0.35 + V((0, 0, h))]
        crown.add(bm_blade(pts, [0.16, 0.1, 0.01], thick=0.03, up=tuple(d)), INK, smooth=False)
        crown.add(bm_sphere(pts[-1] + d * 0.06 + V((0, 0, 0.08)), (0.05,) * 3, seg=6, rings=4), INK)
    crown.add(bm_tube([V((math.cos(a) * 0.78, math.sin(a) * 0.78, 0.08)) for a in [2 * math.pi * i / 20 for i in range(21)]], 0.07, seg=4, cap=False), INK)
    parts.append((crown, (0, 0, 0)))
    for k in range(6):
        a = 2 * math.pi * k / 6 + 0.3
        c = V((math.cos(a) * rnd.uniform(1.2, 1.8), math.sin(a) * rnd.uniform(1.2, 1.8), rnd.uniform(1.0, 2.0)))
        dp = Part(f'Drop_{k + 1}')
        dr = bm_sphere((0, 0, 0), (0.09, 0.09, 0.14), seg=6, rings=4)
        deform(dr, lambda q: V((q.x * (1 - max(0, q.z) * 4), q.y * (1 - max(0, q.z) * 4), q.z)))
        move(dr, c)
        dp.add(dr, INK)
        parts.append((dp, tuple(c)))
    A = Asset('FX_Splash')
    return fin(A, parts, 3.0, 'Ink splash crown for the fish burst, radius ~1 m at scale 1 (scale to the pond). Separate pieces: Base (flat), Crown (rising spikes), Drop_1..6 (droplets, pivots at their centres for flinging).')


def build_fx_dust():
    parts = []
    rnd = random.Random(161)
    for k in range(4):
        p = Part(f'Card_{k + 1}')
        c = V((0, 0, 0))
        for j in range(2):   # two crossed jagged cards per puff
            pts = jag_outline(0.18 + 0.04 * k, 0.15 + 0.03 * k, 9, seed=162 + k * 2 + j, rough=0.35)
            b = bm_prism(pts, -0.004, 0.004, axis='Y')
            tri_ngons(b)
            rot(b, 'Z', 90 * j + rnd.uniform(-15, 15))
            p.add(b, 'M_PaperShade' if j else 'M_Paper', smooth=False)
        cc = V(((k - 1.5) * 0.6, 0, 0.25))
        for pc in p.pieces:
            move(pc[0], cc)
        parts.append((p, tuple(cc)))
    fl = Part('Flecks')
    for k in range(8):
        c = V((rnd.uniform(-1.2, 1.2), rnd.uniform(-0.3, 0.3), rnd.uniform(0.05, 0.6)))
        b = bm_prism(jag_outline(0.035, 0.025, 5, seed=170 + k, rough=0.3), -0.002, 0.002, axis='Y')
        rot(b, 'Z', rnd.uniform(0, 180))
        rot(b, 'X', rnd.uniform(-40, 40))
        move(b, c)
        fl.add(b, 'M_Paper', smooth=False)
    parts.append((fl, (0, 0, 0)))
    A = Asset('FX_Dust')
    return fin(A, parts, 1.0, 'Paper-dust puff cards: Card_1..4 (two crossed jagged paper cards each, pivots at their centres, use as particle meshes) + Flecks (tiny paper bits).')



ASSETS = [
    ('Sketch_Wall_1', build_sketch_wall_1), ('Sketch_Wall_2', build_sketch_wall_2), ('Sketch_Wall_3', build_sketch_wall_3),
    ('Sketch_Tree_1', build_sketch_tree_1), ('Sketch_Tree_2', build_sketch_tree_2), ('Sketch_Tree_3', build_sketch_tree_3),
    ('Sketch_Fence_1', build_sketch_fence_1), ('Sketch_Fence_2', build_sketch_fence_2), ('Sketch_Arch', build_sketch_arch),
    ('Scrap_Paper_1', build_scrap_paper_1), ('Scrap_Paper_2', build_scrap_paper_2), ('Scrap_Paper_3', build_scrap_paper_3),
    ('Stair_Sketch', build_stair_sketch), ('Bench_Puppet', build_bench_puppet), ('Barrel', build_barrel), ('Crate', build_crate),
    ('Basket', build_basket), ('Lantern_Hanging', build_lantern_hanging), ('Banner_Unfinished', build_banner_unfinished),
    ('Rubble_1', build_rubble_1), ('Rubble_2', build_rubble_2), ('PaintPot', build_paint_pot), ('Brush_Big', build_brush_big),
    ('FX_InkRing', build_fx_ink_ring), ('FX_Splash', build_fx_splash), ('FX_Dust', build_fx_dust),
]
