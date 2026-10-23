# -*- coding: utf-8 -*-
"""Craft kit for the 'half-drawn world' (10/23 rework of props + village).

A form is either BUILT (paper/painted shell with real thickness, torn where it stops) or only DRAWN
(pencil construction wire with overshooting corners, guide lines, hatching that keeps going past the
built edge into the air, erased smudges). Every asset mixes the two on purpose.

Blender coords: Z up, front -Y. All builders return bmesh in asset space.
"""
import math, random
import bmesh
from mathutils import Vector, Matrix
import ouat_lib as L
from ouat_lib import stroke, bm_tube, bm_lathe, bm_prism, nval, nvec, jitter, deform, move, rot

V = Vector
INK, PENCIL, HATCH, SMUDGE, BACK, FAINT = 'M_Ink', 'M_Pencil', 'M_Hatch', 'M_Smudge', 'M_PaperBack', 'M_SketchLine'

# --- materials owned by the craft kit (merged into art_materials.json by build_all) ---------------------
L.MATS.update({
    'M_Pencil':    ('474B52', '474B52', False, 'line',   {'note': 'graphite construction line (opaque, softer than ink): wireframe of the unbuilt part of a form, guide lines'}),
    # same values as ouat_slice (terrain) so both modules agree on the shared slots
    'M_Smudge':    ('5E5953', '5E5953', False, 'sketch', {'alpha': 0.16, 'note': 'erased graphite smudge decal (transparent, unlit, no shadow)'}),
    'M_TornEdge':  ('F4EFE3', 'D6D0C2', False, 'paper',  {'note': 'raw paper showing at torn / missing chunks (reads brighter than the drained drawing)'}),
    'M_PaperBack': ('A9A79F', '7C8086', True,  'paper',  {'hatch': True, 'note': 'inside / back face of a torn paper shell (darker than the outside paper)'}),
})


# ===================================================================== basic geometry
def merge(bms):
    out = bmesh.new()
    for b in bms:
        if b is None:
            continue
        me = L.bpy.data.meshes.new('tmp_cmerge')
        b.to_mesh(me)
        out.from_mesh(me)
        L.bpy.data.meshes.remove(me)
        b.free()
    return out


def copy(b):
    return L.copy_bm(b)


def tri_ngons(b):
    ng = [f for f in b.faces if len(f.verts) > 4]
    if ng:
        bmesh.ops.triangulate(b, faces=ng, quad_method='BEAUTY', ngon_method='EAR_CLIP')
    return b


def line(pts, r=0.012, over=0.0, seed=0.0, amp=0.0, taper=True):
    """Hand line along a polyline. over = overshoot past both ends (draughtsman corners)."""
    pts = [V(p) for p in pts]
    if len(pts) < 2:
        return None
    if amp > 0 and len(pts) > 2:
        pts = [pts[0]] + [p + nvec(p, 2.3, seed) * amp for p in pts[1:-1]] + [pts[-1]]
    if over > 0:
        d0 = (pts[0] - pts[1])
        d1 = (pts[-1] - pts[-2])
        if d0.length > 1e-6 and d1.length > 1e-6:
            pts[0] = pts[0] + d0.normalized() * over          # overshoot = extend the end points (no extra segments)
            pts[-1] = pts[-1] + d1.normalized() * over
    if len(pts) == 2 and taper:
        pts = [pts[0], pts[0].lerp(pts[1], 0.5), pts[1]]
    return stroke(pts, r, seg=3, taper=taper)


def dense(pts, step=0.25):
    """resample a polyline so long straight lines can wobble"""
    out = [V(pts[0])]
    for a, b in zip(pts[:-1], pts[1:]):
        a, b = V(a), V(b)
        n = max(1, int((b - a).length / step))
        for i in range(1, n + 1):
            out.append(a.lerp(b, i / n))
    return out


def grid_quad(o, u, v, nu, nv):
    """planar grid: origin o, edge vectors u, v (full length), nu x nv cells. Normal = u x v."""
    b = bmesh.new()
    o, u, v = V(o), V(u), V(v)
    vs = [[b.verts.new(o + u * (i / nu) + v * (j / nv)) for i in range(nu + 1)] for j in range(nv + 1)]
    for j in range(nv):
        for i in range(nu):
            b.faces.new((vs[j][i], vs[j][i + 1], vs[j + 1][i + 1], vs[j + 1][i]))
    return b


def grid_box(center, size, step=0.25, faces='xyzXYZ'):
    """Closed box made of grids (so it can be cut along a ragged line). faces: subset of x,X,y,Y,z,Z (-/+)."""
    c, s = V(center), V(size)
    h = s / 2
    n = lambda l: max(1, int(round(l / step)))
    parts = []
    X, Y, Z = V((s.x, 0, 0)), V((0, s.y, 0)), V((0, 0, s.z))
    if 'y' in faces:
        parts.append(grid_quad(c + V((-h.x, -h.y, -h.z)), X, Z, n(s.x), n(s.z)))
    if 'Y' in faces:
        parts.append(grid_quad(c + V((h.x, h.y, -h.z)), -X, Z, n(s.x), n(s.z)))
    if 'x' in faces:
        parts.append(grid_quad(c + V((-h.x, h.y, -h.z)), -Y, Z, n(s.y), n(s.z)))
    if 'X' in faces:
        parts.append(grid_quad(c + V((h.x, -h.y, -h.z)), Y, Z, n(s.y), n(s.z)))
    if 'z' in faces:
        parts.append(grid_quad(c + V((-h.x, h.y, -h.z)), X, -Y, n(s.x), n(s.y)))
    if 'Z' in faces:
        parts.append(grid_quad(c + V((-h.x, -h.y, h.z)), X, Y, n(s.x), n(s.y)))
    b = merge(parts)
    bmesh.ops.remove_doubles(b, verts=b.verts, dist=1e-5)
    return b


def drum_grid(cx, cy, z0, z1, r0, r1, seg=16, step=0.3, cap_top=False, cap_bottom=False):
    n = max(1, int(round((z1 - z0) / step)))
    prof = [(r0 + (r1 - r0) * i / n, z0 + (z1 - z0) * i / n) for i in range(n + 1)]
    b = bm_lathe(prof, seg=seg, center=(cx, cy, 0), cap_top=cap_top, cap_bottom=cap_bottom)
    tri_ngons(b)
    return b


def dome_grid(cx, cy, z0, r, hk=0.9, seg=16, rings=6, pinch=0.0):
    """Closed-top dome (pole vertex). pinch > 0 = onion tip."""
    prof = []
    for j in range(rings + 1):
        t = j / rings
        a = t * math.pi / 2
        rr = r * math.cos(a) * (1 - pinch * t * t * 0.6)
        prof.append((max(rr, 0.0), z0 + r * hk * math.sin(a) + pinch * r * t ** 3))
    b = bm_lathe(prof, seg=seg, center=(cx, cy, 0), cap_top=False, cap_bottom=False)
    tri_ngons(b)
    return b


# ===================================================================== cutting a form into built / drawn
class Cut:
    """Result of cutting a closed (or open) form with keep(c, n) -> bool per face.
    built: bmesh of kept faces (the paper shell), drawn: bmesh of removed faces (for wire),
    torn: list of (pts, normals, outs) chains along the edge between built and drawn."""

    def __init__(self, built, drawn, torn):
        self.built, self.drawn, self.torn = built, drawn, torn


def cut(b, keep, rag=0.05, seed=0.0):
    """Split mesh b in place into the built part (kept faces). Torn-edge verts wander along the surface
    (rag metres) so the edge reads as torn paper; the ink chain follows the same points."""
    b.faces.ensure_lookup_table()
    b.verts.ensure_lookup_table()
    k = {f.index: bool(keep(f.calc_center_median(), f.normal.copy())) for f in b.faces}
    drawn = copy(b)
    drawn.faces.ensure_lookup_table()
    bmesh.ops.delete(drawn, geom=[f for f in drawn.faces if k[f.index]], context='FACES')
    torn_edges = []
    vout, vnrm = {}, {}
    for e in b.edges:
        fs = e.link_faces
        if len(fs) == 2 and k[fs[0].index] != k[fs[1].index]:
            kf = fs[0] if k[fs[0].index] else fs[1]
            fc, fn = kf.calc_center_median(), kf.normal.copy()
            a, c = e.verts
            t = (c.co - a.co)
            t = t.normalized() if t.length > 1e-9 else V((1, 0, 0))
            mid = (a.co + c.co) / 2
            o = mid - fc
            o = o - fn * o.dot(fn)
            o = o - t * o.dot(t)
            o = o.normalized() if o.length > 1e-9 else V((0, 0, 1))
            for v in (a, c):
                vout[v.index] = vout.get(v.index, V((0, 0, 0))) + o
                vnrm[v.index] = vnrm.get(v.index, V((0, 0, 0))) + fn
            torn_edges.append((a.index, c.index))
    for vi in vout:
        vout[vi] = vout[vi].normalized() if vout[vi].length > 1e-9 else V((0, 0, 1))
        vnrm[vi] = vnrm[vi].normalized() if vnrm[vi].length > 1e-9 else V((0, 0, 1))
        v = b.verts[vi]
        v.co = v.co + vout[vi] * (nval(v.co, 6.0, seed) * rag + nval(v.co, 17.0, seed + 2) * rag * 0.35)
    pos = {v.index: v.co.copy() for v in b.verts}
    adj = {}
    for a, c in torn_edges:
        adj.setdefault(a, []).append(c)
        adj.setdefault(c, []).append(a)
    used = set()
    chains = []
    starts = [v for v in adj if len(adj[v]) != 2] + list(adj.keys())
    for s in starts:
        for nb in adj[s]:
            if frozenset((s, nb)) in used:
                continue
            ch = [s, nb]
            used.add(frozenset((s, nb)))
            while len(adj[ch[-1]]) == 2:
                cur, prev = ch[-1], ch[-2]
                nxt = [x for x in adj[cur] if x != prev]
                if not nxt or frozenset((cur, nxt[0])) in used:
                    break
                used.add(frozenset((cur, nxt[0])))
                ch.append(nxt[0])
            chains.append(([pos[i] for i in ch], [vnrm[i] for i in ch], [vout[i] for i in ch]))
    bmesh.ops.delete(b, geom=[f for f in b.faces if not k[f.index]], context='FACES')
    loose = [v for v in b.verts if not v.link_faces]
    if loose:
        bmesh.ops.delete(b, geom=loose, context='VERTS')
    return Cut(b, drawn, chains)


def shell_parts(built, thick=0.05, near=None, torn=None):
    """(back, rim): inside of the shell and the torn thickness rim as separate meshes
    (back = M_PaperBack, rim = M_TornEdge: the raw paper fibre of the tear)."""
    back = shell_back(built, thick, rim=False, near=near, torn=torn)
    built.verts.index_update()
    built.normal_update()
    nmap = {v.index: v.normal.copy() for v in built.verts}
    rimb = bmesh.new()
    for e in built.edges:
        if not e.is_boundary:
            continue
        a, c = e.verts
        vs = [rimb.verts.new(q) for q in (a.co.copy(), c.co.copy(), c.co - nmap[c.index] * thick, a.co - nmap[a.index] * thick)]
        f = rimb.faces.new(vs)
        fc = e.link_faces[0].calc_center_median()
        if (f.calc_center_median() - fc).dot(f.normal) < 0:
            f.normal_flip()
    return back, rimb


def shell_back(built, thick=0.05, rim=True, near=None, torn=None):
    """Inside of a paper shell: offset copy of the built faces, flipped, + rim along the torn edge.
    Returns bmesh (use BACK material)."""
    built.verts.index_update()
    built.normal_update()
    bb = copy(built)
    bb.verts.ensure_lookup_table()
    nmap = {v.index: v.normal.copy() for v in built.verts}
    built.verts.ensure_lookup_table()
    for v in bb.verts:
        v.co = v.co - nmap[v.index] * thick
    bmesh.ops.reverse_faces(bb, faces=bb.faces)
    if near is not None and torn:
        # closed forms: the inside is only visible through the tear -> keep back faces near the torn edge
        tp = [p for pts, _, _ in torn for p in pts[::2]]
        far = [f for f in bb.faces if min((f.calc_center_median() - q).length for q in tp) > near]
        bmesh.ops.delete(bb, geom=far, context='FACES')
    if rim:
        # rim quads along boundary edges of the original built mesh
        rimb = bmesh.new()
        for e in built.edges:
            if not e.is_boundary:
                continue
            a, c = e.verts
            p = [a.co.copy(), c.co.copy(), c.co - nmap[c.index] * thick, a.co - nmap[a.index] * thick]
            vs = [rimb.verts.new(q) for q in p]
            f = rimb.faces.new(vs)
            # orient outward (away from the face the edge belongs to)
            fc = e.link_faces[0].calc_center_median()
            if (f.calc_center_median() - fc).dot(f.normal) < 0:
                f.normal_flip()
        bb = merge([bb, rimb])
    return bb


def wire(b, angle=28.0, r=0.008, over=0.07, seed=0.0, amp=0.006, turn=40.0, only_boundary=False, min_len=0.05):
    """Pencil construction wire of a mesh: feature edges (angle) + open boundary, chained into strokes
    that overshoot their corners."""
    sel = []
    for e in b.edges:
        fs = e.link_faces
        if len(fs) == 1:
            sel.append(e)
        elif not only_boundary and len(fs) == 2 and fs[0].normal.angle(fs[1].normal, 0) > math.radians(angle):
            sel.append(e)
    return chain_strokes([(e.verts[0].co.copy(), e.verts[1].co.copy()) for e in sel], r, over, seed, amp, turn, min_len)


def chain_strokes(segs, r=0.008, over=0.07, seed=0.0, amp=0.006, turn=40.0, min_len=0.05):
    """segments [(a, b)] -> polylines broken at junctions / sharp turns -> strokes."""
    key = lambda p: (round(p.x, 4), round(p.y, 4), round(p.z, 4))
    adj, P = {}, {}
    for a, c in segs:
        ka, kc = key(a), key(c)
        if ka == kc:
            continue
        P[ka], P[kc] = a, c
        adj.setdefault(ka, set()).add(kc)
        adj.setdefault(kc, set()).add(ka)
    used = set()
    polys = []
    order = sorted(adj.keys(), key=lambda k: (len(adj[k]) == 2, k))
    for s in order:
        for nb in list(adj[s]):
            if frozenset((s, nb)) in used:
                continue
            ch = [s, nb]
            used.add(frozenset((s, nb)))
            while len(adj[ch[-1]]) == 2:
                cur, prev = ch[-1], ch[-2]
                nxt = [x for x in adj[cur] if x != prev][0]
                if frozenset((cur, nxt)) in used:
                    break
                d0 = (P[cur] - P[prev]).normalized()
                d1 = (P[nxt] - P[cur]).normalized()
                if d0.angle(d1, 0) > math.radians(turn):
                    break
                used.add(frozenset((cur, nxt)))
                ch.append(nxt)
            polys.append([P[k] for k in ch])
    out = []
    rnd = random.Random(int(seed * 131) + 7)
    for i, pl in enumerate(polys):
        ln = sum((b - a).length for a, b in zip(pl[:-1], pl[1:]))
        if ln < min_len:
            continue
        o = over * rnd.uniform(0.5, 1.4)
        out.append(line(pl, r * rnd.uniform(0.85, 1.15), over=o, seed=seed + i, amp=amp))
    return merge(out) if out else None


def torn_ink(cut_res, r=0.016, seed=0.0, lift=0.012):
    """dark ink line along the torn edge (slightly broken into pieces)"""
    out = []
    rnd = random.Random(int(seed * 17) + 3)
    for pts, nrm, outs in cut_res.torn:
        if len(pts) < 2:
            continue
        pp = [p + n * lift for p, n in zip(pts, nrm)]
        # break the line in 1-3 pieces with small gaps (a hand never draws a torn edge in one go)
        n = len(pp)
        cuts = sorted(rnd.sample(range(1, n), min(n - 1, rnd.randint(0, 2)))) if n > 3 else []
        prev = 0
        for c in cuts + [n]:
            seg = pp[prev:c + 1] if c < n else pp[prev:]
            if len(seg) >= 2:
                out.append(line(seg, r * rnd.uniform(0.8, 1.2), over=0.0, seed=seed + c, amp=0.0))
            prev = c + 1 if c < n else c
    return merge(out) if out else None


def torn_hatch(cut_res, spacing=0.15, length=(0.25, 0.75), slant=28.0, r=0.0065, density=0.85, seed=0.0,
               lift=0.02, up_only=True, fade=True):
    """Hatching that keeps going past the torn edge into the air (on the would-be surface)."""
    out = []
    rnd = random.Random(int(seed * 29) + 5)
    for pts, nrm, outs in cut_res.torn:
        if len(pts) < 2:
            continue
        # resample along the chain
        acc = 0.0
        for i in range(len(pts) - 1):
            a, b = pts[i], pts[i + 1]
            seg = (b - a).length
            if seg < 1e-6:
                continue
            t_dir = (b - a) / seg
            n, o = nrm[i], outs[i]
            if up_only and o.z < -0.3:
                continue
            k = acc
            while k < seg:
                if rnd.random() < density:
                    p = a + t_dir * k
                    ang = math.radians(slant + rnd.uniform(-6, 6))
                    d = (o * math.cos(ang) + t_dir * math.sin(ang)).normalized()
                    ln = rnd.uniform(*length)
                    st = p + n * lift - d * 0.04
                    out.append(stroke([st, st + d * ln], r * rnd.uniform(0.8, 1.2), seg=3, taper=False))
                k += spacing * rnd.uniform(0.7, 1.3)
            acc = k - seg
    return merge(out) if out else None


def smudge(p, n, w=0.5, h=0.3, seed=0.0, lift=0.03, up=(0, 0, 1)):
    """Erased graphite smudge: soft jagged card lying on a surface (normal n)."""
    rnd = random.Random(int(seed * 53) + 1)
    n = V(n).normalized()
    u = V(up).cross(n)
    if u.length < 1e-4:
        u = V((1, 0, 0)).cross(n)
    u.normalize()
    v = n.cross(u).normalized()
    b = bmesh.new()
    c = b.verts.new(V(p) + n * lift)
    ring = []
    k = 11
    for i in range(k):
        a = 2 * math.pi * i / k
        rr = rnd.uniform(0.65, 1.1)
        ring.append(b.verts.new(V(p) + n * lift + u * math.cos(a) * w * 0.5 * rr + v * math.sin(a) * h * 0.5 * rr))
    for i in range(k):
        b.faces.new((c, ring[i], ring[(i + 1) % k]))
    # a few eraser streaks across it
    out = [b]
    for j in range(3):
        y = rnd.uniform(-0.3, 0.3) * h
        a0 = V(p) + n * (lift + 0.004) + u * (-w * 0.45) + v * y
        a1 = V(p) + n * (lift + 0.004) + u * (w * 0.45) + v * (y + rnd.uniform(-0.1, 0.1) * h)
        out.append(stroke([a0, a0.lerp(a1, 0.5), a1], 0.006, seg=3))
    return merge(out)


def ellipse(c, rx, ry=None, z=0.0, turns=1.06, n=20, r=0.008, seed=0.0, wob=0.03, a0=0.0, tilt=None):
    """Loose freehand ellipse guide (slightly more than one turn, start/end don't meet)."""
    ry = rx if ry is None else ry
    rnd = random.Random(int(seed * 71) + 9)
    pts = []
    m = int(n * turns)
    for i in range(m + 1):
        a = a0 + 2 * math.pi * i / n
        k = 1 + wob * math.sin(a * 2 + seed) + rnd.uniform(-wob, wob) * 0.4
        pts.append(V((math.cos(a) * rx * k, math.sin(a) * ry * k, 0.0)))
    if tilt:
        M = Matrix.Rotation(math.radians(tilt[1]), 4, tilt[0])
        pts = [M @ q for q in pts]
    pts = [V(c) + V((0, 0, z)) + q for q in pts]
    return stroke(pts, r, seg=3, taper=True)


def arc(c, r_, a0, a1, z=0.0, n=12, r=0.008, plane='XY', seed=0.0):
    c = V(c)
    pts = []
    for i in range(n + 1):
        a = math.radians(a0 + (a1 - a0) * i / n)
        if plane == 'XY':
            pts.append(c + V((math.cos(a) * r_, math.sin(a) * r_, z)))
        else:  # XZ
            pts.append(c + V((math.cos(a) * r_, 0, math.sin(a) * r_ + z)))
    return line(pts, r, over=0.0, seed=seed)


def arch2d(w, h, n=7):
    r = w / 2.0
    sh = max(0.0, h - r)
    pts = [(-r, 0.0), (-r, sh)]
    for i in range(1, n):
        a = math.pi - math.pi * i / n
        pts.append((r * math.cos(a), sh + r * math.sin(a)))
    pts += [(r, sh), (r, 0.0)]
    return pts


def on_wall(pts2d, origin, u, n_out, lift=0.02):
    """2D (x, z) points onto a wall plane: origin, horizontal unit u, outward normal n_out."""
    o, u, n = V(origin), V(u).normalized(), V(n_out).normalized()
    return [o + u * x + V((0, 0, z)) + n * lift for x, z in pts2d]


def on_drum(pts2d, cx, cy, r, ang, lift=0.02):
    """2D (x along the arc, z) points wrapped onto a drum of radius r around angle ang (deg)."""
    out = []
    for x, z in pts2d:
        a = math.radians(ang) + x / r
        out.append(V((cx + math.cos(a) * (r + lift), cy + math.sin(a) * (r + lift), z)))
    return out


def sketched_window(pts_fn, w, h, z, seed=0.0, r=0.012, cross=True, hatch=True, double=True):
    """A window that is only sketched (not cut): doubled ink arch, pencil mullion cross, a few hatch lines inside.
    pts_fn(list of (x,z)) -> world points."""
    out = []
    ol = [(x, z + y) for x, y in arch2d(w, h, 7)]
    out.append(line(pts_fn(ol), r, over=0.05, seed=seed, amp=0.006))
    if double:
        ol2 = [(x * 1.12, z + y * 1.06 - 0.03) for x, y in arch2d(w, h, 7)]
        out.append(line(pts_fn(ol2), r * 0.6, over=0.09, seed=seed + 1, amp=0.01))
    if hatch:
        rnd = random.Random(int(seed * 7) + 2)
        for i in range(5):
            x0 = -w * 0.38 + w * 0.76 * i / 4
            a, b = (x0, z + h * 0.12 + rnd.uniform(0, 0.05)), (x0 + w * 0.18, z + h * 0.55 + rnd.uniform(0, 0.12))
            out.append(line(pts_fn([a, b]), r * 0.55, over=0.0, seed=seed + 3 + i))
    return merge(out)


def cut_window(pts_fn, w, h, z, depth_pts_fn, mat_dark='M_StoneDark', r=0.014, seed=0.0):
    """A real window: dark inset panel (prism) + ink arch. depth_pts_fn(list of (x,z), off) -> points pushed
    'off' metres into the wall. Returns (dark_bmesh, ink_bmesh)."""
    ol = [(x, z + y) for x, y in arch2d(w, h, 7)]
    b = bmesh.new()
    outer = [b.verts.new(p) for p in depth_pts_fn(ol, -0.005)]
    f = b.faces.new(outer)
    bmesh.ops.recalc_face_normals(b, faces=b.faces)
    tri_ngons(b)
    ink = line(pts_fn(ol), r, over=0.04, seed=seed, amp=0.004)
    return b, ink


def guides(pts_pairs, r=0.006, over=0.25, seed=0.0, mat=None):
    """Long straight construction lines (plumb, horizon, perspective) that run past the form."""
    out = [line([V(a), V(b)], r, over=over * random.Random(int(seed * 3) + i).uniform(0.6, 1.4), seed=seed + i) for i, (a, b) in enumerate(pts_pairs)]
    return merge(out)


def paint_ragged(thr, axis_fn=lambda c: c.z, amp=0.35, seed=0.0, mat='M_Terracotta', above=True, streak=0.6):
    """face_mat: paint faces on one side of a ragged threshold (two noise octaves = wandering edge + brush streaks)."""
    def fn(c, n):
        v = axis_fn(c) + L.nval(c, 1.1, seed) * amp + L.nval(c * V((3.0, 3.0, 0.4)), 2.7, seed + 7) * amp * streak
        return mat if ((v > thr) if above else (v < thr)) else None
    return fn


def paint_patch(center, radius, seed=0.0, mat='M_Terracotta', amp=0.35):
    """face_mat: a brushed patch of paint around a point (a painter testing colour)."""
    c0 = V(center)

    def fn(c, n):
        d = (c - c0).length + L.nval(c, 2.0, seed) * amp + L.nval(c, 6.0, seed + 3) * amp * 0.4
        return mat if d < radius else None
    return fn


def drips(pts_normals, mat, rnd, ln=(0.15, 0.6), w=0.05):
    """paint runs below a painted edge: list of (p, outward normal)."""
    out = []
    for p, n in pts_normals:
        l = rnd.uniform(*ln)
        n = V(n).normalized()
        out.append(L.bm_blade([p, p + V((0, 0, -l * 0.6)), p + V((0, 0, -l))], [w, w * 0.75, w * 0.15], thick=0.012, up=tuple(n)))
    return merge(out)


def scaffold(base_pts, height, r=0.01, ties=(0.35, 0.7, 1.0), seed=0.0, lean=0.04):
    """Scaffold-like guide poles (pencil) standing around a form, tied by horizontal lines."""
    rnd = random.Random(int(seed * 11) + 4)
    out = []
    tops = []
    for i, p in enumerate(base_pts):
        p = V(p)
        h = height * rnd.uniform(0.92, 1.08)
        t = p + V((rnd.uniform(-lean, lean), rnd.uniform(-lean, lean), h))
        out.append(line([p, t], r, over=0.2, seed=seed + i, amp=0.0, taper=False))
        tops.append((p, t))
    for k in ties:
        pts = [a.lerp(b, k) for a, b in tops]
        for i in range(len(pts) - 1):
            out.append(line([pts[i], pts[i + 1]], r * 0.8, over=0.18, seed=seed + 20 + i, taper=False))
    return merge(out)


def place(b, pos, yaw_deg):
    """front (-Y) turned to yaw (deg around Z), then moved."""
    rot(b, 'Z', yaw_deg)
    move(b, pos)
    return b


def orient_out(b, axis_c=None, center=None):
    """Make faces point away from a vertical axis (axis_c=(x, y)) or from a point (center)."""
    for f in b.faces:
        c = f.calc_center_median()
        if axis_c is not None:
            d = V((c.x - axis_c[0], c.y - axis_c[1], 0))
        else:
            d = c - V(center)
        if d.length > 1e-6 and d.dot(f.normal) < 0:
            f.normal_flip()
    b.normal_update()
    return b


def clip(pts, pred):
    """runs of a polyline where pred(p) is true -> list of polylines"""
    runs, cur = [], []
    for p in pts:
        if pred(p):
            cur.append(p)
        else:
            if len(cur) > 1:
                runs.append(cur)
            cur = []
    if len(cur) > 1:
        runs.append(cur)
    return runs


def clipped_lines(pts, pred, r=0.008, over=0.06, seed=0.0, amp=0.0):
    return merge([line(run, r, over=over, seed=seed + i, amp=amp) for i, run in enumerate(clip([V(p) for p in pts], pred))])


def wire_drawn(full, keep, angle=28.0, r=0.008, over=0.08, seed=0.0, amp=0.006, turn=40.0):
    """Pencil wire for the part of a form that is NOT built: feature edges whose faces are all unbuilt."""
    segs = []
    for e in full.edges:
        fs = e.link_faces
        if not fs or any(keep(f.calc_center_median(), f.normal) for f in fs):
            continue
        if len(fs) == 1 or fs[0].normal.angle(fs[1].normal, 0) > math.radians(angle):
            segs.append((e.verts[0].co.copy(), e.verts[1].co.copy()))
    return chain_strokes(segs, r, over, seed, amp, turn)


def ring_pts(cx, cy, z, r, n=32, a0=0.0, a1=360.0, lift=0.0):
    return [V((cx + math.cos(math.radians(a0 + (a1 - a0) * i / n)) * (r + lift),
               cy + math.sin(math.radians(a0 + (a1 - a0) * i / n)) * (r + lift), z)) for i in range(n + 1)]


def box_wire(center, size, r=0.008, over=0.08, seed=0.0, rot_z=0.0, skip=()):
    """12 edges of a box as overshooting pencil lines (a box that is only drawn)."""
    c, s = V(center), V(size) / 2
    M = Matrix.Rotation(math.radians(rot_z), 3, 'Z')
    P = lambda x, y, z: c + M @ V((x * s.x, y * s.y, z * s.z))
    E = []
    for y in (-1, 1):
        for z in (-1, 1):
            E.append((P(-1, y, z), P(1, y, z)))
    for x in (-1, 1):
        for z in (-1, 1):
            E.append((P(x, -1, z), P(x, 1, z)))
    for x in (-1, 1):
        for y in (-1, 1):
            E.append((P(x, y, -1), P(x, y, 1)))
    E = [e for i, e in enumerate(E) if i not in skip]
    rnd = random.Random(int(seed * 13) + 1)
    return merge([line([a, b], r * rnd.uniform(0.8, 1.2), over=over * rnd.uniform(0.5, 1.5), seed=seed + i, taper=False) for i, (a, b) in enumerate(E)])


def split_part_mats(part_solid, part_lines, b, mat, smooth=True, face_mat=None):
    """add to the right part depending on material category (lines never in the collider part)."""
    cat = L.MATS.get(mat, ('', '', False, 'paper'))[3]
    (part_lines if cat in ('line', 'sketch') else part_solid).add(b, mat, smooth=smooth, face_mat=face_mat)


def cut_field(b, field, zig=0.035, seed=0.0, drawn=False):
    """Contour cut: keep the part of the (triangulated) surface where field(p) > 0. The torn edge follows the
    zero level of the field exactly (no grid staircase); zig adds small alternating tear teeth along it.
    Returns Cut(built, drawn_or_None, torn_chains)."""
    bmesh.ops.triangulate(b, faces=b.faces[:], quad_method='BEAUTY', ngon_method='BEAUTY')
    vals = {v.index: field(v.co) for v in b.verts}
    pos_polys, neg_polys, segs = [], [], []
    for f in b.faces:
        vs = [v for v in f.verts]
        P = [v.co.copy() for v in vs]
        F = [vals[v.index] for v in vs]
        if all(x > 0 for x in F):
            pos_polys.append(P)
            continue
        if all(x <= 0 for x in F):
            neg_polys.append(P)
            continue
        pp, nn, cut_pts = [], [], []
        for i in range(3):
            a, c = P[i], P[(i + 1) % 3]
            fa, fc = F[i], F[(i + 1) % 3]
            (pp if fa > 0 else nn).append(a)
            if (fa > 0) != (fc > 0):
                t = fa / (fa - fc)
                q = a.lerp(c, t)
                pp.append(q); nn.append(q)
                cut_pts.append(q)
        if len(pp) >= 3:
            pos_polys.append(pp)
        if len(nn) >= 3:
            neg_polys.append(nn)
        if len(cut_pts) == 2:
            pin = sum((P[i] for i in range(3) if F[i] > 0), V((0, 0, 0))) / max(1, sum(1 for x in F if x > 0))
            pout = sum((P[i] for i in range(3) if F[i] <= 0), V((0, 0, 0))) / max(1, sum(1 for x in F if x <= 0))
            segs.append((cut_pts[0], cut_pts[1], f.normal.copy(), pout - pin))

    def build(polys):
        nb = bmesh.new()
        for poly in polys:
            try:
                nb.faces.new([nb.verts.new(p) for p in poly])
            except ValueError:
                pass
        bmesh.ops.remove_doubles(nb, verts=nb.verts, dist=1e-5)
        tri_ngons(nb)
        return nb
    built = build(pos_polys)
    # restore outward orientation from the source faces
    built.normal_update()
    dr = build(neg_polys) if drawn else None
    # zigzag tear teeth on the boundary
    key = lambda p: (round(p.x, 4), round(p.y, 4), round(p.z, 4))
    outd, nrmd = {}, {}
    for a, c, n, o in segs:
        t = (c - a)
        t = t.normalized() if t.length > 1e-9 else V((1, 0, 0))
        o = o - n * o.dot(n)
        o = o - t * o.dot(t)
        o = o.normalized() if o.length > 1e-9 else V((0, 0, 1))
        for p in (a, c):
            k = key(p)
            outd[k] = outd.get(k, V((0, 0, 0))) + o
            nrmd[k] = nrmd.get(k, V((0, 0, 0))) + n
    disp = {}
    rnd = random.Random(int(seed * 101) + 13)
    for k in outd:
        o = outd[k].normalized() if outd[k].length > 1e-9 else V((0, 0, 1))
        outd[k] = o
        nrmd[k] = nrmd[k].normalized() if nrmd[k].length > 1e-9 else V((0, 0, 1))
        p = V(k)
        disp[k] = o * (zig * (rnd.random() * 1.6 - 0.5) + nval(p, 9.0, seed) * zig * 0.6)
    for v in built.verts:
        k = key(v.co)
        if k in disp:
            v.co += disp[k]
    # chains
    segs2 = [(V(key(a)), V(key(c))) for a, c, n, o in segs]
    adj, P = {}, {}
    for a, c in segs2:
        ka, kc = key(a), key(c)
        if ka == kc:
            continue
        P[ka], P[kc] = a, c
        adj.setdefault(ka, set()).add(kc)
        adj.setdefault(kc, set()).add(ka)
    used, chains = set(), []
    for s in sorted(adj, key=lambda k: len(adj[k]) == 2):
        for nb_ in list(adj[s]):
            if frozenset((s, nb_)) in used:
                continue
            ch = [s, nb_]
            used.add(frozenset((s, nb_)))
            while len(adj[ch[-1]]) == 2:
                cur, prev = ch[-1], ch[-2]
                nxt = [x for x in adj[cur] if x != prev]
                if not nxt or frozenset((cur, nxt[0])) in used:
                    break
                used.add(frozenset((cur, nxt[0])))
                ch.append(nxt[0])
            chains.append(([P[k] + disp.get(k, V((0, 0, 0))) for k in ch], [nrmd.get(k, V((0, 0, 1))) for k in ch], [outd.get(k, V((0, 0, 1))) for k in ch]))
    b.free()
    return Cut(built, dr, chains)


def hatch2(a, b, r):
    return stroke([V(a), V(b)], r, seg=3, taper=False)
