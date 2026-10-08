# -*- coding: utf-8 -*-
"""正弦sinee采集器（playwright收集列表+详情页OSS直链，urllib带Referer下载）。可重复运行，幂等。"""
from playwright.sync_api import sync_playwright
from pw_util import chromium_path
import time,os,subprocess,urllib.request,json,re
UA="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120 Safari/537.36"
BASE="https://www.sinee.cn";BRAND="sinee";DST="pdfs/"+BRAND
os.makedirs(DST,exist_ok=True)
CATS=[("1","用户手册"),("2","宣传样本")]
def pages_of(fp):
    r=subprocess.run(["pdfinfo",fp],capture_output=True,text=True)
    for l in r.stdout.splitlines():
        if l.startswith("Pages:"):return int(l.split()[1])
    return 0
def dl(u,fp):
    req=urllib.request.Request(u,headers={"User-Agent":UA,"Referer":BASE+"/"})
    raw=urllib.request.urlopen(req,timeout=60).read()
    if raw[:4]!=b"%PDF":return False
    open(fp,"wb").write(raw);return True
def run():
    recs=[]
    seen=set()
    # 云端增量：旧manifest按URL与按详情页ID，已记录的复用（含页数/fn），不重复下载、不重新 pdfinfo
    old={};old_did={}
    if os.path.exists("sinee_manifest.json"):
        try:
            for x in json.load(open("sinee_manifest.json",encoding="utf-8")):
                if x.get("u"):old[x["u"]]=x
                if x.get("durl"):
                    m=re.search(r'/47/(\d+)',x["durl"])
                    if m:old_did[m.group(1)]=x
        except Exception:pass
    with sync_playwright() as p:
        b=p.chromium.launch(headless=True,executable_path=chromium_path(),args=["--no-sandbox","--disable-dev-shm-usage"])
        pg=b.new_page(user_agent=UA)
        for fl,cat in CATS:
            # 遍历分页
            pn=1;detail=[]
            while True:
                url="%s/47/?fl=%s"%(BASE,fl) if pn==1 else "%s/47/pn%d/?fl=%s"%(BASE,pn,fl)
                try:pg.goto(url,wait_until="domcontentloaded",timeout=20000)
                except:pass
                time.sleep(2)
                items=pg.eval_on_selector_all("a[href*='/47/']","""els=>[...new Set(els.map(a=>a.href).filter(h=>/\/47\/\d+/.test(h)))]""")
                if not items:break
                detail.extend(items)
                nxt=pg.eval_on_selector_all("a","""els=>{const a=els.find(e=>e.innerText.includes('下一页'));return a?a.href:null;}""")
                if not nxt or pn>20:break
                pn+=1
            detail=list(dict.fromkeys(detail))
            print("正弦[%s] 详情页 %d 个"%(cat,len(detail)))
            for i,durl in enumerate(detail):
                dm=re.search(r'/47/(\d+)',durl);did=dm.group(1) if dm else None
                # 上版已枚举过的详情页直接复用记录，不再逐个打开（节省约10分钟）
                if did and did in old_did:
                    recs.append(old_did[did]);continue
                try:
                    pg.goto(durl,wait_until="domcontentloaded",timeout=20000);time.sleep(1)
                    info=pg.evaluate("""()=>{
                      const a=document.querySelectorAll("a[href*='.pdf']");
                      let t=(document.title||'').split(/[,，]/)[0].trim();
                      return {pdf:a.length?a[0].href:null,t:t};
                    }""")
                    u=info.get("pdf");t=info.get("t") or ""
                    if not u:continue
                    if u in seen:continue
                    seen.add(u)
                    if not t:t=u.split('/')[-1]
                    fn="sn_%s.pdf"%did;fp=os.path.join(DST,fn)
                    ox=old.get(u)
                    if ox and (ox.get("pages") or 0)>0:
                        recs.append(ox);continue
                    if not(os.path.exists(fp) and os.path.getsize(fp)>10000):
                        if not dl(u,fp):print("  下载失败",t[:30]);continue
                    recs.append({"cat":cat,"t":t,"u":u,"fn":fn,"pages":pages_of(fp),"size":os.path.getsize(fp),"durl":durl})
                except Exception as e:
                    print("  详情页失败",durl,str(e)[:40])
        b.close()
    json.dump(recs,open("sinee_manifest.json","w",encoding="utf-8"),ensure_ascii=False,indent=1)
    print("正弦落盘 %d 个"%len(recs))
if __name__=="__main__":run()
