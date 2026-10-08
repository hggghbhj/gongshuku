# -*- coding: utf-8 -*-
import json,os,re,sys,urllib.parse,concurrent.futures,urllib.request
sys.path.insert(0,".")
from gsk_common import pdf_meta
p="."
brand,jsonfile,outdir=sys.argv[1],sys.argv[2],sys.argv[3]
os.makedirs(outdir,exist_ok=True)
signed=json.load(open(jsonfile,encoding="utf-8"))
UA="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/120 Safari/537.36"
def fname(u):return urllib.parse.unquote(u.split("/file/")[-1].split("?")[0])
def cls(fn):
    low=fn.lower()
    if re.search(r"cert|证书|tuv|ce-emc|lvd|emc|质量体系|iso|rohs",low):return "cert"
    if re.search(r"样本|彩页|sample|brochure|catalog|综合样本",low):return "sample"
    if re.search(r"说明书|手册|指南|配置文件|instruction|manual|user",low):return "manual"
    return "other"
def dl(pair):
    orig,signed_url=pair
    if signed_url=="ERR":return {"fn":fname(orig),"ok":False,"reason":"签名失败","cls":"?"}
    fn=fname(orig);c=cls(fn)
    safe=re.sub(r'[/\\:*?"<>|&]',"_",fn)[:120]
    dest=os.path.join(outdir,safe)
    if os.path.exists(dest) and os.path.getsize(dest)>1000:
        meta=pdf_meta(dest);return {"fn":fn,"ok":True,"size":os.path.getsize(dest),"dest":dest,"meta":meta,"cls":c}
    try:
        import subprocess
        cp=subprocess.run(["curl","-sS","-L","-m","120","-A",UA,"-o",dest,
                           "-w","%{http_code}",signed_url],capture_output=True,text=True,timeout=140)
        code=cp.stdout.strip()
        if not os.path.exists(dest):return {"fn":fn,"ok":False,"reason":"无文件 http="+code,"cls":c}
        raw=open(dest,"rb").read()
        if len(raw)<1000 or raw[:4]!=b"%PDF":
            os.remove(dest);return {"fn":fn,"ok":False,"reason":"非PDF%d http=%s"%(len(raw),code),"cls":c}
        meta=pdf_meta(dest)
        return {"fn":fn,"ok":True,"size":len(raw),"dest":dest,"meta":meta,"cls":c}
    except Exception as e:return {"fn":fn,"ok":False,"reason":str(e)[:80],"cls":c}
with concurrent.futures.ThreadPoolExecutor(max_workers=8) as ex:
    res=list(ex.map(dl,signed))
json.dump(res,open(os.path.join(outdir,"_dl_results.json"),"w",encoding="utf-8"),ensure_ascii=False,indent=1)
mans=[r for r in res if r["ok"] and r["cls"]=="manual"]
print("成功 %d/%d  说明书 %d  样本 %d  证书 %d  其他 %d  失败 %d"%(
 sum(r["ok"] for r in res),len(res),len(mans),
 sum(1 for r in res if r["cls"]=="sample"),sum(1 for r in res if r["cls"]=="cert"),
 sum(1 for r in res if r["cls"]=="other"),sum(1 for r in res if not r["ok"])))
print("--- 失败 ---")
for r in res:
    if not r["ok"]:print("  %s %s"%(r["fn"][:45],r["reason"]))
print("--- 说明书页数/白页 ---")
for r in mans:
    m=r["meta"] or {};print("  p%-4s w%-7s %s"%(m.get("pages"),m.get("white"),r["fn"][:65]))
