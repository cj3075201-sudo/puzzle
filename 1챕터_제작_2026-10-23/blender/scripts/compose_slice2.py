# Slice-2 sheets (python3 + PIL): art/renders/18_구역_<id>.png — three game-camera frames + reading notes per area.
import os, json, sys
from PIL import Image, ImageDraw
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from compose_previews import font, PAPER, INK, GREY

ART = os.path.dirname(HERE)
RAW = os.path.join(ART, 'renders', 'raw', '18')
OUT = os.path.join(ART, 'renders')
ACC = (184, 134, 62)
LAY = json.load(open(os.path.join(ART, 'layout_slice2.json'), encoding='utf-8'))
AREAS = {a['id']: a for a in LAY['areas']}

NOTES = {
    'a_plaza': ['# 읽는 법', '길목 계단을 내려오면 무대가 정면(무대 앞 = 길목 쪽, 서남서)', '무대 양옆 칠한 틀 = 왕의 풀이 그림판 4장(오른쪽 끝 틀은 덜 지어짐)',
                '극장 탑: 남쪽은 돔까지 칠함, 북쪽은 위가 연필 비계(덜 그려진 형태)', '가운데 그려진 고리 = 청중 자리, 먹을 것 탁자·천막(하나는 뼈대만)',
                '오른쪽 아래 종 누각(새로) 옆 계단 = 수레 길 · 오른쪽 위 좁은 길 = 골목',
                '# 빛', '가장 칠해진 곳이지만 땅 밑: 무대 등·가로등 웅덩이만 밝음 (분위기 덮어쓰기 ambient 0.72 · key 0.28 · drain 0.30)'],
    'a_alley': ['# 읽는 법', '광장 쪽(왼쪽 아래)일수록 집이 많이 지어짐 → 골목 끝으로 갈수록 집이 선뿐',
                '집마다 앞 의자에 덩어리(껍데기), 의자 둘레 그려진 자리 고리', '끝: 키노피오 집 — 앞벽이 연필뿐이라 안이 보임(형 덩어리 의자·코 톱밥·초 하나)',
                '집 옆 바위 틈(폭 0.9m) = 비밀 굴 · 오른쪽 난간 틈 긴 계단 = 밭', '빨래줄(종이·덜 칠한 셔츠)이 골목을 가로질러 깊이를 만듦',
                '# 빛', '어둑함(ambient 0.66 · key 0.24 · drain 0.5). 키노피오 집 앞 등과 안의 초만 따뜻'],
    'a_hideout': ['# 읽는 법', '골목 틈에서 뿌리 굴로 비집고 들어옴(왼쪽 아래)', '나무 속 빈 곳: 카메라 쪽 반은 그루터기뿐(잘린 면 = 덜 그려진 반)',
                  '안쪽 벽: 뿌리 선반의 숨긴 사람 물건(원래 색), 두 아이와 빛구멍 낙서(Face_hideout), 줄에 매단 열쇠·숟가락·책장',
                  '왼쪽: 종이 둥지 + 초록 사람 천 + 등불', '# 빛', '옹이구멍 빛줄기와 등불 — 낙하터 다음으로 유일하게 따뜻한 곳 (Moods에 a_hideout 칸 추가 필요)'],
    'a_cart': ['# 읽는 법', '광장 종 누각 옆 계단으로 내려온 아래층 마당', '오른쪽 창고: 앞이 열린 나무 창고, 남쪽 벽·북쪽 벽 뒤 1/3·지붕 남쪽은 선뿐',
               '창고 안 자루마다 거둔 사람 물건(책 색만 튐), 앞 기둥 고리에 주인공 가방(Satchel_cart)', '마당 가운데 바칠 수레(놋쇠 고정쇠 = 북쪽) · 분류 탁자 · 수거꾼 실루엣',
               '동쪽 끝: 수레 길이 다음 쪽으로 — 길 너머 밭과 검은 웅덩이가 보임', '# 빛', '빠지고 어두움(ambient 0.64 · key 0.22 · drain 0.6). 창고 입구 등 하나'],
    'a_field': ['# 읽는 법', '모든 밭고랑(어두운 흙 띠)이 먹물 웅덩이를 향해 모임 = 행렬의 방향', '수레 길(서)·골목 계단(북) 두 길이 만나 웅덩이 앞 계단으로',
                '웅덩이 둘레 = 빈 무대(반지름 6.1~8.5), 서쪽 반원에 주민 줄 자리, 북서 둑에 뱉어진 덩어리 자리', '들어가는 문 기둥 둘은 55%만 쌓고 위는 선, 아치는 먹 선뿐',
                '덜 지은 망루·연필 동전 나무·연필 새싹', '# 빛', '가장 어두움(ambient 0.6 · key 0.2 · drain 0.62). 따뜻한 빛 없음, 웅덩이 = 검은 먹'],
}
NOTES_POLISH = {
    'a_plaza': ['# 다듬기(10/23 밤)', '시작 화면: 피벗 서쪽 끝 -9.5, 길목 계단은 실물 두 단만(나머지 연필) → 무대가 화면 가운데',
                '죽 가게(z_porridge): 반쯤 지은 천막(기둥 둘·지붕 한 면), 화덕 위 솥·국자·그릇, 연필 김 — 카운터가 손님·카메라를 봄'],
    'a_alley': ['# 다듬기', '이웃 창(z_alley_window 3m 앞): 골목 쪽 벽·창턱·덧문 하나만 실물, 안에 켜진 등 → 창이 밝게 읽힘'],
    'a_cart': ['# 다듬기', '뚜껑 없는 통(z_depot_barrel): 카메라 쪽 통널만 실물, 뒤는 연필 — 키노피오가 올라가 춤춤(첫 장)'],
    'a_field': ['# 다듬기', '밭고랑: 흔들리고 끊기고 일부 연필, 흙은 찢긴 조각(일부는 연필 윤곽만), 수레 바퀴 자국 세 갈래가 계단으로',
                '밭둑 + 코 가는 돌(z_field_stone, 둑 뒤) · 웅덩이 둘레 두 줄 16자리(z_pond_lineup), 문 기둥은 벌리고 낮춤'],
}
TITLES = {'a_plaza': '꼭두 광장 (a_plaza)', 'a_alley': '삐걱의자 골목 (a_alley)', 'a_hideout': '키노피오의 비밀 굴 (a_hideout, 새 구역)',
          'a_cart': '수레 길 · 수거꾼 창고 (a_cart)', 'a_field': '기적의 밭 · 먹물 웅덩이 (a_field)'}


def label_of(name):
    p = os.path.join(RAW, name[:-4] + '.json')
    return json.load(open(p, encoding='utf-8')) if os.path.exists(p) else {}


def sheet(aid, cw=1280, tag='', suffix=''):
    files = [f'{aid}_{i}{tag}.png' for i in range(4) if os.path.exists(os.path.join(RAW, f'{aid}_{i}{tag}.png'))]
    notes = NOTES[aid] + (NOTES_POLISH.get(aid, []) if tag else [])
    cols = 2
    ch = cw * 9 // 16
    rows = (len(files) + 1 + 1) // 2
    W = 60 * 2 + cols * cw + (cols - 1) * 30
    H = 210 + rows * (ch + 80) + 40
    img = Image.new('RGB', (W, H), PAPER)
    d = ImageDraw.Draw(img)
    cam = AREAS[aid]['camera']
    d.text((60, 46), f'{TITLES[aid]} — 게임 카메라 그대로', fill=INK, font=font(56, True))
    d.text((62, 122), f"yaw {cam['yaw']} · pitch {cam['pitch']} · 거리 {cam['distance']} · fov {cam['fov']} · 피벗 = 주인공 발(+0.6m), bounds 안쪽 4m로 묶음 · "
                      f"게임 셰이더 흉내: 색 × (둘레빛 + 주광 + 등불) 뒤 색 빼기(drain) · Blender 미리보기", fill=GREY, font=font(24))
    d.line((60, 176, W - 60, 176), fill=ACC, width=3)
    cells = files + ['__notes__']
    for i, f in enumerate(cells):
        x = 60 + (i % cols) * (cw + 30)
        y = 210 + (i // cols) * (ch + 80)
        if f == '__notes__':
            yy = y + 10
            for ln in notes:
                big = ln.startswith('#')
                d.text((x + 10, yy), ln.lstrip('# '), fill=INK if big else (70, 66, 60), font=font(30 if big else 24, big))
                yy += 46 if big else 38
            continue
        im = Image.open(os.path.join(RAW, f)).convert('RGB').resize((cw, ch), Image.LANCZOS)
        img.paste(im, (x, y))
        d.rectangle((x, y, x + cw - 1, y + ch - 1), outline=(120, 116, 108), width=1)
        d.text((x + 4, y + ch + 14), label_of(f).get('label', f), fill=INK, font=font(28, True))
    out = f'18_구역_{aid}{suffix}.png'
    img.save(os.path.join(OUT, out))
    print('OK', out)


def vista_sheet(aid, pairs, out):
    """before (slice 1 vista = old cheap plaza) / after (new plaza vista) from the slice-1 game camera."""
    raw1 = os.path.join(ART, 'renders', 'raw')
    cw = 1280
    ch = cw * 9 // 16
    W = 60 * 2 + 2 * cw + 30
    H = 210 + len(pairs) * (ch + 80) + 40
    img = Image.new('RGB', (W, H), PAPER)
    d = ImageDraw.Draw(img)
    d.text((60, 46), f'{aid} — 멀리 보이는 광장을 새 광장으로 (왼쪽 전 / 오른쪽 후)', fill=INK, font=font(56, True))
    d.text((62, 122), '1차 슬라이스 미리보기 그대로(slice_scene.py, 게임 카메라) · Vista 속 광장만 바꿈: 극장 틀·종 누각·칠한 탑·그림판 틀·가게', fill=GREY, font=font(26))
    d.line((60, 176, W - 60, 176), fill=ACC, width=3)
    for r, (a, b) in enumerate(pairs):
        for c, f in enumerate((a, b)):
            x = 60 + c * (cw + 30)
            y = 210 + r * (ch + 80)
            img.paste(Image.open(os.path.join(raw1, f)).convert('RGB').resize((cw, ch), Image.LANCZOS), (x, y))
            d.rectangle((x, y, x + cw - 1, y + ch - 1), outline=(120, 116, 108), width=1)
            d.text((x + 4, y + ch + 14), ('전 · ' if c == 0 else '후 · ') + f, fill=INK, font=font(26, True))
    img.save(os.path.join(OUT, out))
    print('OK', out)


if __name__ == '__main__':
    if 'vista' in sys.argv:
        vista_sheet('a_fall', [('slice_a_fall_0.png', 'slice_a_fall_0_v2.png'), ('slice_a_fall_2.png', 'slice_a_fall_2_v2.png')], '18_구역_a_fall_2.png')
        vista_sheet('a_gate', [('slice_a_gate_0.png', 'slice_a_gate_0_v2.png'), ('slice_a_gate_2.png', 'slice_a_gate_2_v2.png')], '18_구역_a_gate_2.png')
        sys.exit(0)
    args = [a for a in sys.argv[1:] if '=' not in a]
    kw = dict(a.split('=', 1) for a in sys.argv[1:] if '=' in a)
    for a in (args or ['a_plaza', 'a_alley', 'a_hideout', 'a_cart', 'a_field']):
        sheet(a, tag=kw.get('tag', ''), suffix=kw.get('suffix', ''))
