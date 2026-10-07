from pathlib import Path
from datetime import datetime
import json, gzip

ROOT = Path(__file__).resolve().parent
ARCHIVED = None
LOG = [json.loads(x) for x in (ROOT/'actions.jsonl').read_text().splitlines()]

def timestamp(s):
    return datetime.fromisoformat(s.replace('Z','+00:00')).timestamp()

def frame(participant, case, step):
    global ARCHIVED
    file = ROOT/f'evidence/{participant}/{case}/{step:03}.json'
    if file.exists():
        return json.loads(file.read_text())
    if ARCHIVED is None:
        with gzip.open(ROOT/'전체_UI기록.jsonl.gz', 'rt', encoding='utf-8') as f:
            rows = [json.loads(line) for line in f]
        ARCHIVED = {(r['action']['request']['agent'], r['action']['case'], r['action']['step']): r['ui'] for r in rows}
    return ARCHIVED[(participant, case, step)]

def button_clicked(row):
    req=row['request']
    if req['action']!='click' or row['step']<2:
        return None
    before=frame(req['agent'],row['case'],row['step']-1)
    options=[]
    for c in before['controls']:
        r=c['rect']
        if c['tag']=='button' and not c.get('disabled') and r['x']<=req['x']<=r['x']+r['width'] and r['y']<=req['y']<=r['y']+r['height']:
            options.append(c)
    return min(options,key=lambda c:c['rect']['width']*c['rect']['height'])['text'] if options else None

def measure(participant, case, start, end, first_submit=None, marker=None):
    rr=[r for r in LOG if r['request']['agent']==participant and r['case']==case and start<=r['step']<=end]
    if len({r['step'] for r in rr})!=len(rr):
        raise ValueError('duplicate case/step; inspect overwritten evidence before analysis')
    assert rr and rr[0]['step']==start and rr[-1]['step']==end
    if marker:
        hits=[r for r in rr if marker in frame(participant,case,r['step'])['text']]
        if hits:
            end=hits[0]['step']
            rr=[r for r in rr if r['step']<=end]
    buttons=[(r,button_clicked(r)) for r in rr]
    submits=[r for r,b in buttons if b and ('말하기'==b or '말해 보기'==b or '찾은 상대에게 부탁하기' in b)]
    hint_clicks=[r['step'] for r,b in buttons if b and b in ('막혔을 때','힌트 더 보기','대표 풀이 보기')]
    first=submits[0] if submits else next((r for r in rr if r['step']==first_submit),None)
    deltas=[(timestamp(b['at'])-timestamp(a['at']),a['step'],b['step']) for a,b in zip(rr,rr[1:])]
    gap=max(deltas,default=(0,start,start))
    return dict(participant=participant,case=case,start_step=start,completion_step=end,start_at=rr[0]['at'],completion_at=rr[-1]['at'],elapsed_seconds=round(timestamp(rr[-1]['at'])-timestamp(rr[0]['at']),3),first_submit_step=first['step'] if first else None,first_submit_seconds=round(timestamp(first['at'])-timestamp(rr[0]['at']),3) if first else None,clicks=sum(r['request']['action']=='click' for r in rr),submits=len(submits),submit_steps=[r['step'] for r in submits],hint_steps=hint_clicks,scrolls=sum(r['request']['action']=='scroll' for r in rr),ui_records=len(rr),longest_gap_seconds=round(gap[0],3),longest_gap_steps=list(gap[1:]),evidence=f'분석/evidence/{participant}/{case}/{end:03}.png')

if __name__=='__main__':
    p=ROOT/'report-c-baseline.json'
    report=json.loads(p.read_text())
    output=[]
    for s in report['scenes']:
        marker={'01':'책과 열쇠를 서로 바꿔 건넸습니다.','02':'서로 뜻이 닿았다','03':'대화 완료'}[s['case']]
        result=measure('c',s['case'],s['start_step'],s['completion_step'],s['first_submit_step'],marker)
        result['title']=s['scene'];output.append(result)
    target=Path(__file__).resolve().parent/'기준측정.json'
    target.write_text(json.dumps(output,ensure_ascii=False,indent=2))
    print(json.dumps(output,ensure_ascii=False,indent=2))
