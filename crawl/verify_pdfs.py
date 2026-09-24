# -*- coding: utf-8 -*-
import json,os,time,hashlib,urllib.request,subprocess
BASE="https://www.e-elitech.com"
UA="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/120.0 Safari/537.36"
cands=json.load(open("new_elitech_candidates.json",encoding="utf-8"))
os.makedirs("pdfs",exist_ok=True)
def dl(url,dest,retry=2):
    for k in range(retry+1):
        try:
            req=urllib.request.Request(url,headers={"User-Agent":UA,"Referer":BASE+"/index.php?v=new_manual"})
            data=urllib.request.urlopen(req,timeout=40).read()
            if len(data)>1000:
                open(dest,"wb").write(data);return data
        except Exception as e:
            time.sleep(0.8*(k+1))
    return None
res=[]
for i,c in enumerate(cands):
    fn="pdfs/n%02d_%s.pdf"%(i+1,hashlib.md5(c["pdf"].encode()).hexdigest()[:8])
    data=dl(c["pdf"],fn)
    r={"i":i+1,"model":c["model"] or c["title"],"cat":c["cats"][0],"date":c["date"],"url":c["pdf"],"file":fn if data else ""}
    if not data:
        r.update(status="下载失败",size=0);print("FAIL",i+1,c["model"]);res.append(r);continue
    r["size"]=len(data)
    r["sha256"]=hashlib.sha256(data).hexdigest()
    head=data[:8]
    if not data.startswith(b"%PDF"):
        r["status"]="非PDF"
    else:
        # 页数粗算（/Type /Page 出现次数，含 /Pages）
        pages=data.count(b"/Type/Page")+data.count(b"/Type /Page")
        r["raw_pages"]=pages
        r["status"]="ok"
    res.append(r)
    print(r["i"],r["status"],r["size"],"p~",r.get("raw_pages"),r["model"][:28])
    time.sleep(0.25)
json.dump(res,open("verified_pdfs.json","w",encoding="utf-8"),ensure_ascii=False,indent=1)
ok=[r for r in res if r["status"]=="ok"]
print("\n有效PDF:",len(ok),"/",len(res))
# 内容 hash 重复
seen={}
for r in ok:
    seen.setdefault(r["sha256"],[]).append(r["i"])
dups={h:v for h,v in seen.items() if len(v)>1}
print("候选间内容完全相同的组:",dups)
