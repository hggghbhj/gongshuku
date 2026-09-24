import json,subprocess,os,glob
from PIL import Image
import numpy as np
v=json.load(open("white_check.json"))
sus=[r for r in v if r.get("flag","").startswith(("疑似白页","打不开"))]
final={}
for r in v:
    if r.get("status")!="ok":continue
    final[r["i"]]=r
for r in sus:
    f=r["file"];base="/tmp/pg_%d"%r["i"]
    for old in glob.glob(base+"*.png"):os.remove(old)
    if not os.path.exists(f):r["final"]="无文件";continue
    p=subprocess.run(["pdftoppm","-f","1","-l","1","-r","40","-png",f,base],capture_output=True,text=True)
    pngs=sorted(glob.glob(base+"*.png"))
    if not pngs:
        r["final"]="渲染失败(打不开)"
        continue
    a=np.array(Image.open(pngs[0]).convert("L"))
    nw=(a<235).mean()
    r["nonwhite"]=round(float(nw),3)
    if nw<0.01:r["final"]="真白页(排除)"
    else:r["final"]="有内容(保留)"
    print(r["i"],r["model"][:24],"非白占比%.3f"%nw,"->",r["final"])
json.dump(v,open("white_check.json","w",encoding="utf-8"),ensure_ascii=False,indent=1)
