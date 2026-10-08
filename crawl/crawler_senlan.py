# -*- coding: utf-8 -*-
"""森兰（希望森兰 chinavvvf.com）采集器：列表页 /list-57-<N>.html 直接含 PDF 直链 uploadfile/...，无WAF。
只要手册下载分类（list-57）。可重复运行、幂等：旧 manifest 按 URL 复用。
"""
import re,json,os,subprocess,urllib.request,hashlib
UA="Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/120 Safari/537.36"
BASE="http://www.chinavvvf.com";DST="pdfs/senlan"
os.makedirs(DST,exist_ok=True)
def get(u):
    req=urllib.request.Request(u,headers={"User-Agent":UA,"Referer":BASE+"/"})
    return urllib.request.urlopen(req,timeout=60).read().decode("utf-8","ignore")
def pages_of(fp):
    r=subprocess.run(["pdfinfo",fp],capture_output=True,text=True)
    for l in r.stdout.splitlines():
        if l.startswith("Pages:"):return int(l.split()[1])
    return 0
def run():
    old={}
    if os.path.exists("senlan_manifest.json"):
        try:
            for x in json.load(open("senlan_manifest.json",encoding="utf-8")):
                if x.get("u"):old[x["u"]]=x
        except Exception:pass
    recs=[];seen=set();new=0
    pn=1;empty=0
    while pn<=30 and empty<2:
        try:
            h=get(BASE+"/list-57-%d.html"%pn)
        except Exception as e:
            print("  第%d页失败"%pn,str(e)[:40]);pn+=1;continue
        urls=re.findall(r'href="(uploadfile/[^"]+\.pdf)"',h)
        cnt=0
        for up in urls:
            u=BASE+"/"+up
            if u in seen:continue
            seen.add(u);cnt+=1
            # 标题：从URL文件名提取
            t=os.path.basename(up).split(".pdf")[0]
            # 尝试从链接附近文本找标题
            idx=h.find('href="'+up+'"')
            seg=h[max(0,idx-200):idx]
            m=re.search(r'title="([^"]+)"',seg)
            if m:t=m.group(1)
            ox=old.get(u)
            if ox and (ox.get("pages") or 0)>0:
                recs.append(ox);continue
            fn="sl_%s.pdf"%hashlib.md5(u.encode()).hexdigest()[:8];fp=os.path.join(DST,fn)
            if not(os.path.exists(fp) and os.path.getsize(fp)>10000):
                try:
                    req=urllib.request.Request(u,headers={"User-Agent":UA,"Referer":BASE+"/list-57-%d.html"%pn})
                    raw=urllib.request.urlopen(req,timeout=30).read()
                    if raw[:4]!=b"%PDF":print("  非PDF",t[:24]);continue
                    open(fp,"wb").write(raw)
                except Exception as e:
                    print("  下载失败",t[:24],str(e)[:40]);continue
            recs.append({"t":t,"u":u,"fn":fn,"pages":pages_of(fp),"size":os.path.getsize(fp)})
            new+=1
        if cnt==0:empty+=1
        else:empty=0
        print("  第%d页 PDF%d 累计%d"%(pn,cnt,len(recs)))
        pn+=1
    json.dump(recs,open("senlan_manifest.json","w",encoding="utf-8"),ensure_ascii=False,indent=1)
    print("森兰说明书 %d 个（本次新增下载 %d，复用 %d）"%(len(recs),new,len(recs)-new))
if __name__=="__main__":run()
