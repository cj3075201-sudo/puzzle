import json, socket, sys, time
AGENT=sys.argv[1] if len(sys.argv)>1 else "c"
LAST=None
def act(action, **kwargs):
 global LAST
 request={"agent":AGENT,"action":action,**kwargs}
 with socket.socket(socket.AF_UNIX,socket.SOCK_STREAM) as conn:
  conn.connect("/tmp/grad-core24-20260930/browser.sock")
  conn.sendall((json.dumps(request,ensure_ascii=False)+"\n").encode())
  chunks=[]
  while True:
   data=conn.recv(1024*1024)
   if not data:break
   chunks.append(data)
 response=json.loads(b"".join(chunks))
 if not response.get("ok"):raise RuntimeError(response)
 LAST=response["result"]
 return LAST
def click(text, contains=False, occurrence=0):
 global LAST
 if LAST is None:act("state")
 choices=[c for c in LAST["controls"] if not c.get("disabled") and ((text in c.get("text", "")) if contains else c.get("text", "")==text)]
 choices.sort(key=lambda c:c["rect"]["width"]*c["rect"]["height"])
 if not choices:raise RuntimeError("Visible control not found: "+text)
 r=choices[occurrence]["rect"]
 return act("click",x=r["x"]+r["width"]/2,y=r["y"]+r["height"]/2)
def show(state=None):
 state=state or LAST
 simple={"step":state["step"],"case":state["case"],"text":state["text"],"screenshot":state["screenshot"],"controls":[c for c in state["controls"] if c["tag"] not in ("path","ellipse","circle","line","polygon","text")]}
 print(json.dumps(simple,ensure_ascii=False))
if __name__=="__main__":
 if len(sys.argv)>2 and sys.argv[2]=="open":show(act("open",case=sys.argv[3]))
 elif len(sys.argv)>2 and sys.argv[2]=="click":act("state");show(click(sys.argv[3]))
 else:show(act("state"))
