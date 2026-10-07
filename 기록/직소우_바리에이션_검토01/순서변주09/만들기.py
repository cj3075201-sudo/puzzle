"""사용자 주다 배치 정정과 한 장면의 순서 변주. 독립 설계 설명 자료."""
from pathlib import Path
import ast, sys, json, io, base64

OUT=Path(__file__).resolve().parent
source=OUT.parent/'연결확장08/만들기.py'
tree=ast.parse(source.read_text())
names={'shape','part','transfer','check','svg'}
constants={'NORMAL','MID','OPP','COLORS'}
nodes=[n for n in tree.body if isinstance(n,(ast.Import,ast.ImportFrom)) or isinstance(n,ast.FunctionDef) and n.name in names or isinstance(n,ast.Assign) and any(isinstance(t,ast.Name) and t.id in constants for t in n.targets)]
ns={};exec(compile(ast.Module(body=nodes,type_ignores=[]),str(source),'exec'),ns)
part=ns['part'];transfer=ns['transfer'];svg=ns['svg'];check=ns['check']
boards={
 'give':transfer('주민','나','열쇠','주다'),
 'give_reverse':transfer('나','주민','열쇠','주다'),
 'exit':[part('actor','yellow',0,0,'주민',[('S','tab','round')]),part('verb','blue',0,1,'나가다',[('N','socket','round')])],
 'close':[part('actor','yellow',0,0,'나',[('S','tab','round')]),part('verb','blue',0,1,'닫다',[('N','socket','round'),('E','tab','round')]),part('door','yellow',1,1,'문',[('W','socket','round')])]
}
data={k:svg(v,380 if k.startswith('give') else 310,240) for k,v in boards.items()}
checks={k:check(v) for k,v in boards.items()}
template=(OUT/'보기.template.html').read_text()
from fontTools import subset
from fontTools.ttLib import TTFont
font=TTFont(str(next(p / '기획서/source/assets/Pretendard-Regular.ttf' for p in Path(__file__).resolve().parents if (p / '기획서/source/assets/Pretendard-Regular.ttf').is_file())))
sub=subset.Subsetter();sub.populate(text=template+json.dumps(data,ensure_ascii=False));sub.subset(font)
b=io.BytesIO();font.save(b)
(OUT/'보기.html').write_text(template.replace('__FONT__',base64.b64encode(b.getvalue()).decode()).replace('__DATA__',json.dumps(data,ensure_ascii=False)),encoding='utf-8')
(OUT/'접합확인.json').write_text(json.dumps(checks,ensure_ascii=False,indent=2),encoding='utf-8')
print('generated: 보기.html; 4 local jigsaw layouts')
