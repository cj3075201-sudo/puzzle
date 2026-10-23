# -*- coding: utf-8 -*-
"""Round-6 clips (10/23 '대타 설계' story): extra takes appended to the round-4 characters + the Collector.
Same conventions as ouat_anim.py (rig space Y up, +Z forward, +X = char left, channels B.<bone>.x/y/z ...).
Every existing take stays untouched; add_clips(R) only APPENDS new names.
"""
import math
from mathutils import Vector
from ouat_rig import Keys, Poser, FPS, E, smooth
import ouat_anim as A
from ouat_anim import stand, hand_target, keyed, bump, loopsin, sgn, head_point, kneel_targets

V = Vector
TAU = 2 * math.pi


# =====================================================================================  helpers
class Attach:
    """Pin IK hands to points fixed on a bone (rig-space offset from the bone joint at rest), evaluated per frame."""

    def __init__(self, rig):
        self.rig = rig
        self.P = Poser(rig)

    def point(self, ch, bone, off):
        c = {k: v for k, v in ch.items() if not k.startswith('ik.hand')}
        q, hl = self.P.evaluate(c)
        W = self.P.sk.fk(q, hl)
        p, r = W[bone]
        return p + r @ V(off)

    def pin(self, D, ch, side, bone, off, pole=None, w=1.0, delta=(0, 0, 0)):
        p = self.point(ch, bone, off) + V(delta)
        hand_target(D, ch, side, (p.x, p.y, p.z), w, pole)
        return ch


def wrap(clip, fn2):
    """clip = (frames, fn, loop); fn2(ch, t) -> ch."""
    frames, fn, loop = clip
    return frames, (lambda t: fn2(fn(t), t)), loop


def periodic(base_clip, frames):
    """Repeat a short locomotion cycle so a longer loop can carry slower overlays (e.g. a look-back)."""
    _, fn, _ = base_clip
    return frames, fn, True


def ease_env(t, t0, t1, a=0.15):
    """1 inside [t0, t1] with smooth ramps of length a."""
    return smooth((t - t0) / a) * (1 - smooth((t - (t1 - a)) / a))


# =====================================================================================  KINOPIO
K_NOSE_ROOT = (0.0, 0.115, 0.075)     # Head-local (rig space) = Nose bone joint
K_NOSE_TIP = (0.01, 0.03, 0.32)       # Nose-local tip


def k_filenose(R, D):
    """Guilty glance left/right, lean in, rub the long nose sideways on a stone 4x, glance back, straighten (2.0 s)."""
    st = stand(R, D)
    gl = dict(st, **{'B.Head.y': 45, 'B.Body.y': 10, 'B.Head.x': -2})
    gr = dict(st, **{'B.Head.y': -45, 'B.Body.y': -10, 'B.Head.x': -2})
    lean = dict(st)
    lean.update({'hips.x': 6, 'B.Body.x': 26, 'B.Head.x': 8, 'hips.py': st['hips.py'] - 0.08 * D.leg, 'hips.pz': 0.02})
    lean['tg.footL.pz'] = D.ank['L'].z + 0.06
    lean['tg.footR.pz'] = D.ank['R'].z - 0.05
    for s in 'LR':   # hands braced on the thighs (the long nose reaches the stone ~0.5 m ahead, the hands cannot)
        hand_target(D, lean, s, (sgn(s) * 0.08, 0.32, 0.1), 1.0, (sgn(s) * 1.0, 0.2, -0.4))
    rubL = dict(lean, **{'B.Body.y': 9, 'B.Head.y': 11, 'B.Head.z': -4, 'hips.px': 0.006})
    rubR = dict(lean, **{'B.Body.y': -9, 'B.Head.y': -11, 'B.Head.z': 4, 'hips.px': -0.006})
    back = dict(st, **{'hips.y': 10, 'B.Body.y': 25, 'B.Head.y': 60, 'B.Head.x': -4, 'B.ArmL.x': 10})
    ik0 = {'ik.handL': 0.0, 'ik.handR': 0.0}
    keys = [(0.0, dict(st, **ik0)), (0.16, dict(gl, **ik0), 'snap'), (0.34, dict(gl, **ik0)), (0.46, dict(gr, **ik0), 'snap'),
            (0.58, dict(gr, **ik0)), (0.72, lean, 'snap'),
            (0.86, rubL), (1.0, rubR), (1.14, rubL), (1.28, rubR), (1.42, rubL), (1.52, lean),
            (1.66, dict(back, **ik0), 'snap'), (1.8, dict(back, **ik0)), (2.0, dict(st, **ik0))]
    return keyed(st, keys)


def k_hidenose(R, D):
    """Snap the left (finished) hand over the nose root, head turning away (0.6 s, ends covering)."""
    st = stand(R, D)
    at = Attach(R)
    cov = dict(st, **{'B.Body.y': -26, 'B.Head.y': 50, 'B.Head.x': 14, 'B.Body.x': 6, 'hips.py': st['hips.py'] - 0.02 * D.leg,
                      'B.ArmR.z': -14, 'B.ArmR.x': 8})
    at.pin(D, cov, 'L', 'Head', (0.01, 0.105, 0.085), (1.0, -0.6, -0.4))
    over = dict(cov, **{'B.Head.x': 17, 'hips.py': st['hips.py'] - 0.05 * D.leg})
    at.pin(D, over, 'L', 'Head', (0.01, 0.105, 0.085), (1.0, -0.6, -0.4))
    keys = [(0.0, dict(st, **{'ik.handL': 0.0})), (0.12, over, 'snap'), (0.3, cov), (0.6, cov)]
    return keyed(st, keys)


def k_grin(R, D):
    """'Trust me': hands behind the back, head tilts, two quick shoulder bounces, lean in (1.4 s)."""
    st = stand(R, D)
    tl = dict(st, **{'B.Head.z': -20, 'B.Head.y': 8, 'B.Head.x': -4, 'B.Body.z': -5, 'B.Body.x': 6, 'hips.pz': 0.01})
    for s in 'LR':
        hand_target(D, tl, s, (sgn(s) * 0.045, 0.415, -0.085), 1.0, (sgn(s) * 1.0, -0.3, 0.6))
    up = dict(tl, **{'hips.py': tl['hips.py'] + 0.022 * D.leg, 'B.Body.x': 2, 'B.Head.z': -24})
    for s in 'LR':
        up[f'tg.foot{s}.pitch'] = 18
    ik0 = {'ik.handL': 0.0, 'ik.handR': 0.0}
    keys = [(0.0, dict(st, **ik0)), (0.26, tl, 'snap'), (0.42, up, 'snap'), (0.56, tl), (0.7, up, 'snap'), (0.84, tl),
            (1.15, tl), (1.4, dict(st, **ik0))]
    return keyed(st, keys)


def shout_clip(R, D, mouth, spread, fwd=0.02, lean=10, hop=0.0):
    """Hands cupped beside the mouth, inhale, lean in and shout, two word beats, release (1.2 s)."""
    st = stand(R, D)
    at = Attach(R)
    inh = dict(st, **{'B.Body.x': -8, 'B.Head.x': -10, 'hips.x': -2})
    sh = dict(st, **{'B.Body.x': lean, 'B.Head.x': -8, 'hips.x': 3, 'hips.pz': 0.02 * D.H})
    sh['tg.footL.pz'] = D.ank['L'].z + 0.12 * D.leg
    if hop:
        sh['hips.py'] = st['hips.py'] + hop
        for s in 'LR':
            sh[f'tg.foot{s}.pitch'] = 20
    beat = dict(sh, **{'B.Body.x': lean + 5, 'B.Head.x': -2})
    for key in (inh, sh, beat):
        for s in 'LR':
            m = V(mouth) + V((sgn(s) * spread, -0.005, fwd))
            at.pin(D, key, s, 'Head', tuple(m), (sgn(s) * 1.0, -0.7, -0.3))
    ik0 = {'ik.handL': 0.0, 'ik.handR': 0.0}
    keys = [(0.0, dict(st, **ik0)), (0.26, inh), (0.42, sh, 'snap'), (0.6, beat), (0.72, sh, 'snap'), (0.9, sh), (1.2, dict(st, **ik0))]
    return keyed(st, keys)


def scared_run(R, D):
    """RunAway*: 4.0 m/s sprint (same stride as Run) with panicky arms up, head ducked and one look back (1.2 s = 4 strides)."""
    def extra(ch, t, ph, cL, b_):
        ch['B.Nose.x'] = 2 * b_
        ch['B.Head.z'] = ch.get('B.Head.z', 0) + 4 * cL
        return ch
    base = A.locomotion(R, D, 4.0, 9, stance=0.23, lift=0.07, bob=0.026, lean=17, arm=20, yaw=8,
                        roll=5, elbow=40, crouch=0.04, th_off=35, extra=extra)
    _, fn9, _ = base
    T = 1.2

    def f(t):
        ch = fn9(t)
        ph = (t / 0.3) % 1.0
        c = math.cos(TAU * ph)
        for s in 'LR':   # flailing arms held high
            k = c * sgn(s)
            ch[f'B.Arm{s}.x'] = -95 + 28 * k
            ch[f'B.Arm{s}.z'] = sgn(s) * (32 + 8 * math.sin(TAU * ph * 2 + (0 if s == 'L' else 1.3)))
            ch[f'B.ForeArm{s}.x'] = -70 - 18 * max(0.0, -k)
            ch[f'B.Hand{s}.x'] = -20
        ch['B.Head.x'] = ch.get('B.Head.x', 0) + 10
        lb = ease_env(t, 0.45, 0.95, 0.15)
        ch['B.Head.y'] = ch.get('B.Head.y', 0) + 70 * lb
        ch['B.Body.y'] = ch.get('B.Body.y', 0) + 18 * lb
        ch['B.Head.x'] -= 14 * lb
        return ch
    return int(round(T * FPS)), f, True


def sit_pose(R, D):
    st = stand(R, D)
    s = dict(st)
    seat = D.H * 0.06
    s['hips.py'] = seat - D.hips.y + 0.02 * D.H
    s['hips.x'] = -12
    s['B.Body.x'] = 32
    s['B.Head.x'] = 18
    for k in 'LR':
        s[f'tg.foot{k}.pz'] = D.ank[k].z + 0.72 * D.leg
        s[f'tg.foot{k}.px'] = D.ank[k].x * 1.1
        s[f'tg.foot{k}.pitch'] = -5
        kn = (D.ank[k].x * 1.05, seat + 0.55 * D.leg, D.ank[k].z + 0.45 * D.leg)
        hand_target(D, s, k, (kn[0] * 0.2, kn[1] - 0.12 * D.leg, kn[2] + 0.12 * D.leg), 1.0, (sgn(k) * 1.0, 0.0, -0.5))
    return s


def k_sulk(R, D, T=4.0):
    """Sulk*: sitting hugging the knees, face buried and turned away; a huff (shoulders up-drop) and a 'hmph' head turn."""
    s = sit_pose(R, D)
    s['B.Body.x'] = 38
    s['B.Head.x'] = 30
    s['B.Head.y'] = -22
    s['hips.x'] = -14
    huff = dict(s, **{'B.Body.x': 30, 'B.Head.x': 16, 'B.Head.y': -16, 'hips.py': s['hips.py'] + 0.012})
    hmph = dict(s, **{'B.Head.y': -42, 'B.Head.z': 8, 'B.Head.x': 22, 'B.Body.y': -6})
    keys = [(0.0, s), (0.8, s), (1.15, huff, 'snap'), (1.5, s), (2.3, s), (2.55, hmph, 'snap'), (3.3, hmph), (4.0, s)]
    k = Keys(s, keys, loop=True)

    def f(t):
        ch = k(t)
        ch['hips.x'] += 2.5 * loopsin(t, T)
        ch['B.Body.x'] += 1.2 * loopsin(t, T, 2, 0.1)
        return ch
    return int(round(T * FPS)), f, True


def k_cry(R, D):
    """Cry: both hands pressed to the sides of the face, head bowed, shoulders shaking in sob hitches (2.0 s)."""
    st = stand(R, D)
    at = Attach(R)
    c = dict(st, **{'B.Head.x': 24, 'B.Body.x': 10, 'hips.x': 2, 'hips.py': st['hips.py'] - 0.03 * D.leg})
    ik0 = {'ik.handL': 0.0, 'ik.handR': 0.0}
    k = Keys(st, [(0.0, dict(st, **ik0)), (0.3, dict(c, **{'ik.handL': 1.0, 'ik.handR': 1.0}), 'snap'), (1.65, dict(c, **{'ik.handL': 1.0, 'ik.handR': 1.0})),
                  (2.0, dict(st, **ik0))])

    def f(t):
        ch = k(t)
        env = ease_env(t, 0.25, 1.75, 0.2)
        # sob hitches: 3 bursts of quick shakes
        sob = sum(bump(t, t0, 0.32, 0.2) for t0 in (0.4, 0.85, 1.3))
        shake = math.sin(t * 46) * env
        ch['B.Body.x'] += -4 * sob + 1.6 * shake
        ch['hips.py'] += 0.012 * sob * D.leg + 0.004 * shake * D.leg
        ch['B.Head.x'] += 5 * sob
        ch['B.Head.z'] = ch.get('B.Head.z', 0) + 2.0 * math.sin(t * 31) * env
        w = ch.get('ik.handL', 0.0)
        if w > 0:
            for s in 'LR':
                at.pin(D, ch, s, 'Head', (sgn(s) * 0.105, 0.075, 0.045), (sgn(s) * 1.0, -0.8, 0.0), w)
        return ch
    return 60, f, False


def k_tugsleeve(R, D):
    """Grab the hero's sleeve (hold point ~ (0.07, 0.57, 0.15) Kinopio-root space) and tug it twice, looking up (1.0 s)."""
    st = stand(R, D)
    g = dict(st, **{'B.Head.x': -26, 'B.Head.y': 6, 'B.Body.x': 6, 'hips.pz': 0.01})
    g['tg.footL.pz'] = D.ank['L'].z + 0.06
    hand_target(D, g, 'L', (0.07, 0.57, 0.15), 1.0, (1.0, -0.5, -0.4))
    hand_target(D, g, 'R', (-0.02, 0.52, 0.12), 1.0, (-1.0, -0.6, -0.4))
    pull = dict(g, **{'hips.x': -6, 'B.Body.x': -6, 'hips.pz': -0.03, 'B.Head.x': -30, 'hips.py': g['hips.py'] - 0.02})
    pull['tg.handL.pz'] = 0.10
    pull['tg.handL.py'] = 0.55
    pull['tg.handR.pz'] = 0.08
    ik0 = {'ik.handL': 0.0, 'ik.handR': 0.0}
    keys = [(0.0, dict(st, **ik0)), (0.2, g, 'snap'), (0.34, pull, 'snap'), (0.48, g), (0.62, pull, 'snap'), (0.8, g), (1.0, dict(st, **ik0))]
    return keyed(st, keys)


def k_pointself(R, D):
    """'Me': left hand taps the chest twice with the elbow out wide, leaning back and looking down at himself (1.2 s)."""
    st = stand(R, D)
    a = dict(st, **{'B.Body.x': -9, 'B.Head.x': 14, 'hips.x': -3, 'B.Body.y': 8, 'B.ArmR.z': -16, 'hips.pz': -0.01})
    hand_target(D, a, 'L', (0.0, 0.49, 0.1), 1.0, (1.0, 0.1, 0.0))
    tap = dict(a, **{'B.Head.x': 20, 'B.Body.x': -6})
    tap['tg.handL.pz'] = 0.078
    ik0 = {'ik.handL': 0.0}
    keys = [(0.0, dict(st, **ik0)), (0.25, a, 'snap'), (0.38, tap, 'snap'), (0.5, a), (0.62, tap, 'snap'), (0.9, a), (1.2, dict(st, **ik0))]
    return keyed(st, keys)


def k_pointother(R, D):
    """'You': step in, lean forward and thrust the left arm out and up at the listener's face (arm clear of the body), two jabs (1.2 s)."""
    st = stand(R, D)
    p = dict(st, **{'B.ArmL.x': -112, 'B.ArmL.z': 14, 'B.ArmL.y': 0, 'B.ForeArmL.x': 0, 'B.HandL.x': -4,
                    'B.Body.x': 12, 'B.Body.y': -18, 'hips.y': -6, 'B.Head.x': -10, 'B.Head.y': 14, 'B.ArmR.x': 14, 'B.ArmR.z': -10,
                    'hips.pz': 0.03})
    p['tg.footL.pz'] = D.ank['L'].z + 0.09
    jab = dict(p, **{'B.Body.x': 17, 'B.ArmL.x': -106, 'hips.pz': 0.045})
    keys = [(0.0, st), (0.22, jab, 'snap'), (0.36, p), (0.5, jab, 'snap'), (0.64, p), (0.95, p), (1.2, st)]
    return keyed(st, keys)


def kinopio(R, D):
    R.meta['mouth'] = (0.0, 0.07, 0.08)
    c = R.clips
    c.append(('FileNose',) + k_filenose(R, D))
    c.append(('HideNose',) + k_hidenose(R, D))
    c.append(('Grin',) + k_grin(R, D))
    c.append(('ShoutWord',) + shout_clip(R, D, (0.0, 0.08, 0.03), 0.095, fwd=0.02, lean=12, hop=0.0))
    c.append(('RunAway',) + scared_run(R, D))
    c.append(('Sulk',) + k_sulk(R, D))
    c.append(('Cry',) + k_cry(R, D))
    c.append(('TugSleeve',) + k_tugsleeve(R, D))
    c.append(('PointSelf',) + k_pointself(R, D))
    c.append(('PointOther',) + k_pointother(R, D))
    R.meta.setdefault('speeds', {})['RunAway'] = 4.0


# =====================================================================================  CHIEF
CHIEF_TIE = (0.0, 0.82, 0.88)   # cord knot point (chief-root space): a 1.25 m hero's chest, hero root ~0.95 m in front


def chief_kneel(D, st):
    """One knee down (right), left foot forward (as c_kneel), torso leaning in so the crown stays high above a child."""
    k = dict(st)
    a, b, kr = D.a, D.b, D.kr
    kzR = D.ank['R'].z - 0.05 * D.leg
    k['tg.footR.py'] = kr + 0.02 * D.leg
    k['tg.footR.pz'] = kzR - b * 0.95
    k['tg.footR.pitch'] = 70
    hy = kr + a * 0.97
    k['hips.py'] = hy - D.hipj['R'].y
    k['hips.pz'] = kzR - D.hipj['R'].z
    k['tg.footL.pz'] = D.ank['L'].z + a * 0.95
    k['tg.footL.py'] = D.ank['L'].y
    k.update({'B.Body.x': 26, 'B.Head.x': 16, 'B.Canopy.x': -12, 'hips.x': 4})
    return k


def c_tiecord(R, D):
    """Kneel on one knee, both hands to the chest of a child in front, wrap the cord twice, pull it tight, nod, rise (2.0 s).
    The crown stays above head height of a 1.25 m hero standing ~0.95 m in front."""
    st = stand(R, D)
    kn = chief_kneel(D, st)
    tx, ty, tz = CHIEF_TIE

    def hands(ch, dl, dr):
        hand_target(D, ch, 'L', (tx + 0.11 + dl[0], ty + dl[1], tz + dl[2]), 1.0, (1.0, 0.3, -0.6))
        hand_target(D, ch, 'R', (tx - 0.11 + dr[0], ty + dr[1], tz + dr[2]), 1.0, (-1.0, 0.3, -0.6))
        return ch
    down = dict(kn, **{'B.Body.x': 10, 'B.Head.x': 4})
    for s_ in 'LR':
        down[f'B.Arm{s_}.x'] = -30
    reach = hands(dict(kn), (0.05, 0.08, -0.1), (-0.05, 0.08, -0.1))
    near = hands(dict(kn), (0, 0, 0), (0, 0, 0))
    wraps = []
    for i in range(4):   # hands circle around each other (two wraps)
        a = TAU * i / 4
        r = 0.07
        wraps.append(hands(dict(kn), (-0.06 + r * math.cos(a), r * math.sin(a), 0.03 * math.sin(a)),
                           (0.06 - r * math.cos(a), -r * math.sin(a), -0.03 * math.sin(a))))
    pull = hands(dict(kn, **{'B.Body.x': 22}), (0.15, 0.02, -0.05), (-0.15, 0.02, -0.05))
    nod = dict(pull, **{'B.Head.x': 26})
    ik0 = {'ik.handL': 0.0, 'ik.handR': 0.0}
    keys = [(0.0, dict(st, **ik0)), (0.3, dict(down, **ik0), 'snap'), (0.45, reach), (0.55, near), (0.65, wraps[1]), (0.75, wraps[2]),
            (0.85, wraps[3]), (0.95, wraps[0]), (1.05, wraps[1]), (1.15, wraps[2]), (1.25, near), (1.36, pull, 'snap'), (1.5, nod),
            (1.62, dict(down, **ik0)), (2.0, dict(st, **ik0))]
    return keyed(st, keys)


def c_proclaim(R, D, T=4.0):
    """Proclaim*: both arms raised high and wide, face up, slow ceremonial sway, crown swaying."""
    st = stand(R, D)

    def f(t):
        ch = dict(st)
        br = loopsin(t, T)
        ch['B.Body.x'] = -6 + 1.5 * br
        ch['B.Head.x'] = -16 + 3 * loopsin(t, T, 1, 0.15)
        ch['hips.py'] += 0.01 * D.leg * (0.5 + 0.5 * br)
        ch['B.Body.z'] = 3 * loopsin(t, T, 1, 0.25)
        ch['B.Head.z'] = 3 * loopsin(t, T, 1, 0.35)
        ch['B.Canopy.z'] = 5 * loopsin(t, T, 1, 0.4)
        ch['B.Canopy.x'] = -4 + 2 * loopsin(t, T, 2, 0.1)
        for s in 'LR':
            pulse = loopsin(t, T, 2, 0.05 + (0.08 if s == 'R' else 0))
            ch[f'B.Arm{s}.x'] = -150 - 6 * pulse
            ch[f'B.Arm{s}.z'] = sgn(s) * (38 + 4 * pulse)
            ch[f'B.ForeArm{s}.x'] = -14 + 6 * pulse
            ch[f'B.Hand{s}.x'] = -10
        return ch
    return int(round(T * FPS)), f, True


def chief(R, D):
    R.clips.append(('TieCord',) + c_tiecord(R, D))
    R.clips.append(('Proclaim',) + c_proclaim(R, D))


# =====================================================================================  HERO
def h_squeeze(R, D, v=0.35, T=2.0):
    """Squeeze: body turned side-on (chest to the left wall), shuffling right-shoulder first through a narrow crack.
    In place; feet stay planted when the root moves forward (+Z) at v = 0.35 m/s. Two shuffles, frame 60 == frame 0."""
    st = stand(R, D)
    yaw = 85.0
    cyc = 1.0
    stepL = v * cyc

    def foot_z(u, lift_u, land_u, z_land):
        """planted foot slides back at v; swing between lift_u and land_u (u in cycle units, wraps)."""
        dur = (land_u - lift_u) % 1.0
        since_land = (u - land_u) % 1.0
        if since_land <= 1.0 - dur:   # planted
            return z_land - v * cyc * since_land, 0.0
        s = (u - lift_u) % 1.0 / dur
        z0 = z_land - v * cyc * (1.0 - dur)
        z = z0 + (z_land - z0) * smooth(s)
        return z, math.sin(math.pi * s)

    def f(t):
        ch = dict(st)
        u = (t / cyc) % 1.0
        zR, lR = foot_z(u, 0.05, 0.35, 0.21)
        zL, lL = foot_z(u, 0.55, 0.85, -0.03)
        for s, z, l in (('L', zL, lL), ('R', zR, lR)):
            ch[f'tg.foot{s}.px'] = 0.01 * sgn(s)
            ch[f'tg.foot{s}.pz'] = z
            ch[f'tg.foot{s}.py'] = D.ank[s].y + 0.045 * l
            ch[f'tg.foot{s}.pitch'] = -6 * l
            ch[f'tg.foot{s}.yaw'] = yaw
        mid = 0.5 * (zL + zR)
        ch['hips.y'] = yaw
        ch['hips.pz'] = mid * 0.85
        sep = abs(zR - zL)
        ch['hips.py'] = -0.035 - 0.12 * max(0.0, sep - 0.12) - 0.012 * (lL + lR)
        effort = bump(u, 0.05, 0.4, 0.3)
        ch['hips.z'] = 2 * effort
        ch['B.Body.x'] = -4 - 3 * effort
        ch['B.Body.y'] = -12
        ch['B.Body.z'] = 4 * effort
        ch['B.Head.y'] = -62 + 6 * effort
        ch['B.Head.x'] = 4
        ch['B.Head.z'] = -4
        # lead (right) arm slides along the wall ahead, trailing arm low behind
        ch['B.ArmR.z'] = -62 - 12 * effort
        ch['B.ArmR.x'] = -18
        ch['B.ForeArmR.x'] = -25 + 15 * effort
        ch['B.HandR.z'] = -20
        ch['B.ArmL.z'] = 24
        ch['B.ArmL.x'] = 10
        ch['B.ForeArmL.x'] = -20
        ch['B.Cape.x'] = 2
        ch['B.Cape.z'] = 6
        return ch
    return int(round(T * FPS)), f, False


def h_carry(R, D):
    """Carry*: brisk walk 1.8 m/s hugging the satchel (or any prop) to the chest with both arms."""
    at = Attach(R)

    def walk_extra(ch, t, ph, cL, b_):
        ch['B.Cape.x'] = 6 + 5 * b_
        return ch
    base = A.locomotion(R, D, 1.8, 18, stance=0.55, lift=0.06, bob=0.022, lean=6, arm=0, yaw=6,
                        roll=3, elbow=14, crouch=-0.03, extra=walk_extra)

    def ov(ch, t):
        ch['B.Head.x'] = ch.get('B.Head.x', 0) + 4
        for s in 'LR':
            at.pin(D, ch, s, 'Body', HERO_HOLD_BODY[s], (sgn(s) * 1.0, -0.6, -0.2))
        return ch
    return wrap(base, ov)


HERO_HOLD = (0.0, 0.105, 0.17)    # Body-local (rig space) centre of the hugged object (satchel prop attach point)
HERO_HOLD_BODY = {'L': (0.065, 0.095, 0.165), 'R': (-0.06, 0.11, 0.16)}


def h_startle(R, D):
    """Startle: jump back on the spot (right foot steps back), arms snap up in front, cape flips, settle and return (0.8 s)."""
    st = stand(R, D)
    j = dict(st)
    j.update({'hips.pz': -0.07, 'hips.py': st['hips.py'] + 0.03, 'hips.x': -4, 'B.Body.x': -16, 'B.Head.x': -12, 'B.Head.z': 6,
              'B.Cape.x': 28})
    j['tg.footR.pz'] = D.ank['R'].z - 0.17
    j['tg.footR.py'] = D.ank['R'].y + 0.06
    j['tg.footL.pz'] = D.ank['L'].z - 0.03
    for s in 'LR':
        j[f'B.Arm{s}.x'] = -62
        j[f'B.Arm{s}.z'] = sgn(s) * 12
        j[f'B.ForeArm{s}.x'] = -95
        j[f'B.Hand{s}.x'] = 15
    land = dict(j, **{'hips.py': st['hips.py'] - 0.06, 'B.Body.x': -6, 'B.Head.x': -6, 'B.Cape.x': 8})
    land['tg.footR.py'] = D.ank['R'].y
    land['tg.footR.pitch'] = 18
    hold = dict(land, **{'B.Body.x': -8, 'B.Head.x': -8})
    keys = [(0.0, st), (0.1, j, 'snap'), (0.22, land), (0.5, hold), (0.8, st)]
    return keyed(st, keys)


def hero(R, D):
    R.clips.append(('Squeeze',) + h_squeeze(R, D))
    R.clips.append(('Carry',) + h_carry(R, D))
    R.clips.append(('Startle',) + h_startle(R, D))
    R.meta.setdefault('speeds', {})['Carry'] = 1.8
    R.meta['squeeze_speed'] = 0.35


# =====================================================================================  VILLAGERS (+ Collector body)
def v_carry(R, D, side='R', frames=16, lean_side=7):
    """Carry*: walk 2.2 m/s with a sack on one shoulder (hand on top of it), the other arm swinging; heavier gait."""
    at = Attach(R)
    o = 'L' if side == 'R' else 'R'
    sg = sgn(side)

    def wob(ch, t, ph, cL, b_):
        ch['B.Head.z'] = ch.get('B.Head.z', 0) + 2 * cL
        return ch
    base = A.locomotion(R, D, 2.2, frames, stance=0.34, lift=0.06, bob=0.03, lean=8, arm=18, yaw=6,
                        roll=4, elbow=14, crouch=0.0, extra=wob)
    hold = V(D.sh[side]) - V(D.waist) + V((sg * -0.02, 0.07, 0.07))

    def ov(ch, t):
        ch['B.Body.z'] = ch.get('B.Body.z', 0) + sg * lean_side * 0.6     # lean away from the load (top toward the free side)
        ch['B.Head.z'] = ch.get('B.Head.z', 0) + sg * 10
        ch[f'B.Arm{o}.x'] = ch.get(f'B.Arm{o}.x', 0) * 1.3
        at.pin(D, ch, side, 'Body', tuple(hold), (sg * 1.0, -0.4, -0.6))
        return ch
    return wrap(base, ov)


def v_offer(R, D):
    """Offer: small bow while lifting both hands forward-up (food held up toward someone), hold there (1.5 s, ends held)."""
    st = stand(R, D)
    sh = D.sh['L']
    rp = R.meta.get('rest_pose', {})
    bodyx = rp.get('B.Body.x', 0.0)
    up = dict(st, **{'B.Body.x': bodyx + (14 if bodyx < 5 else 0), 'B.Head.x': rp.get('B.Head.x', 0.0) - (2 if bodyx < 5 else 8), 'hips.x': 3 if bodyx < 5 else -4})
    y = sh.y + 0.13
    z = sh.z + D.arm * 0.68
    for s in 'LR':
        hand_target(D, up, s, (sgn(s) * 0.06, y, z), 1.0, (sgn(s) * 1.0, -0.8, -0.2))
        up[f'tg.hand{s}.pitch'] = -40
    push = dict(up)
    for s in 'LR':
        push[f'tg.hand{s}.pz'] = z + 0.04
        push[f'tg.hand{s}.py'] = y + 0.03
    ik0 = {'ik.handL': 0.0, 'ik.handR': 0.0}
    keys = [(0.0, dict(st, **ik0)), (0.4, up, 'snap'), (0.7, push), (1.0, up), (1.25, push), (1.5, up)]
    frames, k, loop = keyed(st, keys)

    def f(t):
        ch = k(t)
        for s in 'LR':   # palms up (hand bones pitched back) once the hands are up
            ch[f'B.Hand{s}.x'] = ch.get(f'B.Hand{s}.x', 0)
        return ch
    return frames, f, False


def v_crowd(R, D, T=2.0):
    """Crowd*: excited fidget — bouncing on the toes, weight shifting, arms pumping, looking around (loop)."""
    st = stand(R, D)
    rp = R.meta.get('rest_pose', {})

    def f(t):
        ch = dict(st)
        b = 0.5 + 0.5 * math.sin(TAU * 4 * t / T)          # 4 bounces per loop
        ch['hips.py'] = st['hips.py'] + 0.03 * D.leg * b - 0.01 * D.leg
        for s in 'LR':
            ch[f'tg.foot{s}.pitch'] = 22 * b
        ch['hips.px'] = 0.025 * loopsin(t, T, 1)
        ch['hips.z'] = 3 * loopsin(t, T, 1)
        ch['B.Body.z'] = -4 * loopsin(t, T, 1, 0.05)
        ch['B.Body.x'] = rp.get('B.Body.x', 0) + 4 + 3 * b
        ch['B.Head.y'] = 30 * loopsin(t, T, 1, 0.2) + 10 * loopsin(t, T, 3)
        ch['B.Head.x'] = rp.get('B.Head.x', 0) - 12 + 4 * b
        for s in 'LR':
            pump = math.sin(TAU * 4 * t / T + (0 if s == 'L' else math.pi))
            ch[f'B.Arm{s}.x'] = -40 - 22 * pump
            ch[f'B.Arm{s}.z'] = sgn(s) * (14 + 6 * b)
            ch[f'B.ForeArm{s}.x'] = -85 - 15 * pump
        return ch
    return int(round(T * FPS)), f, True


def v_recoil(R, D):
    """Recoil: shrink back — step back, hunch, hands pulled to the chest, head ducked; ends held small (0.8 s)."""
    st = stand(R, D)
    rp = R.meta.get('rest_pose', {})
    at = Attach(R)
    r = dict(st)
    r.update({'hips.pz': -0.06, 'hips.x': -6, 'B.Body.x': rp.get('B.Body.x', 0) + 12, 'B.Head.x': rp.get('B.Head.x', 0) + 16,
              'hips.py': st['hips.py'] - 0.1 * D.leg})
    r['tg.footR.pz'] = D.ank['R'].z - 0.2 * D.leg
    r['tg.footL.pz'] = D.ank['L'].z + 0.03
    for s in 'LR':
        at.pin(D, r, s, 'Body', (sgn(s) * 0.05, D.sh['L'].y - D.waist.y - 0.08, 0.17), (sgn(s) * 1.0, -1.0, -0.2))
    jolt = dict(r, **{'hips.pz': -0.09, 'B.Body.x': r['B.Body.x'] - 8, 'B.Head.x': r['B.Head.x'] - 14,
                      'hips.py': st['hips.py'] - 0.02 * D.leg})
    for s in 'LR':
        at.pin(D, jolt, s, 'Body', (sgn(s) * 0.05, D.sh['L'].y - D.waist.y - 0.08, 0.17), (sgn(s) * 1.0, -1.0, -0.2))
    keys = [(0.0, dict(st, **{'ik.handL': 0.0, 'ik.handR': 0.0})), (0.14, jolt, 'snap'), (0.4, r), (0.8, r)]
    frames, k, loop = keyed(st, keys)

    def f(t):
        ch = k(t)
        tr = smooth((t - 0.35) / 0.2)
        ch['B.Body.x'] += 1.2 * math.sin(t * 50) * tr
        return ch
    return frames, f, False


def villager(R, D):
    side = 'L' if R.meta.get('hand') == 'L' else 'R'
    R.clips.append(('Carry',) + v_carry(R, D, side))
    R.clips.append(('Offer',) + v_offer(R, D))
    R.clips.append(('Crowd',) + v_crowd(R, D))
    R.clips.append(('Recoil',) + v_recoil(R, D))
    R.meta.setdefault('speeds', {})['Carry'] = 2.2


COLL_STRAP = {'L': (0.105, 0.215, 0.205), 'R': (-0.105, 0.215, 0.205)}   # Body-local grip points on the chest straps


def collector_carry(R, D):
    """Collector Carry*: loaded walk 2.2 m/s, deeper stoop, both hands gripping the frame straps at the chest."""
    at = Attach(R)

    def wob(ch, t, ph, cL, b_):
        ch['B.Head.z'] = ch.get('B.Head.z', 0) + 2 * cL
        ch['B.Body.x'] = ch.get('B.Body.x', 0) + 6
        ch['B.Head.x'] = ch.get('B.Head.x', 0) - 5
        return ch
    base = A.locomotion(R, D, 2.2, 18, stance=0.38, lift=0.055, bob=0.032, lean=9, arm=0, yaw=5,
                        roll=5, elbow=14, crouch=0.04, extra=wob)

    def ov(ch, t):
        for s in 'LR':
            at.pin(D, ch, s, 'Body', COLL_STRAP[s], (sgn(s) * 1.0, -0.6, -0.3))
        return ch
    return wrap(base, ov)


def collector_grab(R, D):
    """Grab: stoop, both hands to something on the ground ~0.4 m ahead, lift it to the chest, heave it over the
    right shoulder into the carrier, straighten (1.5 s)."""
    st = stand(R, D)
    rp = R.meta.get('rest_pose', {})
    low = dict(st)
    low.update({'hips.py': st['hips.py'] - 0.46 * D.leg, 'hips.x': 22, 'B.Body.x': rp.get('B.Body.x', 0) + 30, 'B.Head.x': -10,
                'hips.pz': -0.02})
    low['tg.footL.pz'] = D.ank['L'].z + 0.1 * D.leg
    low['tg.footR.pz'] = D.ank['R'].z - 0.12 * D.leg
    for s in 'LR':
        hand_target(D, low, s, (sgn(s) * 0.08, 0.16, 0.42), 1.0, (sgn(s) * 1.0, 0.2, -0.6))
    grip = dict(low)
    for s in 'LR':
        grip[f'tg.hand{s}.px'] = sgn(s) * 0.055
    chest = dict(st, **{'hips.py': st['hips.py'] - 0.1 * D.leg, 'B.Body.x': rp.get('B.Body.x', 0) + 4, 'B.Head.x': -10})
    for s in 'LR':
        hand_target(D, chest, s, (sgn(s) * 0.06, 0.92, 0.3), 1.0, (sgn(s) * 1.0, -0.8, -0.2))
    heave = dict(st, **{'B.Body.x': rp.get('B.Body.x', 0) - 2, 'B.Body.y': 22, 'B.Body.z': 8, 'B.Head.x': -4, 'B.Head.y': -20,
                        'hips.py': st['hips.py'] + 0.015 * D.leg})
    hand_target(D, heave, 'R', (-0.15, 1.13, 0.04), 1.0, (-1.0, -0.4, 0.2))
    hand_target(D, heave, 'L', (-0.03, 1.07, 0.13), 1.0, (1.0, -0.6, -0.2))
    ik0 = {'ik.handL': 0.0, 'ik.handR': 0.0}
    keys = [(0.0, dict(st, **ik0)), (0.35, low, 'snap'), (0.5, grip), (0.62, grip, 'hold'), (0.92, chest), (1.12, heave, 'snap'),
            (1.24, heave), (1.5, dict(st, **ik0))]
    return keyed(st, keys)


def add_clips(R):
    D = A.Dims(R)
    n = R.name
    if n == 'Kinopio':
        kinopio(R, D)
    elif n == 'Chief':
        chief(R, D)
    elif n == 'Hero_Bluebird':
        hero(R, D)
    elif n.startswith('Villager_'):
        villager(R, D)
