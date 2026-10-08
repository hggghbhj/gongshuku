# -*- coding: utf-8 -*-
import re,urllib.request,os,time,json
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
        # 找 PDF（href/src，中文文件名）
        links=set(re.findall(r'["\']([^"\']+\.pdf)["\']',h))
        for l in links:
            url=l if l.startswith("http") else BASE+("/" if not l.startswith("/") else "")+l
            url=url.replace("http://www.jngbdz.com/file/","/file/").replace("http://","http://www.jngbdz.com/")
            if not url.startswith("http"):url="http://www.jngbdz.com"+l
            allpdf.setdefault(url,p)
        print(f"{p}: {len(links)} PDF")
    except Exception as e:
        print(p,"错误",e)
    time.sleep(0.2)
json.dump(list(allpdf),open("gongbei_pdfs.json","w",encoding="utf-8"),ensure_ascii=False,indent=1)
print("\n官网唯一PDF:",len(allpdf))
for u in allpdf:print(" ",u)
