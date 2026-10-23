# Village mood shots: the chapter-1 village assembled from the kit at the §2 coordinates (Unity world, metres).
# Called from render_previews.py (shot=village_overview|village_plaza|village_pond). Render-only scene dressing.
import math, random
import bpy
from mathutils import Vector
import ouat_lib as L
import ouat_render as R
import render_previews as RP

rnd = random.Random(11)


def U(ux, uz, uy=0.0):
    """Unity (x, z, y) -> Blender location."""
    return Vector((-ux, -uz, uy))


def put(name, ux, uz, uy=0.0, yaw=0.0, new=True):
    """Instance an asset at Unity coords. yaw = Unity yaw (deg, 0 = facing +Z)."""
    r = RP.dup(name) if new else RP.root(name)
    r.location = U(ux, uz, uy)
    r.rotation_euler = (0, 0, math.radians(-yaw))
    return r


def child(r, part):
    for ob in r.children_recursive:
        nm = ob.name.split('|', 1)[-1].split('#')[0]
        if nm == part:
            return ob
    return None


def bow(r, deg=70, kneel=0.25):
    """Prostrate pose (엎드림) for a puppet villager: lean the body forward, fold the legs."""
    b = child(r, 'Body')
    if b:
        b.rotation_euler.x = math.radians(deg)
    for lg in ('LegL', 'LegR'):
        o = child(r, lg)
        if o:
            o.rotation_euler.x = math.radians(-85)
    r.location.z -= kneel


def sit(r):
    for lg in ('LegL', 'LegR'):
        o = child(r, lg)
        if o:
            o.rotation_euler.x = math.radians(80)
    r.location.z -= 0.25


def look_up(r, deg=-35):
    h = child(r, 'Head')
    if h:
        h.rotation_euler.x = math.radians(deg)


USED = set()


def use(*names):
    USED.update(names)


def build_village():
    use('Hero_Bluebird', 'Kinopio', 'Chief', 'Mother', 'Villager_A', 'Villager_B', 'Villager_C', 'Silhouette_A',
        'Silhouette_B', 'Lump_1', 'Lump_2', 'Lump_3', 'Fish', 'Puppet')
    for c in bpy.data.collections:
        r = bpy.data.objects.get(c.name)
        if r is not None:
            r.location = (0, 0, -500)
    # ---------------- ground (render only)
    bpy.ops.mesh.primitive_plane_add(size=1, location=U(0, 0, 0))
    g = bpy.context.active_object
    g.scale = (190, 140, 1)
    g.data.materials.append(L.get_mat('M_Paper'))
    g.name = 'Ground'
    import bmesh as _bm
    from ouat_lib import stroke, wobble_line
    cb = _bm.new()
    for i in range(260):
        x, z = rnd.uniform(-68, 68), rnd.uniform(-44, 44)
        p0 = U(x, z, 0.012)
        ang = rnd.uniform(0, math.pi)
        ln = rnd.uniform(0.8, 3.5)
        p1 = p0 + Vector((math.cos(ang) * ln, math.sin(ang) * ln, 0))
        pts = wobble_line(p0, p1, 4, 0.15, i)
        for p in pts:
            p.z = 0.012
        sb = stroke(pts, 0.035, seg=3)
        me = bpy.data.meshes.new('tmpc'); sb.to_mesh(me); cb.from_mesh(me); bpy.data.meshes.remove(me); sb.free()
    cm = bpy.data.meshes.new('GroundCracks'); cb.to_mesh(cm); cb.free()
    cm.materials.append(L.get_mat('M_Ink'))
    co = bpy.data.objects.new('GroundCracks', cm)
    bpy.context.scene.collection.objects.link(co)

    # ---------------- fall: raised plateau, ceiling hole, light shaft, fallen human things
    use('Cliff_1', 'Cliff_2', 'Cliff_3', 'LightShaft', 'CeilingHole', 'ItemPile', 'Gap', 'DrawnBar', 'Ladder',
        'Junk_Book', 'Junk_Umbrella', 'Junk_Clock', 'Junk_Shoe', 'Junk_Teacup', 'Junk_Lantern', 'Rock_1', 'Rock_2', 'Rock_3')
    for nm, x, z, yaw, sc in (('Cliff_2', -55, 30, 0, 1.8), ('Cliff_1', -62.5, 35, 40, 1.4), ('Cliff_3', -48.5, 34.5, 15, 1.5),
                              ('Cliff_1', -61, 24.5, -30, 1.3), ('Cliff_3', -50, 24.5, 70, 1.3)):
        c_ = put(nm, x, z, 1.5, yaw)
        c_.scale = (sc, sc, 1.0)
    put('LightShaft', -55, 30, 1.5)
    ch_ = put('CeilingHole', -55, 30, 29.5)
    for o in [ch_] + list(ch_.children_recursive):
        o.visible_shadow = False
    put('ItemPile', -58, 33, 1.5, 20)
    junk = ['Junk_Book', 'Junk_Umbrella', 'Junk_Clock', 'Junk_Shoe', 'Junk_Teacup', 'Junk_Lantern', 'Junk_Book', 'Junk_Book']
    for i, j in enumerate(junk):
        a = i * 0.8 + 0.3
        put(j, -55 + math.cos(a) * (3 + i * 0.6), 30 + math.sin(a) * (3 + i * 0.5), 1.5, rnd.uniform(0, 360))
    h2 = put('Hero_Bluebird', -53.5, 28, 1.5, 130)
    look_up(h2, -40)
    k2 = put('Kinopio', -51.2, 27.2, 1.5, -60)
    bow(k2, 55, kneel=0.08)
    put('Gap', -52, 17.5, 0, 0)
    put('DrawnBar', -52, 14.5, 0, 0)
    put('Ladder', -46.5, 23, 0, -60)
    # ---------------- gate: sitting villagers, inscription stone
    use('StoneTablet', 'Signpost', 'Paving_HexBroken', 'Paving_Hex')
    put('StoneTablet', -27, 21, 0, 160)
    for nm, x, z, yaw in (('Villager_A', -32, 14.5, 30), ('Villager_C', -29, 13.5, 0), ('Silhouette_A', -34, 20, 80), ('Silhouette_B', -26, 15, -20)):
        r = put(nm, x, z, 0, yaw)
        if nm.startswith('Villager'):
            sit(r)
    # ---------------- plaza: paving, stage (painted), picture board, chief, lamps, painted towers
    use('Stage', 'PictureBoard', 'LampPost', 'Tower_Dome', 'House_4', 'House_3', 'House_2', 'House_1', 'FishProp', 'Chair', 'Fence_DrawnBar')
    for i in range(-2, 2):
        for k in range(-1, 3):
            put('Paving_Hex', 4 + i * 8, 6 + k * 8, 0, (i * 60 + k * 120) % 180)
    st = put('Stage', 2, 21, 0, 180)
    bpy.context.view_layer.update()
    spot = child(st, 'PuppetSpot')
    pp = RP.root('Puppet')
    pp.parent = spot
    pp.matrix_parent_inverse.identity()
    pp.location = (0, 0, 0)
    pp.rotation_euler = (0, 0, 0)
    put('FishProp', 5.5, 21.5, 0.8, 200)
    put('PictureBoard', -7, 19, 0, 160)
    ch = put('Chief', 9.5, 15, 0, 220, new=False)
    put('Tower_Dome', 2, 33, 0, 180)
    put('House_4', -12, 27, 0, 150)
    put('House_4', 15, 29, 0, 200)
    for (x, z) in ((-9, 4), (11, 4), (-15, 13), (16, 12)):
        put('LampPost', x, z, 0, rnd.uniform(0, 360))
    # audience facing the stage, bowing
    aud = [('Villager_B', -2, 12), ('Silhouette_A', 1, 11), ('Silhouette_B', 4, 12.5), ('Silhouette_A', -4.5, 10), ('Silhouette_B', 6.5, 10.5)]
    for nm, x, z in aud:
        r = put(nm, x, z, 0, 0)
        if nm.startswith('Villager'):
            bow(r, 60)
    # hero + Kinopio arriving from the gate side
    hero = put('Hero_Bluebird', -3.2, 11.8, 0, 25, new=False)
    kid = put('Kinopio', -4.6, 11.2, 0, 35, new=False)
    # ---------------- alley: houses with chairs and lumps, mother
    houses = (('House_1', 16, 36, 170), ('House_2', 26, 37, 190), ('House_3', 33, 27, 250), ('House_2', 13, 24, 120), ('House_1', 30, 17, 300))
    for nm, x, z, yaw in houses:
        put(nm, x, z, 0, yaw)
    for (nm, x, z, yaw, lump) in (('Chair', 18, 31, 170, 'Lump_1'), ('Chair', 25, 32, 190, 'Lump_2'), ('Chair', 29, 26, 250, 'Lump_3'), ('Chair', 16, 26, 120, 'Lump_1')):
        c = put('Chair', x, z, 0, yaw)
        l = put(lump, x, z, 0.5, yaw, new=(lump == 'Lump_1' and x == 16))
        if lump != 'Lump_1' or x != 16:
            pass
    put('Mother', 23.6, 31, 0, 200, new=False)
    # ---------------- field: mounds, pile, cart, sign, page
    use('Mound', 'Cart', 'PinocchioPage', 'Pond')
    for k in range(4):
        put('Mound', 38 + (k % 2) * 1.5, -6 + k * 4, 0, 90 + rnd.uniform(-6, 6))
    put('ItemPile', 33, 6, 0, 30)
    put('ItemPile', 35, 3, 0, 110)
    put('Signpost', 44, 6, 0, 200)
    put('PinocchioPage', 42.5, 4.5, 0, 30)
    put('Villager_C', 31, 4, 0, 60, new=True)
    # cart pushed to the end of the field, almost at the pond
    put('Cart', 53, -12, 0, 140)
    # ---------------- pond + fish bursting up
    put('Pond', 58, -18, 0)
    fish = RP.root('Fish')
    fish.location = U(58.5, -18.5, 3.4)
    fish.rotation_euler = (math.radians(-48), 0, math.radians(140))
    child(fish, 'JawUpper').rotation_euler.x = math.radians(-30)
    child(fish, 'JawLower').rotation_euler.x = math.radians(32)
    put('StoneTablet', 51, -21, 0, 70)
    put('Hero_Bluebird', 50.5, -15.5, 0, 110)
    for x, z, nm in ((48, -9, 'Villager_A'), (46.5, -11, 'Villager_B'), (47, -7, 'Silhouette_B'), (45, -9.5, 'Silhouette_A')):
        r = put(nm, x, z, 0, 120)
        if nm.startswith('Villager'):
            bow(r, 70)
    # ---------------- cart road fence
    put('Fence_DrawnBar', -22, 4, 0, 60)
    # ---------------- boundary: cave walls (north/south/east) + rocks, spires behind
    use('CaveWall_1', 'CaveWall_2', 'CaveWall_3', 'Spire_1', 'Spire_2', 'Spire_3')
    for i in range(12):
        x = -66 + i * 12
        put(rnd.choice(('CaveWall_1', 'CaveWall_2', 'CaveWall_1')), x, 47, 0, 180)
        put(rnd.choice(('CaveWall_1', 'CaveWall_2')), x, -47, 0, 0)
    for i in range(8):
        put(rnd.choice(('CaveWall_1', 'CaveWall_2')), 72, -42 + i * 12, 0, 270)
        put(rnd.choice(('CaveWall_1', 'CaveWall_2')), -72, -42 + i * 12, 0, 90)
    for i in range(40):
        a = rnd.uniform(0, 2 * math.pi)
        rr = rnd.uniform(78, 125)
        x, z = math.cos(a) * rr * 1.1, math.sin(a) * rr * 0.75
        if x < -60:
            continue
        put(rnd.choice(('Spire_1', 'Spire_2', 'Spire_3', 'Spire_2')), x, z, 0, rnd.uniform(0, 360))
    # worn hex paving along the main road (fall -> gate -> plaza -> alley -> field -> pond)
    road = [(-48, 26), (-40, 21), (-32, 17), (-24, 14), (-16, 11), (14, 16), (20, 22), (24, 18), (30, 10), (36, 2), (44, -4), (50, -10)]
    for (x, z) in road:
        put('Paving_HexBroken', x + rnd.uniform(-1, 1), z + rnd.uniform(-1, 1), 0, rnd.choice((0, 60, 120)))
    for i in range(30):
        x, z = rnd.uniform(-66, 66), rnd.uniform(-42, 42)
        keep_out = ((0, 10, 20), (58, -18, 12), (-55, 30, 15), (22, 26, 14), (40, 0, 16), (-30, 18, 9))
        if any((x - cx) ** 2 + (z - cz) ** 2 < r * r for cx, cz, r in keep_out):
            continue
        put(rnd.choice(('Rock_1', 'Rock_2', 'Rock_3')), x, z, 0, rnd.uniform(0, 360))
    RP.hide_all_but(USED)
    return dict(hero=hero, kid=kid, chief=ch, stage=st, fish=fish)


DIM = 0.38
WORLD = 0.38


def lights(stage_lamps=True):
    R.world_light(L.hex2rgb('C9D0D8'), WORLD)
    R.add_sun((52, 0, 60), DIM, color=(0.86, 0.9, 1.0), angle=3, name='Dim')
    # the only strong light: the shaft from the ceiling hole onto the fall
    R.add_spot(tuple(U(-55, 30, 30)), tuple(U(-55, 30, 1.5)), energy=60000, size_deg=34, blend=0.5, radius=2.5, name='Shaft')
    if stage_lamps:
        for (x, z) in ((-0.6, 18.9), (1.4, 18.9), (3.6, 18.9), (5.6, 18.9)):
            R.add_point(tuple(U(x, z, 1.6)), energy=260, radius=0.15, name='StageLamp')
        R.add_point(tuple(U(2, 21.5, 4.0)), energy=900, color=(1, 0.85, 0.6), radius=0.5, name='StageFill')
        for (x, z) in ((-9, 4), (11, 4), (-15, 13), (16, 12)):
            R.add_point(tuple(U(x, z, 2.7)), energy=420, radius=0.15, name='Lamp')


def ucam(pos, target, lens):
    return R.add_camera(tuple(U(pos[0], pos[2], pos[1])), tuple(U(target[0], target[2], target[1])), lens=lens)


def _render(name, cam_pos, cam_tgt, lens, res=(3200, 1800)):
    build_village()
    R.setup_render(res=res, samples=RP.SAMPLES, bg=L.hex2rgb('C9D0D8'))
    R.prepare_all(outline_scale=1.6, hatch_scale=420.0, skip=('Ground',))
    lights()
    ucam(cam_pos, cam_tgt, lens)
    R.render(f'{RP.RAW}/{name}.png')


def village_overview():
    # bird's-eye over the whole layout (§2), looking north
    _render('village_overview', (4, 92, -58), (4, 0, 3), 27)
    import os
    bpy.ops.wm.save_as_mainfile(filepath=os.path.join(os.path.dirname(RP.RAW), '..', 'blend', 'ouat_ch1_village_mood.blend'), copy=True)


def village_fall():
    # behind the fall plateau: waking among fallen human things under the shaft, the town beyond
    _render('village_fall', (-43, 7.5, 21), (-55.5, 3.2, 30.5), 30)


def village_plaza():
    _render('village_plaza', (-9, 11, -4), (3, 2.0, 19), 34)


def village_pond():
    _render('village_pond', (43, 6.5, -29), (57, 4.2, -17), 30)


SHOTS = {'village_overview': village_overview, 'village_fall': village_fall, 'village_plaza': village_plaza, 'village_pond': village_pond}
