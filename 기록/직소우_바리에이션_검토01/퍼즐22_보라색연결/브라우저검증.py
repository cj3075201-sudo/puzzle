from pathlib import Path
import subprocess,json,re,html
r=Path(__file__).resolve().parent
tmp=Path('/mnt/c/Users/cj307/AppData/Local/Temp')
s=(r/'플레이.html').read_text().replace("location.search.includes('test=1')","true")
s=s.replace('</body>','<script>'+(r/'browser.test.js').read_text()+'</script></body>')
(tmp/'purple22-test.html').write_text(s)
cmd="& 'C:\\Program Files (x86)\\Microsoft\\Edge\\Application\\msedge.exe' --headless --disable-gpu --no-first-run --user-data-dir='C:\\Users\\cj307\\AppData\\Local\\Temp\\purple22-headless' --window-size=1536,1200 --virtual-time-budget=18000 --screenshot='C:\\Users\\cj307\\AppData\\Local\\Temp\\purple22-test.png' --dump-dom 'file:///C:/Users/cj307/AppData/Local/Temp/purple22-test.html'"
res=subprocess.run(['/mnt/c/Windows/System32/WindowsPowerShell/v1.0/powershell.exe','-NoProfile','-Command',cmd],capture_output=True,timeout=55)
raw=res.stdout.decode('utf-8',errors='replace');(tmp/'purple22-test-dom.txt').write_text(raw)
m=re.search(r'<pre id="verification"[^>]*>(.*?)</pre>',raw,re.S)
if m:
 d=json.loads(html.unescape(m.group(1)));(r/('browser-reload-results.json' if len(d['checks'])==4 else 'browser-results.json')).write_text(json.dumps(d,ensure_ascii=False,indent=2));print('passed',d['passed'],'checks',len(d['checks']));print([c for c in d['checks'] if not c['pass']])
else:print('NO RESULTS',res.returncode,raw[-500:],res.stderr.decode('utf-8',errors='replace')[-800:])
if (tmp/'purple22-test.png').exists():(r/'플레이_검증.png').write_bytes((tmp/'purple22-test.png').read_bytes())
