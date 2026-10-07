import json,socket,sys
with socket.socket(socket.AF_UNIX,socket.SOCK_STREAM) as connection:
    connection.connect('/tmp/grad-core24-20260930/browser.sock')
    connection.sendall((sys.argv[1]+'\n').encode())
    chunks=[]
    while True:
        part=connection.recv(1024*1024)
        if not part: break
        chunks.append(part)
    response=json.loads(b''.join(chunks))
    if response.get('ok') and 'controls' in response.get('result',{}):
        controls=response['result']['controls']
        buttons=[c for c in controls if c['tag'] in ('button','a','select','summary','input','textarea')]
        def inside(child,parent):
            a,b=child['rect'],parent['rect']
            return (a['x']>=b['x']-1 and a['y']>=b['y']-1 and
                    a['x']+a['width']<=b['x']+b['width']+1 and
                    a['y']+a['height']<=b['y']+b['height']+1)
        compact=[]
        for item in controls:
            if item['tag'] in ('path','ellipse','circle','line','polygon','svg','text'):
                continue
            if item not in buttons and any(inside(item,parent) for parent in buttons):
                continue
            item={k:v for k,v in item.items() if not(k=='disabled' and v is False)}
            if not item.get('text'):item.pop('text',None)
            compact.append(item)
        response['result']['controls']=compact
    print(json.dumps(response,ensure_ascii=False))
