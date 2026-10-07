"""09의 주다 배치와 08의 실제 외곽 생성 함수를 재사용하는 설명 자료."""
from pathlib import Path
import ast,sys,json,io,base64,copy

OUT=Path(__file__).resolve().parent
source=OUT/'연결확장08/만들기.py'
tree=ast.parse(source.read_text())
names={'shape','part','transfer','check','svg'}
constants={'NORMAL','MID','OPP','COLORS'}
nodes=[n for n in tree.body if isinstance(n,(ast.Import,ast.ImportFrom)) or isinstance(n,ast.FunctionDef) and n.name in names or isinstance(n,ast.Assign) and any(isinstance(t,ast.Name) and t.id in constants for t in n.targets)]
ns={};exec(compile(ast.Module(body=nodes,type_ignores=[]),str(source),'exec'),ns)
part=ns['part'];transfer=ns['transfer'];check=ns['check'];svg=ns['svg']
base=transfer('주민','나','열쇠','주다')
boards={}
for which in ['A','B']:
    ps=copy.deepcopy(base)
    for p in ps:p['y']+=2
    target=ps[0] if which=='A' else ps[3]
    target['ports'].append(('N','socket','round'))
    x,y=target['x'],target['y']
    ps.extend([part('house','yellow',x,y-2,'집',[('S','tab','round')]),part('inside','yellow',x,y-1,'안',[('N','socket','round'),('S','tab','round')])])
    boards[which]=ps
checks={k:check(v) for k,v in boards.items()}
for k,ps in boards.items():
    assert len(ps)==6 and sorted(p['label'] for p in ps)==sorted(['집','안','주민','나','주다','열쇠'])
    for old,p in zip(base,ps):
        assert p['x']==old['x'] and p['y']==old['y']+2
        assert all(port in p['ports'] for port in old['ports'])
    assert len(checks[k]['connections'])==5
checks['scope']='기존 원형/두 갈래 생성 함수와 주다 배치 재사용. A 주민/B 열쇠에 위쪽 원형 홈을 갖춘 외곽을 사용. 동일 여섯 외곽 세트의 재배치나 게임 채택을 뜻하지 않음.'
(OUT/'판단비교11_접합확인.json').write_text(json.dumps(checks,ensure_ascii=False,indent=2))
style='''*{box-sizing:border-box}body{margin:0;background:#f4f1e7;color:#243e48;font-family:P,"Malgun Gothic",sans-serif;line-height:1.55}main{max-width:1220px;margin:auto;padding:26px 32px}.intro{display:flex;justify-content:space-between;gap:28px;align-items:center}.intro p{margin:8px 0;font-size:18px}h1{font-size:29px;margin:0 0 10px}h2{font-size:22px;margin:0}.eyebrow{font-size:12px;color:#69838b;margin-bottom:10px}.base{width:260px;flex-shrink:0;text-align:center;font-size:13px;color:#657980}.base svg{width:240px;display:block;margin:auto}.grid{display:grid;grid-template-columns:1fr 1fr;gap:24px;margin-top:20px}.card{background:#fffdf6;border:1px solid #d9d7ca;border-radius:12px;padding:20px}.card header p{margin:3px 0;color:#6a7878}.card svg{width:100%;height:405px;display:block}svg text{font-family:inherit;fill:#26414c}.result{border-top:1px solid #ddd9ca;margin:12px 0 0;padding:14px 0 0;font-size:20px}.result b{color:#795616;background:#f7e7b0;padding:2px 4px}.result small{display:block;color:#6d7b7d;font-size:14px;margin-top:8px}.legend{font-size:16px;margin:18px 0 0}.legend strong{color:#87641b}details{margin-top:18px;font-size:13px;color:#6a7878}summary{cursor:pointer}details p{max-width:1000px}@media(max-width:750px){main{padding:22px 15px}.intro{display:block}.base{margin:15px auto}.grid{grid-template-columns:1fr}.card svg{height:350px}h1{font-size:25px}}'''
html='''<!doctype html><html lang="ko"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>직소우 비교 11 · 기존 조각으로 보는 두 연결</title><style>__FONT__'''+style+'''</style></head><body><main><section class="intro"><div><div class="eyebrow">직소우 비교 11 · 연결 비교 후보</div><h1>같은 여섯 글자, 붙는 대상이 다르다</h1><p><b>왼쪽은 집 안의 주민. 오른쪽은 집 안의 열쇠.</b><br>‘집’부터 홈과 돌출부를 따라 읽어 봐.</p></div><aside class="base">기존 ‘주다’ 배치 그대로'''+svg(base,300,215)+'''</aside></section><section class="grid">'''
for which in ['A','B']:
    a=which=='A'
    title='A · 집 → 안 → 주민' if a else 'B · 집 → 안 → 열쇠'
    sub='집·안이 주민 위에 붙는다.' if a else '집·안이 열쇠 위에 붙는다.'
    result='<b>집 안의 주민</b>이 나에게 열쇠를 준다.' if a else '주민이 나에게 <b>집 안의 열쇠</b>를 준다.'
    note='열쇠의 위치는 이 문장에 나오지 않는다.' if a else '주민의 위치는 이 문장에 나오지 않는다.'
    html+=f'<article class="card"><header><h2>{title}</h2><p>{sub}</p></header>'+svg(boards[which],460,450)+f'<p class="result">{result}<small>{note}</small></p></article>'
html+='''</section><p class="legend"><strong>노랑 = 뜻 조각</strong> · 파랑 = 행동 조각 · 주민 아래의 <b>두 갈래 접합 = 주는 주체 표시</b></p><details><summary>모형과 비교 범위</summary><p>09번의 주민·나 입력 / 열쇠 출력 배치와 기존 원형·두 갈래 외곽 생성 함수를 재사용했다. A의 주민, B의 열쇠에는 ‘안’을 받는 위쪽 원형 홈이 필요하다. 같은 여섯 글자의 비교이며, 동일한 여섯 외곽 모형을 옮기기만 한 비교는 아니다. 조각은 각각 따로 선택하는 낱개이며 집·안을 한 묶음으로 이동하는 기능을 뜻하지 않는다.</p><p>현재 의미 비교 후보를 실제 맞물리는 형태로 나타낸 것이다. 새로운 게임 규칙이나 본편 구현을 확정한 자료가 아니다.</p></details></main></body></html>'''
from fontTools import subset
from fontTools.ttLib import TTFont
font=TTFont(str(OUT.parents[1]/'기획서/source/assets/Pretendard-Regular.ttf'))
sub=subset.Subsetter();sub.populate(text=html);sub.subset(font)
b=io.BytesIO();font.save(b)
fontcss='@font-face{font-family:P;src:url(data:font/ttf;base64,'+base64.b64encode(b.getvalue()).decode()+')}'
(OUT/'판단비교11_구조도.html').write_text(html.replace('__FONT__',fontcss))
print(json.dumps(checks,ensure_ascii=False))
