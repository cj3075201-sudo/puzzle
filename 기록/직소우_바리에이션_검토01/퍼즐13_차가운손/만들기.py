"""기존 직소우 다각형·한글 폰트를 단일 HTML 플레이 표본에 포함한다."""
from pathlib import Path
import ast,sys,json,base64,io

OUT=Path(__file__).resolve().parent
source=OUT.parent/'연결확장08/만들기.py';tree=ast.parse(source.read_text())
names={'shape'};const={'NORMAL','MID','OPP'}
nodes=[n for n in tree.body if isinstance(n,(ast.Import,ast.ImportFrom)) or isinstance(n,ast.FunctionDef) and n.name in names or isinstance(n,ast.Assign) and any(isinstance(t,ast.Name) and t.id in const for t in n.targets)]
ns={};exec(compile(ast.Module(body=nodes,type_ignores=[]),str(source),'exec'),ns)
models={
'y_s':dict(color='yellow',ports=[['S','tab','round']]),
'y_ns':dict(color='yellow',ports=[['N','socket','round'],['S','tab','round']]),
'y_ne':dict(color='yellow',ports=[['N','socket','round'],['E','tab','round']]),
'y_e':dict(color='yellow',ports=[['E','tab','round']]),
'y_twin':dict(color='yellow',ports=[['S','tab','twin']]),
'y_ntwin':dict(color='yellow',ports=[['N','socket','round'],['S','tab','twin']]),
'y_w':dict(color='yellow',ports=[['W','socket','round']]),
'b_give':dict(color='blue',ports=[['N','socket','twin'],['W','socket','round'],['E','tab','round']]),
# 발화 전용 모형. 대화별 제시 모형과 별도로 보존한다.
'y_es':dict(color='yellow',ports=[['E','tab','round'],['S','tab','round']]),
'b_w':dict(color='blue',ports=[['W','socket','round']]),
'b_n':dict(color='blue',ports=[['N','socket','round']])}
for mid,m in models.items():
 poly=ns['shape'](m['ports']);assert poly.is_valid
 m['path']='M '+' L '.join(f'{x*100:.3f},{y*100:.3f}' for x,y in poly.exterior.coords)+' Z'
 m['socketSides']=[s for s,k,_ in m['ports'] if k=='socket']
data={'models':models,'palette':list(models)[:8],'words':['나','주민','집','안','밖','열쇠','주다'],
'speech':{'inside':[dict(model='y_es',word='손',x=0,y=0),dict(model='b_w',word='아프다',x=1,y=0),dict(model='b_n',word='차갑다',x=0,y=1)],'outside':[dict(model='y_e',word='손',x=0,y=0),dict(model='b_w',word='아프다',x=1,y=0),dict(model='y_e',word='발',x=0,y=2),dict(model='b_w',word='차갑다',x=1,y=2)]}}
html=(OUT/'보기.template.html').read_text().replace('__DATA__',json.dumps(data,ensure_ascii=False)).replace('__CORE__',(OUT/'core.js').read_text()).replace('__APP__',(OUT/'app.js').read_text()).replace('__CSS__',(OUT/'style.css').read_text())
from fontTools.ttLib import TTFont
from fontTools import subset
font=TTFont(str(OUT.parents[2]/'기획서/source/assets/Pretendard-Regular.ttf'))
sub=subset.Subsetter();sub.populate(text=html);sub.subset(font);buf=io.BytesIO();font.save(buf)
html=html.replace('__FONT__',base64.b64encode(buf.getvalue()).decode())
(OUT/'플레이.html').write_text(html)
(OUT/'모형데이터.json').write_text(json.dumps(data,ensure_ascii=False,indent=2))
print('플레이.html generated',len(html.encode()),'bytes')
