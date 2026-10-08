# -*- coding: utf-8 -*-
"""禾川hcfa采集器（playwright点说明书分类+翻页，context.request下载 hcfa.cc 直链）。可重复运行，幂等。"""
from playwright.sync_api import sync_playwright
from pw_util import chromium_path
import time,os,subprocess,json,hashlib
UA="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/120 Safari/537.36"
DST="pdfs/hcfa";os.makedirs(DST,exist_ok=True)
def pages_of(fp):
    r=subprocess.run(["pdfinfo",fp],capture_output=True,text=True)
    for l in r.stdout.splitlines():
        if l.startswith("Pages:"):return int(l.split()[1])
    return 0
def grab(pg):
    return pg.eval_on_selector_all("a[href*='.pdf']","""els=>{
      const out=[];
      document.querySelectorAll('a[href*=".pdf"]').forEach(a=>{
        const t=(a.innerText||'').trim();
        if(t&&t!=='在线浏览'&&a.href.includes('hcfa'))out.push({t:t,u:a.href});
      });
      return out;
    }""")
def run():
    recs=[];seen=set()
    # 云端增量：旧manifest按URL，已记录的复用（含页数/fn），不重复下载、不重新 pdfinfo
    old={}
    if os.path.exists("hcfa_manifest.json"):
        try:
            for x in json.load(open("hcfa_manifest.json",encoding="utf-8")):
                if x.get("u"):old[x["u"]]=x
        except Exception:pass
    with sync_playwright() as p:
        b=p.chromium.launch(headless=True,executable_path=chromium_path(),args=["--no-sandbox","--ignore-certificate-errors","--disable-dev-shm-usage"])
        ctx=b.new_context(user_agent=UA,ignore_https_errors=True)
        pg=ctx.new_page()
        pg.goto("https://www.hcfa.cn/service/index.html",wait_until="domcontentloaded",timeout=30000)
        time.sleep(5)
        pg.evaluate("""()=>{const e=[...document.querySelectorAll('a,li,span,div')].find(x=>x.innerText.trim()==='说明书');if(e)e.click();}""")
        time.sleep(5)
        maxp=max(pg.eval_on_selector_all("a.num","els=>els.map(a=>parseInt(a.innerText)).filter(n=>n>0)")+[1])
        pn=1
        while True:
            if pn>1:
                clicked=pg.evaluate("""(n)=>{
                  const a=[...document.querySelectorAll('a.num')].find(e=>e.innerText.trim()===String(n));
                  if(a){a.click();return true;}return false;
                }""",pn)
                if not clicked:break
                time.sleep(4)
            rows=grab(pg)
            for it in rows:
                if it["u"] in seen:continue
                seen.add(it["u"])
                key=hashlib.md5(it["u"].encode()).hexdigest()[:8]
                fn="hc_%s.pdf"%key;fp=os.path.join(DST,fn)
                ox=old.get(it["u"])
                if ox and (ox.get("pages") or 0)>0:
                    recs.append(ox);continue
                if not(os.path.exists(fp) and os.path.getsize(fp)>10000):
                    try:
                        r=ctx.request.get(it["u"],headers={"Referer":"https://www.hcfa.cn/"})
                        raw=r.body()
                        if r.status!=200 or raw[:4]!=b"%PDF":print("  失败",it["t"][:24],r.status);continue
                        open(fp,"wb").write(raw)
                    except Exception as e:print("  异常",it["t"][:24],str(e)[:40]);continue
                recs.append({"t":it["t"],"u":it["u"],"fn":fn,"pages":pages_of(fp),"size":os.path.getsize(fp)})
            print("  第%d页 %d项 累计%d"%(pn,len(rows),len(recs)))
            pn+=1
            if pn>maxp:break
        b.close()
    json.dump(recs,open("hcfa_manifest.json","w",encoding="utf-8"),ensure_ascii=False,indent=1)
    print("禾川说明书落盘 %d 个"%len(recs))
if __name__=="__main__":run()
