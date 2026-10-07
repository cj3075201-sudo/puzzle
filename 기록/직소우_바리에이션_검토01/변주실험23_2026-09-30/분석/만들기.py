from pathlib import Path
import html, json

root = Path(__file__).resolve().parent.parent
data = json.loads((root / '분석/종합.json').read_text())
esc = lambda s: html.escape(str(s))

def duration(seconds):
    if seconds is None:
        return '—'
    s = round(seconds)
    return f'{s//60}분 {s%60:02d}초' if s >= 60 else f'{s}초'

cards, rows, details = [], [], []
for item in data['samples']:
    sid = item['id']
    link = f'{sid[0]}/플레이.html#p{sid[1]}'
    trials = item['trials']
    cold = next((x for x in trials if x['participant']=='c'), None)
    cross = next((x for x in trials if x['participant']!='c'), None)
    cards.append(f'''<article class="card"><span class="id">{sid}</span><p class="eyebrow">{esc(item['mechanism'])}</p><h2>{esc(item['title'])}</h2><p>{esc(item['pitch'])}</p><a class="play" href="{link}">플레이하기 <span>↗</span></a></article>''')
    rows.append(f'''<tr><td><a href="#detail-{sid}">{sid} · {esc(item['title'])}</a><small>{esc(item['mechanism'])}</small></td><td>{duration(cold['elapsed_seconds']) if cold else '—'}</td><td>{duration(cross['elapsed_seconds']) if cross else '—'}</td><td>{esc(item['verdict'])}</td></tr>''')
    evidence = []
    for t in trials:
        lab = '초견 C' if t['participant']=='c' else '교차 '+t['participant'].upper()
        proof = f'<a href="{esc(t["evidence"])}">완료 화면</a>' if t.get('evidence') else ''
        evidence.append(f'<li><b>{lab}</b> · {duration(t["elapsed_seconds"])} · 클릭 {t["clicks"]} · 제출 {t["submits"]} · 힌트 {esc(t["hint"])} {proof}</li>')
    details.append(f'''<details id="detail-{sid}" class="finding"><summary><b>{sid} · {esc(item['title'])}</b><span>{esc(item['verdict'])}</span></summary><div><p><b>기존과 다른 판단</b><br>{esc(item['difference'])}</p><p><b>실제로 한 행동과 막힌 곳</b><br>{esc(item['observed'])}</p><p><b>판단</b><br>{esc(item['judgment'])}</p><p><b>다음에 바꿀 것</b><br>{esc(item['next'])}</p><ul>{''.join(evidence)}</ul><p class="muted">기존 비교: {esc(item['prior'])}</p><a href="{link}">직접 플레이 ↗</a></div></details>''')

baselines = ''.join(f'<tr><td>{esc(t["title"])}</td><td>{duration(t["elapsed_seconds"])}</td><td>{t["clicks"]}</td><td>{esc(t["note"])}</td></tr>' for t in data['baselines'])
page = '''<!doctype html><html lang="ko"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>여섯 가지 퍼즐 변주 · 플레이와 비교 결과</title><style>
*{box-sizing:border-box}body{margin:0;background:#f3f0e6;color:#203f3b;font:16px/1.75 'Malgun Gothic',system-ui,sans-serif}main{max-width:1200px;margin:auto;padding:55px 30px 90px}a{color:#226858;text-underline-offset:4px}h1{font-size:clamp(32px,4vw,56px);letter-spacing:-2px;line-height:1.2;margin:12px 0 24px}h2{line-height:1.4;letter-spacing:-.5px}p{max-width:880px}.eyebrow{font-size:12px;font-weight:700;letter-spacing:2px;text-transform:uppercase;color:#59756d}.lead{font-size:19px}.tabs{display:flex;gap:10px;margin:30px 0}button,.play{font:inherit;border:1px solid #afc0b6;border-radius:7px;padding:10px 20px;background:transparent;color:inherit;cursor:pointer}button[aria-selected=true],.play{background:#294f45;color:white;border-color:#294f45}.cards{display:grid;grid-template-columns:repeat(3,1fr);gap:20px}.card{background:#fcfaf4;padding:25px;border:1px solid #d2d6c6;border-radius:12px;display:flex;flex-direction:column}.card h2{font-size:23px;margin:3px 0 12px}.card p{margin:6px 0 16px}.card .eyebrow{font-size:11px;letter-spacing:.5px}.id{font-size:30px;font-weight:750;color:#829588}.play{display:flex;justify-content:space-between;margin-top:auto;text-decoration:none}.note{border-left:3px solid #86a89b;padding:12px 20px;background:#e9eee4;margin:30px 0}.muted,small{color:#687e74;font-size:13px}small{display:block}table{border-collapse:collapse;width:100%;background:#fcfaf4;font-size:14px}th,td{text-align:left;border-bottom:1px solid #d2d6c6;padding:15px}th{background:#e3e9dd}td:first-child{min-width:230px}.table-wrap{overflow:auto}.finding{border:1px solid #c7d0bf;border-radius:8px;background:#fcfaf4;margin:15px 0}.finding summary{padding:18px;cursor:pointer;display:flex;justify-content:space-between;gap:20px}.finding summary span{font-size:13px}.finding>div{padding:0 24px 24px}.finding:target{outline:3px solid #9eb39a}.finding p{max-width:950px}.closing{margin-top:45px;padding-top:20px;border-top:1px solid #c7d0bf}section[hidden]{display:none}@media(max-width:900px){.cards{grid-template-columns:repeat(2,1fr)}}@media(max-width:600px){main{padding:30px 16px}.cards{grid-template-columns:1fr}.finding summary{display:block}th,td{padding:10px}h1{letter-spacing:-1px}}
</style><main><p class="eyebrow">DO YOU UNDERSTAND? · 2026.09.30</p><h1>여섯 가지 퍼즐 변주</h1><p class="lead">같은 직소 언어로 다른 판단을 만들 수 있을까?</p><p>규칙, 지칭, 집단, 실험, 믿음, 목적을 각각 바꿔 만든 여섯 표본입니다. 플레이 화면에는 풀이를 숨기고, 비교 결과에는 실제 선택과 막힌 지점을 남겼습니다.</p><nav class="tabs" aria-label="보기 선택"><button data-tab="games" aria-selected="true">먼저 플레이</button><button data-tab="analysis" aria-selected="false">시험 결과 · 풀이 포함</button></nav><section id="games"><div class="cards">__CARDS__</div><div class="note">모형을 놓고 글자를 넣어 조립합니다. 기본 뜻은 한국어로 표시되는 시험판이며, 진행은 각 표본에 따로 저장됩니다. 막히면 화면의 조립 방법과 단계별 힌트를 볼 수 있습니다.</div></section><section id="analysis" hidden><h2>현재 판단</h2><p class="lead">__CONCLUSION__</p><div class="note">__METHOD__</div><div class="table-wrap"><table><thead><tr><th>표본</th><th>초견 C</th><th>교차 검토</th><th>발전시킬 가치</th></tr></thead><tbody>__ROWS__</tbody></table></div><p class="muted">시간: 장면 첫 관측부터 첫 성공 반응까지. AI 추론과 도구 처리를 포함한 실제 경과입니다. 사람 플레이타임이나 순수 사고 시간이 아닙니다. 시간 증가만으로 깊이를 판정하지 않았습니다.</p><h2>무엇이 달랐고, 어디에서 막혔나</h2>__DETAILS__<h2>같은 C 참가자의 기존 퍼즐</h2><div class="table-wrap"><table><thead><tr><th>기준 표본</th><th>경과</th><th>클릭</th><th>관측</th></tr></thead><tbody>__BASELINES__</tbody></table></div><h2>공통으로 드러난 문제</h2>__COMMON__<p class="muted">A 묶음은 시험 후 상황 설명 두 문장만 명확히 했으며, 규칙과 판정은 같습니다. 자세한 차이는 상세 보고서에 보관했습니다.</p><p><a href="분석/종합보고.md">상세 원본 보고서</a> · <a href="분석/종합.json">시간·클릭 수 원본</a> · <a href="시험계획.md">시험 방법</a> · <a href="레퍼런스.md">참고 작품과 차용 범위</a></p></section><div class="closing"><a href="../../../오늘_직소퍼즐_모음.html">기존 퍼즐 전체 모음 ↗</a><p class="muted">독립 HTML 실험입니다. 새 규칙의 본편 채택은 이 시험과 구별합니다.</p></div></main><script>
function tab(id){document.querySelectorAll('main>section').forEach(s=>s.hidden=s.id!==id);document.querySelectorAll('[data-tab]').forEach(b=>b.setAttribute('aria-selected',String(b.dataset.tab===id)));}document.querySelectorAll('[data-tab]').forEach(b=>b.onclick=()=>tab(b.dataset.tab));function target(){if(location.hash.startsWith('#detail-')){tab('analysis');const d=document.querySelector(location.hash);if(d){d.open=true;d.scrollIntoView({block:'start'});}}}addEventListener('hashchange',target);target();
</script></html>'''
for key,value in {'CARDS':''.join(cards),'ROWS':''.join(rows),'DETAILS':''.join(details),'BASELINES':baselines,'CONCLUSION':esc(data['conclusion']),'METHOD':esc(data['method']),'COMMON':''.join(f'<p>{esc(p)}</p>' for p in data['common'])}.items():
    page=page.replace('__'+key+'__',value)
(root/'플레이와_비교결과.html').write_text(page)
print(root/'플레이와_비교결과.html')
