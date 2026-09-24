# -*- coding: utf-8 -*-
"""雷赛leisai采集器：纯接口 get-download-page 分页，直链 /upload/file 下载，仅PDF。可重复运行幂等。"""
import urllib.request,urllib.parse,json,os,time,subprocess,hashlib
API="https://www.leisai.com/cebest-cms/front/get-download-page"
BASE="https://www.leisai.com"
DST="pdfs/leisai";os.makedirs(DST,exist_ok=True)
HEAD={"User-Agent":"Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/120 Safari/537.36",
 "Content-Type":"application/json;charset=UTF-8","Referer":"https://www.leisai.com/downloads.html"}
def post_page(pn,size=100):
    body=json.dumps({"category":"","key":"","productCategoryId":"","language":"中文","page":pn,"size":size,"totalElements":size}).encode()
    req=urllib.request.Request(API,data=body,headers=HEAD,method="POST")
    with urllib.request.urlopen(req,timeout=30) as r:
        return json.loads(r.read().decode())
def get(url):
    req=urllib.request.Request(url,headers={"User-Agent":HEAD["User-Agent"],"Referer":HEAD["Referer"]})
    with urllib.request.urlopen(req,timeout=90) as r:
        return r.read()
def pages_of(fp):
    r=subprocess.run(["pdfinfo",fp],capture_output=True,text=True)
    for l in r.stdout.splitlines():
        if l.startswith("Pages:"):return int(l.split()[1])
    return 0
def run():
    items=[]
    pn=1
    while True:
        try:d=post_page(pn)
        except Exception as e:
            print("  第%d页失败 %s"%(pn,str(e)[:50]));time.sleep(3);break
        page=d["data"]["contentDTOPage"]
        for it in page["content"]:
            f=it.get("file1") or ""
            if not f.lower().endswith(".pdf") or f in {x["f"] for x in items}:continue
            items.append({"t":it.get("title",""),"f":f,"cat":it.get("single1",""),
              "lang":it.get("single2",""),"ver":it.get("version",""),"date":(it.get("postTime") or "")[:10],"id":it.get("id")})
        print("  第%d页 PDF累计%d"%(pn,len(items)))
        if page.get("last") or pn>=page.get("totalPages",pn):break
        pn+=1;time.sleep(0.5)
    print("PDF总数",len(items))
    # 云端增量：旧manifest按URL，已记录的复用（含页数/fn），不重复下载、不重新 pdfinfo
    old={}
    if os.path.exists("leisai_manifest.json"):
        try:
            for x in json.load(open("leisai_manifest.json",encoding="utf-8")):
                if x.get("u"):old[x["u"]]=x
        except Exception:pass
    recs=[];ok=0
    for i,it in enumerate(items):
        fullu=BASE+it["f"]
        ox=old.get(fullu)
        if ox and (ox.get("pages") or 0)>0:
            recs.append(ox);continue
        key=hashlib.md5(it["f"].encode()).hexdigest()[:8]
        fn="ls_%s.pdf"%key;fp=os.path.join(DST,fn)
        if not(os.path.exists(fp) and os.path.getsize(fp)>10000):
            u=BASE+"/".join(urllib.parse.quote(seg) for seg in it["f"].split("/"))
            try:
                raw=get(u)
                if raw[:4]!=b"%PDF":print("  非PDF",it["t"][:20]);continue
                open(fp,"wb").write(raw);ok+=1
            except Exception as e:
                print("  下载失败",it["t"][:20],str(e)[:40]);continue
        recs.append({"t":it["t"],"u":fullu,"fn":fn,"pages":pages_of(fp),
          "size":os.path.getsize(fp),"cat":it["cat"],"v":it["ver"],"d":it["date"]})
        if (i+1)%25==0:print("  处理%d/%d"%(i+1,len(items)))
    json.dump(recs,open("leisai_manifest.json","w",encoding="utf-8"),ensure_ascii=False,indent=1)
    print("雷赛PDF落盘 %d 个（新下载%d）"%(len(recs),ok))
if __name__=="__main__":run()
