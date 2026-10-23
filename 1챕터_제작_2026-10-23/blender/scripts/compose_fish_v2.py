# Compose art/renders/19_소품_물고기.png from render_fish_v2 cells (python3 + PIL).
import os, json
from PIL import Image, ImageDraw, ImageFont
HERE = os.path.dirname(os.path.abspath(__file__))
ART = os.path.dirname(HERE)
RAW = os.path.join(ART, 'renders', 'raw', '19_fish')
cells = json.load(open(os.path.join(RAW, 'cells.json'), encoding='utf-8'))
rep = json.load(open(os.path.join(ART, 'blend', 'chars_v2', 'report.json'), encoding='utf-8'))['Fish']
ORDER = ['hidden', 'rise_1', 'rise_2', 'rise_3', 'rise_4', 'idle_0', 'idle_side', 'idle_far', 'open_end', 'open_side', 'swal_1', 'swal_2',
         'swal_3', 'spit_1', 'spit_2', 'spit_3', 'sink_1', 'sink_2']
BG, FG, SUB, LINE = (52, 56, 62), (236, 233, 226), (175, 172, 165), (200, 160, 90)


def font(sz, bold=False):
    p = '/mnt/c/Windows/Fonts/malgunbd.ttf' if bold else '/mnt/c/Windows/Fonts/malgun.ttf'
    return ImageFont.truetype(p, sz) if os.path.exists(p) else ImageFont.load_default()


ims = [(cells[n], Image.open(os.path.join(RAW, n + '.png')).convert('RGB')) for n in ORDER if n in cells]
w, h = ims[0][1].size
cols, pad, top = 3, 18, 130
rows = (len(ims) + cols - 1) // cols
W = cols * w + (cols + 1) * pad
H = top + rows * (h + 44) + pad
out = Image.new('RGB', (W, H), BG)
d = ImageDraw.Draw(out)
d.text((pad, 18), '물고기(왕의 배달꾼) · 뼈대 + 동작 7개', fill=FG, font=font(40, True))
clips = ' · '.join(f"{c['clip']} {c['frames']}f{'(반복)' if c['loop'] else ''}" for c in rep['clips'])
d.text((pad, 72), f"게임 카메라(피치 25°, 세로 FOV 32°, 20 m) · 어두운 지하 조명 · 검은 웅덩이 반지름 6 m · 주인공 1.25 m·키노피오 0.87 m · {rep['tris']} tri · 30fps · {clips}",
       fill=SUB, font=font(18))
d.line((pad, 110, W - pad, 110), fill=LINE, width=2)
for i, (c, im) in enumerate(ims):
    x = pad + (i % cols) * (w + pad)
    y = top + (i // cols) * (h + 44)
    out.paste(im, (x, y))
    d.text((x, y + h + 6), c['label'], fill=FG, font=font(20, True))
dst = os.path.join(ART, 'renders', '19_소품_물고기.png')
out.save(dst)
print('SAVED', dst, out.size)
