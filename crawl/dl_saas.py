# -*- coding: utf-8 -*-
"""下载 SaaS 采集到的 PDF，校验，剔除证书/样本，去重，输出标准记录。"""
import json,os,re,sys,time,subprocess,urllib.parse,concurrent.futures
sys.path.insert(0,".")
from gsk_common import BASELINE,norm_url,mk,url_in_lib,pdf_meta
import urllib.request
UA="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/120 Safari/537.36"
BRAND=sys.argv[1]; JSONFILE=sys.argv[2]; OUTDIR=sys.argv[3]
os.makedirs(OUTDIR,exist_ok=True)
data=json.load(open(JSONFILE,encoding="utf-8"))
pdfs=data["pdfs"]
def fname(u):
    return urllib.parse.unquote(u.split("/file/")[-1].split("?")[0])
def classify(fn):
    low=fn.lower()
    if re.search(r"cert|证书|tuv|ce-emc|lvd|emc|质量体系|iso|rohs",low):return "cert"
    if re.search(r"样本|彩页|sample|brochure|catalog|综合样本",low):return "sample"
    if re.search(r"说明书|手册|指南|使用|instruction|manual|user",low):return "manual"
    return "other"
def dl(item):
    u=item["href"];fn=fname(u)
    safe=re.sub(r"[/\\:*?\"<>|]","_",fn)[:110]
    dest=os.path.join(OUTDIR,safe)
    cls=classify(fn)
    try:
        req=urllib.request.Request(u,headers={"User-Agent":UA,"Referer":"https://www.powtran.com/"})
        raw=urllib.request.urlopen(req,timeout=90).read()
        if len(raw)<1000 or raw[:5]!=b"%PDF":return {"fn":fn,"u":u,"cls":cls,"ok":False,"reason":"非PDF %d字节"%len(raw)}
        open(dest,"wb").write(raw)
        meta=pdf_meta(dest)
        return {"fn":fn,"u":u,"cls":cls,"ok":True,"size":len(raw),"dest":dest,"meta":meta}
    except Exception as e:
        return {"fn":fn,"u":u,"cls":cls,"ok":False,"reason":str(e)[:80]}
results=[]
with concurrent.futures.ThreadPoolExecutor(max_workers=6) as ex:
    for r in ex.map(dl,pdfs):results.append(r)
manuals=[r for r in results if r["ok"] and r["cls"]=="manual"]
print("总:",len(results),"成功:",sum(r["ok"] for r in results),"说明书:",len(manuals),
      "样本:",sum(1 for r in results if r["cls"]=="sample"),"证书:",sum(1 for r in results if r["cls"]=="cert"),
      "失败:",sum(1 for r in results if not r["ok"]))
print("\n失败:")
for r in results:
    if not r["ok"]:print("  [%s] %s -> %s"%(r["cls"],r["fn"][:50],r["reason"]))
print("\n说明书清单(页数/白页):")
for r in manuals:
    m=r["meta"] or {};print("  p%-4s w%-6s %s"%(m.get("pages"),m.get("white"),r["fn"][:70]))
json.dump(results,open(os.path.join(OUTDIR,"_dl_results.json"),"w",encoding="utf-8"),ensure_ascii=False,indent=1)
