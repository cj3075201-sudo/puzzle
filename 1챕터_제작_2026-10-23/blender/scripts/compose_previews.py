# Compose final preview sheets (python3 + PIL): paper background/grain, titles, labels.
# usage: python3 compose_previews.py [lineup hero props kit village_overview village_plaza village_pond]
import sys, os, json
import numpy as np
from PIL import Image, ImageDraw, ImageFont, ImageFilter

HERE = os.path.dirname(os.path.abspath(__file__))
ART = os.path.dirname(HERE)
RAW = os.path.join(ART, 'renders', 'raw')
OUT = os.path.join(ART, 'renders')
FONT_DIR = '/mnt/c/Users/cj307/AppData/Local/Microsoft/Windows/Fonts'
STATS = json.load(open(os.path.join(ART, 'blend', 'asset_stats.json'), encoding='utf-8'))
PAPER = (241, 238, 230)
INK = (43, 38, 34)
GREY = (120, 124, 130)


def font(size, bold=False):
    for n in (('Pretendard-Bold.ttf' if bold else 'Pretendard-Regular.ttf'), 'Pretendard-Medium.ttf'):
        p = os.path.join(FONT_DIR, n)
        if os.path.exists(p):
            return ImageFont.truetype(p, size)
    return ImageFont.truetype('/mnt/c/Windows/Fonts/malgun.ttf', size)


def paper_grain(w, h, seed=3, strength=0.05):
    rng = np.random.default_rng(seed)
    fine = rng.normal(0, 1, (h, w)).astype(np.float32)
    small = Image.fromarray(((rng.random((h // 24 + 2, w // 24 + 2)) * 255).astype(np.uint8)))
    blot = np.asarray(small.resize((w, h), Image.BICUBIC).filter(ImageFilter.GaussianBlur(30)), dtype=np.float32) / 255.0
    g = 1.0 - strength * (0.35 * np.clip(fine, -2, 2) / 2 + 0.65 * (blot - 0.5))
    yy, xx = np.mgrid[0:h, 0:w]
    vig = 1.0 - 0.10 * (((xx / w - 0.5) ** 2 + (yy / h - 0.5) ** 2) * 2.2)
    return g * vig


def apply_grain(img, strength=0.05):
    a = np.asarray(img.convert('RGB'), dtype=np.float32)
    g = paper_grain(img.width, img.height, strength=strength)[..., None]
    return Image.fromarray(np.clip(a * g, 0, 255).astype(np.uint8))


def on_paper(raw, pad_top=0, pad_bottom=0):
    im = Image.open(raw).convert('RGBA')
    bg = Image.new('RGBA', (im.width, im.height + pad_top + pad_bottom), PAPER + (255,))
    bg.alpha_composite(im, (0, pad_top))
    return bg


def title_block(d, w, title, sub, y=40, x=70):
    d.text((x, y), title, font=font(64, True), fill=INK)
    d.text((x, y + 92), sub, font=font(30), fill=GREY)
    d.line((x, y + 150, w - x, y + 150), fill=(200, 160, 90), width=4)


def label(d, x, y, t1, t2=None, size=30, anchor='ma'):
    d.text((x, y), t1, font=font(size, True), fill=INK, anchor=anchor)
    if t2:
        d.text((x, y + size + 8), t2, font=font(int(size * 0.78)), fill=GREY, anchor=anchor)


def compose_lineup():
    js = json.load(open(os.path.join(RAW, 'lineup.json'), encoding='utf-8'))
    raw = Image.open(os.path.join(RAW, 'lineup.png')).convert('RGBA')
    W, H = js['res']
    bb = raw.getchannel('A').point(lambda v: 255 if v > 40 else 0).getbbox()
    ct = max(0, bb[1] - 40)
    raw = raw.crop((0, ct, W, H))
    top, left = 230, 120
    im = Image.new('RGBA', (W + left, raw.height + top + 40), PAPER + (255,))
    im.alpha_composite(raw, (left, top))
    d = ImageDraw.Draw(im)
    title_block(d, im.width, '1챕터 등장 인물 — 크기 비교',
                '1 = 1m · 주인공 약 1.05m · 색 = 완성도: 파랑새만 꽉 찬 색, 주민은 칠하다 만 목각 인형, 말 못 하는 주민은 검은 실루엣')
    for i, (x, y) in enumerate(js.get('ruler', [])):
        px, py = x * W + left, y * H - ct + top
        if py < top + 10:
            continue
        d.line((px - 40, py, px + 10, py), fill=GREY, width=2)
        d.text((px - 50, py), f'{i}m', font=font(24), fill=GREY, anchor='rm')
    names = {'Hero_Bluebird': '파랑새', 'Kinopio': '키노피오', 'Villager_A': '주민 A', 'Villager_B': '주민 B', 'Villager_C': '주민 C',
             'Mother': '어미', 'Chief': '촌장', 'Silhouette_A': '실루엣 A', 'Silhouette_B': '실루엣 B', 'Puppet': '나무 인형',
             'Lump_1': '덩어리 1', 'Lump_2': '덩어리 2', 'Lump_3': '덩어리 3', 'Fish': '물고기'}
    for it in js['labels']:
        n = it['name']
        s = STATS.get(n, {})
        x, y = it['x'] * W + left, it['y'] * H - ct + top + 22
        sub = (f"길이 {max(s['size']):.1f}m · {s['tris']}" if n == 'Fish' else f"{s['size'][2]:.2f}m · {s.get('tris', 0)}")
        label(d, x, y, names.get(n, n), sub, size=27)
    ymax = max(it['y'] * H - ct + top for it in js['labels']) + 110
    im = im.crop((0, 0, im.width, int(min(im.height, ymax))))
    im = apply_grain(im)
    im.save(os.path.join(OUT, '01_인물_크기비교.png'))


def compose_hero():
    js = json.load(open(os.path.join(RAW, 'hero.json'), encoding='utf-8'))
    top = 230
    im = on_paper(os.path.join(RAW, 'hero.png'), pad_top=top, pad_bottom=20)
    W, H = js['res']
    d = ImageDraw.Draw(im)
    s = STATS['Hero_Bluebird']
    title_block(d, im.width, '주인공 — 파랑새 의인화',
                f"코발트 2F5FD0 · 배 D9DEE8 · 검은 부리 · 헌팅캡·짧은 망토·크로스 가방(성은 시안 L) · {s['size'][2]:.2f}m · {s['tris']}tri · 부위 {len(s['parts'])}개")
    for it in js['labels']:
        label(d, it['x'] * W, it['y'] * H + top + 30, it['label'], size=30)
    im = apply_grain(im)
    im.save(os.path.join(OUT, '02_주인공_돌려보기.png'))


def compose_grid(raw, out, title, sub):
    js = json.load(open(os.path.join(RAW, raw + '.json'), encoding='utf-8'))
    top = 230
    im = on_paper(os.path.join(RAW, raw + '.png'), pad_top=top, pad_bottom=20)
    W, H = js['res']
    d = ImageDraw.Draw(im)
    title_block(d, im.width, title, sub)
    for it in js['labels']:
        s = STATS.get(it['name'], {})
        sz = s.get('size', [0, 0, 0])
        label(d, it['x'] * W, it['y'] * H + top + 14, it['name'], f"{s.get('tris', 0)}tri · {max(sz):.1f}m", size=24)
    im = apply_grain(im)
    im.save(os.path.join(OUT, out))


def compose_scene(raw, out, title, sub):
    im = Image.open(os.path.join(RAW, raw + '.png')).convert('RGB')
    im = apply_grain(im, 0.06)
    top = 200
    can = Image.new('RGB', (im.width, im.height + top), PAPER)
    can.paste(im, (0, top))
    d = ImageDraw.Draw(can)
    d.text((70, 36), title, font=font(60, True), fill=INK)
    d.text((70, 120), sub, font=font(30), fill=GREY)
    can.save(os.path.join(OUT, out))


KR_NAMES = {
    'Sketch_Wall_1': '그리다 만 벽 1', 'Sketch_Wall_2': '벽 2(창 선)', 'Sketch_Wall_3': '벽 3(모서리)', 'Sketch_Tree_1': '선 나무(낙서 잎)',
    'Sketch_Tree_2': '선 나무(종이 잎)', 'Sketch_Tree_3': '마른 선 나무', 'Sketch_Fence_1': '그리다 만 울타리 1', 'Sketch_Fence_2': '울타리 2',
    'Sketch_Arch': '선으로만 된 아치', 'Scrap_Paper_1': '구긴 종이', 'Scrap_Paper_2': '찢긴 종이', 'Scrap_Paper_3': '접힌 종이',
    'Stair_Sketch': '어디로도 안 가는 계단', 'Bench_Puppet': '목각 긴의자', 'Barrel': '통', 'Crate': '상자', 'Basket': '키노피오 바구니',
    'Lantern_Hanging': '매단 등', 'Banner_Unfinished': '칠하다 만 현수막', 'Rubble_1': '종이돌 더미 1', 'Rubble_2': '종이돌 더미 2',
    'PaintPot': '물감 통', 'Brush_Big': '떨어진 큰 붓', 'FX_InkRing': '먹 고리', 'FX_Splash': '튀는 먹 왕관', 'FX_Dust': '종이 먼지',
    'Ladder': '접힌 사다리(사람 걸쇠)', 'Latch': '사람 걸쇠', 'DrawnBar': '그려진 빗장', 'Gap': '좁은 틈', 'Cart': '수레(사람 고정쇠)',
    'Chair': '의자(새김 면)', 'Stage': '무대(받침대·인형 자리)', 'PictureBoard': '그림판', 'StoneTablet': '새김 돌판', 'Signpost': '팻말',
    'Fence_DrawnBar': '빗장 울타리', 'FishProp': '극 소품 물고기', 'Junk_Book': '책', 'Junk_Umbrella': '우산', 'Junk_Clock': '시계',
    'Junk_Shoe': '신발', 'Junk_Teacup': '찻잔', 'Junk_Lantern': '등', 'ItemPile': '물건 더미', 'PinocchioPage': '피노키오 낱장',
    'Mound': '밭 둔덕', 'LampPost': '가로등', 'House_1': '집 1(안 칠함)', 'House_2': '집 2(위 1/3)', 'House_3': '집 3(2/3)',
    'House_4': '집 4(거의 다)', 'Tower_Dome': '돔 탑(광장)', 'Paving_Hex': '육각 돌길 선', 'Paving_HexBroken': '돌길 선(덜 그림)',
    'Spire_1': '첨탑 1', 'Spire_2': '첨탑 2', 'Spire_3': '첨탑 3', 'Cliff_1': '바위턱 1', 'Cliff_2': '바위턱 2', 'Cliff_3': '바위턱 3',
    'CaveWall_1': '동굴 벽 1', 'CaveWall_2': '동굴 벽 2(버팀)', 'CaveWall_3': '동굴 벽 3(굽음)', 'Rock_1': '바위 1', 'Rock_2': '바위 2',
    'Rock_3': '바위 3', 'Pond': '검은 물웅덩이', 'LightShaft': '빛줄기', 'CeilingHole': '천장 구멍'}


def compose_tiles(group, out, title, sub, cols=6):
    names = [n for n, s in STATS.items() if s['group'] == group]
    cell, lab = 500, 96
    rows = (len(names) + cols - 1) // cols
    W = cols * cell + 140
    top = 230
    im = Image.new('RGBA', (W, top + rows * (cell + lab) + 40), PAPER + (255,))
    d = ImageDraw.Draw(im)
    title_block(d, W, title, sub)
    for i, n in enumerate(names):
        x0 = 70 + (i % cols) * cell
        y0 = top + (i // cols) * (cell + lab)
        p = os.path.join(RAW, 'thumbs', n + '.png')
        if os.path.exists(p):
            t = Image.open(p).convert('RGBA')
            t.thumbnail((cell - 30, cell - 30))
            im.alpha_composite(t, (x0 + (cell - t.width) // 2, y0 + (cell - t.height) // 2))
        s = STATS[n]
        label(d, x0 + cell // 2, y0 + cell - 6, f"{n}", f"{KR_NAMES.get(n, '')} · {s['tris']}tri · {max(s['size']):.1f}m", size=26)
    im = apply_grain(im)
    im.save(os.path.join(OUT, out))


def compose_level_top():
    js = json.load(open(os.path.join(RAW, 'level_top.json'), encoding='utf-8'))
    im = Image.open(os.path.join(RAW, 'level_top.png')).convert('RGB')
    W, H = js['res']
    ov = Image.new('RGBA', im.size, (0, 0, 0, 0))
    d = ImageDraw.Draw(ov)
    for g in js['grid']:
        (ax, ay), (bx, by) = g['a'], g['b']
        d.line((ax * W, ay * H, bx * W, by * H), fill=(90, 110, 140, 70), width=2)
        if g['axis'] == 'x':
            d.text((ax * W + 4, H - 40), f"x {g['v']}", font=font(22), fill=(70, 90, 120, 200))
        else:
            d.text((8, ay * H - 26), f"z {g['v']}", font=font(22), fill=(70, 90, 120, 200))
    for it in js['items']:
        x, y, r = it['x'] * W, it['y'] * H, it['r'] * W
        if it['kind'] == 'place':
            d.ellipse((x - r, y - r, x + r, y + r), outline=(200, 140, 40, 200), width=4)
            d.text((x, y - r - 34), it['id'], font=font(34, True), fill=(150, 95, 20, 255), anchor='mm')
        elif it['kind'] == 'zone':
            d.ellipse((x - r, y - r, x + r, y + r), outline=(30, 110, 200, 230), width=3)
            d.text((x + r + 4, y), it['id'][2:], font=font(18), fill=(30, 90, 170, 255), anchor='lm')
        else:
            d.rectangle((x - 5, y - 5, x + 5, y + 5), fill=(200, 50, 40, 230))
    im = Image.alpha_composite(im.convert('RGBA'), ov).convert('RGB')
    compose_scene_img(im, '09_레벨_위에서_구역표시.png', 'Level_Ch1 — 위에서 본 1챕터 지형 + chapter1.json 구역',
                      '주황 원 = 장소, 파란 원 = zones[], 빨간 점 = props[] · 격자 20m(Unity x, z) · 천장·배경 숨김 · 꾸밈(layout_dressing.json) 포함')


def compose_scene_img(im, out, title, sub):
    im = apply_grain(im, 0.05)
    top = 200
    can = Image.new('RGB', (im.width, im.height + top), PAPER)
    can.paste(im, (0, top))
    d = ImageDraw.Draw(can)
    d.text((70, 36), title, font=font(60, True), fill=INK)
    d.text((70, 120), sub, font=font(30), fill=GREY)
    can.save(os.path.join(OUT, out))


def compose_gamecams():
    names = [('cam_fall', '빛구멍 언덕'), ('cam_gate', '앉은돌 길목'), ('cam_plaza', '꼭두 광장'), ('cam_alley', '삐걱의자 골목'), ('cam_field', '기적의 밭'), ('cam_pond', '먹물 웅덩이')]
    cw, ch = 1280, 720
    can = Image.new('RGB', (cw * 2 + 90, 230 + (ch + 70) * 3), PAPER)
    d = ImageDraw.Draw(can)
    title_block(d, can.width, '게임 카메라로 본 여섯 장소', 'SceneBuilder FollowCamera 값(yaw·pitch·거리·fov) 그대로 · Level_Ch1 + 모델 배치 + 꾸밈 배치 · Blender 미리보기(툰·잉크 외곽선·빗금)')
    for k, (n, label_) in enumerate(names):
        p = os.path.join(RAW, n + '.png')
        if not os.path.exists(p):
            continue
        im = Image.open(p).convert('RGB').resize((cw, ch), Image.LANCZOS)
        x, y = 45 + (k % 2) * (cw + 0), 230 + (k // 2) * (ch + 70)
        can.paste(im, (x, y))
        d.text((x + 10, y + ch + 12), label_, font=font(30, True), fill=INK)
    apply_grain(can, 0.04).save(os.path.join(OUT, '12_게임카메라_여섯장소.png'))


def compose_pages():
    names = [('a_fall', '빛구멍 언덕'), ('a_gate', '앉은돌 길목'), ('a_cart', '수레 길'), ('a_plaza', '꼭두 광장'), ('a_alley', '삐걱의자 골목'), ('a_field', '기적의 밭 · 먹물 웅덩이')]
    cw, ch = 960, 540
    can = Image.new('RGB', (cw * 2 + 150, 230 + (ch + 60) * 6), PAPER)
    d = ImageDraw.Draw(can)
    title_block(d, can.width, '구역 = 그림책 한 쪽 (areas[])', '왼쪽: areas[].camera 값 그대로 · 오른쪽: 같은 방향 1.9배 거리(쪽 전체와 여백) · 활성 구역만 보이고 바탕은 빈 종이')
    for k, (n, label_) in enumerate(names):
        y = 230 + k * (ch + 60)
        for j, suf in enumerate(('', '_wide')):
            p = os.path.join(RAW, f'page_{n}{suf}.png')
            if not os.path.exists(p):
                continue
            im = Image.open(p).convert('RGBA')
            bg = Image.new('RGBA', im.size, PAPER + (255,))
            bg.alpha_composite(im)
            can.paste(bg.convert('RGB').resize((cw, ch), Image.LANCZOS), (50 + j * (cw + 50), y))
        d.text((50, y + ch + 8), f'{label_}  ({n})', font=font(28, True), fill=INK)
    apply_grain(can, 0.04).save(os.path.join(OUT, '14_구역_페이지.png'))


JOBS = {
    'pages': compose_pages,
    'level_top': compose_level_top,
    'dressing': lambda: compose_tiles('dressing', '13_꾸밈_키트.png', '꾸밈 키트(2차) + 효과 메시',
                                      '그리다 만 선 + 흰 종이 · 광장 가까운 것만 칠해짐(현수막·등·붓 유물) · FX = 먹 고리·튀는 먹 왕관·종이 먼지'),
    'gamecams': compose_gamecams,
    'eye_plaza': lambda: compose_scene('eye_plaza', '10_눈높이_광장.png', '눈높이 — 꼭두 광장', '칠해진 육각 돌·무대·현수막·등불(다 그려진 곳) · 붓 유물과 그림판 · 바깥은 흰 종이와 선'),
    'eye_gate': lambda: compose_scene('eye_gate', '11_눈높이_길목.png', '눈높이 — 앉은돌 길목에서 광장 쪽', '바위턱 사이 길, 선으로만 그린 울타리·나무·벽 · 길 돌은 광장에 가까울수록 칠해짐'),
    'lineup': compose_lineup,
    'hero': compose_hero,
    'props': lambda: compose_tiles('props', '03_소품_시트.png', '소품·퍼즐 물건',
                                  '사람 물건은 원래 색 그대로 진하게(놋쇠·쇠·끈·책) · 마을 물건은 흰 종이와 잉크 · 무대 쪽만 칠해짐 · 칸마다 크기 다름(아래 m 참고)'),
    'kit': lambda: compose_tiles('village', '04_마을_키트.png', '마을 키트',
                                '흰 종이 세계 + 잉크 선 + 회청 빗금 그늘 · 테라코타 돔 탑은 광장 가까울수록 더 칠해짐 · 칸마다 크기 다름(아래 m 참고)'),
    'village_overview': lambda: compose_scene('village_overview', '05_마을_전경_위에서.png', '마을 전경 — 위에서 본 배치',
                                              '§2 좌표 그대로(왼쪽 위 낙하터 → 어귀 → 광장 → 집 골목 → 밭 → 오른쪽 아래 물웅덩이) · 빛은 천장 구멍 빛줄기와 광장 등불뿐'),
    'village_fall': lambda: compose_scene('village_fall', '06_낙하터.png', '낙하터 — 빛줄기 아래 깨어남',
                                          '흰 종이 땅 위 사람 물건(책·우산·시계·등)만 진한 색 · 주인공과 엎드린 키노피오 · 잉크 선으로 그린 바위턱'),
    'village_plaza': lambda: compose_scene('village_plaza', '07_광장_무대.png', '광장 — 무대와 그림판',
                                           '붉은 막·남색 배경·등불 = 다 그려진 곳 · 끈에 묶인 나무 인형 · 촌장 · 엎드린 구경꾼 · 육각 돌길은 선으로만'),
    'village_pond': lambda: compose_scene('village_pond', '08_밭끝_물웅덩이.png', '밭 끝 물웅덩이 — 물고기',
                                          '검은 물웅덩이 밑에서 튀어나오는 물고기(약 9.9m) · 밭 끝까지 밀려 온 수레 · 엎드린 주민 · 주인공 크기 비교'),
}

if __name__ == '__main__':
    todo = sys.argv[1:] or list(JOBS)
    for k in todo:
        try:
            JOBS[k]()
            print('OK', k)
        except FileNotFoundError as e:
            print('MISSING', k, e)
