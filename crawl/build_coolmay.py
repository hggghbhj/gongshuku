# -*- coding: utf-8 -*-
import re,os,subprocess,urllib.request,json
UA="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/120 Safari/537.36"
BASE="http://www.coolmay.com"
pages=[("宣传手册","xuanchuanshouce.html"),("用户手册","yonghushouce.html"),("使用手册","shiyongshouce.html")]
DST="pdfs/coolmay";os.makedirs(DST,exist_ok=True)
items=[]
for cat,pg in pages:
    h=open("cm_"+pg.replace(".html","")+".html","rb").read().decode("utf-8","ignore")
    # 每个 tr 内取第一个 pdf 链接
    for tr in re.findall(r"<tr[^>]*>(.*?)</tr>",h,re.S|re.I):
        m=re.search(r'<a[^>]+href=["\']([^"\']+\.pdf)["\'][^>]*>(.*?)</a>',tr,re.S|re.I)
        if not m:continue
        u=m.group(1);t=re.sub(r"<[^>]+>","",m.group(2)).strip()
        if not t:continue  # 跳过纯图标下载链接
        if u.startswith("/"):u=BASE+u
        items.append({"cat":cat,"t":t,"u":u})
# 去重
seen=set();uniq=[]
for it in items:
    if it["u"] in seen:continue
    seen.add(it["u"]);uniq.append(it)
print("条目:",len(uniq))
def dl(u):
    req=urllib.request.Request(u,headers={"User-Agent":UA,"Referer":BASE})
    return urllib.request.urlopen(req,timeout=60).read()
def pginfo(raw):
    fp=DST+"/tmp.pdf";open(fp,"wb").write(raw)
    r=subprocess.run(["pdfinfo",fp],capture_output=True,text=True)
    pages=0
    for l in r.stdout.splitlines():
        if l.startswith("Pages:"):pages=int(l.split()[1])
    os.remove(fp)
    return pages
recs=[]
for i,it in enumerate(uniq):
    try:
        raw=dl(it["u"])
        if raw[:4]!=b"%PDF":print("  非PDF",it["t"]);continue
        pages=pginfo(raw)
        fn="cm_%02d.pdf"%i
        open(os.path.join(DST,fn),"wb").write(raw)
        # 型号
        m=re.search(r"((?:Coolmay[-\s]?)?(?:DK|TK|CX|EX|M|ML|L|FP|Q3|3G|3U)?\d+[A-Za-z0-9\-]*(?:-[0-9A-Za-z]+)?)",it["t"])
        recs.append({"cat":it["cat"],"t":it["t"],"u":it["u"],"fn":fn,"pages":pages,"size":len(raw)})
        print("%2d %-46s %3d页 %6dKB"%(i,it["t"][:46],pages,len(raw)//1024))
    except Exception as e:
        print("  失败",it["t"][:30],str(e)[:50])
json.dump(recs,open("coolmay_dl.json","w",encoding="utf-8"),ensure_ascii=False,indent=1)
print("成功",len(recs))
