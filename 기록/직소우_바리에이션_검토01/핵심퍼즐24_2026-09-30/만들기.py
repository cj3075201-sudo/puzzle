from pathlib import Path
import json, html
root=Path(__file__).resolve().parent
data=json.loads((root/'분석/결과.json').read_text()) if (root/'분석/결과.json').exists() else {"summary":"제작과 시험을 진행하고 있습니다.","puzzles":[]}
esc=html.escape
cards=""
for n in data.get("puzzles",[]):
 cards+=f'<article class="card"><span class="number">{esc(n["code"])}</span><h2>{esc(n["title"])}</h2><p>{esc(n["intro"])}</p><a class="play" href="{esc(n["href"])}">이 사건 플레이 ↗</a></article>'
results=""
for n in data.get("puzzles",[]):
 facts="".join(f'<li>{esc(f)}</li>' for f in n.get("facts",[]))
 results+=f'<article class="result"><span class="number">{esc(n["code"])}</span><h2>{esc(n["title"])}</h2><p>{esc(n.get("judgment","시험 중"))}</p><ul>{facts}</ul><details><summary>풀이와 상세 분석 · 스포일러</summary><p>{esc(n.get("solution",""))}</p><a href="{esc(n.get("report","분석/종합보고.md"))}">관찰 기록 열기 ↗</a></details></article>'
page=(root/'보기.template.html').read_text().replace('__CARDS__',cards).replace('__RESULTS__',results).replace('__SUMMARY__',esc(data.get("summary","")))
(root/'플레이와_검토.html').write_text(page)
print('플레이와_검토.html 생성')
