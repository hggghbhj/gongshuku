# -*- coding: utf-8 -*-
"""易驱电气 szeasydrive.com 采集器：下载页 /download/、/download_2/、/download_3/ 直接含 PDF 直链 /static/upload/file/...，无WAF。
可重复运行、幂等：旧 manifest 按 URL 复用。
"""
import re,json,os,subprocess,urllib.request,hashlib
UA="Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/120 Safari/537.36"
BASE="https://www.szeasydrive.com";DST="pdfs/easydrive"
os.makedirs(DST,exist_ok=True)
def get(u):
    req=urllib.request.Request(u,headers={"User-Agent":UA,"Referer":BASE+"/download/"})
    return urllib.request.urlopen(req,timeout=60).read().decode("utf-8","ignore")
def pages_of(fp):
    r=subprocess.run(["pdfinfo",fp],capture_output=True,text=True)
    for l in r.stdout.splitlines():
        if l.startswith("Pages:"):return int(l.split()[1])
    return 0
def run():
    old={}
    if os.path.exists("easydrive_manifest.json"):
        try:
            for x in json.load(open("easydrive_manifest.json",encoding="utf-8")):
                if x.get("u"):old[x["u"]]=x
        except Exception:pass
    recs=[];seen=set();new=0
    pages=["/download/","/download_2/","/download_3/","/download_4/","/download_5/"]
    for pp in pages:
        try:
            h=get(BASE+pp)
        except Exception as e:
            print("  %s 失败"%pp,str(e)[:40]);continue
        urls=re.findall(r'href="(/static/upload/file/[^"]+\.pdf)"',h)
        if not urls:continue
        cnt=0
        for up in urls:
            u=BASE+up
            if u in seen:continue
            seen.add(u);cnt+=1
            t=os.path.basename(up).split(".pdf")[0]
            idx=h.find('href="'+up+'"')
            seg=h[max(0,idx-300):idx]
            m=re.search(r'<a[^>]*title="([^"]+)"',seg) or re.search(r'title="([^"]+)"',seg)
            if m:t=m.group(1)
            ox=old.get(u)
            if ox and (ox.get("pages") or 0)>0:
                recs.append(ox);continue
            fn="ed_%s.pdf"%hashlib.md5(u.encode()).hexdigest()[:8];fp=os.path.join(DST,fn)
            if not(os.path.exists(fp) and os.path.getsize(fp)>10000):
                try:
                    req=urllib.request.Request(u,headers={"User-Agent":UA,"Referer":BASE+pp})
                    raw=urllib.request.urlopen(req,timeout=120).read()
                    if raw[:4]!=b"%PDF":print("  非PDF",t[:24]);continue
                    open(fp,"wb").write(raw)
                except Exception as e:
                    print("  下载失败",t[:24],str(e)[:40]);continue
            recs.append({"t":t,"u":u,"fn":fn,"pages":pages_of(fp),"size":os.path.getsize(fp)})
            new+=1
        print("  %s PDF%d 累计%d"%(pp,cnt,len(recs)))
    json.dump(recs,open("easydrive_manifest.json","w",encoding="utf-8"),ensure_ascii=False,indent=1)
    print("易驱说明书 %d 个（本次新增下载 %d，复用 %d）"%(len(recs),new,len(recs)-new))
if __name__=="__main__":run()
