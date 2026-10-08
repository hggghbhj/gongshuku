# -*- coding: utf-8 -*-
"""顾美coolmay采集器（直连静态站，curl可下，无需浏览器）。可重复运行，幂等。"""
import re,os,subprocess,urllib.request,json,hashlib
UA="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/120 Safari/537.36"
BASE="http://www.coolmay.com";BRAND="coolmay"
PAGES=[("宣传画册","xuanchuanshouce.html"),("用户手册","yonghushouce.html"),("使用手册","shiyongshouce.html")]
DST="pdfs/"+BRAND;os.makedirs(DST,exist_ok=True)
def fetch(u):
    req=urllib.request.Request(u,headers={"User-Agent":UA,"Referer":BASE})
    return urllib.request.urlopen(req,timeout=60).read()
def pages_of(fp):
    r=subprocess.run(["pdfinfo",fp],capture_output=True,text=True)
    for l in r.stdout.splitlines():
        if l.startswith("Pages:"):return int(l.split()[1])
    return 0
def collect():
    items=[]
    for cat,pg in PAGES:
        html=fetch(BASE+"/"+pg).decode("utf-8","ignore")
        open("cm_"+pg.replace(".html","")+".html","wb").write(html.encode("utf-8","ignore"))
        for tr in re.findall(r"<tr[^>]*>(.*?)</tr>",html,re.S|re.I):
            m=re.search(r'<a[^>]+href=["\']([^"\']+\.pdf)["\'][^>]*>(.*?)</a>',tr,re.S|re.I)
            if not m:continue
            u=m.group(1);t=re.sub(r"<[^>]+>","",m.group(2)).strip()
            t=re.sub(r"\.pdf$","",t,flags=re.I).strip()
            if len(t)<5:continue  # 过滤 cs 等噪声
            if u.startswith("/"):u=BASE+u
            if not any(x["u"]==u for x in items):items.append({"cat":cat,"t":t,"u":u})
    return items
def run():
    items=collect()
    print("coolmay 有效手册:",len(items))
    # 云端增量：加载上一版 manifest（按URL），已记录的直接复用页数/大小，不重复下载、不重新 pdfinfo
    old={}
    if os.path.exists("coolmay_manifest.json"):
        try:
            for x in json.load(open("coolmay_manifest.json",encoding="utf-8")):
                if x.get("u"):old[x["u"]]=x
        except Exception:pass
    recs=[]
    for i,it in enumerate(items,1):
        fn="cm_%02d.pdf"%i;fp=os.path.join(DST,fn)
        ox=old.get(it["u"])
        if ox and (ox.get("pages") or 0)>0:
            recs.append({"i":i,"cat":it["cat"],"t":it["t"],"u":it["u"],"fn":fn,
                         "pages":ox.get("pages"),"size":ox.get("size","")})
            print("  = %s %-40s %3d页(复用)"%(fn,it["t"][:40],ox.get("pages",0)))
            continue
        if not (os.path.exists(fp) and os.path.getsize(fp)>10000):
            try:
                raw=fetch(it["u"])
                if raw[:4]!=b"%PDF":print("  非PDF",it["t"]);continue
                open(fp,"wb").write(raw)
            except Exception as e:
                print("  下载失败",it["t"][:30],str(e)[:50]);continue
        pages=pages_of(fp)
        recs.append({"i":i,"cat":it["cat"],"t":it["t"],"u":it["u"],"fn":fn,"pages":pages,"size":os.path.getsize(fp)})
        print("  %s %-44s %3d页"%(fn,it["t"][:44],pages))
    json.dump(recs,open("coolmay_manifest.json","w",encoding="utf-8"),ensure_ascii=False,indent=1)
    print("已落盘 %d 个，manifest=coolmay_manifest.json"%len(recs))
if __name__=="__main__":run()
