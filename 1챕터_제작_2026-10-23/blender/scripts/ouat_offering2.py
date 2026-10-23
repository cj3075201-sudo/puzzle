# -*- coding: utf-8 -*-
"""Chapter-1 story props, batch 2 (10/23): den door, cloth cover, human trinkets, torch, cord basket / hook, Kinopio's workbench.
Same rules as ouat_offering: Blender Z up, front -Y, root = floor centre unless noted; human objects finished in original colour,
creature-made things unfinished in FORM (built shell stops at a torn edge, the rest pencil). Lines parts carry only ink / pencil."""
import math, random
import bmesh
from mathutils import Vector, Matrix
from mathutils.bvhtree import BVHTree
import ouat_lib as L
from ouat_lib import (bm_sphere, bm_tube, bm_blade, bm_box, bm_cyl, bm_lathe, bm_prism, stroke, rot, move, deform, jitter, nval)
import ouat_craft as CR
import ouat_props as P
import ouat_offering as OF
from ouat_offering import Kit, xf, put_pieces, shaving, lathe_g, ray_down

V = Vector
INK, PENCIL, SMUDGE, BACK = 'M_Ink', 'M_Pencil', 'M_Smudge', 'M_PaperBack'
PWOOD, PJOINT, RED, BLUE = 'M_PuppetWood', 'M_PuppetJoint', 'M_PaintRed', 'M_PaintBlue'
SACK, SACKD, OFFER, OFFERB = OF.SACK, OF.SACKD, OF.OFFER, OF.OFFERB
merge, line = CR.merge, CR.line

L.MATS.update({
    'M_Mirror': ('C5D3DE', '8796A5', True,  'painted', {'keep': True, 'note': 'human mirror glass (silvered face), keep. Unity: may add a fake reflection / rim light'}),
    'M_Flame':  ('FF9A3C', 'E46A1E', False, 'painted', {'emission': 1.0, 'keep': True, 'note': 'creature torch flame: unlit / emissive orange, put a small warm point light at Torch/Flame'}),
})


# ===================================================================== BarkDoor (secret den in the old tree)
def build_bark_door():
    K = Kit('BarkDoor')
    W, H = 0.78, 1.22
    nu, nv = 9, 14
    b = bmesh.new()
    rows = []
    for j in range(nv + 1):
        z = H * j / nv
        row = []
        for i in range(nu + 1):
            x = -W / 2 + W * i / nu
            y = -0.07 * math.cos(math.pi * x / W) - 0.012 * abs(math.sin(x * 26 + 0.5 * math.sin(z * 4))) + nval(V((x, 0, z)), 6.0, 201) * 0.01
            row.append(b.verts.new(V((x, y, z))))
        rows.append(row)
    for j in range(nv):
        for i in range(nu):
            b.faces.new((rows[j][i], rows[j][i + 1], rows[j + 1][i + 1], rows[j + 1][i]))
    for f in b.faces:
        if f.normal.y > 0:
            f.normal_flip()
    arch = lambda c: (H - 0.32 + math.sqrt(max(0.0, (W / 2) ** 2 - c.x ** 2)) * 0.32 / (W / 2)) - c.z
    torn = lambda c: (c.x - 0.05) * -1.0 + (H - 0.42 - c.z) * 0.9 + nval(c, 7.0, 202) * 0.08
    fld = lambda c: min(arch(c), max(torn(c), 0.42 - c.z if c.z < 0.42 else -1.0))
    full = CR.copy(b)
    K.form('Door', 'Lines', b, fld, 'M_Bark', thick=0.035, zig=0.025, seed=203, back_near=None,
           hatch_kw=dict(spacing=0.05, length=(0.08, 0.25), r=0.004, slant=28, density=0.7), ink_r=0.006)
    # planned outline of the missing upper-right part: pencil arch + edge
    pa = [V((math.cos(t) * W / 2, -0.03, H - 0.32 + math.sin(t) * 0.32)) for t in [i * math.pi / 2 / 8 for i in range(9)]]
    K.add('Lines', line(pa + [V((W / 2, -0.03, H * 0.55))], 0.004, over=0.08, seed=204), PENCIL, False)
    # bark grooves (ink) on the built part
    for k in range(7):
        x = -W / 2 + 0.08 + k * 0.1
        pts = [V((x + 0.012 * math.sin(z * 9 + k), -0.07 * math.cos(math.pi * x / W) - 0.016, z)) for z in [0.05 + i * 0.1 for i in range(12)]]
        K.add('Lines', CR.clipped_lines(pts, lambda p: fld(p) > 0.04, 0.0035, 0.0, 205 + k), INK, False)
    # hinge lashings on the left edge (twine)
    for z in (0.22, 0.98):
        K.add('Door', xf(bm_tube([V((math.cos(a) * 0.035, math.sin(a) * 0.05, 0)) for a in [i * 2 * math.pi / 8 for i in range(9)]], 0.009, seg=4, cap=False),
                 rx=90, pos=(-W / 2 + 0.02, -0.04, z)), SACKD, False)
    # knot hole (finger hole / peephole): raised bark ring + dark hole
    kc = V((0.17, -0.07 * math.cos(math.pi * 0.17 / W) - 0.02, 0.72))
    ring = bm_lathe([(0.03, 0.0), (0.055, 0.012), (0.07, 0.0)], seg=12, sx=1.0, sy=1.3, cap_top=False, cap_bottom=False)
    rot(ring, 'X', 90)
    move(ring, kc)
    K.add('Knot', ring, 'M_Bark', False)
    hole = bm_cyl(kc + V((0, 0.03, 0)), kc + V((0, -0.004, 0)), 0.03, seg=10)
    L.xform(hole, Matrix.Translation(kc) @ Matrix.Diagonal((1, 1, 1.3, 1)) @ Matrix.Translation(-kc))
    K.add('Knot', hole, 'M_Ink', False)
    K.add('Lines', CR.ellipse(kc + V((0, -0.016, 0)), 0.075, 0.095, 0.0, turns=1.1, n=12, r=0.003, seed=206, tilt=('X', 90)), INK, False)
    return K.finish(1.3, "Door of Kinopio's secret den (in the old tree): a curved slab of bark 0.78 x 1.22 m, arched top. Root = floor centre under "
                         "the closed door. Door pivot = hinge on the left edge (Unity: rotate local Y to swing; front faces Unity +Z). Knot = "
                         "knot hole used as finger hole / peephole (child of Door). Unfinished: the upper-right part of the slab is torn off, "
                         "its arch only pencil.", pivots={'Door': (-W / 2, 0, 0), 'Knot': tuple(kc)}, parents={'Knot': 'Door', 'Lines': 'Door'})


# ===================================================================== ClothCover (over a seated lump)
def build_cloth_cover():
    K = Kit('ClothCover')
    Hd = 0.62
    prof = [(0.42, -0.36), (0.41, -0.2), (0.39, -0.04), (0.36, 0.06), (0.33, 0.2), (0.29, 0.34), (0.22, 0.47), (0.13, 0.57), (0.05, Hd - 0.01), (0.0, Hd)]
    b = bm_lathe(prof, seg=28, cap_top=False, cap_bottom=False)
    CR.tri_ngons(b)
    CR.orient_out(b, center=(0, 0, 0.2))

    def drape(c):
        a = math.atan2(c.y, c.x)
        r = c.xy.length
        if r < 1e-6:
            return c
        down = max(0.0, -c.z) / 0.36
        fold = 1 + (0.05 + 0.14 * down) * math.sin(a * 7 + 0.6) + 0.05 * math.sin(a * 13 + 2)
        r *= fold
        if c.z < 0.02:   # hang outside the seat (0.52 m square); behind (+Y) it tucks against the backrest
            need = 0.275 / max(abs(math.cos(a)), abs(math.sin(a)))
            r = max(r, need + 0.015)
        z = c.z
        back = max(0.0, math.sin(a))          # +Y side
        if z < 0.0:
            z = z * (1 - 0.92 * back ** 2)
        x, y = math.cos(a) * r, math.sin(a) * r
        if y > 0.24:
            y = 0.24 + (y - 0.24) * 0.15
        # the nose pokes the cloth from inside (front, a little left)
        nb = V((0.06, -0.3, 0.42))
        d = (V((x, y, z)) - nb).length
        if d < 0.12:
            y -= 0.07 * (1 - d / 0.12) ** 2
        return V((x, y, z))
    deform(b, drape)
    jitter(b, 0.008, 9.0, 211)
    fld = lambda c: (((c.x - 0.33) ** 2) / 0.02 + ((c.z - 0.12) ** 2) / 0.03 + ((c.y + 0.02) ** 2) / 0.05) - 1.0 + nval(c, 8.0, 212) * 0.3
    K.form('Cloth', 'Lines', b, fld, SACK, thick=0.012, zig=0.02, seed=213, back_near=None, smooth=True,
           hatch_kw=dict(spacing=0.04, length=(0.05, 0.14), r=0.0035, slant=25, density=0.6, up_only=False), ink_r=0.005)
    # hem ink + fold strokes (drawn on the built cloth) + pencil drape lines across the open window
    hem = []
    for i in range(29):
        a = 2 * math.pi * i / 28
        hem.append(drape(V((math.cos(a) * 0.42, math.sin(a) * 0.42, -0.36))) + V((0, 0, 0.004)))
    K.add('Lines', CR.clipped_lines(hem, lambda p: fld(p) > 0.05, 0.004, 0.0, 214), INK, False)
    for k in range(9):
        a = -math.pi / 2 + (k - 4) * 0.33
        pts = [drape(V((math.cos(a) * r_ * 1.03, math.sin(a) * r_ * 1.03, z))) for r_, z in ((0.3, 0.3), (0.36, 0.08), (0.4, -0.15), (0.43, -0.3))]
        K.add('Lines', CR.clipped_lines(pts, lambda p: fld(p) > 0.05, 0.003, 0.0, 215 + k), INK, False)
    for k in range(4):
        z = 0.02 + 0.06 * k
        K.add('Lines', line([V((0.36, -0.12, z)), V((0.4, 0.05, z + 0.03)), V((0.36, 0.2, z))], 0.003, over=0.04, seed=220 + k), PENCIL, False)
    return K.finish(1.0, "Sackcloth draped over a seated lump on a chair. Root = seat top centre (same as the lumps / Chair seat 0.5 m). Covers a "
                         "body up to ~0.62 m, hangs ~0.36 m over the front and sides of a 0.52 m seat, tucked flat at the back (backrest). "
                         "A nose pokes the cloth from inside (front). Unfinished: on the right side the weave never closed - a window with "
                         "pencil drape lines.", parents={'Lines': 'Cloth'})


# ===================================================================== human trinkets (finished, original colour)
def build_music_box():
    K = Kit('MusicBox')
    W, D, H = 0.2, 0.13, 0.085
    K.add('Box', P.bbox((0, 0, H / 2 + 0.008), (W, D, H), 0.006), 'M_Wood', False)
    K.add('Box', P.bbox((0, -D / 2 - 0.001, H * 0.55 + 0.008), (W * 0.98, 0.004, 0.018), 0.0), 'M_Brass', False)
    for sx in (-1, 1):
        for sy in (-1, 1):
            K.add('Box', bm_sphere((sx * (W / 2 - 0.012), sy * (D / 2 - 0.012), 0.006), (0.009,) * 3, seg=6, rings=4), 'M_Brass', False)
            K.add('Box', P.bbox((sx * (W / 2 - 0.004), sy * (D / 2 - 0.004), H / 2 + 0.008), (0.012, 0.012, H + 0.002), 0.0), 'M_Brass', False)
    K.add('Box', P.bbox((0, 0, H + 0.004), (W - 0.016, D - 0.016, 0.006)), 'M_BookRed', False)       # red velvet inside
    K.add('Box', bm_cyl((-0.05, 0.01, H - 0.008), (0.05, 0.01, H - 0.008), 0.014, seg=8), 'M_Brass', False)   # pin cylinder
    K.add('Box', P.bbox((0, -0.025, H - 0.004), (0.11, 0.02, 0.004)), 'M_Iron', False)                       # comb
    K.add('Box', P.bbox((0, -D / 2 - 0.002, H * 0.8), (0.018, 0.004, 0.014)), 'M_Brass', False)               # keyhole plate
    # lid (pivot = back top hinge)
    hz = H + 0.008
    lid = P.bbox((0, 0, hz + 0.014), (W + 0.006, D + 0.006, 0.028), 0.006)
    K.add('Lid', lid, 'M_Wood', False)
    K.add('Lid', P.bbox((0, 0, hz + 0.029), (W * 0.7, D * 0.6, 0.004), 0.0), 'M_BookBlue', False)
    K.add('Lid', P.bbox((0, 0, hz + 0.0305), (W * 0.74, D * 0.64, 0.002), 0.0), 'M_Brass', False)
    K.add('Lid', bm_sphere((0, 0, hz + 0.033), (0.018, 0.012, 0.006), seg=8, rings=4), 'M_Porcelain', False)   # little porcelain dancer plate
    # crank on the right side (pivot = axle)
    ax = V((W / 2 + 0.004, 0.0, H * 0.5 + 0.008))
    K.add('Crank', bm_cyl(ax, ax + V((0.02, 0, 0)), 0.005, seg=6), 'M_Brass', False)
    K.add('Crank', bm_cyl(ax + V((0.02, 0, 0.0)), ax + V((0.02, 0, -0.04)), 0.004, seg=5), 'M_Brass', False)
    K.add('Crank', bm_cyl(ax + V((0.02, 0, -0.04)), ax + V((0.04, 0, -0.04)), 0.007, seg=6), 'M_Porcelain', False)
    return K.finish(0.25, "Human music box (0.2 m), finished: wooden case with brass corners and band, blue + brass lid inlay, red velvet, brass "
                          "pin cylinder and comb inside. Lid pivot = back top hinge (rotate local X to open). Crank pivot = axle on the right side "
                          "(Blender +X = Unity -X side), turns about local X.",
                    pivots={'Lid': (0, D / 2 + 0.003, hz), 'Crank': tuple(ax)}, parents={'Lid': 'Box', 'Crank': 'Box'})


def build_mirror_shard():
    K = Kit('MirrorShard')
    rnd = random.Random(231)
    outline = [(-0.1, -0.05), (-0.02, -0.075), (0.03, -0.03), (0.12, -0.045), (0.085, 0.01), (0.1, 0.05), (0.02, 0.04), (-0.04, 0.085), (-0.06, 0.02)]
    sh = bm_prism(outline, 0.0, 0.007, axis='Z')
    CR.tri_ngons(sh)
    K.add('Shard', sh, 'M_Iron', False, lambda c, n: 'M_Mirror' if n.z > 0.5 else ('M_Glass' if abs(n.z) < 0.5 else None))
    # piece of the gilt frame still on the long edge
    fr = [V((-0.1, -0.058, 0.006)), V((-0.04, -0.075, 0.007)), V((-0.02, -0.083, 0.007))]
    K.add('Shard', bm_tube(fr, 0.009, seg=5), 'M_Brass', False)
    for k in range(2):
        K.add('Shard', bm_sphere(fr[0].lerp(fr[2], 0.3 + 0.4 * k) + V((0, -0.006, 0.006)), (0.006,) * 3, seg=5, rings=3), 'M_Brass', False)
    # painted highlight streaks (reads as a mirror even in the dark) + crack lines
    for a, b_ in (((-0.05, -0.02), (0.04, 0.03)), ((-0.03, -0.035), (0.0, -0.015))):
        K.add('Shard', bm_blade([V((a[0], a[1], 0.0075)), V(((a[0] + b_[0]) / 2, (a[1] + b_[1]) / 2, 0.0075)), V((b_[0], b_[1], 0.0075))],
                                [0.002, 0.006, 0.002], thick=0.0008, up=(0, 0, 1)), 'M_EyeShine', False)
    K.add('Lines', stroke([V((0.03, -0.03, 0.008)), V((0.045, 0.0, 0.008)), V((0.02, 0.04, 0.008))], 0.0012, seg=3), INK, False)
    A = K.finish(0.25, "Human mirror shard (0.22 m), finished: silvered glass with a green glass edge and a piece of the gilt frame, painted "
                       "highlight streaks. Lies flat (tilt it in Unity to catch light).", parents={'Lines': 'Shard'})
    return A


def build_spin_top():
    K = Kit('SpinTop')
    prof = [(0.0, 0.0), (0.004, 0.006), (0.012, 0.014), (0.03, 0.034), (0.038, 0.045), (0.036, 0.055), (0.02, 0.062), (0.007, 0.064),
            (0.006, 0.09), (0.0, 0.092)]
    b = bm_lathe(prof, seg=14)

    def bands(c, n):
        if c.z < 0.009:
            return 'M_Iron'
        if c.z > 0.063:
            return 'M_Wood'
        k = int((c.z - 0.009) / 0.009)
        return ('M_BookRed', 'M_PageWhite', 'M_BookBlue', 'M_PageWhite', 'M_BookRed', 'M_Brass', 'M_BookBlue')[k % 7]
    K.add('Top', b, 'M_Wood', False, bands)
    return K.finish(0.1, "Human spinning top (9 cm), finished: painted red / white / blue bands, brass ring, iron tip. Root = tip on the floor; Top "
                         "pivot = tip (spin about local Y, wobble by tilting).")


# ===================================================================== Torch (creature, half drawn)
def flame_pieces(c, h=0.34, seed=0.0):
    rnd = random.Random(int(seed * 7) + 3)
    out = []
    for k in range(5):
        a = 2 * math.pi * k / 5 + rnd.uniform(-0.3, 0.3)
        r0 = rnd.uniform(0.03, 0.06)
        hh = h * rnd.uniform(0.6, 1.0)
        pts = [c + V((math.cos(a) * r0, math.sin(a) * r0, 0.0)), c + V((math.cos(a + 0.4) * r0 * 0.9, math.sin(a + 0.4) * r0 * 0.9, hh * 0.4)),
               c + V((math.cos(a + 0.9) * r0 * 0.4, math.sin(a + 0.9) * r0 * 0.4, hh * 0.8)), c + V((math.cos(a + 1.3) * 0.01, math.sin(a + 1.3) * 0.01, hh))]
        out.append((bm_blade(pts, [0.05, 0.05, 0.03, 0.004], thick=0.02, up=(math.cos(a), math.sin(a), 0)), 'M_Flame'))
    core = bm_sphere(c + V((0, 0, 0.07)), (0.045, 0.045, 0.09), seg=8, rings=5)
    out.append((core, 'M_LampGlow'))
    return out


def build_torch():
    K = Kit('Torch')
    Hp = 1.55
    # pole: a carved branch, built; the ground socket tripod has one built leg, two only pencil
    K.add('Pole', bm_tube([V((0, 0, 0.0)), V((0.01, 0, 0.6)), V((-0.005, 0, 1.1)), V((0, 0, Hp))], [0.04, 0.035, 0.032, 0.03], seg=7), PWOOD, True)
    K.add('Pole', bm_sphere((0.01, 0, 0.6), (0.045,) * 3, seg=7, rings=5), PJOINT, False)
    K.add('Pole', bm_tube([V((0, 0, 0.35)), V((0.18, -0.08, 0.12)), V((0.3, -0.13, 0.0))], [0.025, 0.022, 0.02], seg=6), PWOOD, True)
    for a in (110, 230):
        d = V((math.cos(math.radians(a)), math.sin(math.radians(a)), 0))
        for dz in (-0.015, 0.015):
            K.add('Lines', line([V((0, 0, 0.35 + dz)), d * 0.18 + V((0, 0, 0.12 + dz)), d * 0.32 + V((0, 0, dz))], 0.003, over=0.05, seed=241 + a + dz), PENCIL, False)
    K.add('Lines', line([V((0.0, -0.034, 0.65)), V((0.0, -0.032, 1.45))], 0.004, seed=243), INK, False)
    # basket head: rim + three built slats, the rest of the cage pencil
    hc = V((0, 0, Hp + 0.02))
    K.add('Pole', bm_tube(CR.ring_pts(0, 0, Hp + 0.12, 0.11, 12), 0.012, seg=4, cap=False), PWOOD, False)
    K.add('Pole', bm_tube(CR.ring_pts(0, 0, Hp - 0.02, 0.045, 8), 0.014, seg=4, cap=False), PWOOD, False)
    for k in range(8):
        a = 2 * math.pi * k / 8
        p0 = V((math.cos(a) * 0.045, math.sin(a) * 0.045, Hp - 0.02))
        p1 = V((math.cos(a) * 0.11, math.sin(a) * 0.11, Hp + 0.12))
        if k in (5, 6, 7):
            K.add('Pole', bm_tube([p0, p1], [0.01, 0.01], seg=4), PWOOD, False)
            K.add('Lines', stroke([p0 + V((0, 0, 0.002)), p1 + V((0, 0, 0.002))], 0.002, seg=3), INK, False)
        else:
            K.add('Lines', line([p0, p1], 0.003, over=0.04, seed=244 + k), PENCIL, False)
    # flame (pivot at its base, flicker by scaling) + ink contour strokes around it (storybook flame)
    fc = V((0, 0, Hp + 0.03))
    for b_, m_ in flame_pieces(fc, 0.36, seed=1.0):
        K.add('Flame', b_, m_, False)
    for k in range(3):
        a = k * 2.1
        pts = [fc + V((math.cos(a) * 0.08, math.sin(a) * 0.08, 0.05)), fc + V((math.cos(a + 0.6) * 0.07, math.sin(a + 0.6) * 0.07, 0.2)),
               fc + V((math.cos(a + 1.2) * 0.02, math.sin(a + 1.2) * 0.02, 0.38))]
        K.add('Flame', stroke(pts, 0.004, seg=3), INK, False)
    return K.finish(1.95, "Creature torch on a carved branch (1.95 m with flame). Unfinished: the socket tripod has one built leg and two pencil legs, "
                          "five of the eight cage slats are only pencil. Flame pivot = flame base (flicker: scale / sway); emissive M_Flame + "
                          "M_LampGlow core -> add a small warm point light at Flame.", pivots={'Flame': tuple(fc)}, parents={'Flame': 'Pole', 'Lines': 'Pole'})


# ===================================================================== CordBasket + CordHook (the red cord)
def cord_coil(c, r, turns, seed, rise=0.01, wob=0.012):
    rnd = random.Random(int(seed * 11) + 1)
    pts = []
    n = int(turns * 14)
    for i in range(n + 1):
        a = 2 * math.pi * i / 14 + seed
        rr = r * (1 + rnd.uniform(-0.12, 0.12))
        pts.append(V(c) + V((math.cos(a) * rr, math.sin(a) * rr * 0.85, rise * i / 14 + rnd.uniform(-wob, wob))))
    return pts


def build_cord_basket():
    K = Kit('CordBasket')
    R0, Hb = 0.22, 0.26
    prof = [(0.17, 0.0), (0.2, 0.06), (0.215, 0.14), (R0, Hb)]
    pr = lambda z: next((r0 + (r1 - r0) * (z - z0) / max(1e-6, z1 - z0) for (r0, z0), (r1, z1) in zip(prof[:-1], prof[1:]) if z0 <= z <= z1), R0)
    b = lathe_g([(pr(z), z) for z in [Hb * i / 7 for i in range(8)]], seg=16)
    fld = lambda p: Hb - max(0.0, math.cos(math.atan2(p.y, p.x) - math.radians(-30))) * 0.09 + nval(p, 10.0, 251) * 0.015 - p.z
    K.form('Basket', 'Lines', b, fld, PWOOD, thick=0.012, zig=0.01, seed=252, back_near=None,
           hatch_kw=dict(spacing=0.06, length=(0.03, 0.09), r=0.0035, density=0.5), ink_r=0.005)
    K.add('Basket', bm_lathe([(0.0, 0.004), (0.17, 0.004)], seg=16, cap_top=False, cap_bottom=False), PWOOD, False)
    for z in (0.05, 0.1, 0.15, 0.2):
        ring = CR.ring_pts(0, 0, z, pr(z) + 0.006, 18)
        K.add('Lines', CR.clipped_lines(ring, lambda p: fld(p) > 0.004, 0.0045, 0.0, 253 + z * 10), INK, False)
    for i in range(0, 16, 2):
        a = 2 * math.pi * (i + 0.5) / 16
        for z in (0.07, 0.17):
            p0 = V((math.cos(a) * (pr(z - 0.03) + 0.006), math.sin(a) * (pr(z - 0.03) + 0.006), z - 0.03))
            p1 = V((math.cos(a + 0.15) * (pr(z + 0.03) + 0.006), math.sin(a + 0.15) * (pr(z + 0.03) + 0.006), z + 0.03))
            if fld(p1) > 0:
                K.add('Lines', stroke([p0, p1], 0.0035, seg=3, taper=False), INK, False)
    K.add('Lines', CR.ellipse((0, 0, Hb + 0.004), R0, R0, 0.0, turns=1.06, n=16, r=0.004, seed=256), PENCIL, False)
    # red cord pile inside + strands spilling over the front rim
    for k, (rr, z, t) in enumerate(((0.15, 0.17, 1.6), (0.11, 0.2, 1.4), (0.07, 0.225, 1.2), (0.13, 0.215, 1.0))):
        K.add('Cords', bm_tube(cord_coil((0.0, 0.0, z), rr, t, 257 + k)[::2], 0.008, seg=3), OFFER, False)
    for k, (a, ln) in enumerate(((-1.75, 0.2), (-1.35, 0.13), (-2.2, 0.16))):
        d = V((math.cos(a), math.sin(a), 0))
        top = d * (R0 + 0.005) + V((0, 0, Hb + 0.012))
        pts = [d * 0.12 + V((0, 0, 0.22)), d * 0.19 + V((0, 0, Hb + 0.02)), top, top + d * 0.025 + V((0, 0, -0.04)), top + d * 0.03 + V((0.01 * k, 0, -ln))]
        K.add('Cords', bm_tube(pts, [0.008, 0.008, 0.008, 0.008, 0.007], seg=4), OFFER, False)
        K.add('Lines', stroke([pts[-1] + V((0.004, 0, 0)), pts[-1] + V((0.008, -0.003, -0.02))], 0.0012, seg=3), OFFERB, False)
    # lid (pivot = back rim hinge): front half woven, back half only pencil -> the cords show through
    lid = bm_lathe([(0.0, Hb + 0.045), (0.12, Hb + 0.04), (R0 + 0.012, Hb + 0.012), (R0 + 0.012, Hb + 0.0)], seg=16, cap_top=False, cap_bottom=False)
    CR.tri_ngons(lid)
    CR.orient_out(lid, center=(0, 0, Hb - 0.2))
    lfld = lambda p: -p.y + 0.02 + nval(p, 12.0, 260) * 0.03
    K.form('Lid', 'Lines', lid, lfld, PWOOD, thick=0.01, zig=0.01, seed=261, back_near=None,
           hatch_kw=dict(spacing=0.06, length=(0.03, 0.08), r=0.003, density=0.45, up_only=False), ink_r=0.004)
    K.add('Lid', bm_sphere((0, -0.02, Hb + 0.055), (0.025, 0.025, 0.018), seg=8, rings=4), PJOINT, False)
    K.add('Lines', CR.arc(V((0, 0, Hb + 0.03)), R0 + 0.01, 10, 170, n=12, r=0.003, seed=262), PENCIL, False)
    return K.finish(0.4, "Basket of red offering cord (0.44 x 0.3 m). Unfinished: the weave stops at a torn rim on the front-right, the lid's "
                         "back half is only pencil (the coiled red cord shows through). Lid pivot = back rim hinge (rotate local X to open). "
                         "Cords = coils inside + three strands hanging over the front rim (keep red).",
                    pivots={'Lid': (0, R0, Hb)}, parents={'Lines': 'Basket'})


def build_cord_hook():
    K = Kit('CordHook')
    # root = mount point on the wall (wall plane = local y 0, hook sticks out toward -Y / Unity +Z)
    plate = CR.grid_box((0, 0.015 - 0.03, -0.02), (0.11, 0.03, 0.24), step=0.04)
    fld = lambda c: c.z + 0.08 + nval(c, 14.0, 271) * 0.03
    full, res = K.form('Hook', 'Lines', plate, fld, PWOOD, thick=0.01, zig=0.01, seed=272, back_near=0.1,
                       hatch_kw=dict(spacing=0.03, length=(0.03, 0.08), r=0.003, density=0.7), ink_r=0.004)
    K.add('Lines', CR.wire_drawn(full, lambda c, n: fld(c) > 0, r=0.0028, over=0.03, seed=273), PENCIL, False)
    K.add('Hook', bm_sphere((0, -0.033, 0.07), (0.012, 0.006, 0.012), seg=6, rings=4), PJOINT, False)              # built peg
    K.add('Lines', CR.ellipse((0, -0.032, -0.1), 0.012, 0.012, 0.0, turns=1.1, n=8, r=0.002, seed=274, tilt=('X', 90)), PENCIL, False)  # drawn peg
    hk = [V((0, -0.03, 0.0)), V((0, -0.08, -0.005)), V((0, -0.12, 0.01)), V((0, -0.135, 0.045))]
    K.add('Hook', bm_tube(hk, [0.016, 0.014, 0.012, 0.01], seg=6), PWOOD, True)
    K.add('Lines', stroke([p + V((0, 0, 0.016)) for p in hk[:3]], 0.0022, seg=3), INK, False)
    # one red cord strand: looped over the hook, hanging, torn off at the end (frayed + pencil where the rest was)
    tip = V((0, -0.115, 0.012))
    loop = [tip + V((-0.012, 0.0, 0.0)), tip + V((0, -0.006, 0.018)), tip + V((0.012, 0.0, 0.0))]
    hang = [tip + V((0.012, 0.0, 0.0)), tip + V((0.018, -0.01, -0.08)), tip + V((0.01, -0.02, -0.18)), tip + V((0.016, -0.022, -0.27))]
    hang2 = [tip + V((-0.012, 0.0, 0.0)), tip + V((-0.016, -0.008, -0.06)), tip + V((-0.012, -0.012, -0.11))]
    for pts in (loop, hang, hang2):
        K.add('Cord', bm_blade(pts, [0.009] * len(pts), thick=0.004, up=(0, -1, 0)), OFFER, False)
    end = hang[-1]
    rnd = random.Random(275)
    for i in range(5):
        a = end + V((rnd.uniform(-0.006, 0.006), -0.002, 0))
        K.add('Cord', stroke([a, a + V((rnd.uniform(-0.01, 0.01), -0.002, -rnd.uniform(0.015, 0.03)))], 0.0012, seg=3), OFFERB, False)
    K.add('Lines', line([end + V((0, -0.004, -0.03)), end + V((0.004, -0.006, -0.18))], 0.0018, over=0.02, seed=276), PENCIL, False)
    K.add('Lines', line([hang2[-1] + V((0, -0.004, -0.01)), hang2[-1] + V((0.002, -0.006, -0.08))], 0.0015, over=0.01, seed=277), PENCIL, False)
    return K.finish(0.3, "Wall hook (creature-carved peg on a plank) with one torn red cord strand looped over it. Root = mount point on the wall "
                         "(wall plane = local y 0, hook sticks out toward Unity +Z; place at ~1.0-1.2 m). Unfinished: lower half of the plank "
                         "and one peg only pencil; the strand is torn off (frayed) and its missing length pencil. Cord pivot = hook tip.",
                    pivots={'Cord': tuple(tip)}, parents={'Cord': 'Hook', 'Lines': 'Hook'})


# ===================================================================== Kinopio's workbench + sawdust trail
def wooden_bird(c, stage, yaw, seed):
    """thumbnail bird (~6 cm) at a carving stage: 0 block, 1 rough, 2 carved (wing pencil), 3 carved + blue paint started"""
    solid, lines = [], []
    if stage == 0:
        bx = bm_box((0, 0, 0.018), (0.035, 0.065, 0.034))
        solid.append((L.bevel(bx, 0.004, 1, 40), PWOOD))
        lines.append((CR.box_wire((0, 0, 0.022), (0.03, 0.06, 0.038), r=0.0012, over=0.008, seed=seed), PENCIL))
        lines.append((stroke([V((-0.016, -0.03, 0.03)), V((0.0, -0.034, 0.038)), V((0.016, -0.03, 0.03))], 0.0012, seg=3), PENCIL))
    else:
        body = bm_sphere((0, 0.004, 0.02), (0.016, 0.03, 0.018), seg=7, rings=4)
        if stage == 1:
            jitter(body, 0.003, 60.0, seed)
        solid.append((body, PWOOD))
        solid.append((bm_sphere((0, -0.026, 0.036), (0.012, 0.012, 0.012), seg=6, rings=4), PWOOD))
        solid.append((bm_cyl((0, -0.036, 0.036), (0, -0.05, 0.034), 0.005, 0.0005, seg=5), PJOINT))
        solid.append((bm_blade([V((0, 0.03, 0.022)), V((0, 0.048, 0.03)), V((0, 0.058, 0.034))], [0.008, 0.012, 0.004], thick=0.003, up=(0, 0, 1)), PWOOD))
        if stage >= 2:
            for sx in (-1, 1):
                lines.append((stroke([V((sx * 0.016, -0.01, 0.026)), V((sx * 0.019, 0.012, 0.03)), V((sx * 0.014, 0.034, 0.024))], 0.0012, seg=3), PENCIL))
            solid.append((bm_sphere((0.009, -0.032, 0.04), (0.002, 0.002, 0.002), seg=4, rings=3), INK))
        if stage == 3:
            solid.append((bm_sphere((0, 0.006, 0.024), (0.0165, 0.026, 0.016), seg=7, rings=4), 'M_PaintBlue'))
            body_cut = solid[-1][0]
            deform(body_cut, lambda q: V((q.x, q.y, max(q.z, 0.026))))
    M = Matrix.Translation(V(c)) @ Matrix.Rotation(math.radians(yaw), 4, 'Z')
    for b, _ in solid + lines:
        L.xform(b, M)
    return solid, lines


def build_kid_workbench():
    K = Kit('KidWorkbench')
    Wt, Dt, Ht = 0.82, 0.4, 0.55
    # top: built from the left, the right end torn and only pencil
    top = CR.grid_box((0, 0, Ht - 0.025), (Wt, Dt, 0.05), step=0.08)
    tfld = lambda c: 0.3 - c.x + nval(c, 8.0, 281) * 0.05
    full, res = K.form('Bench', 'Lines', top, tfld, PWOOD, thick=0.012, zig=0.015, seed=282, back_near=0.2,
                       hatch_kw=dict(spacing=0.06, length=(0.04, 0.12), r=0.0035, density=0.5), ink_r=0.005)
    K.add('Lines', CR.wire_drawn(full, lambda c, n: tfld(c) > 0, r=0.003, over=0.06, seed=283), PENCIL, False)
    for k, (x, y) in enumerate(((-0.36, -0.16), (-0.36, 0.16), (0.36, -0.16), (0.36, 0.16))):
        if k == 2:   # front-right leg only pencil
            for dx in (-0.022, 0.022):
                K.add('Lines', line([V((x + dx, y, 0.0)), V((x + dx, y, Ht - 0.05))], 0.003, over=0.04, seed=284 + dx), PENCIL, False)
            continue
        K.add('Bench', P.bbox((x, y, (Ht - 0.05) / 2), (0.05, 0.05, Ht - 0.05), 0.008), PWOOD, False)
        K.add('Lines', stroke([V((x - 0.026, y - 0.026, 0.05)), V((x - 0.026, y - 0.026, Ht - 0.1))], 0.0025, seg=3), INK, False)
    K.add('Bench', P.bbox((-0.36, 0, 0.12), (0.04, 0.32, 0.04), 0.006), PWOOD, False)
    K.add('Lines', line([V((-0.34, 0.16, 0.12)), V((0.34, 0.16, 0.12))], 0.003, over=0.05, seed=288), PENCIL, False)
    # on top: small whetstone, a sawdust heap, a carving knife (human, finished), the birds at every stage
    K.add('Bench', P.bbox((-0.26, 0.08, Ht + 0.02), (0.16, 0.06, 0.04), 0.01), 'M_Whetstone', False)
    K.add('Lines', stroke([V((-0.32, 0.05, Ht + 0.041)), V((-0.2, 0.06, Ht + 0.041))], 0.002, seg=3), INK, False)
    heap = bm_lathe([(0.0, Ht), (0.11, Ht), (0.07, Ht + 0.02), (0.0, Ht + 0.035)], seg=10, center=(-0.05, 0.06, 0), sy=0.8)
    jitter(heap, 0.006, 20.0, 289)
    K.add('Bench', heap, 'M_Shaving', True)
    rnd = random.Random(290)
    for k in range(4):
        a = rnd.uniform(0, 6.28)
        d = rnd.uniform(0.03, 0.16)
        K.add('Bench', shaving(V((-0.05 + math.cos(a) * d, 0.06 + math.sin(a) * d * 0.7, Ht + 0.004)), rnd, 0.8), 'M_Shaving', False)
    knife = [(P.bbox((0.0, 0, 0.004), (0.09, 0.016, 0.008), 0.003), 'M_Wood'), (bm_blade([V((0.045, 0, 0.005)), V((0.08, 0, 0.005)), V((0.11, 0, 0.004))],
                                                                                       [0.008, 0.007, 0.001], thick=0.002, up=(0, 0, 1)), 'M_Iron')]
    put_pieces(K, 'Bench', knife, (-0.05, -0.12, Ht), rz=-20)
    for (x, y, st, yw) in ((0.0, -0.08, 0, 10), (0.08, -0.06, 1, -25), (0.16, -0.1, 2, 30), (0.11, 0.06, 3, -60), (0.2, 0.02, 2, 160)):
        sol, lin = wooden_bird((x, y, Ht), st, yw, 291 + x * 10)
        for b, m in sol:
            K.add('Birds', b, m, False)
        for b, m in lin:
            K.add('Lines', b, m, False)
    return K.finish(0.9, "Kinopio's little workbench (0.82 x 0.4, top at 0.55 m - child height). On it: a small whetstone, a sawdust heap with "
                         "shavings, a carving knife (fallen human object, finished) and five thumbnail wooden birds at every stage (block -> "
                         "rough -> carved with pencil wings -> one with blue paint started; part Birds). Unfinished: right end of the top and "
                         "the front-right leg only pencil.", parents={'Birds': 'Bench', 'Lines': 'Bench'})


def build_sawdust_bits():
    K = Kit('SawdustBits')
    rnd = random.Random(301)
    for k in range(9):
        p = V((rnd.uniform(-0.25, 0.25), rnd.uniform(-0.12, 0.12), 0.0))
        K.add('Bits', shaving(p, rnd, rnd.uniform(1.0, 1.5)), 'M_Shaving', False)
    for k in range(10):
        p = V((rnd.uniform(-0.28, 0.28), rnd.uniform(-0.14, 0.14), 0.002))
        K.add('Bits', bm_sphere(p, (0.01, 0.008, 0.003), seg=5, rings=3), 'M_PuppetJoint', False)
    K.add('Lines', D_loop((0.18, 0.08, 0.01), 0.02), PENCIL, False)
    return K.finish(0.6, "A few scattered wood shavings and dust specks (0.55 x 0.28 m) for a trail. Repeat with random yaw / scale along a path. "
                         "Lies on the floor.", parents={'Lines': 'Bits'})


def D_loop(c, r):
    import ouat_dressing as D
    return D.loop(V(c), r, r * 0.75, n=8, r=0.0022, seed=302)


ASSETS = [
    ('BarkDoor', build_bark_door), ('ClothCover', build_cloth_cover), ('MusicBox', build_music_box), ('MirrorShard', build_mirror_shard),
    ('SpinTop', build_spin_top), ('Torch', build_torch), ('CordBasket', build_cord_basket), ('CordHook', build_cord_hook),
    ('KidWorkbench', build_kid_workbench), ('SawdustBits', build_sawdust_bits),
]
