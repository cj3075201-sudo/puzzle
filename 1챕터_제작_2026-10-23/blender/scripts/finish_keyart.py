# -*- coding: utf-8 -*-
"""Finish the key-art renders (render_keyart.py): fish seen through the ink pond, soft bloom on the light, paper grain,
vignette, optional torn transparent edge. Writes art/renders/raw/keyart/<shot><tag>_final.png and, with publish,
Unity/Assets/Game/Resources/Pictures/<name>.png (title_art / chapter_card_1 / chapter_end_1).
usage: python3 finish_keyart.py <shot> [tag] [publish] [key=value ...]"""
import sys, os, json
import numpy as np
from PIL import Image, ImageFilter

HERE = os.path.dirname(os.path.abspath(__file__))
ART = os.path.dirname(HERE)
PROJ = os.path.dirname(ART)
RAW = os.path.join(ART, 'renders', 'raw', 'keyart')
PICS = os.path.join(PROJ, 'Unity', 'Assets', 'Game', 'Resources', 'Pictures')
OUT_NAME = {'title': 'title_art', 'card': 'chapter_card_1', 'end': 'chapter_end_1'}

shot = sys.argv[1]
rest = sys.argv[2:]
tag = next((a for a in rest if '=' not in a and a != 'publish'), '')
opt = dict(a.split('=', 1) for a in rest if '=' in a)
publish = 'publish' in rest
rng = np.random.default_rng(int(opt.get('seed', 7)))


def load(p, mode='RGB'):
    return np.asarray(Image.open(p).convert(mode)).astype(np.float32) / 255.0


def blur(a, r):
    im = Image.fromarray(np.clip(a * 255, 0, 255).astype(np.uint8))
    return np.asarray(im.filter(ImageFilter.GaussianBlur(r))).astype(np.float32) / 255.0


def lum(a):
    return a[..., 0] * 0.299 + a[..., 1] * 0.587 + a[..., 2] * 0.114


base = load(os.path.join(RAW, f'{shot}{tag}.png'))
H, W = base.shape[:2]

# ---------------------------------------------------------------- fish under the ink (title)
fp, mp = os.path.join(RAW, f'{shot}{tag}_fish.png'), os.path.join(RAW, f'{shot}{tag}_mask.png')
if shot == 'title' and os.path.exists(fp) and os.path.exists(mp) and opt.get('fish', '1') != '0':
    f = load(fp, 'RGBA')
    m = load(mp, 'RGBA')[..., 3]
    m = blur(np.stack([m] * 3, -1), 1.2)[..., 0]
    # fade toward the pond rim so the shape sinks into the ink instead of being cut out
    inner = blur(np.stack([np.clip((m - 0.5) * 2, 0, 1)] * 3, -1), float(opt.get('feather', 9)))[..., 0]
    fa = f[..., 3] * inner * float(opt.get('fish_k', 0.55))
    fl = lum(f[..., :3])
    if opt.get('flat', '1') == '1':
        a = (fa * np.clip(1 - lum(base) / 0.22, 0, 1))[..., None]
        base = base * (1 - a) + f[..., :3] * a
        fl = None
if shot == 'title' and os.path.exists(fp) and os.path.exists(mp) and opt.get('fish', '1') != '0' and opt.get('flat', '1') != '1':
    teal = np.array([0.10, 0.17, 0.19])
    pale = np.array([0.80, 0.82, 0.76])
    eye = np.clip((fl - float(opt.get('pale_lo', 0.2))) / 0.25, 0, 1)[..., None]   # pale eye / fangs / scratches
    tint = teal[None, None, :] * (0.4 + 1.6 * fl[..., None]) * (1 - eye) + pale * eye
    keep = np.clip(1 - lum(base) / 0.22, 0, 1)                    # do not cover the ripple lines
    a = (fa * keep * (float(opt.get('body_a', 0.35)) + (1 - float(opt.get('body_a', 0.35))) * eye[..., 0]))[..., None]
    base = base * (1 - a) + tint * a

# ---------------------------------------------------------------- bloom on the light
bk = float(opt.get('bloom', 0.35))
if bk > 0:
    hi = np.clip((base - 0.62) / 0.38, 0, 1)
    base = 1 - (1 - base) * (1 - blur(hi, W / 90) * bk) * (1 - blur(hi, W / 25) * bk * 0.6)

yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
# ---------------------------------------------------------------- unfinished corner: the drawing stops, blank paper for the title
if opt.get('paper', '0') == '1':
    def fbm(n0, oct_=4):
        acc = np.zeros((H, W), np.float32); amp = 1.0; tot = 0
        for o in range(oct_):
            g = rng.normal(0, 1, (max(2, n0 * 2 ** o * H // W), n0 * 2 ** o)).astype(np.float32)
            g = np.asarray(Image.fromarray(((g * 0.2 + 0.5) * 255).clip(0, 255).astype(np.uint8)).resize((W, H), Image.BICUBIC)).astype(np.float32) / 255 - 0.5
            acc += g * amp; tot += amp; amp *= 0.5
        return acc / tot
    rx, ry = float(opt.get('prx', 0.6)) * W, float(opt.get('pry', 0.5)) * H
    e = np.sqrt((xx / rx) ** 2 + (yy / ry) ** 2)                      # < 1 inside the blank corner
    e = e + fbm(3, 3) * float(opt.get('pwob', 0.25))
    # dry-brush streaks: the wash stops in horizontal-ish drags, not a torn hole
    streak = rng.normal(0, 1, (H // 3, 6)).astype(np.float32)
    streak = np.asarray(Image.fromarray(((streak * 0.2 + 0.5) * 255).clip(0, 255).astype(np.uint8)).resize((W, H), Image.BICUBIC)).astype(np.float32) / 255 - 0.5
    e = e + streak * float(opt.get('pstreak', 0.10))
    soft = float(opt.get('psoft', 0.06))
    a = np.clip((1 - e) / soft, 0, 1)                                 # paper alpha
    a = a * a * (3 - 2 * a) * float(opt.get('pmax', 1.0))
    edge = np.exp(-((e - 1 - soft * 0.1) / 0.012) ** 2) * 0.35 * (1.0 if float(opt.get('pmax', 1.0)) >= 1 else 0.0)
    pc = np.array([int(opt.get('pcol', 'E9E4D8')[i:i + 2], 16) / 255 for i in (0, 2, 4)])
    paper_rgb = pc[None, None, :] * (1 - 0.06 * np.clip(e, 0, 1) ** 2)[..., None]
    base = base * (1 - a[..., None]) + paper_rgb * a[..., None]
    ec = np.array([0.30, 0.31, 0.34])
    base = base * (1 - (edge * (1 - a) * 0.7)[..., None]) + ec * (edge * (1 - a) * 0.7)[..., None]
    # a few graphite construction lines running on into the blank paper
    from PIL import ImageDraw
    ln = Image.new('L', (W, H), 0)
    dr = ImageDraw.Draw(ln)
    for (x0, y0, x1, y1, w) in [(0.0, 0.43, 0.62, 0.29, 2), (0.08, 0.0, 0.30, 0.52, 2), (0.0, 0.50, 0.45, 0.47, 1), (0.36, 0.0, 0.47, 0.40, 1),
                                (0.52, 0.02, 0.27, 0.48, 1)]:
        dr.line([(x0 * W, y0 * H), (x1 * W, y1 * H)], fill=255, width=w)
    ln = np.asarray(ln.filter(ImageFilter.GaussianBlur(0.6))).astype(np.float32) / 255
    la = ln * a * float(opt.get('pline', 0.28)) * (1.0 if float(opt.get('pmax', 1.0)) >= 1 else 0.0) * np.clip(e * 1.4 - 0.25, 0, 1)
    base = base * (1 - la[..., None]) + np.array([0.36, 0.35, 0.34]) * la[..., None]
    PAPER_A = a

# ---------------------------------------------------------------- paper: grain + fibres, multiply
g1 = rng.normal(0, 1, (H // 2, W // 2)).astype(np.float32)
g1 = np.asarray(Image.fromarray(((g1 * 0.25 + 0.5) * 255).clip(0, 255).astype(np.uint8)).resize((W, H), Image.BICUBIC)).astype(np.float32) / 255 - 0.5
g2 = rng.normal(0, 1, (H // 60, W // 60)).astype(np.float32)
g2 = np.asarray(Image.fromarray(((g2 * 0.25 + 0.5) * 255).clip(0, 255).astype(np.uint8)).resize((W, H), Image.BICUBIC)).astype(np.float32) / 255 - 0.5
fib = rng.normal(0, 1, (H, W // 6)).astype(np.float32)          # faint horizontal paper fibres
fib = np.asarray(Image.fromarray(((fib * 0.25 + 0.5) * 255).clip(0, 255).astype(np.uint8)).resize((W, H), Image.BILINEAR)).astype(np.float32) / 255 - 0.5
gk = float(opt.get('grain', 1.0))
paper = 1 + gk * (0.09 * g1 + 0.07 * g2 + 0.05 * fib)
base = base * paper[..., None]

# ---------------------------------------------------------------- vignette (heavier at the bottom corners)
yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
cx, cy = float(opt.get('vcx', 0.55)) * W, float(opt.get('vcy', 0.5)) * H
d = np.sqrt(((xx - cx) / (W * 0.62)) ** 2 + ((yy - cy) / (H * 0.62)) ** 2)
vig = 1 - float(opt.get('vig', 0.38)) * np.clip(d - 0.45, 0, 1) ** 1.4
if 'PAPER_A' in globals():
    vig = vig * (1 - PAPER_A) + PAPER_A
base = base * vig[..., None]

out = np.clip(base, 0, 1)
img = Image.fromarray((out * 255).astype(np.uint8))

# ---------------------------------------------------------------- torn edge (end card): alpha
if opt.get('torn', '0') == '1':
    edge = np.zeros((H, W), np.float32)
    m = int(opt.get('margin', 34))
    n1 = rng.normal(0, 1, 400).cumsum()
    def wob(n, k):
        t = np.interp(np.linspace(0, 399, n), np.arange(400), np.convolve(rng.normal(0, 1, 400), np.ones(9) / 9, 'same'))
        return (t - t.mean()) * k
    top, bot = m + wob(W, 9) + rng.normal(0, 1.2, W), H - m + wob(W, 9) + rng.normal(0, 1.2, W)
    lef, rig = m + wob(H, 9) + rng.normal(0, 1.2, H), W - m + wob(H, 9) + rng.normal(0, 1.2, H)
    a = ((yy > top[None, :]) & (yy < bot[None, :]) & (xx > lef[:, None]) & (xx < rig[:, None])).astype(np.float32)
    a = blur(np.stack([a] * 3, -1), 0.8)[..., 0]
    # torn paper fibre rim: a thin light band just inside the edge
    rim = np.clip(a - blur(np.stack([a] * 3, -1), 3.0)[..., 0], 0, 1) * 2.2
    rgb = np.asarray(img).astype(np.float32) / 255
    rgb = rgb * (1 - rim[..., None]) + np.array([0.93, 0.90, 0.83]) * rim[..., None]
    img = Image.fromarray(np.dstack([np.clip(rgb, 0, 1), a]).__mul__(255).astype(np.uint8), 'RGBA')

dst = os.path.join(RAW, f'{shot}{tag}_final.png')
img.save(dst)
print('FINAL', dst)
if publish:
    name = OUT_NAME[shot]
    p = os.path.join(PICS, name + '.png')
    img.save(p)
    print('PUBLISHED', p)
