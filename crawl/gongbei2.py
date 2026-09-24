# -*- coding: utf-8 -*-
import re,urllib.request,time,json
from urllib.parse import urljoin
UA="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/120.0 Safari/537.36"
BASE="http://www.jngbdz.com"
pages=["web-1200SM","web-200CPU","web-200GPU","web-GR_GT","web-GS700","web-HMI","web-KPLC",
"web-MCGS","web-PLC_Guide","web-PM","web-PPI-CH340","web-SR_ST","web-Smart-EM","web-SmartDM",
"web-SmartGM","web-T100"]
def get(u):
    req=urllib.request.Request(u,headers={"User-Agent":UA})
    raw=urllib.request.urlopen(req,timeout=25).read()
    for enc in ['utf-8','gbk']:
        try:return raw.decode(enc)
        except:pass
    return raw.decode('utf-8','ignore')
allpdf={}
for p in pages:
    try:
        h=get(BASE+"/"+p+".html")
        links=set(re.findall(r'["\']([^"\']+\.pdf)["\']',h))
        for l in links:
            url=urljoin(BASE+"/"+p+".html",l).replace("http://www.jngbdz.com","https://www.jngbdz.com")
            allpdf.setdefault(url,p)
        print(f"{p}: {len(links)} PDF")
    except Exception as e:print(p,"错误",e)
    time.sleep(0.2)
# 对比现有
docs=json.load(open("baseline.json",encoding="utf-8"))
cur=set(d["pdf"].replace("http://","https://") for d in docs if d.get("b")=="工贝电子")
cur_norm=set(u.split("/")[-1] for u in cur)
print("\n官网PDF:",len(allpdf)," 现有:",len(cur))
for u,page in allpdf.items():
    fn=u.split("/")[-1]
    new = fn not in cur_norm and u not in cur
    print(("🆕新增" if new else "已有   "),page,f.split("/")[-1][:55] if False else fn[:55])
json.dump([{"url":u,"page":pg} for u,pg in allpdf.items()],open("gongbei_pdfs.json","w",encoding="utf-8"),ensure_ascii=False,indent=1)
