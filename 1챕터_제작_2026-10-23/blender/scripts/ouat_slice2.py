# -*- coding: utf-8 -*-
"""Slice 2 (10/23): the remaining chapter-1 pages rebuilt as composed dioramas, same language as ouat_slice (slice 1):
a_plaza (꼭두 광장), a_alley (삐걱의자 골목), a_hideout (키노피오의 비밀 굴, NEW), a_cart (수레 길 · 수거꾼 창고),
a_field (기적의 밭 · 먹물 웅덩이).  Everything = UNITY world (x, z, y-up); a_fall / a_gate (slice 1) are untouched.

Height / light logic (continues slice 1 down the east axis, away from the only bright place):
    fall hill 5.5 (light) -> gate 2.5 -> plaza 0 (the most painted, warm lamps) -> alley 0 / hideout -0.4 (warm, hidden)
    -> depot -2.5 -> field -2.5 -> pond apron -3.1 (darkest, black ink)
Every page stands on drawn plateaus over the same abyss (FLOOR -16) and looks at the next destination.

Parts per area (under Area_<id>):  Ground_Walk_<s> / Margin_<s> / Ground_Lines_<s> / Cliffs_<s> / Exit_<s>_<t> / Vista_<s>
  + Decor_<s>   (NEW: painted canopies, roofs, crowns, high frames - no collider, casts shadow; keeps raycasts off props)
  + Light_<s>   (light pools / thin beams, as Light_fall)
  + Bell_plaza (pivot = hanging point, swing local X), Satchel_cart (pivot = bag centre), Face_hideout (UV 0..1 drawing)
"""
import math, random, json, os
import bmesh
from mathutils import Vector
import ouat_lib as L
import ouat_level as LV
from ouat_lib import Part
import ouat_craft  # noqa: F401  (registers M_Pencil, M_PaperBack, M_TornEdge, M_Smudge in L.MATS)
import ouat_slice as SL
from ouat_slice import (V, B, ccw, inside, poly_dist, jag, jag_poly, fill, grid_pts, stroke3, ground_stroke, shaded,
                        hatch_face, walls, rock, box, hex_lines, cracks, pennant, arrow, wire_loop, hexp, cairn, rock_wire,
                        wire_tiers, unfinished_house, torn_hole, smudge, guide, compass, ticks_along, light_pool, beam, dust,
                        cave, vista_spires, riser, strip_poly, exit_marker, add_face, FLOOR)

HERE = os.path.dirname(os.path.abspath(__file__))
ART = os.path.dirname(HERE)
RAD = math.radians
L.MATS.update({
    'M_FieldSoil': ('9C8F7C', '6E6457', False, 'paper', {'note': 'slice 2: dark turned soil of the field beds (the furrows that all run to the pond). Ground_Lines, no shadow'}),
})

# ============================================================================================ heights
YP = 0.0       # plaza
YA = 0.0       # alley lane (same plateau as the plaza, a side street)
YH = -0.4      # hideout floor (sunken root hollow)
YC = -2.5      # depot yard
YF = -2.5      # field
YS = -2.8      # pond steps
YO = -3.1      # pond apron (the stage round the pond)
YPOND = -3.16  # black ink surface (walkable, 'dried ink'); Pond.fbx Surface sits on it


def fwd(yaw):
    return V((math.sin(RAD(yaw)), math.cos(RAD(yaw))))


def side(yaw):
    """Unity local +X of an object with this yaw, in world xz."""
    return V((math.cos(RAD(yaw)), -math.sin(RAD(yaw))))


def r2(v):
    return [round(float(x), 2) for x in v]


# ============================================================================================ kit
class Kit2(SL.Kit):
    EXTRA = ('terra_r', 'terrad_r', 'swood', 'curt', 'navy_r', 'pst1', 'pst2', 'pst3', 'painted', 'earth', 'pond', 'pwood',
             'bark', 'paperback', 'iron', 'brass', 'leather', 'rope', 'puppet', 'green', 'sack', 'earthwalk', 'soil')

    def __init__(self):
        super().__init__()
        for n in self.EXTRA:
            setattr(self, n, bmesh.new())


MAP = {'walk': 'M_UnderGround', 'road': 'M_UnderRoad', 'margin': 'M_UnderGround', 'solid': 'M_UnderCliff', 'ink': 'M_Ink',
       'hatch': 'M_HatchDark', 'sketch': 'M_SketchLine', 'beam': 'M_Beam', 'paint': 'M_PaintBlue', 'paintr': 'M_PaintRed',
       'dark': 'M_UnderDeep', 'wood': 'M_Wood', 'terra': 'M_Terracotta', 'terrad': 'M_TerracottaDark', 'stage': 'M_StageWood',
       'curtain': 'M_CurtainRed', 'navy': 'M_BackdropNavy', 'glow': 'M_LampGlow', 'plaza': 'M_GroundPainted',
       'stones': 'M_PlazaStone2', 'spire': 'M_UnderSpire', 'lower': 'M_UnderLow', 'abyss': 'M_Abyss', 'cave': 'M_CaveWall',
       'torn': 'M_TornEdge', 'smudge': 'M_Smudge', 'pool': 'M_LightPool', 'dust': 'M_Dust',
       'terra_r': 'M_Terracotta', 'terrad_r': 'M_TerracottaDark', 'swood': 'M_StageWood', 'curt': 'M_CurtainRed',
       'navy_r': 'M_BackdropNavy', 'pst1': 'M_PlazaStone1', 'pst2': 'M_PlazaStone2', 'pst3': 'M_PlazaStone3',
       'painted': 'M_GroundPainted', 'earth': 'M_GroundEarth', 'pond': 'M_Pond', 'pwood': 'M_PuppetWood', 'bark': 'M_Bark',
       'paperback': 'M_PaperBack', 'iron': 'M_Iron', 'brass': 'M_Brass', 'leather': 'M_Leather', 'rope': 'M_Rope',
       'puppet': 'M_PuppetJoint', 'green': 'M_BookGreen', 'sack': 'M_PaperBack', 'earthwalk': 'M_GroundEarth', 'soil': 'M_FieldSoil'}
VISTA_MAP = {'walk': 'M_VistaGround', 'margin': 'M_VistaGround', 'road': 'M_VistaGround', 'solid': 'M_VistaCliff',
             'terra': 'M_VistaTerracotta', 'terrad': 'M_VistaTerraDark', 'stage': 'M_VistaWood', 'curtain': 'M_VistaCurtain',
             'navy': 'M_VistaNavy', 'plaza': 'M_VistaPlaza', 'stones': 'M_VistaStone', 'terra_r': 'M_VistaTerracotta',
             'terrad_r': 'M_VistaTerraDark', 'swood': 'M_VistaWood', 'curt': 'M_VistaCurtain', 'navy_r': 'M_VistaNavy',
             'painted': 'M_VistaPlaza', 'pst1': 'M_VistaStone', 'pst2': 'M_VistaStone', 'pst3': 'M_VistaStone', 'earth': 'M_VistaGround',
             'bark': 'M_VistaCliff', 'paperback': 'M_VistaCliff', 'pwood': 'M_VistaWood'}
ALL_KEYS = ('walk', 'painted', 'pond', 'earthwalk', 'sack', 'soil', 'margin', 'road', 'earth', 'pst1', 'pst2', 'pst3', 'stones', 'plaza', 'solid', 'dark', 'torn',
            'lower', 'abyss', 'terra', 'terrad', 'terra_r', 'terrad_r', 'stage', 'swood', 'curtain', 'curt', 'navy', 'navy_r', 'glow',
            'paint', 'paintr', 'wood', 'pwood', 'bark', 'paperback', 'iron', 'brass', 'leather', 'rope', 'puppet', 'green',
            'spire', 'cave', 'ink', 'hatch', 'sketch', 'smudge', 'books', 'pool', 'beam', 'dust')


def to_part(part, k, which, vista=False, top='M_UnderGround'):
    m = dict(MAP)
    if vista:
        m.update(VISTA_MAP)
    for w in which:
        if w == 'books':
            for mn, bm in k.books.items():
                if len(bm.faces):
                    part.add(bm, mn, smooth=False)
            continue
        bm = getattr(k, w)
        if len(bm.faces) == 0:
            continue
        fm = None
        if w == 'solid':
            tm = 'M_VistaGround' if vista else top
            fm = lambda c, n, tm=tm: tm if n.z > 0.7 else None
        part.add(bm, m[w], smooth=False, face_mat=fm)


WALK_KEYS = ('walk', 'painted', 'pond', 'earthwalk')
LINE_KEYS = ('road', 'earth', 'soil', 'pst1', 'pst2', 'pst3', 'ink', 'hatch', 'sketch', 'smudge', 'paintr', 'paint')
CLIFF_KEYS = ('solid', 'dark', 'torn', 'terra', 'terrad', 'terra_r', 'terrad_r', 'stage', 'swood', 'curtain', 'curt', 'navy',
              'navy_r', 'glow', 'wood', 'pwood', 'bark', 'paperback', 'iron', 'brass', 'leather', 'rope', 'puppet', 'green', 'sack', 'books')


# ============================================================================================ generic builders
def tri_count(bm):
    return sum(len(f.verts) - 2 for f in bm.faces)


def plateau(k, outer, walk_polys, y, seed, unf=None, skip=None, ledge=1.3, hatch_density=1.0, holes=(), walk_key='walk',
            margin_y=None, deep_y=None, hatch_floor=None, real=True):
    """walkable polygons + paper margin (outer minus walk) + stepped cliff wall round the outer outline down to the abyss."""
    outer = ccw(outer)
    for wp in walk_polys:
        wp = ccw(wp)
        fill(getattr(k, walk_key), wp, y, steiner=grid_pts(wp, 2.2, seed + len(wp)))
    my = y if margin_y is None else margin_y
    fill(k.margin, outer, my, holes=[ccw(walk_polys[0])] + [ccw(h) for h in holes], steiner=grid_pts(outer, 2.6, seed + 7))
    walls(k.solid, k.ink, k.hatch if real else None, outer, my, FLOOR, seed, ledge=ledge, ledge_out=0.32, skip=skip,
          hatch_floor=(y - 3.0) if hatch_floor is None else hatch_floor, hatch_density=hatch_density if real else 0.0,
          deep=k.dark, deep_y=(y - 3.2) if deep_y is None else deep_y, unf=unf, sketch=k.sketch, torn=k.torn)


def obox(bm, ink, c, size, y0, yaw, ink_top=True, ink_w=0.05, corners=True, rnd=None):
    """SL.box + ink on its top edges and (some) vertical corners."""
    corners_, top = box(bm, c, size, y0, yaw)
    if ink is not None and ink_top:
        pts = [v.co + V((0, 0, 0.012)) for v in top]
        stroke3(ink, pts + [pts[0]], ink_w)
        if corners:
            for i, p in enumerate(corners_):
                if rnd is None or rnd.random() < 0.6:
                    stroke3(ink, [B(p.x, p.y, y0), B(p.x, p.y, y0 + size[1])], ink_w * 0.7)
    return corners_


def lathe(bm, c, prof, seg=10, y0=0.0, want_out=True, cap=True):
    """profile = [(r, y), ...] bottom -> top, revolved round c (Unity xz)."""
    rings = []
    for (r, y) in prof:
        rings.append([bm.verts.new(B(c[0] + math.cos(2 * math.pi * i / seg) * r, c[1] + math.sin(2 * math.pi * i / seg) * r, y0 + y)) for i in range(seg)])
    cB = B(c[0], c[1], 0)
    for ri in range(len(rings) - 1):
        for i in range(seg):
            j = (i + 1) % seg
            f = add_face(bm, [rings[ri][i], rings[ri][j], rings[ri + 1][j], rings[ri + 1][i]], None)
            if f:
                m = f.calc_center_median()
                out = V((m.x - cB.x, m.y - cB.y, 0))
                if (f.normal.dot(out) < 0) == want_out:
                    f.normal_flip()
    if cap and prof[-1][0] > 0.01:
        f = add_face(bm, list(rings[-1]), V((0, 0, 1)))
    return rings


def slab_wall(k, p0, p1, y0, h, t, done, seed, bm=None, ink=True, frac_fall=0.45, studs=True, planks=0.0):
    """a wall p0->p1 (Unity xz) of height h and thickness t, built only for `done` of its length (ragged top falling off
    toward the end), the rest drawn: pencil outline, studs and a diagonal brace (unfinished FORM, not unpainted colour)."""
    rnd = random.Random(seed)
    bm = bm or k.solid
    p0, p1 = V(p0), V(p1)
    d = (p1 - p0)
    ln = d.length
    if ln < 0.05:
        return
    u = d / ln
    n = V((-u.y, u.x)) * (t / 2)
    nseg = max(2, int(ln * done / 0.7))
    tops = []
    for i in range(nseg + 1):
        s = i / nseg
        fall = max(0.0, (s - (1 - frac_fall)) / frac_fall) if done < 0.999 else 0.0
        yy = y0 + h * (1.0 - 0.7 * fall) + (rnd.uniform(-0.1, 0.06) if 0 < i < nseg and done < 0.999 else 0.0)
        tops.append((p0 + u * (ln * done * s), yy))
    for i in range(nseg):
        (a, ya), (b, yb) = tops[i], tops[i + 1]
        for sd in (1, -1):
            q = [bm.verts.new(B(*(a + n * sd), y0 - 0.1)), bm.verts.new(B(*(b + n * sd), y0 - 0.1)),
                 bm.verts.new(B(*(b + n * sd), yb)), bm.verts.new(B(*(a + n * sd), ya))]
            add_face(bm, q, V((-(n * sd).x, -(n * sd).y, 0)))
        q = [bm.verts.new(B(*(a + n), ya)), bm.verts.new(B(*(b + n), yb)), bm.verts.new(B(*(b - n), yb)), bm.verts.new(B(*(a - n), ya))]
        add_face(bm, q, V((0, 0, 1)))
        if ink:
            stroke3(k.ink, [B(*(a + n * 1.1), ya + 0.02), B(*(b + n * 1.1), yb + 0.02)], 0.06)
            stroke3(k.ink, [B(*(a - n * 1.1), ya + 0.02), B(*(b - n * 1.1), yb + 0.02)], 0.05)
        if planks > 0:
            yy = y0 + planks
            while yy < min(ya, yb) - 0.1:
                for sd in (1.15, -1.15):
                    if rnd.random() < 0.8:
                        stroke3(k.ink, [B(*(a + n * sd), yy + rnd.uniform(-0.03, 0.03)), B(*(b + n * sd), yy + rnd.uniform(-0.03, 0.03))], 0.02)
                yy += planks
    # end cap of the built part (a torn edge in raw paper)
    (a, ya) = tops[0]
    (e, ye) = tops[-1]
    for (p, yy) in ((a, ya), (e, ye)):
        q = [bm.verts.new(B(*(p + n), y0 - 0.1)), bm.verts.new(B(*(p - n), y0 - 0.1)), bm.verts.new(B(*(p - n), yy)), bm.verts.new(B(*(p + n), yy))]
        add_face(k.torn if (p is e and done < 0.999) else bm, q, None)
    if ink:
        stroke3(k.ink, [B(*(a + n * 1.1), y0), B(*(a + n * 1.1), ya)], 0.05)
    if done < 0.999:
        # drawn remainder: outline at full height, studs, a brace, measuring ticks
        q0 = p0 + u * (ln * done)
        stroke3(k.sketch, [B(*(q0 + n), y0 + h), B(*(p1 + n), y0 + h + rnd.uniform(-0.1, 0.1))], 0.035)
        stroke3(k.sketch, [B(*(p1 + n), y0), B(*(p1 + n), y0 + h + 0.3)], 0.035)
        if studs:
            m = max(1, int(ln * (1 - done) / 0.9))
            for i in range(1, m + 1):
                p = q0 + u * (ln * (1 - done) * i / (m + 1))
                stroke3(k.sketch, [B(*(p + n), y0), B(*(p + n), y0 + h * rnd.uniform(0.85, 1.05))], 0.03)
        stroke3(k.sketch, [B(*(q0 + n), ye), B(*(p1 + n), y0 + h * 0.15)], 0.03)
        stroke3(k.ink, [B(*(e + n * 1.2), ye + 0.02), B(*((e + u * 0.6) + n * 1.2), y0 + h * rnd.uniform(0.85, 1.0))], 0.04)


def steps(k, top, d, w, n, rise, run, y_top, built, seed=0, down=True, walk_bm=None):
    """a flight from `top` along d. built = how many treads are real (the rest only pencil). down=True: each step lower."""
    d = V(d).normalized()
    nn = V((-d.y, d.x))
    sg = -1.0 if down else 1.0
    for i in range(n):
        c0 = V(top) + d * (run * i)
        y_hi = y_top + sg * rise * i
        y = y_top + sg * rise * (i + 1)
        e0, e1 = c0 - nn * w / 2, c0 + nn * w / 2
        tread_y = y if down else y_hi + rise
        corners = [e0, e1, e1 + d * run, e0 + d * run]
        if i < built:
            fill(walk_bm if walk_bm is not None else k.margin, ccw(corners), tread_y if not down else y)
            ya, yb = (y + rise, y) if down else (y_hi, y_hi + rise)
            q = [k.solid.verts.new(B(e0.x, e0.y, ya)), k.solid.verts.new(B(e1.x, e1.y, ya)),
                 k.solid.verts.new(B(e1.x, e1.y, min(ya, yb) - 0.02)), k.solid.verts.new(B(e0.x, e0.y, min(ya, yb) - 0.02))]
            if down:
                add_face(k.solid, q, V((-d.x, -d.y, 0)) * -1)
                stroke3(k.ink, [B(e0.x, e0.y, y + rise + 0.02), B(e1.x, e1.y, y + rise + 0.02)], 0.05)
            else:
                q = [k.solid.verts.new(B(e0.x, e0.y, y_hi)), k.solid.verts.new(B(e1.x, e1.y, y_hi)),
                     k.solid.verts.new(B(e1.x, e1.y, y_hi + rise)), k.solid.verts.new(B(e0.x, e0.y, y_hi + rise))]
                add_face(k.solid, q, V((-d.x, -d.y, 0)))
                stroke3(k.ink, [B(e0.x, e0.y, y_hi + rise + 0.02), B(e1.x, e1.y, y_hi + rise + 0.02)], 0.05)
            # side cheeks down to the ground
            for (ea, sgn) in ((e0, -1), (e1, 1)):
                yy = (y if down else y_hi + rise)
                q = [k.solid.verts.new(B(ea.x, ea.y, yy)), k.solid.verts.new(B((ea + d * run).x, (ea + d * run).y, yy)),
                     k.solid.verts.new(B((ea + d * run).x, (ea + d * run).y, yy - rise - 0.25)), k.solid.verts.new(B(ea.x, ea.y, yy - rise - 0.25))]
                add_face(k.solid, q, V((nn.x * -sgn, nn.y * -sgn, 0)))
        else:
            yy = (y if down else y_hi + rise)
            yr = (y + rise if down else y_hi)
            stroke3(k.sketch, [B(e0.x, e0.y, yr), B(e1.x, e1.y, yr)], 0.04)
            stroke3(k.sketch, [B(e0.x, e0.y, yr), B(e0.x, e0.y, yy), B((e0 + d * run).x, (e0 + d * run).y, yy)], 0.035)
            stroke3(k.sketch, [B(e1.x, e1.y, yy), B((e1 + d * run).x, (e1 + d * run).y, yy)], 0.03)
    for s_ in (-1, 1):
        p0 = V(top) + nn * s_ * (w / 2 + 0.05)
        p1 = V(top) + d * (run * n) + nn * s_ * (w / 2 + 0.05)
        y1 = y_top + sg * rise * n
        stroke3(k.ink, [B(p0.x, p0.y, y_top + 0.05), B(p1.x, p1.y, y1 + 0.05)], 0.06)
        stroke3(k.ink if s_ < 0 else k.sketch, [B(p0.x, p0.y, y_top + 0.9), B(p1.x, p1.y, y1 + 0.9)], 0.04)


def balustrade(k, pts, y0, done, seed, bm=None, h=0.95, post=0.24, gap=1.3):
    """painted rail along a polyline: real posts + top rail for the first `done` of its length, then drawn posts."""
    rnd = random.Random(seed)
    bm = bm or k.terra
    pts = [V(p) for p in pts]
    total = sum((pts[i + 1] - pts[i]).length for i in range(len(pts) - 1))
    acc = 0.0
    for i in range(len(pts) - 1):
        a, b = pts[i], pts[i + 1]
        ln = (b - a).length
        if ln < 0.05:
            continue
        u = (b - a) / ln
        yaw = math.degrees(math.atan2(u.x, u.y)) - 90
        t = 0.0
        while t < ln:
            p = a + u * t
            f = (acc + t) / total
            if f < done:
                box(bm, (p.x, p.y), (post, h, post), y0, yaw)
                stroke3(k.ink, [B(p.x, p.y, y0 + h + 0.03), B(p.x, p.y, y0 + 0.05)], 0.035)
            else:
                stroke3(k.sketch, [B(p.x, p.y, y0), B(p.x, p.y, y0 + h * rnd.uniform(0.8, 1.1))], 0.035)
            t += gap
        # rail
        f0, f1 = acc / total, (acc + ln) / total
        if f1 <= done:
            m = (a + b) / 2
            box(k.terrad if bm is k.terra else bm, (m.x, m.y), (ln + 0.1, 0.14, post * 1.25), y0 + h, yaw)
            stroke3(k.ink, [B(a.x, a.y, y0 + h + 0.16), B(b.x, b.y, y0 + h + 0.16)], 0.05)
        elif f0 < done:
            cut = (done - f0) / (f1 - f0)
            e = a + (b - a) * cut
            m = (a + e) / 2
            box(k.terrad if bm is k.terra else bm, (m.x, m.y), ((e - a).length, 0.14, post * 1.25), y0 + h, yaw)
            stroke3(k.ink, [B(a.x, a.y, y0 + h + 0.16), B(e.x, e.y, y0 + h + 0.16)], 0.05)
            stroke3(k.sketch, [B(e.x, e.y, y0 + h + 0.07), B(b.x, b.y, y0 + h + rnd.uniform(-0.05, 0.08))], 0.035)
        else:
            stroke3(k.sketch, [B(a.x, a.y, y0 + h + rnd.uniform(-0.05, 0.05)), B(b.x, b.y, y0 + h + rnd.uniform(-0.05, 0.05))], 0.035)
            if rnd.random() < 0.5:
                stroke3(k.sketch, [B(a.x, a.y, y0 + h * 0.5), B(b.x, b.y, y0 + h * 0.5)], 0.025)
        acc += ln


def sack(k, c, r, h, seed, books=(), y0=0.0, tilt=0.0):
    """lumpy paper sack (the collectors' bags of human objects): a sagging lathe with a pinched neck, tie in ink,
    human things (books) poking out in their own colours."""
    rnd = random.Random(seed)
    seg = 8
    prof = [(r * 0.82, 0.0), (r * 1.0, h * 0.18), (r * 1.04, h * 0.45), (r * 0.86, h * 0.72), (r * 0.42, h * 0.9), (r * 0.5, h * 1.0)]
    rings = []
    for (rr, yy) in prof:
        ring = []
        for i in range(seg):
            a = 2 * math.pi * i / seg
            w = rr * (1.0 + rnd.uniform(-0.12, 0.1))
            ring.append(k.sack.verts.new(B(c[0] + math.cos(a) * w + tilt * yy, c[1] + math.sin(a) * w * 0.9, y0 + yy * (1.0 + rnd.uniform(-0.04, 0.04)))))
        rings.append(ring)
    cB = B(c[0], c[1], 0)
    for ri in range(len(rings) - 1):
        for i in range(seg):
            j = (i + 1) % seg
            f = add_face(k.sack, [rings[ri][i], rings[ri][j], rings[ri + 1][j], rings[ri + 1][i]], None)
            if f:
                m = f.calc_center_median()
                if f.normal.dot(V((m.x - cB.x, m.y - cB.y, 0))) < 0:
                    f.normal_flip()
    add_face(k.sack, list(rings[-1]), V((0, 0, 1)))
    neck = [v.co + V((0, 0, 0.01)) for v in rings[-2]]
    stroke3(k.ink, neck + [neck[0]], 0.035)
    # a seam and a fold in ink on the camera side
    for i in (4, 5):
        stroke3(k.ink, [rings[1][i].co, rings[2][i].co, rings[3][i].co], 0.025)
    for (m, dx, dz, yaw, ln) in books:
        bx, bz = c[0] + dx, c[1] + dz
        box(k.books[m], (bx, bz), (0.42 * ln, 0.09, 0.3), y0 + h * 0.86, yaw)
        box(k.books['M_PageWhite'], (bx + 0.02, bz), (0.38 * ln, 0.06, 0.26), y0 + h * 0.86 + 0.012, yaw)


def book(k, c, y, yaw, m='M_BookRed', s=1.0):
    box(k.books[m], c, (0.5 * s, 0.1 * s, 0.36 * s), y, yaw)
    box(k.books['M_PageWhite'], (c[0] + 0.02, c[1]), (0.46 * s, 0.07 * s, 0.32 * s), y + 0.016 * s, yaw)


def drape(bm, ink, top_pts, y_top, y_bot, folds=6, depth=0.18, seed=0, sway=0.0):
    """a hanging curtain: vertical folds (zig-zag columns) from a top polyline down to y_bot."""
    rnd = random.Random(seed)
    a, b = V(top_pts[0]), V(top_pts[1])
    u = (b - a)
    nrm = V((-u.y, u.x)).normalized()
    cols = folds * 2 + 1
    top, bot = [], []
    for i in range(cols):
        t = i / (cols - 1)
        p = a + u * t
        off = nrm * (depth if i % 2 else -depth * 0.3)
        top.append(bm.verts.new(B(*(p + off * 0.4), y_top)))
        q = p + off + u.normalized() * sway * (1 - abs(0.5 - t) * 2)
        bot.append(bm.verts.new(B(*q, y_bot + rnd.uniform(-0.12, 0.12))))
    for i in range(cols - 1):
        add_face(bm, [top[i], top[i + 1], bot[i + 1], bot[i]], None)
    for i in range(0, cols, 2):
        stroke3(ink, [top[i].co, bot[i].co], 0.03)
    stroke3(ink, [v.co for v in bot], 0.04)


def wavy_banner(bm, ink, pole_top, d, ln, h, seed):
    """a pennant/banner hanging from a pole top, cut swallow-tail."""
    rnd = random.Random(seed)
    p = V(pole_top[:2])
    y = pole_top[2]
    d = V(d).normalized()
    pts_t, pts_b = [], []
    for i in range(6):
        t = i / 5
        q = p + d * ln * t
        dy = 0.12 * math.sin(t * 5 + seed)
        pts_t.append(bm.verts.new(B(q.x, q.y, y + dy)))
        pts_b.append(bm.verts.new(B(q.x, q.y, y - h + dy - (0.25 if i == 5 else 0) + (0.0 if i < 5 else 0))))
    for i in range(5):
        f = add_face(bm, [pts_t[i], pts_t[i + 1], pts_b[i + 1], pts_b[i]], None)
        if f:
            add_face(bm, [bm.verts.new(v.co) for v in reversed(f.verts)], None)
    stroke3(ink, [v.co for v in pts_t], 0.03)
    stroke3(ink, [v.co for v in pts_b], 0.03)


def bark_ring(k, c, r, h_fn, y0, seg, seed, bm_out=None, bm_in=None, thick=0.45, pencil_above=None, ink_rim=True):
    """a hollow trunk wall: ring of bark quads whose height varies per segment (h_fn(angle) -> height above y0, 0 = absent).
    outer face bark, inner face paper-back, top cap in raw torn paper; the planned rest drawn in pencil."""
    rnd = random.Random(seed)
    bm_out = bm_out if bm_out is not None else k.bark
    bm_in = bm_in if bm_in is not None else k.paperback
    for i in range(seg):
        a0 = 2 * math.pi * i / seg
        a1 = 2 * math.pi * (i + 1) / seg
        h0, h1 = h_fn(a0), h_fn(a1)
        r0 = r * (1 + 0.06 * math.sin(i * 1.7 + seed))
        r1 = r * (1 + 0.06 * math.sin((i + 1) * 1.7 + seed))
        po0 = V((c[0] + math.cos(a0) * r0, c[1] + math.sin(a0) * r0))
        po1 = V((c[0] + math.cos(a1) * r1, c[1] + math.sin(a1) * r1))
        pi0 = V((c[0] + math.cos(a0) * (r0 - thick), c[1] + math.sin(a0) * (r0 - thick)))
        pi1 = V((c[0] + math.cos(a1) * (r1 - thick), c[1] + math.sin(a1) * (r1 - thick)))
        cB = B(c[0], c[1], 0)
        if h0 > 0.05 or h1 > 0.05:
            h0_, h1_ = max(h0, 0.05), max(h1, 0.05)
            for (p0, p1, bm, outward) in ((po0, po1, bm_out, True), (pi0, pi1, bm_in, False)):
                q = [bm.verts.new(B(p0.x, p0.y, y0 - 0.2)), bm.verts.new(B(p1.x, p1.y, y0 - 0.2)), bm.verts.new(B(p1.x, p1.y, y0 + h1_)), bm.verts.new(B(p0.x, p0.y, y0 + h0_))]
                f = add_face(bm, q, None)
                if f:
                    m = f.calc_center_median()
                    o = V((m.x - cB.x, m.y - cB.y, 0))
                    if (f.normal.dot(o) < 0) == outward:
                        f.normal_flip()
            q = [k.torn.verts.new(B(po0.x, po0.y, y0 + h0_)), k.torn.verts.new(B(po1.x, po1.y, y0 + h1_)),
                 k.torn.verts.new(B(pi1.x, pi1.y, y0 + h1_)), k.torn.verts.new(B(pi0.x, pi0.y, y0 + h0_))]
            add_face(k.torn, q, V((0, 0, 1)))
            if ink_rim:
                stroke3(k.ink, [B(po0.x, po0.y, y0 + h0_ + 0.02), B(po1.x, po1.y, y0 + h1_ + 0.02)], 0.06)
                stroke3(k.ink, [B(pi0.x, pi0.y, y0 + h0_ + 0.02), B(pi1.x, pi1.y, y0 + h1_ + 0.02)], 0.04)
            # bark grain strokes (vertical, a few)
            if rnd.random() < 0.55:
                t = rnd.uniform(0.2, 0.8)
                p = po0.lerp(po1, t) + (po0 - V(c)).normalized() * 0.03
                hh = h0_ + (h1_ - h0_) * t
                stroke3(k.ink, [B(p.x, p.y, y0 + hh * rnd.uniform(0.0, 0.3)), B(p.x, p.y, y0 + hh * rnd.uniform(0.6, 0.95))], 0.03)
        if pencil_above is not None:
            hp = pencil_above(a0)
            if hp > max(h0, 0.0) + 0.3 and i % 2 == 0:
                stroke3(k.sketch, [B(po0.x, po0.y, y0 + max(h0, 0.0)), B(po0.x, po0.y, y0 + hp)], 0.03)
    if pencil_above is not None:
        for frac in (0.55, 1.0):
            pts = []
            for i in range(seg + 1):
                a = 2 * math.pi * i / seg
                hp = pencil_above(a) * frac
                pts.append(B(c[0] + math.cos(a) * r, c[1] + math.sin(a) * r, y0 + hp))
            stroke3(k.sketch, pts, 0.03)


def root(k, pts3, r0, r1, seed, bm=None):
    """a thick root/branch: tapered tube (Blender coords) + an ink contour line on its top."""
    bm = bm if bm is not None else k.bark
    b = L.bm_tube(pts3, [r0 + (r1 - r0) * i / (len(pts3) - 1) for i in range(len(pts3))], seg=6)
    me = L.bpy.data.meshes.new('t')
    b.to_mesh(me)
    bm.from_mesh(me)
    L.bpy.data.meshes.remove(me)
    b.free()
    stroke3(k.ink, [p + V((0, 0, r0 * 0.9 + (r1 - r0) * i / (len(pts3) - 1))) for i, p in enumerate(pts3)], 0.035)


def abyss_floor(k, c, rx, rz, seed):
    rnd = random.Random(seed)
    floor = [V((c[0] - rx, c[1] - rz)), V((c[0] + rx, c[1] - rz)), V((c[0] + rx, c[1] + rz)), V((c[0] - rx, c[1] + rz))]
    fill(k.abyss, ccw(floor), FLOOR, uv=False)
    for _ in range(40):
        p = V((rnd.uniform(c[0] - rx * 0.6, c[0] + rx * 0.6), rnd.uniform(c[1] - rz * 0.6, c[1] + rz * 0.6)))
        ground_stroke(k.hatch, [p, p + V((0.9, 1.3)) * rnd.uniform(0.6, 1.4)], FLOOR, 0.09)


def stacks(k, items, seed):
    """drawn stone stacks rising out of the abyss round a page (some carry fallen books)."""
    for i, (c, r, top, books) in enumerate(items):
        yb, cc = cairn(k, c, r, top - FLOOR, FLOOR, seed + i * 3, True, 0.25 if not books and i % 3 == 0 else 0.0)
        yb = top if books else yb
        for (m, dx, dz, yaw) in books:
            box(k.books[m], (cc.x + dx, cc.y + dz), (0.62, 0.11, 0.46), yb, yaw)
            box(k.books['M_PageWhite'], (cc.x + dx + 0.03, cc.y + dz), (0.56, 0.08, 0.40), yb + 0.015, yaw)
            yb += 0.11


def vdisc(bm, c, y, r, u, n=12, half=False):
    """vertical disc (or upper half) in the plane spanned by u (Unity xz direction) and up."""
    m = n // 2 if half else n
    pts = [B(*(V(c) + V(u) * (math.cos(math.pi * i / (n // 2)) * r)), y + math.sin(math.pi * i / (n // 2)) * r) for i in range(m + (1 if half else 0))]
    f = bm.faces.new([bm.verts.new(p) for p in pts])
    bm.faces.new([bm.verts.new(p) for p in reversed(pts)])
    return pts


def light_glow(k, c, y, s=0.28):
    box(k.glow, c, (s, s * 1.4, s), y, 0)


def finish_area(A, aid, k, kd=None, kl=None, kv=None, top='M_UnderGround', exits=(), extra_parts=()):
    s = aid[2:]
    parent = f'Area_{aid}'
    A.empty(parent, (0, 0, 0))
    stats = {}

    def add(name, kit, keys, vista=False, tp=top):
        p = Part(name)
        to_part(p, kit, keys, vista, tp)
        if p.pieces:
            ob = A.part(p, parent=parent)
            stats[name] = sum(len(pp.vertices) - 2 for pp in ob.data.polygons)
    add(f'Ground_Walk_{s}', k, WALK_KEYS)
    add(f'Margin_{s}', k, ('margin',))
    add(f'Ground_Lines_{s}', k, LINE_KEYS)
    add(f'Cliffs_{s}', k, CLIFF_KEYS)
    if kd is not None:
        add(f'Decor_{s}', kd, ALL_KEYS)
    if kl is not None:
        add(f'Light_{s}', kl, ('pool', 'beam', 'dust'))
    if kv is not None:
        add(f'Vista_{s}', kv, ALL_KEYS, vista=True)
    for (ex, d, y, paint, pen) in exits:
        t = ex['to'][2:]
        ep = exit_marker(f'Exit_{s}_{t}', ex['pos'], d, y, paint=paint, pen=pen)
        ob = A.part(ep, pivot=tuple(B(ex['pos'][0], ex['pos'][1], y)), parent=parent)
        stats[f'Exit_{s}_{t}'] = sum(len(pp.vertices) - 2 for pp in ob.data.polygons)
    for (name, kit, keys, pivot) in extra_parts:
        p = Part(name)
        to_part(p, kit, keys)
        if p.pieces:
            ob = A.part(p, pivot=pivot, parent=parent)
            stats[name] = sum(len(pp.vertices) - 2 for pp in ob.data.polygons)
    stats['_total'] = sum(v for kk, v in stats.items() if not kk.startswith('_'))
    TRIS[aid] = stats
    return stats


TRIS = {}


# ============================================================================================ AREA DATA
# ---------------------------------------------------------------- plaza (꼭두 광장)
ST_C = V((0.0, 20.4))        # Stage.fbx centre (same place the slice-1 vistas show), front faces the pass (WSW)
ST_YAW = 248.0
AX = side(ST_YAW)            # along the stage front (north-north-west)
FW = fwd(ST_YAW)             # toward the audience


def SP(ka, kf):
    return ST_C + AX * ka + FW * kf


BOARDS = [SP(8.2, 0.3), SP(5.0, 0.3), SP(-5.0, 0.3), SP(-8.2, 0.3)]          # ins_board_1..4, left -> right from the audience
W_PLAZA = [V(p) for p in [(-14.6, 26.3), (-11.0, 27.4), (-7.5, 28.6), (-4.9, 30.4)]] + \
          [SP(10.5, -0.3), SP(3.0, -0.3), SP(3.0, -2.6), SP(-3.0, -2.6), SP(-3.0, -0.3), SP(-10.5, -0.3)] + \
          [V(p) for p in [(7.5, 12.2), (10.8, 13.4), (11.4, 11.2), (8.0, 9.6), (7.0, 6.0), (7.6, 2.6), (7.2, 0.4), (5.0, -0.5), (2.2, -0.4),
                          (-2.0, 0.2), (-6.5, 1.3), (-10.5, 3.7), (-13.2, 7.4), (-14.5, 12.0), (-14.8, 16.5), (-14.6, 22.4)]]
P_PLAZA = [V(p) for p in [(-16.4, 22.0), (-16.6, 27.2), (-15.0, 28.4), (-11.5, 31.5), (-8.0, 34.5), (-4.0, 35.5), (1.5, 34.0), (6.5, 29.0),
                          (9.5, 22.0), (12.8, 16.4), (13.8, 11.8), (12.6, 8.0), (13.0, 3.2), (10.2, -0.8), (7.8, -2.4), (3.0, -2.5),
                          (-2.5, -1.7), (-7.5, -0.7), (-12.0, 1.5), (-15.6, 5.6), (-17.2, 11.0), (-17.4, 16.5), (-17.0, 21.0)]]
BELL_TOWER = V((8.4, 5.2))
GATE_STAIR = (V((-14.6, 24.4)), V((-1.0, 0.03)), 3.6, 8, 0.3, 0.6)     # foot centre (plaza edge), direction UP toward the gate
DEPOT_STAIR = (V((6.2, -0.2)), V((0.55, -0.835)), 2.0, 8, 0.31, 0.56)  # head centre, direction DOWN to the depot

PLAZA_PTS = {
    'z_stage': SP(-0.5, 3.8), 'z_doll_seat': SP(0, 0.9), 'z_board': SP(6.6, 2.2), 'z_board_s': SP(-6.6, 2.2),
    'z_chief_seat': SP(-5.0, 4.2), 'z_pedestal': SP(-3.0, 2.6), 'z_crowd_rows': V((-5.5, 12.5)), 'z_back_corner': V((-11.0, 6.0)),
    'z_bell': V((6.4, 4.4)), 'z_crowd_offer': V((-9.0, 19.0)), 'z_porridge': V((-8.2, 8.6)),
    'stage': ST_C, 'doll': SP(0, 0.6), 'fish_prop': SP(-2.2, 0.4), 'pedestal': SP(-3.0, 2.2), 'lump_prop': SP(2.2, 0.4),
    'board': SP(6.6, 0.9), 'bell': BELL_TOWER, 'ins_stage': SP(0, 3.2),
    'ins_board_1': BOARDS[0], 'ins_board_2': BOARDS[1], 'ins_board_3': BOARDS[2], 'ins_board_4': BOARDS[3],
    'actor_a': SP(1.4, 0.3), 'actor_b': SP(0, 0.9), 'actor_c': SP(-1.4, 0.3), 'crowd_plaza': V((-5.5, 13.0)),
    'pz_pedestal': SP(-3.0, 2.2), 'pz_string': SP(0, 0.6), 'pz_pick': V((-5.5, 12.5)),
}
CAM_PLAZA = {'yaw': 102, 'pitch': 24, 'distance': 14.0, 'fov': 34}
PIVOT_PLAZA = (-9.5, 4.5, 3.5, 25.0)

# ---------------------------------------------------------------- alley (삐걱의자 골목)
K_C = V((33.6, 22.4))        # Kinopio's house: open front faces WSW (toward the lane and the camera)
K_YAW = 250.0
KF, KX = fwd(K_YAW), side(K_YAW)
K_W, K_D = 4.4, 3.8


def KP(kx, kf):
    return K_C + KX * kx + KF * kf


ALLEY_HOUSES = [('House_4', V((15.2, 21.6)), 200, 0.85, 1.6), ('House_3', V((20.6, 23.6)), 205, 0.85, 2.0),
                ('House_2', V((26.0, 25.0)), 212, 0.85, 1.85)]          # (model, centre, yaw, scale, half depth)
Y_ALLEY = [V(p) for p in [(12.0, 15.0), (12.4, 17.0), (13.4, 20.2), (16.4, 21.2), (18.6, 22.2), (19.6, 23.2), (22.4, 23.6), (24.6, 24.4),
                          (27.6, 24.6), (29.9, 24.6)]] + [KP(2.2, 1.9), KP(2.2, -1.6), KP(-2.2, -1.6), KP(-2.2, 1.9)] + \
    [V(p) for p in [(31.2, 19.1), (29.72, 18.58), (28.08, 17.82), (27.0, 18.3), (23.4, 17.5), (19.6, 16.3), (16.4, 15.0), (13.8, 13.9), (12.2, 13.9)]]
K_FLOOR = [KP(2.2, 1.9), KP(2.2, -1.6), KP(-2.2, -1.6), KP(-2.2, 1.9)]
CRACK = [V((30.2, 24.55)), V((30.7, 24.75)), V((34.4, 26.1)), V((35.9, 27.1))]
P_ALLEY = [V(p) for p in [(11.0, 12.8), (11.2, 18.5), (12.6, 22.6), (15.0, 25.8), (19.0, 27.8), (24.0, 29.2), (29.0, 30.0), (33.0, 30.4),
                          (37.2, 29.2), (37.8, 26.0), (37.8, 21.0), (36.8, 18.4), (33.4, 16.6), (30.0, 16.0), (26.0, 15.4), (21.0, 13.2),
                          (16.0, 11.4), (12.6, 11.2)]]
ALLEY_STAIR = (V((28.9, 18.2)), V((0.42, -0.91)), 1.8, 9, 0.28, 1.0)   # long flight over the gap down to the field
TREE_C = V((42.4, 29.4))      # the old hollow tree = the hideout, its outside rises behind the end of the alley

ALLEY_CHAIRS = []
for (m_, c_, y_, s_, hd_) in ALLEY_HOUSES:
    ALLEY_CHAIRS.append((c_ + fwd(y_) * (hd_ * s_ + 1.2), y_))
ALLEY_CHAIRS += [(V((22.0, 17.9)), 340.0), (V((17.6, 16.2)), 330.0)]   # two more chairs at the rail, their houses never got built
LUMPS = ['Lump_1', 'Lump_3', 'Lump_2', 'Lump_3', 'Lump_1']

ALLEY_PTS = {
    'z_kid_house': KP(0.0, 2.6), 'z_kid_house_chair': KP(0.6, 0.2), 'z_sawdust': KP(-1.0, 0.2), 'z_crack': V((30.5, 24.6)),
    'z_mother_house': V((21.5, 21.7)), 'z_lump': ALLEY_CHAIRS[1][0],
    'chairs': V((20.0, 19.6)), 'mother_lump': ALLEY_CHAIRS[1][0], 'kid_house_chair': KP(0.6, -0.9), 'z_alley_window': V((29.0, 22.4)),
    'neighbor_window': V((29.2, 26.06)),
    'ins_chair': ALLEY_CHAIRS[1][0], 'mother': V((21.5, 21.7)), 'crowd_alley': V((20.5, 18.6)),
}
CAM_ALLEY = {'yaw': 72, 'pitch': 25, 'distance': 13.0, 'fov': 34}
PIVOT_ALLEY = (14.5, 32.0, 16.0, 22.5)

# ---------------------------------------------------------------- hideout (키노피오의 비밀 굴)
H_C = V((42.4, 29.4))         # hollow centre (= TREE_C)
H_RX, H_RZ = 3.9, 3.2
H_WALL_R = 4.25
HIDE_WALK = []
for _i in range(20):
    HIDE_WALK.append(V((H_C.x + math.cos(2 * math.pi * _i / 20) * H_RX * (0.93 + 0.05 * math.sin(_i * 2.3)),
                        H_C.y + math.sin(2 * math.pi * _i / 20) * H_RZ * (0.93 + 0.05 * math.sin(_i * 2.3)))))
    if _i == 11:
        HIDE_WALK += [V((38.2, 28.15)), V((37.2, 27.8)), V((37.4, 27.15)), V((38.6, 27.45))]      # the root tunnel from the alley crack
HIDE_PTS = {
    'z_hideout_stash': V((44.6, 30.6)), 'z_hideout_drawing': V((43.4, 31.3)), 'z_hideout_nest': V((40.5, 30.6)),
    'z_hideout_talk': V((42.2, 29.0)), 'hideout_lantern': V((40.9, 31.3)),
}
CAM_HIDE = {'yaw': 52, 'pitch': 29, 'distance': 8.0, 'fov': 38}
PIVOT_HIDE = (40.2, 44.2, 28.2, 30.4)

# ---------------------------------------------------------------- cart / depot (수레 길 · 수거꾼 창고)
SHED = (18.0, 23.0, -13.0, -7.0)    # x0, x1, z0, z1: open front at x0 faces west (the camera)
W_CART = [V(p) for p in [(7.4, -2.6), (10.0, -2.7), (14.0, -2.8), (18.0, -2.9), (22.0, -3.1), (25.5, -3.2), (28.3, -3.4), (28.4, -6.4),
                         (25.0, -6.5), (22.6, -6.4), (22.6, -12.6), (18.2, -12.6), (15.0, -12.4), (11.6, -11.8), (9.2, -10.6), (6.6, -10.4),
                         (5.2, -9.9), (5.2, -8.3), (7.0, -7.8), (7.6, -5.4), (7.0, -3.6)]]
P_CART = [V(p) for p in [(4.4, -11.2), (4.2, -7.2), (6.0, -2.3), (12.0, -2.2), (20.0, -2.4), (26.0, -2.6), (30.0, -2.8), (30.2, -7.6),
                         (26.5, -8.4), (24.6, -14.6), (17.0, -15.4), (10.0, -14.0), (6.8, -12.6)]]
CART_PTS = {
    'cart': V((13.4, -7.2)), 'z_cart': V((13.4, -7.2)), 'z_cart_lock': V((13.4, -5.7)), 'pz_cart': V((13.4, -5.9)),
    'z_depot': V((17.0, -9.6)), 'z_satchel': V((16.9, -9.8)), 'satchel': V((17.78, -10.05)), 'collector_boss': V((16.4, -11.4)),
    'collectors': V((15.8, -4.4)), 'z_depot_barrel': V((11.2, -8.6)),
}
CAM_CART = {'yaw': 96, 'pitch': 25, 'distance': 13.0, 'fov': 34}
PIVOT_CART = (7.5, 24.5, -11.0, -4.0)

# ---------------------------------------------------------------- field + pond (기적의 밭 · 먹물 웅덩이)
POND_C = V((58.0, -18.0))
POND_R = 6.1
APRON_R = 10.6
STEP_R = 11.4
ARC0, ARC1 = 95.0, 200.0        # the field side of the pond (steps); elsewhere the apron edge drops into the abyss


def pc(a, r):
    return POND_C + V((math.cos(RAD(a)), math.sin(RAD(a)))) * r


def arc(a0, a1, r, step=7.0):
    n = max(2, int(abs(a1 - a0) / step))
    return [pc(a0 + (a1 - a0) * i / n, r) for i in range(n + 1)]


W_FIELD = [V(p) for p in [(29.4, -3.1), (31.0, 0.5), (31.4, 5.0), (32.0, 10.6), (34.6, 10.9), (36.6, 7.2), (41.0, 6.6), (45.6, 4.6),
                          (49.6, 0.8), (53.2, -3.4)]] + arc(ARC0, ARC1, STEP_R) + \
          [V(p) for p in [(44.0, -22.0), (39.0, -17.5), (34.5, -13.0), (31.0, -8.6), (29.6, -6.8)]]
P_FIELD = [V(p) for p in [(28.0, -1.6), (29.6, 4.0), (30.4, 11.8), (36.4, 12.6), (42.0, 9.8), (48.0, 7.0), (53.0, 2.0), (57.6, -4.0)]] + \
          arc(ARC0 - 2, ARC1 + 2, STEP_R + 0.08) + [V(p) for p in [(43.0, -24.5), (36.0, -18.5), (30.6, -12.0), (28.0, -8.0)]]
ROAD_F = [V((30.0, -4.9)), V((35.0, -4.2)), V((40.2, -6.4)), V((45.0, -9.6)), pc(142, STEP_R + 0.4)]
ROAD_N = [V((32.7, 10.0)), V((36.0, 3.0)), V((38.6, -3.2)), V((40.2, -6.4))]
FIELD_PTS = {
    'z_field_pile': V((41.0, 1.0)), 'field_pile': V((41.0, 1.0)), 'field_mound': V((44.6, 2.4)), 'z_cart_procession': V((40.2, -6.4)),
    'z_sign': V((36.8, -8.4)), 'sign': V((36.8, -8.4)), 'ins_sign': V((36.8, -8.4)), 'z_page': V((37.6, -9.2)), 'page': V((37.6, -9.2)),
    'rd_page': V((37.6, -9.2)), 'tracks': V((44.0, -9.0)),
    'z_pond_stop': V((46.4, -9.0)), 'z_pond_edge': pc(140, 8.6), 'z_pond_bank': pc(118, 7.4), 'z_pond_center': POND_C,
    'z_pond_stone': pc(205, 8.6), 'pond_stone': pc(205, 8.9), 'ins_pond': pc(205, 8.9), 'pond': POND_C,
    'stacker': V((42.2, 2.6)), 'crowd_field': V((44.0, -3.0)), 'fish': POND_C,
    'z_field_stone': V((47.0, -6.6)), 'field_stone': V((47.0, -6.6)), 'z_pond_lineup': V((51.6, -11.6)), 'z_lump_spat': V((52.4, -13.4)),
}
LINEUP = [pc(112 + i * 7.1, 8.4) for i in range(8)] + [pc(110 + i * 7.6, 9.75) for i in range(8)]   # 16: two rows round z_pond_lineup
CART_TRACKS = [[V((33.4, 1.6)), V((38.0, -2.0)), V((42.4, -6.6)), V((46.2, -9.6)), pc(146, STEP_R + 0.3)],
               [V((31.6, -9.2)), V((37.0, -11.2)), V((42.4, -12.6)), pc(158, STEP_R + 0.3)],
               [V((44.0, 3.2)), V((46.0, -1.6)), V((48.2, -6.0)), pc(132, STEP_R + 0.3)]]
CAM_FIELD = {'yaw': 128, 'pitch': 26, 'distance': 15.0, 'fov': 36}
PIVOT_FIELD = (32.0, 55.0, -18.0, 7.5)


def _bounds(piv):
    return [round(piv[0] - 4.0, 2), round(piv[1] + 4.0, 2), round(piv[2] - 4.0, 2), round(piv[3] + 4.0, 2)]


# ---------------------------------------------------------------- areas (chapter1.json areas[] format)
AREA_PLAZA = {
    'id': 'a_plaza', 'name': '꼭두 광장', 'places': ['plaza'],
    'shape': [{'c': [-3.0, 13.0], 'r': 11.2}, {'line': [[-14.0, 24.4], [-5.0, 25.0], [1.2, 20.0]], 'w': 2.6},
              {'line': [[4.0, 9.8], [10.4, 12.3]], 'w': 1.6}, {'line': [[2.0, 3.0], [6.0, 0.6]], 'w': 2.0}],
    'bounds': _bounds(PIVOT_PLAZA), 'camera': CAM_PLAZA,
    'mood': {'ambient': 0.72, 'keyIntensity': 0.28, 'drain': 0.3, 'note': '가장 칠해진 곳이지만 땅 밑: 윗면도 등불 웅덩이보다 어둡게(AreaSystem이 읽는 덮어쓰기 값)'},
    'exits': [
        {'to': 'a_gate', 'pos': [-14.0, 24.4], 'radius': 1.5, 'spawn': [-23.2, 23.5], 'face': 270, 'label': '길목 쪽',
         'note': 'pos = 길목 계단 발치(서쪽), spawn = 길목 문 안쪽'},
        {'to': 'a_alley', 'pos': [10.4, 12.3], 'radius': 1.4, 'spawn': [15.4, 16.6], 'face': 70, 'label': '골목 쪽',
         'note': 'pos = 무대 남쪽 끝을 돌아 나가는 좁은 길 끝'},
        {'to': 'a_cart', 'pos': [6.0, 0.6], 'radius': 1.3, 'spawn': [11.0, -4.0], 'face': 120, 'label': '수레 길',
         'note': 'pos = 종탑 옆 내리막 계단 머리(남동)'},
    ],
}
AREA_ALLEY = {
    'id': 'a_alley', 'name': '삐걱의자 골목', 'places': ['alley'],
    'shape': [{'line': [[13.0, 15.6], [18.5, 18.6], [24.5, 20.8], [29.6, 21.4]], 'w': 2.4}, {'c': [33.4, 22.5], 'r': 2.3},
              {'line': [[30.2, 24.55], [34.4, 26.1], [35.9, 27.1]], 'w': 0.6}, {'line': [[28.4, 19.0], [28.9, 18.2]], 'w': 1.0}],
    'bounds': _bounds(PIVOT_ALLEY), 'camera': CAM_ALLEY,
    'mood': {'ambient': 0.66, 'keyIntensity': 0.24, 'drain': 0.5},
    'exits': [
        {'to': 'a_plaza', 'pos': [13.2, 15.4], 'radius': 1.4, 'spawn': [6.8, 10.6], 'face': 250, 'label': '광장 쪽',
         'note': 'pos = 골목 서쪽 끝'},
        {'to': 'a_field', 'pos': [28.9, 18.3], 'radius': 1.1, 'spawn': [34.4, 7.4], 'face': 160, 'label': '밭 쪽',
         'note': 'pos = 남쪽 난간 틈 내리막 계단 머리'},
        {'to': 'a_hideout', 'pos': [35.6, 26.9], 'radius': 0.8, 'spawn': [39.6, 28.2], 'face': 60, 'label': '틈새',
         'note': 'pos = 키노피오 집 옆 바위 틈 끝(폭 약 0.9m: 키노피오는 쉽게, 주인공은 비집고)'},
    ],
}
AREA_HIDE = {
    'id': 'a_hideout', 'name': '키노피오의 비밀 굴', 'places': ['hideout'],
    'shape': [{'c': [42.4, 29.4], 'r': 3.6}, {'line': [[37.0, 27.45], [39.0, 28.0]], 'w': 0.6}],
    'bounds': _bounds(PIVOT_HIDE), 'camera': CAM_HIDE,
    'mood': {'note': 'AreaSystem Moods에 a_hideout 칸이 없음 → 추가 필요: ambient (0.36,0.31,0.26) key (0.85,0.70,0.52) 0.30 drain 0.30 bg (0.20,0.17,0.15). 따뜻함은 옹이구멍 빛줄기·등불이 만듦'},
    'exits': [
        {'to': 'a_alley', 'pos': [37.6, 27.55], 'radius': 0.7, 'spawn': [30.9, 24.6], 'face': 240, 'label': '골목으로',
         'note': 'pos = 뿌리 굴 입구(남서)'},
    ],
}
AREA_CART = {
    'id': 'a_cart', 'name': '수레 길', 'places': ['depot'],
    'shape': [{'c': [14.5, -7.6], 'r': 5.6}, {'line': [[8.6, -3.6], [18.0, -4.6], [27.6, -4.9]], 'w': 1.6},
              {'line': [[5.6, -9.2], [10.0, -9.6]], 'w': 1.2}, {'line': [[19.0, -10.0], [21.8, -10.0]], 'w': 2.4}],
    'bounds': _bounds(PIVOT_CART), 'camera': CAM_CART,
    'mood': {'ambient': 0.64, 'keyIntensity': 0.22, 'drain': 0.6},
    'exits': [
        {'to': 'a_plaza', 'pos': [8.6, -3.5], 'radius': 1.2, 'spawn': [4.6, 2.2], 'face': 310, 'label': '광장 쪽',
         'note': 'pos = 광장 계단 발치'},
        {'to': 'a_field', 'pos': [27.6, -4.9], 'radius': 1.4, 'spawn': [32.4, -4.6], 'face': 100, 'label': '밭 쪽',
         'note': 'pos = 동쪽 수레 길 끝'},
        {'to': 'a_gate', 'pos': [5.8, -9.2], 'radius': 1.2, 'spawn': [-28.0, 21.6], 'face': 0, 'label': '길목 쪽',
         'note': 'pos = 서쪽 선반 길 끝(길목 남쪽 계단으로 이어짐)'},
    ],
}
AREA_FIELD = {
    'id': 'a_field', 'name': '기적의 밭 · 먹물 웅덩이', 'places': ['field', 'pond'],
    'shape': [{'c': [40.5, -4.0], 'r': 9.6}, {'c': [58.0, -18.0], 'r': 11.4}, {'line': [[32.7, 10.0], [36.0, 3.0], [38.6, -3.2]], 'w': 1.6},
              {'line': [[30.0, -4.9], [35.0, -4.2]], 'w': 1.6}, {'line': [[40.2, -6.4], [49.0, -11.4]], 'w': 3.4}],
    'bounds': _bounds(PIVOT_FIELD), 'camera': CAM_FIELD,
    'mood': {'ambient': 0.6, 'keyIntensity': 0.2, 'drain': 0.62},
    'exits': [
        {'to': 'a_alley', 'pos': [32.9, 9.7], 'radius': 1.2, 'spawn': [26.8, 20.0], 'face': 300, 'label': '골목 쪽',
         'note': 'pos = 골목에서 내려오는 긴 계단 발치(북)'},
        {'to': 'a_cart', 'pos': [30.0, -4.9], 'radius': 1.4, 'spawn': [24.0, -4.9], 'face': 270, 'label': '수레 길',
         'note': 'pos = 서쪽 수레 길 끝'},
    ],
}
NEW_AREAS = [AREA_PLAZA, AREA_ALLEY, AREA_HIDE, AREA_CART, AREA_FIELD]
NEW_IDS = tuple(a['id'] for a in NEW_AREAS)
EXITS_INTO2 = {('a_gate', 'a_plaza'): {'spawn': [-11.8, 23.8], 'face': 100}, ('a_gate', 'a_cart'): {'spawn': [8.6, -8.8], 'face': 80}}
PLACES2 = {'plaza': ([-3.0, 13.0], 12), 'alley': ([23.0, 20.0], 10), 'hideout': ([42.4, 29.4], 3.6), 'depot': ([15.5, -7.5], 7),
           'field': ([40.5, -2.0], 11), 'pond': ([58.0, -18.0], 8)}
GAME_CAM2 = {'a_plaza': (CAM_PLAZA, PIVOT_PLAZA), 'a_alley': (CAM_ALLEY, PIVOT_ALLEY), 'a_hideout': (CAM_HIDE, PIVOT_HIDE),
             'a_cart': (CAM_CART, PIVOT_CART), 'a_field': (CAM_FIELD, PIVOT_FIELD)}


def patch_areas(areas):
    """replace plaza/alley/cart/field, add the hideout, re-point the gate's exit spawns into them."""
    byid = {a['id']: i for i, a in enumerate(areas)}
    for na in NEW_AREAS:
        cp = json.loads(json.dumps(na))
        if na['id'] in byid:
            areas[byid[na['id']]] = cp
        else:
            areas.append(cp)
    for a in areas:
        for ex in a['exits']:
            key = (a['id'], ex['to'])
            if key in EXITS_INTO2:
                ex.update(EXITS_INTO2[key])
    return areas


# ============================================================================================ PLAZA
def theatre(k, kd):
    """Fire-eater's great puppet theatre: two painted towers framing Stage.fbx, a navy night back wall with lit windows,
    red drapes, a crowned arch with a flame crest, banner poles. The most painted thing in chapter 1; one tower top and
    a banner pole are still only drawn."""
    rnd = random.Random(301)
    y = YP
    # back wall behind the stage (collider), navy painted inner face with tiny lit windows + a moon
    bw0, bw1 = SP(3.2, -2.85), SP(-3.2, -2.85)
    mid = (bw0 + bw1) / 2
    box(k.terra_r, (mid.x, mid.y), (6.6, 6.5, 0.5), y, ST_YAW)
    box(k.navy_r, (SP(0, -2.55).x, SP(0, -2.55).y), (5.6, 4.9, 0.08), y + 1.3, ST_YAW)
    for i in range(9):
        q = SP(-2.3 + i * 0.58, -2.49)
        light_glow(k, (q.x, q.y), y + 2.0 + (i % 3) * 0.55 + rnd.uniform(0, 0.4), 0.16)
    q = SP(1.4, -2.48)
    vdisc(k.glow, q, y + 5.2, 0.42, AX, 12)
    # towers framing the stage (shafts = collider; tops in decor)
    for (ka, wire, sd) in ((3.95, True, 1), (-3.95, False, 2)):
        c = SP(ka, -0.9)
        obox(k.terra_r, k.ink, (c.x, c.y), (1.55, 6.2, 1.55), y, ST_YAW, rnd=rnd)
        box(k.terrad_r, (c.x, c.y), (1.75, 0.35, 1.75), y + 6.2, ST_YAW)
        # arched window slots + lamp glow on the audience side
        for hh in (2.0, 4.0):
            p = c + FW * 0.79
            stroke3(k.ink, [B(*(p - AX * 0.25), y + hh), B(*(p - AX * 0.25), y + hh + 0.7)] +
                    [B(*(p + AX * (0.25 * math.cos(math.pi - math.pi * u / 6))), y + hh + 0.7 + 0.25 * math.sin(math.pi * u / 6)) for u in range(7)] +
                    [B(*(p + AX * 0.25), y + hh)], 0.05)
            light_glow(k, ((p - FW * 0.05).x, (p - FW * 0.05).y), y + hh + 0.15, 0.2)
        # octagonal top: painted drum + dome (south tower), or only drawn tiers (north tower = unfinished)
        if not wire:
            lathe(kd.terra_r, (c.x, c.y), [(0.95, 0.0), (0.95, 1.5), (1.05, 1.6), (0.85, 1.75)], seg=8, y0=y + 6.55)
            lathe(kd.terrad_r, (c.x, c.y), [(0.85, 0.0), (0.7, 0.55), (0.42, 0.95), (0.12, 1.2), (0.0, 1.25)], seg=8, y0=y + 8.3)
            stroke3(kd.ink, [B(c.x, c.y, y + 9.5), B(c.x, c.y, y + 10.6)], 0.05)
            wavy_banner(kd.curt, kd.ink, (c.x, c.y, y + 10.55), AX * -1, 1.4, 0.45, sd)
            ring = [B(c.x + math.cos(2 * math.pi * i / 8) * 0.97, c.y + math.sin(2 * math.pi * i / 8) * 0.97, y + 8.15) for i in range(9)]
            stroke3(kd.ink, ring, 0.05)
        else:
            lathe(kd.terra_r, (c.x, c.y), [(0.95, 0.0), (0.95, 0.55)], seg=8, y0=y + 6.55, cap=False)
            poly = [V((c.x + math.cos(2 * math.pi * i / 8) * 0.95, c.y + math.sin(2 * math.pi * i / 8) * 0.95)) for i in range(8)]
            wire_tiers(kd, poly, y + 7.1, y + 9.4, 3, 307)
            for i in range(4):
                p = c + AX * (0.9 if i % 2 else -0.9) + FW * (0.9 if i < 2 else -0.9)
                stroke3(kd.sketch, [B(p.x, p.y, y + 6.4), B(p.x, p.y, y + 10.4)], 0.035)      # scaffold poles
            stroke3(kd.sketch, [B(*(c - AX * 0.9 - FW * 0.9), y + 7.0), B(*(c + AX * 0.9 + FW * 0.9), y + 9.6)], 0.03)
            stroke3(kd.ink, [B(c.x, c.y, y + 6.6), B(c.x, c.y, y + 11.2)], 0.05)          # the banner pole stands, its flag only drawn
            stroke3(kd.sketch, [B(c.x, c.y, y + 11.1), B(*(c + AX * 1.3), y + 10.9), B(*(c + AX * 1.3), y + 10.45), B(c.x, c.y, y + 10.6)], 0.03)
    # arch beam over the stage (decor: Stage.fbx sits under it, raycasts must not hit it)
    a0, a1 = SP(3.95, -0.9), SP(-3.95, -0.9)
    m = (a0 + a1) / 2
    box(kd.terrad_r, (m.x, m.y), (8.6, 0.75, 1.0), y + 5.9, ST_YAW)
    stroke3(kd.ink, [B(*(a0 + FW * 0.52), y + 6.68), B(*(a1 + FW * 0.52), y + 6.68)], 0.06)
    stroke3(kd.ink, [B(*(a0 + FW * 0.52), y + 5.92), B(*(a1 + FW * 0.52), y + 5.92)], 0.05)
    # crest: a painted half-sun with flame rays (Fire-eater's sign)
    cc = m + FW * 0.56
    rays = 9
    for i in range(rays):
        t0 = math.pi * i / rays
        t1 = math.pi * (i + 1) / rays
        tm = (t0 + t1) / 2
        rr = 1.9 if i % 2 == 0 else 1.45
        p0 = cc + AX * (math.cos(t0) * 0.85)
        p1 = cc + AX * (math.cos(t1) * 0.85)
        pt = cc + AX * (math.cos(tm) * rr)
        bm = kd.paintr if i % 2 == 0 else kd.terra_r
        f = add_face(bm, [bm.verts.new(B(p0.x, p0.y, y + 6.65 + math.sin(t0) * 0.85)), bm.verts.new(B(p1.x, p1.y, y + 6.65 + math.sin(t1) * 0.85)),
                          bm.verts.new(B(pt.x, pt.y, y + 6.65 + math.sin(tm) * rr))], V((FW.x * -1, FW.y * -1, 0)))
        if f:
            add_face(bm, [bm.verts.new(v.co) for v in reversed(f.verts)], None)
        stroke3(kd.ink, [B(p0.x, p0.y, y + 6.65 + math.sin(t0) * 0.85), B(pt.x, pt.y, y + 6.65 + math.sin(tm) * rr), B(p1.x, p1.y, y + 6.65 + math.sin(t1) * 0.85)], 0.04)
    disc = vdisc(kd.glow, cc + FW * 0.01, y + 6.65, 0.85, AX, 20, half=True)
    stroke3(kd.ink, disc, 0.05)
    # valance + two big red drapes tied back to the towers
    drape(kd.curt, kd.ink, (SP(3.3, -0.35), SP(-3.3, -0.35)), y + 5.9, y + 5.05, folds=9, depth=0.12, seed=303)
    for (ka, sway) in ((4.75, 0.45), (-4.75, -0.45)):
        drape(kd.curt, kd.ink, (SP(ka, 0.08), SP(ka - math.copysign(1.6, ka), 0.08)), y + 5.85, y + 0.9, folds=4, depth=0.16, seed=304 + int(ka), sway=sway)
    # striped canopy behind (a big painted tent roof falling back to the east)
    for i in range(6):
        ka0, ka1 = -3.3 + i * 1.1, -3.3 + (i + 1) * 1.1
        bm = kd.paintr if i % 2 == 0 else kd.terra_r
        q = [SP(ka0, -1.45), SP(ka1, -1.45), SP(ka1, -5.6), SP(ka0, -5.6)]
        ys = [y + 7.4, y + 7.4, y + 4.6, y + 4.6]
        f = add_face(bm, [bm.verts.new(B(p.x, p.y, yy)) for p, yy in zip(q, ys)], V((0, 0, 1)))
        stroke3(kd.ink, [B(q[0].x, q[0].y, ys[0] + 0.02), B(q[3].x, q[3].y, ys[3] + 0.02)], 0.035)
    stroke3(kd.ink, [B(*SP(-3.3, -1.45), y + 7.43), B(*SP(3.3, -1.45), y + 7.43)], 0.06)
    # its far half was never painted: drawn ribs only
    for i in range(4):
        ka = -3.3 + i * 2.2
        stroke3(kd.sketch, [B(*SP(ka, -5.6), y + 4.6), B(*SP(ka, -8.0), y + 2.4)], 0.035)
    stroke3(kd.sketch, [B(*SP(-3.3, -8.0), y + 2.4), B(*SP(3.3, -8.0), y + 2.4)], 0.035)
    # side wagons / booths at the back (the travelling theatre's carts), painted
    for (ka, sd) in ((5.6, 311), (-6.0, 312)):
        c = SP(ka, -3.6)
        obox(k.swood, k.ink, (c.x, c.y), (2.2, 1.8, 2.6), y + 0.45, ST_YAW, rnd=rnd)
        for s_ in (-1, 1):
            p = c + FW * (1.32 * s_)
            ring = [B(*(p + AX * (math.cos(2 * math.pi * u / 10) * 0.45)), y + 0.45 + math.sin(2 * math.pi * u / 10) * 0.45) for u in range(11)]
            stroke3(k.ink, ring, 0.05)
        box(k.terrad_r, (c.x, c.y), (2.5, 0.25, 2.9), y + 2.25, ST_YAW)


def board_wall(k, kd):
    """the picture-board wall on both sides of the stage: painted arcade frames holding the king's 4 readings (PictureBoard.fbx
    stands in each frame). The far-right frame was never finished: built to waist height, the rest drawn."""
    rnd = random.Random(321)
    y = YP
    spans = [(10.4, 6.6, 0), (6.6, 3.4, 1), (-3.4, -6.6, 2), (-6.6, -10.4, 3)]
    for (k0, k1, i) in spans:
        done = 1.0 if i < 3 else 0.45
        p0, p1 = SP(k0, -0.55), SP(k1, -0.55)
        slab_wall(k, p0, p1, y, 4.1 if i in (1, 2) else 3.6, 0.45, done, 330 + i, bm=k.terra_r)
        if done > 0.99:
            c = (p0 + p1) / 2
            box(k.terrad_r, (c.x, c.y), ((p1 - p0).length + 0.3, 0.3, 0.7), y + (4.1 if i in (1, 2) else 3.6), ST_YAW)
            # frame round the board + a painted brush emblem above it
            fc = SP((k0 + k1) / 2, -0.28)
            stroke3(k.ink, [B(*(fc + AX * 1.55), y + 0.5), B(*(fc + AX * 1.55), y + 3.35), B(*(fc - AX * 1.55), y + 3.35), B(*(fc - AX * 1.55), y + 0.5)], 0.06)
            q = fc + FW * 0.02
            pts = [B(*(q + AX * (0.5 * math.cos(2 * math.pi * u / 12))), y + 3.75 + 0.18 * math.sin(2 * math.pi * u / 12)) for u in range(13)]
            stroke3(k.ink, pts, 0.04)
        else:
            fc = SP((k0 + k1) / 2, -0.28)
            stroke3(k.sketch, [B(*(fc + AX * 1.55), y + 0.5), B(*(fc + AX * 1.55), y + 3.35), B(*(fc - AX * 1.55), y + 3.35), B(*(fc - AX * 1.55), y + 0.5)], 0.035)
    # pillars between the spans (painted piers with lamp brackets)
    for ka in (10.4, 6.6, -6.6, -10.4):
        c = SP(ka, -0.55)
        hh = 4.4 if abs(ka) < 7 else 3.9
        if ka == -10.4:
            cairn_wire = True
            box(k.terra_r, (c.x, c.y), (0.7, 1.4, 0.75), y, ST_YAW)
            wire_tiers(k, hexp(c, 0.42, 340, 0.0), y + 1.4, y + hh, 3, 341)
            continue
        obox(k.terra_r, k.ink, (c.x, c.y), (0.7, hh, 0.75), y, ST_YAW, rnd=rnd)
        box(k.terrad_r, (c.x, c.y), (0.9, 0.3, 0.95), y + hh, ST_YAW)
        lc = c + FW * 0.6
        stroke3(kd.ink, [B(*(c + FW * 0.38), y + hh - 0.6), B(lc.x, lc.y, y + hh - 0.5), B(lc.x, lc.y, y + hh - 0.85)], 0.045)
        light_glow(kd, (lc.x, lc.y), y + hh - 1.15, 0.22)


def bell_tower(k, kd, kb):
    """the offering bell (new): a stone foot, a timber frame (one post and the roof only drawn), the bell on a real beam.
    kb receives the bell itself (separate part Bell_plaza, pivot = the hanging point)."""
    rnd = random.Random(351)
    c = BELL_TOWER
    y = YP
    yaw = 250.0
    cairn(k, c, 1.25, 0.6, y, 352, True, 0.0)
    yb = y + 0.6
    posts = [c + side(yaw) * sx * 0.95 + fwd(yaw) * sz * 0.95 for sx, sz in ((-1, -1), (1, -1), (1, 1), (-1, 1))]
    top = yb + 3.5
    for i, p in enumerate(posts):
        if i == 2:
            box(kd.swood, (p.x, p.y), (0.26, 1.6, 0.26), yb, yaw)
            stroke3(kd.sketch, [B(p.x, p.y, yb + 1.6), B(p.x, p.y, top + 0.4)], 0.035)
            stroke3(kd.ink, [B(p.x, p.y, yb + 1.62), B(p.x + 0.05, p.y, yb + 1.48)], 0.03)
        else:
            obox(kd.swood, kd.ink, (p.x, p.y), (0.26, top - yb, 0.26), yb, yaw, ink_w=0.04, rnd=rnd)
    # beams (front and back real, braces in ink)
    for (a, b_) in ((posts[0], posts[1]), (posts[3], posts[2])):
        m = (a + b_) / 2
        box(kd.swood, (m.x, m.y), ((b_ - a).length + 0.4, 0.3, 0.3), top - 0.3, yaw)
        stroke3(kd.ink, [B(a.x, a.y, top + 0.02), B(b_.x, b_.y, top + 0.02)], 0.04)
    for p in posts[:2]:
        stroke3(kd.ink, [B(p.x, p.y, top - 1.3), B(*((posts[0] + posts[1]) / 2), top - 0.3)], 0.035)
    hang = (posts[0] + posts[1] + posts[2] + posts[3]) / 4
    box(kd.swood, (hang.x, hang.y), (0.28, 0.32, 2.3), top - 0.3, yaw)        # the cross beam the bell hangs on
    # roof: only drawn (pyramid lines + one row of painted shingles)
    apex = B(c.x, c.y, top + 1.5)
    for p in posts:
        q = c + (p - c) * 1.35
        stroke3(kd.sketch, [B(q.x, q.y, top + 0.2), apex], 0.035)
    sh = [c + (p - c) * 1.35 for p in posts]
    stroke3(kd.sketch, [B(p.x, p.y, top + 0.2) for p in sh] + [B(sh[0].x, sh[0].y, top + 0.2)], 0.03)
    for i in range(4):
        a, b_ = sh[i], sh[(i + 1) % 4]
        if i in (0, 3):
            q = [kd.terrad_r.verts.new(B(a.x, a.y, top + 0.2)), kd.terrad_r.verts.new(B(b_.x, b_.y, top + 0.2)),
                 kd.terrad_r.verts.new(B(*(b_ + (c - b_) * 0.3), top + 0.75)), kd.terrad_r.verts.new(B(*(a + (c - a) * 0.3), top + 0.75))]
            add_face(kd.terrad_r, q, V((0, 0, 1)))
            stroke3(kd.ink, [B(*(a + (c - a) * 0.3), top + 0.77), B(*(b_ + (c - b_) * 0.3), top + 0.77)], 0.04)
    # the bell (pivot = hang point at top - 0.3)
    hp = top - 0.3
    lathe(kb.terrad_r, (hang.x, hang.y), [(0.0, -1.45), (0.86, -1.45), (0.76, -1.24), (0.6, -0.8), (0.5, -0.38), (0.38, -0.08), (0.12, 0.0)], seg=12, y0=hp)
    lathe(kb.iron, (hang.x, hang.y), [(0.14, -1.2), (0.14, -0.95), (0.0, -0.95)], seg=6, y0=hp)
    stroke3(kb.ink, [B(hang.x, hang.y, hp - 0.05), B(hang.x, hang.y, hp - 1.0)], 0.03)
    rim = [B(hang.x + math.cos(2 * math.pi * i / 16) * 0.88, hang.y + math.sin(2 * math.pi * i / 16) * 0.88, hp - 1.43) for i in range(17)]
    stroke3(kb.ink, rim, 0.05)
    band = [B(hang.x + math.cos(2 * math.pi * i / 16) * 0.57, hang.y + math.sin(2 * math.pi * i / 16) * 0.57, hp - 0.72) for i in range(17)]
    stroke3(kb.ink, band, 0.035)
    # pull rope down to a cleat (paper rope)
    stroke3(kd.ink, [B(hang.x + 0.5, hang.y, hp - 0.6), B(*(c + fwd(yaw) * 1.4), yb + 0.4)], 0.03)
    return hp, hang


def plaza_ground(k):
    y = YP
    w = ccw(W_PLAZA)
    rnd = random.Random(361)
    # painted hex stones (R 0.85): thick round the stage, thinning toward the gate side and the rims
    R = 0.85
    dx, dz = math.sqrt(3) * R, 1.5 * R
    for j in range(-12, 26):
        for i in range(-14, 14):
            cx = i * dx + (dx / 2 if j % 2 else 0)
            cz = 10.0 + j * dz
            p = V((cx, cz))
            if not inside(p, w) or poly_dist(p, w) < 0.9:
                continue
            dstage = (p - ST_C).length
            keep = 0.92 - 0.045 * max(0.0, dstage - 4.0) - (0.25 if p.x < -10 else 0.0)
            if rnd.random() > keep:
                continue
            hx = [V((cx + 0.9 * R * math.cos(RAD(60 * t + 30)), cz + 0.9 * R * math.sin(RAD(60 * t + 30)))) for t in range(6)]
            bm = k.pst3 if dstage < 7.5 + rnd.uniform(-1.5, 1.5) else (k.pst2 if rnd.random() < 0.55 else k.pst1)
            fill(bm, ccw(hx), y + 0.012, uv=False)
    hex_lines(k.ink, w, y, R, 362, keep=0.55, origin=(0.0, 10.0), w=0.045)
    cracks(k.ink, w, y, 12, 363, avoid=lambda p: (p - ST_C).length < 6)
    # drawn rings round the audience space (where the crowd sits on offering day) + compass marks
    for rr, ww in ((4.2, 0.05), (6.4, 0.04)):
        pts = []
        for i in range(0, 37):
            th = RAD(150 + i * 6.5)
            q = V((-5.5, 12.5)) + V((math.cos(th), math.sin(th))) * rr
            if inside(q, w) and poly_dist(q, w) > 0.4 and rnd.random() > 0.1:
                pts.append(q)
            else:
                if len(pts) > 1:
                    ground_stroke(k.ink, pts, y, ww)
                pts = []
        if len(pts) > 1:
            ground_stroke(k.ink, pts, y, ww)
    compass(k, V((-5.5, 12.5)), 1.2, y, 364, 1.0)
    # a painted red runner from the gate stairs to the stage front (the guest's way) - only half painted
    run = [V((-13.6, 24.2)), V((-9.5, 23.0)), V((-5.6, 21.2)), SP(0, 2.8)]
    for i in range(len(run) - 1):
        a, b = run[i], run[i + 1]
        d = (b - a).normalized()
        n = V((-d.y, d.x))
        if i < 2:
            q = [a + n * 0.65, b + n * 0.65, b - n * 0.65, a - n * 0.65]
            fill(k.paintr, ccw(q), y + 0.018, uv=False)
        ground_stroke(k.ink, [a + n * 0.7, b + n * 0.7], y, 0.04, 0.025)
        ground_stroke(k.ink if i < 2 else k.sketch, [a - n * 0.7, b - n * 0.7], y, 0.04, 0.025)
    for (c, rx, rz, rot, sd) in (((-12.0, 14.0), 1.6, 0.5, 0.3, 1), ((-8.0, 4.0), 1.2, 0.45, -0.4, 2), ((4.2, 3.0), 1.0, 0.4, 0.1, 3)):
        smudge(k, c, rx, rz, rot, y, 365 + sd)


def plaza_edges(k, kd):
    rnd = random.Random(371)
    y = YP
    # painted balustrade along the south and west rims: finished near the theatre, dissolving toward the gate
    south = [V((7.4, -0.9)), V((2.2, -0.95)), V((-2.2, -0.35)), V((-6.8, 0.7)), V((-11.0, 3.1)), V((-13.9, 7.0)), V((-15.3, 11.8)), V((-15.5, 16.4)), V((-15.3, 21.3))]
    balustrade(k, south, y, 0.55, 372)
    north = [V((-15.3, 27.2)), V((-11.2, 28.3)), V((-7.9, 29.5)), V((-5.6, 31.1))]
    balustrade(k, north, y, 0.25, 373)
    # neck to the alley: a low painted wall on its south side
    slab_wall(k, V((6.6, 9.1)), V((11.9, 11.0)), y, 1.1, 0.35, 0.7, 374, bm=k.terra_r)
    # the gate stairs (up to the pass): 5 real treads, the rest drawn (matches the pass page)
    top, d, sw, n, rise, run = GATE_STAIR
    steps(k, top, d, sw, n, rise, run, y, 2, seed=375, down=False)     # only two real treads: the flight is drawn (start shot stays on the stage)
    # stairs down to the depot (SE)
    top, d, sw, n, rise, run = DEPOT_STAIR
    steps(k, top, d, sw, n, rise, run, y, 4, seed=376, down=True)
    pennant(k.solid, k.paintr, k.ink, top + V((-d.y, d.x)) * 1.3 + d * 0.3, y, h=2.2, d=(d.x, d.y))
    # rocks / ledges on the margin north of the theatre and behind the board wall
    for (c, rx, rz, h, t, sd) in (((-9.2, 31.4), 1.4, 0.9, 1.2, 2, 381), ((-13.0, 29.6), 1.0, 0.7, 0.8, 1, 382), ((12.2, 6.2), 0.9, 0.8, 1.0, 1, 383),
                                  ((-16.2, 8.4), 0.8, 0.7, 0.6, 1, 384), ((11.6, 14.6), 0.8, 0.6, 1.4, 2, 385)):
        if sd % 2:
            rock_wire(k, hexp(c, rx, sd, sq=rz / rx), y, h, t, sd, wire=0.45)
        else:
            rock(k.solid, k.ink, k.hatch, hexp(c, rx, sd, sq=rz / rx), y, h, t, sd)
    # a half-built painted house at the north-west rim (front wall only) - the colour reaches the edge but not the form
    unfinished_house(k, (-12.6, 31.0), 3.0, 2.2, 2.6, 102, y, 386, roof=1.5)
    torn_hole(k, jag_poly((-16.4, 18.6), 0.7, 0.5, 7, 387, 0.3), y, 1.0, 388)
    torn_hole(k, jag_poly((4.2, 31.2), 0.9, 0.6, 8, 389, 0.2), y, 1.0, 390)


def catenary(a3, b3, sag, n=10):
    return [a3.lerp(b3, t / n) - V((0, 0, sag * math.sin(math.pi * t / n))) for t in range(n + 1)]


def bunting(kd, a3, b3, sag, seed):
    """a paper flag string: ink line + little painted triangles (alternating red / terracotta / navy, some only drawn)."""
    rnd = random.Random(seed)
    pts = catenary(a3, b3, sag, 14)
    stroke3(kd.ink, pts, 0.02)
    for i in range(1, len(pts) - 1):
        p = pts[i]
        d = (pts[i + 1] - pts[i - 1]).normalized() * 0.16
        tri = [p - d, p + d, p - V((0, 0, 0.32))]
        if i % 5 == 4:
            stroke3(kd.sketch, [tri[0], tri[2], tri[1]], 0.015)
            continue
        bm = (kd.paintr, kd.terra_r, kd.navy_r)[i % 3]
        f = bm.faces.new([bm.verts.new(v) for v in tri])
        bm.faces.new([bm.verts.new(v) for v in reversed(tri)])


def plaza_market(k, kd):
    """where the villagers pile food for the 'honoured guest': painted offering tables, one finished booth, one booth that is
    only a frame (its canopy drawn), bunting from the theatre towers. Keeps the audience ring and the path to the bell clear."""
    rnd = random.Random(391)
    y = YP
    for (c, yaw, sd) in ((V((3.0, 7.2)), 40.0, 1), (V((-10.6, 17.6)), 75.0, 2), (V((-3.2, 2.4)), 8.0, 3)):
        obox(k.swood, k.ink, (c.x, c.y), (2.0, 0.85, 0.85), y, yaw, ink_w=0.035, rnd=rnd)
        cl = [c + side(yaw) * (sx * 1.05) + fwd(yaw) * (sz * 0.47) for sx, sz in ((-1, -1), (1, -1), (1, 1), (-1, 1))]
        fill(k.paintr if sd != 3 else k.terra_r, ccw(cl), y + 0.865, uv=False)
        for s_ in (-1, 1):
            p0 = c + side(yaw) * 1.05 * s_ + fwd(yaw) * 0.47
            stroke3(k.ink, [B(p0.x, p0.y, y + 0.87), B(p0.x, p0.y, y + 0.55)], 0.03)
        # food: round paper loaves and painted fruit (creature food, not human things)
        for j in range(5):
            p = c + side(yaw) * rnd.uniform(-0.8, 0.8) + fwd(yaw) * rnd.uniform(-0.25, 0.25)
            lathe(k.paperback if j % 2 else k.terrad_r, (p.x, p.y), [(0.0, 0.0), (0.14, 0.03), (0.15, 0.1), (0.08, 0.17), (0.0, 0.19)], seg=6, y0=y + 0.87)
    # a finished booth (south-west rim) and an unfinished one (south rim): posts real, canopy painted / only drawn
    for (c, yaw, done, sd) in ((V((-8.8, 4.4)), 35.0, True, 4), (V((-0.4, 1.6)), 5.0, False, 5)):
        P_ = [c + side(yaw) * sx * 1.2 + fwd(yaw) * sz * 0.8 for sx, sz in ((-1, -1), (1, -1), (1, 1), (-1, 1))]
        for i, p in enumerate(P_):
            if done or i < 2:
                obox(kd.swood, kd.ink, (p.x, p.y), (0.12, 2.4, 0.12), y, yaw, ink_w=0.025)
            else:
                stroke3(kd.sketch, [B(p.x, p.y, y), B(p.x, p.y, y + 2.4)], 0.03)
        top = [B(p.x, p.y, y + 2.4) for p in P_]
        apex = B(c.x, c.y, y + 3.0)
        if done:
            for i in range(4):
                bm = kd.paintr if i % 2 == 0 else kd.terra_r
                f = bm.faces.new([bm.verts.new(top[i]), bm.verts.new(top[(i + 1) % 4]), bm.verts.new(apex)])
                bm.faces.new([bm.verts.new(apex), bm.verts.new(top[(i + 1) % 4]), bm.verts.new(top[i])])
                stroke3(kd.ink, [top[i], apex], 0.025)
            stroke3(kd.ink, top + [top[0]], 0.03)
        else:
            for i in range(4):
                stroke3(kd.sketch, [top[i], apex], 0.025)
            stroke3(kd.sketch, top + [top[0]], 0.025)
        obox(k.swood, k.ink, (c.x, c.y), (1.8, 0.8, 0.6), y, yaw, ink_w=0.03, rnd=rnd)
    # bunting: theatre towers -> lamp posts / bell frame (paper flags over the audience)
    tn, ts = SP(3.95, -0.1), SP(-3.95, -0.1)
    bunting(kd, B(tn.x, tn.y, y + 6.0), B(-6.0, 26.0, y + 2.85), 0.8, 392)
    bunting(kd, B(ts.x, ts.y, y + 6.0), B(BELL_TOWER.x - 0.9, BELL_TOWER.y + 0.3, y + 5.4), 1.0, 393)
    bunting(kd, B(-3.0, 3.0, y + 2.85), B(-11.6, 11.0, y + 2.85), 0.6, 394)
    bunting(kd, B(-11.6, 11.0, y + 2.85), B(-11.5, 19.5, y + 2.85), 0.7, 395)


PORRIDGE_OFF = V((1.2, -1.2))
PORRIDGE_YAW = 300.0


def porridge_stall(k, kd):
    """the porridge stall (z_porridge): a half-built booth — two real posts and half a painted canopy, the rest drawn —
    a big pot on a ring of stones with a ladle, a stack of bowls, a bench of a counter facing the zone."""
    rnd = random.Random(397)
    y = YP
    z = PLAZA_PTS['z_porridge']
    c = z + PORRIDGE_OFF
    yaw = PORRIDGE_YAW                                       # the counter faces the zone and the area camera (west-north-west)
    P_ = [c + side(yaw) * sx * 1.25 + fwd(yaw) * sz * 0.85 for sx, sz in ((-1, -1), (1, -1), (1, 1), (-1, 1))]
    for i, p in enumerate(P_):
        if i in (2, 3):
            obox(kd.swood, kd.ink, (p.x, p.y), (0.13, 2.3, 0.13), y, yaw, ink_w=0.025)
        else:
            stroke3(kd.sketch, [B(p.x, p.y, y), B(p.x, p.y, y + 2.3)], 0.03)
    top = [B(p.x, p.y, y + 2.3) for p in P_]
    apex = B(c.x, c.y, y + 2.9)
    for i in range(4):
        if i == 2:
            for bm in (kd.terra_r,):
                bm.faces.new([bm.verts.new(top[i]), bm.verts.new(top[(i + 1) % 4]), bm.verts.new(apex)])
                bm.faces.new([bm.verts.new(apex), bm.verts.new(top[(i + 1) % 4]), bm.verts.new(top[i])])
            stroke3(kd.ink, [top[i], apex, top[(i + 1) % 4]], 0.025)
        else:
            stroke3(kd.sketch, [top[i], apex], 0.025)
    stroke3(kd.sketch, top + [top[0]], 0.025)
    # counter (front, real) + painted cloth edge
    cc = c + fwd(yaw) * 0.55
    obox(k.swood, k.ink, (cc.x, cc.y), (2.0, 0.9, 0.5), y, yaw, ink_w=0.03, rnd=rnd)
    for j in range(4):
        q = cc + side(yaw) * (-0.7 + j * 0.45)
        lathe(k.paperback, (q.x, q.y), [(0.0, 0.0), (0.08, 0.0), (0.13, 0.08), (0.12, 0.09)], seg=6, y0=y + 0.9, cap=False)   # bowls
    # the pot on its fire stones
    pp = c - fwd(yaw) * 0.25 + side(yaw) * 0.35
    for i in range(7):
        a = 2 * math.pi * i / 7
        q = pp + V((math.cos(a), math.sin(a))) * 0.62
        rock(k.solid, k.ink, None, hexp(q, 0.17, 398 + i), y, 0.18, 1, 398 + i)
    lathe(k.terrad_r, (pp.x, pp.y), [(0.0, 0.18), (0.38, 0.2), (0.52, 0.42), (0.55, 0.72), (0.5, 0.86), (0.53, 0.9)], seg=10, y0=y)
    fill(k.paperback, ccw([pp + V((math.cos(2 * math.pi * i / 10), math.sin(2 * math.pi * i / 10))) * 0.48 for i in range(10)]), y + 0.84, uv=False)
    stroke3(k.ink, [B(pp.x + math.cos(2 * math.pi * i / 12) * 0.54, pp.y + math.sin(2 * math.pi * i / 12) * 0.54, y + 0.91) for i in range(13)], 0.03)
    stroke3(k.ink, [B(pp.x + 0.1, pp.y, y + 0.85), B(pp.x + 0.55, pp.y + 0.3, y + 1.55)], 0.035)               # ladle
    lathe(k.swood, ((pp + V((0.6, 0.33))).x, (pp + V((0.6, 0.33))).y), [(0.0, 0.0), (0.09, 0.0), (0.0, 0.06)], seg=6, y0=y + 1.5)
    for i in range(3):                                                                                                 # steam: pencil wisps
        q = pp + V((rnd.uniform(-0.2, 0.2), rnd.uniform(-0.2, 0.2)))
        stroke3(kd.sketch, [B(q.x, q.y, y + 1.0), B(q.x + 0.1, q.y, y + 1.4), B(q.x - 0.05, q.y, y + 1.8), B(q.x + 0.08, q.y, y + 2.15)], 0.02)
    ground_stroke(k.ink, [z + V((math.cos(t), math.sin(t))) * 1.2 for t in [i * 0.42 for i in range(16)]], y, 0.03)


def vista_plaza(kv):
    """the plaza as it really is now, cheap (~2.6k tris), for Vista_fall / Vista_gate: painted ground + stones, the theatre
    frame round the stage (towers, navy back wall, arch, drapes, flame crest, striped canopy), the board frames, the bell
    pavilion, the two finished domed towers and the booths. Same places / yaws as the a_plaza page."""
    rnd = random.Random(911)
    y = YP
    w = ccw(W_PLAZA)
    fill(kv.plaza, w, y + 0.02, uv=False)
    R = 0.85
    dx, dz = math.sqrt(3) * R, 1.5 * R
    for j in range(-12, 26):
        for i in range(-14, 14):
            cx = i * dx + (dx / 2 if j % 2 else 0)
            cz = 10.0 + j * dz
            p = V((cx, cz))
            if not inside(p, w) or poly_dist(p, w) < 0.9 or rnd.random() > 0.7 - 0.03 * max(0.0, (p - ST_C).length - 4.0):
                continue
            hx = [V((cx + 0.9 * R * math.cos(RAD(60 * t + 30)), cz + 0.9 * R * math.sin(RAD(60 * t + 30)))) for t in range(6)]
            fill(kv.stones, ccw(hx), y + 0.035, uv=False)
    stroke3(kv.ink, [B(p.x, p.y, y + 0.06) for p in w] + [B(w[0].x, w[0].y, y + 0.06)], 0.1)
    # stage (as Stage.fbx: base, steps, backdrop, curtains, lamps)
    W_ = lambda lx, lz: (ST_C.x + lx * math.cos(RAD(ST_YAW)) + lz * math.sin(RAD(ST_YAW)), ST_C.y - lx * math.sin(RAD(ST_YAW)) + lz * math.cos(RAD(ST_YAW)))
    box(kv.stage, W_(0, 0), (6.1, 1.2, 4.6), y, ST_YAW)
    box(kv.stage, W_(0, 2.5), (2.6, 0.45, 0.7), y, ST_YAW)
    box(kv.navy, W_(0, -2.2), (5.6, 3.6, 0.12), y + 1.2, ST_YAW)
    for lx in (-2.3, 2.3):
        box(kv.curtain, W_(lx, -1.9), (1.2, 3.4, 0.25), y + 1.25, ST_YAW)
    # theatre frame: back wall + navy panel + towers + arch beam + crest + drapes + canopy
    m = SP(0, -2.85)
    box(kv.terra, (m.x, m.y), (6.6, 6.5, 0.5), y, ST_YAW)
    for i in range(6):
        q = SP(-2.3 + i * 0.9, -2.49)
        box(kv.glow, (q.x, q.y), (0.18, 0.24, 0.05), y + 2.2 + (i % 3) * 0.6, ST_YAW)
    for (ka, top) in ((3.95, False), (-3.95, True)):
        c = SP(ka, -0.9)
        box(kv.terra, (c.x, c.y), (1.55, 6.2, 1.55), y, ST_YAW)
        box(kv.terrad, (c.x, c.y), (1.75, 0.35, 1.75), y + 6.2, ST_YAW)
        if top:
            lathe(kv.terra, (c.x, c.y), [(0.95, 0.0), (0.95, 1.5), (0.85, 1.75)], seg=8, y0=y + 6.55)
            lathe(kv.terrad, (c.x, c.y), [(0.85, 0.0), (0.6, 0.6), (0.0, 1.2)], seg=8, y0=y + 8.3, cap=False)
        else:
            for t in range(3):
                stroke3(kv.ink, [B(c.x + math.cos(2 * math.pi * u / 8) * 0.95, c.y + math.sin(2 * math.pi * u / 8) * 0.95, y + 7.0 + t * 0.9) for u in range(0, 9, 2)], 0.06)
            stroke3(kv.ink, [B(c.x, c.y, y + 6.5), B(c.x, c.y, y + 11.0)], 0.07)
        box(kv.glow, ((c + FW * 0.8).x, (c + FW * 0.8).y), (0.25, 0.35, 0.05), y + 4.2, ST_YAW)
    a = SP(0, -0.9)
    box(kv.terrad, (a.x, a.y), (8.6, 0.75, 1.0), y + 5.9, ST_YAW)
    cc = a + FW * 0.56
    for i in range(7):
        t0, t1 = math.pi * i / 7, math.pi * (i + 1) / 7
        tm = (t0 + t1) / 2
        rr = 1.9 if i % 2 == 0 else 1.4
        tri = [B(*(cc + AX * (math.cos(t0) * 0.85)), y + 6.65 + math.sin(t0) * 0.85), B(*(cc + AX * (math.cos(t1) * 0.85)), y + 6.65 + math.sin(t1) * 0.85),
               B(*(cc + AX * (math.cos(tm) * rr)), y + 6.65 + math.sin(tm) * rr)]
        bm = kv.paintr if i % 2 == 0 else kv.terra
        bm.faces.new([bm.verts.new(v) for v in tri])
        bm.faces.new([bm.verts.new(v) for v in reversed(tri)])
    vdisc(kv.glow, cc + FW * 0.01, y + 6.65, 0.85, AX, 12, half=True)
    for ka in (4.75, -4.75):
        p0, p1 = SP(ka, 0.08), SP(ka - math.copysign(1.6, ka), 0.08)
        q = [B(p0.x, p0.y, y + 5.85), B(p1.x, p1.y, y + 5.85), B(p1.x, p1.y, y + 0.9), B(p0.x, p0.y, y + 0.9)]
        kv.curtain.faces.new([kv.curtain.verts.new(v) for v in q])
        kv.curtain.faces.new([kv.curtain.verts.new(v) for v in reversed(q)])
    for i in range(6):
        ka0, ka1 = -3.3 + i * 1.1, -3.3 + (i + 1) * 1.1
        bm = kv.paintr if i % 2 == 0 else kv.terra
        q = [B(*SP(ka0, -1.45), y + 7.4), B(*SP(ka1, -1.45), y + 7.4), B(*SP(ka1, -5.6), y + 4.6), B(*SP(ka0, -5.6), y + 4.6)]
        bm.faces.new([bm.verts.new(v) for v in q])
        bm.faces.new([bm.verts.new(v) for v in reversed(q)])
    # board frames (painted arcade), the far-right frame half built
    for (k0, k1, i) in ((10.4, 6.6, 0), (6.6, 3.4, 1), (-3.4, -6.6, 2), (-6.6, -10.4, 3)):
        p0, p1 = SP(k0, -0.55), SP(k1, -0.55)
        c = (p0 + p1) / 2
        h = (4.1 if i in (1, 2) else 3.6) * (0.5 if i == 3 else 1.0)
        box(kv.terra, (c.x, c.y), ((p1 - p0).length, h, 0.45), y, ST_YAW)
        b = BOARDS[i]
        box(kv.solid, (b.x, b.y), (2.4, 1.6, 0.1), y + 1.3, ST_YAW)
    # bell pavilion
    c = BELL_TOWER
    box(kv.solid, (c.x, c.y), (2.2, 0.6, 2.2), y, 250)
    for sx, sz in ((-1, -1), (1, -1), (1, 1), (-1, 1)):
        p = c + side(250) * sx * 0.95 + fwd(250) * sz * 0.95
        box(kv.stage, (p.x, p.y), (0.26, 3.5, 0.26), y + 0.6, 250)
    box(kv.stage, (c.x, c.y), (2.4, 0.3, 0.3), y + 3.8, 250)
    lathe(kv.terrad, (c.x, c.y), [(0.0, -1.45), (0.86, -1.45), (0.6, -0.8), (0.38, -0.08), (0.12, 0.0)], seg=8, y0=y + 3.8)
    # the two finished domed towers + the east house + two booths
    SL.lathe_tower(kv, (-9.0, 32.4), 2.9, 5.6, 1.0, 0.35, seed=12)
    SL.lathe_tower(kv, (7.0, 26.6), 2.9, 5.6, 1.15, 0.3, seed=13)
    box(kv.terra, (11.6, 8.2), (3.2, 4.4, 3.0), y, 255)
    for (c, yaw) in ((V((-8.8, 4.4)), 35.0), (PLAZA_PTS['z_porridge'] + PORRIDGE_OFF, PORRIDGE_YAW)):
        P_ = [c + side(yaw) * sx * 1.2 + fwd(yaw) * sz * 0.8 for sx, sz in ((-1, -1), (1, -1), (1, 1), (-1, 1))]
        top = [B(p.x, p.y, y + 2.4) for p in P_]
        apex = B(c.x, c.y, y + 3.0)
        for i in range(4):
            bm = kv.paintr if i % 2 == 0 else kv.terra
            bm.faces.new([bm.verts.new(top[i]), bm.verts.new(top[(i + 1) % 4]), bm.verts.new(apex)])
        box(kv.stage, (c.x, c.y), (1.8, 0.8, 0.6), y, yaw)
    for (x, z) in ((-11.5, 19.5), (-11.6, 11.0), (-3.0, 3.0), (-6.0, 26.0)):
        stroke3(kv.ink, [B(x, z, y), B(x, z, y + 2.9)], 0.1)
        box(kv.glow, (x, z), (0.3, 0.4, 0.3), y + 2.6, 0)
    for (cc, yaw, hh, paint) in (((15.2, 21.6), 200, 5.2, 0.8), ((20.6, 23.6), 205, 4.6, 0.55), ((26.0, 25.0), 212, 4.2, 0.3)):   # the alley beyond
        box(kv.solid, cc, (3.2, hh * (1 - paint), 3.0), y, yaw)
        box(kv.terra, cc, (3.22, hh * paint, 3.02), y + hh * (1 - paint), yaw)


def vista_depot(kv, real_shed=False):
    """the collectors' depot below the plaza's south-east rim (cheap copy): yard, shed, sacks, the cart, the road east."""
    y = YC
    yard = ccw([V(p) for p in [(6.0, -2.4), (22.0, -2.6), (29.0, -3.0), (29.0, -7.0), (24.5, -14.0), (12.0, -13.5), (5.0, -10.5)]])
    fill(kv.walk, yard, y, uv=False)
    walls(kv.solid, kv.ink, None, yard, y, FLOOR, 391, ledge=1.2, ledge_out=0.3, hatch_floor=y - 2, hatch_density=0.0, deep=kv.dark, deep_y=y - 2.5,
          vstroke=0.2)
    x0, x1, z0, z1 = SHED
    box(kv.solid, (x1 - 0.15, (z0 + z1) / 2), (0.3, 3.0, z1 - z0), y, 0)            # back wall only; the shed front stays open
    box(kv.solid, ((x0 + x1) / 2, z1 - 0.15), (x1 - x0, 2.9, 0.3), y, 0)
    for zz in (z0, (z0 + z1) / 2, z1):
        box(kv.wood, (x0 + 0.2, zz), (0.26, 3.2, 0.26), y, 0)
    for i in range(3):
        box(kv.solid, (x1 - 1.0, z0 + 1.2 + i * 1.8), (1.0, 1.0, 1.1), y, 15 * i)
    rp = [B(x0, z1, y + 3.0), B(x1, z1, y + 3.0), B(x1, (z0 + z1) / 2, y + 4.4), B(x0, (z0 + z1) / 2, y + 4.4)]
    add_face(kv.paperback, [kv.paperback.verts.new(v) for v in rp], None)
    for i in range(6):
        xx = x0 + (x1 - x0) * i / 5
        stroke3(kv.ink, [B(xx, z0, y + 3.0), B(xx, (z0 + z1) / 2, y + 4.4)], 0.05)
    stroke3(kv.ink, [B(x0, (z0 + z1) / 2, y + 4.6), B(x1, (z0 + z1) / 2, y + 4.6)], 0.08)
    stroke3(kv.sketch, [B(x0, z1, y + 3.0), B(x0, (z0 + z1) / 2, y + 4.6)], 0.06)
    for i, (c, r) in enumerate(((V((12.0, -11.0)), 0.6), (V((13.2, -11.6)), 0.5), (V((10.8, -10.6)), 0.55))):
        box(kv.solid, (c.x, c.y), (r * 2, r * 1.6, r * 1.8), y, 20 * i)
    box(kv.wood, (13.4, -7.2), (1.4, 0.9, 2.2), y + 0.3, 90)
    box(kv.books['M_BookRed'], (13.4, -7.0), (0.5, 0.2, 0.4), y + 1.2, 20)


def vista_field(kv, c0=None, detail=1.0):
    """field + pond seen from afar: earth disc, radial furrows to the black pond, the stepped apron, two carts."""
    y = YF
    fd = ccw(jag(W_FIELD[:], 3.0, 0.4, 401))
    fill(kv.earth, fd, y, uv=False)
    walls(kv.solid, kv.ink, None, ccw(P_FIELD), y, FLOOR, 402, ledge=1.4, ledge_out=0.3, hatch_floor=y - 2, hatch_density=0.0, deep=kv.dark,
          deep_y=y - 2.6, vstroke=0.15)
    fill(kv.walk, ccw(P_FIELD), y - 0.02, holes=[fd], uv=False)
    rnd = random.Random(403)
    for i in range(int(16 * detail)):
        a = RAD(98 + i * 6.3)
        p0 = POND_C + V((math.cos(a), math.sin(a))) * 12.5
        p1 = POND_C + V((math.cos(a), math.sin(a))) * rnd.uniform(22, 30)
        if inside(p1, W_FIELD) or inside((p0 + p1) / 2, W_FIELD):
            ground_stroke(kv.ink, [p0, p1], y, 0.12)
    ap = [pc(a, APRON_R) for a in range(0, 360, 15)]
    fill(kv.walk, ccw(ap), YO, holes=[ccw([pc(a, POND_R) for a in range(0, 360, 20)])], uv=False)
    fill(kv.pond, ccw([pc(a, POND_R) for a in range(0, 360, 20)]), YPOND, uv=False)
    stroke3(kv.ink, [B(*pc(a, APRON_R), YO + 0.03) for a in range(0, 361, 15)], 0.1)
    for (c, yaw) in ((V((40.2, -6.4)), 135), (V((44.0, -8.6)), 135)):
        box(kv.wood, (c.x, c.y), (1.4, 0.9, 2.2), y + 0.3, yaw)
    for i in range(int(12 * detail)):
        a0, a1 = RAD(100 + i * 8.0), RAD(100 + i * 8.0 + 3.2)
        wedge = [POND_C + V((math.cos(a0), math.sin(a0))) * 13.0, POND_C + V((math.cos(a1), math.sin(a1))) * 13.0,
                 POND_C + V((math.cos(a1), math.sin(a1))) * 26.0, POND_C + V((math.cos(a0), math.sin(a0))) * 26.0]
        if all(inside(q, W_FIELD) for q in wedge):
            fill(kv.soil, ccw(wedge), y + 0.02, uv=False)
    for a in (134, 152):
        g = pc(a, STEP_R + 0.9)
        box(kv.solid, (g.x, g.y), (1.0, 2.6, 1.0), y, 0)
        stroke3(kv.ink, [B(g.x, g.y, y + 2.6), B(g.x, g.y, y + 4.6)], 0.08)


def vista_tree(kv, detail=1.0):
    """the hollow tree's outside: a huge drawn trunk with roots; the crown only in pencil (seen above the alley's end)."""
    y = YH
    c = TREE_C
    bark_ring(kv, c, 5.6, lambda a: 8.5 + 1.5 * math.sin(a * 3) - (2.5 if math.cos(a - RAD(220)) > 0.85 else 0.0), y, 14, 411, bm_out=kv.bark,
              bm_in=kv.paperback, thick=0.6, pencil_above=lambda a: 13.5 + 2 * math.sin(a * 2), ink_rim=True)
    rnd = random.Random(412)
    for i in range(int(7 * detail)):
        a = RAD(150 + i * 30 + rnd.uniform(-8, 8))
        p0 = c + V((math.cos(a), math.sin(a))) * 5.0
        p1 = c + V((math.cos(a), math.sin(a))) * rnd.uniform(7.5, 9.5)
        root(kv, [B(p0.x, p0.y, y + 1.6), B((p0 + p1).x / 2, (p0 + p1).y / 2, y + 0.9), B(p1.x, p1.y, y - 0.3)], 0.7, 0.18, 413 + i, bm=kv.bark)
    # crown: big pencil scribble loops + a few drawn branches
    for i in range(10):
        a = RAD(rnd.uniform(0, 360))
        p0 = c + V((math.cos(a), math.sin(a))) * 3.5
        p1 = c + V((math.cos(a), math.sin(a))) * rnd.uniform(7, 11)
        stroke3(kv.ink if i % 3 == 0 else kv.sketch, [B(p0.x, p0.y, y + 9.5), B(*((p0 + p1) / 2), y + 12.5 + rnd.uniform(0, 2)), B(p1.x, p1.y, y + 14.5 + rnd.uniform(0, 3))], 0.08 if i % 3 == 0 else 0.05)
    for i in range(int(9 * detail)):
        a = RAD(rnd.uniform(0, 360))
        cc = c + V((math.cos(a), math.sin(a))) * rnd.uniform(4, 9)
        yy = y + rnd.uniform(13, 18)
        r = rnd.uniform(1.6, 2.6)
        pts = [B(cc.x + math.cos(t * 0.5) * r * (1 + 0.15 * math.sin(t * 2.3)), cc.y + math.sin(t * 0.5) * r * 0.7, yy + math.sin(t * 0.5) * r * 0.6) for t in range(0, 26)]
        stroke3(kv.sketch, pts, 0.05)


def build_plaza(A):
    k, kd, kv, kl, kb = Kit2(), Kit2(), Kit2(), Kit2(), Kit2()
    # plateau: painted walk + margin + rim walls to the abyss (the depot's side is lower, -2.5, built on its own page)
    plateau(k, jag(P_PLAZA, 2.2, 0.3, 300), [W_PLAZA], YP, 300, walk_key='painted', ledge=1.4,
            unf=lambda a, b: (a + b).y / 2 > 30.0 and (a + b).x / 2 < -6.0)
    theatre(k, kd)
    board_wall(k, kd)
    hp, hang = bell_tower(k, kd, kb)
    plaza_ground(k)
    plaza_edges(k, kd)
    plaza_market(k, kd)
    porridge_stall(k, kd)
    # light: warm pools under the stage and the lamps (additive decals)
    light_pool(kl, SP(0, 3.0), 4.2, YP)
    for (x, z) in ((-11.5, 19.5), (-11.6, 11.0), (-3.0, 3.0), (-6.0, 26.0)):
        light_pool(kl, V((x, z)), 2.2, YP, seg=16)
    light_pool(kl, PLAZA_PTS['z_porridge'] + PORRIDGE_OFF - fwd(PORRIDGE_YAW) * 0.25, 1.5, YP, seg=14)      # the porridge fire
    # vista: abyss, the depot below (SE), the field and pond far east, the hollow tree far north-east, cave wall, spires
    abyss_floor(kv, (5.0, 10.0), 90.0, 70.0, 395)
    vista_depot(kv)
    vista_field(kv, detail=0.6)
    vista_tree(kv, detail=0.6)
    stacks(kv, [((14.0, 20.0), 1.4, -3.0, []), ((17.0, 6.0), 1.0, -4.5, [('M_BookBlue', 0, 0, 30)]), ((-20.0, 4.0), 1.5, -2.0, []),
                ((3.0, -8.0), 1.0, -5.0, [('M_BookRed', 0, 0, 10)]), ((-14.0, -4.0), 1.2, -6.0, [])], 396)
    vista_spires(kv, (-3.0, 13.0), 102, 397)
    cave(kv, (-3.0, 13.0), 102, 398)
    exits = [(AREA_PLAZA['exits'][0], (-1, 0.03), YP, 'M_PaintRed', False),
             (AREA_PLAZA['exits'][1], (0.9, 0.4), YP, 'M_PaintRed', True),
             (AREA_PLAZA['exits'][2], (0.55, -0.835), YP, 'M_PaintRed', False)]
    return finish_area(A, 'a_plaza', k, kd, kl, kv, top='M_GroundPainted', exits=exits,
                       extra_parts=[('Bell_plaza', kb, ('terrad_r', 'iron', 'ink'), tuple(B(hang.x, hang.y, hp)))])


# ============================================================================================ ALLEY
def kid_house(k, kd):
    """Kinopio's house at the end of the alley: open front (never built - only pencil), so the camera sees inside:
    the brother's lump on a chair, a heap of nose shavings on the floor, a carving board, a small bed."""
    rnd = random.Random(501)
    y = YA
    yaw = K_YAW
    # floor boards (walk is the plain alley ground; boards drawn in ink over it)
    for i in range(7):
        a = KP(-2.1, 1.85 - i * 0.55)
        b = KP(2.1, 1.85 - i * 0.55)
        ground_stroke(k.ink, [a, b], y, 0.03, 0.02)
    # back wall (full) + side walls (south full, north built to 60% then drawn)
    slab_wall(k, KP(2.3, -1.9), KP(-2.3, -1.9), y, 2.9, 0.3, 1.0, 502, bm=k.solid)
    slab_wall(k, KP(-2.3, -1.9), KP(-2.3, 1.9), y, 2.7, 0.3, 1.0, 503, bm=k.solid)
    slab_wall(k, KP(2.3, -1.9), KP(2.3, 1.9), y, 2.8, 0.3, 0.55, 504, bm=k.solid)
    # front: two corner posts real, the wall between only drawn (outline, door, window)
    for kx in (2.3, -2.3):
        p = KP(kx, 1.9)
        obox(k.wood, k.ink, (p.x, p.y), (0.22, 2.7, 0.22), y, yaw, ink_w=0.035)
    stroke3(k.sketch, [B(*KP(2.3, 1.95), y + 2.75), B(*KP(-2.3, 1.95), y + 2.75)], 0.035)
    stroke3(k.sketch, [B(*KP(0.5, 1.95), y), B(*KP(0.5, 1.95), y + 1.9), B(*KP(-0.6, 1.95), y + 1.9), B(*KP(-0.6, 1.95), y)], 0.03)
    stroke3(k.sketch, [B(*KP(1.9, 1.95), y + 1.2), B(*KP(1.1, 1.95), y + 1.2), B(*KP(1.1, 1.95), y + 1.9), B(*KP(1.9, 1.95), y + 1.9), B(*KP(1.9, 1.95), y + 1.2)], 0.03)
    for t in range(6):
        p = KP(2.3 - t * 0.92, 1.97)
        stroke3(k.sketch, [B(p.x, p.y, y), B(p.x, p.y, y + 0.12 + 0.08 * (t % 2))], 0.03)
    # roof: a lean-to with half the boards on (decor), the other half rafters in ink and pencil
    for i in range(9):
        kx0 = 2.45 - i * 0.55
        if i < 3:
            q = [KP(kx0, 2.3), KP(kx0 - 0.5, 2.3), KP(kx0 - 0.5, -2.2), KP(kx0, -2.2)]
            ys = [y + 2.8, y + 2.8, y + 3.6, y + 3.6]
            add_face(kd.paperback, [kd.paperback.verts.new(B(p.x, p.y, yy)) for p, yy in zip(q, ys)], V((0, 0, 1)))
            stroke3(kd.ink, [B(q[0].x, q[0].y, ys[0] + 0.02), B(q[3].x, q[3].y, ys[3] + 0.02)], 0.03)
        else:
            stroke3(kd.ink if i % 2 else kd.sketch, [B(*KP(kx0, 2.3), y + 2.8), B(*KP(kx0, -2.2), y + 3.6)], 0.04)
    stroke3(kd.ink, [B(*KP(2.45, 2.3), y + 2.82), B(*KP(-2.45, 2.3), y + 2.82)], 0.05)
    # inside: carving board with a knife, a small bed of paper scraps, a shelf with two little puppet heads (unpainted)
    c = KP(-1.4, -1.2)
    obox(k.pwood, k.ink, (c.x, c.y), (1.0, 0.7, 0.6), y, yaw, ink_w=0.03)
    stroke3(k.ink, [B(c.x, c.y, y + 0.72), B(*(c + KX * 0.35), y + 0.74)], 0.025)
    c = KP(1.5, -1.25)
    obox(k.paperback, k.ink, (c.x, c.y), (1.2, 0.3, 1.0), y, yaw, ink_w=0.03)
    for i in range(2):
        hc = KP(-0.6 + i * 0.5, -1.75)
        box(k.pwood, (hc.x, hc.y), (0.12, 0.05, 0.25), y + 1.5, yaw)
        lathe(k.puppet, (hc.x, hc.y), [(0.0, 0.0), (0.12, 0.05), (0.13, 0.17), (0.08, 0.27), (0.0, 0.29)], seg=6, y0=y + 1.55)
    box(k.pwood, (KP(-0.35, -1.75).x, KP(-0.35, -1.75).y), (1.3, 0.06, 0.3), y + 1.5, yaw)
    # the heap of nose shavings: curled pale-wood ribbons in a cone, a few scattered to the door (z_sawdust)
    sc = ALLEY_PTS['z_sawdust']
    for i in range(34):
        a = rnd.uniform(0, 2 * math.pi)
        rr = 0.42 * math.sqrt(rnd.random())
        hh = 0.22 * (1 - rr / 0.42) + rnd.uniform(0, 0.04)
        p = sc + V((math.cos(a), math.sin(a))) * rr
        ang = rnd.uniform(0, 2 * math.pi)
        pts = [B(p.x + math.cos(ang + t * 1.3) * 0.06, p.y + math.sin(ang + t * 1.3) * 0.06, y + hh + t * 0.012) for t in range(5)]
        stroke3(k.pwood, pts, 0.022)
    cone = lathe(k.pwood, (sc.x, sc.y), [(0.36, 0.0), (0.2, 0.1), (0.0, 0.17)], seg=7, y0=y)
    for i in range(8):
        p = sc + (KP(0, 2.0) - sc) * rnd.uniform(0.3, 0.95) + V((rnd.uniform(-0.4, 0.4), rnd.uniform(-0.4, 0.4)))
        stroke3(k.pwood, [B(p.x, p.y, y + 0.02), B(p.x + 0.07, p.y + 0.03, y + 0.04)], 0.02)


def alley_houses(k, kd):
    """level-built house shells between the FBX houses: the farther from the plaza, the less of the form exists."""
    y = YA
    unfinished_house(k, (17.8, 12.7), 2.6, 1.8, 2.0, 60, y, 511, roof=1.3)                    # south side: only the front wall stands
    unfinished_house(k, (30.2, 28.4), 3.0, 2.2, 2.5, 72, y, 512, roof=1.5)                    # behind the crack, never finished
    # the neighbour's house (z_alley_window): only its lane wall is built, with a real window and sill looking onto the lane
    # in front of Kinopio's door; the rest of the house is a drawn box (the neighbour stands inside at neighbor_window)
    yaw = 200.0
    wc = V((29.0, 25.5))
    w0, w1 = wc - side(yaw) * 0.95, wc + side(yaw) * 0.95
    hw = 0.5
    win0, win1 = wc - side(yaw) * hw, wc + side(yaw) * hw
    slab_wall(k, w0, win0, y, 2.5, 0.25, 1.0, 513, bm=k.solid, planks=0.0)
    slab_wall(k, win1, w1, y, 2.5, 0.25, 0.7, 514, bm=k.solid)
    box(k.solid, (wc.x, wc.y), (2 * hw, 0.95, 0.25), y, yaw)                       # wall under the sill
    box(k.solid, (wc.x, wc.y), (2 * hw, 0.5, 0.25), y + 2.0, yaw)                  # lintel
    box(k.wood, ((wc + fwd(yaw) * 0.12).x, (wc + fwd(yaw) * 0.12).y), (2 * hw + 0.3, 0.07, 0.32), y + 0.95, yaw)   # sill
    for s_ in (-1, 1):
        q = wc + side(yaw) * hw * s_ + fwd(yaw) * 0.14
        stroke3(k.ink, [B(q.x, q.y, y + 0.95), B(q.x, q.y, y + 2.0)], 0.045)
        sh = wc + side(yaw) * (hw + 0.45) * s_ + fwd(yaw) * 0.16                    # one shutter real, one drawn
        bm = k.swood if s_ < 0 else None
        if bm is not None:
            box(bm, (sh.x, sh.y), (0.48, 1.0, 0.04), y + 1.0, yaw)
        else:
            stroke3(k.sketch, [B(sh.x, sh.y, y + 1.0), B(sh.x, sh.y, y + 2.0), B((sh - side(yaw) * 0.48).x, (sh - side(yaw) * 0.48).y, y + 2.0)], 0.03)
    stroke3(k.ink, [B(*(wc + fwd(yaw) * 0.14 - side(yaw) * hw), y + 2.0), B(*(wc + fwd(yaw) * 0.14 + side(yaw) * hw), y + 2.0)], 0.045)
    fill(k.dark, ccw([wc + side(yaw) * hw * sx + fwd(yaw) * (-0.2 + 0.12 * sz) for sx, sz in ((-1, 0), (1, 0), (1, 1), (-1, 1))]), y + 0.96, uv=False)
    back = [wc - fwd(yaw) * 1.6 + side(yaw) * sx * 0.95 for sx in (-1, 1)]
    for p in (w0, w1) + tuple(back):
        stroke3(k.sketch, [B(p.x, p.y, y), B(p.x, p.y, y + 2.5)], 0.03)
    stroke3(k.sketch, [B(w0.x, w0.y, y + 2.5), B(back[0].x, back[0].y, y + 2.5), B(back[1].x, back[1].y, y + 2.5), B(w1.x, w1.y, y + 2.5)], 0.03)
    compass(k, ALLEY_PTS['z_alley_window'], 0.7, y, 515, 0.6)
    lamp = wc - fwd(yaw) * 0.55
    box(k.wood, (lamp.x, lamp.y), (0.5, 0.75, 0.4), y, yaw)                        # a table inside with a lit lamp (the window reads)
    light_glow(k, (lamp.x, lamp.y), y + 0.75, 0.2)


def alley_ground(k):
    y = YA
    rnd = random.Random(521)
    lane = [V((12.4, 15.2)), V((17.5, 17.6)), V((23.0, 19.4)), V((28.5, 20.6)), V((31.6, 21.2))]
    road = ccw(strip_poly(lane, 1.45))
    fill(k.road, road, y + 0.012, uv=False)
    in_road = lambda p: inside(p, road)
    hex_lines(k.ink, road, y, 0.55, 522, keep=0.7, origin=(20.0, 18.0), w=0.035)
    hex_lines(k.ink, ccw(Y_ALLEY), y, 0.9, 523, keep=0.22, origin=(20.0, 18.0), avoid=in_road)
    for side_ in (1, -1):
        pts = [p + V((-(lane[min(i + 1, 4)] - lane[max(i - 1, 0)]).normalized().y, (lane[min(i + 1, 4)] - lane[max(i - 1, 0)]).normalized().x)) * 1.5 * side_
               for i, p in enumerate(lane)]
        ground_stroke(k.ink, pts, y, 0.07)
    cracks(k.ink, ccw(Y_ALLEY), y, 10, 524, avoid=in_road)
    # 'sitting places': drawn arcs round each chair; worn rings where chairs were dragged
    for (c, yaw) in ALLEY_CHAIRS:
        pts = [c + V((math.cos(t), math.sin(t))) * 0.95 for t in [i * 0.35 for i in range(15)]]
        ground_stroke(k.ink, pts, y, 0.035)
        compass(k, c, 0.55, y, 525 + int(c.x), 0.6)
    # drag marks from each chair toward the lane (chairs are turned to face the passers-by)
    for (c, yaw) in ALLEY_CHAIRS[:3]:
        d = fwd(yaw)
        for s_ in (-0.2, 0.2):
            n = V((-d.y, d.x)) * s_
            ground_stroke(k.ink, [c + n + d * 0.5, c + n + d * 1.6], y, 0.025)
    ticks_along(k, [V((13.8, 13.2)), V((19.6, 15.6)), V((27.0, 18.0))], y, 0.6, 526, side=1)
    for (cc, rx, rz, rot, sd) in (((24.0, 18.0), 1.2, 0.45, 0.3, 1), ((15.0, 18.0), 1.0, 0.4, -0.3, 2), ((31.0, 23.2), 0.8, 0.35, 0.8, 3)):
        smudge(k, cc, rx, rz, rot, y, 527 + sd)


def build_alley(A):
    k, kd, kv = Kit2(), Kit2(), Kit2()
    holes = []
    plateau(k, jag(P_ALLEY, 2.2, 0.3, 500), [Y_ALLEY, ccw(strip_poly(CRACK, 0.45))], YA, 500, ledge=1.3,
            unf=lambda a, b: (a + b).y / 2 > 28.0 and (a + b).x / 2 < 26.0)
    kid_house(k, kd)
    alley_houses(k, kd)
    kl = Kit2()
    light_pool(kl, KP(0.3, 0.2), 1.6, YA, seg=16)       # a candle stub on the floor by the brother's chair (point light: see lights2)
    lathe(k.glow, (KP(-0.5, -0.4).x, KP(-0.5, -0.4).y), [(0.05, 0.0), (0.05, 0.14), (0.0, 0.16)], seg=6, y0=YA)
    alley_ground(k)
    # the crack: two tall layered rocks squeezing a 0.9 m slot beside Kinopio's house (hero squeezes, the kid slips)
    cn = V((-0.341, 0.94))
    for (p, h, sd) in ((V((31.1, 26.2)), 3.2, 531), (V((33.0, 26.95)), 4.2, 532), (V((34.9, 27.85)), 3.6, 533), (V((36.4, 25.9)), 2.6, 534)):
        poly = hexp(p, 0.8, sd, sq=0.7)
        if sd == 532:
            rock(k.solid, k.ink, k.hatch, poly, YA, h, 3, sd)
        else:
            rock_wire(k, poly, YA, h, 2, sd, wire=0.4)
    stroke3(k.ink, [B(30.7, 24.4, YA + 0.02), B(34.4, 25.75, YA + 0.02), B(35.8, 26.8, YA + 0.02)], 0.05)
    # south rail (paper stone posts + drawn rail) with the gap for the field stairs
    balustrade(k, [V((12.4, 13.5)), V((16.4, 14.7)), V((19.6, 16.0)), V((23.4, 17.2)), V((27.4, 18.0))], YA, 0.4, 541, bm=k.solid, h=0.9, post=0.28)
    # washing lines across the lane: house fronts -> rail posts, paper sheets and a puppet shirt hung to dry (decor)
    for (a2, b2, sd) in (((15.6, 20.2), (16.6, 14.9), 545), ((21.2, 22.2), (21.4, 16.8), 546), ((26.4, 23.4), (27.2, 18.1), 547)):
        A3, B3 = B(a2[0], a2[1], YA + 3.2), B(b2[0], b2[1], YA + 2.2)
        pts = catenary(A3, B3, 0.5, 10)
        stroke3(kd.ink, pts, 0.02)
        stroke3(kd.ink, [B(b2[0], b2[1], YA), B3], 0.05)
        rr = random.Random(sd)
        for i in (2, 4, 5, 7):
            p = pts[i]
            d = (pts[i + 1] - pts[i - 1]).normalized() * rr.uniform(0.18, 0.3)
            hh = rr.uniform(0.4, 0.7)
            bm = (kd.paperback, kd.torn, kd.paint, kd.paperback)[i % 4]
            q = [p - d, p + d, p + d - V((0, 0, hh)), p - d - V((0, 0, hh * 0.9))]
            bm.faces.new([bm.verts.new(v) for v in q])
            bm.faces.new([bm.verts.new(v) for v in reversed(q)])
            stroke3(kd.ink, [q[0], q[3], q[2], q[1]], 0.012)
    balustrade(k, [V((30.0, 18.6)), V((31.6, 19.0)), V((33.0, 19.5))], YA, 1.0, 542, bm=k.solid, h=0.9, post=0.28)
    top, d, sw, n, rise, run = ALLEY_STAIR
    steps(k, top, d, sw, n, rise, run, YA, 5, seed=543, down=True)
    pennant(k.solid, k.paintr, k.ink, top - V((-d.y, d.x)) * 1.25 + d * 0.2, YA, h=2.0, d=(d.x, d.y))
    # back ledges behind the houses (frame the top of the page)
    for (c, rx, h, sd) in (((13.0, 24.6), 1.6, 2.2, 551), ((18.6, 27.4), 1.8, 3.4, 552), ((24.6, 28.6), 1.6, 2.8, 553), ((34.8, 29.6), 1.4, 4.6, 554)):
        rock(k.solid, k.ink, k.hatch, hexp(c, rx, sd, 0.0, sq=0.6), YA, h, 2, sd)
    # the hollow tree rising behind the end of the alley (decor: drawn crown)
    vista_tree(kd, detail=1.0)
    # vista: abyss, field far south-east below, cave, spires
    abyss_floor(kv, (25.0, 18.0), 80.0, 60.0, 561)
    vista_field(kv, detail=0.5)
    stacks(kv, [((10.0, 26.0), 1.2, -3.0, []), ((38.0, 16.0), 1.4, -4.0, [('M_BookGreen', 0, 0, 20)]), ((30.0, 36.0), 1.6, -2.0, [])], 562)
    vista_spires(kv, (23.0, 20.0), 72, 563)
    cave(kv, (23.0, 20.0), 72, 564)
    exits = [(AREA_ALLEY['exits'][0], (-0.9, -0.45), YA, 'M_PaintRed', True),
             (AREA_ALLEY['exits'][1], (0.42, -0.91), YA, 'M_PaintRed', False),
             (AREA_ALLEY['exits'][2], (0.78, 0.62), YA, 'M_PaintRed', False)]
    return finish_area(A, 'a_alley', k, kd, kl, kv, exits=exits)


# ============================================================================================ HIDEOUT
def build_hideout(A):
    """the hollow of the old tree: small, low, crowded with the kid's secrets. The camera-side half of the trunk is only
    a stump + a few pencil strokes (the cutaway is the 'unfinished' half); the far half is warm bark with root shelves,
    the stash in its human colours, the wall drawing, a nest and a knot-hole of warm light."""
    k, kd, kl, kv, kf = Kit2(), Kit2(), Kit2(), Kit2(), Kit2()
    y = YH
    c = H_C
    rnd = random.Random(601)
    walk = ccw(HIDE_WALK)
    fill(k.earthwalk, walk, y, steiner=grid_pts(walk, 1.2, 602))
    outer = ccw([V((c.x + math.cos(2 * math.pi * i / 22) * 7.0 * (1 + 0.08 * math.sin(i * 1.9)), c.y + math.sin(2 * math.pi * i / 22) * 6.0 * (1 + 0.08 * math.sin(i * 1.9))))
                 for i in range(22)])
    fill(k.margin, outer, y, holes=[walk], steiner=grid_pts(outer, 2.4, 603))
    walls(k.solid, k.ink, k.hatch, outer, y, FLOOR, 604, ledge=1.2, ledge_out=0.3, hatch_floor=y - 3, deep=k.dark, deep_y=y - 3.2, sketch=k.sketch, torn=k.torn)
    view = RAD(90 - CAM_HIDE['yaw'])
    ring_r = H_WALL_R

    def hwall(a):
        f = math.cos(a - view)                  # +1 far side (the camera looks at it), -1 near side
        if f < -0.2:
            return 0.45 + 0.3 * math.sin(a * 5)
        return 0.7 + 4.6 * min(1.0, (f + 0.2) / 0.85) + 0.3 * math.sin(a * 3)
    gap = lambda a: abs(math.atan2(math.sin(a - RAD(204)), math.cos(a - RAD(204)))) < RAD(13)
    bark_ring(k, c, ring_r, lambda a: 0.0 if gap(a) else hwall(a), y, 24, 605, bm_out=k.bark, bm_in=k.bark, thick=0.45,
              pencil_above=None)
    # the cut side: a few pencil verticals and one contour where the trunk should close (low: never across the view)
    for i in range(24):
        a = 2 * math.pi * i / 24
        if math.cos(a - view) < -0.35 and i % 2 == 0 and not gap(a):
            p = c + V((math.cos(a), math.sin(a))) * ring_r
            stroke3(k.sketch, [B(p.x, p.y, y + hwall(a)), B(p.x, p.y, y + hwall(a) + rnd.uniform(0.5, 1.1))], 0.025)
    pts = [B(*(c + V((math.cos(a), math.sin(a))) * ring_r), y + 1.6) for a in [view + math.pi + RAD(t) for t in range(-60, 61, 10)]]
    stroke3(k.sketch, pts, 0.025)
    # roof: the hollow closes over the far half toward a knot hole (decor)
    for i in range(14):
        a = 2 * math.pi * i / 14
        a2 = a + 2 * math.pi / 14
        if math.cos(a - view) > 0.05 and math.cos(a2 - view) > 0.05:
            r0 = ring_r - 0.25
            p0 = c + V((math.cos(a), math.sin(a))) * r0
            p1 = c + V((math.cos(a2), math.sin(a2))) * r0
            q0 = c + V((0.4, 0.5)) + V((math.cos(a), math.sin(a))) * 1.3
            q1 = c + V((0.4, 0.5)) + V((math.cos(a2), math.sin(a2))) * 1.3
            q = [kd.bark.verts.new(B(p0.x, p0.y, y + hwall(a) - 0.05)), kd.bark.verts.new(B(p1.x, p1.y, y + hwall(a2) - 0.05)),
                 kd.bark.verts.new(B(q1.x, q1.y, y + 6.6)), kd.bark.verts.new(B(q0.x, q0.y, y + 6.6))]
            add_face(kd.bark, q, V((0, 0, -1)))
            if i % 2 == 0:
                stroke3(kd.ink, [B(p0.x, p0.y, y + hwall(a)), B(q0.x, q0.y, y + 6.6)], 0.03)
    # inner roots climbing the far wall
    for i in range(7):
        a = view + RAD(-80 + i * 27 + rnd.uniform(-6, 6))
        p0 = c + V((math.cos(a), math.sin(a))) * (ring_r - 0.4)
        p1 = c + V((math.cos(a), math.sin(a))) * (ring_r - 1.2)
        root(k, [B(p0.x, p0.y, y + rnd.uniform(1.2, 2.6)), B(*((p0 + p1) / 2), y + 0.35), B(p1.x, p1.y, y - 0.05)], 0.16, 0.06, 610 + i)
    # root shelves holding the stash (three tiers on the right, one by the nest) + human things in their own colours
    stash = HIDE_PTS['z_hideout_stash']
    sdir = (stash - c).normalized()
    yaw_ = math.degrees(math.atan2(sdir.x, sdir.y))
    sn = side(yaw_)
    shelves = []
    for (hh, w_, off) in ((0.7, 2.0, 0.0), (1.35, 1.7, 0.25), (2.0, 1.2, -0.2)):
        sc_ = c + sdir * (ring_r - 0.6) + sn * off
        obox(k.pwood, k.ink, (sc_.x, sc_.y), (w_, 0.12, 0.55), y + hh, yaw_, ink_w=0.035)
        for s_ in (-1, 1):
            p = sc_ + sn * (w_ / 2 - 0.12) * s_
            stroke3(k.ink, [B(p.x, p.y, y + hh), B(p.x, p.y, y + hh - 0.35)], 0.03)
        shelves.append((sc_, y + hh + 0.12, yaw_, w_))
    for si, (sc_, yy, yw, w_) in enumerate(shelves):
        n = int(w_ / 0.3)
        for j in range(n):
            if (j + si) % 4 == 3:
                continue
            p = sc_ + side(yw) * (-w_ / 2 + 0.18 + j * 0.3) - fwd(yw) * 0.05
            m = ('M_BookRed', 'M_BookGreen', 'M_BookBlue')[(j + si) % 3]
            hgt = rnd.uniform(0.28, 0.4)
            box(k.books[m], (p.x, p.y), (0.09, hgt, 0.26), yy, yw + rnd.uniform(-8, 8))
            box(k.books['M_PageWhite'], (p.x, p.y), (0.07, hgt - 0.04, 0.24), yy + 0.01, yw)
    # a string across the hollow with little human things hung on it (key, spoon, a blue page, a bead)
    s0 = c + V((math.cos(view + 1.25), math.sin(view + 1.25))) * (ring_r - 0.4)
    s1 = c + V((math.cos(view - 1.15), math.sin(view - 1.15))) * (ring_r - 0.4)
    line = [B(*s0.lerp(s1, t / 10), y + 2.9 - 0.45 * math.sin(math.pi * t / 10)) for t in range(11)]
    stroke3(kd.ink, line, 0.02)
    for t, mat, sz in ((2, kd.brass, (0.05, 0.16, 0.05)), (4, kd.iron, (0.05, 0.2, 0.04)), (6, None, None), (8, kd.brass, (0.07, 0.07, 0.07))):
        q = s0.lerp(s1, t / 10)
        yy = y + 2.9 - 0.45 * math.sin(math.pi * t / 10)
        stroke3(kd.ink, [B(q.x, q.y, yy), B(q.x, q.y, yy - 0.22)], 0.012)
        if mat is None:
            box(kd.books['M_BookBlue'], (q.x, q.y), (0.22, 0.28, 0.01), yy - 0.5, yaw_)
        else:
            box(mat, (q.x, q.y), sz, yy - 0.22 - sz[1], 0)
    # the nest: ring of paper scraps and twigs, a green human cloth, a pillow of folded pages
    nc = HIDE_PTS['z_hideout_nest']
    for i in range(16):
        a = 2 * math.pi * i / 16
        p0 = nc + V((math.cos(a), math.sin(a))) * 0.7
        p1 = nc + V((math.cos(a + 0.7), math.sin(a + 0.7))) * 0.78
        stroke3(k.paperback, [B(p0.x, p0.y, y + 0.12 + 0.06 * (i % 2)), B(p1.x, p1.y, y + 0.2)], 0.09)
        stroke3(k.ink, [B(p0.x, p0.y, y + 0.22), B(p1.x, p1.y, y + 0.26)], 0.02)
    cloth = [nc + V((math.cos(2 * math.pi * i / 9), math.sin(2 * math.pi * i / 9))) * (0.52 + 0.08 * math.sin(i * 2.1)) for i in range(9)]
    fill(k.green, ccw(cloth), y + 0.14, uv=False)
    lathe(k.paperback, (nc.x, nc.y), [(0.8, 0.0), (0.88, 0.14), (0.66, 0.2)], seg=10, y0=y, cap=False)
    box(k.books['M_PageWhite'], (nc.x - 0.25, nc.y + 0.15), (0.5, 0.12, 0.32), y + 0.16, 40)
    # floor: a patchwork rug of torn pages, root lines, a worn path from the tunnel
    for i in range(9):
        a = rnd.uniform(0, 2 * math.pi)
        p = c + V((-0.3, -0.2)) + V((math.cos(a), math.sin(a))) * rnd.uniform(0.0, 1.0)
        q = jag_poly(p, rnd.uniform(0.25, 0.38), rnd.uniform(0.2, 0.3), 5, 640 + i, rnd.uniform(0, 3))
        fill(k.paperback, ccw(q), y + 0.012 + i * 0.002, uv=False)
        stroke3(k.ink, [B(v.x, v.y, y + 0.03) for v in q] + [B(q[0].x, q[0].y, y + 0.03)], 0.015)
    for i in range(8):
        a = rnd.uniform(0, 2 * math.pi)
        p0 = c + V((math.cos(a), math.sin(a))) * rnd.uniform(1.6, 2.6)
        p1 = p0 + V((math.cos(a + 0.4), math.sin(a + 0.4))) * rnd.uniform(0.5, 0.9)
        if inside(p0, walk) and inside(p1, walk):
            ground_stroke(k.ink, [p0, (p0 + p1) / 2 + V((0.08, 0.04)), p1], y, 0.03, 0.02)
    ground_stroke(k.sketch, [V((38.0, 27.9)), V((39.6, 28.4)), V((41.4, 29.0))], y, 0.03, 0.02)
    # the wall drawing (two puppet kids hand in hand under the light hole) on a smoothed bark panel (Face_hideout, UV 0..1)
    dc = HIDE_PTS['z_hideout_drawing']
    dd = (dc - c).normalized()
    wall_p = c + dd * (ring_r - 0.62)
    nrm = -dd
    tng = V((dd.y, -dd.x))          # the viewer's right when facing the wall
    face_c = wall_p
    fp = [face_c - tng * 1.0, face_c + tng * 1.0]
    ya, yb = y + 0.35, y + 2.25
    q = [kf.paperback.verts.new(B(fp[0].x, fp[0].y, ya)), kf.paperback.verts.new(B(fp[1].x, fp[1].y, ya)),
         kf.paperback.verts.new(B(fp[1].x, fp[1].y, yb)), kf.paperback.verts.new(B(fp[0].x, fp[0].y, yb))]
    f = add_face(kf.paperback, q, V((nrm.x * -1, nrm.y * -1, 0)))
    uvl = kf.paperback.loops.layers.uv.active or kf.paperback.loops.layers.uv.new('UVMap')
    if f:
        for lp, uv in zip(f.loops, ((0, 0), (1, 0), (1, 1), (0, 1))):
            lp[uvl].uv = uv
    stroke3(k.ink, [B(*(fp[0] + nrm * 0.02), ya), B(*(fp[1] + nrm * 0.02), ya), B(*(fp[1] + nrm * 0.02), yb), B(*(fp[0] + nrm * 0.02), yb), B(*(fp[0] + nrm * 0.02), ya)], 0.03)
    dp = wall_p + nrm * 0.03

    def W2(u, v):
        return B(*(dp + tng * u), y + v)
    hole_u, hole_v = 0.5, 1.85
    stroke3(k.ink, [W2(hole_u + math.cos(2 * math.pi * i / 14) * 0.24, hole_v + math.sin(2 * math.pi * i / 14) * 0.24) for i in range(15)], 0.035)
    for i in range(8):
        a = 2 * math.pi * i / 8
        stroke3(k.paintr if i % 2 else k.ink, [W2(hole_u + math.cos(a) * 0.32, hole_v + math.sin(a) * 0.32), W2(hole_u + math.cos(a) * 0.5, hole_v + math.sin(a) * 0.5)], 0.03)
    for (u0, s, nose, col) in ((-0.55, 1.0, False, k.paint), (-0.05, 0.8, True, k.paintr)):
        base = 0.5
        hy = base + 0.95 * s
        stroke3(k.ink, [W2(u0 + math.cos(2 * math.pi * i / 10) * 0.17 * s, hy + math.sin(2 * math.pi * i / 10) * 0.17 * s) for i in range(11)], 0.035)
        stroke3(k.ink, [W2(u0, hy - 0.17 * s), W2(u0, hy - 0.66 * s)], 0.035)
        stroke3(k.ink, [W2(u0 - 0.2 * s, base), W2(u0, hy - 0.66 * s), W2(u0 + 0.2 * s, base)], 0.035)
        stroke3(k.ink, [W2(u0 - 0.28 * s, hy - 0.48 * s), W2(u0, hy - 0.3 * s), W2(u0 + 0.3 * s, hy - 0.48 * s)], 0.035)
        stroke3(col, [W2(u0 - 0.1 * s, hy - 0.27 * s), W2(u0 + 0.1 * s, hy - 0.58 * s)], 0.09)
        stroke3(k.ink, [W2(u0 - 0.05 * s, hy + 0.04), W2(u0 - 0.05 * s, hy + 0.06)], 0.03)
        if nose:
            stroke3(k.ink, [W2(u0 + 0.14 * s, hy + 0.02), W2(u0 + 0.5 * s, hy + 0.13)], 0.025)
    for i in range(4):
        stroke3(k.sketch, [W2(0.75, 0.5 + i * 0.3), W2(0.95, 0.5 + i * 0.3)], 0.025)
    stroke3(k.sketch, [W2(0.75, 0.4), W2(0.75, 1.55)], 0.025)
    stroke3(k.sketch, [W2(0.95, 0.4), W2(0.95, 1.55)], 0.025)
    compass(k, HIDE_PTS['z_hideout_talk'], 0.7, y, 611, 0.7)
    # outside the trunk: big roots spreading over the margin (frame the cut side)
    for i in range(8):
        a = RAD(i * 45 + rnd.uniform(-10, 10))
        p0 = c + V((math.cos(a), math.sin(a))) * (ring_r - 0.1)
        p1 = c + V((math.cos(a), math.sin(a))) * rnd.uniform(5.8, 6.6)
        root(k, [B(p0.x, p0.y, y + 0.35), B(*((p0 + p1) / 2), y + 0.15), B(p1.x, p1.y, y - 0.25)], 0.26, 0.08, 620 + i)
    # light: a thin warm beam from the knot hole to the floor + warm pools (the only cosy light after the fall)
    lc = c + V((0.4, 0.5))
    light_pool(kl, lc, 1.5, y, seg=18)
    beam(kl, lc, 0.5, 0.32, y + 0.02, y + 6.6, seg=12)
    dust(kl, lc, 0.45, y + 0.4, y + 5.0, 22, 625)
    light_pool(kl, HIDE_PTS['hideout_lantern'], 1.3, y, seg=14)
    abyss_floor(kv, (42.0, 29.0), 50.0, 40.0, 630)
    cave(kv, (42.4, 29.4), 52, 631)
    exits = [(AREA_HIDE['exits'][0], (-0.85, -0.5), YH, 'M_PaintRed', False)]
    return finish_area(A, 'a_hideout', k, kd, kl, kv, top='M_GroundEarth', exits=exits,
                       extra_parts=[('Face_hideout', kf, ('paperback',), tuple(B(face_c.x, face_c.y, y + 1.3)))])


# ============================================================================================ CART / DEPOT
def shed(k, kd, ks):
    """the collectors' depot: an open-fronted timber shed, walls half built, the roof boards only on the north half;
    sacks of collected human things piled inside, shelves of sorted books, the hero's satchel hanging on the front post."""
    rnd = random.Random(701)
    y = YC
    x0, x1, z0, z1 = SHED
    zc = (z0 + z1) / 2
    slab_wall(k, V((x1, z0)), V((x1, z1)), y, 3.0, 0.3, 1.0, 702, bm=k.solid, planks=0.42)                 # back wall
    slab_wall(k, V((x0 + 0.2, z1)), V((x1, z1)), y, 2.9, 0.3, 0.62, 703, bm=k.solid, planks=0.42)          # north wall: back third only drawn
    slab_wall(k, V((x1, z0)), V((x0 + 0.2, z0)), y, 2.9, 0.3, 0.45, 704, bm=k.solid, planks=0.42)         # south wall: half built
    for (zz, hh) in ((z1, 3.0), (zc, 3.6), (z0, 3.0)):
        obox(k.wood, k.ink, (x0 + 0.2, zz), (0.26, hh, 0.26), y, 0, ink_w=0.04)
    box(kd.wood, (x0 + 0.2, zc), (0.3, 0.3, z1 - z0 + 0.4), y + 2.9, 0)
    stroke3(kd.ink, [B(x0 + 0.05, z0 - 0.2, y + 3.22), B(x0 + 0.05, z1 + 0.2, y + 3.22)], 0.045)
    # roof: ridge along x at zc (y+4.4). north half boarded (decor), south half rafters only
    for i in range(10):
        xx = x0 + (x1 - x0) * i / 9
        stroke3(kd.ink, [B(xx, z1 + 0.3, y + 2.95), B(xx, zc, y + 4.4)], 0.045)
        stroke3(kd.sketch if i % 2 else kd.ink, [B(xx, z0 - 0.3, y + 2.95), B(xx, zc, y + 4.4)], 0.035)
    q = [B(x0 - 0.3, z1 + 0.3, y + 2.95), B(x1 + 0.3, z1 + 0.3, y + 2.95), B(x1 + 0.3, zc, y + 4.4), B(x0 - 0.3, zc, y + 4.4)]
    add_face(kd.paperback, [kd.paperback.verts.new(v) for v in q], V((0, 0, 1)))
    for i in range(7):
        t = i / 6
        stroke3(kd.ink, [B(x0 - 0.3, z1 + 0.3 + (zc - z1 - 0.3) * t, y + 2.95 + 1.45 * t + 0.02), B(x1 + 0.3, z1 + 0.3 + (zc - z1 - 0.3) * t, y + 2.95 + 1.45 * t + 0.02)], 0.03)
    stroke3(kd.ink, [B(x0 - 0.4, zc, y + 4.42), B(x1 + 0.4, zc, y + 4.42)], 0.07)
    # sacks of collected human things along the back wall and in the yard
    books = lambda s: [(('M_BookRed', 'M_BookGreen', 'M_BookBlue')[(s + i) % 3], rnd.uniform(-0.2, 0.2), rnd.uniform(-0.15, 0.15), rnd.uniform(0, 180), 1.0) for i in range(1 + s % 2)]
    for i, (sx, sz, r, h) in enumerate(((22.1, -8.0, 0.55, 1.1), (22.0, -9.3, 0.6, 1.25), (22.2, -10.7, 0.5, 1.0), (21.9, -12.0, 0.55, 1.15),
                                        (21.0, -8.6, 0.45, 0.9), (21.1, -11.4, 0.5, 0.95), (21.6, -9.9, 0.45, 0.8))):
        sack(k, (sx, sz), r, h, 710 + i, books(i), y0=y)
    for i, (sx, sz, r, h) in enumerate(((11.6, -11.0, 0.5, 0.95), (12.7, -11.6, 0.45, 0.85), (10.6, -10.4, 0.5, 1.0), (16.2, -3.9, 0.45, 0.8))):
        sack(k, (sx, sz), r, h, 720 + i, books(i + 1), y0=y)
    # shelf of sorted things on the north wall inside (umbrella handles, books, a lantern)
    for (hh, w_) in ((1.0, 3.6), (1.8, 3.0)):
        box(k.wood, (20.4, z1 - 0.45), (w_, 0.08, 0.5), y + hh, 0)
        stroke3(k.ink, [B(20.4 - w_ / 2, z1 - 0.2, y + hh + 0.09), B(20.4 + w_ / 2, z1 - 0.2, y + hh + 0.09)], 0.03)
        for j in range(int(w_ / 0.45)):
            m = ('M_BookRed', 'M_BookBlue', 'M_BookGreen', 'M_BookRed')[(j + int(hh * 3)) % 4]
            box(k.books[m], (20.4 - w_ / 2 + 0.25 + j * 0.45, z1 - 0.45), (0.1, 0.4, 0.32), y + hh + 0.08, rnd.uniform(-6, 6))
    # sorting table in the yard + a tally board (collectors count what they collect) - board only drawn
    obox(k.wood, k.ink, (15.6, -10.6), (1.8, 0.85, 0.9), y, 0, ink_w=0.035)
    book(k, (15.3, -10.6), y + 0.85, 30, 'M_BookBlue')
    book(k, (15.9, -10.5), y + 0.85, -20, 'M_BookRed', 0.8)
    stroke3(k.sketch, [B(17.0, -12.3, y), B(17.0, -12.3, y + 2.2), B(17.0, -13.4, y + 2.2), B(17.0, -13.4, y)], 0.03)
    for i in range(6):
        stroke3(k.ink, [B(17.02, -12.45 - i * 0.16, y + 1.9), B(17.02, -12.45 - i * 0.16, y + 1.55)], 0.025)
    stroke3(k.ink, [B(17.02, -12.4, y + 1.6), B(17.02, -13.3, y + 1.85)], 0.025)
    # the hero's satchel: hanging from a hook on the middle front post (separate part, pivot = bag centre)
    sp = CART_PTS['satchel']
    hook = V((x0 + 0.2, zc - 0.05))
    stroke3(k.iron, [B(hook.x - 0.14, hook.y, y + 1.75), B(hook.x - 0.3, hook.y, y + 1.82)], 0.04)
    sc_ = V((hook.x - 0.42, hook.y))
    yb = y + 1.25
    box(ks.leather, (sc_.x, sc_.y), (0.16, 0.4, 0.46), yb - 0.2, 0)
    q = [B(sc_.x - 0.09, sc_.y - 0.24, yb + 0.2), B(sc_.x - 0.09, sc_.y + 0.24, yb + 0.2), B(sc_.x - 0.1, sc_.y + 0.24, yb - 0.02), B(sc_.x - 0.1, sc_.y - 0.24, yb - 0.02)]
    add_face(ks.leather, [ks.leather.verts.new(v) for v in q], V((1, 0, 0)))
    box(ks.brass, (sc_.x - 0.11, sc_.y), (0.04, 0.09, 0.09), yb - 0.02, 0)
    stroke3(ks.leather, [B(sc_.x, sc_.y - 0.22, yb + 0.18), B(hook.x - 0.3, hook.y, y + 1.82), B(sc_.x, sc_.y + 0.22, yb + 0.18)], 0.04)
    stroke3(ks.ink, [B(sc_.x - 0.1, sc_.y - 0.24, yb - 0.03), B(sc_.x - 0.1, sc_.y + 0.24, yb - 0.03)], 0.02)
    return (sc_.x, sc_.y, yb)


def build_cart(A):
    k, kd, kv, ks, kl = Kit2(), Kit2(), Kit2(), Kit2(), Kit2()
    y = YC
    plateau(k, jag(P_CART, 2.2, 0.3, 700), [W_CART], y, 700, ledge=1.3, unf=lambda a, b: (a + b).y / 2 < -14.0)
    sat = shed(k, kd, ks)
    # the town's foundation to the north: a tiered paper cliff from the yard up to the plaza height (y 0), hatched, with
    # stacked basalt slabs at its foot; only a thin strip of the plaza on top (the rest is beyond the page)
    rnd = random.Random(731)
    bank_poly = ccw([V(p) for p in [(9.4, -1.2), (13.0, -1.0), (17.0, -0.9), (20.4, -0.7), (21.6, 1.6), (17.4, 2.4), (13.4, 2.0), (9.4, 1.2)]])
    fill(kd.lower, bank_poly, YP, uv=False)
    walls(k.solid, k.ink, k.hatch, bank_poly, YP, YC - 0.05, 732, ledge=1.0, ledge_out=0.35, hatch_floor=YC, hatch_density=1.2,
          skip=lambda a, b: (a + b).y / 2 > 1.0, sketch=k.sketch, torn=k.torn,
          unf=lambda a, b: 17.0 < (a + b).x / 2 < 21.5 and (a + b).y / 2 < 0.0)
    bp = [V(p) for p in [(9.4, -1.2), (13.0, -1.0), (17.0, -0.9), (20.4, -0.7)]]
    for i in range(len(bp) - 1):          # the bank faces the light: draw its strata and a few torn courses by hand
        a, b_ = bp[i], bp[i + 1]
        for t in range(3):
            yy = YC + 0.55 + t * 0.62 + rnd.uniform(-0.1, 0.1)
            stroke3(k.ink if t == 1 else k.hatch, [B(a.x, a.y - 0.05, yy), B(b_.x, b_.y - 0.05, yy + rnd.uniform(-0.15, 0.15))], 0.035)
        en = V(((b_ - a).y, -(b_ - a).x)).normalized()
        hatch_face(k.hatch, a, b_, YP, YP, YC + 0.4, en, rnd, 0.55, 1.2)
    for i, x in enumerate((11.2, 14.6, 19.0)):
        cairn(k, (x, -1.6 - 0.2 * (i % 2)), 0.7 + 0.15 * (i % 3), 1.2 + 0.5 * (i % 2), YC, 733 + i, True, 0.3 if i == 2 else 0.0)
    # plaza balustrade + the bell tower (vista copies) seen above the bank
    vk = Kit2()
    balustrade(vk, [V((-1.0, -0.6)), V((4.0, -0.9)), V((7.4, -0.9))], YP, 0.55, 372)
    c = BELL_TOWER
    cairn(vk, c, 1.25, 0.6, YP, 352, False, 0.0)
    for sx, sz in ((-1, -1), (1, -1), (1, 1), (-1, 1)):
        p = c + side(250) * sx * 0.95 + fwd(250) * sz * 0.95
        box(vk.swood, (p.x, p.y), (0.26, 3.5, 0.26), YP + 0.6, 250)
    lathe(vk.terrad_r, (c.x, c.y), [(0.0, -1.45), (0.86, -1.45), (0.6, -0.8), (0.38, -0.08), (0.12, 0.0)], seg=10, y0=YP + 3.8)
    # the depot stairs coming down from the plaza (real here; pennant at the foot)
    top, d, sw, n, rise, run = DEPOT_STAIR
    steps(k, top, d, sw, n, rise, run, YP, 8, seed=376, down=True)
    # the offering road east: drawn road strip, wheel ruts heading for the field, a drawn bridge over a crack
    road = [V((8.8, -4.2)), V((13.0, -4.6)), V((18.0, -4.6)), V((22.5, -4.8)), V((28.4, -4.9))]
    rp = ccw(strip_poly(road, 1.3))
    fill(k.road, rp, y + 0.012, uv=False)
    for s_ in (-0.55, 0.55):
        pts = [p + V((0, s_ + rnd.uniform(-0.04, 0.04))) for p in road]
        ground_stroke(k.ink, pts, y, 0.05)
        ground_stroke(k.sketch, [p + V((0, s_ * 1.25)) for p in road], y, 0.03, 0.02)
    # the yard: hex flagstones round the shed mouth, cracks, sitting arcs of the collectors, compass round the cart
    w = ccw(W_CART)
    hex_lines(k.ink, w, y, 0.95, 732, keep=0.3, origin=(16.0, -8.0), avoid=lambda p: inside(p, rp))
    cracks(k.ink, w, y, 10, 733, avoid=lambda p: inside(p, rp))
    compass(k, CART_PTS['cart'], 2.1, y, 734, 0.75)
    ticks_along(k, [V((9.2, -10.6)), V((15.0, -12.4)), V((18.2, -12.6))], y, 0.6, 735, side=1)
    for (cc, rx, rz, rot, sd) in (((10.6, -6.2), 1.2, 0.45, 0.2, 1), ((24.0, -6.2), 1.1, 0.4, -0.2, 2)):
        smudge(k, cc, rx, rz, rot, y, 736 + sd)
    # the open barrel at z_depot_barrel (Kinopio climbs it and dances): staves real on the camera side, the rest drawn, hoops in ink
    bc = CART_PTS['z_depot_barrel']
    seg = 12
    for i in range(seg):
        a0, a1 = 2 * math.pi * i / seg, 2 * math.pi * (i + 1) / seg
        real = math.cos((a0 + a1) / 2 - RAD(90 - 96 + 180)) > -0.35
        r0, r1 = 0.4, 0.46
        prof = [(r0, 0.0), (r1, 0.45), (r0, 0.9)]
        if real:
            for j in range(2):
                (ra, ya), (rb, yb2) = prof[j], prof[j + 1]
                q = [k.swood.verts.new(B(bc.x + math.cos(a0) * ra, bc.y + math.sin(a0) * ra, y + ya)), k.swood.verts.new(B(bc.x + math.cos(a1) * ra, bc.y + math.sin(a1) * ra, y + ya)),
                     k.swood.verts.new(B(bc.x + math.cos(a1) * rb, bc.y + math.sin(a1) * rb, y + yb2)), k.swood.verts.new(B(bc.x + math.cos(a0) * rb, bc.y + math.sin(a0) * rb, y + yb2))]
                f = add_face(k.swood, q, None)
                if f:
                    m = f.calc_center_median()
                    if f.normal.dot(V((m.x + bc.x, m.y + bc.y, 0))) < 0:
                        f.normal_flip()
                    add_face(k.swood, [k.swood.verts.new(v.co) for v in reversed(f.verts)], None)
            stroke3(k.ink, [B(bc.x + math.cos(a0) * r0, bc.y + math.sin(a0) * r0, y), B(bc.x + math.cos(a0) * r1, bc.y + math.sin(a0) * r1, y + 0.45),
                            B(bc.x + math.cos(a0) * r0, bc.y + math.sin(a0) * r0, y + 0.9)], 0.02)
        else:
            stroke3(k.sketch, [B(bc.x + math.cos(a0) * r0, bc.y + math.sin(a0) * r0, y), B(bc.x + math.cos(a0) * r1, bc.y + math.sin(a0) * r1, y + 0.45),
                               B(bc.x + math.cos(a0) * r0, bc.y + math.sin(a0) * r0, y + 0.9)], 0.02)
    for (rr, yy) in ((0.4, 0.9), (0.45, 0.62), (0.45, 0.28)):
        stroke3(k.ink, [B(bc.x + math.cos(2 * math.pi * i / 16) * (rr + 0.01), bc.y + math.sin(2 * math.pi * i / 16) * (rr + 0.01), y + yy) for i in range(17)], 0.03)
    fill(k.dark, ccw([bc + V((math.cos(2 * math.pi * i / 10), math.sin(2 * math.pi * i / 10))) * 0.38 for i in range(10)]), y + 0.7, uv=False)
    compass(k, bc, 1.0, y, 745, 0.7)
    # the far (east) end: the road runs over a drawn trestle onto the next page; a gate post with a blue flag
    for s_ in (-1, 1):
        p = V((28.6, -4.9 + 1.6 * s_))
        cairn(k, p, 0.42, 1.6, y, 740 + s_, True, 0.45)
    # the south edge: drawn fence (first posts real) + rocks
    for i, x in enumerate((9.0, 11.0, 13.0, 15.0)):
        if i < 2:
            obox(k.wood, k.ink, (x, -13.2), (0.16, 1.1, 0.16), y, 0, ink_w=0.03)
        else:
            stroke3(k.sketch, [B(x, -13.4, y), B(x, -13.4, y + 1.1)], 0.03)
    stroke3(k.ink, [B(9.0, -13.2, y + 0.95), B(11.0, -13.2, y + 0.95)], 0.035)
    stroke3(k.sketch, [B(11.0, -13.3, y + 0.95), B(15.0, -13.4, y + 0.95)], 0.03)
    for (cc, rx, h, sd) in (((5.4, -12.2), 1.0, 0.9, 751), ((25.4, -12.0), 1.2, 1.8, 752), ((27.6, -9.4), 0.9, 1.1, 753)):
        rock_wire(k, hexp(cc, rx, sd), y, h, 1 + (sd % 2), sd, wire=0.45)
    # west shelf path from the pass (the long way round): a drawn rope rail on the abyss side
    for x in (5.6, 7.0, 8.4):
        stroke3(k.ink, [B(x, -10.9, y), B(x, -10.9, y + 0.9)], 0.04)
    stroke3(k.ink, [B(5.0, -10.9, y + 0.85), B(8.8, -10.9, y + 0.8)], 0.03)
    # light: a single lantern pool at the shed mouth (Lantern_Hanging dressing), the rest stays drained
    light_pool(kl, V((18.0, -8.2)), 2.0, y, seg=16)
    # vista: field + pond far east (the next page), the alley cliff north-east, abyss, cave, spires
    abyss_floor(kv, (20.0, -8.0), 80.0, 60.0, 760)
    vista_field(kv, detail=1.0)
    stacks(kv, [((4.0, -16.0), 1.2, -4.0, []), ((30.0, -14.0), 1.5, -3.0, [('M_BookRed', 0, 0, 25)]), ((20.0, -19.0), 1.2, -6.0, [])], 761)
    vista_spires(kv, (16.0, -8.0), 100, 762)
    cave(kv, (16.0, -8.0), 100, 763)
    exits = [(AREA_CART['exits'][0], (-0.55, 0.835), YC, 'M_PaintBlue', False),
             (AREA_CART['exits'][1], (1.0, 0.0), YC, 'M_PaintBlue', True),
             (AREA_CART['exits'][2], (-1.0, 0.05), YC, 'M_PaintBlue', True)]
    st = finish_area(A, 'a_cart', k, kd, kl, kv, exits=exits,
                     extra_parts=[('Satchel_cart', ks, ('leather', 'brass', 'ink'), tuple(B(sat[0], sat[1], sat[2])))])
    # vista copies of the plaza rim go to Decor (no collider, they stand on the plaza's height)
    p = Part('Decor_cart_rim')
    to_part(p, vk, ALL_KEYS, vista=True)
    if p.pieces:
        ob = A.part(p, parent='Area_a_cart')
        TRIS['a_cart']['Decor_cart_rim'] = sum(len(pp.vertices) - 2 for pp in ob.data.polygons)
        TRIS['a_cart']['_total'] += TRIS['a_cart']['Decor_cart_rim']
    return st


# ============================================================================================ FIELD + POND
def build_field(A):
    k, kd, kv, kl = Kit2(), Kit2(), Kit2(), Kit2()
    y = YF
    rnd = random.Random(801)
    wf = ccw(W_FIELD)
    pond = ccw([pc(a, POND_R) for a in range(0, 360, 10)])
    apron = ccw([pc(a, APRON_R) for a in range(0, 360, 8)])
    stepring = ccw(arc(ARC0, ARC1, APRON_R) + list(reversed(arc(ARC0, ARC1, STEP_R))))
    # field plateau + margin; apron + steps + black pond (walkable 'dried ink')
    outer = ccw(P_FIELD)
    fill(k.walk, wf, y, steiner=grid_pts(wf, 2.4, 802))
    fill(k.walk, stepring, YS, uv=False)
    fill(k.walk, apron, YO, holes=[pond], steiner=grid_pts(apron, 2.2, 803))
    fill(k.pond, pond, YPOND, uv=False)
    fill(k.margin, outer, y, holes=[wf], steiner=grid_pts(outer, 2.8, 804))
    walls(k.solid, k.ink, k.hatch, outer, y, FLOOR, 805, ledge=1.3, ledge_out=0.3, hatch_floor=y - 3, deep=k.dark, deep_y=y - 3.2,
          sketch=k.sketch, torn=k.torn, unf=lambda a, b: (a + b).x / 2 < 33.0 and (a + b).y / 2 < -8.0,
          skip=lambda a, b: ((a + b) / 2 - POND_C).length < STEP_R + 1.2 and math.cos(math.atan2(((a + b) / 2 - POND_C).y, ((a + b) / 2 - POND_C).x) - RAD(147)) > 0.6)
    # apron edge: on the field side two risers (field -> step -> apron), elsewhere the apron falls into the abyss
    riser(k, list(reversed(arc(ARC0, ARC1, STEP_R))), y, YS, True, 806)
    riser(k, list(reversed(arc(ARC0, ARC1, APRON_R))), YS, YO, True, 807)
    walls(k.solid, k.ink, k.hatch, ccw([pc(a, APRON_R) for a in range(0, 360, 8)]), YO, FLOOR, 808, ledge=1.5, ledge_out=0.35, hatch_floor=YO - 3,
          deep=k.dark, deep_y=YO - 3.0, sketch=k.sketch, torn=k.torn,
          skip=lambda a, b: math.cos(math.atan2(((a + b) / 2 - POND_C).y, ((a + b) / 2 - POND_C).x) - RAD((ARC0 + ARC1) / 2)) > math.cos(RAD((ARC1 - ARC0) / 2 + 2)))
    # the pond: ink well (dark inner wall), a ring of drawn stones, ink rings on the surface
    for i in range(36):
        a0, a1 = RAD(i * 10), RAD((i + 1) * 10)
        p0, p1 = pc(i * 10, POND_R), pc((i + 1) * 10, POND_R)
        q = [k.dark.verts.new(B(p0.x, p0.y, YO)), k.dark.verts.new(B(p1.x, p1.y, YO)), k.dark.verts.new(B(p1.x, p1.y, YPOND)), k.dark.verts.new(B(p0.x, p0.y, YPOND))]
        add_face(k.dark, q, None)
    stroke3(k.ink, [B(*pc(a, POND_R + 0.05), YO + 0.03) for a in range(0, 361, 6)], 0.09)
    for i in range(22):
        a = i * 360 / 22 + rnd.uniform(-4, 4)
        if 104 < a < 172:
            continue                               # the villagers' rows and the carts' landing: the pond edge stays open there
        cc = pc(a, POND_R + 0.45)
        rock(k.solid, k.ink, None, hexp(cc, rnd.uniform(0.32, 0.5), 820 + i), YO, rnd.uniform(0.15, 0.35), 1, 820 + i)
    for rr in (2.0, 3.6, 5.0):
        pts = [B(*pc(a, rr), YPOND + 0.012) for a in range(0, 361, 12)]
        stroke3(k.hatch, pts, 0.04)
    # apron drawing: flagstone spokes toward the pond (the 'stage'), the line where villagers kneel, the bank mark
    for i in range(24):
        a = i * 15
        if ARC0 - 10 < a < ARC1 + 10 or i % 2 == 0:
            ground_stroke(k.ink, [pc(a, POND_R + 0.9), pc(a, APRON_R - 0.3)], YO, 0.04)
    for rr in (7.8, 9.05, 10.3):
        pts = [pc(a, rr) for a in range(int(ARC0) + 6, int(ARC1) - 4, 4)]
        ground_stroke(k.ink if rr != 9.05 else k.sketch, pts, YO, 0.04)
    for p in LINEUP:
        ground_stroke(k.ink, [p + V((math.cos(t), math.sin(t))) * 0.42 for t in [i * 0.5 for i in range(13)]], YO if (p - POND_C).length < APRON_R else YS, 0.03)
    bank = FIELD_PTS['z_pond_bank']
    compass(k, bank, 1.1, YO, 830, 0.8)
    smudge(k, bank + V((0.4, 0.2)), 1.2, 0.6, 0.6, YO, 831)
    # the pond stone (carved) foot, the procession gate: two pillar cairns built 55 %, the arch only drawn, a fish drawn on it
    g0, g1 = pc(124, STEP_R + 1.3), pc(166, STEP_R + 1.3)        # wide apart and low: they must not hide the rows from the camera
    for (gp, sd) in ((g0, 841), (g1, 842)):
        cairn(k, gp, 0.5, 3.4, y, sd, True, 0.45)
    arch = []
    for i in range(13):
        t = i / 12
        p = g0.lerp(g1, t)
        arch.append(B(p.x, p.y, y + 3.3 + math.sin(math.pi * t) * 1.4))
    stroke3(kd.ink, arch, 0.08)
    stroke3(kd.sketch, [v + V((0, 0, 0.3)) for v in arch[1:-1]], 0.04)
    mid = g0.lerp(g1, 0.5)
    fishpts = [B(*(mid + (g1 - g0).normalized() * (0.75 * math.cos(t))), y + 4.3 + 0.32 * math.sin(t)) for t in [i * 0.4 for i in range(17)]]
    stroke3(kd.ink, fishpts, 0.04)
    pennant(kd.solid, kd.paint, kd.ink, mid + (g1 - g0).normalized() * 0.2, y + 3.9, h=0.9, d=((POND_C - mid).normalized().x, (POND_C - mid).normalized().y))
    # field surface (polish 10/23): hand-dug furrows that all lean toward the pond — wobbling, broken, some only in pencil;
    # soil turned in ragged patches (some only outlined); cart tracks cut across the beds toward the steps.
    rf = lambda p: inside(p, wf) and poly_dist(p, wf) > 0.6
    stone = FIELD_PTS['z_field_stone']
    on_track = lambda p: any(min(LV.seg_dist(p, tr[i], tr[i + 1])[0] for i in range(len(tr) - 1)) < 0.75 for tr in CART_TRACKS)
    on_road = lambda p: min(LV.seg_dist(p, ROAD_F[i], ROAD_F[i + 1])[0] for i in range(len(ROAD_F) - 1)) < 1.9 or \
        min(LV.seg_dist(p, ROAD_N[i], ROAD_N[i + 1])[0] for i in range(len(ROAD_N) - 1)) < 1.6 or on_track(p) or (p - stone).length < 1.6
    for i in range(28):
        a0 = 96.5 + i * 3.6 + rnd.uniform(-1.3, 1.3)
        r_end = rnd.uniform(19.0, 35.0)
        ph, amp = rnd.uniform(0, 6.3), rnd.uniform(0.12, 0.38)
        pts_all = []
        rr = STEP_R + rnd.uniform(0.8, 2.4)
        while rr < r_end:
            a = RAD(a0 + 0.9 * math.sin(rr * 0.21 + ph))
            u = V((math.cos(a), math.sin(a)))
            n = V((-u.y, u.x))
            pts_all.append((POND_C + u * rr + n * (amp * math.sin(rr * 0.55 + ph * 2) + rnd.uniform(-0.05, 0.05)), u, n))
            rr += rnd.uniform(0.75, 1.1)
        run = []
        pencil = rnd.random() < 0.3
        for (p, u, n) in pts_all + [(None, None, None)]:
            ok = p is not None and rf(p) and not on_road(p) and rnd.random() > 0.04
            if ok:
                run.append((p, u, n))
                continue
            if len(run) > 1:
                ground_stroke(k.sketch if pencil else k.ink, [q for q, _, _ in run], y, 0.035 if pencil else rnd.uniform(0.04, 0.06), 0.02)
                # soil patches beside this furrow: ragged both sides, width breathing, broken where a track or the road crosses;
                # most filled with dark turned soil, some only outlined in pencil (dug in the drawing, not yet painted)
                if i % 3 != 2 and len(run) > 2:
                    side_ = 1 if i % 2 else -1
                    cur = []
                    for (q, _, nn) in run + [(None, None, None)]:
                        if q is not None:
                            w_ = rnd.uniform(0.5, 1.05)
                            lq = q + nn * side_ * (0.14 + rnd.uniform(-0.04, 0.06))
                            rq = q + nn * side_ * (0.14 + w_)
                            if rf(rq) and not on_road(rq) and not on_road(lq):
                                cur.append((lq, rq, nn))
                                continue
                        if len(cur) >= 3 and rnd.random() < 0.85:
                            left = [c_[0] for c_ in cur]
                            right = [c_[1] for c_ in cur]
                            left[0] = left[0].lerp(right[0], 0.5)
                            right[-1] = right[-1].lerp(left[-1], rnd.uniform(0.3, 0.7))
                            bed = left + list(reversed(right))
                            if rnd.random() < 0.75:
                                fill(k.soil, ccw(bed), y + 0.014, uv=False)
                                for (lq, rq, nn) in cur[::2]:
                                    c_ = lq.lerp(rq, rnd.uniform(0.3, 0.7))
                                    ground_stroke(k.ink, [c_ - nn * 0.12, c_ + nn * 0.12], y, 0.022, 0.03)
                            else:
                                ground_stroke(k.sketch, right + [left[-1]], y, 0.025, 0.02)
                        cur = []
            run = []
    # the ridge (밭둑) with the nose-file stone: a low earth bank Kinopio can hide behind (NoseFileStone prop on its lee side)
    rd = (POND_C - stone).normalized()
    rn = V((-rd.y, rd.x))
    lathe_bank = [stone + rd * 0.95 + rn * t for t in (-1.9, -1.1, 0.0, 1.1, 1.9)]
    hs = [0.12, 0.42, 0.55, 0.4, 0.1]
    for j in range(4):
        p0, p1 = lathe_bank[j], lathe_bank[j + 1]
        f0, f1 = p0 - rd * 0.55, p1 - rd * 0.55
        b0, b1 = p0 + rd * 0.55, p1 + rd * 0.55
        top0, top1 = B(p0.x, p0.y, y + hs[j]), B(p1.x, p1.y, y + hs[j + 1])
        for (e0, e1) in ((f0, f1), (b0, b1)):
            add_face(k.solid, [k.solid.verts.new(B(e0.x, e0.y, y - 0.02)), k.solid.verts.new(B(e1.x, e1.y, y - 0.02)),
                               k.solid.verts.new(top1), k.solid.verts.new(top0)], None)
        stroke3(k.ink, [top0, top1], 0.04)
    for j in range(5):
        p = lathe_bank[j] - rd * 0.3
        ground_stroke(k.ink, [p + rn * 0.15, p - rd * 0.35], y, 0.02, 0.02)
    compass(k, stone - rd * 0.2, 0.75, y, 846, 0.55)
    # cart tracks: pairs of wobbling ruts from the entries across the field to the steps (the procession's real paths)
    for ti, tr in enumerate(CART_TRACKS):
        for s_ in (-0.5, 0.5):
            pts = []
            for i in range(len(tr) - 1):
                a, b_ = tr[i], tr[i + 1]
                d = (b_ - a)
                nseg = max(2, int(d.length / 0.8))
                nrm = V((-d.y, d.x)).normalized()
                for t in range(nseg):
                    pts.append(a + d * (t / nseg) + nrm * (s_ + 0.06 * math.sin(t * 1.7 + ti)))
            pts.append(tr[-1] + V((-(tr[-1] - tr[-2]).y, (tr[-1] - tr[-2]).x)).normalized() * s_)
            run = []
            for p in pts:
                if inside(p, wf) and rnd.random() > 0.08:
                    run.append(p)
                elif len(run) > 1:
                    ground_stroke(k.ink, run, y, 0.045, 0.03)
                    run = []
                else:
                    run = []
            if len(run) > 1:
                ground_stroke(k.ink, run, y, 0.045, 0.03)
    # 'miracle' sprouts: little drawn stalks with coin leaves (pencil) along the beds
    for i in range(46):
        a = RAD(rnd.uniform(98, 196))
        p = POND_C + V((math.cos(a), math.sin(a))) * rnd.uniform(13.5, 30)
        if not rf(p) or on_road(p):
            continue
        hh = rnd.uniform(0.35, 0.7)
        stroke3(k.ink, [B(p.x, p.y, y), B(p.x + 0.04, p.y, y + hh)], 0.025)
        for s_ in (-1, 1):
            cc = V((p.x + 0.12 * s_, p.y))
            pts = [B(cc.x + math.cos(t) * 0.09, cc.y, y + hh * 0.8 + math.sin(t) * 0.09) for t in [j * 1.26 for j in range(6)]]
            stroke3(k.sketch, pts, 0.02)
    # the procession road: drawn track from both entries to the steps, deep wheel ruts
    for line, wd in ((ROAD_F, 1.35), (ROAD_N, 1.1)):
        rp = ccw(strip_poly(line, wd))
        fill(k.road, rp, y + 0.012, uv=False)
        for s_ in (-0.55, 0.55):
            pts = []
            for i, p in enumerate(line):
                a_ = line[max(0, i - 1)]
                b_ = line[min(len(line) - 1, i + 1)]
                dd = (b_ - a_).normalized()
                pts.append(p + V((-dd.y, dd.x)) * s_)
            ground_stroke(k.ink, pts[:-1] + [pts[-1]], y, 0.05)
    cracks(k.ink, wf, y, 10, 845, avoid=lambda p: on_road(p))
    # posts along the procession: tall stakes, the near ones real with paper charms, the far ones drawn
    for i, t in enumerate((0.15, 0.32, 0.5, 0.68, 0.86)):
        seg = ROAD_F
        L_ = [(seg[j + 1] - seg[j]).length for j in range(len(seg) - 1)]
        tot = sum(L_)
        d_ = t * tot
        j = 0
        while j < len(L_) - 1 and d_ > L_[j]:
            d_ -= L_[j]
            j += 1
        p = seg[j] + (seg[j + 1] - seg[j]).normalized() * d_
        dd = (seg[j + 1] - seg[j]).normalized()
        for s_ in (-1, 1):
            q = p + V((-dd.y, dd.x)) * 1.9 * s_
            if i < 3:
                box(k.wood, (q.x, q.y), (0.14, 2.4, 0.14), y, 0)
                stroke3(k.ink, [B(q.x, q.y, y), B(q.x, q.y, y + 2.4)], 0.03)
                wavy_banner(k.paperback, k.ink, (q.x, q.y, y + 2.3), (dd.x, dd.y), 0.5, 0.6, 850 + i)
            else:
                stroke3(k.sketch, [B(q.x, q.y, y), B(q.x, q.y, y + 2.4)], 0.035)
    # an unfinished watch hut on the north rim, a coin tree (pencil crown, real trunk), a fallen cart
    unfinished_house(k, (47.2, 4.4), 3.0, 2.2, 2.4, 128, y, 861, roof=1.4)
    tc = V((35.4, -11.6))
    lathe(k.bark, (tc.x, tc.y), [(0.45, 0.0), (0.32, 1.2), (0.26, 2.2)], seg=7, y0=y)
    stroke3(k.ink, [B(tc.x - 0.3, tc.y, y), B(tc.x - 0.22, tc.y, y + 2.2)], 0.03)
    for i in range(7):
        a = RAD(i * 51)
        p1 = tc + V((math.cos(a), math.sin(a))) * rnd.uniform(1.2, 2.0)
        stroke3(k.ink if i % 2 else k.sketch, [B(tc.x, tc.y, y + 2.1), B(p1.x, p1.y, y + rnd.uniform(3.2, 4.2))], 0.04)
        for j in range(3):
            q = tc + (p1 - tc) * rnd.uniform(0.6, 1.2) + V((rnd.uniform(-0.3, 0.3), rnd.uniform(-0.3, 0.3)))
            yy = y + rnd.uniform(3.0, 4.4)
            stroke3(k.sketch, [B(q.x + math.cos(t) * 0.16, q.y, yy + math.sin(t) * 0.16) for t in [m * 0.7 for m in range(10)]], 0.025)
    for (cc, rx, h, t, sd) in (((31.0, 8.0), 1.1, 1.6, 2, 871), ((49.6, 3.0), 1.0, 1.2, 1, 872), ((33.0, -13.4), 1.2, 1.0, 1, 873),
                               ((52.6, -1.6), 0.9, 2.2, 2, 874)):
        rock_wire(k, hexp(cc, rx, sd), y, h, t, sd, wire=0.45)
    # the long flight from the alley over the gap (all real on this page; the alley page shows its top dissolving)
    top, d, sw, n, rise, run = ALLEY_STAIR
    steps(k, top, d, sw, n, rise, run, YA, n, seed=875, down=True)
    for (c, rx, rz, rot, sd) in (((38.0, 1.0), 1.4, 0.5, 0.3, 1), ((44.0, -14.0), 1.2, 0.45, -0.4, 2), ((36.0, -6.0), 1.0, 0.4, 0.2, 3)):
        smudge(k, c, rx, rz, rot, y, 880 + sd)
    # light: none warm. a faint cold sheen on the pond rim is the only accent (the fish is down there)
    # vista: alley bank + houses up north, abyss, cave, spires
    vk = kv
    abyss_floor(vk, (45.0, -8.0), 80.0, 60.0, 890)
    for (cc, sz, hh, yaw) in (((20.6, 23.6), 3.4, 4.6, 205), ((26.0, 25.0), 3.0, 4.0, 212), ((15.2, 21.6), 3.0, 5.6, 200)):
        box(vk.solid, cc, (sz, hh, sz * 0.9), YA, yaw)
    pa = ccw(jag(P_ALLEY, 3.0, 0.3, 891))
    fill(vk.walk, pa, YA, uv=False)
    walls(vk.solid, vk.ink, None, pa, YA, FLOOR, 892, ledge=1.3, ledge_out=0.3, hatch_floor=YA - 2, hatch_density=0.0, deep=vk.dark, deep_y=YA - 3.0, vstroke=0.2)
    vista_tree(vk, detail=0.5)
    stacks(vk, [((62.0, -2.0), 1.6, -4.0, []), ((70.0, -14.0), 1.4, -2.5, [('M_BookBlue', 0, 0, 15)]), ((48.0, -32.0), 1.4, -5.0, []),
                ((66.0, -30.0), 1.8, -3.5, [])], 893)
    vista_spires(vk, (45.0, -8.0), 128, 894)
    cave(vk, (45.0, -8.0), 128, 895)
    exits = [(AREA_FIELD['exits'][0], (-0.42, 0.91), YF, 'M_PaintBlue', True),
             (AREA_FIELD['exits'][1], (-1.0, -0.05), YF, 'M_PaintBlue', True)]
    return finish_area(A, 'a_field', k, kd, None, kv, exits=exits)


def build_slice2(A):
    TRIS.clear()
    build_plaza(A)
    build_alley(A)
    build_hideout(A)
    build_cart(A)
    build_field(A)
    return TRIS


# ============================================================================================ dressing / layout
CHAIR_SEAT = 0.5
SLICE2_DRESSING = [
    # plaza: finished painted towers and houses on the rim (colour = near the king), lamps round the audience
    ('Tower_Dome', -9.0, 32.4, 165, 1.0, 'a_plaza', 0.0, 'north rim, behind the gate-side audience'),
    ('Tower_Dome', 7.0, 26.6, 230, 1.15, 'a_plaza', 0.0, 'behind the theatre north end: frames the stage crown'),
    ('House_4', 11.6, 8.2, 255, 0.9, 'a_plaza', 0.0, 'east rim by the alley neck'),
    ('LampPost', -11.5, 19.5, 120, 1.0, 'a_plaza', 0.0, 'point light needed (local -0.38, 2.6, 0)'),
    ('LampPost', -11.6, 11.0, 60, 1.0, 'a_plaza', 0.0, 'point light needed (moved off the porridge stall 10/23)'),
    ('LampPost', -3.0, 3.0, 20, 1.0, 'a_plaza', 0.0, 'point light needed'),
    ('LampPost', -6.0, 26.0, 160, 1.0, 'a_plaza', 0.0, 'point light needed'),
    ('Bench_Puppet', -8.6, 14.8, 70, 1.0, 'a_plaza', 0.0, 'audience bench'),
    ('Bench_Puppet', -9.2, 11.2, 80, 1.0, 'a_plaza', 0.0, ''),
    ('Basket', -10.6, 21.6, 30, 1.0, 'a_plaza', 0.0, 'food brought for the guest'),
    ('Basket', -8.2, 20.2, 200, 0.9, 'a_plaza', 0.0, ''),
    ('Barrel', 5.6, 12.2, 0, 1.0, 'a_plaza', 0.0, ''),
    ('Banner_Unfinished', -13.2, 21.0, 90, 1.0, 'a_plaza', 0.0, 'by the gate stairs'),
    ('PaintPot', 4.4, 6.6, 30, 1.0, 'a_plaza', 0.0, 'a painter left it by the unfinished board frame'),
    ('Scrap_Paper_2', -4.0, 6.0, 20, 1.0, 'a_plaza', 0.0, ''),
    # alley: houses by completion (near the plaza = more finished), chairs (lumps seated: see alley_seated_lumps)
    ('House_4', 15.2, 21.6, 200, 0.85, 'a_alley', 0.0, 'chair + lump in front'),
    ('House_3', 20.6, 23.6, 205, 0.85, 'a_alley', 0.0, 'z_mother_house'),
    ('House_2', 26.0, 25.0, 212, 0.85, 'a_alley', 0.0, ''),
    ('Chair', 25.0, 16.4, 120, 1.0, 'a_alley', 0.0, 'a heap of spare chairs beyond the rail (the creaky-chair alley)'),
    ('Chair', 25.9, 16.0, 300, 1.0, 'a_alley', 0.0, ''),
    ('Chair', 24.3, 15.7, 210, 0.95, 'a_alley', 0.0, ''),
    ('Sketch_Wall_1', 19.8, 14.2, 345, 1.0, 'a_alley', 0.0, 'unfinished wall on the south margin'),
    ('Lantern_Hanging', 30.4, 20.0, 250, 0.9, 'a_alley', 0.0, 'the only warm light at Kinopio\'s door: point light'),
    ('Scrap_Paper_1', 22.4, 18.4, 0, 1.0, 'a_alley', 0.0, ''),
    ('Scrap_Paper_3', 28.0, 21.6, 120, 1.0, 'a_alley', 0.0, ''),
    ('Sketch_Fence_2', 13.4, 22.8, 110, 1.0, 'a_alley', 0.0, 'between the plaza neck and House_4'),
    # hideout: nothing big - the stash is in hideout_stash
    # depot: crates and baskets of sorted things, the lantern at the shed mouth, the collectors' sorting bench
    ('Crate', 9.8, -6.0, 15, 1.0, 'a_cart', YC, ''),
    ('Crate', 10.4, -7.2, 70, 0.9, 'a_cart', YC, ''),
    ('Basket', 16.6, -11.6, 10, 1.0, 'a_cart', YC, 'books and a spoon inside'),
    ('Barrel', 21.4, -3.8, 0, 1.0, 'a_cart', YC, 'road side'),
    ('Lantern_Hanging', 17.4, -7.0, 260, 1.0, 'a_cart', YC, 'shed mouth: point light (only warm light in the depot)'),
    ('Bench_Puppet', 14.2, -11.8, 0, 1.0, 'a_cart', YC, ''),
    ('Cart', 24.4, -5.0, 90, 0.9, 'a_cart', YC, 'second (empty) cart already on the road'),
    ('Scrap_Paper_2', 12.4, -4.0, 40, 1.0, 'a_cart', YC, ''),
    # field: procession carts waiting on the road, the watch post, paper scraps
    ('Cart', 37.6, -5.0, 120, 0.9, 'a_field', YF, 'procession cart (loaded on offering day)'),
    ('Cart', 42.6, -7.8, 125, 0.9, 'a_field', YF, ''),
    ('Signpost', 34.0, -2.4, 110, 1.0, 'a_field', YF, 'west entry'),
    ('Sketch_Tree_3', 50.6, 2.6, 0, 1.1, 'a_field', YF, 'dead drawn tree on the north-east rim'),
    ('Sketch_Fence_1', 39.8, 7.6, 170, 1.0, 'a_field', YF, 'north rim'),
    ('Scrap_Paper_1', 45.6, -5.0, 0, 1.0, 'a_field', YF, ''),
    ('Scrap_Paper_3', 49.0, -12.4, 60, 1.0, 'a_field', YF, 'on the steps'),
    ('Basket', 47.6, -13.8, 200, 1.0, 'a_field', YS, 'offering basket on the steps'),
]
ALLEY_SEATED = [{'chair': r2(c), 'yaw': y_, 'lump': LUMPS[i], 'seat_y': YA + CHAIR_SEAT} for i, (c, y_) in enumerate(ALLEY_CHAIRS)]
KID_CHAIR = {'chair': r2(KP(0.6, -0.9)), 'yaw': K_YAW, 'lump': 'Lump_2', 'seat_y': YA + CHAIR_SEAT,
             'note': '형의 덩어리: Lump_2(붉은 표시 Mark = 주인공 망토와 같은 붉은 끈). 의자는 열린 앞쪽(카메라)을 봄'}
HIDEOUT_STASH = [('Junk_Book', 0.0, 0.0), ('Junk_Teacup', 0.0, 0.0), ('Junk_Clock', 0.0, 0.0), ('Junk_Shoe', 0.0, 0.0),
                 ('Junk_Umbrella', 0.0, 0.0), ('Junk_Lantern', 0.0, 0.0)]


def hideout_stash_list():
    """stash props on the root shelves (y = shelf top; the raycast hits the Cliffs_hideout shelves) + by the nest."""
    c = H_C
    stash = HIDE_PTS['z_hideout_stash']
    sdir = (stash - c).normalized()
    yaw_ = math.degrees(math.atan2(sdir.x, sdir.y))
    sn = side(yaw_)
    out = []
    shelf = [(0.7, 0.0, [('Junk_Teacup', -0.75), ('Junk_Clock', 0.7)]), (1.35, 0.25, [('Junk_Shoe', -0.5)]), (2.0, -0.2, [('Junk_Book', 0.35)])]
    for (hh, off, items) in shelf:
        sc_ = c + sdir * (H_WALL_R - 0.6) + sn * off
        for (m, u) in items:
            p = sc_ + sn * u
            out.append({'model': m, 'pos': r2(p), 'y': round(YH + hh + 0.12, 2), 'yaw': round(yaw_ + 180, 1), 'scale': 0.9})
    out.append({'model': 'Junk_Umbrella', 'pos': r2(stash - sn * 1.3 - sdir * 0.5), 'y': YH, 'yaw': round(yaw_ + 120, 1), 'scale': 1.0,
                'note': '선반 옆 바닥(눕혀 둠)'})
    out.append({'model': 'Junk_Lantern', 'pos': r2(HIDE_PTS['hideout_lantern']), 'y': YH, 'yaw': 0, 'scale': 1.1,
                'note': '따뜻한 점광원(범위 4m, FFB866) — 굴의 등'})
    out.append({'model': 'Junk_Book', 'pos': r2(HIDE_PTS['z_hideout_nest'] + V((0.25, -0.1))), 'y': YH + 0.15, 'yaw': 30, 'scale': 1.0})
    return out


def patch_dressing_json(path=None):
    """replace items of the five new areas in art/layout_dressing.json (other areas untouched)."""
    path = path or os.path.join(ART, 'layout_dressing.json')
    d = json.load(open(path, encoding='utf-8'))
    keep = [it for it in d['items'] if it.get('area') not in NEW_IDS]
    for (m, x, z, yaw, sc, area, yy, note) in SLICE2_DRESSING:
        it = {'model': m, 'pos': [x, z], 'yaw': yaw, 'scale': sc, 'place': area[2:], 'area': area, 'y': yy}
        if note:
            it['note'] = note
        keep.append(it)
    d['items'] = keep
    d['count'] = len(keep)
    if '"y"' not in d.get('_doc', '') and 'y = ' not in d.get('_doc', ''):
        d['_doc'] = d['_doc'] + ' (10/23 slice 2) y = the ground height the item expects: use it if the raycast misses (depot/field stand at -2.5, pond steps -2.8).'
    json.dump(d, open(path, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
    return len(keep)


def write_layout_json(path=None, all_areas=None):
    path = path or os.path.join(ART, 'layout_slice2.json')
    P = {}
    for dct in (PLAZA_PTS, ALLEY_PTS, HIDE_PTS, CART_PTS, FIELD_PTS):
        P.update(dct)
    zr = {'z_stage': 5, 'z_doll_seat': 2, 'z_board': 2.5, 'z_board_s': 2.5, 'z_chief_seat': 1.5, 'z_pedestal': 1.5, 'z_crowd_rows': 6,
          'z_back_corner': 1.5, 'z_bell': 1.5, 'z_crowd_offer': 3, 'z_kid_house': 1.6, 'z_kid_house_chair': 0.9, 'z_sawdust': 0.7,
          'z_crack': 1.0, 'z_mother_house': 2.0, 'z_lump': 1.2, 'z_hideout_stash': 1.2, 'z_hideout_drawing': 1.2, 'z_hideout_nest': 1.0,
          'z_hideout_talk': 1.6, 'z_cart': 1.5, 'z_cart_lock': 0.9, 'z_depot': 2.5, 'z_satchel': 0.9, 'z_field_pile': 3,
          'z_cart_procession': 2.0, 'z_sign': 1.5, 'z_page': 1.0, 'z_pond_stop': 3, 'z_pond_edge': 1.6, 'z_pond_bank': 1.4,
          'z_pond_center': 3, 'z_pond_stone': 1.5}
    zones = {k: r2(v) for k, v in P.items() if k.startswith('z_')}
    facing = {'stage': ST_YAW, 'doll': ST_YAW, 'fish_prop': ST_YAW, 'pedestal': ST_YAW, 'lump_prop': ST_YAW, 'board': ST_YAW,
              'ins_board_1': ST_YAW, 'ins_board_2': ST_YAW, 'ins_board_3': ST_YAW, 'ins_board_4': ST_YAW, 'ins_stage': ST_YAW,
              'actor_a': ST_YAW, 'actor_b': ST_YAW, 'actor_c': ST_YAW, 'crowd_plaza': 68, 'chief': ST_YAW + 30,
              'cart': 90, 'satchel': 270, 'collector_boss': 300, 'collectors': 200,
              'pond_stone': 25, 'sign': 120, 'page': 120, 'stacker': 230, 'crowd_field': 140, 'fish': 315, 'mother': 205,
              'crowd_alley': 70, 'kid_house_chair': K_YAW}
    props = {}
    for kk in ('stage', 'doll', 'fish_prop', 'pedestal', 'lump_prop', 'board', 'bell', 'chairs', 'mother_lump', 'kid_house_chair', 'cart',
               'satchel', 'field_pile', 'field_mound', 'tracks', 'sign', 'page', 'pond', 'pond_stone'):
        if kk in P:
            props[kk] = {'pos': r2(P[kk])}
            if kk in facing:
                props[kk]['facing'] = facing[kk]
    npcs = {'chief_plaza': {'spawn': r2(PLAZA_PTS['z_chief_seat']), 'facing': round(ST_YAW + 30, 1), 'note': '촌장 광장 자리(무대 오른쪽 앞)'},
            'actor_a': {'spawn': r2(P['actor_a']), 'facing': ST_YAW}, 'actor_b': {'spawn': r2(P['actor_b']), 'facing': ST_YAW},
            'actor_c': {'spawn': r2(P['actor_c']), 'facing': ST_YAW},
            'crowd_plaza': {'spawn': r2(P['crowd_plaza']), 'facing': 68, 'count': 6, 'note': '청중 반원 ±2.4m 안쪽(모두 걷는 땅)'},
            'mother': {'spawn': r2(P['mother']), 'facing': 205}, 'crowd_alley': {'spawn': r2(P['crowd_alley']), 'facing': 70, 'count': 4},
            'stacker': {'spawn': r2(P['stacker']), 'facing': 230}, 'crowd_field': {'spawn': r2(P['crowd_field']), 'facing': 140, 'count': 5},
            'collector_boss': {'spawn': r2(P['collector_boss']), 'facing': 300, 'note': '수거꾼 우두머리(대화 5), 분류 탁자 뒤'},
            'collectors': {'spawn': r2(P['collectors']), 'facing': 200, 'count': 3, 'note': '수거꾼(실루엣) — 수레 옆'},
            'fish': {'spawn': r2(POND_C), 'facing': 315}}
    out = {
        '_doc': '2차 슬라이스(10/23) 꼭두 광장 · 삐걱의자 골목 · 키노피오의 비밀 굴(새 구역) · 수레 길(수거꾼 창고) · 기적의 밭·먹물 웅덩이 디오라마 배치. '
                '좌표 = Unity 월드 [x, z] (높이는 레이캐스트; heights·y 값은 참고). areas[] = 일곱 구역 전부(a_fall·a_gate 모양은 layout_slice1 그대로, '
                '출구 spawn만 고침) — chapter1.json areas[]를 이것으로 통째로 바꿈. positions = 같은 id의 pos/spawn/facing 덮어쓰기, 새 id는 새로 만듦. '
                '각도 = 도(0 = +Z). 생성: art/blender/ouat_slice2.py write_layout_json(). 주의: SceneBuilder LoadSlice는 layout_slice*.json을 이름순으로 읽고 '
                '앞 파일의 키가 이김 — 이 파일의 키는 slice1과 겹치지 않게 지음(areas만 겹침: areas는 SceneBuilder가 읽지 않음).',
        'heights2': {'plaza': YP, 'alley': YA, 'hideout': YH, 'depot': YC, 'field': YF, 'pond_steps': YS, 'pond_apron': YO, 'pond_surface': YPOND,
                     'note': '광장·골목 0 → 굴 -0.4 → 창고·밭 -2.5 → 웅덩이 둘레 -3.1. 웅덩이 검은 면(-3.16)은 Ground_Walk_field에 포함(걸을 수 있는 마른 먹) — '
                             'Pond.fbx는 0.9배로 Ground()에 그대로 두면 Surface가 그 위에 얹힘'},
        'areas': all_areas,
        'places2': {k: {'center': v[0], 'radius': v[1]} for k, v in PLACES2.items()},
        'positions2': {
            'zones': zones,
            'zone_radius': {k: v for k, v in zr.items() if k in zones},
            'props': props,
            'npcs': npcs,
            'inscriptions': {k: r2(P[k]) for k in ('ins_stage', 'ins_board_1', 'ins_board_2', 'ins_board_3', 'ins_board_4', 'ins_chair', 'ins_sign', 'ins_pond')},
            'inscription_facing': {'ins_stage': ST_YAW, 'ins_board_1': ST_YAW, 'ins_board_2': ST_YAW, 'ins_board_3': ST_YAW, 'ins_board_4': ST_YAW,
                                   'ins_sign': 120, 'ins_pond': 25},
            'readables': {'rd_page': r2(P['rd_page'])},
            'puzzles': {'pz_pedestal': r2(P['pz_pedestal']), 'pz_string': r2(P['pz_string']), 'pz_pick': r2(P['pz_pick']), 'pz_cart': r2(P['pz_cart'])},
            'removed': {'ins_board_5': '그림판은 4장(왕의 풀이 4개) — 다섯째 자리 없음', 'z_fence/fence/pz_fence': '수레 길 울타리는 이번 창고 구역에 없음(옛 (-28,-4)는 길목 남쪽 선반 밖)'},
        },
        'stage_place': {'pos': r2(ST_C), 'yaw': ST_YAW, 'note': 'Stage.fbx를 이 자리·이 yaw로(지금 SceneBuilder는 at+(0,2.4)·yaw 180 고정). 무대 앞(관객) = 서남서, 길목 계단과 마주봄. '
                                                           '극장 틀(탑·아치·막·볏·천막)은 Level의 Cliffs_plaza/Decor_plaza에 있음'},
        'picture_boards': [{'id': f'ins_board_{i + 1}', 'pos': r2(b), 'yaw': ST_YAW} for i, b in enumerate(BOARDS)],
        'bell': {'tower': r2(BELL_TOWER), 'zone': r2(PLAZA_PTS['z_bell']), 'part': 'Level_Ch1/Area_a_plaza/Bell_plaza',
                 'note': '종 = 따로 된 부품, 피벗 = 매달린 점. 로컬 X로 ±12~18° 흔들면 울림. 종소리 행렬 방향 = 종탑 옆 계단(창고) → 밭'},
        'alley_seated_lumps': ALLEY_SEATED,
        'kid_house_chair': KID_CHAIR,
        'kid_house': {'pos': r2(K_C), 'yaw': K_YAW, 'sawdust': r2(ALLEY_PTS['z_sawdust']),
                      'note': '키노피오 집 = Level 지형(Cliffs_alley). 앞벽은 연필선뿐 → 카메라에서 안이 보임. 톱밥 더미도 지형'},
        'hideout_stash': hideout_stash_list(),
        'satchel': {'part': 'Level_Ch1/Area_a_cart/Satchel_cart', 'pos': r2(CART_PTS['satchel']), 'zone': r2(CART_PTS['z_satchel']),
                    'note': '주인공 가방 = 창고 앞 기둥 고리에 걸림. 되찾으면 이 부품을 끄면 됨'},
        'pond_lineup': [{'pos': r2(p), 'facing': round(math.degrees(math.atan2((POND_C - p).x, (POND_C - p).y)) % 360, 1)} for p in LINEUP],
        'pond_lineup_note': '막오름 날 주민 줄: 웅덩이 둘레(반지름 9.2·10.25) 서북~서남 반원, 모두 웅덩이를 봄. 물고기 장면용 빈 무대 = 웅덩이 둘레(반지름 6.1~8.5)',
        'game_camera2': {k: {**v[0], 'pivot_rect': list(v[1])} for k, v in GAME_CAM2.items()},
        'game_camera2_note': 'bounds = 피벗 범위 + 4m(FollowCamera가 4m 안쪽으로 묶음). Place_* CameraZone(우선순위 1)이 이 값을 덮으면 같은 값으로 맞출 것',
        'lights2': {
            'a_plaza': {'stage_lamps': [r2(SP(3.95, -0.1)), r2(SP(-3.95, -0.1))], 'stage_spot': {'pos': r2(SP(0, 4.0)), 'height': 7.5, 'color': 'FFC27A',
                        'note': '무대만 따뜻하게(약하게, 그림자 끔)'}, 'board_lamps': [r2(SP(ka, 0.05)) for ka in (10.4, 6.6, -6.6)],
                        'lamp_posts': 'layout_dressing LampPost 4개 각각 점광원 FFC870 세기 5 범위 8',
                        'mood': 'AreaSystem a_plaza 그대로(가장 칠해진 곳)'},
            'a_alley': {'kid_door_lantern': 'Lantern_Hanging (30.4, 20.0)', 'note': '골목은 어둑. 키노피오 집 앞 등 하나만 따뜻하게'},
            'a_hideout': {'knot_hole_spot': {'pos': [42.7, YH + 9.0, 29.8], 'target': [42.7, YH, 29.8], 'spot_angle': 14, 'color': 'FFDDA8'},
                          'lantern': r2(HIDE_PTS['hideout_lantern']), 'note': '굴 = 낙하터 다음으로 따뜻한 곳. Moods에 a_hideout 칸 추가 필요(areas[].mood 참고)'},
            'a_cart': {'shed_lantern': 'Lantern_Hanging (17.4, -7.0)', 'note': '창고는 어둡고 빠짐. 창고 입구 등 하나'},
            'a_field': {'note': '밭은 가장 어두움. 따뜻한 빛 없음. 웅덩이 = 검은 면(M_Pond)'},
        },
        'scenebuilder_notes2': [
            'areas[]: 이 파일의 areas로 chapter1.json areas를 통째로 바꿈(a_hideout 새로, a_gate→a_plaza/a_cart spawn 고침). places에 hideout·depot 추가(places2)',
            'AreaSystem.Moods에 a_hideout 칸 추가: ambient (0.42,0.36,0.30), key (0.85,0.70,0.52) 0.38, drain 0.30, bg (0.20,0.17,0.15) — 없으면 골목 분위기가 그대로 남음',
            'BuildLevel: Decor_*는 콜라이더 없음·그림자 켬(이름 규칙상 이미 그렇게 됨). Bell_plaza·Satchel_cart·Face_hideout도 콜라이더 없음. Light_plaza/hideout/cart는 Light_fall과 같은 처리',
            'stage: Model("Stage", Ground(stage_place.pos), stage_place.yaw) — 지금의 at+(0,2.4)·yaw 180은 극장 틀과 어긋남',
            'board: 그림판 4장 = picture_boards (yaw 248, 극장 양옆 틀 안). ins_board_5 없앰',
            'BuildDressing: 광장 Tower_Dome 3개·LampPost 5개·골목 House 6채 하드코딩 빼기 → layout_dressing.json(a_plaza·a_alley 항목)이 대신함. LampPost(꾸밈)에도 점광원 붙이기',
            'chairs: 지금 골목 의자 6개 하드코딩 → alley_seated_lumps(의자 + 덩어리, 덩어리 y = seat_y)로. 형 덩어리 = kid_house_chair',
            'cart: 수레 = 창고 마당(13.4,-7.2) yaw 90(동쪽 길을 봄), 바퀴 고정쇠 쪽 = 북쪽(z_cart_lock). YawToward(at,(54,-15)) 빼기',
            'pond: Ground(at,0.02)는 이제 웅덩이 검은 면(-3.16)에 닿음 → Pond.fbx 0.9배 그대로 맞음',
            'hideout_stash: Junk_* 를 y 값 높이에(뿌리 선반 = Cliffs_hideout, 레이캐스트도 선반에 닿음)',
            '키노피오 길잡이: 골목 → 굴은 alley 출구(틈새, 반지름 0.8). 틈 폭 약 0.9m → 주인공 NavMeshAgent 반지름 0.35 이하여야 지나감',
            'layout_dressing.json: 새 필드 y(기대 땅 높이) — 레이캐스트가 비면 이 값. 창고·밭 꾸밈은 -2.5',
            '카메라: 각 구역 camera 값이 Place_* CameraZone에 덮이지 않게(slice1과 같은 문제)',
        ],
        'placeholders_used2': {
            'a_plaza': ['Stage', 'PictureBoard x4', 'Tower_Dome', 'House_4', 'LampPost', 'Bench_Puppet', 'Basket', 'Barrel', 'Banner_Unfinished', 'PaintPot'],
            'a_alley': ['House_1~4', 'Chair + Lump_1/2/3', 'Lantern_Hanging', 'Sketch_Fence_2', 'Scrap_Paper'],
            'a_hideout': ['Junk_* (숨긴 물건)'],
            'a_cart': ['Cart(+ItemPile Items)', 'Crate', 'Basket', 'Barrel', 'Lantern_Hanging', 'Bench_Puppet'],
            'a_field': ['Cart x2', 'Signpost', 'Sketch_Tree_3', 'Sketch_Fence_1', 'Basket', 'Pond(0.9)', 'StoneTablet(pond_stone)', 'PinocchioPage'],
        },
        'tris2': {k: v.get('_total') for k, v in TRIS.items()},
    }
    json.dump(out, open(path, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
    return path


# ============================================================================================ polish round (slice 3 json: changed keys only)
def write_layout3_json(path=None):
    path = path or os.path.join(ART, 'layout_slice3.json')
    stone = FIELD_PTS['z_field_stone']
    rd = (POND_C - stone).normalized()
    out = {
        '_doc': '2차 슬라이스 다듬기(10/23 밤). layout_slice2.json에서 바뀐 것만. 키 이름은 slice1·2와 겹치지 않게 지음(SceneBuilder LoadSlice는 앞 파일 키가 이김). '
                '좌표 = Unity 월드 [x, z]. 생성: art/blender/ouat_slice2.py write_layout3_json().',
        'areas_patch3': {'a_plaza': {'bounds': _bounds(PIVOT_PLAZA),
                                     'note': '피벗 범위 서쪽 끝 -12.5 → -9.5: 길목 계단 발치에서도 카메라가 계단 위가 아니라 무대를 봄(시작 화면). 출구·spawn은 그대로'}},
        'positions3': {
            'zones_checked': {k: r2(v) for k, v in (('z_porridge', PLAZA_PTS['z_porridge']), ('z_depot_barrel', CART_PTS['z_depot_barrel']),
                                                     ('z_alley_window', ALLEY_PTS['z_alley_window']), ('z_field_stone', stone),
                                                     ('z_pond_lineup', FIELD_PTS['z_pond_lineup']), ('z_lump_spat', FIELD_PTS['z_lump_spat']))},
            'zones_checked_note': '메인 표 좌표 그대로 둠 — 모두 걷는 땅·제 구역·카메라에서 잘 보임(check_layout2.py). 바꾼 zone 없음',
            'npcs': {'neighbor': {'spawn': r2(ALLEY_PTS['neighbor_window']), 'facing': 200,
                                  'note': '이웃 = 창 안쪽(걷는 땅 밖, 제자리 서 있기 — NavMeshAgent 끄거나 Warp). 창턱 0.95m, 창 0.95~2.0m'},
                     'porridge': {'spawn': r2(PLAZA_PTS['z_porridge'] + PORRIDGE_OFF - fwd(PORRIDGE_YAW) * 0.75), 'facing': PORRIDGE_YAW,
                                  'note': '죽 주는 이 = 카운터 뒤 솥 옆(걷는 땅), 손님(z_porridge)과 카메라 쪽을 봄'}},
            'props': {'field_stone': {'pos': r2(stone - rd * 0.35), 'facing': round(math.degrees(math.atan2(rd.x, rd.y)), 1),
                                      'note': 'NoseFileStone = 밭둑(높이 0.55, 웅덩이 쪽) 뒤 그늘 쪽. 줄 선 주민 쪽에서 둑에 가려짐'}},
        },
        'pond_lineup3': [{'pos': r2(p), 'facing': round(math.degrees(math.atan2((POND_C - p).x, (POND_C - p).y)) % 360, 1), 'row': 0 if i < 8 else 1}
                         for i, p in enumerate(LINEUP)],
        'pond_lineup3_note': '16자리(앞줄 8 반지름 8.4 · 뒷줄 8 반지름 9.75, 웅덩이 둘레 북서~서남). z_pond_lineup(51.6,-11.6) r4.5 안팎. 문 기둥은 각 124°·166° 반지름 12.7로 벌리고 3.4m로 낮춤 → '
                             '짚기 카메라(웅덩이 쪽을 봄)에서 줄을 가리지 않음. 이 구간 웅덩이 둘레 돌 없음. 뱉은 덩어리(z_lump_spat)는 앞줄 안쪽',
        'staging3': {
            'porridge_stall': {'pos': r2(PLAZA_PTS['z_porridge'] + PORRIDGE_OFF), 'yaw': PORRIDGE_YAW, 'part': 'Cliffs_plaza(솥·화덕·카운터) + Decor_plaza(반만 칠한 지붕)',
                               'note': '반쯤 지은 천막(기둥 둘·지붕 한 면만), 화덕 위 솥·국자·그릇, 김은 연필선. 불빛 웅덩이 Light_plaza. 점광원 권장 (솥 위 1.2m, FFB866, 범위 3)'},
            'depot_barrel': {'pos': r2(CART_PTS['z_depot_barrel']), 'top_y': round(YC + 0.9, 2), 'part': 'Cliffs_cart',
                             'note': '뚜껑 없는 통(카메라 쪽 통널만 실물, 뒤는 연필, 테 먹선). 키노피오는 윗면 y -1.6(통 안 어두운 면 -1.8)에 서면 됨'},
            'alley_window': {'wall_center': [29.0, 25.5], 'yaw': 200, 'sill_y': 0.95, 'zone': r2(ALLEY_PTS['z_alley_window']), 'part': 'Cliffs_alley',
                             'note': '이웃집은 골목 쪽 벽과 창만 실물(창턱·덧문 하나), 나머지 집은 연필 상자. 3m 앞 골목에서 창이 카메라를 봄'},
            'field_ridge': {'pos': r2(stone + rd * 0.95), 'height': 0.55, 'part': 'Cliffs_field', 'note': '밭둑(돌 앞, 웅덩이 쪽)'},
            'cart_tracks': [[r2(p) for p in tr] for tr in CART_TRACKS],
        },
        'lights3': {'alley_window_lamp': {'pos': [29.1, 25.9], 'height': 1.3, 'color': 'FFC870', 'range': 2.5, 'intensity_hint': 1.5, 'note': '이웃 창 안 등(창이 밝게 읽히게)'},
                    'porridge_fire': {'pos': r2(PLAZA_PTS['z_porridge'] + PORRIDGE_OFF - fwd(PORRIDGE_YAW) * 0.25), 'height': 1.2, 'color': 'FFB866', 'range': 3.0, 'intensity_hint': 2.5},
                    'plaza_lamp_moved': 'layout_dressing LampPost (-9.5,8.0) → (-11.6,11.0) (죽 가게 자리 비움)'},
        'vista3': 'a_fall·a_gate의 Vista_* 속 광장 = 새 광장(극장 틀·종 누각·칠한 탑·그림판 틀·가게)으로 바꿈. 자리·방향은 a_plaza와 같음',
        'scenebuilder_notes3': [
            'a_plaza bounds만 areas_patch3 값으로(나머지 areas 값 그대로)',
            '이웃(neighbor)은 창 안 걷는 땅 밖: 에이전트 없이 제자리',
            'field_stone(NoseFileStone)은 positions3.props 자리·facing으로 — 둑 뒤',
            '짚기(pick) 카메라 = z_pond_lineup, 줄 선 주민 자리 = pond_lineup3(16)',
            '죽 가게 점광원 1개(lights3.porridge_fire)',
        ],
    }
    json.dump(out, open(path, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
    return path
