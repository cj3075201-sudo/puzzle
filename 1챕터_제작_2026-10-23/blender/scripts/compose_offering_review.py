# -*- coding: utf-8 -*-
"""Compose the 10/23 story-prop review sheets (python3 + Pillow): art/renders/19_소품_소품시트.png, 19_소품_게임카메라.png
(19_소품_물고기.png is made by compose_fish_v2.py).  usage: python3 compose_offering_review.py [props] [scenes]"""
import sys, os, json
from PIL import Image, ImageDraw, ImageFont

BG, FG, SUB, ACC = (58, 61, 66), (232, 228, 218), (170, 172, 176), (196, 150, 90)   # same as compose_props_review


def font(sz, bold=False):
    for p in (r'/mnt/c/Windows/Fonts/malgunbd.ttf' if bold else r'/mnt/c/Windows/Fonts/malgun.ttf',
              '/usr/share/fonts/truetype/noto/NotoSansCJK-Regular.ttc'):
        if os.path.exists(p):
            return ImageFont.truetype(p, sz)
    return ImageFont.load_default()

HERE = os.path.dirname(os.path.abspath(__file__))
ART = os.path.dirname(HERE)
RAW = os.path.join(ART, 'renders', 'raw', '19')
OUT = os.path.join(ART, 'renders')

LABELS = {
    'RedCord': '붉은 끈(바칠 표시) · 매듭 피벗', 'Sack': '수거꾼 자루(닫힘, Mouth)', 'Sack_Open': '빈 자루(열림, Mouth)', 'HookPole': '수거꾼 갈고리 장대',
    'DecreeScroll': '왕의 풀이 띠(말림, 봉인)', 'DecreeOpen': '펼친 띠 · Face + 밑의 HumanText', 'Lump_Brother': '형 덩어리(붉은 끈·코·모자)',
    'Lump_4': '덩어리 4(다리 하나 남음)', 'Lump_5': '덩어리 5(접혀 엎드린 몸)', 'NoseFileStone': '코 가는 돌', 'SawdustPile': '톱밥 더미(연필 코 조각)',
    'HiddenStash': '숨긴 사람 물건(헝겊 둥지)', 'WallDrawing': '벽 낙서(Face)', 'Bell': '광장 종(반만 지은 틀, Clapper)', 'OfferingPile': '수레에 실린 바칠 것',
}


LABELS2 = {
    'BarkDoor': '나무껍질 문(Door 경첩·Knot)', 'ClothCover': '앉은 덩어리 덮는 자루천', 'MusicBox': '오르골(사람, Lid·Crank)', 'MirrorShard': '거울 조각(사람)',
    'SpinTop': '팽이(사람)', 'Torch': '크리처 횃불(Flame)', 'CordBasket': '붉은 끈 바구니(Lid)', 'CordHook': '벽 고리 + 찢긴 붉은 끈',
    'KidWorkbench': '키노피오 작업대(새 조각들)', 'SawdustBits': '톱밥 흔적',
}


def sheet(out_name, cols=5, tile_w=520, pre='tiles', labels=None, title='1챕터 이야기 소품 · 물고기 배달꾼 · 바치기'):
    LABELS_ = labels or LABELS
    info = json.load(open(os.path.join(RAW, pre + '.json'), encoding='utf-8'))
    names = [n for n in LABELS_ if n in info and os.path.exists(os.path.join(RAW, f'{pre}__{n}.png'))]
    rows = (len(names) + cols - 1) // cols
    th = int(tile_w * 9 / 16)
    W = cols * tile_w + (cols + 1) * 24
    H = 150 + rows * (th + 74) + 30
    im = Image.new('RGB', (W, H), BG)
    d = ImageDraw.Draw(im)
    d.text((24, 24), title, font=font(44, True), fill=FG)
    d.text((24, 84), '사람 물건 = 다 그려지고 원래 색 · 크리처가 만든 것 = 형태가 덜 그려짐 · 붉은 끈만 크리처 물건 중 색 유지(keep) · Face/HumanText 그림은 미리보기용 임시',
           font=font(22), fill=SUB)
    d.line((24, 124, W - 24, 124), fill=ACC, width=2)
    for i, n in enumerate(names):
        r, c = divmod(i, cols)
        x, y = 24 + c * (tile_w + 24), 150 + r * (th + 74)
        im.paste(Image.open(os.path.join(RAW, f'{pre}__{n}.png')).convert('RGB').resize((tile_w, th), Image.LANCZOS), (x, y))
        d.text((x, y + th + 8), n, font=font(22, True), fill=FG)
        it = info[n]
        d.text((x, y + th + 38), f"{LABELS_[n]} · {it['tris']} tri · {max(it['size']):.2f} m", font=font(18), fill=SUB)
    im.save(os.path.join(OUT, out_name))
    print('SHEET', out_name, len(names))


SCENES = [('house', '키노피오의 집 · 의자 위 형 덩어리(붉은 끈) · 톱밥 · 코 가는 돌 · 주인공 망토의 같은 붉은 끈'),
          ('den', '비밀 굴 · 숨긴 사람 물건(원색) · 벽 낙서(두 아이와 빛구멍, 임시 그림)'),
          ('cart', '수레 길 · 수레 위 바칠 것 · 닫힌/열린 자루 · 갈고리 장대 · 수거꾼(실루엣)'),
          ('pond', '웅덩이 가 · 물고기가 뱉은 풀이 띠(왕 글자 띠 밑으로 사람 글) · 덩어리'),
          ('plaza', '광장 · 반만 지은 틀의 종(게임 거리 10 m)')]


SCENES2 = [('den2', '비밀 굴 입구 · 열린 나무껍질 문 · 크리처 횃불(점광원 흉내) · 벽 고리의 찢긴 붉은 끈 · 붉은 끈 바구니 · 톱밥 흔적'),
           ('bench', '키노피오 작업대 · 새 조각(덩이 → 다듬음 → 연필 날개 → 파랑 칠 시작) · 톱밥 흔적이 주인공 쪽으로'),
           ('cloth', '자루천 덮인 의자 위 덩어리(안에서 코가 천을 밀어 올림) · 빛 아래 사람 물건(오르골·거울 조각·팽이)'),
           ('satchel', '주인공 가방 분리 확인: 왼쪽 둘 = Satchel 보임, 오른쪽 둘 = Satchel 끔(앞 3/4 · 뒤 3/4)')]


def scenes(out_name, scene_list=None, title='이야기 소품 · 게임 카메라 검토'):
    have = [(k, t) for k, t in (scene_list or SCENES) if os.path.exists(os.path.join(RAW, k + '.png'))]
    tw, th = 1600, 900
    W = 2 * tw + 72
    rows = (len(have) + 1) // 2
    H = 150 + rows * (th + 60) + 20
    im = Image.new('RGB', (W, H), BG)
    d = ImageDraw.Draw(im)
    d.text((24, 24), title, font=font(44, True), fill=FG)
    d.text((24, 84), '어두운 지하 조명(엔진 드레인 흉내) · 피치 25°, 세로 FOV 32°, 거리 6.5~10 m · 인물은 내보낸 FBX(기본 자세)', font=font(22), fill=SUB)
    d.line((24, 124, W - 24, 124), fill=ACC, width=2)
    for i, (k, t) in enumerate(have):
        r, c = divmod(i, 2)
        x, y = 24 + c * (tw + 24), 150 + r * (th + 60)
        im.paste(Image.open(os.path.join(RAW, k + '.png')).convert('RGB').resize((tw, th), Image.LANCZOS), (x, y))
        d.text((x, y + th + 12), t, font=font(22, True), fill=FG)
    im.save(os.path.join(OUT, out_name))
    print('SHEET', out_name, len(have))


want = set(sys.argv[1:]) or {'props', 'scenes', 'props2', 'scenes2'}
if 'props2' in want:
    sheet('19_소품_2_소품시트.png', pre='tiles2', labels=LABELS2, title='1챕터 이야기 소품 2 · 비밀 굴 · 사람 물건 · 붉은 끈')
if 'scenes2' in want:
    scenes('19_소품_2_게임카메라.png', SCENES2, '이야기 소품 2 · 게임 카메라 검토')
if 'props' in want:
    sheet('19_소품_소품시트.png')
if 'scenes' in want:
    scenes('19_소품_게임카메라.png')
