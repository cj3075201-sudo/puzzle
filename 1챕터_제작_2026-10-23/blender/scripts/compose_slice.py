# Slice-1 sheets (python3 + PIL): art/renders/15_슬라이스_빛구멍언덕.png, 15_슬라이스_앉은돌길목.png, 15_슬라이스_배치도.png
# Renders are shown as rendered (no grading, no grain on the frames); only titles/labels are added.
import os, json, sys
from PIL import Image, ImageDraw
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from compose_previews import font, PAPER, INK, GREY

ART = os.path.dirname(HERE)
RAW = os.path.join(ART, 'renders', 'raw')
OUT = os.path.join(ART, 'renders')
ACC = (184, 134, 62)


def label_of(name):
    p = os.path.join(RAW, name[:-4] + '.json')
    return json.load(open(p, encoding='utf-8')) if os.path.exists(p) else {}


def sheet(files, out, title, sub, notes, cols=2, cw=1280):
    ch = cw * 9 // 16
    rows = (len(files) + (1 if notes else 0) + cols - 1) // cols
    W = 60 * 2 + cols * cw + (cols - 1) * 30
    H = 210 + rows * (ch + 80) + 40
    img = Image.new('RGB', (W, H), PAPER)
    d = ImageDraw.Draw(img)
    d.text((60, 46), title, fill=INK, font=font(56, True))
    d.text((62, 122), sub, fill=GREY, font=font(26))
    d.line((60, 176, W - 60, 176), fill=ACC, width=3)
    cells = list(files) + (['__notes__'] if notes else [])
    for i, f in enumerate(cells):
        x = 60 + (i % cols) * (cw + 30)
        y = 210 + (i // cols) * (ch + 80)
        if f == '__notes__':
            yy = y + 10
            for ln in notes:
                big = ln.startswith('#')
                d.text((x + 10, yy), ln.lstrip('# '), fill=INK if big else (70, 66, 60), font=font(30 if big else 24, big))
                yy += 46 if big else 36
            continue
        im = Image.open(os.path.join(RAW, f)).convert('RGB').resize((cw, ch), Image.LANCZOS)
        img.paste(im, (x, y))
        d.rectangle((x, y, x + cw - 1, y + ch - 1), outline=(120, 116, 108), width=1)
        lab = label_of(f).get('label', f)
        d.text((x + 4, y + ch + 14), lab, fill=INK, font=font(28, True))
    img.save(os.path.join(OUT, out))
    print('OK', out)


def topmap():
    meta = json.load(open(os.path.join(RAW, 'slice_top.json'), encoding='utf-8'))
    im = Image.open(os.path.join(RAW, 'slice_top.png')).convert('RGB')
    w, h = im.size
    W, H = w + 120, h + 260
    img = Image.new('RGB', (W, H), PAPER)
    img.paste(im, (60, 200))
    d = ImageDraw.Draw(img)
    d.text((60, 46), '1차 슬라이스 배치도 — 빛구멍 언덕 · 앉은돌 길목 (위에서)', fill=INK, font=font(56, True))
    d.text((62, 122), 'Unity 월드 x→오른쪽, z→위 · 5m 격자 · 점 = art/layout_slice1.json 위치 · 노란 테두리 = 카메라 피벗(플레이어) 따라가기 범위 · 빨강 = 출구',
           fill=GREY, font=font(24))
    ox, oy = 60, 200
    for g in meta['grid']:
        (ax, ay), (bx, by) = g['a'], g['b']
        d.line((ox + ax * w, oy + ay * h, ox + bx * w, oy + by * h), fill=(150, 150, 150), width=1)
        tx, ty = (ox + ax * w + 4, oy + h - 26) if g['axis'] == 'x' else (ox + 4, oy + ay * h - 22)
        d.text((tx, ty), f"{g['axis']}{g['v']}", fill=(90, 90, 90), font=font(18))
    names = {'z_hero_start': '주인공 시작', 'z_kid_pile': '키노피오(더미 뒤)', 'z_fall_gap': '틈(작은 몸만)', 'z_ladder': '사다리 걸쇠',
             'z_fall_bolt': '그려진 빗장', 'kid_wait_below': '키노피오 기다림', 'kid_cleft_exit': '틈 아래', 'fall_pile': '물건 더미·빛',
             'look_book': '책', 'look_umbrella': '우산', 'look_clock': '시계', 'z_gate_stone': '새김 돌', 'z_chief_gate': '촌장',
             'gate_a': '주민 A(앉음)', 'gate_b': '주민 B(앉음)', 'crowd_gate': '실루엣 4(앉음)', 'kid_greet': '인사 자리'}
    skip = {'light_beam', 'ladder', 'bolt_fall', 'pz_ladder', 'gate_stone', 'ins_gate', 'chief'}
    for it in meta['items']:
        if it['kind'] == 'pivot':
            pts = [(ox + x * w, oy + y * h) for x, y in it['poly']]
            d.polygon(pts, outline=(214, 170, 40), width=3)
            continue
        if it['id'] in skip:
            continue
        x, y = ox + it['x'] * w, oy + it['y'] * h
        col = (190, 50, 40) if it['kind'] == 'exit' else ((150, 100, 30) if it['kind'] == 'ladder' else (40, 70, 160))
        r = 9
        d.ellipse((x - r, y - r, x + r, y + r), fill=col, outline=(255, 255, 255), width=2)
        txt = names.get(it['id'], it['id'])
        d.text((x + 12, y - 14), txt, fill=col, font=font(22, True))
    img.save(os.path.join(OUT, '15_슬라이스_배치도.png'))
    print('OK topmap')


if __name__ == '__main__':
    sys.path.insert(0, HERE)
    cf = {'yaw': 100, 'pitch': 22, 'distance': 12.0, 'fov': 34}
    cg = {'yaw': 96, 'pitch': 24, 'distance': 12.0, 'fov': 34}
    sheet(['slice_a_fall_0.png', 'slice_a_fall_1.png', 'slice_a_fall_2.png', 'slice_a_fall_3.png'], '15_슬라이스_빛구멍언덕.png',
          '빛구멍 언덕 (a_fall) — 게임 카메라 그대로',
          f"yaw {cf['yaw']} · pitch {cf['pitch']} · 거리 {cf['distance']} · fov {cf['fov']} · 피벗 = 주인공 발(+0.6m), bounds 안쪽 4m로 묶음 · 16:9 · Blender 미리보기(툰·잉크·빗금), Unity 셰이더와 같지 않음",
          None)
    sheet(['slice_a_gate_0.png', 'slice_a_gate_1.png', 'slice_a_gate_2.png'], '15_슬라이스_앉은돌길목.png',
          '앉은돌 길목 (a_gate) — 게임 카메라 그대로',
          f"yaw {cg['yaw']} · pitch {cg['pitch']} · 거리 {cg['distance']} · fov {cg['fov']} · 다리 → 좁은 돌 길목 → 문(촌장) 너머 광장 · 오른쪽 바위 틈 계단 = 수레 길",
          ['# 읽는 법', '언덕에서 넘어오면 다리 위(시작) — 다리 난간이 길목 안으로 끌고 감',
           '왼쪽 벽: 짓다 만 집 · 새김 돌 · 앉아 굳은 실루엣', '오른쪽: 길가에 앉은 주민 둘 · 바위 틈 내리막 = 수레 길(파란 깃발)',
           '끝: 덜 쌓은 문 기둥 둘 + 선으로만 그린 아치, 촌장이 섬', '문 너머 아래: 칠해진 무대·광장(다음 쪽)',
           '# 빛', '길목은 어둑한 회색, 따뜻한 빛은 문 기둥 등 하나 + 광장 무대뿐'])
    topmap()
