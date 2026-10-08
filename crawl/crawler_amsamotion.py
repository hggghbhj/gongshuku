# -*- coding: utf-8 -*-
"""艾莫迅 amsamotion.com 采集器（服务端渲染表格，PDF 直链 oss.amsamotion.com/uploads/，无WAF）。
遍历 download.html?page=1..N，只要 PDF 说明书。可重复运行、幂等：旧 manifest 按 URL 复用，不重复下载/取页数。
"""
import re,json,os,subprocess,urllib.request,hashlib
UA="Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/120 Safari/537.36"
BASE="https://www.amsamotion.com";DST="pdfs/amsamotion"
os.makedirs(DST,exist_ok=True)
def get(u):
    req=urllib.request.Request(u,headers={"User-Agent":UA,"Referer":BASE+"/download.html"})
    return urllib.request.urlopen(req,timeout=60).read().decode("utf-8","ignore")
def pages_of(fp):
    r=subprocess.run(["pdfinfo",fp],capture_output=True,text=True)
    for l in r.stdout.splitlines():
        if l.startswith("Pages:"):return int(l.split()[1])
    return 0
def run():
    old={}
    if os.path.exists("amsamotion_manifest.json"):
        try:
            for x in json.load(open("amsamotion_manifest.json",encoding="utf-8")):
                if x.get("u"):old[x["u"]]=x
        except Exception:pass
    recs=[];seen=set();new=0
    pn=1;empty_streak=0
    while pn<=60 and empty_streak<2:
        try:
            h=get(BASE+"/download.html?page=%d"%pn)
        except Exception as e:
            print("  第%d页抓取失败"%pn,str(e)[:40]);pn+=1;continue
        # 找所有 oss PDF 链接
        urls=re.findall(r'href="(https://oss\.amsamotion\.com/uploads/[^"]+\.pdf)"',h)
        # 标题：链接附近的 data-fullname 或链接文本
        # 用行级匹配：每个链接所在片段
        cnt=0
        for u in urls:
            if u in seen:continue
            seen.add(u);cnt+=1
            # 从该URL附近提取标题
            idx=h.find(u)
            seg=h[max(0,idx-400):idx]
            m=re.search(r'data-fullname="([^"]+)"',seg)
            t=m.group(1) if m else os.path.basename(u).split(".pdf")[0]
            ox=old.get(u)
            if ox and (ox.get("pages") or 0)>0:
                recs.append(ox);continue
            fn="am_%s.pdf"%hashlib.md5(u.encode()).hexdigest()[:8];fp=os.path.join(DST,fn)
            if not(os.path.exists(fp) and os.path.getsize(fp)>10000):
                try:
                    req=urllib.request.Request(u,headers={"User-Agent":UA,"Referer":BASE+"/"})
                    raw=urllib.request.urlopen(req,timeout=90).read()
                    if raw[:4]!=b"%PDF":print("  非PDF",t[:24]);continue
                    open(fp,"wb").write(raw)
                except Exception as e:
                    print("  下载失败",t[:24],str(e)[:40]);continue
            recs.append({"t":t,"u":u,"fn":fn,"pages":pages_of(fp),"size":os.path.getsize(fp)})
            new+=1
        if cnt==0:empty_streak+=1
        else:empty_streak=0
        print("  第%d页 PDF%d 累计%d"%(pn,cnt,len(recs)))
        pn+=1
    json.dump(recs,open("amsamotion_manifest.json","w",encoding="utf-8"),ensure_ascii=False,indent=1)
    print("艾莫迅说明书 %d 个（本次新增下载 %d，复用 %d）"%(len(recs),new,len(recs)-new))
if __name__=="__main__":run()
