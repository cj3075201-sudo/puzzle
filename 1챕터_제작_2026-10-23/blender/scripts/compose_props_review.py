# -*- coding: utf-8 -*-
"""Compose the 10/23 prop review sheets (python3 + Pillow): art/renders/17_소품_*.png
usage: python3 compose_props_review.py [sheet ...]   sheets: village props dressing scenes"""
import sys, os, json
from PIL import Image, ImageDraw, ImageFont

HERE = os.path.dirname(os.path.abspath(__file__))
ART = os.path.dirname(HERE)
RAW = os.path.join(ART, 'renders', 'raw', '17')
OUT = os.path.join(ART, 'renders')
BG = (58, 61, 66)
FG = (232, 228, 218)
SUB = (170, 172, 176)
ACC = (196, 150, 90)


def font(sz, bold=False):
    for p in (r'/mnt/c/Windows/Fonts/malgunbd.ttf' if bold else r'/mnt/c/Windows/Fonts/malgun.ttf',
              '/usr/share/fonts/truetype/noto/NotoSansCJK-Regular.ttc'):
        if os.path.exists(p):
            return ImageFont.truetype(p, sz)
    return ImageFont.load_default()


LABELS = {
    'House_1': '집 1 · 바깥(약 20% 지어짐)', 'House_2': '집 2 · 약 45%', 'House_3': '집 3 · 약 70%', 'House_4': '집 4 · 광장 옆 약 95%',
    'Tower_Dome': '돔 탑 · 광장(다 그려짐)',
    'Ladder': '사다리(사람 물건, 완성)', 'Latch': '걸쇠(사람 물건)', 'DrawnBar': '그려진 빗장', 'Cart': '수레(먼 바퀴 = 연필 원)', 'Chair': '의자(뒷다리 연필)',
    'Signpost': '팻말(판 반만 칠함)', 'StoneTablet': '새김 돌판(윗모서리 선)', 'PictureBoard': '왕의 그림판(완성)', 'LampPost': '가로등(광장, 완성)',
    'Fence_DrawnBar': '빗장 울타리', 'ItemPile': '물건 더미(빛 아래)', 'Junk_Book': '책', 'Junk_Umbrella': '우산', 'Junk_Clock': '시계', 'Junk_Shoe': '신발',
    'Junk_Teacup': '찻잔', 'Junk_Lantern': '등', 'Gap': '좁은 틈',
    'Barrel': '통(통널 반은 선)', 'Crate': '상자(두 면만 지어짐)', 'Basket': '바구니', 'Bench_Puppet': '목각 긴의자', 'Lantern_Hanging': '매단 등',
    'PaintPot': '물감 통', 'Brush_Big': '큰 붓 유물', 'Banner_Unfinished': '칠하다 만 현수막', 'Sketch_Wall_1': '그리다 만 벽 1', 'Sketch_Wall_2': '벽 2(창)',
    'Sketch_Wall_3': '벽 3(모서리)', 'Sketch_Tree_1': '선 나무 1', 'Sketch_Tree_2': '선 나무 2', 'Sketch_Tree_3': '마른 선 나무', 'Sketch_Fence_1': '울타리',
    'Sketch_Arch': '선 아치', 'Stair_Sketch': '어디로도 안 가는 계단', 'Rubble_1': '종이돌 더미',
}


def sheet(key, title, subtitle, cols, out_name, tile_w=520):
    jp = os.path.join(RAW, f'{key}.json')
    info = json.load(open(jp, encoding='utf-8')) if os.path.exists(jp) else {}
    names = [n for n in info if os.path.exists(os.path.join(RAW, f'{key}__{n}.png'))]
    order = list(LABELS.keys())
    names.sort(key=lambda n: order.index(n) if n in order else 999)
    rows = (len(names) + cols - 1) // cols
    th = int(tile_w * 9 / 16)
    W = cols * tile_w + (cols + 1) * 24
    H = 150 + rows * (th + 74) + 30
    im = Image.new('RGB', (W, H), BG)
    d = ImageDraw.Draw(im)
    d.text((24, 24), title, font=font(44, True), fill=FG)
    d.text((24, 84), subtitle, font=font(22), fill=SUB)
    d.line((24, 124, W - 24, 124), fill=ACC, width=2)
    for i, n in enumerate(names):
        r, c = divmod(i, cols)
        x = 24 + c * (tile_w + 24)
        y = 150 + r * (th + 74)
        t = Image.open(os.path.join(RAW, f'{key}__{n}.png')).convert('RGB').resize((tile_w, th), Image.LANCZOS)
        im.paste(t, (x, y))
        d.text((x, y + th + 8), n, font=font(22, True), fill=FG)
        it = info[n]
        d.text((x, y + th + 38), f"{LABELS.get(n, '')} · {it['tris']} tri · {max(it['size']):.1f} m", font=font(18), fill=SUB)
    im.save(os.path.join(OUT, out_name))
    print('SHEET', out_name, len(names))


def scenes(out_name):
    shots = [('fall', '낙하터 · 빛줄기 아래가 가장 밝음(물건 더미만 따뜻하게)'), ('houses', '게임 카메라 거리(약 10~13 m, 25°) · 바깥 집 두 채'),
             ('street', '바깥 → 광장 길 · 완성도 단계(왼쪽 덜 지어짐 → 오른쪽 다 그려짐)'), ('plaza', '광장 · 다 그려진 쪽, 등불만 따뜻하게')]
    files = {'fall': 'fall.png', 'houses': 'houses_close.png', 'street': 'street.png', 'plaza': 'plaza.png'}
    have = [(k, t) for k, t in shots if os.path.exists(os.path.join(RAW, files[k]))]
    tw, th = 1600, 900
    W = tw + 48
    H = 150 + len(have) * (th + 60) + 20
    im = Image.new('RGB', (W, H), BG)
    d = ImageDraw.Draw(im)
    d.text((24, 24), '소품·마을 · 게임 카메라 검토', font=font(44, True), fill=FG)
    d.text((24, 84), '지하 세계: 어둡고 색 빠짐(엔진 드레인 흉내) · 사람 물건만 원래 색 · 피치 25°, 세로 FOV 32°', font=font(22), fill=SUB)
    d.line((24, 124, W - 24, 124), fill=ACC, width=2)
    for i, (k, t) in enumerate(have):
        y = 150 + i * (th + 60)
        im.paste(Image.open(os.path.join(RAW, files[k])).convert('RGB').resize((tw, th), Image.LANCZOS), (24, y))
        d.text((24, y + th + 12), t, font=font(22, True), fill=FG)
    im.save(os.path.join(OUT, out_name))
    print('SHEET', out_name, len(have))


want = set(sys.argv[1:]) or {'village', 'props', 'dressing', 'scenes'}
if 'village' in want:
    sheet('tiles_village', '마을 키트 · 형태가 덜 지어진 집', '바깥 → 광장으로 갈수록 더 지어지고 칠해짐 · 지어진 곳 = 두께 있는 종이 껍질, 안 지어진 곳 = 연필 구성선·빗금·지운 자국',
          3, '17_소품_마을키트.png', 600)
if 'props' in want:
    sheet('tiles_props', '소품·퍼즐 물건', '사람 물건은 다 그려지고 원래 색 · 크리처 물건은 한 군데씩 일부러 덜 그려짐', 6, '17_소품_소품시트.png')
if 'dressing' in want:
    sheet('tiles_dressing', '꾸밈 키트', '통·상자·바구니·의자·등·붓 · 형태가 일부만 지어짐', 6, '17_소품_꾸밈키트.png')
if 'scenes' in want:
    scenes('17_소품_게임카메라.png')
