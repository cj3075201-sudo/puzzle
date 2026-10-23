# -*- coding: utf-8 -*-
"""PREVIEW-ONLY stand-in textures for the 10/23 story props' UV planes (python3 + Pillow). Not game art:
the real glyph band / human page / child drawing textures belong to the UI/glyph pipeline.
Writes art/renders/raw/19/tex_decree_face.png, tex_human_text.png, tex_wall_drawing.png"""
import os, random, math
from PIL import Image, ImageDraw
HERE = os.path.dirname(os.path.abspath(__file__))
RAW = os.path.join(os.path.dirname(HERE), 'renders', 'raw', '19')
os.makedirs(RAW, exist_ok=True)
rnd = random.Random(5)

# king's band: yellowed creature paper, ruled border, rows of blocky creature glyphs (plum-black)
W, H = 1560, 500
im = Image.new('RGB', (W, H), (228, 217, 188)); d = ImageDraw.Draw(im)
for y in (36, H - 36):
    d.line((30, y, W - 30, y), fill=(58, 34, 56), width=6)
x = 70
while x < W - 120:
    for row in range(2):
        cy = 150 + row * 190
        g = rnd.randint(0, 3)
        if g == 0:
            d.rectangle((x, cy - 50, x + 70, cy + 50), outline=(40, 26, 40), width=12)
            d.line((x + 35, cy - 50, x + 35, cy + 70), fill=(40, 26, 40), width=12)
        elif g == 1:
            d.ellipse((x, cy - 45, x + 80, cy + 45), outline=(40, 26, 40), width=12)
            d.line((x - 5, cy, x + 90, cy - 30), fill=(40, 26, 40), width=10)
        elif g == 2:
            d.polygon([(x, cy + 50), (x + 40, cy - 55), (x + 85, cy + 50)], outline=(40, 26, 40), width=12)
        else:
            for k in range(3):
                d.line((x + k * 30, cy - 50, x + k * 30 + 10, cy + 50), fill=(40, 26, 40), width=11)
    x += rnd.randint(120, 160)
im.save(os.path.join(RAW, 'tex_decree_face.png'))

# human page: warm white, sepia handwriting lines
W, H = 1280, 800
im = Image.new('RGB', (W, H), (250, 244, 230)); d = ImageDraw.Draw(im)
for row in range(9):
    y = 80 + row * 78
    x = 70 + (40 if row == 0 else 0)
    while x < W - 90 and not (row == 8 and x > W * 0.45):
        wl = rnd.randint(50, 150)
        pts = [(x + t * wl / 12, y + 10 * math.sin(t * 1.9 + row) + rnd.uniform(-5, 5)) for t in range(13)]
        d.line(pts, fill=(92, 60, 36), width=5)
        x += wl + rnd.randint(22, 40)
im.save(os.path.join(RAW, 'tex_human_text.png'))

# child's wall drawing: charcoal on the rubbed-clean wall - two children holding hands under the light hole
W, H = 1000, 720
im = Image.new('RGB', (W, H), (236, 232, 222)); d = ImageDraw.Draw(im)
C = (44, 40, 38)
d.ellipse((410, 40, 590, 150), outline=C, width=9)
for k in range(9):
    a = math.pi * (0.15 + 0.7 * k / 8)
    d.line((500 + math.cos(a) * 110, 190 - math.sin(a) * 30, 500 + math.cos(a) * 200, 330 - math.sin(a) * 40), fill=C, width=5)
for cx, h_, hat in ((380, 300, True), (600, 250, False)):
    top = 640 - h_
    d.ellipse((cx - 45, top - 90, cx + 45, top), outline=C, width=9)
    if hat:
        d.line((cx - 55, top - 80, cx + 55, top - 95), fill=C, width=10); d.rectangle((cx - 35, top - 125, cx + 35, top - 85), outline=C, width=8)
    else:
        d.line((cx, top - 50, cx + 60, top - 40), fill=C, width=6)   # long nose
    d.line((cx, top, cx, top + h_ * 0.55), fill=C, width=10)
    d.line((cx, top + h_ * 0.55, cx - 40, 640), fill=C, width=10); d.line((cx, top + h_ * 0.55, cx + 40, 640), fill=C, width=10)
    d.line((cx, top + 40, cx - 70, top + 110), fill=C, width=9); d.line((cx, top + 40, cx + 70, top + 110), fill=C, width=9)
d.line((450, 445, 530, 470), fill=C, width=9)
im.save(os.path.join(RAW, 'tex_wall_drawing.png'))
print('TEX done')
