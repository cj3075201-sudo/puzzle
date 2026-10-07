from pathlib import Path
from datetime import datetime
from collections import Counter
import json, gzip, shutil, hashlib
root=Path(__file__).resolve().parent
source=Path('/tmp/grad-core24-20260930')
rows=[json.loads(s) for s in (source/'actions.jsonl').read_text().splitlines() if s.strip()]
(root/'actions.jsonl').write_text('\n'.join(json.dumps(r,ensure_ascii=False) for r in rows)+'\n')
measured=[]
with gzip.open(root/'전체_UI기록.jsonl.gz','wt',encoding='utf8') as out:
 for r in rows:
  evidence=Path(r['screenshot']).with_suffix('.json')
  state=json.loads(evidence.read_text()) if evidence.exists() else None
  out.write(json.dumps({'action':r,'rendered':state},ensure_ascii=False)+'\n')
for case in ['11','12']:
 run=[r for r in rows if r['request']['agent']=='c' and r['case']==case]
 if not run: continue
 first=run[0]; last=run[-1]; success=None; submits=[]; failures=[]; hint_clicks=[]
 for r in run:
  p=Path(r['screenshot']).with_suffix('.json')
  state=json.loads(p.read_text()) if p.exists() else {}
  text=state.get('text','')
  if success is None and ('책을 마른 채로 선착장에 내려놓았다' in text or '기록을 진료소에 전달했다' in text or '완료 ·' in text or '책이 도착했다' in text or '두 화물을 모두 올바른 수령구에 보냈습니다' in text): success=r
  req=r['request']
  if req['action']=='click':
   # The clicked control is identified from the *prior* observation.
   prev=[z for z in run if z['step']<r['step']]
   if prev:
    q=Path(prev[-1]['screenshot']).with_suffix('.json')
    obs=json.loads(q.read_text()) if q.exists() else {}
    matches=[c for c in obs.get('controls',[]) if c.get('tag')=='button' and c.get('rect',{}).get('x',1e9)<=req['x']<=c.get('rect',{}).get('x',-1e9)+c.get('rect',{}).get('width',0) and c.get('rect',{}).get('y',1e9)<=req['y']<=c.get('rect',{}).get('y',-1e9)+c.get('rect',{}).get('height',0)]
    labels=[c.get('text','') for c in matches]
    if any(s in ['부탁하기','말하기','말해 보기'] for s in labels): submits.append({'at':r['at'],'step':r['step'],'text':text})
    if any('막혔을 때' in s for s in labels): hint_clicks.append(r['step'])
 end=success or last
 seconds=(datetime.fromisoformat(end['at'].replace('Z','+00:00'))-datetime.fromisoformat(first['at'].replace('Z','+00:00'))).total_seconds()
 counts=Counter(r['request']['action'] for r in run if r['step']<=end['step'])
 measured.append({'case':case,'first':first['at'],'end':end['at'],'success_step':success['step'] if success else None,'seconds':round(seconds,3),'actions':dict(counts),'submissions':submits,'hint_clicks':hint_clicks,'note':'시간은 가설 메모·조작·도구 지연 포함. 성공문구는 최종 화면과 대조해 검산.'})
 notes=source/f'notes-c-{case}.md'
 if notes.exists(): shutil.copy2(notes,root/f'초견_C_{case}.md')
 # Keep all rendered observations; preserve milestone PNGs separately without overwriting source.
 dest=root/'evidence'/'c'/case;dest.mkdir(parents=True,exist_ok=True)
 candidates={1,last['step']}
 if success:candidates.add(success['step'])
 candidates.update(z['step'] for z in submits)
 for n in sorted(candidates):
  for suffix in ['.png','.json']:
   p=source/'evidence'/'c'/case/(f'{n:03d}'+suffix)
   if p.exists():shutil.copy2(p,dest/p.name)
(root/'UI측정.json').write_text(json.dumps(measured,ensure_ascii=False,indent=2))
print(json.dumps([{k:v for k,v in m.items() if k!='submissions'} for m in measured],ensure_ascii=False,indent=2))
