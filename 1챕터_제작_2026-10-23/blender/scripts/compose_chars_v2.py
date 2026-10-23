# Compose round-4 character contact sheets (python3, PIL).  usage: python3 compose_chars_v2.py Name [title] [rows_per_page]
import sys, os, json
from PIL import Image, ImageDraw, ImageFont

HERE = os.path.dirname(os.path.abspath(__file__))
ART = os.path.dirname(HERE)
NAME = sys.argv[1]
TITLE = sys.argv[2] if len(sys.argv) > 2 else NAME
RPP = int(sys.argv[3]) if len(sys.argv) > 3 else 7
TAG = sys.argv[4] if len(sys.argv) > 4 else ''          # e.g. _r6 -> raw/chars_v2/<Name>_r6, sheets 20_캐릭터_추가_<Name>_n.png
RAW = os.path.join(ART, 'renders', 'raw', 'chars_v2', NAME + TAG)
REP = json.load(open(os.path.join(ART, 'blend', 'chars_v2', 'report.json'), encoding='utf-8'))[NAME]
cells = json.load(open(os.path.join(RAW, 'cells.json'), encoding='utf-8'))['cells']
VER = json.load(open(os.path.join(RAW, 'verify.json'), encoding='utf-8'))
INK, GREY, BG = (43, 38, 34), (110, 106, 100), (236, 233, 226)
KO = {'Idle': '서 있기', 'Walk': '걷기', 'Run': '달리기', 'Talk': '말하기', 'Bow': '엎드리기', 'BowHold': '엎드린 채', 'Rise': '일어나기',
      'Point': '가리키기', 'PointUp': '위 가리키기', 'LookUp': '올려다보기', 'Beckon': '이리 와', 'LookBack': '뒤돌아보기', 'Nod': '끄덕',
      'HeadTilt': '갸웃', 'Reach': '손 뻗다 거두기', 'Gather': '줍기', 'SitIdle': '앉아 있기', 'Cower': '움츠리기', 'Push': '밀기',
      'FallTumble': '떨어지며 구르기', 'LieDown': '엎어져 누움', 'GetUp': '일어서기', 'LookAround': '둘러보기', 'Kneel': '한쪽 무릎',
      'Greet': '큰 절', 'StandSway': '흔들리며 서기',
      'FileNose': '돌에 코 갈기', 'HideNose': '코 가리기', 'Grin': '"믿어 봐"', 'ShoutWord': '외쳐 알리기', 'RunAway': '겁먹고 도망',
      'Sulk': '웅크려 삐침', 'Cry': '울기', 'TugSleeve': '소매 당기기', 'PointSelf': '나(가슴 짚기)', 'PointOther': '너(앞 가리키기)',
      'TieCord': '끈 매어 주기', 'Proclaim': '선포', 'Squeeze': '틈 비집기', 'Carry': '들고 걷기', 'Startle': '깜짝 물러섬',
      'Offer': '먹을 것 바치기', 'Crowd': '들떠 몰려듦', 'Recoil': '움츠려 물러남', 'Grab': '집어 올려 지게에'}


def font(size, bold=False):
    for p in (('/mnt/c/Windows/Fonts/malgunbd.ttf' if bold else '/mnt/c/Windows/Fonts/malgun.ttf'),):
        if os.path.exists(p):
            return ImageFont.truetype(p, size)
    return ImageFont.load_default()


rows = []
turn = [c for c in cells if c[0] == 'turn']
if turn:
    rows.append(('돌려보기', '앞, 3/4, 옆, 뒤3/4, 뒤 = 빛 웅덩이 안|3/4, 게임 크기(1080p) = 빛 밖 어둠', turn))
clipinfo = {c['clip']: c for c in REP['clips']}
order = [c['clip'] for c in REP['clips']]
for clip in order:
    cs = [c for c in cells if c[0] == clip]
    if not cs:
        continue
    ci = clipinfo[clip]
    sp = REP.get('speeds', {}).get(clip)
    sub = f"{ci['frames']}f · {ci['seconds']}s · {'반복' if ci['loop'] else '1회'}" + (f" · {sp} m/s" if sp else '')
    if clip in VER.get('slip', {}):
        sub += f" · 미끄럼 {VER['slip'][clip]['max_slip_cm_per_frame']}cm/f"
    rows.append((f"{clip}  {KO.get(clip, '')}", sub, cs))

CW, CH_, LW = 300, 340, 230
ncol = max(len(r[2]) for r in rows)
pages = [rows[i:i + RPP] for i in range(0, len(rows), RPP)]
outs = []
for pi, pg in enumerate(pages):
    W = LW + ncol * CW + 40
    Hh = 150 + len(pg) * (CH_ + 16) + 30
    im = Image.new('RGB', (W, Hh), BG)
    d = ImageDraw.Draw(im)
    d.text((40, 28), f"{TITLE}  ({pi + 1}/{len(pages)})", font=font(44, True), fill=INK)
    d.text((40, 90), f"게임 카메라 각도(내려보기 25° · 10m · 화각 32°)를 잘라 확대 · 어두운 지하 조명 + 따뜻한 빛 웅덩이 · {REP['tris']} tri · 뼈 {len(REP['bones'])}개 · 30fps",
           font=font(22), fill=GREY)
    y = 150
    for title, sub, cs in pg:
        d.text((40, y + 20), title, font=font(26, True), fill=INK)
        yy = y + 62
        for line in sub.replace('|', ' · ').split(' · '):
            d.text((40, yy), line, font=font(19), fill=GREY)
            yy += 26
        for k, c in enumerate(cs):
            try:
                pth = c[3].replace('\\', '/')
                if len(pth) > 1 and pth[1] == ':':
                    pth = '/mnt/' + pth[0].lower() + pth[2:]
                c_im = Image.open(pth).convert('RGB')
            except Exception:
                continue
            x = LW + k * CW
            im.paste(c_im, (x, y))
            lab = f"f{c[2]}" if c[0] != 'turn' else ('게임 크기' if c[1] == 'game' else '')
            if lab:
                d.text((x + 8, y + 6), lab, font=font(18), fill=(250, 248, 240))
        y += CH_ + 16
    out = os.path.join(ART, 'renders', (f'20_캐릭터_추가_{NAME}_{pi + 1}.png' if TAG else f'16_캐릭터_{NAME}_{pi + 1}.png'))
    im.save(out)
    outs.append(out)
print('\n'.join(outs))
