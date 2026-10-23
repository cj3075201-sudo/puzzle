# -*- coding: utf-8 -*-
"""Preview-render helpers: toon material approximation of the Unity look + inverted-hull ink outline.
Only used for preview renders (never for the exported FBX)."""
import bpy, math, json
from mathutils import Vector
from bpy_extras.object_utils import world_to_camera_view
import ouat_lib as L

INK = L.hex2rgb('2B2622')


def _mix(a, b, t):
    return [a[i] * (1 - t) + b[i] * t for i in range(3)]


def toonify(mat, deep_k=0.42, grain=0.05, hatch=True, hatch_scale=260.0):
    """Rebuild the node tree of an M_* material as a 3-band toon (deep / shade / base)."""
    name = mat.name
    if name not in L.MATS:
        return
    base, shade, ol, cat, extra = L.MATS[name]
    cb, cs = L.hex2rgb(base), L.hex2rgb(shade)
    mat.use_nodes = True
    nt = mat.node_tree
    nt.nodes.clear()
    out = nt.nodes.new('ShaderNodeOutputMaterial')
    if cat in ('silhouette', 'line'):
        em = nt.nodes.new('ShaderNodeEmission')
        em.inputs['Color'].default_value = (*cb, 1)
        nt.links.new(em.outputs[0], out.inputs['Surface'])
        return
    if cat in ('sketch', 'light'):
        em = nt.nodes.new('ShaderNodeEmission')
        em.inputs['Color'].default_value = (*cb, 1)
        em.inputs['Strength'].default_value = 1.0 if cat == 'sketch' else 1.4
        tr = nt.nodes.new('ShaderNodeBsdfTransparent')
        mix = nt.nodes.new('ShaderNodeMixShader')
        alpha = extra.get('alpha', 0.5) * (0.4 if cat == 'light' else 1.0)
        if cat == 'light':
            # fade towards the top of the cone (object Z) so the shaft reads as falling light
            tc = nt.nodes.new('ShaderNodeTexCoord')
            sep = nt.nodes.new('ShaderNodeSeparateXYZ')
            nt.links.new(tc.outputs['Generated'], sep.inputs[0])
            mr = nt.nodes.new('ShaderNodeMapRange')
            mr.inputs['From Min'].default_value = 0.0
            mr.inputs['From Max'].default_value = 1.0
            mr.inputs['To Min'].default_value = alpha
            mr.inputs['To Max'].default_value = alpha * 0.25
            nt.links.new(sep.outputs['Z'], mr.inputs['Value'])
            # facing ratio -> softer edges
            lw = nt.nodes.new('ShaderNodeLayerWeight')
            lw.inputs['Blend'].default_value = 0.5
            inv = nt.nodes.new('ShaderNodeMath'); inv.operation = 'SUBTRACT'
            inv.inputs[0].default_value = 1.0
            nt.links.new(lw.outputs['Facing'], inv.inputs[1])
            mul = nt.nodes.new('ShaderNodeMath'); mul.operation = 'MULTIPLY'
            nt.links.new(mr.outputs[0], mul.inputs[0]); nt.links.new(inv.outputs[0], mul.inputs[1])
            nt.links.new(mul.outputs[0], mix.inputs['Fac'])
        else:
            mix.inputs['Fac'].default_value = alpha
        nt.links.new(tr.outputs[0], mix.inputs[1])
        nt.links.new(em.outputs[0], mix.inputs[2])
        nt.links.new(mix.outputs[0], out.inputs['Surface'])
        try:
            mat.surface_render_method = 'BLENDED'
        except Exception:
            mat.blend_method = 'BLEND'
        mat.use_backface_culling = False
        return
    # lit toon
    dif = nt.nodes.new('ShaderNodeBsdfDiffuse')
    dif.inputs['Color'].default_value = (1, 1, 1, 1)
    s2r = nt.nodes.new('ShaderNodeShaderToRGB')
    nt.links.new(dif.outputs[0], s2r.inputs[0])
    bw = nt.nodes.new('ShaderNodeRGBToBW')
    nt.links.new(s2r.outputs['Color'], bw.inputs[0])
    ramp = nt.nodes.new('ShaderNodeValToRGB')
    ramp.color_ramp.interpolation = 'CONSTANT'
    els = ramp.color_ramp.elements
    deep = _mix([c * deep_k for c in cs], INK, 0.15)
    if name == 'M_Ink':
        deep = cs
    els[0].position = 0.0
    els[0].color = (*deep, 1)
    els[1].position = 0.10
    els[1].color = (*cs, 1)
    e = els.new(0.42)
    e.color = (*cb, 1)
    nt.links.new(bw.outputs[0], ramp.inputs['Fac'])
    col = ramp.outputs['Color']
    if extra.get('emission'):
        # self-glow: blend toward base
        mixc = nt.nodes.new('ShaderNodeMix'); mixc.data_type = 'RGBA'
        mixc.inputs['Factor'].default_value = extra['emission']
        nt.links.new(col, mixc.inputs[6]); mixc.inputs[7].default_value = (*cb, 1)
        col = mixc.outputs[2]
    if grain > 0 and cat == 'paper':
        tex = nt.nodes.new('ShaderNodeTexNoise')
        tex.inputs['Scale'].default_value = 18.0
        tex.inputs['Detail'].default_value = 6.0
        mr = nt.nodes.new('ShaderNodeMapRange')
        mr.inputs['To Min'].default_value = 1.0 - grain
        mr.inputs['To Max'].default_value = 1.0 + grain * 0.4
        nt.links.new(tex.outputs['Fac'], mr.inputs['Value'])
        mul = nt.nodes.new('ShaderNodeMix'); mul.data_type = 'RGBA'; mul.blend_type = 'MULTIPLY'
        mul.inputs['Factor'].default_value = 1.0
        nt.links.new(col, mul.inputs[6])
        cv = nt.nodes.new('ShaderNodeCombineColor')
        for k in ('Red', 'Green', 'Blue'):
            nt.links.new(mr.outputs[0], cv.inputs[k])
        nt.links.new(cv.outputs[0], mul.inputs[7])
        col = mul.outputs[2]
    if extra.get('hatch') and hatch:
        # screen-space diagonal hatching in the shade/deep bands (hand-drawn hatch approximation)
        tc = nt.nodes.new('ShaderNodeTexCoord')
        mp = nt.nodes.new('ShaderNodeMapping')
        mp.inputs['Scale'].default_value = (1.0, 0.5625, 1.0)
        nt.links.new(tc.outputs['Window'], mp.inputs['Vector'])
        wv = nt.nodes.new('ShaderNodeTexWave')
        wv.wave_type = 'BANDS'; wv.bands_direction = 'DIAGONAL'
        wv.inputs['Scale'].default_value = hatch_scale
        wv.inputs['Distortion'].default_value = 1.2
        wv.inputs['Detail Scale'].default_value = 0.6
        nt.links.new(mp.outputs['Vector'], wv.inputs['Vector'])
        thr = nt.nodes.new('ShaderNodeMath'); thr.operation = 'GREATER_THAN'
        thr.inputs[1].default_value = 0.8
        nt.links.new(wv.outputs['Fac'], thr.inputs[0])
        sh_m = nt.nodes.new('ShaderNodeMath'); sh_m.operation = 'LESS_THAN'
        sh_m.inputs[1].default_value = 0.42
        nt.links.new(bw.outputs[0], sh_m.inputs[0])
        both = nt.nodes.new('ShaderNodeMath'); both.operation = 'MULTIPLY'
        nt.links.new(thr.outputs[0], both.inputs[0]); nt.links.new(sh_m.outputs[0], both.inputs[1])
        hm = nt.nodes.new('ShaderNodeMix'); hm.data_type = 'RGBA'
        nt.links.new(both.outputs[0], hm.inputs['Factor'])
        nt.links.new(col, hm.inputs[6])
        hc = _mix([c * 0.78 for c in cs], INK, 0.12)
        hm.inputs[7].default_value = (*hc, 1)
        col = hm.outputs[2]
    em = nt.nodes.new('ShaderNodeEmission')
    nt.links.new(col, em.inputs['Color'])
    nt.links.new(em.outputs[0], out.inputs['Surface'])


def outline_material():
    m = bpy.data.materials.get('R_OutlineInk')
    if m:
        return m
    m = bpy.data.materials.new('R_OutlineInk')
    m.use_nodes = True
    nt = m.node_tree
    nt.nodes.clear()
    out = nt.nodes.new('ShaderNodeOutputMaterial')
    em = nt.nodes.new('ShaderNodeEmission')
    em.inputs['Color'].default_value = (*INK, 1)
    nt.links.new(em.outputs[0], out.inputs['Surface'])
    m.use_backface_culling = True
    try:
        m.use_backface_culling_shadow = True
    except Exception:
        pass
    return m


def add_outline(ob, thickness):
    if ob.type != 'MESH':
        return
    names = [m.name for m in ob.data.materials if m]
    if not any(L.MATS.get(n, (0, 0, False))[2] for n in names):
        return
    olm = outline_material()
    n = len(ob.data.materials)
    if olm.name not in names:
        ob.data.materials.append(olm)
    md = ob.modifiers.new('ink', 'SOLIDIFY')
    md.thickness = thickness
    md.offset = 1.0
    md.use_flip_normals = True
    md.use_rim = False
    md.use_even_offset = False
    md.use_quality_normals = True
    md.material_offset = n
    # respect the per-material outline flag (Unity's shader does): vertices that only belong to outline=False faces
    # get zero hull thickness (10/23: nose / eye decals / seams no longer get a thick ink ring)
    no = {i for i, m in enumerate(ob.data.materials) if m and m.name in L.MATS and not L.MATS[m.name][2]}
    if no:
        keep = set()
        for poly in ob.data.polygons:
            if poly.material_index not in no:
                keep.update(poly.vertices)
        mask = [v.index for v in ob.data.vertices if v.index not in keep]
        if mask:
            vg = ob.vertex_groups.get('ol_mask') or ob.vertex_groups.new(name='ol_mask')
            vg.add(mask, 1.0, 'REPLACE')
            md.vertex_group = 'ol_mask'
            md.invert_vertex_group = True
            md.thickness_vertex_group = 0.0


def prepare_all(outline_scale=1.0, grain=0.05, deep_k=0.42, skip=(), hatch=True, hatch_scale=260.0):
    for m in bpy.data.materials:
        if m.name in L.MATS:
            toonify(m, deep_k=deep_k, grain=grain, hatch=hatch, hatch_scale=hatch_scale)
    done_meshes = set()
    for ob in bpy.data.objects:
        if ob.type != 'MESH' or ob.name in skip:
            continue
        # thickness from size of the whole asset (root dims)
        root = ob
        while root.parent:
            root = root.parent
        sz = root.get('ouat_size', 1.0)
        t = max(0.0025, min(0.06, 0.012 * (sz ** 0.6))) * outline_scale
        if ob.data.name in done_meshes and ob.data.users > 1:
            pass
        add_outline(ob, t)
        done_meshes.add(ob.data.name)
        mats = [m.name for m in ob.data.materials if m]
        if any(L.MATS.get(n, (0, 0, 0, ''))[3] in ('light', 'sketch') for n in mats):
            ob.visible_shadow = False


def setup_render(res=(1920, 1080), samples=32, transparent=False, bg=(0.93, 0.9, 0.82)):
    sc = bpy.context.scene
    sc.render.engine = 'BLENDER_EEVEE'
    sc.render.resolution_x, sc.render.resolution_y = res
    sc.render.resolution_percentage = 100
    sc.render.film_transparent = transparent
    try:
        sc.eevee.taa_render_samples = samples
    except Exception:
        pass
    sc.view_settings.view_transform = 'Standard'
    sc.view_settings.look = 'None'
    sc.view_settings.exposure = 0.0
    sc.view_settings.gamma = 1.0
    sc.render.image_settings.file_format = 'PNG'
    sc.render.image_settings.color_mode = 'RGBA' if transparent else 'RGB'
    w = sc.world or bpy.data.worlds.new('World')
    sc.world = w
    w.use_nodes = True
    bgn = w.node_tree.nodes.get('Background')
    if bgn is None:
        bgn = w.node_tree.nodes.new('ShaderNodeBackground')
        w.node_tree.links.new(bgn.outputs[0], w.node_tree.nodes.new('ShaderNodeOutputWorld').inputs[0])
    lin = [c for c in bg]
    bgn.inputs['Color'].default_value = (*lin, 1)
    bgn.inputs['Strength'].default_value = 1.0
    return sc


def world_light(color, strength):
    w = bpy.context.scene.world
    bgn = w.node_tree.nodes.get('Background')
    bgn.inputs['Color'].default_value = (*color, 1)
    bgn.inputs['Strength'].default_value = strength


def add_sun(rot_deg, strength=3.0, color=(1, 1, 1), angle=2.0, shadow=True, name='Sun'):
    ld = bpy.data.lights.new(name, 'SUN')
    ld.energy = strength
    ld.color = color
    ld.angle = math.radians(angle)
    ld.use_shadow = shadow
    ob = bpy.data.objects.new(name, ld)
    bpy.context.scene.collection.objects.link(ob)
    ob.rotation_euler = [math.radians(a) for a in rot_deg]
    return ob


def add_spot(loc, target, energy=50000, size_deg=40, blend=0.3, color=(1, 0.96, 0.85), radius=1.0, name='Spot'):
    ld = bpy.data.lights.new(name, 'SPOT')
    ld.energy = energy
    ld.color = color
    ld.spot_size = math.radians(size_deg)
    ld.spot_blend = blend
    ld.shadow_soft_size = radius
    ob = bpy.data.objects.new(name, ld)
    bpy.context.scene.collection.objects.link(ob)
    ob.location = loc
    d = Vector(target) - Vector(loc)
    ob.rotation_euler = d.to_track_quat('-Z', 'Y').to_euler()
    return ob


def add_point(loc, energy=200, color=(1, 0.9, 0.7), radius=0.2, name='Point'):
    ld = bpy.data.lights.new(name, 'POINT')
    ld.energy = energy
    ld.color = color
    ld.shadow_soft_size = radius
    ob = bpy.data.objects.new(name, ld)
    bpy.context.scene.collection.objects.link(ob)
    ob.location = loc
    return ob


def add_camera(loc, target, lens=50, ortho=None, name='Cam'):
    cd = bpy.data.cameras.new(name)
    cd.lens = lens
    cd.clip_end = 1000
    if ortho:
        cd.type = 'ORTHO'
        cd.ortho_scale = ortho
    ob = bpy.data.objects.new(name, cd)
    bpy.context.scene.collection.objects.link(ob)
    ob.location = loc
    d = Vector(target) - Vector(loc)
    ob.rotation_euler = d.to_track_quat('-Z', 'Y').to_euler()
    bpy.context.scene.camera = ob
    return ob


def project(cam, pts):
    sc = bpy.context.scene
    out = []
    for p in pts:
        co = world_to_camera_view(sc, cam, Vector(p))
        out.append((co.x, 1 - co.y, co.z))
    return out


def render(path):
    bpy.context.scene.render.filepath = path
    bpy.ops.render.render(write_still=True)
