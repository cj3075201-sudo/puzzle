# -*- coding: utf-8 -*-
"""Clip library for the skinned characters (round 4). All poses in rig space (Y up, +Z forward, +X = char left).
Channel names: B.<bone>.x/y/z (deg, local), hips.px/py/pz (m), hips.x/y/z (deg), ik.<limb> (0..1),
tg.<limb>.px/py/pz (rig-space target of ankle / wrist), tg.<foot>.pitch (deg, world, + = toes down), ground (0..1)."""
import math
from mathutils import Vector, Quaternion
from ouat_rig import Keys, Poser, Skel, FPS, E, smooth, smoother, add_ch

V = Vector
TAU = 2 * math.pi


class Dims:
    def __init__(self, rig):
        sk = Skel(rig)
        R = sk.rest
        b = rig.b
        self.rig = rig
        self.hips = R['Hips'].copy()
        self.ank = {s: R[b('Foot' + s)].copy() for s in 'LR'}
        self.hipj = {s: R[b('Leg' + s)].copy() for s in 'LR'}
        self.knee = {s: R[b('Shin' + s)].copy() for s in 'LR'}
        self.a = (self.hipj['L'] - self.knee['L']).length
        self.b = (self.knee['L'] - self.ank['L']).length
        self.leg = self.a + self.b
        self.sh = {s: R[b('Arm' + s)].copy() for s in 'LR'}
        self.el = {s: R[b('ForeArm' + s)].copy() for s in 'LR'}
        self.wr = {s: R[b('Hand' + s)].copy() for s in 'LR'}
        self.ua = (self.sh['L'] - self.el['L']).length
        self.la = (self.el['L'] - self.wr['L']).length
        self.arm = self.ua + self.la
        self.neck = R['Head'].copy()
        self.waist = R['Body'].copy()
        m = rig.meta
        self.H = m['height']
        self.ha = self.ank['L'].y
        self.lt = m.get('toe', 0.1)
        self.lh = m.get('heel', 0.04)
        self.hr = m.get('head_r', 0.15)
        self.hc = V(m.get('head_c', (0, 0, 0)))   # rig-space offset from Head joint
        self.kr = m.get('knee_r', 0.03)
        self.kind = m.get('kind', 'puppet')


def sgn(s):
    return 1.0 if s == 'L' else -1.0


def stand(rig, D, drop=0.025):
    ch = {'ik.footL': 1.0, 'ik.footR': 1.0, 'hips.py': -drop * D.leg}
    for s in 'LR':
        a = D.ank[s]
        ch[f'tg.foot{s}.px'] = a.x
        ch[f'tg.foot{s}.py'] = a.y
        ch[f'tg.foot{s}.pz'] = a.z
        ch[f'tg.foot{s}.pitch'] = 0.0
    ch.update(rig.meta.get('rest_pose', {}))
    return ch


def bump(t, t0, dur, attack=0.25):
    """0 -> 1 -> 0 accent: quick attack (string pull), slow release."""
    u = (t - t0) / dur
    if u <= 0 or u >= 1:
        return 0.0
    if u < attack:
        return smooth(u / attack)
    return 1 - smooth((u - attack) / (1 - attack))


def loopsin(t, T, k=1, ph=0.0):
    return math.sin(TAU * (k * t / T + ph))


# =====================================================================================  locomotion
def hermite(p0, p1, m0, m1, u):
    u2, u3 = u * u, u * u * u
    return (2 * u3 - 3 * u2 + 1) * p0 + (u3 - 2 * u2 + u) * m0 + (-2 * u3 + 3 * u2) * p1 + (u3 - u2) * m1


def foot_track(D, s, p, v, T, stance, lift, th_strike, th_off, side):
    """Ankle target (y, z offset from rest) + world pitch for phase p (0 = heel strike).
    Planted pivots move backwards at exactly v (no sliding)."""
    L = v * stance * T
    lt, lh, ha = D.lt, D.lh, D.ha

    def planted(pp):
        zf = L / 2 - v * T * pp
        # pitch profile over stance: heel strike -> flat -> heel lift toward toe-off
        u = pp / stance
        if u < 0.25:
            th = th_strike * (1 - smooth(u / 0.25))
        elif u > 0.55:
            th = th_off * smooth((u - 0.55) / 0.45)
        else:
            th = 0.0
        return pivot_pose(zf, th)

    def pivot_pose(zf, th):
        r = math.radians(th)
        if th < 0:   # around heel point (zf - lh, 0)
            pz, py = zf - lh, 0.0
            oy, oz = ha, lh
        else:        # around toe point
            pz, py = zf + lt, 0.0
            oy, oz = ha, -lt
        # Rx(th): y' = y cos - z sin ; z' = y sin + z cos   (+th = toes down)
        y = py + oy * math.cos(r) - oz * math.sin(r)
        z = pz + oy * math.sin(r) + oz * math.cos(r)
        return y, z, th

    if p < stance:
        return planted(p)
    # swing: Hermite from toe-off to next heel strike, end velocities = ground speed
    u = (p - stance) / (1 - stance)
    y0, z0, t0 = planted(stance - 1e-4)
    y1, z1, t1 = planted(0.0)
    dur = (1 - stance) * T
    vz = -v * dur
    z = hermite(z0, z1, vz * 0.6, vz * 0.5, u)
    y = y0 + (y1 - y0) * smooth(u) + lift * math.sin(math.pi * u) ** 0.9
    th = t0 + (t1 - t0) * smooth(u) + (-8.0) * math.sin(math.pi * u)
    return y, z, th


def locomotion(rig, D, v, frames, stance, lift, bob, lean, arm, yaw=6.0, roll=3.0, elbow=15.0,
               th_strike=-12.0, th_off=28.0, crouch=0.04, head_bob=3.0, extra=None, narrow=0.0):
    """Cyclic walk / trot / run matching ground speed v (m/s). Returns (frames, fn, loop)."""
    T = frames / FPS
    L = v * stance * T
    # pelvis height: extended leg at the contact extremes must fit inside 97 % of the leg
    ext = math.sqrt(max(0.0, (0.965 * D.leg) ** 2 - (L / 2 + D.lt * 0.3) ** 2))
    rest_h = D.hipj['L'].y - D.ha
    drop = max(0.0, rest_h - ext) + crouch * D.leg
    base = stand(rig, D)
    flight = stance < 0.5

    def fn(t):
        ch = dict(base)
        ph = (t / T) % 1.0
        cL = math.cos(TAU * ph)            # +1 when left foot is fully forward (heel strike)
        for s, off in (('L', 0.0), ('R', 0.5)):
            p = (ph + off) % 1.0
            y, z, th = foot_track(D, s, p, v, T, stance, lift, th_strike, th_off, s)
            a = D.ank[s]
            ch[f'tg.foot{s}.px'] = a.x * (1 - narrow)
            ch[f'tg.foot{s}.py'] = y
            ch[f'tg.foot{s}.pz'] = a.z + z
            ch[f'tg.foot{s}.pitch'] = th
        # vertical: lowest at mid-stance for flight gaits, at double support for walks
        if flight:
            b_ = -math.cos(TAU * 2 * (ph - stance / 2))
        else:
            b_ = -math.cos(TAU * 2 * ph)
        ch['hips.py'] = -drop + bob * b_ * 0.5 - bob * 0.5
        ch['hips.y'] = -yaw * cL
        ch['hips.z'] = roll * math.sin(TAU * 2 * ph) * 0.0 + roll * cL * 0.0 - roll * math.sin(TAU * ph)
        ch['hips.x'] = lean * 0.35
        rp = rig.meta.get('rest_pose', {})
        ch['B.Body.x'] = rp.get('B.Body.x', 0.0) + lean * 0.65 + 2.0 * b_
        ch['B.Body.y'] = yaw * 1.4 * cL
        ch['B.Body.z'] = roll * 0.6 * math.sin(TAU * ph)
        ch['B.Head.x'] = rp.get('B.Head.x', 0.0) - lean * 0.8 - head_bob * b_
        ch['B.Head.y'] = -yaw * 0.4 * cL
        ch['B.Head.z'] = -roll * 0.4 * math.sin(TAU * ph)
        for s in 'LR':
            c = cL * sgn(s)       # + when this side's foot is forward -> arm back
            ch[f'B.Arm{s}.x'] = arm * c + rig.meta.get('rest_pose', {}).get(f'B.Arm{s}.x', 0.0)
            ch[f'B.Arm{s}.z'] = sgn(s) * (rig.meta.get('arm_out', 6.0) + 2 * abs(c))
            ch[f'B.ForeArm{s}.x'] = min(-elbow, rp.get(f'B.ForeArm{s}.x', 0.0)) - elbow * 0.6 * max(0.0, -c)
        if extra:
            ch = extra(ch, t, ph, cL, b_)
        return ch
    return frames, fn, True


# =====================================================================================  helpers for gestures
def kneel_targets(D, ch, back=0.0, sit=0.85, toes=165.0, knee_fwd=0.3):
    """Both knees on the ground (Korean big-bow kneel). Fills feet targets + hips offset."""
    a, b, kr = D.a, D.b, D.kr
    for s in 'LR':
        an = D.ank[s]
        kz = an.z + knee_fwd * b - back
        ch[f'tg.foot{s}.px'] = an.x
        ch[f'tg.foot{s}.py'] = kr * 0.9
        ch[f'tg.foot{s}.pz'] = kz - b * 0.97
        ch[f'tg.foot{s}.pitch'] = toes
        ch[f'tg.foot{s}.polex'] = 0.0
    # hip joint: thigh from knee going back by sit*b horizontally
    kz = D.ank['L'].z + knee_fwd * b - back
    dz = min(a * 0.98, sit * b)
    hy = kr + math.sqrt(max(0.0, a * a - dz * dz))
    hz = kz - dz
    ch['hips.py'] = hy - D.hipj['L'].y
    ch['hips.pz'] = hz - D.hipj['L'].z
    return ch


def hand_target(D, ch, s, p, w=1.0, pole=None):
    ch[f'ik.hand{s}'] = w
    ch[f'tg.hand{s}.px'] = p[0]
    ch[f'tg.hand{s}.py'] = p[1]
    ch[f'tg.hand{s}.pz'] = p[2]
    if pole:
        ch[f'tg.hand{s}.polex'], ch[f'tg.hand{s}.poley'], ch[f'tg.hand{s}.polez'] = pole
    return ch


def fit(rig, chfn, lo, hi, measure, target, iters=18):
    """Bisection on a scalar pose parameter so that measure(world FK) == target (measure increasing in x)."""
    P = Poser(rig)
    for _ in range(iters):
        mid = (lo + hi) / 2
        q, hl = P.evaluate(chfn(mid))
        W = P.sk.fk(q, hl)
        if measure(W) > target:
            hi = mid
        else:
            lo = mid
    return (lo + hi) / 2


def head_bottom(D):
    def m(W):
        p, r = W['Head']
        return (p + r @ D.hc).y - D.hr
    return m


def keyed(base, keys, loop=False):
    k = Keys(base, keys, loop=loop)
    frames = int(round(k.T * FPS))
    return frames, k, loop


def with_overlay(clip, ov):
    frames, fn, loop = clip

    def f(t):
        ch = fn(t)
        return ov(ch, t)
    return frames, f, loop


# =====================================================================================  clips
def c_idle(rig, D, T=2.8, twitch=True):
    base = stand(rig, D)
    k = D.kind
    amp = 1.0 if k != 'tree' else 0.6

    def f(t):
        ch = dict(base)
        br = loopsin(t, T)
        ch['hips.py'] += -0.006 * D.H * (0.5 + 0.5 * br) * amp
        ch['B.Body.x'] = ch.get('B.Body.x', 0) + 1.8 * br * amp
        ch['B.Head.x'] = ch.get('B.Head.x', 0) - 1.2 * br + 1.5 * loopsin(t, T, 1, 0.3)
        ch['B.Head.y'] = ch.get('B.Head.y', 0) + 5 * loopsin(t, T, 1, 0.15) * amp
        for s in 'LR':
            ch[f'B.Arm{s}.x'] = ch.get(f'B.Arm{s}.x', 0) + 2.5 * loopsin(t, T, 1, 0.1 + 0.2 * (s == 'R'))
            ch[f'B.Arm{s}.z'] = ch.get(f'B.Arm{s}.z', 0) + sgn(s) * 1.5 * (0.5 + 0.5 * br)
        if twitch:
            if k == 'bird':   # quick bird head flick + look
                ch['B.Head.z'] = ch.get('B.Head.z', 0) + 14 * bump(t, 0.9, 0.7, 0.18)
                ch['B.Head.y'] += 18 * bump(t, 1.7, 0.8, 0.2)
                ch['B.Tail.x'] = -12 * bump(t, 1.2, 0.35, 0.3)
            elif k == 'human':    # weight shift + a glance to the side
                ch['hips.px'] = ch.get('hips.px', 0) + 0.012 * loopsin(t, T, 1, 0.25)
                ch['hips.z'] = ch.get('hips.z', 0) + 1.5 * loopsin(t, T, 1, 0.25)
                ch['B.Body.z'] = ch.get('B.Body.z', 0) - 1.8 * loopsin(t, T, 1, 0.25)
                ch['B.Head.y'] += 22 * bump(t, 1.5, 0.9, 0.22)
                ch['B.Cape.x'] = 3 + 2 * br
            elif k == 'puppet':   # string tug: shoulder pops, head drops and catches
                ch['B.Head.x'] += 6 * bump(t, 1.4, 0.5, 0.15)
                ch['B.ArmL.z'] += 7 * bump(t, 1.38, 0.45, 0.12)
                ch['hips.py'] += 0.012 * D.H * bump(t, 1.36, 0.4, 0.12)
        return ch
    return int(round(T * FPS)), f, True


def c_talk(rig, D, T=2.4):
    base = stand(rig, D)

    def f(t):
        ch = dict(base)
        u = loopsin(t, T, 2)
        ch['B.Body.x'] = ch.get('B.Body.x', 0) + 3 + 2 * loopsin(t, T, 1)
        ch['B.Body.y'] = 6 * loopsin(t, T, 1, 0.1)
        ch['B.Head.x'] = 4 * loopsin(t, T, 3, 0.2)
        ch['B.Head.z'] = 5 * loopsin(t, T, 1, 0.4)
        ch['B.Head.y'] = -6 * loopsin(t, T, 1, 0.1)
        # right hand: open-palm gesture, two beats; left small
        g = 0.5 + 0.5 * loopsin(t, T, 2, -0.25)
        ch['B.ArmR.x'] = -28 - 14 * g
        ch['B.ArmR.z'] = -10 - 8 * g
        ch['B.ForeArmR.x'] = -55 - 25 * g
        ch['B.HandR.x'] = -10 * g
        ch['B.HandR.z'] = 20 * g
        g2 = 0.5 + 0.5 * loopsin(t, T, 1, 0.35)
        ch['B.ArmL.x'] = -10 - 10 * g2
        ch['B.ForeArmL.x'] = -25 - 20 * g2
        ch['hips.py'] += -0.004 * D.H * (0.5 + 0.5 * u)
        return ch
    return int(round(T * FPS)), f, True


def bow_pose(rig, D, ch):
    if D.kind == 'tree':   # the crown must not hit the ground: kneel, lean, head down
        ch = kneel_targets(D, ch, sit=0.8)
        ch.update({'hips.x': 10, 'B.Body.x': 22, 'B.Head.x': 20, 'B.Canopy.x': 8})
        for s in 'LR':
            hand_target(D, ch, s, (D.sh[s].x * 0.9, 0.06 * D.H, D.ank['L'].z + 0.3 * D.b + 0.55 * D.arm), 1.0, (sgn(s) * 1.0, 0.5, -0.4))
        return ch
    ch = kneel_targets(D, ch)
    ch['hips.x'] = 25
    ch['B.Body.x'] = 58
    ch['B.Head.x'] = 5
    for s in 'LR':
        x = D.sh[s].x * 1.05
        kz = D.ank['L'].z + 0.3 * D.b
        hand_target(D, ch, s, (x, 0.02 * D.H + 0.03, kz + D.ua * 1.1 + 0.25 * D.la), 1.0, (sgn(s) * 1.0, 0.8, -0.3))
    # fit the torso pitch so the head just rests above the ground
    def chf(x):
        c = dict(ch)
        c['B.Body.x'] = x
        return c
    hb = head_bottom(D)
    x = fit(rig, chf, 20, 95, lambda W: -hb(W), -0.015 * D.H)
    ch['B.Body.x'] = x
    return ch


def c_bow(rig, D):
    """Stand -> crouch -> knees down -> full prostration (0.8 s)."""
    st = stand(rig, D)
    full = bow_pose(rig, D, dict(st))
    mid = dict(st)
    mid = kneel_targets(D, mid, sit=0.55, toes=110)
    mid['hips.py'] = (mid['hips.py'] + st['hips.py']) * 0.5 + 0.0
    mid['hips.x'] = 10
    mid['B.Body.x'] = 25
    mid['B.Head.x'] = 10
    for s in 'LR':
        mid[f'B.Arm{s}.x'] = -30
        mid[f'B.ForeArm{s}.x'] = -30
    knees = kneel_targets(D, dict(st), sit=0.7)
    knees.update({'hips.x': 12, 'B.Body.x': 30, 'B.Head.x': 8})
    for s in 'LR':
        knees[f'B.Arm{s}.x'] = -45
        knees[f'B.ForeArm{s}.x'] = -20
    keys = [(0.0, st), (0.22, mid), (0.42, knees, 'snap'), (0.8, full, 'snap')]
    return keyed(st, keys)


def c_bowhold(rig, D, T=2.4):
    full = bow_pose(rig, D, stand(rig, D))

    def f(t):
        ch = dict(full)
        br = loopsin(t, T)
        ch['B.Body.x'] += 1.2 * br
        ch['hips.py'] += 0.004 * D.H * br
        ch['B.Head.x'] += 1.5 * loopsin(t, T, 1, 0.25)
        return ch
    return int(round(T * FPS)), f, True


def c_rise(rig, D):
    st = stand(rig, D)
    full = bow_pose(rig, D, dict(st))
    knees = kneel_targets(D, dict(st), sit=0.7)
    knees.update({'hips.x': 8, 'B.Body.x': 18, 'B.Head.x': -5})
    for s in 'LR':
        knees[f'B.Arm{s}.x'] = -20
    crouch = dict(st)
    crouch['hips.py'] = -0.28 * D.leg
    crouch['hips.x'] = 10
    crouch['B.Body.x'] = 18
    for s in 'LR':
        crouch[f'tg.foot{s}.pz'] = D.ank[s].z - 0.05 * D.leg
    keys = [(0.0, full), (0.3, knees, 'snap'), (0.6, crouch), (0.9, st)]
    return keyed(st, keys)


def c_point(rig, D, up=False):
    st = stand(rig, D)
    p = dict(st)
    if up:
        p.update({'B.ArmR.x': -160, 'B.ArmR.z': -12, 'B.ForeArmR.x': -5, 'B.Head.x': -32, 'B.Body.x': -6, 'hips.x': -2,
                  'B.ArmL.x': 5, 'B.ArmL.z': 10})
    else:
        p.update({'B.ArmR.x': -88, 'B.ArmR.z': 6, 'B.ArmR.y': 8, 'B.ForeArmR.x': -4, 'B.Body.x': 6, 'B.Body.y': 12,
                  'B.Head.y': -8, 'B.Head.x': -2, 'B.ArmL.x': 6})
    over = dict(p)
    over['B.ArmR.x'] = p['B.ArmR.x'] - 8
    keys = [(0.0, st), (0.28, over, 'snap'), (0.42, p), (1.1, p), (1.5, st)]
    return keyed(st, keys)


def c_lookup(rig, D, T=3.0):
    st = stand(rig, D)

    def f(t):
        ch = dict(st)
        ch['B.Head.x'] = -38 + 3 * loopsin(t, T)
        ch['B.Head.y'] = 8 * loopsin(t, T, 1, 0.2)
        ch['B.Body.x'] = -8 + 1.5 * loopsin(t, T, 1, 0.1)
        ch['hips.x'] = -3
        for s in 'LR':
            ch[f'B.Arm{s}.x'] = 6
            ch[f'B.Arm{s}.z'] = sgn(s) * 8
        return ch
    return int(round(T * FPS)), f, True


def c_beckon(rig, D):
    st = stand(rig, D)
    up = dict(st)
    up.update({'B.ArmR.x': -70, 'B.ArmR.z': -15, 'B.ForeArmR.x': -10, 'B.HandR.x': -20, 'B.Body.x': 5, 'B.Head.z': -6})
    curl = dict(up)
    curl.update({'B.ForeArmR.x': -95, 'B.HandR.x': -50, 'B.Body.x': 2})
    keys = [(0.0, st), (0.25, up, 'snap'), (0.45, curl), (0.62, up), (0.82, curl), (1.0, up), (1.2, st)]
    return keyed(st, keys)


def c_lookback(rig, D):
    st = stand(rig, D)
    lb = dict(st)
    lb.update({'hips.y': 18, 'B.Body.y': 40, 'B.Head.y': 65, 'B.Head.x': -4, 'B.Body.x': -3,
               'B.ArmL.x': 14, 'B.ArmR.x': -12, 'B.ArmL.z': 8})
    keys = [(0.0, st), (0.35, lb, 'snap'), (1.2, lb), (1.7, st)]
    return keyed(st, keys)


def c_nod(rig, D):
    st = stand(rig, D)
    dn = dict(st, **{'B.Head.x': 24, 'B.Body.x': 4})
    upk = dict(st, **{'B.Head.x': -3})
    keys = [(0.0, st), (0.16, dn, 'snap'), (0.32, upk), (0.5, dn, 'snap'), (0.66, upk), (0.85, st)]
    return keyed(st, keys)


def c_headtilt(rig, D):
    st = stand(rig, D)
    tl = dict(st, **{'B.Head.z': 24, 'B.Head.y': 8, 'B.Head.x': 4, 'B.Body.z': 4})
    keys = [(0.0, st), (0.3, tl, 'snap'), (1.0, tl), (1.4, st)]
    return keyed(st, keys)


def c_reach(rig, D):
    """Reach toward an object in front (latch height ~ waist), hesitate, then withdraw the hand to the chest."""
    st = stand(rig, D)
    s = 'R'
    sh = D.sh[s]
    tgt = (sh.x * 0.6, D.hips.y + 0.05 * D.H, sh.z + D.arm * 0.95)
    lean = dict(st)
    lean.update({'B.Body.x': 14, 'hips.x': 4, 'B.Head.x': 12, 'hips.pz': 0.03 * D.H})
    for k in 'LR':
        lean[f'tg.foot{k}.pz'] = D.ank[k].z
    lean['tg.footR.pz'] = D.ank['R'].z + 0.18 * D.leg
    hand_target(D, lean, s, tgt, 1.0, (-0.6, -0.6, -0.4))
    near = dict(lean)
    near['tg.handR.pz'] = tgt[2] - 0.08 * D.arm
    hes = dict(lean)
    hes['tg.handR.pz'] = tgt[2] - 0.02 * D.arm
    back = dict(st)
    back.update({'B.Body.x': -6, 'hips.x': -3, 'B.Head.x': -2, 'hips.pz': -0.01 * D.H})
    hand_target(D, back, s, (sh.x * 0.1, sh.y - D.ua * 0.6, sh.z + 0.18 * D.arm), 1.0, (-0.8, -0.6, -0.4))
    back['B.ArmL.x'] = 10
    keys = [(0.0, dict(st, **{'ik.handR': 0.0})), (0.25, dict(near, **{'ik.handR': 0.6})), (0.7, near), (0.95, hes),
            (1.2, near, 'hold'), (1.4, back, 'snap'), (1.75, back), (2.2, dict(st, **{'ik.handR': 0.0}))]
    return keyed(st, keys)


def c_gather(rig, D, T=2.4):
    """Crouch and pick things up from the ground into the left arm (loop)."""
    st = stand(rig, D)
    low = dict(st)
    low['hips.py'] = -0.42 * D.leg
    big = D.hr / D.H > 0.13          # big-headed puppets squat lower and keep the head up
    low['hips.py'] = -(0.52 if big else 0.42) * D.leg
    low['hips.x'] = 10 if big else 18
    low['B.Body.x'] = 18 if big else 32
    low['B.Head.x'] = 8 if big else 20
    low['tg.footL.pz'] = D.ank['L'].z + 0.12 * D.leg
    low['tg.footR.pz'] = D.ank['R'].z - 0.08 * D.leg
    # left arm cradles at the belly
    hand_target(D, low, 'L', (D.sh['R'].x * 0.2, D.waist.y + 0.02 * D.H, D.waist.z + 0.32 * D.arm), 1.0, (1.0, -0.6, -0.3))
    g1 = dict(low)
    hand_target(D, g1, 'R', (D.sh['R'].x * 1.1, 0.03 + D.H * 0.01, D.ank['R'].z + 0.75 * D.arm), 1.0, (-0.6, 0.0, -1.0))
    g2 = dict(low)
    hand_target(D, g2, 'R', (D.sh['R'].x * 0.15, D.waist.y + 0.06 * D.H, D.waist.z + 0.35 * D.arm), 1.0, (-1.0, -0.5, -0.3))
    g2['B.Body.x'] = 14 if big else 24
    g3 = dict(g1)
    g3['tg.handR.px'] = D.sh['R'].x * 0.4
    g3['tg.handR.pz'] = D.ank['R'].z + 0.85 * D.arm
    keys = [(0.0, g2), (0.5, g1, 'snap'), (0.8, g1), (1.2, g2), (1.7, g3, 'snap'), (1.95, g3), (2.4, g2)]
    k = Keys(st, keys, loop=True)
    return int(round(T * FPS)), k, True


def c_sitidle(rig, D, T=3.6):
    """Sit on the ground hugging the knees, like a stone (loop)."""
    st = stand(rig, D)
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

    def f(t):
        ch = dict(s)
        r = loopsin(t, T)
        ch['hips.x'] += 3 * r
        ch['B.Body.x'] += 1.5 * loopsin(t, T, 1, 0.1)
        ch['B.Head.y'] = 6 * loopsin(t, T, 1, 0.3)
        return ch
    return int(round(T * FPS)), f, True


def c_cower(rig, D):
    """Flinch down into a crouch with arms over the head, tremble, hold."""
    st = stand(rig, D)
    cw = dict(st)
    cw['hips.py'] = -0.42 * D.leg
    cw['hips.x'] = 8
    cw['B.Body.x'] = 18
    cw['B.Head.x'] = 30
    for k in 'LR':
        cw[f'tg.foot{k}.pz'] = D.ank[k].z + (0.08 if k == 'L' else -0.1) * D.leg
        cw[f'B.Arm{k}.x'] = -150
        cw[f'B.Arm{k}.z'] = sgn(k) * 30
        cw[f'B.ForeArm{k}.x'] = -110
        cw[f'B.Arm{k}.y'] = -sgn(k) * 20
    fl = dict(cw)
    fl['hips.py'] = -0.3 * D.leg
    keys = [(0.0, st), (0.18, fl, 'snap'), (0.4, cw), (1.4, cw)]
    frames, k, loop = keyed(st, keys)

    def f(t):
        ch = k(t)
        tr = smooth((t - 0.4) / 0.2)
        ch['B.Body.x'] += 1.3 * math.sin(t * 55) * tr
        ch['B.Head.z'] = ch.get('B.Head.z', 0) + 1.6 * math.sin(t * 47) * tr
        return ch
    return frames, f, False


def c_push(rig, D):
    st = stand(rig, D)
    lean = dict(st)
    lean['hips.x'] = 10
    lean['B.Body.x'] = 22
    lean['hips.py'] = -0.12 * D.leg
    lean['hips.pz'] = 0.04 * D.H
    lean['tg.footL.pz'] = D.ank['L'].z + 0.22 * D.leg
    lean['tg.footR.pz'] = D.ank['R'].z - 0.3 * D.leg
    lean['tg.footR.pitch'] = 25
    lean['B.Head.x'] = -10
    for k in 'LR':
        hand_target(D, lean, k, (D.sh[k].x * 0.95, D.sh[k].y - 0.02 * D.H, D.sh[k].z + 0.75 * D.arm), 1.0, (sgn(k), -1.0, -0.5))
    shove = dict(lean)
    shove['hips.pz'] = 0.08 * D.H
    shove['B.Body.x'] = 28
    shove['tg.handL.pz'] = lean['tg.handL.pz'] + 0.08 * D.arm
    shove['tg.handR.pz'] = lean['tg.handR.pz'] + 0.08 * D.arm
    keys = [(0.0, dict(st, **{'ik.handL': 0.0, 'ik.handR': 0.0})), (0.3, lean), (0.55, shove, 'snap'), (0.75, lean),
            (1.0, shove, 'snap'), (1.25, lean), (1.6, dict(st, **{'ik.handL': 0.0, 'ik.handR': 0.0}))]
    return keyed(st, keys)


def c_kneel(rig, D, T=2.6):
    """One knee down (right), left foot planted forward, hands on the left knee (loop)."""
    st = stand(rig, D)
    k = dict(st)
    a, b, kr = D.a, D.b, D.kr
    # right knee on the ground slightly behind the origin, shin back, toes tucked
    kzR = D.ank['R'].z - 0.05 * D.leg
    k['tg.footR.py'] = kr + 0.02 * D.leg
    k['tg.footR.pz'] = kzR - b * 0.95
    k['tg.footR.pitch'] = 70
    # hip above the right knee
    hy = kr + a * 0.97
    k['hips.py'] = hy - D.hipj['R'].y
    k['hips.pz'] = kzR - D.hipj['R'].z
    # left foot forward so the thigh is near horizontal
    k['tg.footL.pz'] = D.ank['L'].z + a * 0.95
    k['tg.footL.py'] = D.ank['L'].y
    k['B.Body.x'] = 12
    k['B.Head.x'] = 6
    hand_target(D, k, 'L', (D.ank['L'].x, hy + 0.02 * D.leg, D.ank['L'].z + a * 0.8), 1.0, (1, 0, -0.3))
    hand_target(D, k, 'R', (D.ank['L'].x * 0.4, hy + 0.08 * D.leg, D.ank['L'].z + a * 0.7), 1.0, (-1, 0, -0.3))

    def f(t):
        ch = dict(k)
        br = loopsin(t, T)
        ch['B.Body.x'] += 1.8 * br
        ch['hips.py'] += -0.003 * D.H * br
        ch['B.Head.y'] = 6 * loopsin(t, T, 1, 0.2)
        return ch
    return int(round(T * FPS)), f, True


def c_lookaround(rig, D):
    st = stand(rig, D)
    L_ = dict(st, **{'B.Head.y': 55, 'B.Body.y': 20, 'hips.y': 6, 'B.Head.z': -5})
    R_ = dict(st, **{'B.Head.y': -55, 'B.Body.y': -20, 'hips.y': -6, 'B.Head.z': 5})
    U_ = dict(st, **{'B.Head.x': -35, 'B.Body.x': -6})
    keys = [(0.0, st), (0.35, L_, 'snap'), (0.85, L_), (1.2, R_, 'snap'), (1.65, R_), (2.0, U_), (2.25, U_), (2.5, st)]
    return keyed(st, keys)


def c_greet(rig, D):
    """Chief: slow big bow with arms opening (3 s)."""
    st = stand(rig, D)
    bw = dict(st)
    bw.update({'hips.x': 10, 'B.Body.x': 22, 'B.Head.x': 16, 'B.Canopy.x': 10, 'hips.py': st['hips.py'] - 0.1 * D.leg, 'hips.pz': -0.03 * D.H})
    for s in 'LR':
        bw[f'B.Arm{s}.x'] = -40
        bw[f'B.Arm{s}.z'] = sgn(s) * 35
        bw[f'B.ForeArm{s}.x'] = -20
    op = dict(st)
    op.update({'B.Body.x': -4, 'B.Head.x': -6})
    for s in 'LR':
        op[f'B.Arm{s}.z'] = sgn(s) * 28
        op[f'B.Arm{s}.x'] = -20
    keys = [(0.0, st), (0.7, op), (1.6, bw), (2.3, bw, 'hold'), (3.0, st)]
    return keyed(st, keys)


def c_standsway(rig, D, T=4.0):
    st = stand(rig, D)

    def f(t):
        ch = dict(st)
        ch['hips.z'] = 1.5 * loopsin(t, T)
        ch['B.Body.z'] = 3 * loopsin(t, T, 1, 0.08)
        ch['B.Body.x'] = 2 * loopsin(t, T, 1, 0.3)
        ch['B.Head.z'] = 4 * loopsin(t, T, 1, 0.16)
        ch['B.Canopy.z'] = 6 * loopsin(t, T, 1, 0.25)
        ch['B.Canopy.x'] = 3 * loopsin(t, T, 2, 0.1)
        for s in 'LR':
            ch[f'B.Arm{s}.z'] = ch.get(f'B.Arm{s}.z', 0) + 4 * loopsin(t, T, 1, 0.2 + 0.1 * (s == 'R'))
            ch[f'B.ForeArm{s}.x'] = ch.get(f'B.ForeArm{s}.x', 0) - 5 * loopsin(t, T, 1, 0.3)
        return ch
    return int(round(T * FPS)), f, True


# -------------------------------------------------------------------------------- hero-only
def c_falltumble(rig, D, T=1.0):
    """In-air somersault loop around the body centre (ik off, limbs flailing, cape flutter)."""
    cy = D.H * 0.5
    hip0 = D.hips

    def f(t):
        ph = (t / T) % 1.0
        ang = 360 * ph
        ch = {'ik.footL': 0, 'ik.footR': 0}
        ch.update(rig.meta.get('rest_pose', {}))
        ch['hips.x'] = ang
        # keep rotation around the body centre (cy above the floor)
        r = math.radians(ang)
        dy = hip0.y - cy
        # Rx(r) applied to offset (0, dy, 0): y' = dy cos, z' = dy sin
        ch['hips.py'] = (cy + dy * math.cos(r)) - hip0.y + 0.1 * D.H
        ch['hips.pz'] = dy * math.sin(r)
        fl = math.sin(TAU * ph * 2)
        ch['B.LegL.x'] = -50 + 25 * fl
        ch['B.LegR.x'] = -20 - 25 * fl
        ch['B.ShinL.x'] = 70 - 20 * fl
        ch['B.ShinR.x'] = 50 + 20 * fl
        ch['B.FootL.x'] = 20
        ch['B.FootR.x'] = 20
        for s in 'LR':
            ch[f'B.Arm{s}.z'] = sgn(s) * (95 + 25 * math.sin(TAU * ph * 3 + (0 if s == 'L' else 1.5)))
            ch[f'B.Arm{s}.x'] = -20 + 20 * math.sin(TAU * ph * 2)
            ch[f'B.ForeArm{s}.x'] = -20
        ch['B.Body.x'] = 25
        ch['B.Head.x'] = 20 + 10 * fl
        ch['B.Cape.x'] = 70 + 30 * math.sin(TAU * ph * 4)
        ch['B.Tail.x'] = -40 + 25 * math.sin(TAU * ph * 4 + 1)
        return ch
    return int(round(T * FPS)), f, True


def lie_pose(rig, D):
    ch = {'ik.footL': 0.0, 'ik.footR': 0.0, 'ground': 1.0}
    ch.update(rig.meta.get('rest_pose', {}))
    ch['hips.x'] = 88
    ch['hips.pz'] = -0.2 * D.H
    ch['B.Body.x'] = 4
    ch['B.Head.x'] = -35
    ch['B.Head.y'] = 0
    ch['B.Head.z'] = 0
    ch['B.LegL.x'] = 4
    ch['B.LegR.x'] = 0
    ch['B.LegL.z'] = 8
    ch['B.LegR.z'] = -6
    ch['B.FootL.x'] = 60
    ch['B.FootR.x'] = 55
    for s in 'LR':
        ch[f'B.Arm{s}.x'] = -20
        ch[f'B.Arm{s}.z'] = sgn(s) * 55
        ch[f'B.ForeArm{s}.x'] = -15
    ch['B.Cape.x'] = 10
    ch['B.Tail.x'] = -10
    return ch


def c_liedown(rig, D, T=3.0):
    lp = lie_pose(rig, D)

    def f(t):
        ch = dict(lp)
        ch['B.Body.x'] += 1.2 * loopsin(t, T)
        ch['B.Head.x'] += 1.5 * loopsin(t, T, 1, 0.2)
        ch['B.Tail.x'] += 4 * bump(t, 1.6, 0.6)
        ch['B.LegR.x'] += 3 * loopsin(t, T, 1, 0.4)
        return ch
    return int(round(T * FPS)), f, True


def c_getup(rig, D):
    """Lying face down -> push up on the wings -> sit back on the knees -> stand -> shake head (2.0 s)."""
    st = stand(rig, D)
    lp = lie_pose(rig, D)
    push = dict(lp)
    push.update({'hips.x': 70, 'B.Body.x': -18, 'B.Head.x': -20})
    for s in 'LR':
        push[f'B.Arm{s}.x'] = -70
        push[f'B.Arm{s}.z'] = sgn(s) * 20
        push[f'B.ForeArm{s}.x'] = -10
    kn = kneel_targets(D, dict(st), sit=0.75)
    kn.update({'hips.x': 10, 'B.Body.x': 8, 'B.Head.x': 6, 'ground': 0.0, 'B.Cape.x': 0, 'B.Tail.x': 0})
    for s in 'LR':
        kn[f'B.Arm{s}.x'] = -15
        kn[f'B.Arm{s}.z'] = sgn(s) * 25
        kn[f'B.Arm{s}.y'] = 0
    # transition: IK feet fade in while kneeling
    kn0 = dict(kn, **{'ik.footL': 1.0, 'ik.footR': 1.0})
    crouch = dict(st)
    crouch['hips.py'] = -0.3 * D.leg
    crouch['hips.x'] = 14
    crouch['B.Body.x'] = 20
    crouch['tg.footR.pz'] = D.ank['R'].z - 0.1 * D.leg
    stand_ = dict(st, **{'B.Head.x': 4})
    sh1 = dict(st, **{'B.Head.z': 16, 'B.Head.y': 10})
    sh2 = dict(st, **{'B.Head.z': -16, 'B.Head.y': -10})
    sh3 = dict(st, **{'B.Head.z': 8})
    # pre-pack lying pose with ik 0 and the kneel pose's targets so IK fades from the right place
    for k in ('tg.footL.px', 'tg.footL.py', 'tg.footL.pz', 'tg.footL.pitch', 'tg.footR.px', 'tg.footR.py', 'tg.footR.pz', 'tg.footR.pitch'):
        lp[k] = kn[k]
        push[k] = kn[k]
    lp.setdefault('ground', 1.0)
    push['ground'] = 1.0
    keys = [(0.0, lp), (0.35, push, 'snap'), (0.75, dict(kn0, ground=0.0), 'snap'), (1.1, crouch), (1.38, stand_),
            (1.55, sh1, 'snap'), (1.7, sh2, 'snap'), (1.82, sh3), (2.0, st)]
    return keyed(st, keys)


# =====================================================================================  mirroring (use the other hand)
def _swap(k):
    for a, b in (('L.', 'R.'),):
        pass
    import re
    def rep(m):
        return m.group(1) + ('R' if m.group(2) == 'L' else 'L') + m.group(3)
    return re.sub(r'((?:Arm|ForeArm|Hand|Leg|Shin|Foot|Wing|WingTip|hand|foot))([LR])(\.|$)', rep, k)


def mirror_ch(ch):
    out = {}
    for k, v in ch.items():
        k2 = _swap(k)
        if k.startswith('B.') or k.startswith('hips.'):
            ax = k.split('.')[-1]
            if ax in ('y', 'z', 'px'):
                v = -v
        elif k.startswith('tg.'):
            ax = k.split('.')[-1]
            if ax in ('px', 'polex', 'yaw', 'roll'):
                v = -v
        out[k2] = v
    return out


def mirrored(clip):
    frames, fn, loop = clip
    return frames, (lambda t: mirror_ch(fn(t))), loop


# =====================================================================================  human hero extras
def head_point(rig, ch, off):
    """Rig-space position of a point fixed to the Head (offset in rig space at rest) for a channel dict."""
    P = Poser(rig)
    q, hl = P.evaluate(ch)
    W = P.sk.fk(q, hl)
    p, r = W['Head']
    return p + r @ V(off)


def c_shout(rig, D):
    """Hands cupped around the mouth, lean in and shout (1.2 s)."""
    st = stand(rig, D)
    mo = rig.meta['mouth']
    inh = dict(st, **{'B.Body.x': -7, 'B.Head.x': -8, 'hips.x': -2, 'B.Cape.x': 2})
    sh = dict(st, **{'B.Body.x': 12, 'B.Head.x': -6, 'hips.x': 3, 'hips.pz': 0.02 * D.H, 'B.Cape.x': 10})
    sh['tg.footL.pz'] = D.ank['L'].z + 0.12 * D.leg
    for key in (inh, sh):
        m = head_point(rig, key, mo)
        for s_ in 'LR':
            hand_target(D, key, s_, (m.x + sgn(s_) * 0.065, m.y - 0.01, m.z - 0.01), 1.0, (sgn(s_) * 1.0, -0.7, -0.3))
    hold = dict(sh)
    keys = [(0.0, dict(st, **{'ik.handL': 0.0, 'ik.handR': 0.0})), (0.28, inh), (0.45, sh, 'snap'), (0.85, hold),
            (1.2, dict(st, **{'ik.handL': 0.0, 'ik.handR': 0.0}))]
    return keyed(st, keys)


def c_shrug(rig, D):
    st = stand(rig, D)
    sh = dict(st)
    sh.update({'B.Head.z': 16, 'B.Head.x': -6, 'B.Body.x': -7, 'B.Body.z': -3, 'hips.py': st['hips.py'] + 0.015 * D.leg,
               'B.Cape.x': 6})
    for s_ in 'LR':
        sh[f'B.Arm{s_}.z'] = sgn(s_) * 42
        sh[f'B.Arm{s_}.x'] = -20
        sh[f'B.ForeArm{s_}.x'] = -70
        sh[f'B.ForeArm{s_}.z'] = sgn(s_) * 25
        sh[f'B.ForeArm{s_}.y'] = -sgn(s_) * 60
        sh[f'B.Hand{s_}.z'] = sgn(s_) * 25
    keys = [(0.0, st), (0.3, sh, 'snap'), (0.7, sh), (1.0, st)]
    return keyed(st, keys)
