# -*- coding: utf-8 -*-
"""Skinned + animated characters (round 4, 2026-10-23).

Build space: designs are modelled in the usual Blender character space (Z up, front -Y, character's left +X).
Rig space ("armature space", what Unity sees): Y up, front +Z, left +X  (C = Rx(-90): (x, y, z) -> (x, z, -y)).
The armature object carries rotation Rx(+90) so it stands upright in Blender; the FBX exporter (axis_up=Y,
axis_forward=-Z) cancels it -> the root node in the FBX has rotation 0 / scale 1, like every other OUAT asset.

Every bone points along +Y of the armature space with roll 0, so every bone's rest matrix is the identity rotation.
=> In Unity every bone's rest localRotation is identity, and a local rotation reads directly as:
   X = pitch (+ tilts the bone's +Y toward +Z = forward; a hanging limb swings BACK), Y = yaw (+ turns face to
   the character's left), Z = roll (+ leans the top toward the character's right; a hanging left limb lifts out).
Poses are authored as flat channel dicts and baked per frame (30 fps) into one action per clip,
pushed to NLA strips so each FBX take is named exactly like the clip.
"""
import bpy, bmesh, math
from mathutils import Vector, Matrix, Quaternion, Euler
import ouat_lib as L

V = Vector
FPS = 30
C = Matrix.Rotation(math.radians(-90), 4, 'X')
C3 = C.to_3x3()


def to_rig(p):
    return C3 @ V(p)


def E(rx=0.0, ry=0.0, rz=0.0):
    """Degrees -> quaternion. Roll (Z) first, then pitch (X), then yaw (Y)."""
    return Euler((math.radians(rx), math.radians(ry), math.radians(rz)), 'ZXY').to_quaternion()


def smooth(x):
    x = max(0.0, min(1.0, x))
    return x * x * (3 - 2 * x)


def smoother(x):
    x = max(0.0, min(1.0, x))
    return x * x * x * (x * (x * 6 - 15) + 10)


# =====================================================================================  model + rig builder
class RigChar:
    def __init__(self, name):
        self.name = name
        self.bones = {}      # name -> (parent, head_world Vector (Z-up build space), length)
        self.order = []
        self.pieces = {}     # obj name -> list of (bm, mat, smooth, face_mat, target)
        self.meta = {}
        self.clips = []      # (name, frames, fn, loop)
        self.alias = {}      # library limb name -> bone name (e.g. ArmL -> WingL)
        self.contacts = {}   # extra ground-contact points: name -> (bone, offset in rig space)

    # ---------------------------------------------------------------- skeleton
    def bone(self, name, parent, head, length=0.08):
        assert parent is None or parent in self.bones, (name, parent)
        self.bones[name] = (parent, V(head), length)
        self.order.append(name)

    def head(self, name):
        """Rest joint position in rig space."""
        return to_rig(self.bones[name][1])

    def parent(self, name):
        return self.bones[name][0]

    def has(self, name):
        return name in self.bones

    def b(self, name):
        """Resolve a library limb name through the alias table."""
        return self.alias.get(name, name)

    # ---------------------------------------------------------------- geometry
    def add(self, target, bm, mat, smooth=True, face_mat=None, obj='Geo'):
        """target: bone name (rigid skin) or fn(co_build_space) -> {bone: weight}."""
        self.pieces.setdefault(obj, []).append((bm, mat, smooth, face_mat, target))
        return self

    # ---------------------------------------------------------------- build Blender objects
    def build(self, collection=None):
        coll = bpy.data.collections.new(self.name)
        (collection or bpy.context.scene.collection).children.link(coll)
        self.coll = coll
        arm = bpy.data.armatures.new(self.name + '_Armature')
        arm.display_type = 'STICK'
        ob = bpy.data.objects.new(self.name, arm)
        coll.objects.link(ob)
        ob.show_in_front = True
        bpy.context.view_layer.objects.active = ob
        for o in bpy.context.view_layer.objects:
            o.select_set(False)
        ob.select_set(True)
        bpy.ops.object.mode_set(mode='EDIT')
        ebs = {}
        for n in self.order:
            par, h, ln = self.bones[n]
            eb = arm.edit_bones.new(n)
            hh = to_rig(h)
            eb.head = hh
            eb.tail = hh + V((0, ln, 0))
            eb.roll = 0.0
            eb.use_deform = True
            if par:
                eb.parent = ebs[par]
                eb.use_connect = False
            ebs[n] = eb
        bpy.ops.object.mode_set(mode='OBJECT')
        ob.rotation_euler = (math.radians(90), 0, 0)
        for pb in ob.pose.bones:
            pb.rotation_mode = 'QUATERNION'
        self.arm = ob
        self.meshes = {}
        for objname, pieces in self.pieces.items():
            self.meshes[objname] = self._build_mesh(objname, pieces, coll)
        return ob

    def _build_mesh(self, objname, pieces, coll):
        bm = bmesh.new()
        dl = bm.verts.layers.deform.verify()
        bidx = {b: i for i, b in enumerate(self.order)}
        mats = []
        for b, mat, smooth_, fmf, tgt in pieces:
            me = bpy.data.meshes.new('tmp_join')
            b.to_mesh(me)
            nv0, nf0 = len(bm.verts), len(bm.faces)
            bm.from_mesh(me)
            bpy.data.meshes.remove(me)
            bm.verts.ensure_lookup_table()
            bm.faces.ensure_lookup_table()
            for i in range(nf0, len(bm.faces)):
                f = bm.faces[i]
                mname = mat
                if fmf is not None:
                    r = fmf(f.calc_center_median(), f.normal)
                    if r:
                        mname = r
                if mname not in mats:
                    mats.append(mname)
                f.material_index = mats.index(mname)
                f.smooth = smooth_
            for i in range(nv0, len(bm.verts)):
                v = bm.verts[i]
                w = {tgt: 1.0} if isinstance(tgt, str) else tgt(v.co.copy())
                tot = sum(w.values()) or 1.0
                for bn, ww in w.items():
                    if ww > 1e-4:
                        v[dl][bidx[bn]] = ww / tot
            b.free()
        for v in bm.verts:
            v.co = C3 @ v.co
        me = bpy.data.meshes.new(self.name + '_' + objname)
        bm.to_mesh(me)
        bm.free()
        for m in mats:
            me.materials.append(L.get_mat(m))
        o = bpy.data.objects.new(objname, me)
        coll.objects.link(o)
        for bn in self.order:
            o.vertex_groups.new(name=bn)
        o.parent = self.arm
        o.matrix_parent_inverse = Matrix.Identity(4)
        md = o.modifiers.new('Armature', 'ARMATURE')
        md.object = self.arm
        return o

    def tris(self):
        n = 0
        for o in self.meshes.values():
            n += sum(len(p.vertices) - 2 for p in o.data.polygons)
        return n


# =====================================================================================  skeleton maths (rig space)
class Skel:
    """Forward/inverse kinematics on the rest skeleton (rig space, identity bone rests)."""

    def __init__(self, rig):
        self.rig = rig
        self.order = rig.order
        self.rest = {b: rig.head(b) for b in rig.order}
        self.par = {b: rig.parent(b) for b in rig.order}
        self.ch = {b: [c for c in rig.order if rig.parent(c) == b] for b in rig.order}

    def off(self, b):
        p = self.par[b]
        return self.rest[b] - (self.rest[p] if p else V((0, 0, 0)))

    def fk(self, q, hips_loc, root='Hips'):
        """q: bone -> local quaternion. Returns bone -> (world pos, world rot) in rig space."""
        W = {}
        for b in self.order:
            p = self.par[b]
            qb = q.get(b, Quaternion())
            if p is None:
                W[b] = (self.rest[b] + V(hips_loc), qb.copy())
            else:
                pp, pr = W[p]
                W[b] = (pp + pr @ self.off(b), pr @ qb)
        return W

    def chain_down(self, b):
        """World pos of a bone's rest child direction helper: list of child bones."""
        return self.ch[b]


def ik2(root_pos, parent_rot, u0, l0, target, pole):
    """Two-bone IK. u0/l0 = rest vectors (parent-local == rig space since rests are identity).
    Returns (q_upper_local, q_lower_local, upper_world_rot, lower_world_rot, reach_ratio)."""
    a, b = u0.length, l0.length
    d = target - root_pos
    dl = d.length
    ratio = dl / (a + b)
    dl = max(abs(a - b) + 1e-4, min(dl, (a + b) * 0.9995))
    dn = d.normalized()
    # elbow position in plane (dn, pole)
    pl = V(pole) - dn * V(pole).dot(dn)
    if pl.length < 1e-6:
        pl = dn.orthogonal()
    pl.normalize()
    cos_a = (a * a + dl * dl - b * b) / (2 * a * dl)
    cos_a = max(-1.0, min(1.0, cos_a))
    sa = math.sqrt(1 - cos_a * cos_a)
    elbow = root_pos + dn * (a * cos_a) + pl * (a * sa)
    t_pt = root_pos + dn * dl
    # upper: rotate rest direction (in world, through parent) to elbow dir; keep twist minimal from the parent frame
    u_rest_w = parent_rot @ u0
    r1 = u_rest_w.rotation_difference(elbow - root_pos)
    Rw1 = r1 @ parent_rot
    l_rest_w = Rw1 @ l0
    r2 = l_rest_w.rotation_difference(t_pt - elbow)
    Rw2 = r2 @ Rw1
    q1 = parent_rot.inverted() @ Rw1
    q2 = Rw1.inverted() @ Rw2
    return q1, q2, Rw1, Rw2, ratio


# =====================================================================================  pose evaluation
LIMBS = {  # limb -> (upper, lower, end) library names
    'footL': ('LegL', 'ShinL', 'FootL'), 'footR': ('LegR', 'ShinR', 'FootR'),
    'handL': ('ArmL', 'ForeArmL', 'HandL'), 'handR': ('ArmR', 'ForeArmR', 'HandR'),
}


class Poser:
    def __init__(self, rig):
        self.rig = rig
        self.sk = Skel(rig)
        self.maxratio = 0.0
        self.warn = []

    def limb(self, lm):
        up, lo, en = LIMBS[lm]
        return self.rig.b(up), self.rig.b(lo), self.rig.b(en)

    def rest_end(self, lm):
        up, lo, en = self.limb(lm)
        return self.sk.rest[en].copy()

    def evaluate(self, ch):
        """ch: channel dict -> (q dict, hips loc Vector)."""
        rig, sk = self.rig, self.sk
        q = {}
        for b in rig.order:
            q[b] = E(ch.get(f'B.{b}.x', 0.0), ch.get(f'B.{b}.y', 0.0), ch.get(f'B.{b}.z', 0.0))
        for nm, bn in rig.alias.items():
            if bn in q and any(f'B.{nm}.{a}' in ch for a in 'xyz'):
                q[bn] = E(ch.get(f'B.{nm}.x', 0.0), ch.get(f'B.{nm}.y', 0.0), ch.get(f'B.{nm}.z', 0.0))
        q['Hips'] = E(ch.get('hips.x', 0.0), ch.get('hips.y', 0.0), ch.get('hips.z', 0.0))
        hl = V((ch.get('hips.px', 0.0), ch.get('hips.py', 0.0), ch.get('hips.pz', 0.0)))
        g = ch.get('ground', 0.0)
        if g > 0:
            W = sk.fk(q, hl)
            low = self.lowest(W)
            hl.y -= g * low
        # IK limbs
        for lm in ('footL', 'footR', 'handL', 'handR'):
            w = ch.get(f'ik.{lm}', 0.0)
            if w <= 0:
                continue
            up, lo, en = self.limb(lm)
            if up not in q:
                continue
            W = sk.fk(q, hl)
            par = sk.par[up]
            ppos, prot = W[par]
            root = W[up][0]
            tgt = V((ch.get(f'tg.{lm}.px', 0.0), ch.get(f'tg.{lm}.py', 0.0), ch.get(f'tg.{lm}.pz', 0.0)))
            if lm.startswith('foot'):
                yaw = ch.get(f'tg.{lm}.yaw', ch.get('hips.y', 0.0) * 0.5)
                pole = E(0, yaw, 0) @ V((0, 0, 1))
                pole = pole + V((ch.get(f'tg.{lm}.polex', 0.0), 0, 0))
            else:
                side = 1 if lm.endswith('L') else -1
                pole = V((ch.get(f'tg.{lm}.polex', 0.5 * side), ch.get(f'tg.{lm}.poley', -0.4), ch.get(f'tg.{lm}.polez', -1.0)))
                pole = prot @ pole
            u0 = sk.off(lo)
            l0 = sk.off(en)
            q1, q2, Rw1, Rw2, ratio = ik2(root, prot, u0, l0, tgt, pole)
            if w >= 0.999 and ratio > 1.0005:
                self.warn.append((lm, round(ratio, 3)))
            if w >= 0.999:
                self.maxratio = max(self.maxratio, ratio)
            q[up] = q[up].slerp(q1, w) if w < 1 else q1
            q[lo] = q[lo].slerp(q2, w) if w < 1 else q2
            if f'tg.{lm}.pitch' in ch and en in q:
                yaw = ch.get(f'tg.{lm}.yaw', ch.get('hips.y', 0.0) * 0.5)
                want = E(ch[f'tg.{lm}.pitch'], yaw, ch.get(f'tg.{lm}.roll', 0.0))
                W2 = sk.fk(q, hl)
                lr = W2[lo][1]
                qe = lr.inverted() @ want
                q[en] = q[en].slerp(qe, w) if w < 1 else qe
        return q, hl

    def lowest(self, W):
        """Lowest ground-contact height (rig space y) given world FK."""
        rig = self.rig
        ys = []
        for side in 'LR':
            for nm, (bn, off) in rig.contacts.items():
                pass
        for nm, (bn, off) in rig.contacts.items():
            if bn in W:
                p, r = W[bn]
                ys.append((p + r @ off).y)
        return min(ys) if ys else 0.0


# =====================================================================================  keyed clips
class Keys:
    """Keyed channel animation. keys: list of (time_s, {channel: value}, opts).
    Each key inherits all channels from the previous key (first key inherits `base`).
    Cubic Hermite (Catmull-Rom tangents); opts 'hold' -> zero tangent (puppet stop), 'snap' -> sharper ease."""

    def __init__(self, base, keys, loop=False, tension=0.0):
        self.loop = loop
        self.tension = tension
        full = []
        cur = dict(base)
        for k in keys:
            t, d = k[0], k[1]
            opts = k[2] if len(k) > 2 else ''
            cur = dict(cur)
            cur.update(d)
            full.append((t, cur, opts))
        chans = set()
        for _, d, _ in full:
            chans |= set(d)
        for _, d, _ in full:
            for c in chans:
                d.setdefault(c, base.get(c, 0.0))
        self.full = full
        self.chans = chans
        self.T = full[-1][0]

    def __call__(self, t):
        F = self.full
        n = len(F)
        if t <= F[0][0]:
            return dict(F[0][1])
        if t >= F[-1][0]:
            return dict(F[-1][1])
        i = 0
        while i < n - 2 and t > F[i + 1][0]:
            i += 1
        t0, d0, o0 = F[i]
        t1, d1, o1 = F[i + 1]
        h = t1 - t0
        u = (t - t0) / h if h > 0 else 1.0
        if 'snap' in o1:
            u = 1 - (1 - u) ** 2.2   # fast attack, soft landing (string pull)
        out = {}
        for c in self.chans:
            p0, p1 = d0[c], d1[c]
            m0 = self._tan(i, c, h) if 'hold' not in o0 else 0.0
            m1 = self._tan(i + 1, c, h) if 'hold' not in o1 else 0.0
            u2, u3 = u * u, u * u * u
            out[c] = (2 * u3 - 3 * u2 + 1) * p0 + (u3 - 2 * u2 + u) * m0 + (-2 * u3 + 3 * u2) * p1 + (u3 - u2) * m1
        return out

    def _tan(self, i, c, h):
        F = self.full
        n = len(F)
        if i == 0 or i == n - 1:
            if not self.loop:
                return 0.0
            # loop: neighbours wrap (last key == first key)
            ta, va = F[-2][0] - self.T, F[-2][1][c]
            tb, vb = F[1][0], F[1][1][c]
            t0 = 0.0
        else:
            ta, va = F[i - 1][0], F[i - 1][1][c]
            tb, vb = F[i + 1][0], F[i + 1][1][c]
        if tb - ta <= 0:
            return 0.0
        return (1 - self.tension) * (vb - va) / (tb - ta) * h


def add_ch(*dicts):
    out = {}
    for d in dicts:
        for k, v in d.items():
            out[k] = out.get(k, 0.0) + v
    return out


# =====================================================================================  bake + export
def bake(rig, report):
    """Bake every clip in rig.clips to its own action + NLA strip."""
    ob = rig.arm
    ob.animation_data_create()
    P = Poser(rig)
    pbs = ob.pose.bones
    for name, frames, fn, loop in rig.clips:
        act = bpy.data.actions.new(name)
        act.use_fake_user = True
        ob.animation_data.action = act
        prevq = {}
        P.maxratio = 0.0
        P.warn = []
        for f in range(frames + 1):
            t = f / FPS
            if loop and f == frames:
                t = 0.0   # exact loop closure
            ch = fn(t)
            post = rig.meta.get('post')
            if post:
                ch = post(ch)
            q, hl = P.evaluate(ch)
            for b in rig.order:
                pb = pbs[b]
                qq = q.get(b, Quaternion())
                if b in prevq and prevq[b].dot(qq) < 0:
                    qq = -qq
                prevq[b] = qq
                pb.rotation_quaternion = qq
                pb.keyframe_insert('rotation_quaternion', frame=f, group=b)
                if b == 'Hips':
                    pb.location = hl
                    pb.keyframe_insert('location', frame=f, group=b)
        report.append(dict(clip=name, frames=frames, seconds=round(frames / FPS, 3), loop=loop,
                           ik_max_reach=round(P.maxratio, 3), ik_overreach=sorted(set(P.warn))[:4]))
        act.frame_range = (0, frames)
        ob.animation_data.action = None
        tr = ob.animation_data.nla_tracks.new()
        tr.name = name
        st = tr.strips.new(name, 0, act)
        st.name = name
        st.frame_end = frames
        tr.mute = False
    # rest pose for the file itself
    for pb in pbs:
        pb.rotation_quaternion = Quaternion()
        pb.location = (0, 0, 0)


def export(rig, path):
    ob = rig.arm
    for o in bpy.context.view_layer.objects:
        o.select_set(False)
    ob.select_set(True)
    for m in rig.meshes.values():
        m.select_set(True)
    bpy.context.view_layer.objects.active = ob
    loc = ob.location.copy()
    ob.location = (0, 0, 0)
    bpy.ops.export_scene.fbx(
        filepath=path, use_selection=True, object_types={'ARMATURE', 'MESH'},
        global_scale=1.0, apply_unit_scale=True, apply_scale_options='FBX_SCALE_ALL',
        bake_space_transform=False, axis_forward='-Z', axis_up='Y',
        use_mesh_modifiers=False, mesh_smooth_type='FACE', use_mesh_edges=False, use_triangles=True,
        use_tspace=False, use_custom_props=False, add_leaf_bones=False,
        primary_bone_axis='Y', secondary_bone_axis='X', armature_nodetype='NULL',
        use_armature_deform_only=False,
        bake_anim=True, bake_anim_use_all_bones=True, bake_anim_use_nla_strips=True,
        bake_anim_use_all_actions=False, bake_anim_force_startend_keying=True,
        bake_anim_step=1.0, bake_anim_simplify_factor=0.0,
        path_mode='STRIP', embed_textures=False, use_metadata=True)
    ob.location = loc
