# -*- coding: utf-8 -*-
"""昆仑通态 mcgspro.com 采集器（纯JSON接口 /api/files + /api/download/<id>，无WAF）。
只要 category=manual 的 PDF 说明书（筛掉 DOCX/软件包）。可重复运行、幂等：旧 manifest 按 id 复用，不重复下载/取页数。
"""
import json,os,subprocess,urllib.request,hashlib
UA="Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/120 Safari/537.36"
BASE="https://www.mcgspro.com";DST="pdfs/mcgs"
os.makedirs(DST,exist_ok=True)
def get(u,binary=False):
    req=urllib.request.Request(u,headers={"User-Agent":UA,"Referer":BASE+"/downloads.html"})
    raw=urllib.request.urlopen(req,timeout=60).read()
    return raw if binary else raw.decode("utf-8","ignore")
def pages_of(fp):
    r=subprocess.run(["pdfinfo",fp],capture_output=True,text=True)
    for l in r.stdout.splitlines():
        if l.startswith("Pages:"):return int(l.split()[1])
    return 0
def run():
    old={}
    if os.path.exists("mcgs_manifest.json"):
        try:
            for x in json.load(open("mcgs_manifest.json",encoding="utf-8")):
                if x.get("id"):old[x["id"]]=x
        except Exception:pass
    data=json.loads(get(BASE+"/api/files"))
    recs=[];new=0
    for it in data:
        if it.get("category")!="manual":continue
        if not it.get("filename","").lower().endswith(".pdf"):continue
        cid=it["id"]
        u=BASE+"/api/download/%d"%cid
        ox=old.get(cid)
        if ox and (ox.get("pages") or 0)>0:
            recs.append(ox);continue
        fn="mc_%d.pdf"%cid;fp=os.path.join(DST,fn)
        if not(os.path.exists(fp) and os.path.getsize(fp)>10000):
            try:
                raw=get(u,binary=True)
                if raw[:4]!=b"%PDF":print("  非PDF",it["name"][:30]);continue
                open(fp,"wb").write(raw)
            except Exception as e:
                print("  下载失败",it["name"][:30],str(e)[:40]);continue
        recs.append({"id":cid,"cat":it.get("subCategory",""),"t":it["name"],
                      "d":it.get("date",""),"u":u,"fn":fn,
                      "pages":pages_of(fp),"size":os.path.getsize(fp)})
        new+=1
    json.dump(recs,open("mcgs_manifest.json","w",encoding="utf-8"),ensure_ascii=False,indent=1)
    print("昆仑通态说明书 %d 个（本次新增下载 %d，复用 %d）"%(len(recs),new,len(recs)-new))
if __name__=="__main__":run()
