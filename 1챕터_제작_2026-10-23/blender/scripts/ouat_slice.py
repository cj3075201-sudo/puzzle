# -*- coding: utf-8 -*-
"""Slice 1 (10/23): a_fall (빛구멍 언덕) and a_gate (앉은돌 길목) rebuilt as composed dioramas for a low, close
game camera (Chants-of-Sennaar style: every screen is a picture). Everything here is UNITY world (x, z, y-up).

Levels:   fall hilltop  y = H (5.5)       landing / bridge / gate pass  y = G0 (2.5)
          lower drawn ground  y = 0       chasm slot floor  y = FLOOR (-6)
Look:     camera looks EAST (yaw ~95-100). From the hilltop you see down past the ladder ledge, over the chasm
          (rail bridge drawn in ink, books lying on stone pillars), to the gate pass, and further down the painted
          plaza/stage, towers and blue-grey spires.

Parts (per area, under Area_<id>):
  Ground_Walk_<s>  walkable tops (collider + NavMesh)           Margin_<s>  non-walk tops (no collider)
  Cliffs_<s>       walls / rocks / pillars (collider)          Ground_Lines_<s>  ink + hatch + paint decals
  Exit_<s>_<t>     drawn exit marker (pivot = exits[].pos)     Vista_<s>  background layer, NO collider:
                   cheap copies of the neighbour area seen from this page, chasm floor, lower ground, plaza, spires
"""
import math, random, json, os
import bmesh
from mathutils import Vector
from mathutils.geometry import delaunay_2d_cdt
import ouat_lib as L
import ouat_level as LV
from ouat_lib import Part

V = Vector
HERE = os.path.dirname(os.path.abspath(__file__))

# underground value structure: base = lit (only under the ceiling-hole light reaches it), shade = the drained,
# colour-leaked look of everything else. Toon bands: most of the slice sits in the shade band; the light pool in base.
L.MATS.update({
    'M_UnderGround': ('E8E2D3', 'A9A59B', False, 'paper', {'note': 'underground walkable paper ground (slice 1). base = in the light pool, shade = drained grey-beige everywhere else'}),
    'M_UnderRoad':   ('DDD6C6', '9C988E', False, 'paper', {'note': 'drawn path / road strip, a shade darker'}),
    'M_UnderCliff':  ('DAD6CC', '9A9C9E', True,  'paper', {'hatch': False, 'note': 'cliff walls, rocks, pillars (slice 1)'}),
    'M_UnderLow':    ('C9CBCB', '959A9F', False, 'paper', {'hatch': False, 'note': 'lower ground seen below the ledges (vista): cooler and lighter = farther'}),
    'M_VistaGround': ('DEDDD6', 'B0B2B2', False, 'paper', {'hatch': False, 'note': 'ground of the neighbour page seen from this page (cooler, lighter)'}),
    'M_VistaCliff':  ('D3D5D6', 'A4A9AE', True,  'paper', {'hatch': False, 'note': 'cliffs/rocks of the neighbour page seen from this page'}),
    'M_UnderDeep':   ('60656C', '43474D', False, 'paper', {'hatch': False, 'note': 'chasm walls below the lower ground, chasm floor, holes: the deepest places'}),
    # muted copies of the painted town for the far view (colour leaking out with distance / depth)
    'M_VistaTerracotta': ('B48C6C', '8C6D57', True, 'painted', {'note': 'far painted towers (muted terracotta)'}),
    'M_VistaTerraDark':  ('9A7258', '765644', True, 'painted', {'note': 'far domes, beams'}),
    'M_VistaCurtain':    ('A84B3E', '7E362D', True, 'painted', {'note': 'far stage curtain'}),
    'M_VistaNavy':       ('3E4A72', '2C3655', True, 'painted', {'note': 'far stage backdrop'}),
    'M_VistaWood':       ('9C7B5C', '765C45', True, 'painted', {'note': 'far stage boards'}),
    'M_VistaPlaza':      ('C2B59D', '9B907D', False, 'painted', {'note': 'far painted plaza ground'}),
    'M_VistaStone':      ('B7A584', '948469', False, 'painted', {'note': 'far painted hex stones'}),
    'M_Abyss':       ('4F535A', '3A3D43', False, 'paper', {'hatch': False, 'note': 'the abyss floor far below every plateau (darkest drained value, never lit)'}),
    'M_HatchDark':   ('4E5157', '4E5157', False, 'line',  {'note': 'bold diagonal hand hatching modelled on shaded cliff faces (slice 1). unlit flat, double-sided'}),
    'M_Beam':        ('FFF1CF', 'FFF1CF', False, 'light', {'alpha': 0.11, 'note': 'light beam from the ceiling hole to the fall spot. additive; UV v = 0 at the ground -> 1 at the ceiling (fade toward the top); no shadow'}),
    'M_UnderSpire':  ('A6AEB9', '7E8794', False, 'paper', {'hatch': False, 'note': 'blue-grey spires rising from below (vista)'}),
    'M_CaveWall':    ('979EA7', '6F7680', False, 'paper', {'hatch': False, 'note': 'far cave wall, stalactites, columns (vista)'}),
    'M_TornEdge':    ('F4EFE3', 'D6D0C2', False, 'paper', {'note': 'raw paper showing at torn / missing chunks (reads brighter than the drained drawing)'}),
    'M_LightPool':   ('FFEFC8', 'FFEFC8', False, 'light', {'alpha': 0.45, 'note': 'additive light pool decal under the ceiling hole. UV v = 0 centre -> 1 rim; fade alpha to 0 at v = 1. No shadow'}),
    'M_Dust':        ('FFF4D6', 'FFF4D6', False, 'light', {'alpha': 0.8, 'note': 'dust / paper flecks floating in the beam (additive, unlit, no shadow; may drift slowly)'}),
    'M_Smudge':      ('5E5953', '5E5953', False, 'sketch', {'alpha': 0.16, 'note': 'erased graphite smudge decal (transparent, unlit, no shadow)'}),
})
ART = os.path.dirname(HERE)
H = 5.5          # hilltop walk height
G0 = 2.5         # landing, bridge, gate pass
FLOOR = -16.0    # abyss floor (everything stands on drawn stacks rising out of the dark)

# --------------------------------------------------------------------------------------------- layout
# hilltop walk (CCW in x right / z up). Three terraces step DOWN toward the ladder edge so that, from the low game
# camera, the ramp, the bar and the kid below stay visible over the rim (a 3 m drop would hide ~6.5 m below it).
H_HI, H_MID, H_LO = 5.5, 5.1, 4.6
RAMP_T = V((-50.7, 23.1))           # SE prow of the hilltop; the ladder goes down south-east = seen in profile by the camera
RAMP_DIR = V((math.sin(math.radians(145)), math.cos(math.radians(145))))
RAMP_B = RAMP_T + RAMP_DIR * 6.0    # 6.0 m run, 2.1 m drop -> 19 deg (flatter than the camera's sight line)
RAMP_W = 1.8
_rd = (RAMP_B - RAMP_T).normalized()
_rn = V((-_rd.y, _rd.x)) * (RAMP_W / 2)          # left of travel (east-north-east)
RAMP_TL, RAMP_TR = RAMP_T + _rn, RAMP_T - _rn       # TL north-east corner, TR south-west corner
RAMP_BL, RAMP_BR = RAMP_B + _rn, RAMP_B - _rn
CLEFT = [V((-53.75, 22.40)), V((-53.55, 22.80)), V((-53.35, 22.40))]   # 0.35 m gap in the south rim (small bodies only)

WALK_F = [V(p) for p in [(-61.0, 24.4), (-58.6, 23.0), (-55.2, 22.5), (-54.6, 22.45), (-54.0, 22.42)]] + CLEFT + \
         [V((-52.4, 22.3)), RAMP_TR, RAMP_TL] + \
         [V(p) for p in [(-49.85, 25.0), (-49.8, 28.4), (-50.3, 30.6), (-51.0, 33.0), (-52.5, 35.5), (-55.0, 37.1), (-58.0, 37.3),
                         (-60.5, 36.3), (-61.0, 33.0), (-61.1, 28.5)]]
HILL_HI = [V(p) for p in [(-58.8, 27.9), (-57.9, 27.1), (-56.8, 26.75), (-55.6, 27.2), (-54.1, 26.9), (-53.3, 27.6), (-52.8, 28.6), (-53.3, 29.9),
                          (-53.0, 31.6), (-53.9, 32.2), (-54.6, 33.1), (-55.9, 32.7), (-57.2, 33.1), (-58.2, 32.3), (-58.9, 31.1), (-58.5, 29.5)]]
HILL_LO_IN = [V(p) for p in [(-49.8, 28.4), (-51.5, 27.7), (-52.9, 25.6), (-54.3, 24.3), (-54.6, 22.45)]]   # inner border, ccw-continuing
HILL_LO = [V(p) for p in [(-54.6, 22.45), (-54.0, 22.42)]] + CLEFT + [V((-52.4, 22.3)), RAMP_TR, RAMP_TL, V((-49.85, 25.0))] + HILL_LO_IN[:-1]
HILL_MID = [V(p) for p in [(-61.0, 24.4), (-58.6, 23.0), (-55.2, 22.5)]] + list(reversed(HILL_LO_IN)) + \
    [V(p) for p in [(-50.3, 30.6), (-51.0, 33.0), (-52.5, 35.5), (-55.0, 37.1), (-58.0, 37.3), (-60.5, 36.3), (-61.0, 33.0), (-61.1, 28.5)]]
MARGIN_F = [V(p) for p in [(-61.0, 24.4), (-61.1, 28.5), (-61.0, 33.0), (-60.5, 36.3), (-62.9, 37.2), (-65.3, 34.6),
                           (-66.2, 30.2), (-65.6, 26.1), (-63.6, 23.9)]]
MARGIN_DROP = 0.45
# the near (camera-side) edge of the hill breaks into separate paper slabs with dark gaps between them (non-walk)
MARGIN_SLABS = [([V(p) for p in [(-61.25, 24.4), (-61.3, 28.2), (-62.8, 29.0), (-65.5, 28.4), (-65.6, 26.1), (-63.6, 23.9)]], 0.45, 0.06),
                ([V(p) for p in [(-61.35, 29.05), (-61.25, 32.6), (-63.0, 33.1), (-66.0, 32.0), (-66.1, 29.6), (-63.3, 29.75)]], 0.85, -0.05),
                ([V(p) for p in [(-61.2, 33.45), (-60.75, 36.3), (-62.9, 37.2), (-65.1, 34.9), (-63.4, 33.95)]], 0.35, 0.04)]
# L-shaped shelf at the foot of the hill: under the south rim (where the kid lands from the cleft), round the ladder foot,
# then a switchback path north-east through the bar neck to the bridge head
LAND = [V(p) for p in [(-55.8, 19.7), (-52.6, 19.0), (-49.8, 17.6), (-47.6, 17.0), (-45.6, 17.8), (-44.4, 19.2), (-43.3, 20.2),
                       (-42.2, 20.8), (-40.6, 22.2), (-39.0, 23.3), (-39.0, 25.5), (-40.6, 25.6), (-42.4, 24.2), (-44.4, 22.4),
                       (-46.4, 22.9), (-49.3, 23.1), (-50.6, 22.1), (-52.8, 21.95), (-55.8, 21.9)]]
PATH_LAND = [RAMP_B, V((-43.8, 21.3)), V((-39.9, 24.3))]
BRIDGE_X0, BRIDGE_X1, BRIDGE_Z, BRIDGE_W = -39.0, -33.8, 24.4, 2.2
H = H_HI


def hill_h(p):
    p = V(p)
    if inside(p, HILL_HI):
        return H_HI
    if inside(p, HILL_LO):
        return H_LO
    return H_MID


HEAP = V((-55.0, 30.0))
FALL_PTS = {
    'z_hero_start': (-57.3, 30.9), 'z_kid_pile': (-53.4, 29.4), 'z_fall_gap': (-53.55, 23.35), 'z_ladder': (-51.3, 23.75),
    'z_fall_bolt': (-43.8, 21.3), 'kid_wait_below': (-44.75, 20.25), 'kid_cleft_exit': (-53.5, 20.9),
    'fall_pile': (-55.0, 30.0), 'light_beam': (-55.0, 30.0), 'ladder': (-51.3, 23.75), 'bolt_fall': (-43.8, 21.3),
    'look_book': (-57.9, 28.4), 'look_umbrella': (-53.6, 33.3), 'look_clock': (-58.7, 32.9), 'pz_ladder': (-51.3, 23.75),
}
FALL_FACING = {'look_book': 40, 'look_umbrella': 200, 'look_clock': 120, 'kinopio': 250, 'bolt_fall': 57, 'hero': 100}
# items that fell with the hero: around the heap, a few rolled toward the ladder edge (a trail that leads the eye)
FALL_JUNK = [('Junk_Book', -56.6, 28.9, 15, 1.2), ('Junk_Shoe', -54.2, 31.9, 140, 1.2), ('Junk_Teacup', -56.3, 32.3, 60, 1.2),
             ('Junk_Lantern', -53.9, 27.8, 200, 1.1), ('Junk_Book', -52.4, 28.1, 75, 1.15), ('Junk_Shoe', -52.0, 27.3, 300, 1.15),
             ('Junk_Teacup', -51.8, 25.3, 20, 1.1), ('Junk_Book', -59.6, 31.0, 280, 1.1), ('Junk_Clock', -56.0, 34.6, 30, 1.0),
             ('Junk_Umbrella', -59.3, 27.0, 120, 1.0), ('Junk_Book', -53.0, 35.0, 160, 1.0), ('Junk_Lantern', -57.8, 35.4, 0, 1.0),
             ('Junk_Book', -60.2, 29.6, 310, 1.1), ('Junk_Shoe', -59.9, 33.6, 80, 1.1)]

GATE_PTS = {
    'z_gate_stone': (-28.8, 28.3), 'gate_stone': (-28.8, 28.3), 'ins_gate': (-28.8, 28.3),
    'z_chief_gate': (-23.4, 27.0), 'chief': (-23.4, 27.0),
    'gate_a': (-32.3, 21.7), 'gate_b': (-25.9, 21.5), 'crowd_gate': (-31.8, 27.9),
    'kid_greet': (-25.9, 24.0),
}
GATE_FACING = {'gate_stone': 235, 'chief': 250, 'gate_a': 20, 'gate_b': 340, 'crowd_gate': 160}
WALK_G = [V(p) for p in [(-33.8, 21.0), (-31.2, 20.45), (-29.2, 20.5), (-28.85, 18.45), (-27.15, 18.45), (-26.8, 20.4),
                         (-24.0, 20.7), (-21.7, 21.4), (-19.3, 22.6), (-19.3, 26.6), (-21.8, 28.3), (-24.2, 29.15),
                         (-27.0, 29.6), (-30.0, 29.7), (-33.0, 29.5), (-33.8, 28.0)]]
PLAT = [V(p) for p in [(-34.0, 16.8), (-29.6, 16.9), (-28.9, 18.4), (-27.1, 18.4), (-26.4, 16.9), (-21.0, 17.3), (-18.6, 19.4),
                       (-18.4, 22.6), (-18.4, 26.6), (-18.0, 30.5), (-20.6, 33.6), (-27.0, 34.4), (-33.6, 33.9), (-34.2, 29.2),
                       (-33.8, 28.0), (-33.8, 25.6), (-33.8, 23.2), (-33.8, 21.0)]]
# gate rocks: (center, rx, rz, height, tiers, seed, rot)
# the pass = two walls of tiered stone ledges (long, low near the bridge, rising toward the gate), not loose stumps
GATE_ROCKS = [((-32.7, 30.9), 1.9, 1.05, 1.3, 2, 11, 0.05), ((-24.4, 30.6), 2.2, 1.1, 2.9, 2, 13, -0.12),
              ((-21.0, 29.7), 1.35, 1.3, 6.4, 3, 14, 0.0),          # north gate pillar
              ((-32.4, 19.4), 1.6, 0.85, 0.9, 1, 15, 0.1), ((-30.4, 19.2), 1.0, 0.7, 1.3, 2, 16, 0.0),
              ((-25.1, 19.4), 1.7, 0.85, 1.9, 2, 17, -0.05), ((-22.6, 19.8), 1.4, 0.85, 2.6, 2, 18, 0.15),
              ((-20.6, 20.4), 1.15, 1.1, 5.0, 3, 19, 0.0)]           # south gate pillar
SEAT_STONES = [((-31.0, 21.1), 0.55, 0.42, 0.42, 21), ((-24.7, 21.25), 0.5, 0.4, 0.38, 22), ((-30.4, 29.0), 0.6, 0.45, 0.45, 23),
               ((-26.4, 28.9), 0.45, 0.4, 0.35, 24)]
CART_STAIR = (V((-28.0, 18.45)), V((0.0, -1.0)), 1.7, 7, 0.32, 0.55)   # top centre, direction, width, steps, rise, run

# camera (Unity FollowCamera: rot = Euler(pitch, yaw, 0); look = pivot + (0, 0.6, 0); pivot clamped to bounds shrunk by 4 m)
CAM_FALL = {'yaw': 100, 'pitch': 22, 'distance': 12.0, 'fov': 34}
CAM_GATE = {'yaw': 96, 'pitch': 24, 'distance': 12.0, 'fov': 34}
PIVOT_FALL = (-59.0, -46.0, 21.0, 34.4)      # xmin, xmax, zmin, zmax of the camera pivot (= player) range
PIVOT_GATE = (-36.0, -23.2, 23.4, 26.2)


def _bounds(piv):
    return [piv[0] - 4.0, piv[1] + 4.0, piv[2] - 4.0, piv[3] + 4.0]


AREA_FALL = {
    'id': 'a_fall', 'name': '빛구멍 언덕', 'places': ['fall'],
    'shape': [{'c': [-55.6, 30.0], 'r': 6.6}, {'line': [[-50.7, 23.1], [-47.26, 18.19], [-43.8, 21.3], [-39.9, 24.3]], 'w': 2.0},
              {'line': [[-55.2, 20.8], [-48.5, 19.6]], 'w': 1.3}],
    'bounds': _bounds(PIVOT_FALL), 'camera': CAM_FALL,
    'exits': [{'to': 'a_gate', 'pos': [-39.9, 24.3], 'radius': 1.0, 'spawn': [-35.9, 24.4], 'face': 90, 'label': '사다리 아래로',
               'note': 'pos = 이 구역의 출구(빗장 너머 다리 머리), spawn = 목적 구역에서 서는 자리'}],
}
AREA_GATE = {
    'id': 'a_gate', 'name': '앉은돌 길목', 'places': ['gate'],
    'shape': [{'line': [[-38.4, 24.4], [-33.6, 24.4]], 'w': 1.6}, {'c': [-28.0, 25.0], 'r': 5.0},
              {'line': [[-24.5, 24.8], [-20.3, 24.6]], 'w': 2.2}, {'line': [[-28.0, 21.0], [-28.0, 19.1]], 'w': 1.3}],
    'bounds': _bounds(PIVOT_GATE), 'camera': CAM_GATE,
    'exits': [{'to': 'a_fall', 'pos': [-38.3, 24.4], 'radius': 0.8, 'spawn': [-51.8, 26.9], 'face': 280, 'label': '언덕으로',
               'note': 'pos = 다리 서쪽 끝, spawn = 언덕 위 사다리 머리'},
              {'to': 'a_plaza', 'pos': [-20.3, 24.6], 'radius': 1.5, 'spawn': [-13.5, 11.5], 'face': 100, 'label': '광장 쪽',
               'note': 'pos = 문 기둥 사이 길 끝(내리막 계단 머리)'},
              {'to': 'a_cart', 'pos': [-28.0, 19.15], 'radius': 1.3, 'spawn': [-36.0, 4.5], 'face': 150, 'label': '수레 길',
               'note': 'pos = 남쪽 바위 틈 내리막 계단 머리'}],
}
EXITS_INTO = {('a_plaza', 'a_gate'): {'spawn': [-23.2, 23.5], 'face': 270}, ('a_cart', 'a_gate'): {'spawn': [-28.0, 21.6], 'face': 0}}
PLACE_CENTERS = {'fall': ([-55.5, 30.0], 7), 'gate': ([-28.0, 25.0], 7)}

# footprint: other areas' colliders / walk inside these boxes are dropped (only one page shows at a time, but colliders stay)
FOOTPRINT = [(-68.0, -33.4, 15.6, 40.5), (-34.4, -17.8, 16.2, 35.0)]


def in_footprint(p):
    return any(b[0] <= p[0] <= b[1] and b[2] <= p[1] <= b[3] for b in FOOTPRINT)


# --------------------------------------------------------------------------------------------- 2d helpers
def ccw(poly):
    a = sum(poly[i].x * poly[(i + 1) % len(poly)].y - poly[(i + 1) % len(poly)].x * poly[i].y for i in range(len(poly)))
    return poly if a > 0 else list(reversed(poly))


def inside(p, poly):
    x, y = p[0], p[1]
    c = False
    n = len(poly)
    for i in range(n):
        a, b = poly[i], poly[(i + 1) % n]
        if (a.y > y) != (b.y > y):
            xi = a.x + (y - a.y) * (b.x - a.x) / (b.y - a.y)
            if x < xi:
                c = not c
    return c


def poly_dist(p, poly):
    p = V(p)
    return min(LV.seg_dist(p, poly[i], poly[(i + 1) % len(poly)])[0] for i in range(len(poly)))


def jag(poly, step, amp, seed, closed=True):
    """subdivide edges and push points sideways a little (hand-drawn broken edge)."""
    rnd = random.Random(seed)
    out = []
    n = len(poly)
    for i in range(n if closed else n - 1):
        a, b = poly[i], poly[(i + 1) % n]
        out.append(a)
        k = max(1, int((b - a).length / step))
        d = (b - a)
        nr = V((d.y, -d.x)).normalized() if d.length > 1e-6 else V((0, 0))
        for j in range(1, k):
            out.append(a + d * (j / k) + nr * rnd.uniform(-amp, amp))
    if not closed:
        out.append(poly[-1])
    return out


def jag_poly(c, rx, rz, n, seed, rot=0.0, lo=0.7, hi=1.15):
    rnd = random.Random(seed)
    out = []
    for i in range(n):
        th = 2 * math.pi * i / n + rnd.uniform(-0.18, 0.18)
        k = rnd.uniform(lo, hi)
        x, z = math.cos(th) * rx * k, math.sin(th) * rz * k
        cs, sn = math.cos(rot), math.sin(rot)
        out.append(V(c) + V((x * cs - z * sn, x * sn + z * cs)))
    return out


def B(x, z, y):
    return LV.B(x, z, y)


# --------------------------------------------------------------------------------------------- mesh helpers
def add_face(bm, verts, want=None):
    try:
        f = bm.faces.new(verts)
    except ValueError:
        return None
    f.normal_update()
    if want is not None and f.normal.dot(want) < 0:
        f.normal_flip()
    return f


def fill(bm, poly, y, holes=(), steiner=None, uv=True, up=True):
    """flat polygon at height y (Unity xz poly), optional holes; triangulated with CDT."""
    pts = list(poly)
    edges = []
    n0 = 0
    rings = [list(poly)] + [list(h) for h in holes]
    allp = []
    for r in rings:
        m = len(r)
        for i in range(m):
            edges.append((n0 + i, n0 + (i + 1) % m))
        allp += r
        n0 += m
    extra = []
    if steiner:
        extra = [q for q in steiner if inside(q, poly) and not any(inside(q, h) for h in holes) and poly_dist(q, poly) > 0.3]
    co = [(p.x, p.y) for p in allp + extra]
    res = delaunay_2d_cdt(co, edges, [], 0, 1e-5)
    vout, eout, fout = res[0], res[1], res[2]
    vm = {}

    def gv(i):
        if i not in vm:
            vm[i] = bm.verts.new(B(vout[i][0], vout[i][1], y if not callable(y) else y(V(vout[i]))))
        return vm[i]
    uvl = bm.loops.layers.uv.active or (bm.loops.layers.uv.new('UVMap') if uv else None)
    for f in fout:
        c = V((sum(vout[i][0] for i in f) / 3, sum(vout[i][1] for i in f) / 3))
        if not inside(c, poly) or any(inside(c, h) for h in holes):
            continue
        face = add_face(bm, [gv(i) for i in f], V((0, 0, 1 if up else -1)))
        if face and uvl:
            for lp in face.loops:
                lp[uvl].uv = (lp.vert.co.x / 8.0, lp.vert.co.y / 8.0)
    return bm


def grid_pts(poly, step, seed):
    rnd = random.Random(seed)
    xs = [p.x for p in poly]
    zs = [p.y for p in poly]
    out = []
    x = min(xs)
    while x < max(xs):
        z = min(zs)
        while z < max(zs):
            out.append(V((x + rnd.uniform(-0.3, 0.3) * step, z + rnd.uniform(-0.3, 0.3) * step)))
            z += step
        x += step
    return out


def stroke3(bm, pts, w):
    LV.rib_vertical(bm, pts, w)


def wall_stroke(bm, a, b, w, nrm2):
    """single quad lying in a wall plane (hatch on a face of known outward normal) - half the cost of rib_vertical."""
    nb = V((-nrm2.x, -nrm2.y, 0.0))
    d = (b - a)
    if d.length < 1e-6:
        return
    side = d.cross(nb)
    if side.length < 1e-6:
        return
    side = side.normalized() * (w * 0.5)
    f = bm.faces.new([bm.verts.new(a - side), bm.verts.new(b - side), bm.verts.new(b + side), bm.verts.new(a + side)])
    f.normal_update()
    if f.normal.dot(nb) < 0:
        f.normal_flip()


def ground_stroke(bm, pts2, y, w, lift=0.03):
    LV.ribbon(bm, [B(p.x, p.y, (y(p) if callable(y) else y) + lift) for p in pts2], w)


SUN_FROM = V((0.33, -0.47)).normalized()     # Unity sun Euler(55,-35,0): light comes from the south-east; west/north faces are in shade


def shaded(nrm2):
    return nrm2.dot(SUN_FROM) < 0.08


def hatch_face(hatch, p0, p1, ytop0, ytop1, ybot, nrm2, rnd, density=1.0, band=1.4, w=0.034):
    """bold diagonal hand hatching on a shaded vertical face strip p0->p1 (Unity xz), clustered under the top edge:
    parallel strokes ~50 deg, a few longer ones that run down the face."""
    e = p1 - p0
    ln = e.length
    if ln < 0.15:
        return
    d = e / ln
    off = V((-nrm2.x, -nrm2.y, 0)) * 0.03
    step = 0.16 / max(density, 0.05)
    t = rnd.uniform(0, step)
    while t < ln:
        if rnd.random() < 0.85:
            p = p0 + d * t
            yt = ytop0 + (ytop1 - ytop0) * (t / ln)
            L_ = band * rnd.uniform(0.35, 1.0) * (2.2 if rnd.random() < 0.12 else 1.0)
            y0 = yt - rnd.uniform(0.04, 0.18)
            y1 = max(ybot + 0.05, y0 - L_)
            q = p + d * (y0 - y1) * 0.62
            wall_stroke(hatch, B(p.x, p.y, y0) + off, B(q.x, q.y, y1) + off, w * rnd.uniform(0.8, 1.2), nrm2)
        t += step * rnd.uniform(0.7, 1.3)


def walls(solid, ink, hatch, poly, ytop, ybot, seed, ledge=1.3, ledge_out=0.32, skip=None, hatch_floor=None, rim=True,
          vstroke=0.5, hatch_density=1.0, unf=None, sketch=None, torn=None, deep=None, deep_y=0.0):
    """vertical paper cliff around a CCW polygon: top face edge at ytop(i), one stepped ledge, down to ybot.
    Ink rim on the top edge and the ledge, vertical strokes, bold diagonal hatch on shaded faces. Below deep_y the
    face goes into the 'deep' bucket (dark: chasm). unf(a, b): the drawing stops at a torn line, below = blank paper."""
    rnd = random.Random(seed)
    poly = ccw(poly)
    n = len(poly)
    yt = [ytop(i) if callable(ytop) else ytop for i in range(n)]
    nrm = []
    for i in range(n):
        a, b, c = poly[i - 1], poly[i], poly[(i + 1) % n]
        e1, e2 = (b - a), (c - b)
        n1 = V((e1.y, -e1.x)).normalized()
        n2 = V((e2.y, -e2.x)).normalized()
        m = (n1 + n2)
        m = m.normalized() if m.length > 1e-6 else n1
        nrm.append(m)
    hf = ybot if hatch_floor is None else hatch_floor
    for i in range(n):
        j = (i + 1) % n
        a, b = poly[i], poly[j]
        if skip and skip(a, b):
            continue
        e = b - a
        if e.length < 1e-4:
            continue
        en = V((e.y, -e.x)).normalized()
        want = V((-en.x, -en.y, 0))     # Blender: outward of Unity normal (x,z) -> (-x,-z)
        off = V((-en.x, -en.y, 0)) * 0.025
        yl_i = yt[i] - ledge - 0.15 * math.sin(i * 1.7 + seed)
        yl_j = yt[j] - ledge - 0.15 * math.sin(j * 1.7 + seed)
        if unf and unf(a, b):
            k_ = 3
            pts_top = [a.lerp(b, t / k_) for t in range(k_ + 1)]
            ytt = [yt[i] + (yt[j] - yt[i]) * t / k_ for t in range(k_ + 1)]
            ybt = [y - ledge * rnd.uniform(0.45, 1.2) for y in ytt]
            for t in range(k_):
                q = [solid.verts.new(B(pts_top[t].x, pts_top[t].y, ytt[t])), solid.verts.new(B(pts_top[t + 1].x, pts_top[t + 1].y, ytt[t + 1])),
                     solid.verts.new(B(pts_top[t + 1].x, pts_top[t + 1].y, ybt[t + 1])), solid.verts.new(B(pts_top[t].x, pts_top[t].y, ybt[t]))]
                add_face(solid, q, want)
                if shaded(en) and hatch is not None:
                    hatch_face(hatch, pts_top[t], pts_top[t + 1], ytt[t], ytt[t + 1], min(ybt[t], ybt[t + 1]), en, rnd, hatch_density, ledge * 0.6)
            if rim:
                stroke3(ink, [B(pts_top[0].x, pts_top[0].y, ytt[0] + 0.02) + off, B(pts_top[-1].x, pts_top[-1].y, ytt[-1] + 0.02) + off], 0.11)
            stroke3(ink, [B(pts_top[t].x, pts_top[t].y, ybt[t]) + off for t in range(k_ + 1)], 0.035)
            if torn is not None:
                for t in range(k_):
                    p0, p1 = pts_top[t], pts_top[t + 1]
                    q = [torn.verts.new(B(p0.x, p0.y, ybt[t])), torn.verts.new(B(p1.x, p1.y, ybt[t + 1])),
                         torn.verts.new(B(p1.x, p1.y, max(ybot, hf - 0.4))), torn.verts.new(B(p0.x, p0.y, max(ybot, hf - 0.4)))]
                    add_face(torn, q, want)
            sk = sketch if sketch is not None else ink
            yb = max(hf, ybot)
            for t in range(k_ + 1):
                if rnd.random() < 0.75:
                    stroke3(sk, [B(pts_top[t].x, pts_top[t].y, ybt[t] + 0.1) + off * 1.3, B(pts_top[t].x, pts_top[t].y, yb + rnd.uniform(-0.3, 1.0)) + off * 1.3], 0.04)
            for yy in (yl_i - 0.3, (yl_i + yb) / 2):
                if yy > yb + 0.2:
                    stroke3(sk, [B(a.x, a.y, yy) + off * 1.3, B(b.x, b.y, yy + rnd.uniform(-0.1, 0.1)) + off * 1.3], 0.035)
            continue
        oi, oj = a + nrm[i] * ledge_out, b + nrm[j] * ledge_out
        t_i, t_j = solid.verts.new(B(a.x, a.y, yt[i])), solid.verts.new(B(b.x, b.y, yt[j]))
        l_i, l_j = solid.verts.new(B(a.x, a.y, yl_i)), solid.verts.new(B(b.x, b.y, yl_j))
        lo_i, lo_j = solid.verts.new(B(oi.x, oi.y, yl_i)), solid.verts.new(B(oj.x, oj.y, yl_j))
        add_face(solid, [t_i, t_j, l_j, l_i], want)
        add_face(solid, [l_i, l_j, lo_j, lo_i], V((0, 0, 1)))
        if deep is not None and ybot < deep_y < min(yl_i, yl_j):
            m_i, m_j = solid.verts.new(B(oi.x, oi.y, deep_y)), solid.verts.new(B(oj.x, oj.y, deep_y))
            add_face(solid, [lo_i, lo_j, m_j, m_i], want)
            d_i, d_j = deep.verts.new(B(oi.x, oi.y, deep_y)), deep.verts.new(B(oj.x, oj.y, deep_y))
            b_i, b_j = deep.verts.new(B(oi.x, oi.y, ybot)), deep.verts.new(B(oj.x, oj.y, ybot))
            add_face(deep, [d_i, d_j, b_j, b_i], want)
        else:
            b_i, b_j = solid.verts.new(B(oi.x, oi.y, ybot)), solid.verts.new(B(oj.x, oj.y, ybot))
            add_face(solid, [lo_i, lo_j, b_j, b_i], want)
        if rim:
            stroke3(ink, [t_i.co + off + V((0, 0, 0.02)), t_j.co + off + V((0, 0, 0.02))], 0.11)
            stroke3(ink, [lo_i.co + off + V((0, 0, 0.02)), lo_j.co + off + V((0, 0, 0.02))], 0.065)
        if rnd.random() < vstroke:
            yb = max(hf, ybot) + rnd.uniform(0.0, 0.8)
            stroke3(ink, [lo_i.co + off, V((lo_i.co.x, lo_i.co.y, yb)) + off], 0.05)
            stroke3(ink, [t_i.co + off, l_i.co + off + V((0, 0, rnd.uniform(0, 0.3)))], 0.045)
        if shaded(en) and hatch is not None and hatch_density > 0:
            hatch_face(hatch, a, b, yt[i], yt[j], min(yl_i, yl_j), en, rnd, hatch_density, ledge * 0.9)
            hatch_face(hatch, oi, oj, yl_i - 0.05, yl_j - 0.05, max(hf, ybot), en, rnd, hatch_density * 0.7, 1.6)


def rock(solid, ink, hatch, poly, y0, h, tiers, seed, top_ink=True):
    """stacked angular slabs (concept ledges, developed): tilted paper tops, slightly tapering sides, offset tiers,
    ink rims, a crack on the near face, bold hatch on shaded faces."""
    rnd = random.Random(seed)
    cur = ccw(poly)
    cx = sum(p.x for p in cur) / len(cur)
    cz = sum(p.y for p in cur) / len(cur)
    zb = y0 - 0.3
    for t in range(tiers):
        z1 = y0 + h * (t + 1) / tiers + (rnd.uniform(-0.12, 0.12) if t < tiers - 1 else 0)
        n = len(cur)
        ta = rnd.uniform(0, 2 * math.pi)
        tilt = V((math.cos(ta), math.sin(ta))) * rnd.uniform(0.08, 0.22) * min(1.0, h / tiers)
        tc = V((sum(p.x for p in cur) / n, sum(p.y for p in cur) / n))
        topp = [tc + (p - tc) * rnd.uniform(0.86, 0.95) for p in cur]
        tz = [z1 + (p - tc).dot(tilt) + rnd.uniform(-0.04, 0.04) for p in cur]
        bot = [solid.verts.new(B(p.x, p.y, zb)) for p in cur]
        top = [solid.verts.new(B(p.x, p.y, z)) for p, z in zip(topp, tz)]
        for i in range(n):
            j = (i + 1) % n
            e = cur[j] - cur[i]
            en = V((e.y, -e.x)).normalized() if e.length > 1e-6 else V((1, 0))
            add_face(solid, [bot[i], bot[j], top[j], top[i]], V((-en.x, -en.y, 0)))
        add_face(solid, top, V((0, 0, 1)))
        if top_ink:
            stroke3(ink, [v.co + V((0, 0, 0.02)) for v in top] + [top[0].co + V((0, 0, 0.02))], 0.09)
        best = None
        for i in range(n):
            j = (i + 1) % n
            e = cur[j] - cur[i]
            if e.length < 0.15:
                continue
            en = V((e.y, -e.x)).normalized()
            off = V((-en.x, -en.y, 0)) * 0.02
            if rnd.random() < 0.22:
                stroke3(ink, [top[i].co + off, bot[i].co + V((0, 0, max(0.3, y0 - zb) + 0.02)) + off], 0.04)
            if shaded(en) and hatch is not None:
                hatch_face(hatch, topp[i], topp[j], tz[i], tz[j], max(y0, zb), en, rnd, 1.0, (z1 - max(y0, zb)) * 0.75)
            if en.x < -0.4 and (best is None or e.length > best[0]):
                best = (e.length, i, j, en)
        if best and rnd.random() < 0.8:
            _, i, j, en = best
            off = V((-en.x, -en.y, 0)) * 0.03
            p = topp[i].lerp(topp[j], rnd.uniform(0.3, 0.7))
            ztop = tz[i] + (tz[j] - tz[i]) * 0.5
            pts = [B(p.x, p.y, ztop) + off]
            q = V(p)
            zz = ztop
            d = (topp[j] - topp[i]).normalized()
            for kk in range(3):
                zz -= (z1 - max(y0, zb)) * rnd.uniform(0.15, 0.3)
                q = q + d * rnd.uniform(-0.18, 0.18)
                pts.append(B(q.x, q.y, zz) + off)
            stroke3(ink, pts, 0.04)
        sx, sz = cx + rnd.uniform(-0.35, 0.35), cz + rnd.uniform(-0.35, 0.35)
        k = rnd.uniform(0.58, 0.76)
        rot = rnd.uniform(-0.25, 0.25)
        cs, sn = math.cos(rot), math.sin(rot)
        cur = [V((sx + ((p.x - cx) * cs - (p.y - cz) * sn) * k, sz + ((p.x - cx) * sn + (p.y - cz) * cs) * k)) for p in cur]
        zb = min(tz) - 0.05


def box(bm, c, size, y0, yaw=0.0, want_up=True):
    """axis box in Unity coords: c=(x,z), size=(sx, sy, sz) along local x, y(up), z; rotated by yaw deg."""
    sx, sy, sz = size
    cs, sn = math.cos(math.radians(yaw)), math.sin(math.radians(yaw))

    def W(lx, lz):
        # Unity yaw: local x -> (cos, -sin), local z -> (sin, cos)
        return V((c[0] + lx * cs + lz * sn, c[1] - lx * sn + lz * cs))
    corners = [W(-sx / 2, -sz / 2), W(sx / 2, -sz / 2), W(sx / 2, sz / 2), W(-sx / 2, sz / 2)]
    corners = ccw(corners)
    bot = [bm.verts.new(B(p.x, p.y, y0)) for p in corners]
    top = [bm.verts.new(B(p.x, p.y, y0 + sy)) for p in corners]
    for i in range(4):
        j = (i + 1) % 4
        e = corners[j] - corners[i]
        en = V((e.y, -e.x)).normalized()
        add_face(bm, [bot[i], bot[j], top[j], top[i]], V((-en.x, -en.y, 0)))
    add_face(bm, top, V((0, 0, 1)))
    add_face(bm, bot, V((0, 0, -1)))
    return corners, top


def hex_lines(bm, poly, y, R, seed, keep=0.75, origin=(0.0, 0.0), w=0.045, rot=0.0, avoid=None):
    """drawn hex paving (pointy) clipped to poly; edges randomly left out (unfinished)."""
    rnd = random.Random(seed)
    xs = [p.x for p in poly]
    zs = [p.y for p in poly]
    dx = math.sqrt(3) * R
    dz = 1.5 * R
    cs, sn = math.cos(rot), math.sin(rot)
    seen = set()
    j = int((min(zs) - origin[1]) / dz) - 2
    while origin[1] + j * dz < max(zs) + 2:
        i = int((min(xs) - origin[0]) / dx) - 2
        while origin[0] + i * dx < max(xs) + 2:
            cx = origin[0] + i * dx + (dx / 2 if j % 2 else 0)
            cz = origin[1] + j * dz
            for k in range(6):
                a0 = math.radians(60 * k + 30)
                a1 = math.radians(60 * k + 90)
                p0 = V((cx + R * math.cos(a0), cz + R * math.sin(a0)))
                p1 = V((cx + R * math.cos(a1), cz + R * math.sin(a1)))
                key = tuple(sorted(((round(p0.x, 2), round(p0.y, 2)), (round(p1.x, 2), round(p1.y, 2)))))
                if key in seen:
                    continue
                seen.add(key)
                if not (inside(p0, poly) and inside(p1, poly)):
                    continue
                if poly_dist((p0 + p1) / 2, poly) < 0.25:
                    continue
                if avoid and avoid((p0 + p1) / 2):
                    continue
                if callable(y) and abs(y(p0) - y(p1)) > 0.01:
                    continue
                if rnd.random() > keep:
                    continue
                s = rnd.uniform(0.0, 0.12)
                a = p0.lerp(p1, s)
                b = p1.lerp(p0, rnd.uniform(0.0, 0.12))
                ground_stroke(bm, [a, b], y, w * rnd.uniform(0.8, 1.2))
            i += 1
        j += 1


def cracks(bm, poly, y, n, seed, avoid=None):
    rnd = random.Random(seed)
    xs = [p.x for p in poly]
    zs = [p.y for p in poly]
    for _ in range(n * 4):
        if n <= 0:
            break
        p = V((rnd.uniform(min(xs), max(xs)), rnd.uniform(min(zs), max(zs))))
        if not inside(p, poly) or poly_dist(p, poly) < 0.4 or (avoid and avoid(p)):
            continue
        pts = [p]
        ang = rnd.uniform(0, 2 * math.pi)
        for k in range(rnd.randint(2, 4)):
            ang += rnd.uniform(-0.7, 0.7)
            q = pts[-1] + V((math.cos(ang), math.sin(ang))) * rnd.uniform(0.3, 0.8)
            if not inside(q, poly) or (callable(y) and abs(y(q) - y(pts[-1])) > 0.01) or (avoid and avoid(q)):
                break
            pts.append(q)
        if len(pts) > 1:
            ground_stroke(bm, pts, y, 0.04)
        n -= 1


def pennant(solid, paint, ink, base, y, h=2.4, d=(1, 0)):
    """small post with a painted pennant: the 'way onward' is the only coloured thing on the edge."""
    stroke3(ink, [B(base.x, base.y, y - 0.1), B(base.x, base.y, y + h)], 0.07)
    top = B(base.x, base.y, y + h)
    dd = V(d).normalized()
    tri = [top, top - V((0, 0, 0.55)), B(base.x + dd.x * 0.85, base.y + dd.y * 0.85, y + h - 0.22)]
    paint.faces.new([paint.verts.new(v) for v in tri])
    paint.faces.new([paint.verts.new(v) for v in reversed(tri)])


def arrow(ink, p, d, y, size=1.0):
    d = V(d).normalized()
    n = V((-d.y, d.x))
    c = V(p)
    ground_stroke(ink, [c - d * 1.3 * size, c - d * 0.3 * size + n * 0.04, c + d * 0.35 * size], y, 0.15 * size)
    ground_stroke(ink, [c + d * 0.6 * size, c - d * 0.05 * size + n * 0.55 * size], y, 0.14 * size, 0.035)
    ground_stroke(ink, [c + d * 0.6 * size, c - d * 0.05 * size - n * 0.55 * size], y, 0.14 * size, 0.035)


# --------------------------------------------------------------------------------------------- unfinished-form helpers
def clip_x(poly, cut):
    """Sutherland-Hodgman: keep the part of poly with x <= cut."""
    out = []
    n = len(poly)
    for i in range(n):
        a, b = poly[i], poly[(i + 1) % n]
        ain, bin_ = a.x <= cut, b.x <= cut
        if ain:
            out.append(a)
        if ain != bin_:
            t = (cut - a.x) / (b.x - a.x)
            out.append(a.lerp(b, t))
    return out


def wire_loop(bm, poly, y, w=0.06, gap=0.0, seed=0):
    rnd = random.Random(seed)
    pts = [B(p.x, p.y, y) for p in poly] + [B(poly[0].x, poly[0].y, y)]
    if gap <= 0:
        stroke3(bm, pts, w)
        return
    for i in range(len(pts) - 1):
        if rnd.random() > gap:
            a, b = pts[i], pts[i + 1]
            stroke3(bm, [a.lerp(b, rnd.uniform(-0.08, 0.05)), b.lerp(a, rnd.uniform(-0.1, 0.05))], w)


def hexp(c, r, seed, rot=None, sq=1.0):
    """basalt-like hexagonal slab outline (the hex motif of the paving, in stone)."""
    rnd = random.Random(seed)
    rot = rnd.uniform(0, math.pi / 3) if rot is None else rot
    return [V(c) + V((math.cos(rot + math.pi / 3 * i) * r * rnd.uniform(0.85, 1.12), math.sin(rot + math.pi / 3 * i) * r * sq * rnd.uniform(0.85, 1.12))) for i in range(6)]


def cairn(k, c, r, h, y_base, seed, real=True, wire_frac=0.0):
    """stacked hexagonal slabs, each offset and turned a little; the top wire_frac only drawn (ink rings + plumb)."""
    rnd = random.Random(seed)
    y = y_base
    cc = V(c)
    rr = r
    solid_top = y_base + h * (1 - wire_frac)
    i = 0
    while y < solid_top - 0.25:
        t = min(rnd.uniform(0.6, 1.25) * (1.0 + max(0.0, (solid_top - 4.0 - y) / 2.0)), solid_top - y)
        deep_slab = y + t < -3.0          # down in the dark: plain slabs, no ink / hatch (unseen, saves triangles)
        rock(k.solid, k.ink, (k.hatch if real else None) if not deep_slab else None, hexp(cc, rr, seed * 7 + i), y, t, 1, seed * 13 + i,
             top_ink=not deep_slab)
        y += t
        cc = cc + V((rnd.uniform(-0.16, 0.16), rnd.uniform(-0.16, 0.16)))
        rr *= rnd.uniform(0.86, 0.97)
        i += 1
    if wire_frac > 0:
        wire_tiers(k, hexp(cc, rr * 0.95, seed + 99), y, y_base + h, 3, seed)
    return y, cc


def rock_wire(k, poly, y0, h, tiers, seed, wire=0.45, hatch=True):
    """rock whose far (east) side is only a drawn contour: solid west part, ink outline + hatch for the rest."""
    rnd = random.Random(seed)
    cur = ccw(poly)
    cx = sum(p.x for p in cur) / len(cur)
    cz = sum(p.y for p in cur) / len(cur)
    zb = y0 - 0.3
    for t in range(tiers):
        z1 = y0 + h * (t + 1) / tiers + (rnd.uniform(-0.12, 0.12) if t < tiers - 1 else 0)
        xs = [p.x for p in cur]
        cut = min(xs) + (max(xs) - min(xs)) * (1.0 - wire * (0.7 + 0.3 * t / max(1, tiers - 1)))
        sp = ccw(clip_x(cur, cut))
        if len(sp) >= 3:
            rock(k.solid, k.ink, k.hatch if hatch else None, sp, zb + 0.3 if t == 0 else zb, z1 - (zb + 0.3 if t == 0 else zb), 1, seed + t, top_ink=False)
        # full contour of this tier in ink (the 'drawn' rest), broken a little
        wire_loop(k.ink, cur, z1 + 0.02, 0.07, gap=0.12, seed=seed + 10 * t)
        for p in cur:
            if p.x > cut + 0.05:
                stroke3(k.ink, [B(p.x, p.y, z1), B(p.x, p.y, max(y0, zb) + rnd.uniform(0.0, 0.4))], 0.045)
        # hatched contour on the wire side: strokes hanging from the drawn top edge
        n = len(cur)
        for i in range(n):
            a, b = cur[i], cur[(i + 1) % n]
            if a.x < cut and b.x < cut:
                continue
            e = b - a
            cnt = int(e.length / 0.22)
            for kk in range(cnt):
                p = a.lerp(b, (kk + 0.5) / max(cnt, 1))
                if p.x < cut:
                    continue
                stroke3(k.hatch, [B(p.x, p.y, z1 - 0.05), B(p.x + 0.12, p.y + 0.1, z1 - (z1 - max(y0, zb)) * rnd.uniform(0.3, 0.7))], 0.03)
        sx, sz = cx + rnd.uniform(-0.3, 0.3), cz + rnd.uniform(-0.3, 0.3)
        kk = rnd.uniform(0.6, 0.78)
        cur = [V((sx + (p.x - cx) * kk + rnd.uniform(-0.1, 0.1), sz + (p.y - cz) * kk + rnd.uniform(-0.1, 0.1))) for p in cur]
        zb = z1 - 0.05


def wire_tiers(k, poly, y0, y1, n, seed):
    """a structure that continues upward only as drawn tiers (ink rings + pencil verticals)."""
    rnd = random.Random(seed)
    cur = list(poly)
    cx = sum(p.x for p in cur) / len(cur)
    cz = sum(p.y for p in cur) / len(cur)
    for t in range(n):
        y = y0 + (y1 - y0) * (t + 1) / n
        kk = 0.92 - 0.08 * t
        cur = [V((cx + (p.x - cx) * kk, cz + (p.y - cz) * kk)) for p in cur]
        wire_loop(k.ink if t == 0 else k.sketch, cur, y, 0.06 if t == 0 else 0.05, gap=0.15 + 0.15 * t, seed=seed + t)
        for p in cur[::2]:
            stroke3(k.sketch, [B(p.x, p.y, y - (y1 - y0) / n - 0.1), B(p.x, p.y, y + rnd.uniform(0.0, 0.4))], 0.04)
    # plumb line + level ticks (left-over construction)
    stroke3(k.sketch, [B(cx, cz, y0 - 0.5), B(cx, cz, y1 + 1.2)], 0.03)
    for t in range(6):
        yy = y0 + (y1 - y0) * t / 5
        stroke3(k.sketch, [B(cx - 0.35, cz, yy), B(cx + 0.35, cz, yy)], 0.03)


def unfinished_house(k, c, w, d, h, yaw, y0, seed, roof=1.8):
    """half a house: the camera-facing wall and a stub of the side wall built, the rest only drawn as a box outline
    with a gable roof, construction diagonals and measuring ticks."""
    rnd = random.Random(seed)
    cs, sn = math.cos(math.radians(yaw)), math.sin(math.radians(yaw))

    def W(lx, lz):
        return V((c[0] + lx * cs + lz * sn, c[1] - lx * sn + lz * cs))
    hw, hd = w / 2, d / 2
    P = [W(-hw, -hd), W(hw, -hd), W(hw, hd), W(-hw, hd)]       # local -z = front (yaw 270 -> front faces west/camera)
    # front wall: solid with a ragged top that falls off toward one end; door + window drawn
    nseg = 6
    top = []
    for i in range(nseg + 1):
        t = i / nseg
        yy = y0 + h * (1.0 - 0.55 * max(0.0, t - 0.45) / 0.55) + (rnd.uniform(-0.15, 0.1) if 0 < i < nseg else 0)
        top.append((P[0].lerp(P[1], t), yy))
    for i in range(nseg):
        (a, ya), (b, yb) = top[i], top[i + 1]
        e = b - a
        en = V((e.y, -e.x)).normalized()
        q = [k.solid.verts.new(B(a.x, a.y, y0 - 0.1)), k.solid.verts.new(B(b.x, b.y, y0 - 0.1)), k.solid.verts.new(B(b.x, b.y, yb)), k.solid.verts.new(B(a.x, a.y, ya))]
        add_face(k.solid, q, V((-en.x, -en.y, 0)))
        stroke3(k.ink, [B(a.x, a.y, ya + 0.02), B(b.x, b.y, yb + 0.02)], 0.07)
    # wall thickness on the front: inner face (so it is not a paper sheet)
    off = (P[3] - P[0]).normalized() * 0.25
    for i in range(nseg):
        (a, ya), (b, yb) = top[i], top[i + 1]
        a2, b2 = a + off, b + off
        e = b2 - a2
        en = V((-e.y, e.x)).normalized()
        q = [k.solid.verts.new(B(a2.x, a2.y, y0 - 0.1)), k.solid.verts.new(B(b2.x, b2.y, y0 - 0.1)), k.solid.verts.new(B(b2.x, b2.y, yb)), k.solid.verts.new(B(a2.x, a2.y, ya))]
        add_face(k.solid, q, V((-en.x, -en.y, 0)))
        q = [k.solid.verts.new(B(a.x, a.y, ya)), k.solid.verts.new(B(b.x, b.y, yb)), k.solid.verts.new(B(b2.x, b2.y, yb)), k.solid.verts.new(B(a2.x, a2.y, ya))]
        add_face(k.solid, q, V((0, 0, 1)))
    # side wall stub (left end), low and torn
    a, b = P[0], P[3]
    for i in range(3):
        t0, t1 = i / 3 * 0.55, (i + 1) / 3 * 0.55
        p0, p1 = a.lerp(b, t0), a.lerp(b, t1)
        y_a = y0 + h * (1 - t0 * 1.1) * 0.95
        y_b = y0 + h * (1 - t1 * 1.1) * 0.95 - rnd.uniform(0, 0.3)
        e = p1 - p0
        en = V((-e.y, e.x)).normalized()
        q = [k.solid.verts.new(B(p0.x, p0.y, y0 - 0.1)), k.solid.verts.new(B(p1.x, p1.y, y0 - 0.1)), k.solid.verts.new(B(p1.x, p1.y, y_b)), k.solid.verts.new(B(p0.x, p0.y, y_a))]
        add_face(k.solid, q, V((-en.x, -en.y, 0)))
        stroke3(k.ink, [B(p0.x, p0.y, y_a + 0.02), B(p1.x, p1.y, y_b + 0.02)], 0.06)
    # door (dark) + drawn window on the front
    dc = P[0].lerp(P[1], 0.3)
    u = (P[1] - P[0]).normalized()
    fo = (P[0] - P[3]).normalized() * 0.02
    door = [dc - u * 0.45 + fo, dc + u * 0.45 + fo]
    q = [k.dark.verts.new(B(door[0].x, door[0].y, y0)), k.dark.verts.new(B(door[1].x, door[1].y, y0)),
         k.dark.verts.new(B(door[1].x, door[1].y, y0 + 1.5)), k.dark.verts.new(B(door[0].x, door[0].y, y0 + 1.5))]
    add_face(k.dark, q, V((-fo.x, -fo.y, 0)))
    arch = [B((dc + u * 0.45 * math.cos(math.pi * i / 8) + fo * 2).x, (dc + u * 0.45 * math.cos(math.pi * i / 8) + fo * 2).y, y0 + 1.5 + 0.45 * math.sin(math.pi * i / 8)) for i in range(9)]
    stroke3(k.ink, [B(door[0].x, door[0].y, y0)] + arch[::-1] + [B(door[1].x, door[1].y, y0)], 0.07)
    wc = P[0].lerp(P[1], 0.68) + fo * 2
    win = [wc - u * 0.35, wc + u * 0.35]
    stroke3(k.ink, [B(win[0].x, win[0].y, y0 + 1.4), B(win[1].x, win[1].y, y0 + 1.4), B(win[1].x, win[1].y, y0 + 2.1), B(win[0].x, win[0].y, y0 + 2.1), B(win[0].x, win[0].y, y0 + 1.4)], 0.05)
    stroke3(k.sketch, [B(wc.x, wc.y, y0 + 1.4), B(wc.x, wc.y, y0 + 2.1)], 0.03)
    # the rest of the volume: drawn only (box edges, gable roof, ridge), partly broken
    ytop = y0 + h
    ridge0, ridge1 = (P[0] + P[3]) / 2, (P[1] + P[2]) / 2
    edges = [(P[1], ytop, P[2], ytop), (P[2], ytop, P[3], ytop), (P[3], ytop, P[0], ytop), (P[0], ytop, P[1], ytop),
             (P[1], y0, P[2], y0), (P[2], y0, P[3], y0), (P[1], y0, P[1], ytop), (P[2], y0, P[2], ytop), (P[3], y0, P[3], ytop),
             (P[0], ytop, ridge0, ytop + roof), (P[3], ytop, ridge0, ytop + roof), (P[1], ytop, ridge1, ytop + roof),
             (P[2], ytop, ridge1, ytop + roof), (ridge0, ytop + roof, ridge1, ytop + roof)]
    for i, (a, ya, b, yb) in enumerate(edges):
        bm = k.ink if i < 9 or rnd.random() < 0.5 else k.sketch
        A_, B_ = B(a.x, a.y, ya), B(b.x, b.y, yb)
        if rnd.random() < 0.25:
            stroke3(bm, [A_, A_.lerp(B_, rnd.uniform(0.4, 0.7))], 0.055)
        else:
            stroke3(bm, [A_ + (A_ - B_).normalized() * 0.3, B_ + (B_ - A_).normalized() * 0.3], 0.05)   # overshoot like a sketch
    # construction diagonals on the missing side, measuring ticks along the base, a plumb line at the corner
    stroke3(k.sketch, [B(P[1].x, P[1].y, y0), B(P[2].x, P[2].y, ytop)], 0.03)
    stroke3(k.sketch, [B(P[2].x, P[2].y, y0), B(P[1].x, P[1].y, ytop)], 0.03)
    for i in range(int(w / 0.5) + 1):
        p = P[0].lerp(P[1], i / (w / 0.5)) - (P[3] - P[0]).normalized() * 0.15
        stroke3(k.sketch, [B(p.x, p.y, y0 + 0.02), B(p.x, p.y, y0 + (0.25 if i % 2 == 0 else 0.12))], 0.03)
    stroke3(k.sketch, [B(P[1].x, P[1].y, y0 - 0.3), B(P[1].x, P[1].y, ytop + roof + 0.8)], 0.025)


def torn_hole(k, hole, y, depth, seed):
    """missing chunk: ragged paper edge, a strip of raw paper, a dark inside. (cut the hole out of the fill yourself)"""
    rnd = random.Random(seed)
    hole = ccw(hole)
    n = len(hole)
    cx = sum(p.x for p in hole) / n
    cz = sum(p.y for p in hole) / n
    outer = [V((cx + (p.x - cx) * 1.0, cz + (p.y - cz) * 1.0)) + (p - V((cx, cz))).normalized() * rnd.uniform(0.08, 0.22) for p in hole]
    for i in range(n):
        j = (i + 1) % n
        q = [k.torn.verts.new(B(hole[i].x, hole[i].y, y + 0.006)), k.torn.verts.new(B(hole[j].x, hole[j].y, y + 0.006)),
             k.torn.verts.new(B(outer[j].x, outer[j].y, y + 0.006)), k.torn.verts.new(B(outer[i].x, outer[i].y, y + 0.006))]
        add_face(k.torn, q, V((0, 0, 1)))
        e = hole[j] - hole[i]
        en = V((e.y, -e.x)).normalized()
        q = [k.dark.verts.new(B(hole[i].x, hole[i].y, y)), k.dark.verts.new(B(hole[j].x, hole[j].y, y)),
             k.dark.verts.new(B(hole[j].x, hole[j].y, y - depth)), k.dark.verts.new(B(hole[i].x, hole[i].y, y - depth))]
        add_face(k.dark, q, V((en.x, en.y, 0)))      # facing into the hole
    fill(k.dark, hole, y - depth, uv=False)
    wire_loop(k.ink, outer, y + 0.03, 0.05, gap=0.1, seed=seed)
    wire_loop(k.ink, hole, y + 0.02, 0.035, gap=0.35, seed=seed + 1)


def smudge(k, c, rx, rz, rot, y, seed):
    pts = jag_poly(c, rx, rz, 12, seed, rot, 0.8, 1.1)
    fill(k.smudge, ccw(pts), (lambda p: y(p) + 0.02) if callable(y) else y + 0.02, uv=False)


def guide(k, a, b, y, w=0.028):
    ground_stroke(k.sketch, [V(a), V(b)], y, w, 0.02)


def compass(k, c, r, y, seed, frac=0.8):
    rnd = random.Random(seed)
    a0 = rnd.uniform(0, 2 * math.pi)
    pts = [V(c) + V((math.cos(a0 + 2 * math.pi * frac * i / 40), math.sin(a0 + 2 * math.pi * frac * i / 40))) * r for i in range(41)]
    ground_stroke(k.sketch, pts, y, 0.03, 0.02)
    c = V(c)
    ground_stroke(k.sketch, [c - V((0.35, 0)), c + V((0.35, 0))], y, 0.03, 0.02)
    ground_stroke(k.sketch, [c - V((0, 0.35)), c + V((0, 0.35))], y, 0.03, 0.02)


def ticks_along(k, pts, y, step, seed, side=1.0, bm=None):
    """measuring marks along an edge (every step m; long every 4th)."""
    rnd = random.Random(seed)
    bm = bm or k.sketch
    acc = 0.0
    cnt = 0
    for i in range(len(pts) - 1):
        a, b = V(pts[i]), V(pts[i + 1])
        e = b - a
        ln = e.length
        if ln < 1e-4:
            continue
        nrm = V((-e.y, e.x)).normalized() * side
        t = (step - acc) % step
        while t < ln:
            p = a + e * (t / ln)
            L_ = 0.32 if cnt % 4 == 0 else 0.15
            ground_stroke(bm, [p, p + nrm * L_], y, 0.03, 0.02)
            cnt += 1
            t += step
        acc = (acc + ln) % step


def light_pool(k, c, r, y, seg=28):
    """radial light pool decal: UV v = 0 at the centre -> 1 at the rim (fade in the shader)."""
    uvl = k.pool.loops.layers.uv.active or k.pool.loops.layers.uv.new('UVMap')
    rings = [0.0, 0.35, 0.65, 0.85, 1.0]
    vv = []
    for rr in rings:
        ring = []
        for i in range(seg if rr > 0 else 1):
            th = 2 * math.pi * i / seg
            wob = 1.0 + (0.06 * math.sin(th * 5) if rr > 0.6 else 0)
            p = V(c) + V((math.cos(th) * r * rr * wob, math.sin(th) * r * rr * wob))
            yy = y(p) if callable(y) else y
            ring.append((k.pool.verts.new(B(p.x, p.y, yy + 0.05)), rr))
        vv.append(ring)
    for ri in range(1, len(rings)):
        for i in range(seg):
            j = (i + 1) % seg
            if ri == 1:
                vs = [vv[0][0], vv[1][i], vv[1][j]]
            else:
                vs = [vv[ri - 1][i], vv[ri][i], vv[ri][j], vv[ri - 1][j]]
            f = add_face(k.pool, [x[0] for x in vs], V((0, 0, 1)))
            if f:
                for lp in f.loops:
                    for (vert, rr) in [x for x in vs]:
                        if vert == lp.vert:
                            lp[uvl].uv = (0.5, rr)


def beam(k, c, r0, r1, y0, y1, seg=16):
    """light beam (two nested open cones), UV v = 0 at the ground -> 1 at the top."""
    uvl = k.beam.loops.layers.uv.active or k.beam.loops.layers.uv.new('UVMap')
    for (k0, k1) in ((1.0, 1.0), (0.55, 0.6)):
        rows = 4
        vr = []
        for r_ in range(rows + 1):
            t = r_ / rows
            y = y0 + (y1 - y0) * t
            rr = (r0 * k0) + ((r1 * k1) - (r0 * k0)) * t
            vr.append([k.beam.verts.new(B(c.x + math.cos(2 * math.pi * i / seg) * rr, c.y + math.sin(2 * math.pi * i / seg) * rr, y)) for i in range(seg)])
        for r_ in range(rows):
            for i in range(seg):
                j = (i + 1) % seg
                f = add_face(k.beam, [vr[r_][i], vr[r_][j], vr[r_ + 1][j], vr[r_ + 1][i]], None)
                if f:
                    for lp, (uu, vv) in zip(f.loops, ((i / seg, r_ / rows), ((i + 1) / seg, r_ / rows), ((i + 1) / seg, (r_ + 1) / rows), (i / seg, (r_ + 1) / rows))):
                        lp[uvl].uv = (uu, vv)


def dust(k, c, r, y0, y1, n, seed):
    rnd = random.Random(seed)
    for _ in range(n):
        a = rnd.uniform(0, 2 * math.pi)
        rr = r * math.sqrt(rnd.random())
        y = rnd.uniform(y0, y1)
        p = V(c) + V((math.cos(a), math.sin(a))) * rr * (0.75 + 0.25 * (y - y0) / (y1 - y0))
        s = rnd.uniform(0.035, 0.09)
        ang = rnd.uniform(0, math.pi)
        dx, dz = math.cos(ang) * s, math.sin(ang) * s
        q = [k.dust.verts.new(B(p.x - dx, p.y - dz, y - s)), k.dust.verts.new(B(p.x + dx, p.y + dz, y - s)),
             k.dust.verts.new(B(p.x + dx, p.y + dz, y + s)), k.dust.verts.new(B(p.x - dx, p.y - dz, y + s))]
        add_face(k.dust, q, None)


def cave(k, origin, yaw_c, seed):
    """underground backdrop: far cave wall arc with strata, stalactites hanging into the low camera's frame, a few
    columns, and distant unfinished structures drawn only as lines."""
    rnd = random.Random(seed)
    o = V(origin)
    # far wall (arc, faces the origin)
    R0 = 135.0
    cols = 26
    rows = [FLOOR - 2.0, -4.0, 12.0, 30.0, 52.0]
    grid = []
    for ci in range(cols + 1):
        th = math.radians(yaw_c - 75 + 150 * ci / cols)
        col = []
        for ry in rows:
            rr = R0 + 9 * math.sin(ci * 1.3 + ry * 0.07) + rnd.uniform(-3, 3)
            p = o + V((math.sin(th), math.cos(th))) * rr
            col.append(k.cave.verts.new(B(p.x, p.y, ry)))
        grid.append(col)
    for ci in range(cols):
        for ri in range(len(rows) - 1):
            th = math.radians(yaw_c - 75 + 150 * (ci + 0.5) / cols)
            inward = V((-math.sin(th), -math.cos(th)))
            add_face(k.cave, [grid[ci][ri], grid[ci + 1][ri], grid[ci + 1][ri + 1], grid[ci][ri + 1]], V((-inward.x, -inward.y, 0)))
    # strata lines on the wall (thick: seen from 100 m+)
    for s in range(5):
        yy = -6 + s * 6.5 + rnd.uniform(-1, 1)
        pts = []
        for ci in range(0, cols + 1):
            th = math.radians(yaw_c - 75 + 150 * ci / cols)
            rr = R0 + 9 * math.sin(ci * 1.3 + yy * 0.07) - 1.5
            p = o + V((math.sin(th), math.cos(th))) * rr
            pts.append(B(p.x, p.y, yy + 2.0 * math.sin(ci * 0.9 + s)))
        for i in range(0, len(pts) - 2, 3):
            if rnd.random() < 0.7:
                stroke3(k.hatch, pts[i:i + 3], 0.35)
    # stalactites
    for i in range(18):
        th = math.radians(yaw_c + rnd.uniform(-40, 40))
        d = rnd.uniform(70, 125)
        c = o + V((math.sin(th), math.cos(th))) * d
        tip = rnd.uniform(-16.0, -4.0) + (d - 70) * 0.08
        r = rnd.uniform(2.0, 6.5)
        sides = 6
        rings = [(46.0, r), (tip + (46 - tip) * 0.45, r * rnd.uniform(0.55, 0.75)), (tip + (46 - tip) * 0.15, r * rnd.uniform(0.2, 0.35))]
        vr = []
        for (yy, rr) in rings:
            a0 = rnd.uniform(0, 1)
            vr.append([k.cave.verts.new(B(c.x + math.cos(a0 + 2 * math.pi * s / sides) * rr, c.y + math.sin(a0 + 2 * math.pi * s / sides) * rr, yy)) for s in range(sides)])
        tv = k.cave.verts.new(B(c.x + rnd.uniform(-0.5, 0.5), c.y + rnd.uniform(-0.5, 0.5), tip))
        cB = B(c.x, c.y, 0)
        for ri in range(len(vr) - 1):
            for s in range(sides):
                f = add_face(k.cave, [vr[ri][s], vr[ri][(s + 1) % sides], vr[ri + 1][(s + 1) % sides], vr[ri + 1][s]], None)
                if f:
                    m = f.calc_center_median(); out = V((m.x - cB.x, m.y - cB.y, 0))
                    if f.normal.dot(out) < 0: f.normal_flip()
        for s in range(sides):
            f = add_face(k.cave, [vr[-1][s], vr[-1][(s + 1) % sides], tv], None)
            if f:
                m = f.calc_center_median(); out = V((m.x - cB.x, m.y - cB.y, 0))
                if f.normal.dot(out) < 0: f.normal_flip()
        # one contour line down the near edge
        stroke3(k.ink, [vr[0][0].co, vr[1][0].co, vr[2][0].co, tv.co], 0.18)
    # columns (stalactite meets stalagmite)
    for i in range(3):
        th = math.radians(yaw_c + rnd.uniform(-35, 35))
        d = rnd.uniform(95, 125)
        c = o + V((math.sin(th), math.cos(th))) * d
        prof = [(FLOOR - 1, 6.5), (-9, 3.4), (-3, 1.8), (1, 1.5), (8, 2.4), (46, 7.0)]
        sides = 7
        vr = [[k.cave.verts.new(B(c.x + math.cos(2 * math.pi * s / sides) * rr, c.y + math.sin(2 * math.pi * s / sides) * rr, yy)) for s in range(sides)] for (yy, rr) in prof]
        cB = B(c.x, c.y, 0)
        for ri in range(len(vr) - 1):
            for s in range(sides):
                f = add_face(k.cave, [vr[ri][s], vr[ri][(s + 1) % sides], vr[ri + 1][(s + 1) % sides], vr[ri + 1][s]], None)
                if f:
                    m = f.calc_center_median(); out = V((m.x - cB.x, m.y - cB.y, 0))
                    if f.normal.dot(out) < 0: f.normal_flip()
    # distant unfinished structures: towers and a bridge drawn only in lines
    for i in range(3):
        th = math.radians(yaw_c + rnd.uniform(-30, 30))
        d = rnd.uniform(78, 100)
        c = o + V((math.sin(th), math.cos(th))) * d
        base = FLOOR
        hgt = rnd.uniform(14, 22)
        rr = rnd.uniform(1.8, 3.0)
        for s in range(4):
            a = 2 * math.pi * s / 4 + 0.4
            p = c + V((math.cos(a), math.sin(a))) * rr
            stroke3(k.sketch, [B(p.x, p.y, base), B(p.x, p.y, base + hgt)], 0.14)
        for t in range(5):
            yy = base + hgt * t / 4
            wire_loop(k.sketch, [c + V((math.cos(2 * math.pi * s / 4 + 0.4), math.sin(2 * math.pi * s / 4 + 0.4))) * rr for s in range(4)], yy, 0.12, gap=0.2, seed=seed + i * 7 + t)
        tipc = B(c.x, c.y, base + hgt + 4.0)
        for s in range(4):
            a = 2 * math.pi * s / 4 + 0.4
            p = c + V((math.cos(a), math.sin(a))) * rr
            stroke3(k.sketch, [B(p.x, p.y, base + hgt), tipc], 0.12)


# --------------------------------------------------------------------------------------------- pieces
class Kit:
    """bmesh buckets for one target part set."""

    def __init__(self):
        self.walk, self.road, self.margin = bmesh.new(), bmesh.new(), bmesh.new()
        self.solid, self.ink, self.hatch, self.sketch = bmesh.new(), bmesh.new(), bmesh.new(), bmesh.new()
        self.paint, self.paintr, self.dark, self.wood = bmesh.new(), bmesh.new(), bmesh.new(), bmesh.new()
        self.books = {'M_BookRed': bmesh.new(), 'M_BookGreen': bmesh.new(), 'M_BookBlue': bmesh.new(), 'M_PageWhite': bmesh.new()}
        self.terra, self.terrad, self.stage, self.curtain, self.navy, self.glow = (bmesh.new() for _ in range(6))
        self.plaza, self.stones, self.spire, self.lower = bmesh.new(), bmesh.new(), bmesh.new(), bmesh.new()
        self.cave, self.torn, self.smudge, self.pool, self.dust = bmesh.new(), bmesh.new(), bmesh.new(), bmesh.new(), bmesh.new()
        self.beam = bmesh.new()
        self.abyss = bmesh.new()


def riser(k, poly_pts, y_hi, y_lo, real, seed, closed=False):
    """a low step wall along a polyline (terrace edge), facing to the right of travel; ink on its lip."""
    rnd = random.Random(seed)
    m = len(poly_pts)
    rng = range(m if closed else m - 1)
    for i in rng:
        a, b = poly_pts[i], poly_pts[(i + 1) % m]
        e = b - a
        if e.length < 1e-4:
            continue
        en = V((e.y, -e.x)).normalized()
        q = [k.solid.verts.new(B(a.x, a.y, y_hi)), k.solid.verts.new(B(b.x, b.y, y_hi)), k.solid.verts.new(B(b.x, b.y, y_lo - 0.02)), k.solid.verts.new(B(a.x, a.y, y_lo - 0.02))]
        add_face(k.solid, q, V((-en.x, -en.y, 0)))
        off = V((-en.x, -en.y, 0)) * 0.02
        if rnd.random() < 0.8:
            t0, t1 = rnd.uniform(0.0, 0.15), rnd.uniform(0.8, 1.05)
            stroke3(k.ink, [B(*a.lerp(b, t0), y_hi + 0.02) + off, B(*a.lerp(b, t1), y_hi + 0.02) + off], 0.075 if real else 0.06)
        if real and shaded(en):
            hatch_face(k.hatch, a, b, y_hi, y_hi, y_lo, en, rnd, 0.8, (y_hi - y_lo) * 0.9, 0.028)


def mesa_fall(k, real=True):
    """hilltop (3 terraces) + margin terrace + ramp + landing (+ neck stumps). real=False: vista copy."""
    hi, lo, mid = ccw(HILL_HI), ccw(HILL_LO), ccw(HILL_MID)
    fill(k.walk, hi, H_HI, steiner=grid_pts(hi, 2.0, 2))
    fill(k.walk, mid, H_MID, holes=[hi], steiner=grid_pts(mid, 2.2, 3))
    fill(k.walk, lo, H_LO, steiner=grid_pts(lo, 2.0, 6))
    riser(k, HILL_HI, H_HI, H_MID, real, 12, closed=True)
    riser(k, HILL_LO_IN, H_MID, H_LO, real, 13)
    # step slabs where the drawn path crosses the terrace edges
    PA, PB = HEAP + V((1.4, -0.8)), RAMP_T
    pd = (PB - PA).normalized()
    for poly, y0, y1 in ((HILL_HI, H_MID, H_HI), (HILL_LO_IN, H_LO, H_MID)):
        m = len(poly)
        for i in range(m if poly is HILL_HI else m - 1):
            a, b = poly[i], poly[(i + 1) % m]
            den = (PB.x - PA.x) * (b.y - a.y) - (PB.y - PA.y) * (b.x - a.x)
            if abs(den) < 1e-6:
                continue
            t = ((a.x - PA.x) * (b.y - a.y) - (a.y - PA.y) * (b.x - a.x)) / den
            u = ((a.x - PA.x) * (PB.y - PA.y) - (a.y - PA.y) * (PB.x - PA.x)) / den
            if 0 <= t <= 1 and 0 <= u <= 1:
                c = PA + (PB - PA) * t + pd * (0.3 if y1 == H_HI else 0.3)
                box(k.solid, (c.x, c.y), (1.0, (y1 - y0) * 0.5, 0.5), y0, math.degrees(math.atan2(pd.x, pd.y)))
    for si, (slab, drop, tilt) in enumerate(MARGIN_SLABS):
        sl = ccw(slab)
        y0 = H_MID - drop
        yf = lambda p, y0=y0, tilt=tilt: y0 + (p.x + 63.5) * tilt
        fill(k.margin, sl, yf, steiner=grid_pts(sl, 1.6, 4 + si))
        walls(k.solid, k.ink, k.hatch, sl, lambda i, sl=sl, yf=yf: yf(sl[i]), FLOOR, 104 + si, ledge=1.2, ledge_out=0.25, hatch_floor=-1.0,
              hatch_density=1.0, deep=k.dark, deep_y=-0.6, unf=(lambda a, b: (a + b).y / 2 > 35.5) if si == 2 else None, sketch=k.sketch, torn=k.torn)
    ramp_edge = lambda a, b: ((a - RAMP_TR).length < 0.05 and (b - RAMP_TL).length < 0.05) or ((a - RAMP_TL).length < 0.05 and (b - RAMP_TR).length < 0.05)

    def skip_w(a, b):
        return ramp_edge(a, b)

    def unf_w(a, b):
        e = b - a
        en = V((e.y, -e.x)).normalized()
        m = (a + b) / 2
        return (en.y > 0.55 and -57.5 < m.x < -51.8) or (en.y < -0.55 and -58.2 < m.x < -55.5)
    wf = ccw(WALK_F)
    walls(k.solid, k.ink, k.hatch, wf, lambda i: hill_h(wf[i] + (V((-60, 30)) - wf[i]).normalized() * 0.3), FLOOR, 101,
          ledge=1.5, skip=skip_w, hatch_floor=0.0, hatch_density=1.0 if real else 0.6, unf=unf_w, sketch=k.sketch, torn=k.torn,
          deep=k.dark, deep_y=-0.6)
    # ramp (the ladder lies on it): walk surface + side walls down to the landing
    vs = [k.walk.verts.new(B(RAMP_TL.x, RAMP_TL.y, H_LO)), k.walk.verts.new(B(RAMP_TR.x, RAMP_TR.y, H_LO)),
          k.walk.verts.new(B(RAMP_BR.x, RAMP_BR.y, G0)), k.walk.verts.new(B(RAMP_BL.x, RAMP_BL.y, G0))]
    add_face(k.walk, vs, V((0, 0, 1)))
    for (a, b) in ((RAMP_TR, RAMP_BR), (RAMP_BL, RAMP_TL)):
        ya = H_LO if (a - RAMP_T).length < 1.2 else G0
        yb = H_LO if (b - RAMP_T).length < 1.2 else G0
        e = b - a
        en = V((e.y, -e.x)).normalized()
        q = [k.solid.verts.new(B(a.x, a.y, ya)), k.solid.verts.new(B(b.x, b.y, yb)),
             k.solid.verts.new(B(b.x, b.y, G0 - 0.05)), k.solid.verts.new(B(a.x, a.y, G0 - 0.05))]
        add_face(k.solid, q, V((-en.x, -en.y, 0)))
        stroke3(k.ink, [B(a.x, a.y, ya + 0.03), B(b.x, b.y, yb + 0.03)], 0.08)
    # landing ledge
    land = ccw(LAND)
    fill(k.walk, land, G0, steiner=grid_pts(land, 1.8, 5))
    walls(k.solid, k.ink, k.hatch if real else None, LAND, G0, FLOOR, 103, ledge=1.6, ledge_out=0.4,
          skip=lambda a, b: (a.x > -39.1 and b.x > -39.1 and min(a.y, b.y) < 25.6 and max(a.y, b.y) > 23.2) or
          (min(a.y, b.y) > 21.8 and max(a.x, b.x) < -49.2) or ((a + b).x / 2 < -46.0 and (a + b).y / 2 > 22.6),
          hatch_density=0.8 if real else 0.0, unf=lambda a, b: (a + b).y / 2 < 18.6 and -52.0 < (a + b).x / 2 < -46.5, sketch=k.sketch, torn=k.torn,
          deep=k.dark, deep_y=-0.6)
    # neck stumps (hold the drawn bar; make the bar the only way): near half solid, far half only drawn
    bd = (PATH_LAND[2] - PATH_LAND[1]).normalized()
    bp = V((-bd.y, bd.x))
    for c, sd in ((PATH_LAND[1] + bp * 1.3, 21), (PATH_LAND[1] - bp * 1.3, 22)):
        rock_wire(k, hexp(c, 0.5, sd, sq=0.9), G0, 1.35, 1, sd, wire=0.45, hatch=real)
    # the cleft: a dark slot down the south face under the notch (the kid slips through it to the shelf)
    q = [k.dark.verts.new(B(-53.72, 22.62, H_LO - 0.02)), k.dark.verts.new(B(-53.38, 22.62, H_LO - 0.02)),
         k.dark.verts.new(B(-53.38, 22.25, G0 + 0.05)), k.dark.verts.new(B(-53.72, 22.25, G0 + 0.05))]
    add_face(k.dark, q, V((0, 1, 0)))
    stroke3(k.ink, [B(-53.75, 22.4, H_LO + 0.03), B(-53.8, 22.05, G0 + 0.05)], 0.06)
    stroke3(k.ink, [B(-53.35, 22.4, H_LO + 0.03), B(-53.3, 22.05, G0 + 0.05)], 0.06)


def fall_lines(k):
    """hilltop drawing: paving thick around the heap, thinning outward; a drawn path that steps down the terraces to the
    ladder edge; cracks; light-pool rings; construction left on the page; landing lines."""
    hy = lambda p: hill_h(p)
    walk = ccw(WALK_F)
    near_heap = lambda p: (p - HEAP).length < 1.6
    PA, PB = HEAP + V((1.4, -0.8)), RAMP_T + V((-0.1, 0.0))
    on_path = lambda p: LV.seg_dist(p, PA, PB)[0] < 0.95

    def edge_ok(p):
        return abs(hill_h(p) - hill_h(p + V((0.25, 0.0)))) < 0.01 and abs(hill_h(p) - hill_h(p - V((0.25, 0.0)))) < 0.01 and \
            abs(hill_h(p) - hill_h(p + V((0.0, 0.25)))) < 0.01 and abs(hill_h(p) - hill_h(p - V((0.0, 0.25)))) < 0.01
    hex_lines(k.ink, walk, hy, 1.15, 31, keep=0.6, origin=(HEAP.x, HEAP.y), avoid=lambda p: near_heap(p) or on_path(p) or (p - HEAP).length > 6.0 or not edge_ok(p))
    hex_lines(k.ink, walk, hy, 1.15, 32, keep=0.16, origin=(HEAP.x, HEAP.y), avoid=lambda p: (p - HEAP).length <= 6.0 or on_path(p) or not edge_ok(p))
    cracks(k.ink, walk, hy, 14, 33, avoid=lambda p: near_heap(p) or on_path(p) or not edge_ok(p))
    # the path: double broken edges + stepping stones, from the heap down toward the ladder (pieces stay on one terrace)
    d = (PB - PA).normalized()
    n = V((-d.y, d.x))
    ln = (PB - PA).length
    rnd = random.Random(35)
    for side in (1, -1):
        t = 0.0
        while t < ln:
            seg = rnd.uniform(0.5, 1.1)
            p0 = PA + d * t + n * 0.82 * side
            p1 = PA + d * min(ln, t + seg) + n * (0.82 + rnd.uniform(-0.05, 0.05)) * side
            if abs(hill_h(p0) - hill_h(p1)) < 0.01 and edge_ok(p0) and edge_ok(p1):
                ground_stroke(k.ink, [p0, p1], hy, 0.075)
            t += seg + rnd.uniform(0.15, 0.4)
    for i in range(6):
        p = PA + d * (ln * (i + 0.5) / 6.2) + n * rnd.uniform(-0.25, 0.25)
        if not edge_ok(p):
            continue
        poly = jag_poly(p, 0.3, 0.22, 7, 40 + i, rot=math.atan2(d.y, d.x))
        ground_stroke(k.ink, poly + [poly[0]], hy, 0.045)
    # light pool rings (drawn)
    for r, w in ((2.6, 0.05), (3.15, 0.035)):
        pts = []
        for i in range(0, 41):
            th = 2 * math.pi * i / 40
            q = HEAP + V((math.cos(th) * r * 1.05, math.sin(th) * r))
            if rnd.random() < 0.18 or not edge_ok(q):
                if len(pts) > 1:
                    ground_stroke(k.ink, pts, hy, w)
                pts = []
                continue
            pts.append(q)
        if len(pts) > 1:
            ground_stroke(k.ink, pts, hy, w)
    # landing: flagstones and the drawn path to the bridge
    land = ccw(LAND)
    hex_lines(k.ink, land, G0, 0.9, 36, keep=0.5, origin=(-43.8, 21.3), avoid=lambda p: LV.seg_dist(p, RAMP_B, RAMP_T)[0] < 1.2)
    for side in (1, -1):
        pts = []
        for i in range(len(PATH_LAND) - 1):
            a, b = PATH_LAND[i], PATH_LAND[i + 1]
            d = (b - a).normalized()
            nn = V((-d.y, d.x)) * 1.05 * side
            pts += [a + nn + d * 0.4, b + nn - d * 0.2]
        ground_stroke(k.ink, pts, G0, 0.07)
    for si, (slab, drop, tilt) in enumerate(MARGIN_SLABS):
        cracks(k.ink, ccw(slab), lambda p, d=drop, t=tilt: H_MID - d + (p.x + 63.5) * t, 3, 37 + si)
    # left-over construction: compass circles round the landing spot, guide lines from the heap toward the ladder,
    # measuring ticks along the east rim, smudged erasures
    compass(k, HEAP, 4.6, hy, 41, 0.72)
    compass(k, HEAP, 1.2, hy, 42, 1.0)
    for off in (-0.7, 0.7):
        a0 = HEAP + V((1.0, off * 0.5))
        b0 = RAMP_T + V((0.0, off * 0.9))
        pts = [a0.lerp(b0, t / 14) for t in range(15)]
        run = []
        for p in pts:
            if edge_ok(p) and (not run or abs(hill_h(p) - hill_h(run[-1])) < 0.01):
                run.append(p)
            else:
                if len(run) > 1:
                    ground_stroke(k.sketch, run, hy, 0.03, 0.02)
                run = [p] if edge_ok(p) else []
        if len(run) > 1:
            ground_stroke(k.sketch, run, hy, 0.03, 0.02)
    ticks_along(k, [V((-52.4, 22.3)), RAMP_TR], H_LO, 0.5, 43, side=1)
    ticks_along(k, [RAMP_TL, V((-49.85, 25.0)), V((-49.8, 28.4))], H_LO, 0.5, 44, side=-1)
    ticks_along(k, [V((-50.4, 30.6)), V((-51.1, 33.0)), V((-52.5, 35.4))], H_MID, 0.5, 45, side=-1)
    for (c, rx, rz, rot, sd) in (((-59.6, 25.2), 1.6, 0.6, 0.4, 1), ((-51.6, 33.6), 1.3, 0.5, -0.5, 2), ((-58.4, 35.0), 0.9, 0.45, 1.2, 3),
                                 ((-47.6, 20.6), 1.0, 0.4, 0.3, 4)):
        smudge(k, c, rx, rz, rot, (lambda p: hill_h(p)) if c[0] < -50 else G0, 60 + sd)


def fall_rocks(k):
    """framing rocks on the hilltop edge (never between camera and player: west/foreground ones stay low)."""
    rocks = [((-64.2, 26.2), 1.0, 0.75, 0.55, 1, 51), ((-64.9, 31.0), 0.9, 0.8, 0.5, 1, 52), ((-63.4, 35.6), 1.0, 0.75, 0.5, 1, 53),
             ((-57.8, 36.5), 1.1, 0.65, 0.7, 1, 55), ((-51.2, 32.0), 0.85, 1.0, 1.3, 2, 57), ((-50.9, 29.9), 0.6, 0.6, 0.7, 1, 61),
             ((-59.6, 23.9), 0.9, 0.6, 0.5, 1, 58)]
    for i, (c, rx, rz, h, t, s) in enumerate(rocks):
        y0 = hill_h(c)
        for (slab, drop, tilt) in MARGIN_SLABS:
            if inside(V(c), slab):
                y0 = H_MID - drop + (c[0] + 63.5) * tilt
        poly = hexp(c, rx, s, sq=rz / rx)
        if i % 2 == 1 or c[0] > -54:
            rock_wire(k, poly, y0, h, t, s, wire=0.5)
        else:
            rock(k.solid, k.ink, k.hatch, poly, y0, h, t, s)
    # the way out: two human-made posts at the ladder top with a blue rag (the only painted thing on the hill edge)
    for side, hgt in ((1, 1.25), (-1, 1.0)):
        c = RAMP_T + _rn * (1.18 * side) - RAMP_DIR * 0.15
        box(k.wood, (c.x, c.y), (0.16, hgt + 0.3, 0.16), H_LO - 0.3, 145)
        stroke3(k.ink, [B(c.x, c.y, H_LO), B(c.x, c.y, H_LO + hgt)], 0.035)
    c = RAMP_T + _rn * 1.18 - RAMP_DIR * 0.15
    pennant(k.solid, k.paint, k.ink, c, H_LO + 0.55, h=0.75, d=(RAMP_DIR.x, RAMP_DIR.y))
    # a house that was never finished, at the north edge of the hill (front wall built, the rest only drawn)
    unfinished_house(k, (-53.4, 35.0), 2.9, 2.0, 2.2, 100, H_MID, 77, roof=1.4)


def gate_plateau(k, real=True):
    walk = ccw(WALK_G)
    plat = ccw(PLAT)
    fill(k.walk, walk, G0, steiner=grid_pts(walk, 2.0, 61))
    # margin = plateau minus walk
    gh = [jag_poly((-19.6, 31.7), 0.9, 0.7, 8, 63, 0.2), jag_poly((-33.0, 17.6), 0.7, 0.45, 7, 64)]
    fill(k.margin, plat, G0, holes=[walk] + [ccw(h) for h in gh], steiner=grid_pts(plat, 2.4, 62))
    for i, h in enumerate(gh):
        torn_hole(k, h, G0, 1.2, 65 + i)
    # chasm-facing (west) wall goes to the floor, others to the lower ground
    walls(k.solid, k.ink, k.hatch, PLAT, G0, FLOOR, 111, ledge=1.1, ledge_out=0.3,
          skip=lambda a, b: (a - V((-28.9, 18.4))).length < 0.1 and (b - V((-27.1, 18.4))).length < 0.1 or
          (a.x > -18.5 and b.x > -18.5 and min(a.y, b.y) >= 22.5 and max(a.y, b.y) <= 26.7),
          hatch_floor=0.0, hatch_density=1.0 if real else 0.35, deep=k.dark, deep_y=-0.6,
          unf=lambda a, b: ((a + b).y / 2 > 33.0 and -31.0 < (a + b).x / 2 < -21.0) or ((a + b).y / 2 < 17.6 and (a + b).x / 2 > -26.0),
          sketch=k.sketch, torn=k.torn)
    for i, (c, rx, rz, h, t, s, rot) in enumerate(GATE_ROCKS):
        poly = hexp(c, rx, s, rot, sq=rz / rx)
        if h > 4.5:
            # gate pillars: stacked basalt slabs up to ~60 %, the rest stands only as drawn tiers + plumb line
            cairn(k, c, rx, h, G0, s, real, 0.4)
        elif i in (1, 5):
            rock_wire(k, poly, G0, h, t, s, wire=0.4, hatch=True)
        else:
            rock(k.solid, k.ink, k.hatch, poly, G0, h, t, s)
    # in the north wall: a gatekeeper's house that was never finished (front built, the rest only drawn)
    unfinished_house(k, (-28.6, 31.7), 3.4, 2.2, 2.7, 12, G0, 78, roof=1.6)
    # the north wall continues as a back ledge (higher, behind the front slabs) = the pass walls step up
    for (c, rx, h, sd) in (((-31.6, 32.6), 1.6, 2.4, 41), ((-25.6, 32.5), 1.9, 3.8, 42), ((-22.6, 32.2), 1.2, 4.6, 43)):
        rock(k.solid, k.ink, k.hatch, hexp(c, rx, sd, 0.0, sq=0.55), G0, h, 2, sd)
    for (c, rx, rz, h, s) in SEAT_STONES:
        rock(k.solid, k.ink, k.hatch if real else None, hexp(c, rx, s, sq=rz / rx), G0, h, 1, s)
    # tablet curb: three low stones behind the tablet
    tb = V(GATE_PTS['gate_stone'])
    for i, (dx, dz) in enumerate(((-1.0, 0.9), (0.2, 1.25), (1.2, 0.75))):
        rock(k.solid, k.ink, k.hatch if real else None, jag_poly(tb + V((dx, dz)), 0.45, 0.35, 6, 70 + i), G0, 0.35 + 0.1 * i, 1, 70 + i)
    # drawn arch over the gate: ink only (pillar tops -> sagging double line), a red pennant hanging from it
    n_top = V((-21.0, 30.0))
    s_top = V((-20.6, 20.3))
    arch = []
    for i in range(13):
        t = i / 12
        p = n_top.lerp(s_top, t)
        arch.append(B(p.x, p.y, G0 + 6.0 + (5.0 - 6.0) * t + math.sin(math.pi * t) * 1.3))
    stroke3(k.ink, arch, 0.09)
    stroke3(k.ink, [v + V((0, 0, 0.28)) for v in arch[1:-1]], 0.05)
    for i in (3, 6, 9):
        stroke3(k.ink, [arch[i], arch[i] + V((0, 0, -0.55))], 0.04)
    mid = n_top.lerp(s_top, 0.5)
    pennant(k.solid, k.paintr, k.ink, mid + V((0.15, 0.0)), G0 + 5.55 + 1.3 - 0.9, h=0.7, d=(1, 0))
    # bridge: paper planks + rails drawn only in ink
    x0, x1, zc, w = BRIDGE_X0, BRIDGE_X1, BRIDGE_Z, BRIDGE_W
    deck = [V((x0, zc - w / 2)), V((x1, zc - w / 2)), V((x1, zc + w / 2)), V((x0, zc + w / 2))]
    fill(k.walk, ccw(deck), G0, steiner=[V((x0 + 1.7 * i, zc)) for i in range(1, 4)])
    q = [k.solid.verts.new(B(x0, zc - w / 2, G0 - 0.22)), k.solid.verts.new(B(x1, zc - w / 2, G0 - 0.22)),
         k.solid.verts.new(B(x1, zc + w / 2, G0 - 0.22)), k.solid.verts.new(B(x0, zc + w / 2, G0 - 0.22))]
    add_face(k.solid, q, V((0, 0, -1)))
    for side in (-1, 1):
        zz = zc + side * w / 2
        q = [k.solid.verts.new(B(x0, zz, G0)), k.solid.verts.new(B(x1, zz, G0)), k.solid.verts.new(B(x1, zz, G0 - 0.22)), k.solid.verts.new(B(x0, zz, G0 - 0.22))]
        add_face(k.solid, q, V((0, side * -1, 0)))
    rnd = random.Random(80)
    xx = x0 + 0.25
    while xx < x1 - 0.1:
        ground_stroke(k.ink, [V((xx, zc - w / 2 + 0.05)), V((xx + rnd.uniform(-0.04, 0.04), zc + w / 2 - 0.05))], G0, 0.035, 0.015)
        xx += rnd.uniform(0.42, 0.55)
    for side in (-1, 1):
        zz = zc + side * (w / 2 - 0.08)
        ground_stroke(k.ink, [V((x0, zz)), V((x1, zz))], G0, 0.06, 0.016)
        posts = [x0 + (x1 - x0) * i / 6 for i in range(7)]
        for px in posts:
            stroke3(k.ink, [B(px, zz, G0 - 0.25), B(px + rnd.uniform(-0.04, 0.04), zz, G0 + 1.05)], 0.055)
        for hh, ww in ((1.0, 0.06), (0.55, 0.04)):
            pts = [B(x0 + (x1 - x0) * t / 10, zz, G0 + hh - 0.12 * math.sin(math.pi * t / 10)) for t in range(11)]
            if side > 0 and hh < 1.0:
                stroke3(k.sketch, pts[:6], ww)        # the far lower rail was never inked
            else:
                stroke3(k.ink, pts, ww)
        # rope stays down to the banks
        stroke3(k.ink, [B(x0, zz, G0 + 1.05), B(x0 - 0.9, zz + side * 0.3, G0 + 0.02)], 0.035)
        stroke3(k.ink, [B(x1, zz, G0 + 1.05), B(x1 + 0.9, zz + side * 0.3, G0 + 0.02)], 0.035)
    # under-bridge hatch (a drawn truss)
    for i in range(6):
        px = x0 + (x1 - x0) * (i + 0.5) / 6
        stroke3(k.ink, [B(px - 0.5, zc - w / 2 - 0.02, G0 - 0.22), B(px + 0.5, zc - w / 2 - 0.02, G0 - 0.9)], 0.03)
    # cart stairs (non-walk; the exit sits on their top step)
    top, d, sw, nsteps, rise, run = CART_STAIR
    nn = V((-d.y, d.x))
    for i in range(nsteps):
        c0 = top + d * (run * i)
        y = G0 - rise * (i + 1)
        corners = [c0 - nn * sw / 2, c0 + nn * sw / 2, c0 + nn * sw / 2 + d * run, c0 - nn * sw / 2 + d * run]
        e0, e1 = c0 - nn * sw / 2, c0 + nn * sw / 2
        if i < 4:
            fill(k.margin, ccw(corners), y)
            qq = [k.solid.verts.new(B(e0.x, e0.y, y + rise)), k.solid.verts.new(B(e1.x, e1.y, y + rise)),
                  k.solid.verts.new(B(e1.x, e1.y, y)), k.solid.verts.new(B(e0.x, e0.y, y))]
            add_face(k.solid, qq, V((-d.x, -d.y, 0)) * -1)
            stroke3(k.ink, [B(e0.x, e0.y, y + 0.02), B(e1.x, e1.y, y + 0.02)], 0.05)
        else:
            # the stairs dissolve into sketch strokes
            bm = k.sketch
            stroke3(bm, [B(e0.x, e0.y, y + rise), B(e1.x, e1.y, y + rise)], 0.04)
            stroke3(bm, [B(e0.x, e0.y, y + rise), B(e0.x, e0.y, y)], 0.035)
            stroke3(bm, [B(e0.x, e0.y, y), B((e0 + d * run).x, (e0 + d * run).y, y)], 0.035)
    for side in (-1, 1):
        p0 = top + nn * side * (sw / 2 + 0.05)
        p1 = top + d * (run * nsteps) + nn * side * (sw / 2 + 0.05)
        stroke3(k.ink, [B(p0.x, p0.y, G0 + 0.05), B(p1.x, p1.y, G0 - rise * nsteps + 0.05)], 0.06)
        stroke3(k.ink, [B(p0.x, p0.y, G0 + 0.85), B(p1.x, p1.y, G0 - rise * nsteps + 0.85)], 0.04)
    if real:
        pennant(k.solid, k.paint, k.ink, top + nn * 1.25 + d * 0.3, G0, h=2.2, d=(-d.x, -d.y))
    # steps down toward the plaza beyond the gate (east): non-walk, they lead the eye
    for i in range(8):
        x = -18.4 + i * 0.6
        y = G0 - 0.3 * (i + 1)
        corners = [V((x, 22.7 - i * 0.12)), V((x + 0.6, 22.7 - (i + 1) * 0.12)), V((x + 0.6, 26.5 - (i + 1) * 0.12)), V((x, 26.5 - i * 0.12))]
        if i < 5:
            fill(k.margin, ccw(corners), y)
            qq = [k.solid.verts.new(B(x, 22.7 - i * 0.12, y + 0.3)), k.solid.verts.new(B(x, 26.5 - i * 0.12, y + 0.3)),
                  k.solid.verts.new(B(x, 26.5 - i * 0.12, y)), k.solid.verts.new(B(x, 22.7 - i * 0.12, y))]
            add_face(k.solid, qq, V((1, 0, 0)))
            stroke3(k.ink, [B(x, 22.7 - i * 0.12, y + 0.02), B(x, 26.5 - i * 0.12, y + 0.02)], 0.05)
        else:
            stroke3(k.sketch, [B(x, 22.7 - i * 0.12, y + 0.3), B(x, 26.5 - i * 0.12, y + 0.3)], 0.04)
            stroke3(k.sketch, [B(x, 26.5 - i * 0.12, y + 0.3), B(x, 26.5 - i * 0.12, y), B(x + 0.6, 26.5 - (i + 1) * 0.12, y)], 0.035)


def gate_lines(k):
    walk = ccw(WALK_G)
    road = [V((-33.8, 23.2)), V((-30.0, 22.9)), V((-26.0, 22.95)), V((-22.0, 23.0)), V((-19.3, 23.1)), V((-19.3, 26.2)),
            V((-22.0, 26.3)), V((-26.0, 26.35)), V((-30.0, 25.9)), V((-33.8, 25.6))]
    fill(k.road, ccw(road), G0 + 0.012)
    in_road = lambda p: inside(p, road)
    hex_lines(k.ink, ccw(road), G0, 0.62, 91, keep=0.8, origin=(-28.0, 24.4), w=0.04)
    hex_lines(k.ink, walk, G0, 0.95, 92, keep=0.32, origin=(-28.0, 24.4), avoid=in_road)
    rnd = random.Random(93)
    for edge in (road[:5], road[5:]):
        pts = []
        for p in edge:
            pts.append(p + V((0, rnd.uniform(-0.06, 0.06))))
        ground_stroke(k.ink, pts, G0, 0.08)
    cracks(k.ink, walk, G0, 10, 94, avoid=in_road)
    # drawn 'sitting places': short ink arcs around the seat stones and the villagers' spots
    for (c, rx, rz, h, s) in SEAT_STONES:
        pts = [V(c) + V((math.cos(t) * (rx + 0.35), math.sin(t) * (rz + 0.35))) for t in [i * 0.4 for i in range(12)]]
        ground_stroke(k.ink, pts, G0, 0.035)
    # tablet base: a drawn slab under it
    tb = V(GATE_PTS['gate_stone'])
    sl = jag_poly(tb, 1.2, 0.8, 8, 95, rot=math.radians(-35))
    ground_stroke(k.ink, sl + [sl[0]], G0, 0.06)
    # construction left on the page: road guides running to the gate, ticks on the road edge, compass round the tablet
    for dz in (-1.6, 1.6):
        guide(k, V((-33.6, 24.4 + dz * 1.15)), V((-19.4, 24.6 + dz * 0.75)), G0)
    ticks_along(k, road[:5], G0, 0.6, 96, side=-1)
    compass(k, GATE_PTS['gate_stone'], 1.9, G0, 97, 0.66)
    for (c, rx, rz, rot, sd) in (((-31.4, 27.3), 1.4, 0.5, 0.3, 1), ((-23.0, 21.9), 1.2, 0.45, -0.4, 2), ((-26.4, 30.0), 1.0, 0.4, 0.1, 3)):
        smudge(k, c, rx, rz, rot, G0, 98 + sd)
    # exits
    arrow(k.ink, V((-20.0, 24.6)), (1, 0), G0, 0.9)
    arrow(k.ink, V((-28.0, 19.4)), (0, -1), G0, 0.8)
    arrow(k.ink, V((-38.9, 24.4)), (-1, 0), G0, 0.7)


CART_SHELF = [V((-28.3, 16.6)), V((-30.6, 8.0)), V((-28.0, 0.5)), V((-18.0, -4.6)), V((-8.0, -6.0))]
TOWN = [V(p) for p in [(-18.6, 21.6), (-19.4, 27.4), (-17.0, 36.0), (-9.0, 43.0), (6.0, 44.5), (19.0, 41.0), (24.5, 30.0),
                       (23.0, 15.0), (18.0, 0.0), (8.0, -8.0), (-6.0, -9.5), (-15.0, -5.0), (-19.0, 4.0), (-19.6, 14.0)]]


def strip_poly(line, w):
    left, right = [], []
    for i, p in enumerate(line):
        a = line[max(0, i - 1)]
        b = line[min(len(line) - 1, i + 1)]
        d = (b - a).normalized()
        n = V((-d.y, d.x))
        left.append(p + n * w)
        right.append(p - n * w)
    return left + list(reversed(right))


def chasm(k):
    """the abyss: a dark floor far below, the town plateau and the cart-road shelf at y = 0, drawn stone stacks rising
    out of the dark (books lying on some of them)."""
    rnd = random.Random(73)
    floor = [V((-95.0, -30.0)), V((150.0, -60.0)), V((150.0, 110.0)), V((-95.0, 75.0))]
    fill(k.abyss, ccw(floor), FLOOR, steiner=None, uv=False)
    for _ in range(60):
        p = V((rnd.uniform(-70, 10), rnd.uniform(-5, 50)))
        ground_stroke(k.hatch, [p, p + V((0.9, 1.3)) * rnd.uniform(0.6, 1.4)], FLOOR, 0.09)
    # town plateau (the painted plaza stands on it) + cart-road shelf
    town = ccw(jag(TOWN, 3.0, 0.8, 81))
    fill(k.lower, town, 0.0, steiner=grid_pts(town, 6.0, 82))
    walls(k.solid, k.ink, k.hatch, town, 0.0, FLOOR, 131, ledge=2.2, ledge_out=0.6, hatch_floor=-4.0, hatch_density=0.15,
          deep=k.dark, deep_y=-1.0, vstroke=0.3, skip=lambda a, b: (a + b).x / 2 > 12.0 and (a + b).y / 2 > 34.0)
    shelf = ccw(strip_poly(CART_SHELF, 2.6))
    fill(k.lower, shelf, 0.0, steiner=grid_pts(shelf, 4.0, 83))
    walls(k.solid, k.ink, k.hatch, shelf, 0.0, FLOOR, 132, ledge=1.6, ledge_out=0.4, hatch_floor=-4.0, hatch_density=0.3,
          deep=k.dark, deep_y=-1.0, vstroke=0.3, skip=lambda a, b: inside((a + b) / 2 + V((1.2, 0.0)), town) or inside((a + b) / 2 - V((1.2, 0.0)), town))
    for side in (1, -1):
        for i in range(len(CART_SHELF) - 1):
            a_, b_ = CART_SHELF[i], CART_SHELF[i + 1]
            d_ = (b_ - a_).normalized()
            nn = V((-d_.y, d_.x)) * 0.8 * side
            t_ = 0.0
            L_ = (b_ - a_).length
            while t_ < L_:
                sg = rnd.uniform(0.8, 2.2)
                if rnd.random() < 0.8:
                    ground_stroke(k.ink, [a_ + d_ * t_ + nn, a_ + d_ * min(L_, t_ + sg) + nn], 0.0, 0.08)
                t_ += sg + rnd.uniform(0.3, 1.0)
    # drawn stacks rising out of the abyss (some carry fallen books: the human things land everywhere)
    stacks = [((-37.6, 29.4), 0.9, G0 - 1.2, 81, [('M_BookRed', 0.0, 0.0, 20), ('M_BookGreen', 0.25, 0.2, -40)]),
              ((-36.6, 19.4), 0.8, G0 - 2.4, 82, [('M_BookBlue', 0.0, 0.0, 70), ('M_BookRed', -0.1, 0.25, 10)]),
              ((-47.4, 31.8), 1.0, G0 - 0.7, 83, [('M_BookGreen', 0.0, 0.0, -15)]),
              ((-41.6, 16.8), 0.8, G0 - 3.0, 84, [('M_BookRed', 0.0, 0.0, 50)]),
              ((-44.0, 37.0), 1.6, -1.5, 85, []), ((-52.0, 15.0), 1.4, -0.5, 86, []), ((-35.0, 36.5), 1.2, 0.8, 87, [('M_BookBlue', 0.0, 0.0, 33)]),
              ((-22.0, 38.5), 1.8, -2.0, 88, []), ((-23.0, 12.0), 1.3, -3.0, 89, []), ((-62.0, 18.0), 1.5, 1.0, 90, []),
              ((-38.0, 11.0), 1.2, -4.0, 91, [])]
    for (c, r, top, sd, books) in stacks:
        yb, cc = cairn(k, c, r, top - FLOOR, FLOOR, sd, True, 0.25 if not books and sd % 3 == 0 else 0.0)
        yb = top if books else yb
        for (m, dx, dz, yaw) in books:
            box(k.books[m], (cc.x + dx, cc.y + dz), (0.62, 0.11, 0.46), yb, yaw)
            box(k.books['M_PageWhite'], (cc.x + dx + 0.03, cc.y + dz), (0.56, 0.08, 0.40), yb + 0.015, yaw)
            yb += 0.11


def lathe_tower(k, c, r, h_body, scale=1.0, painted_from=0.35, yaw=0.0, seed=0):
    """cheap painted tower silhouette: paper lower part, terracotta upper, dark dome, two chimneys, window strokes."""
    seg = 12
    rnd = random.Random(seed)
    r *= scale
    h_body *= scale
    rings = [(0.0, r), (h_body * painted_from, r), (h_body, r * 0.97), (h_body + 0.25 * scale, r * 1.06), (h_body + 0.5 * scale, r * 0.9)]
    vr = []
    for (y, rr) in rings:
        ring = []
        for i in range(seg):
            a = 2 * math.pi * i / seg
            ring.append((c[0] + math.cos(a) * rr, c[1] + math.sin(a) * rr, y))
        vr.append(ring)
    for ri in range(len(rings) - 1):
        bm = k.solid if ri == 0 else (k.terra if ri < 2 else k.terrad)
        for i in range(seg):
            j = (i + 1) % seg
            a0, a1 = vr[ri][i], vr[ri][j]
            b0, b1 = vr[ri + 1][i], vr[ri + 1][j]
            mid = V(((a0[0] + a1[0]) / 2 - c[0], (a0[1] + a1[1]) / 2 - c[1]))
            q = [bm.verts.new(B(*a0[:2], a0[2])), bm.verts.new(B(*a1[:2], a1[2])), bm.verts.new(B(*b1[:2], b1[2])), bm.verts.new(B(*b0[:2], b0[2]))]
            add_face(bm, q, V((-mid.x, -mid.y, 0)))
    # dome
    top_y = h_body + 0.5 * scale
    dr = r * 0.9
    prev = vr[-1]
    for k2 in range(1, 4):
        t = k2 / 4
        rr = dr * math.cos(t * math.pi / 2)
        yy = top_y + dr * 0.85 * math.sin(t * math.pi / 2)
        ring = [(c[0] + math.cos(2 * math.pi * i / seg) * rr, c[1] + math.sin(2 * math.pi * i / seg) * rr, yy) for i in range(seg)]
        for i in range(seg):
            j = (i + 1) % seg
            q = [k.terrad.verts.new(B(*prev[i][:2], prev[i][2])), k.terrad.verts.new(B(*prev[j][:2], prev[j][2])),
                 k.terrad.verts.new(B(*ring[j][:2], ring[j][2])), k.terrad.verts.new(B(*ring[i][:2], ring[i][2]))]
            add_face(k.terrad, q, V((0, 0, 1)))
        prev = ring
    apex = k.terrad.verts.new(B(c[0], c[1], top_y + dr * 0.85))
    for i in range(seg):
        j = (i + 1) % seg
        add_face(k.terrad, [k.terrad.verts.new(B(*prev[i][:2], prev[i][2])), k.terrad.verts.new(B(*prev[j][:2], prev[j][2])), apex], V((0, 0, 1)))
    for (dx, dz) in ((0.35, 0.2), (-0.3, 0.3)):
        box(k.terrad, (c[0] + dx * r, c[1] + dz * r), (0.45 * scale, 2.2 * scale, 0.45 * scale), top_y + dr * 0.3, yaw)
    # windows: arched ink strokes on the camera side (west)
    for i in range(3):
        a = math.radians(160 + i * 25)
        p = V((c[0] + math.cos(a) * (r + 0.03), c[1] + math.sin(a) * (r + 0.03)))
        y0 = h_body * (0.55 + 0.12 * (i % 2))
        pts = [B(p.x, p.y, y0), B(p.x, p.y, y0 + 0.9 * scale)]
        stroke3(k.ink, pts, 0.12 * scale)
    stroke3(k.ink, [B(c[0] + math.cos(math.radians(a)) * (r + 0.02), c[1] + math.sin(math.radians(a)) * (r + 0.02), h_body * painted_from + rnd.uniform(-0.1, 0.1)) for a in range(100, 270, 15)], 0.06)


def vista_town(k):
    """the painted plaza and stage seen from the fall/gate, cheap (real positions; stage turned to face the pass)."""
    pc = V((0.0, 10.0))
    disc = [pc + V((math.cos(2 * math.pi * i / 28) * 17.5, math.sin(2 * math.pi * i / 28) * 17.5)) for i in range(28)]
    fill(k.plaza, ccw(disc), 0.02)
    rnd = random.Random(101)
    R = 1.25
    for j in range(-8, 9):
        for i in range(-8, 9):
            cx = pc.x + i * math.sqrt(3) * R + (math.sqrt(3) * R / 2 if j % 2 else 0)
            cz = pc.y + j * 1.5 * R
            if (V((cx, cz)) - pc).length > 16.5 or rnd.random() < 0.55:
                continue
            hexp = [V((cx + 0.92 * R * math.cos(math.radians(60 * t + 30)), cz + 0.92 * R * math.sin(math.radians(60 * t + 30)))) for t in range(6)]
            fill(k.stones, ccw(hexp), 0.035, uv=False)
    stroke3(k.ink, [B(pc.x + math.cos(2 * math.pi * i / 40) * 17.6, pc.y + math.sin(2 * math.pi * i / 40) * 17.6, 0.06) for i in range(41)], 0.14)
    # low painted balustrade arc on the west rim (reads as 'the finished place')
    for i in range(10):
        a0 = math.radians(150 + i * 6.5)
        a1 = math.radians(150 + (i + 1) * 6.5 - 1.5)
        p0 = pc + V((math.cos(a0), math.sin(a0))) * 18.0
        p1 = pc + V((math.cos(a1), math.sin(a1))) * 18.0
        mid = (p0 + p1) / 2
        box(k.terra, (mid.x, mid.y), ((p1 - p0).length, 0.9, 0.35), 0.0, math.degrees(math.atan2(p1.x - p0.x, p1.y - p0.y)) - 90)
    # stage: wooden base, painted frame, red curtains, navy backdrop with tiny lit windows; faces yaw SY (toward the pass)
    sc, SY = V((0.0, 20.4)), 248.0
    cs, sn = math.cos(math.radians(SY)), math.sin(math.radians(SY))

    def W(lx, lz):
        return (sc.x + lx * cs + lz * sn, sc.y - lx * sn + lz * cs)
    box(k.stage, W(0, 0), (7.0, 1.3, 4.2), 0.0, SY)
    box(k.stage, W(0, 2.4), (3.0, 0.45, 0.7), 0.0, SY)               # front steps
    box(k.stage, W(0, 2.9), (2.2, 0.22, 0.5), 0.0, SY)
    box(k.terra, W(-3.2, -1.6), (0.7, 5.2, 0.7), 1.3, SY)             # frame posts
    box(k.terra, W(3.2, -1.6), (0.7, 5.2, 0.7), 1.3, SY)
    box(k.terrad, W(0, -1.6), (7.4, 0.9, 0.8), 6.0, SY)               # top beam
    box(k.navy, W(0, -1.95), (5.8, 4.7, 0.12), 1.3, SY)               # backdrop
    box(k.curtain, W(-2.25, -1.45), (1.3, 4.6, 0.25), 1.35, SY)
    box(k.curtain, W(2.25, -1.45), (1.3, 4.6, 0.25), 1.35, SY)
    box(k.curtain, W(0, -1.4), (5.6, 0.8, 0.22), 5.15, SY)            # valance
    for i in range(6):
        lx = -2.0 + i * 0.8
        box(k.glow, W(lx, -1.85), (0.18, 0.26, 0.05), 2.0 + (i % 2) * 0.5, SY)
    box(k.glow, W(0.6, -1.86), (0.6, 0.6, 0.05), 4.0, SY)            # moon
    for lx in (-3.2, 3.2):
        box(k.glow, W(lx, -1.0), (0.3, 0.42, 0.3), 5.0, SY)          # lamps
    # finished white wall with arches behind the stage + a painted stair (concept)
    for (x0, x1, z) in ((-10.0, -4.5, 26.8), (4.5, 12.0, 27.2)):
        box(k.solid, ((x0 + x1) / 2, z), (x1 - x0, 3.4, 0.9), 0.0, 0)
        for t in range(int((x1 - x0) / 2.4)):
            ax = x0 + 1.2 + t * 2.4
            pts = [B(ax - 0.6, z - 0.47, 0.05), B(ax - 0.6, z - 0.47, 1.6)] + [B(ax + 0.6 * math.cos(math.pi - math.pi * u / 6), z - 0.47, 1.6 + 0.6 * math.sin(math.pi * u / 6)) for u in range(7)] + [B(ax + 0.6, z - 0.47, 0.05)]
            stroke3(k.ink, pts, 0.07)
    for i in range(7):
        box(k.stage, (-3.0 + 0.0, 24.6 + i * 0.35), (1.6, 0.48 * (i + 1), 0.35), 0.0, 0)
    # towers (real dressing places; west one moved to (-12, 30) so it belongs to the plaza page)
    lathe_tower(k, (-12.0, 30.0), 2.9, 5.6, 1.1, 0.4, seed=1)
    lathe_tower(k, (17.0, 30.0), 2.9, 5.6, 1.25, 0.3, seed=2)
    lathe_tower(k, (30.0, 40.0), 2.9, 5.6, 0.9, 0.25, seed=3)
    lathe_tower(k, (-6.0, 34.0), 2.2, 7.5, 1.0, 0.45, seed=4)
    lathe_tower(k, (9.0, 36.5), 2.5, 6.5, 1.0, 0.35, seed=5)
    # a few half-painted houses toward the alley / beyond
    for (c, sz, ph, hh) in (((14.0, 20.0), 3.4, 0.5, 4.2), ((20.0, 33.0), 3.6, 0.3, 5.0), ((26.0, 20.5), 3.2, 0.6, 3.8), ((-15.5, 2.0), 3.0, 0.0, 3.4),
                            ((-11.0, -4.0), 2.8, 0.2, 3.0), ((-14.0, 38.0), 3.0, 0.15, 4.4), ((12.0, 40.0), 3.2, 0.45, 4.8)):
        box(k.solid, c, (sz, hh * (1 - ph) + 0.01, sz * 0.8), 0.0, 15)
        if ph > 0:
            box(k.terra, c, (sz * 1.01, hh * ph, sz * 0.81), hh * (1 - ph), 15)
        # gable roof (prism), painted if the house is painted, else paper
        cs_, sn_ = math.cos(math.radians(15)), math.sin(math.radians(15))
        Wf = lambda lx, lz: V((c[0] + lx * cs_ + lz * sn_, c[1] - lx * sn_ + lz * cs_))
        bm = k.terrad if ph > 0 else k.solid
        e = [Wf(-sz * 0.56, -sz * 0.46), Wf(sz * 0.56, -sz * 0.46), Wf(sz * 0.56, sz * 0.46), Wf(-sz * 0.56, sz * 0.46)]
        r0, r1 = Wf(-sz * 0.56, 0), Wf(sz * 0.56, 0)
        vv = [bm.verts.new(B(p.x, p.y, hh)) for p in e]
        rv = [bm.verts.new(B(r0.x, r0.y, hh + sz * 0.45)), bm.verts.new(B(r1.x, r1.y, hh + sz * 0.45))]
        add_face(bm, [vv[0], vv[1], rv[1], rv[0]], None)
        add_face(bm, [vv[2], vv[3], rv[0], rv[1]], None)
        add_face(bm, [vv[0], rv[0], vv[3]], None)
        add_face(bm, [vv[1], vv[2], rv[1]], None)
        stroke3(k.ink, [rv[0].co, rv[1].co], 0.12)
        dpos = Wf(-sz * 0.2, -sz * 0.41)
        stroke3(k.ink, [B(dpos.x, dpos.y, 0.05), B(dpos.x, dpos.y, 1.6), B((dpos + Wf(0.7, 0) - Wf(0, 0)).x, (dpos + Wf(0.7, 0) - Wf(0, 0)).y, 1.6),
                        B((dpos + Wf(0.7, 0) - Wf(0, 0)).x, (dpos + Wf(0.7, 0) - Wf(0, 0)).y, 0.05)], 0.1)
    # lamp posts as ink + glow
    for (x, z) in ((-12.0, 6.0), (-6.0, 12.0), (6.0, 12.0)):
        stroke3(k.ink, [B(x, z, 0.0), B(x, z, 2.9)], 0.1)
        box(k.glow, (x, z), (0.3, 0.4, 0.3), 2.7, 0)


def vista_town_now(k):
    """slice-2 polish (10/23): the plaza seen from the fall / gate is the real new plaza (ouat_slice2.vista_plaza)."""
    try:
        import ouat_slice2 as SL2
    except Exception:
        return vista_town(k)
    SL2.vista_plaza(k)


def vista_spires(k, origin, yaw_c, seed):
    """blue-grey spire backdrop, rising from below so their bodies sit inside the low camera's frame."""
    rnd = random.Random(seed)
    for i in range(18):
        yaw = math.radians(yaw_c + rnd.uniform(-36, 36))
        d = rnd.uniform(80, 128)
        c = V(origin) + V((math.sin(yaw), math.cos(yaw))) * d
        if c.x < 30:
            continue
        hgt = rnd.uniform(30, 52)
        base_y = FLOOR - 2.0
        r = hgt * rnd.uniform(0.11, 0.16)
        sides = rnd.choice((4, 5, 6))
        a0 = rnd.uniform(0, 1)
        base = [k.spire.verts.new(B(c.x + math.cos(a0 + 2 * math.pi * s / sides) * r, c.y + math.sin(a0 + 2 * math.pi * s / sides) * r, base_y)) for s in range(sides)]
        tip = k.spire.verts.new(B(c.x + rnd.uniform(-0.6, 0.6), c.y + rnd.uniform(-0.6, 0.6), base_y + hgt))
        for s in range(sides):
            add_face(k.spire, [base[s], base[(s + 1) % sides], tip], None)
    bmesh.ops.recalc_face_normals(k.spire, faces=k.spire.faces)


# --------------------------------------------------------------------------------------------- parts
def kit_to_part(part, k, which, vista=False):
    m = {'walk': 'M_UnderGround', 'road': 'M_UnderRoad', 'margin': 'M_UnderGround', 'solid': 'M_UnderCliff', 'ink': 'M_Ink', 'hatch': 'M_HatchDark',
         'sketch': 'M_SketchLine', 'beam': 'M_Beam', 'paint': 'M_PaintBlue', 'paintr': 'M_PaintRed', 'dark': 'M_UnderDeep', 'wood': 'M_Wood',
         'terra': 'M_VistaTerracotta', 'terrad': 'M_VistaTerraDark', 'stage': 'M_VistaWood', 'curtain': 'M_VistaCurtain',
         'navy': 'M_VistaNavy', 'glow': 'M_LampGlow', 'plaza': 'M_VistaPlaza', 'stones': 'M_VistaStone', 'spire': 'M_UnderSpire',
         'lower': 'M_UnderLow', 'abyss': 'M_Abyss', 'cave': 'M_CaveWall', 'torn': 'M_TornEdge', 'smudge': 'M_Smudge', 'pool': 'M_LightPool', 'dust': 'M_Dust'}
    if vista:
        m.update({'walk': 'M_VistaGround', 'margin': 'M_VistaGround', 'road': 'M_VistaGround', 'solid': 'M_VistaCliff'})
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
            fm = (lambda c, n: 'M_VistaGround' if n.z > 0.7 else None) if vista else (lambda c, n: 'M_UnderGround' if n.z > 0.7 else None)
        part.add(bm, m[w], smooth=False, face_mat=fm)


def exit_marker(part_name, pos, d, y, paint='M_PaintBlue', pen=True):
    ep = Part(part_name)
    k = Kit()
    p = V(pos)
    d = V(d).normalized()
    n = V((-d.y, d.x))
    arrow(k.ink, p + d * 0.4, d, y, 0.8)
    rnd = random.Random(int(abs(p.x * 7 + p.y * 3)))
    for side in (1, -1):
        t = 0.0
        while t < 5.0:
            ln = max(0.25, 1.0 - t * 0.12)
            if rnd.random() < 1.0 - t / 6.0:
                a = p + d * t + n * 1.15 * side
                b = p + d * (t + ln) + n * (1.15 + 0.06 * t) * side
                ground_stroke(k.ink, [a, b], y, 0.06)
            t += ln + 0.3
    if pen:
        pennant(k.solid, k.paint if paint == 'M_PaintBlue' else k.paintr, k.ink, p + n * 1.35, y, h=2.0, d=d)
    kit_to_part(ep, k, ('solid', 'ink', 'paint', 'paintr'))
    return ep


VISTA_KEYS = ('walk', 'margin', 'road', 'solid', 'dark', 'torn', 'lower', 'abyss', 'plaza', 'stones', 'stage', 'terra', 'terrad', 'curtain', 'navy',
              'glow', 'paint', 'paintr', 'spire', 'cave', 'ink', 'hatch', 'sketch', 'smudge', 'books')


def build_slice(A):
    """Add Area_a_fall and Area_a_gate parts to the Level asset A (ouat_lib.Asset)."""
    # ---------------- a_fall
    A.empty('Area_a_fall', (0, 0, 0))
    k = Kit()
    mesa_fall(k, True)
    fall_lines(k)
    fall_rocks(k)
    gw = Part('Ground_Walk_fall'); kit_to_part(gw, k, ('walk',)); A.part(gw, parent='Area_a_fall')
    mg = Part('Margin_fall'); kit_to_part(mg, k, ('margin',)); A.part(mg, parent='Area_a_fall')
    gl = Part('Ground_Lines_fall'); kit_to_part(gl, k, ('road', 'ink', 'hatch', 'sketch', 'smudge')); A.part(gl, parent='Area_a_fall')
    cl = Part('Cliffs_fall'); kit_to_part(cl, k, ('solid', 'dark', 'torn', 'wood', 'paint')); A.part(cl, parent='Area_a_fall')
    lk = Kit()
    light_pool(lk, HEAP, 3.9, lambda p: hill_h(p))
    beam(lk, HEAP, 2.3, 3.6, H_HI + 0.02, 30.0)
    dust(lk, HEAP, 2.2, H_HI + 0.3, H_HI + 12.0, 70, 5)
    lp = Part('Light_fall'); kit_to_part(lp, lk, ('pool', 'beam', 'dust')); A.part(lp, parent='Area_a_fall')
    ex = AREA_FALL['exits'][0]
    ep = exit_marker('Exit_fall_gate', ex['pos'], (0.79, 0.61), G0, pen=False)
    A.part(ep, pivot=tuple(B(ex['pos'][0], ex['pos'][1], G0)), parent='Area_a_fall')
    vk = Kit()
    gate_plateau(vk, real=False)
    vk.sketch = bmesh.new()      # the far copy of the pass: no pencil construction (reads as noise at 30 m)
    chasm(vk)
    vista_town_now(vk)
    vista_spires(vk, (-55.0, 30.0), 100, 7)
    cave(vk, (-55.0, 30.0), 100, 17)
    # pennant at the bar stump: the only painted thing at the edge besides the ladder
    pennant(vk.solid, vk.paint, vk.ink, V((-44.59, 22.33)), G0 + 1.3, h=1.6, d=(0.79, 0.61))
    vs = Part('Vista_fall'); kit_to_part(vs, vk, VISTA_KEYS, vista=True); A.part(vs, parent='Area_a_fall')
    # ---------------- a_gate
    A.empty('Area_a_gate', (0, 0, 0))
    k = Kit()
    gate_plateau(k, True)
    gate_lines(k)
    gw = Part('Ground_Walk_gate'); kit_to_part(gw, k, ('walk',)); A.part(gw, parent='Area_a_gate')
    mg = Part('Margin_gate'); kit_to_part(mg, k, ('margin',)); A.part(mg, parent='Area_a_gate')
    gl = Part('Ground_Lines_gate'); kit_to_part(gl, k, ('road', 'ink', 'hatch', 'sketch', 'smudge')); A.part(gl, parent='Area_a_gate')
    cl = Part('Cliffs_gate'); kit_to_part(cl, k, ('solid', 'dark', 'torn', 'paint', 'paintr')); A.part(cl, parent='Area_a_gate')
    for ex, d, pen in ((AREA_GATE['exits'][0], (-1, 0), True), (AREA_GATE['exits'][1], (1, 0), False), (AREA_GATE['exits'][2], (0, -1), False)):
        t = ex['to'][2:]
        ep = exit_marker(f'Exit_gate_{t}', ex['pos'], d, G0, pen=pen)
        A.part(ep, pivot=tuple(B(ex['pos'][0], ex['pos'][1], G0)), parent='Area_a_gate')
    vk = Kit()
    mesa_fall(vk, False)
    vk.sketch = bmesh.new()
    pennant(vk.solid, vk.paint, vk.ink, V((-44.59, 22.33)), G0 + 1.3, h=1.6, d=(0.79, 0.61))
    chasm(vk)
    vista_town_now(vk)
    vista_spires(vk, (-28.0, 25.0), 96, 9)
    cave(vk, (-28.0, 25.0), 96, 19)
    vs = Part('Vista_gate'); kit_to_part(vs, vk, VISTA_KEYS, vista=True); A.part(vs, parent='Area_a_gate')


# --------------------------------------------------------------------------------------------- data for the main agent
def patch_areas(areas):
    """replace a_fall / a_gate in a chapter1.json areas[] list and update spawns of exits into them."""
    for i, a in enumerate(areas):
        if a['id'] == 'a_fall':
            areas[i] = json.loads(json.dumps(AREA_FALL))
        elif a['id'] == 'a_gate':
            areas[i] = json.loads(json.dumps(AREA_GATE))
    for a in areas:
        for ex in a['exits']:
            key = (a['id'], ex['to'])
            if key in EXITS_INTO:
                ex.update(EXITS_INTO[key])
    return areas


def patch_ch1(d):
    """apply the slice positions to a loaded chapter1.json dict (for Blender-side previews/keepouts)."""
    patch_areas(d['areas'])
    P = dict(FALL_PTS)
    P.update(GATE_PTS)
    for z in d['zones']:
        if z['id'] in P:
            z['pos'] = list(P[z['id']])
    for p in d['props']:
        if p['id'] in P:
            p['pos'] = list(P[p['id']])
    for ins in d['inscriptions']:
        if ins['id'] in P:
            ins['pos'] = list(P[ins['id']])
    for pz in d['puzzles']:
        if pz['id'] in P:
            pz['pos'] = list(P[pz['id']])
        if pz['id'] == 'pz_bolt_fall':
            pz['pos'] = list(P['bolt_fall'])
    for n in d['npcs']:
        if n['id'] == 'kinopio':
            n['spawn'] = list(FALL_PTS['z_kid_pile'])
        elif n['id'] in GATE_PTS:
            n['spawn'] = list(GATE_PTS[n['id']])
            if n['id'] in GATE_FACING:
                n['facing'] = GATE_FACING[n['id']]
    for ph in d['phases']:
        for nid, v in ph['npcs'].items():
            if nid in ('gate_a', 'gate_b', 'crowd_gate') and isinstance(v.get('at'), list) and v['at'][0] < -18:
                v['at'] = list(GATE_PTS[nid])
    for pl in d['places']:
        if pl['id'] in PLACE_CENTERS:
            pl['center'], pl['radius'] = PLACE_CENTERS[pl['id']]
    return d


# placeholder kit pieces (art/layout_dressing.json, area a_fall / a_gate). The props agent may swap the models.
SLICE_DRESSING = [
    # a_fall: stairs drawn into nothing toward the light, scraps blown about, a dead drawn tree on the rim, a sketched fence on the landing
    ('Stair_Sketch', -56.2, 36.3, 170, 0.9, 'a_fall', 'stairs that stop in the air, rising toward the light (left edge, never between camera and hero)'),
    ('Sketch_Tree_3', -51.0, 34.4, 30, 1.0, 'a_fall', 'dead drawn tree on the north-east rim: frames the view to the gate'),
    ('Scrap_Paper_2', -58.9, 26.2, 40, 1.1, 'a_fall', ''), ('Scrap_Paper_1', -52.3, 31.2, 0, 1.0, 'a_fall', ''),
    ('Scrap_Paper_3', -56.6, 36.3, 200, 1.0, 'a_fall', ''), ('Scrap_Paper_3', -54.6, 20.6, 110, 1.0, 'a_fall', 'on the shelf below the cleft'),
    ('Sketch_Fence_1', -50.9, 18.85, 27, 1.0, 'a_fall', 'drawn fence along the shelf edge (south)'),
    # a_gate: the gate lantern (only warm light of the pass, pulls the eye to the exit), a drawn arch window wall in the margin,
    # a drawn tree on the chasm rim, scraps, rubble, a crate by the gate (sign of the finished town ahead)
    ('Lantern_Hanging', -22.1, 21.75, 300, 1.0, 'a_gate', 'warm light at the south gate pillar: point light needed'),
    ('Sketch_Wall_2', -19.4, 32.6, 250, 1.0, 'a_gate', 'unfinished arched wall behind the north pillar'),
    ('Sketch_Tree_1', -33.3, 32.6, 120, 1.0, 'a_gate', 'drawn tree on the chasm rim (left)'),
    ('Scrap_Paper_2', -30.4, 26.9, 15, 1.0, 'a_gate', ''), ('Scrap_Paper_3', -25.2, 29.2, 300, 1.0, 'a_gate', ''),
    ('Rubble_2', -23.4, 32.9, 80, 0.9, 'a_gate', ''), ('Crate', -21.6, 21.9, 20, 1.0, 'a_gate', ''),
]


def patch_dressing_json(path=None):
    """replace a_fall / a_gate items in art/layout_dressing.json and drop any other item standing inside the slice footprint."""
    path = path or os.path.join(ART, 'layout_dressing.json')
    d = json.load(open(path, encoding='utf-8'))
    keep = [it for it in d['items'] if it.get('area') not in ('a_fall', 'a_gate') and not in_footprint(it['pos'])]
    for (m, x, z, yaw, sc, area, note) in SLICE_DRESSING:
        it = {'model': m, 'pos': [x, z], 'yaw': yaw, 'scale': sc, 'place': area[2:], 'area': area}
        if note:
            it['note'] = note
        keep.append(it)
    d['items'] = keep
    d['count'] = len(keep)
    json.dump(d, open(path, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
    return len(keep)


def write_layout_json(path=None):
    path = path or os.path.join(ART, 'layout_slice1.json')
    r2 = lambda v: [round(x, 2) for x in v]
    P = dict(FALL_PTS)
    P.update(GATE_PTS)
    ladder_top = [RAMP_T.x, H_LO, RAMP_T.y]
    ladder_bot = [RAMP_B.x, G0, RAMP_B.y]
    span = math.sqrt((RAMP_B.x - RAMP_T.x) ** 2 + (G0 - H_LO) ** 2 + (RAMP_B.y - RAMP_T.y) ** 2)
    ramp_yaw = round(math.degrees(math.atan2(RAMP_B.x - RAMP_T.x, RAMP_B.y - RAMP_T.y)), 1)
    out = {
        '_doc': '1차 슬라이스(10/23) 빛구멍 언덕(a_fall) · 앉은돌 길목(a_gate) 디오라마 배치. 좌표 = Unity 월드 [x, z] (높이는 아래로 쏘는 레이캐스트; '
                'ladder_top/bottom만 [x, y, z]). areas[] = chapter1.json areas[]와 같은 형식, a_fall·a_gate를 통째로 바꿈. exits_into = 다른 구역 출구의 spawn/face 고침. '
                'positions = chapter1.json 같은 id 항목의 pos/spawn/facing/phase 자리에 덮어씀. 각도 = 도(0 = +Z). 생성: art/blender/ouat_slice.py write_layout_json().',
        'hilltop_height': H_HI, 'hilltop_terraces': {'heap_dais': H_HI, 'middle': H_MID, 'ladder_shelf': H_LO,
                                                     'note': '언덕 윗면은 세 단(0.4·0.5m 턱, NavMesh 오를 수 있음). 빛줄기·LightShaft 바닥 = 5.5, 사다리 머리 = 4.6'},
        'landing_height': G0, 'gate_height': G0, 'abyss_floor': FLOOR,
        'ladder_top': r2(ladder_top), 'ladder_bottom': r2(ladder_bot), 'ladder_span_m': round(span, 2), 'ladder_yaw': ramp_yaw,
        'ladder_scale_length_only': round(span / 3.1, 2),
        'ladder_note': '편 사다리 3.1m → 비탈 6.36m: 길이 방향(로컬 Y)만 2.05배 권장(폭은 1~1.15배). 주의: SceneBuilder의 LookRotation(Cross(side, down), down)은 '
                       '사다리 앞(+Z, 놋쇠 걸쇠)이 비탈 속을 향함 → Cross(down, side)로 바꿔야 걸쇠가 위로 보이고 사다리가 비탈 위에 얹힘(미리보기는 이렇게 함). '
                       '비탈 경사 19도(카메라 시선보다 완만해서 언덕 위에서 보임).',
        'ladder_blocker': {'pos': r2([(RAMP_T.x + RAMP_B.x) / 2, (H_LO + G0) / 2 - 1.2, (RAMP_T.y + RAMP_B.y) / 2]), 'size': [2.2, 3.0, round(span, 2)],
                           'yaw': ramp_yaw, 'note': 'NavMeshObstacle 상자(가로·높이·길이, 길이 = yaw 방향). 사다리가 펴지기 전 비탈을 막음'},
        'bolt_fall': {'pos': r2(P['bolt_fall']), 'yaw': FALL_FACING['bolt_fall'], 'path_dir_yaw': FALL_FACING['bolt_fall'],
                      'note': 'DrawnBar 앞(+Z)이 길 방향을 보게 yaw 57 → 막대(로컬 X)가 길을 가로지름. 길 목 폭 약 2.2m(좌우 바위 그루터기). '
                              'Blocker 2.6×2.5×1.2도 같은 yaw. (기존 YawToward(at, gate)+90은 막대가 길과 나란해짐)'},
        'gap': {'pos': r2(P['z_fall_gap']), 'below': r2(FALL_PTS['kid_cleft_exit']),
                'note': '틈은 언덕 남쪽 가장자리 지형에 새김(0.35m 홈 + 검은 틈). Gap.fbx는 놓지 않음. 키노피오: z_fall_gap까지 걸음 → below로 순간이동(또는 바로 kid_wait_below) → 아래 선반을 따라 빗장까지'},
        'kid_wait_below': r2(FALL_PTS['kid_wait_below']), 'kid_wait_facing': 320,
        'kid_greet_gate': r2(GATE_PTS['kid_greet']),
        'areas': [AREA_FALL, AREA_GATE],
        'exits_into': [{'area': a, 'to': t, **v} for (a, t), v in EXITS_INTO.items()],
        'places': {k: {'center': v[0], 'radius': v[1]} for k, v in PLACE_CENTERS.items()},
        'positions': {
            'zones': {k: r2(P[k]) for k in ('z_hero_start', 'z_kid_pile', 'z_fall_gap', 'z_ladder', 'z_fall_bolt', 'z_gate_stone', 'z_chief_gate')},
            'zone_radius': {'z_kid_pile': 2.0, 'z_fall_gap': 0.8, 'z_ladder': 1.2, 'z_fall_bolt': 1.2, 'z_gate_stone': 1.4, 'z_chief_gate': 1.5},
            'props': {k: {'pos': r2(P[k]), **({'facing': FALL_FACING[k]} if k in FALL_FACING else {}), **({'facing': GATE_FACING[k]} if k in GATE_FACING else {})}
                      for k in ('fall_pile', 'light_beam', 'ladder', 'bolt_fall', 'look_book', 'look_umbrella', 'look_clock', 'gate_stone')},
            'npcs': {'kinopio': {'spawn': r2(FALL_PTS['z_kid_pile']), 'facing': FALL_FACING['kinopio']},
                     'chief': {'spawn': r2(GATE_PTS['chief']), 'facing': GATE_FACING['chief']},
                     'gate_a': {'spawn': r2(GATE_PTS['gate_a']), 'facing': GATE_FACING['gate_a']},
                     'gate_b': {'spawn': r2(GATE_PTS['gate_b']), 'facing': GATE_FACING['gate_b']},
                     'crowd_gate': {'spawn': r2(GATE_PTS['crowd_gate']), 'facing': GATE_FACING['crowd_gate'], 'count': 4,
                                    'note': '4명을 ±1.6(x)·±1.2(z) 고리로 둘러 앉히면 모두 걷는 땅 안'}},
            'phases': {'P0_intro': {'gate_a': r2(GATE_PTS['gate_a']), 'gate_b': r2(GATE_PTS['gate_b']), 'crowd_gate': r2(GATE_PTS['crowd_gate'])},
                       'P2_free': {'gate_a': r2(GATE_PTS['gate_a']), 'gate_b': r2(GATE_PTS['gate_b'])}},
            'inscriptions': {'ins_gate': r2(GATE_PTS['ins_gate'])},
            'puzzles': {'pz_ladder': r2(FALL_PTS['pz_ladder']), 'pz_bolt_fall': r2(FALL_PTS['bolt_fall'])},
        },
        'fall_junk': [{'model': m, 'pos': [x, z], 'yaw': y, 'scale': s_} for (m, x, z, y, s_) in FALL_JUNK],
        'game_camera': {'a_fall': CAM_FALL, 'a_gate': CAM_GATE, 'pivot_rect_fall': list(PIVOT_FALL), 'pivot_rect_gate': list(PIVOT_GATE),
                        'note': 'bounds = 피벗 범위 + 4m(FollowCamera가 4m 안쪽으로 묶음). 카메라 배경색 권장 9A9C9C(빈 곳이 밝은 종이로 튀지 않게)'},
        'lights': {
            'key': {'euler': [55, -35, 0], 'color': 'C9CFD8', 'intensity_hint': '지금 0.95 → 0.55~0.7(어둑하게, 윗면이 툰 그늘 단에 오도록)'},
            'ambient': {'color': '8E96A3', 'note': '평면 앰비언트 9DA6B1 → 8E96A3 정도로 낮춤. 수직 그늘 면이 깊은 그늘 단에 들어가야 절벽이 어두워짐'},
            'shaft_spot': {'pos': [HEAP.x, 30.0, HEAP.y], 'target': [HEAP.x, H_HI, HEAP.y], 'spot_angle': 17, 'color': 'FFE9C4',
                           'note': '챕터에서 가장 밝은 곳. 반경 ~3.7m가 더미 단을 덮음. 그림자 켬'},
            'gate_lantern': {'pos_from_dressing': 'Lantern_Hanging (-22.1, 21.75)', 'intensity_hint': '작게(범위 4m), 따뜻한 색 = 출구 쪽 눈길'},
            'town_glow': 'Vista의 무대 등·광장 등에 작은 점광원 2~3개(약하게): 문 너머 목적지가 따뜻하게',
            'light_fall_part': 'Level의 Light_fall = 빛 웅덩이(M_LightPool, UV v 중심0→가장자리1) + 빛줄기(M_Beam, UV v 바닥0→천장1) + 먼지(M_Dust). 그림자 끄기',
        },
        'scenebuilder_notes': [
            'MesaHeight 1.5 → 언덕 5.5(더미 단). LightShaft는 Light_fall/빛줄기로 대체(기존 10m 원뿔은 화면 전체를 뿌옇게 덮음) — 쓰려면 0.45배 정도',
            'ladder: top/bottom = ladder_top/ladder_bottom, 길이만 ladder_scale_length_only 배, 앞 방향 Cross(down, side)',
            'Gap.fbx 빼기(틈은 지형), 사다리 Blocker = ladder_blocker, 빗장 yaw = bolt_fall.yaw',
            '언덕 무작위 잡동사니 30개 → fall_junk 목록',
            'BuildDressing: 길목 집 두 채(C("gate")±9) 빼기(디오라마에 짓다 만 집이 있음), 광장 서쪽 탑 plaza+(-17,18) → plaza+(-12,20)(안 그러면 길목 구역에 잡혀 문 앞을 막음)',
            'BuildZones: Place_fall/Place_gate CameraZone(우선순위 1)의 views가 areas[].camera를 덮어씀 → fall/gate 값을 game_camera와 같게 하거나 CameraZone 빼기',
            'BuildLevel: Vista_*·Light_* 그림자 끄기(콜라이더 없음은 이름 규칙상 이미 맞음), Light_*는 NavMeshModifier ignore',
            'DirectorScenes sc_kid_to_latch: kid.Warp(-41.8,0,22.9) → gap.below 또는 kid_wait_below. sc_path_open의 Shot(At("gate"))은 언덕 쪽에서 보면 Vista_fall이 보여 줌',
            '카메라 배경색 F1EEE6 → 9A9C9C 권장(지하, 빈 곳이 하얗게 튀지 않게)',
        ],
        'placeholders_used': {'a_fall': ['ItemPile(더미)', 'Junk_*', 'Ladder', 'DrawnBar', 'Stair_Sketch', 'Sketch_Tree_3', 'Scrap_Paper_1/2/3', 'Sketch_Fence_1'],
                              'a_gate': ['StoneTablet', 'Lantern_Hanging', 'Sketch_Wall_2', 'Sketch_Tree_1', 'Scrap_Paper_2/3', 'Rubble_2', 'Crate']},
    }
    json.dump(out, open(path, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
    return path
