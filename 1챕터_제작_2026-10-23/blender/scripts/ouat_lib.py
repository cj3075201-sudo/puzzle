# -*- coding: utf-8 -*-
"""Once Under a Time - chapter 1 art kit: shared helpers (Blender 5.2, headless).

Conventions (see art/아트기준_1챕터.md):
  * Blender: Z up, character front = -Y, character's left = +X, 1 unit = 1 m.
  * FBX export with axis_forward='-Z', axis_up='Y', bake_space_transform=True,
    apply_scale_options='FBX_SCALE_ALL'  ->  Unity: Y up, front = +Z, scale 1, rotation 0.
    Mapping Blender (x, y, z) -> Unity (-x, z, -y).
  * Every asset = root Empty (origin at the feet / floor centre) + child mesh parts.
    Each part's origin is its joint, parts carry only a location (no rotation/scale).
  * Internal object names are "<Asset>|<Part>" so many assets can live in one .blend;
    they are renamed to the bare part name only while exporting.
"""
import bpy, bmesh, math, random, os, json
from mathutils import Vector, Matrix, noise

# ---------------------------------------------------------------- palette / materials
# name: (base hex, shade hex, outline, category, extra)
MATS = {
    # ---- world = white paper drawn in ink (unfinished). shade = grey-blue, hatched in shadow
    'M_Paper':        ('F1EEE6', 'C9CCCF', True,  'paper',   {'hatch': True, 'note': 'ground, walls, rocks, unpainted buildings'}),
    'M_PaperShade':   ('E2E0DA', '9EA3A8', True,  'paper',   {'hatch': True, 'note': 'cliff sides, wall feet, darker paper'}),
    'M_StoneDark':    ('A9AEB4', '7A8087', True,  'paper',   {'hatch': True, 'note': 'chasm depths, ceiling underside'}),
    'M_Spire':        ('AEB8C4', '8E98A6', False, 'paper',   {'hatch': True, 'note': 'background cone spires (far silhouettes)'}),
    'M_Ink':          ('2B2622', '2B2622', False, 'line',    {'note': 'ink line geometry: strokes, unfinished edges, hex paving lines, eyes. unlit flat, double-sided'}),
    'M_Hatch':        ('8A9099', '8A9099', False, 'line',    {'note': 'grey hatch strokes modelled on shadow sides. unlit flat, double-sided'}),
    'M_SketchLine':   ('2B2622', '2B2622', False, 'sketch',  {'alpha': 0.5, 'note': 'faint pencil construction lines. unlit, transparent, double-sided'}),
    'M_SketchNose':   ('2B2622', '2B2622', False, 'sketch',  {'alpha': 0.45, 'note': 'Kinopio nose = translucent pencil line. unlit, transparent, double-sided, no shadow'}),
    # ---- creatures = half-painted wooden puppets
    'M_PuppetWood':   ('E8C99A', 'C49C6C', True,  'paper',   {'note': 'bare wood of creature puppets (unpainted = creature-world paper category)'}),
    'M_PuppetJoint':  ('D8B584', 'AE8A5C', True,  'paper',   {'note': 'ball joints'}),
    'M_PaintRed':     ('C23A2E', '8E2A22', True,  'painted', {'note': 'brushed-on red paint, ragged edges (faces)'}),
    'M_PaintBlue':    ('5B86C9', '3D6198', True,  'painted', {'note': 'brushed-on blue paint, ragged edges (faces)'}),
    'M_Bark':         ('D9C3A0', 'A8957A', True,  'paper',   {'hatch': True, 'note': 'chief tree bark (pale, half-drawn)'}),
    'M_Leaf':         ('E4E3D6', 'A7B0AE', True,  'paper',   {'hatch': True, 'note': 'chief canopy, unpainted paper leaves'}),
    # ---- fully drawn (painted) world near the plaza
    'M_Terracotta':   ('C98A55', 'B5703F', True,  'painted', {'note': 'domed towers, painted houses'}),
    'M_TerracottaDark':('B5703F', '8C5230', True, 'painted', {'note': 'chimneys, dome caps, trims'}),
    'M_StageWood':    ('B07A48', '82552F', True,  'painted', {'note': 'stage boards, stairs, finished wood of the plaza'}),
    'M_CurtainRed':   ('C23A2E', '8A2820', True,  'painted', {}),
    'M_BackdropNavy': ('2C3E7A', '1E2B57', True,  'painted', {}),
    'M_LampGlow':     ('FFD27A', 'FFD27A', False, 'painted', {'emission': 1.0, 'note': 'warm lamp glass. unlit / emissive, put a small point light near'}),
    # ---- hero (from the human world above): the only fully coloured creature
    'M_Bluebird':     ('2F5FD0', '1F3F94', True,  'painted', {}),
    'M_BluebirdBelly':('D9DEE8', 'A9B1C0', True,  'painted', {}),
    'M_Beak':         ('2B2622', '17130F', True,  'painted', {'note': 'beak, legs, eye mask'}),
    'M_CapNavy':      ('26305A', '161C38', True,  'painted', {'note': 'hunting cap, short cape'}),
    'M_EyeShine':     ('FFFDF6', 'FFFDF6', False, 'painted', {'note': 'tiny eye highlight, unlit'}),
    # ---- human objects (vivid, original colours)
    'M_Brass':        ('C8902E', '8C6420', True,  'painted', {}),
    'M_Iron':         ('6E7681', '4A5059', True,  'painted', {}),
    'M_Rope':         ('C2452F', '8A2E20', True,  'painted', {}),
    'M_Wood':         ('A8763F', '74512B', True,  'painted', {'note': 'human-made wood (ladder, cart lock block, clock case)'}),
    'M_Leather':      ('7E5233', '563621', True,  'painted', {}),
    'M_BookRed':      ('C0392B', '8A2A20', True,  'painted', {}),
    'M_BookGreen':    ('3E8E4F', '2A6236', True,  'painted', {}),
    'M_BookBlue':     ('2E62B5', '1F447F', True,  'painted', {}),
    'M_PageWhite':    ('FBF6EA', 'E0D6BF', True,  'painted', {'note': 'human paper (book pages, Pinocchio page): warmer and brighter than the world paper'}),
    'M_Porcelain':    ('F7F4EE', 'C6CCD3', True,  'painted', {}),
    'M_Mark':         ('B5452F', '8A3020', False, 'painted', {'note': 'red mark stripe (Lump_2, Kinopio shoulder). Kinopio/Mark hidden by default'}),
    # ---- deep / dark
    'M_Fish':         ('243B3F', '152427', True,  'painted', {}),
    'M_FishMouth':    ('4A1E1E', '260F0F', True,  'painted', {}),
    'M_FishEye':      ('E9E2C8', 'E9E2C8', False, 'painted', {'emission': 0.6, 'note': 'pale eye, slight self-glow'}),
    'M_Silhouette':   ('141211', '0D0B0A', False, 'silhouette', {'note': 'non-talking villagers: flat black, unlit'}),
    'M_Pond':         ('0B0A09', '050404', False, 'silhouette', {'note': 'black pond surface, unlit flat black'}),
    'M_Light':        ('FFF4D6', 'FFF4D6', False, 'light',   {'alpha': 0.22, 'note': 'light shaft: unlit additive / transparent, no shadow, fade toward the top (UV v / object Y)'}),
}


def hex2rgb(h, linear=True):
    c = [int(h[i:i + 2], 16) / 255.0 for i in (0, 2, 4)]
    if linear:
        c = [x / 12.92 if x <= 0.04045 else ((x + 0.055) / 1.055) ** 2.4 for x in c]
    return c


def get_mat(name):
    """Plain material carrying the base colour (survives FBX as diffuse colour)."""
    m = bpy.data.materials.get(name)
    if m is None:
        m = bpy.data.materials.new(name)
        base = MATS[name][0]
        r, g, b = hex2rgb(base)
        m.diffuse_color = (r, g, b, 1.0)
        # node-based principled colour (5.x materials are node based by default)
        try:
            bsdf = m.node_tree.nodes.get('Principled BSDF')
            if bsdf:
                bsdf.inputs['Base Color'].default_value = (r, g, b, 1.0)
                bsdf.inputs['Roughness'].default_value = 1.0
        except Exception:
            pass
    return m


def write_material_json(path):
    out = {"_doc": "Once Under a Time ch1 toon material table. base/shade = sRGB hex. "
                   "categories: paper (unpainted world + bare-wood creatures; 'hatch': true = diagonal hand hatching in the shade band), "
                   "painted (fully drawn: hero, human objects, plaza/stage, terracotta towers), "
                   "line (ink/grey line geometry: unlit flat, double-sided, no outline), "
                   "silhouette (flat black unlit), sketch (translucent pencil line, unlit, double-sided), "
                   "light (additive unlit). outline = inverted-hull ink outline colour 2B2622, slightly irregular width.",
           "ink": "2B2622", "materials": {}}
    for k, (base, shade, ol, cat, extra) in MATS.items():
        d = {"base": base, "shade": shade, "outline": ol, "category": cat}
        d.update(extra)
        out["materials"][k] = d
    with open(path, 'w', encoding='utf-8') as f:
        json.dump(out, f, ensure_ascii=False, indent=2)


# ---------------------------------------------------------------- deterministic noise
def nvec(co, freq=1.0, seed=0.0):
    p = Vector((co.x * freq + seed * 17.3, co.y * freq - seed * 7.1, co.z * freq + seed * 3.7))
    return noise.noise_vector(p)


def nval(co, freq=1.0, seed=0.0):
    p = Vector((co.x * freq + seed * 17.3, co.y * freq - seed * 7.1, co.z * freq + seed * 3.7))
    return noise.noise(p)


# ---------------------------------------------------------------- primitive bmesh builders
# every builder returns a fresh bmesh in WORLD coordinates (pre-pivot)

def bm_sphere(center=(0, 0, 0), radii=(1, 1, 1), seg=12, rings=8):
    b = bmesh.new()
    bmesh.ops.create_uvsphere(b, u_segments=seg, v_segments=rings, radius=1.0)
    c = Vector(center)
    for v in b.verts:
        v.co = Vector((v.co.x * radii[0], v.co.y * radii[1], v.co.z * radii[2])) + c
    return b


def bm_box(center=(0, 0, 0), size=(1, 1, 1)):
    b = bmesh.new()
    bmesh.ops.create_cube(b, size=1.0)
    c = Vector(center)
    for v in b.verts:
        v.co = Vector((v.co.x * size[0], v.co.y * size[1], v.co.z * size[2])) + c
    return b


def bm_cyl(p0, p1, r0, r1=None, seg=8, cap=True):
    """Cylinder/cone between two points."""
    return bm_tube([p0, p1], [r0, r0 if r1 is None else r1], seg=seg, cap=cap)


def _frames(pts, up_hint=None):
    """Parallel-transport frames along a polyline. Returns list of (t, n, b)."""
    pts = [Vector(p) for p in pts]
    n = len(pts)
    tans = []
    for i in range(n):
        if i == 0:
            t = pts[1] - pts[0]
        elif i == n - 1:
            t = pts[-1] - pts[-2]
        else:
            t = (pts[i + 1] - pts[i]).normalized() + (pts[i] - pts[i - 1]).normalized()
        if t.length < 1e-9:
            t = Vector((0, 0, 1))
        tans.append(t.normalized())
    up = Vector(up_hint) if up_hint else Vector((0, 0, 1))
    if abs(tans[0].dot(up)) > 0.95:
        up = Vector((1, 0, 0)) if abs(tans[0].x) < 0.9 else Vector((0, 1, 0))
    nrm = (up - tans[0] * up.dot(tans[0])).normalized()
    frames = []
    for i in range(n):
        t = tans[i]
        if i > 0:
            nrm = (nrm - t * nrm.dot(t))
            if nrm.length < 1e-9:
                nrm = t.orthogonal()
            nrm.normalize()
        b = t.cross(nrm).normalized()
        frames.append((t, nrm, b))
    return frames


def bm_tube(pts, radii, seg=8, cap=True, flat=1.0, up=None, twist=0.0):
    """Sweep an (elliptical) ring along pts. radii: scalar list. flat scales the 'n' axis.
    up: hint for the flat axis direction."""
    b = bmesh.new()
    pts = [Vector(p) for p in pts]
    if not isinstance(radii, (list, tuple)):
        radii = [radii] * len(pts)
    fr = _frames(pts, up)
    rings = []
    for i, p in enumerate(pts):
        t, nn, bb = fr[i]
        r = radii[i]
        ring = []
        for k in range(seg):
            a = 2 * math.pi * k / seg + twist * i
            off = nn * (math.cos(a) * r * flat) + bb * (math.sin(a) * r)
            ring.append(b.verts.new(p + off))
        rings.append(ring)
    for i in range(len(rings) - 1):
        r0, r1 = rings[i], rings[i + 1]
        for k in range(seg):
            k2 = (k + 1) % seg
            b.faces.new((r0[k], r0[k2], r1[k2], r1[k]))
    if cap:
        if radii[0] > 1e-5:
            b.faces.new(list(reversed(rings[0])))
        if radii[-1] > 1e-5:
            b.faces.new(rings[-1])
    # collapse zero-radius ends
    bmesh.ops.remove_doubles(b, verts=b.verts, dist=1e-6)
    bmesh.ops.recalc_face_normals(b, faces=b.faces)
    return b


def bm_blade(pts, widths, thick=0.02, up=(0, 0, 1)):
    """Feather / leaf / fin: flat ellipse sweep (4 sides). widths along pts, thickness along 'up'."""
    b = bmesh.new()
    pts = [Vector(p) for p in pts]
    fr = _frames(pts, up)
    rings = []
    for i, p in enumerate(pts):
        t, nn, bb = fr[i]
        w = widths[i]
        th = thick * (0.3 + 0.7 * min(1.0, w / (max(widths) + 1e-9)))
        ring = [b.verts.new(p + bb * w), b.verts.new(p + nn * th), b.verts.new(p - bb * w), b.verts.new(p - nn * th)]
        rings.append(ring)
    for i in range(len(rings) - 1):
        r0, r1 = rings[i], rings[i + 1]
        for k in range(4):
            k2 = (k + 1) % 4
            b.faces.new((r0[k], r0[k2], r1[k2], r1[k]))
    b.faces.new(list(reversed(rings[0])))
    b.faces.new(rings[-1])
    bmesh.ops.remove_doubles(b, verts=b.verts, dist=1e-6)
    bmesh.ops.recalc_face_normals(b, faces=b.faces)
    return b


def bm_lathe(profile, seg=12, center=(0, 0, 0), sx=1.0, sy=1.0, cap_top=True, cap_bottom=True):
    """Revolve (r, z) profile around Z."""
    b = bmesh.new()
    c = Vector(center)
    rings = []
    for r, z in profile:
        ring = []
        for k in range(seg):
            a = 2 * math.pi * k / seg
            ring.append(b.verts.new(c + Vector((math.cos(a) * r * sx, math.sin(a) * r * sy, z))))
        rings.append(ring)
    for i in range(len(rings) - 1):
        for k in range(seg):
            k2 = (k + 1) % seg
            b.faces.new((rings[i][k], rings[i][k2], rings[i + 1][k2], rings[i + 1][k]))
    if cap_bottom and profile[0][0] > 1e-5:
        b.faces.new(list(reversed(rings[0])))
    if cap_top and profile[-1][0] > 1e-5:
        b.faces.new(rings[-1])
    bmesh.ops.remove_doubles(b, verts=b.verts, dist=1e-6)
    bmesh.ops.recalc_face_normals(b, faces=b.faces)
    return b


def bm_prism(outline2d, z0, z1, center=(0, 0, 0), axis='Z'):
    """Extrude a 2D polygon (list of (u,v)) between z0..z1. axis: extrusion axis."""
    b = bmesh.new()
    c = Vector(center)

    def P(u, v, w):
        if axis == 'Z':
            return c + Vector((u, v, w))
        if axis == 'Y':
            return c + Vector((u, w, v))
        return c + Vector((w, u, v))
    bot = [b.verts.new(P(u, v, z0)) for u, v in outline2d]
    top = [b.verts.new(P(u, v, z1)) for u, v in outline2d]
    n = len(outline2d)
    b.faces.new(list(reversed(bot)))
    b.faces.new(top)
    for i in range(n):
        j = (i + 1) % n
        b.faces.new((bot[i], bot[j], top[j], top[i]))
    bmesh.ops.recalc_face_normals(b, faces=b.faces)
    return b


def bm_plane_uv(center, size, normal='-Y'):
    """Quad with UV 0..1 (for 'Face' decal planes). normal: '-Y' (front), '+Z' (up)..."""
    b = bmesh.new()
    uv = b.loops.layers.uv.new('UVMap')
    w, h = size
    c = Vector(center)
    if normal == '-Y':
        cs = [c + Vector((-w / 2, 0, -h / 2)), c + Vector((w / 2, 0, -h / 2)), c + Vector((w / 2, 0, h / 2)), c + Vector((-w / 2, 0, h / 2))]
    elif normal == '+Z':
        cs = [c + Vector((-w / 2, -h / 2, 0)), c + Vector((w / 2, -h / 2, 0)), c + Vector((w / 2, h / 2, 0)), c + Vector((-w / 2, h / 2, 0))]
    else:
        raise ValueError(normal)
    vs = [b.verts.new(p) for p in cs]
    f = b.faces.new(vs)
    for loop, (u, v) in zip(f.loops, [(0, 0), (1, 0), (1, 1), (0, 1)]):
        loop[uv].uv = (u, v)
    return b


def stroke(pts, r=0.008, seg=3, taper=True):
    """Ink stroke: thin tube with tapered ends."""
    n = len(pts)
    if taper:
        radii = [r * (0.25 + 0.75 * math.sin(math.pi * (0.08 + 0.84 * i / max(1, n - 1)))) for i in range(n)]
    else:
        radii = [r] * n
    return bm_tube(pts, radii, seg=seg, cap=True)


def wobble_line(p0, p1, n=5, amp=0.02, seed=0.0, sag=0.0):
    p0, p1 = Vector(p0), Vector(p1)
    out = []
    for i in range(n):
        t = i / (n - 1)
        p = p0.lerp(p1, t)
        off = nvec(p, 3.0, seed) * amp * math.sin(math.pi * t)
        p = p + off + Vector((0, 0, -sag * math.sin(math.pi * t)))
        out.append(p)
    return out


# ---------------------------------------------------------------- bmesh ops on pieces
def xform(b, mat):
    bmesh.ops.transform(b, matrix=mat, verts=b.verts)
    return b


def rot(b, axis, deg, pivot=(0, 0, 0)):
    pv = Vector(pivot)
    m = Matrix.Translation(pv) @ Matrix.Rotation(math.radians(deg), 4, axis) @ Matrix.Translation(-pv)
    return xform(b, m)


def move(b, d):
    return xform(b, Matrix.Translation(Vector(d)))


def deform(b, fn):
    for v in b.verts:
        v.co = fn(v.co.copy())
    return b


def jitter(b, amp=0.01, freq=3.0, seed=0.0):
    for v in b.verts:
        v.co += nvec(v.co, freq, seed) * amp
    return b


def mirror_x(b):
    """Return a mirrored copy (x -> -x) with fixed normals."""
    me = bpy.data.meshes.new('tmp_m')
    b.to_mesh(me)
    c = bmesh.new()
    c.from_mesh(me)
    bpy.data.meshes.remove(me)
    for v in c.verts:
        v.co.x = -v.co.x
    bmesh.ops.reverse_faces(c, faces=c.faces)
    return c


def copy_bm(b):
    me = bpy.data.meshes.new('tmp_c')
    b.to_mesh(me)
    c = bmesh.new()
    c.from_mesh(me)
    bpy.data.meshes.remove(me)
    return c


def subdivide(b, levels=1, crease_all=False):
    """Catmull-Clark via a temporary object + Subsurf modifier. Returns new bmesh."""
    if levels <= 0:
        return b
    me = bpy.data.meshes.new('tmp_sub')
    b.to_mesh(me)
    ob = bpy.data.objects.new('tmp_sub', me)
    bpy.context.scene.collection.objects.link(ob)
    md = ob.modifiers.new('sub', 'SUBSURF')
    md.levels = levels
    md.render_levels = levels
    md.uv_smooth = 'PRESERVE_BOUNDARIES'
    dg = bpy.context.evaluated_depsgraph_get()
    ev = ob.evaluated_get(dg)
    m2 = bpy.data.meshes.new_from_object(ev)
    out = bmesh.new()
    out.from_mesh(m2)
    bpy.data.objects.remove(ob)
    bpy.data.meshes.remove(me)
    bpy.data.meshes.remove(m2)
    b.free()
    return out


def bevel(b, width=0.02, segments=1, angle=40.0):
    me = bpy.data.meshes.new('tmp_bev')
    b.to_mesh(me)
    ob = bpy.data.objects.new('tmp_bev', me)
    bpy.context.scene.collection.objects.link(ob)
    md = ob.modifiers.new('bev', 'BEVEL')
    md.width = width
    md.segments = segments
    md.limit_method = 'ANGLE'
    md.angle_limit = math.radians(angle)
    md.harden_normals = False
    dg = bpy.context.evaluated_depsgraph_get()
    m2 = bpy.data.meshes.new_from_object(ob.evaluated_get(dg))
    out = bmesh.new()
    out.from_mesh(m2)
    bpy.data.objects.remove(ob)
    bpy.data.meshes.remove(me)
    bpy.data.meshes.remove(m2)
    b.free()
    return out


def decimate(b, ratio=0.5):
    me = bpy.data.meshes.new('tmp_dec')
    b.to_mesh(me)
    ob = bpy.data.objects.new('tmp_dec', me)
    bpy.context.scene.collection.objects.link(ob)
    md = ob.modifiers.new('dec', 'DECIMATE')
    md.ratio = ratio
    dg = bpy.context.evaluated_depsgraph_get()
    m2 = bpy.data.meshes.new_from_object(ob.evaluated_get(dg))
    out = bmesh.new()
    out.from_mesh(m2)
    bpy.data.objects.remove(ob)
    bpy.data.meshes.remove(me)
    bpy.data.meshes.remove(m2)
    b.free()
    return out


# ---------------------------------------------------------------- parts / assets
class Part:
    """Accumulates bmesh pieces (each with a material + smooth flag), then becomes one object."""

    def __init__(self, name):
        self.name = name
        self.pieces = []  # (bmesh, matname, smooth, face_mat_fn)

    def add(self, b, mat, smooth=True, face_mat=None):
        """face_mat: optional fn(face_center, face_normal) -> matname or None (keep mat)."""
        self.pieces.append((b, mat, smooth, face_mat))
        return self


class Asset:
    def __init__(self, name, collection=None):
        self.name = name
        self.coll = bpy.data.collections.new(name)
        (collection or bpy.context.scene.collection).children.link(self.coll)
        self.root = bpy.data.objects.new(name, None)
        self.root.empty_display_type = 'ARROWS'
        self.root.empty_display_size = 0.3
        self.coll.objects.link(self.root)
        self.objs = {}  # part name -> object
        self.pivots = {name: Vector((0, 0, 0))}
        self.meta = {}

    def _link(self, ob, parent, pivot):
        pv = Vector(pivot)
        ppv = self.pivots[parent] if parent else Vector((0, 0, 0))
        pob = self.objs[parent] if parent else self.root
        ob.parent = pob
        ob.matrix_parent_inverse = Matrix.Identity(4)
        ob.location = pv - ppv

    def part(self, part, pivot=(0, 0, 0), parent=None, flat_angle=None):
        """Build object from Part. pivot in world coords. parent: part name or None(root).
        flat_angle: if set, sharp edges above this angle (deg) - for hard props."""
        bm = bmesh.new()
        mats = []
        uv_present = any(p[0].loops.layers.uv.active is not None for p in part.pieces)
        for b, mat, smooth, fmf in part.pieces:
            me = bpy.data.meshes.new('tmp_join')
            b.to_mesh(me)
            start = len(bm.faces)
            bm.from_mesh(me)
            bpy.data.meshes.remove(me)
            bm.faces.ensure_lookup_table()
            for i in range(start, len(bm.faces)):
                f = bm.faces[i]
                mname = mat
                if fmf is not None:
                    r = fmf(f.calc_center_median(), f.normal)
                    if r:
                        mname = r
                if mname not in mats:
                    mats.append(mname)
                f.material_index = mats.index(mname)
                f.smooth = smooth
            b.free()
        pv = Vector(pivot)
        for v in bm.verts:
            v.co -= pv
        me = bpy.data.meshes.new(f"{self.name}|{part.name}")
        bm.to_mesh(me)
        bm.free()
        for m in mats:
            me.materials.append(get_mat(m))
        if flat_angle is not None:
            # hard-surface: smooth shading with sharp edges by angle
            for p in me.polygons:
                p.use_smooth = True
            try:
                me.set_sharp_from_angle(angle=math.radians(flat_angle))
            except Exception:
                pass
        ob = bpy.data.objects.new(f"{self.name}|{part.name}", me)
        self.coll.objects.link(ob)
        self.pivots[part.name] = pv
        self.objs[part.name] = ob
        self._link(ob, parent, pv)
        return ob

    def empty(self, name, pivot, parent=None):
        ob = bpy.data.objects.new(f"{self.name}|{name}", None)
        ob.empty_display_size = 0.1
        self.coll.objects.link(ob)
        self.pivots[name] = Vector(pivot)
        self.objs[name] = ob
        self._link(ob, parent, Vector(pivot))
        return ob

    def tris(self):
        n = 0
        per = {}
        for k, ob in self.objs.items():
            if ob.type != 'MESH':
                continue
            t = sum(len(p.vertices) - 2 for p in ob.data.polygons)
            per[k] = t
            n += t
        return n, per

    def bounds(self):
        mn = Vector((1e9, 1e9, 1e9))
        mx = Vector((-1e9, -1e9, -1e9))
        bpy.context.view_layer.update()
        for ob in self.objs.values():
            if ob.type != 'MESH':
                continue
            for v in ob.data.vertices:
                w = ob.matrix_world @ v.co
                mn = Vector(map(min, mn, w))
                mx = Vector(map(max, mx, w))
        return mn, mx

    def scale_all(self, k):
        """Uniformly scale the finished asset (mesh data + part offsets), keeping transforms clean."""
        for nm, ob in self.objs.items():
            if ob.type == 'MESH':
                for v in ob.data.vertices:
                    v.co *= k
            ob.location *= k
            self.pivots[nm] = self.pivots[nm] * k

    def offset_all(self, d):
        """Move the whole asset relative to its root origin (shifts the direct children)."""
        d = Vector(d)
        for ob in self.root.children:
            ob.location += d
        for k in self.pivots:
            if k != self.name:
                self.pivots[k] = self.pivots[k] + d

    def all_objects(self):
        return [self.root] + list(self.root.children_recursive)


# ---------------------------------------------------------------- export
def bare_name(asset_name, internal):
    """Exported node name. A part named like its asset (e.g. Stage/Stage) becomes 'Main'."""
    nm = internal.split('|', 1)[1]
    return 'Main' if nm == asset_name else nm


def export_fbx(asset, path):
    objs = asset.all_objects()
    # temporarily rename to bare part names (unique within this asset)
    old = {}
    for ob in objs:
        if ob is asset.root:
            continue
        old[ob] = ob.name
    # move every other object with a clashing name out of the way first
    bare = {ob: bare_name(asset.name, ob.name) for ob in old}
    moved = []
    for ob, nm in bare.items():
        clash = bpy.data.objects.get(nm)
        if clash is not None and clash not in old:
            moved.append((clash, clash.name))
            clash.name = nm + '__tmp'
    for ob, nm in bare.items():
        ob.name = nm
    # Axis handling: the FBX exporter's 'bake_space_transform' breaks for hierarchies deeper than one level,
    # so we pre-convert instead: child data/locations go to Y-up space (C = Rx(-90): Blender (x,y,z) -> (x,z,-y))
    # and the root gets the inverse rotation. The exporter then applies C to the root only -> every node in the
    # FBX has rotation 0 and scale 1, Y up, character front (+Blender -Y) = FBX +Z = Unity +Z.
    C = Matrix.Rotation(math.radians(-90), 4, 'X')
    Ci = C.inverted()
    root_rot = asset.root.rotation_euler.copy()
    for ob in objs:
        if ob is asset.root:
            continue
        if ob.type == 'MESH':
            ob.data.transform(C)
        ob.location = C @ ob.location
    asset.root.rotation_euler = (math.radians(90), 0, 0)
    for ob in bpy.context.view_layer.objects:
        ob.select_set(False)
    for ob in objs:
        ob.select_set(True)
    bpy.context.view_layer.objects.active = asset.root
    root_loc = asset.root.location.copy()
    asset.root.location = (0, 0, 0)
    bpy.ops.export_scene.fbx(
        filepath=path, use_selection=True, object_types={'EMPTY', 'MESH'},
        global_scale=1.0, apply_unit_scale=True, apply_scale_options='FBX_SCALE_ALL',
        bake_space_transform=False, axis_forward='-Z', axis_up='Y',
        use_mesh_modifiers=True, mesh_smooth_type='FACE', use_mesh_edges=False, use_triangles=True,
        use_tspace=False, use_custom_props=False, add_leaf_bones=False,
        bake_anim=False, path_mode='STRIP', embed_textures=False, use_metadata=True)
    asset.root.location = root_loc
    asset.root.rotation_euler = root_rot
    for ob in objs:
        if ob is asset.root:
            continue
        if ob.type == 'MESH':
            ob.data.transform(Ci)
        ob.location = Ci @ ob.location
    for ob, nm in old.items():
        ob.name = nm
    for ob, nm in moved:
        ob.name = nm
    for ob in objs:
        ob.select_set(False)


def reset_scene():
    bpy.ops.wm.read_factory_settings(use_empty=True)
    sc = bpy.context.scene
    sc.unit_settings.system = 'METRIC'
    sc.unit_settings.scale_length = 1.0


# ---------------------------------------------------------------- paint helpers ("colour = completion")
def ragged(value_fn, threshold, mat, amp=0.08, freq=6.0, seed=0.0, else_mat=None):
    """face_mat factory: paint faces where value_fn(center) + noise > threshold with `mat`.
    The noise gives a brushed, broken edge. Use e.g. value_fn = lambda c: c.z for 'painted from the top down'."""
    def fn(c, n):
        v = value_fn(c) + nval(c, freq, seed) * amp
        if v > threshold:
            return mat
        return else_mat
    return fn


def chain(*fns):
    """Combine several face_mat functions: the first one that returns a material wins."""
    def fn(c, n):
        for f in fns:
            r = f(c, n)
            if r:
                return r
        return None
    return fn
