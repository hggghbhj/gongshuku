# -*- coding: utf-8 -*-
"""欧瑞euradrives采集器（playwright翻页收集，直链带Referer下载）。可重复运行，幂等。"""
from playwright.sync_api import sync_playwright
import time,os,subprocess,urllib.request,json,re,hashlib
UA="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120 Safari/537.36"
BASE="https://www.euradrives.com";BRAND="oura";DST="pdfs/"+BRAND
os.makedirs(DST,exist_ok=True)
def pages_of(fp):
    r=subprocess.run(["pdfinfo",fp],capture_output=True,text=True)
    for l in r.stdout.splitlines():
        if l.startswith("Pages:"):return int(l.split()[1])
    return 0
def dl(u,fp):
    req=urllib.request.Request(u,headers={"User-Agent":UA,"Referer":BASE+"/service/down.html"})
    raw=urllib.request.urlopen(req,timeout=90).read()
    if raw[:4]!=b"%PDF":return False
    open(fp,"wb").write(raw);return True
def grab_page(pg):
    return pg.evaluate("""()=>{
      const out=[];
      document.querySelectorAll("a[href*='Upload/File'][href*='.pdf']").forEach(a=>{
        let tr=a.closest('tr')||a.closest('li')||a.parentElement;
        let date='';
        if(tr){const m=tr.innerText.match(/20\\d{2}[-\\/.]\\d{1,2}[-\\/.]\\d{1,2}/);if(m)date=m[0];}
        out.push({u:a.href,t:(a.innerText||'').trim().replace(/\\.pdf$/,''),d:date});
      });
      return out;
    }""")
def run():
    # 云端增量：加载上一版 manifest（按URL与按fn），已记录的复用（含页数/fn），不重复下载、不重新 pdfinfo
    old_u={};old_url={}
    if os.path.exists("oura_manifest.json"):
        try:
            for x in json.load(open("oura_manifest.json",encoding="utf-8")):
                if x.get("fn"):old_u[x["fn"]]=x
                if x.get("u"):old_url[x["u"]]=x
        except Exception:pass
    recs=[];seen=set()
    with sync_playwright() as p:
        b=p.chromium.launch(headless=True,executable_path="/usr/local/bin/chromium",args=["--no-sandbox","--disable-dev-shm-usage"])
        pg=b.new_page(user_agent=UA)
        pg.goto(BASE+"/service/down.html",wait_until="networkidle",timeout=35000);time.sleep(2)
        for label in ["用户手册","宣传资料"]:
            # 每个分类重新导航，避免上一分类停留页干扰
            pg.goto(BASE+"/service/down.html",wait_until="networkidle",timeout=35000)
            time.sleep(2)
            pg.evaluate("(l)=>{const t=[...document.querySelectorAll('a,li,span,div')].find(e=>e.innerText.trim()===l);if(t)t.click();}",label)
            time.sleep(3)
            # 确保回到第1页
            pg.evaluate("""()=>{const a=[...document.querySelectorAll('a.num')].find(e=>e.innerText.trim()==='1');if(a)a.click();}""")
            time.sleep(2)
            page_n=1
            while True:
                rows=grab_page(pg)
                for r in rows:
                    if r["u"] in seen:continue
                    seen.add(r["u"])
                    fn="or_%s.pdf"%hashlib.md5(r["u"].encode()).hexdigest()[:8];fp=os.path.join(DST,fn)
                    ox=old_url.get(r["u"])
                    if ox and (ox.get("pages") or 0)>0:
                        recs.append(ox);continue
                    if not(os.path.exists(fp) and os.path.getsize(fp)>10000):
                        try:
                            if not dl(r["u"],fp):print("  失败",r["t"][:30]);continue
                        except Exception as e:print("  下载异常",r["t"][:24],str(e)[:40]);continue
                    recs.append({"cat":label,"t":r["t"],"d":r["d"],"u":r["u"],"fn":fn,"pages":pages_of(fp),"size":os.path.getsize(fp)})
                # 翻页
                nums=pg.eval_on_selector_all("a.num","els=>els.map(e=>e.innerText.trim()).filter(t=>/^\\d+$/.test(t))")
                maxn=max([int(x) for x in nums]+[1])
                if page_n>=maxn:break
                page_n+=1
                clicked=pg.evaluate("""(n)=>{
                  const a=[...document.querySelectorAll('a.num')].find(e=>e.innerText.trim()==String(n));
                  if(a){a.click();return true;}return false;
                }""",page_n)
                if not clicked:break
                time.sleep(2)
            print("欧瑞[%s] 累计 %d 个"%(label,len(recs)))
        b.close()
    # 合并：本次发现（按fn）+ 上一版 manifest 全部记录（保留历史URL，不依赖磁盘文件，云端全新环境也不丢）
    merged={r["fn"]:r for r in recs}
    for fn,ox in old_u.items():
        if fn not in merged:merged[fn]=ox
    # 磁盘上若有 manifest 之外的健康文件（本地首次采集场景），补登
    if os.path.isdir(DST):
        for fn in sorted(os.listdir(DST)):
            if not fn.endswith(".pdf") or fn in merged:continue
            fp=os.path.join(DST,fn)
            if os.path.getsize(fp)<10000:continue
            merged[fn]={"cat":"历史抓取","t":"欧瑞说明书 "+fn[3:11],"d":"","u":"","fn":fn,"pages":pages_of(fp),"size":os.path.getsize(fp)}
    out=list(merged.values())
    json.dump(out,open("oura_manifest.json","w",encoding="utf-8"),ensure_ascii=False,indent=1)
    print("欧瑞落盘（本次发现%d，合并历史后%d）"%(len(recs),len(out)))
if __name__=="__main__":run()
