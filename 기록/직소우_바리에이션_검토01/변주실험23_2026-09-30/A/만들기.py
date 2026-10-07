from pathlib import Path
import base64, io, sys

from fontTools.ttLib import TTFont
from fontTools import subset
root=Path(__file__).resolve().parent
html=(root/'보기.template.html').read_text()
for marker,name in [('CSS','style.css'),('CORE','core.js'),('MODELS','models.json'),('SCENARIOS_A','scenarios-a.js'),('SCENARIOS_B','scenarios-b.js'),('SCENE','scene.js'),('APP','app.js')]:
 html=html.replace('__'+marker+'__',(root/name).read_text())
font=TTFont(str(next(p / '기획서/source/assets/Pretendard-Regular.ttf' for p in Path(__file__).resolve().parents if (p / '기획서/source/assets/Pretendard-Regular.ttf').is_file())))
sub=subset.Subsetter();sub.populate(text=html);sub.subset(font)
buf=io.BytesIO();font.save(buf)
html=html.replace('__FONT__',base64.b64encode(buf.getvalue()).decode())
(root/'플레이.html').write_text(html)
print('플레이.html',len(html.encode()),'bytes')
