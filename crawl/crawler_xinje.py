# -*- coding: utf-8 -*-
"""信捷xinje采集器（纯接口分页+CDN直链带Referer，无需浏览器）。可重复运行，幂等。
接口 /web/downloadCenter/file?seriesId=0&oneId=16&twoId=0&page=N （16=产品手册）。"""
import urllib.request,urllib.parse,re,os,subprocess,json,hashlib
UA="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/120 Safari/537.36"
SITE="https://www.xinje.com";CDN="https://cdn.xinje.com";BRAND="xinje";DST="pdfs/"+BRAND
os.makedirs(DST,exist_ok=True)
def enc(u):
    # 对URL路径部分的非ASCII做百分号编码，保留 :/?&=#%
    import urllib.parse as up
    p=up.urlsplit(u)
    return up.urlunsplit((p.scheme,p.netloc,up.quote(p.path),p.query,p.fragment))
def get(u):
    req=urllib.request.Request(enc(u),headers={"User-Agent":UA,"Referer":SITE+"/web/downloadCenter/index"})
    return urllib.request.urlopen(req,timeout=90).read()
def pages_of(fp):
    r=subprocess.run(["pdfinfo",fp],capture_output=True,text=True)
    for l in r.stdout.splitlines():
        if l.startswith("Pages:"):return int(l.split()[1])
    return 0
def parse_page(html):
    out=[]
    for li in re.findall(r'<li[^>]*>(.*?)</li>',html,re.S):
        if 'cdn.xinje.com' not in li:continue
        m=re.search(r'href="(https://cdn\.xinje\.com[^"]+\.pdf)"',li)
        if not m:continue
        u=m.group(1)
        txt=re.sub(r'<[^>]+>',' ',li);txt=re.sub(r'\s+',' ',txt)
        ver=re.search(r'版本[:：]\s*([0-9A-Za-z.]+)',txt)
        dt=re.search(r'更新日期[:：]\s*(\d{4})[.\-/]?(\d{1,2})?[.\-/]?(\d{1,2})?',txt)
        size=re.search(r'大小[:：]\s*([0-9.]+[KMG]?B)',txt)
        t=re.sub(r'^\s*预览\s*下载\s*','',txt).split('大小')[0].strip()
        out.append({"u":u,"t":t,
                    "v":ver.group(1) if ver else "",
                    "d":("%s-%s-%s"%(dt.group(1),dt.group(2) or '01',dt.group(3) or '01')) if dt else "",
                    "size_h":size.group(1) if size else ""})
    return out
def run():
    # 云端增量：加载上一版 manifest（按URL），已记录的直接复用（含页数/fn），不重复下载、不重新 pdfinfo
    old={}
    if os.path.exists("xinje_manifest.json"):
        try:
            for x in json.load(open("xinje_manifest.json",encoding="utf-8")):
                if x.get("u"):old[x["u"]]=x
        except Exception:pass
    recs=[];seen=set();page=1
    while True:
        api="%s/web/downloadCenter/file?seriesId=0&oneId=16&twoId=0&page=%d&fileName="%(SITE,page)
        try:html=get(api).decode("utf-8","ignore")
        except Exception as e:
            print("  第%d页接口失败 %s"%(page,str(e)[:50]));break
        items=parse_page(html)
        if not items:break
        added=0
        for it in items:
            if it["u"] in seen:continue
            seen.add(it["u"])
            ox=old.get(it["u"])
            if ox and (ox.get("pages") or 0)>0:
                recs.append(ox);added+=1;continue
            key=hashlib.md5(it["u"].encode()).hexdigest()[:8]
            fn="xj_%s.pdf"%key;fp=os.path.join(DST,fn)
            if not(os.path.exists(fp) and os.path.getsize(fp)>10000):
                try:
                    raw=get(it["u"])
                    if raw[:4]!=b"%PDF":print("  非PDF",it["t"][:24]);continue
                    open(fp,"wb").write(raw)
                except Exception as e:print("  下载失败",it["t"][:24],str(e)[:40]);continue
            recs.append({**it,"fn":fn,"pages":pages_of(fp),"size":os.path.getsize(fp)})
            added+=1
        print("  第%d页 %d 项（累计%d）"%(page,len(items),len(recs)))
        page+=1
        if page>60:break
    json.dump(recs,open("xinje_manifest.json","w",encoding="utf-8"),ensure_ascii=False,indent=1)
    print("信捷产品手册落盘 %d 个"%len(recs))
if __name__=="__main__":run()
