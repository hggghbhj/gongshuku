# -*- coding: utf-8 -*-
"""伟创电气 veichi.cn 采集器（playwright 过阿里云WAF + ?page=N 翻页收集 + 增量下载验证）。
服务端渲染列表，PDF 在 /Uploads/*.pdf 直链。可重复运行、幂等：旧 manifest 按 URL 复用，不重复下载/取页数。
"""
from playwright.sync_api import sync_playwright
from pw_util import chromium_path
import time,os,subprocess,json,hashlib,re
UA="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/120 Safari/537.36"
BASE="https://www.veichi.cn";LIST=BASE+"/service/datadownload";BRAND="veichi";DST="pdfs/"+BRAND
os.makedirs(DST,exist_ok=True)
def pages_of(fp):
    r=subprocess.run(["pdfinfo",fp],capture_output=True,text=True)
    for l in r.stdout.splitlines():
        if l.startswith("Pages:"):return int(l.split()[1])
    return 0
def run():
    # 旧 manifest 按 URL 复用（含页数/fn），云端全新环境也不重下
    old={}
    if os.path.exists("veichi_manifest.json"):
        try:
            for x in json.load(open("veichi_manifest.json",encoding="utf-8")):
                if x.get("u"):old[x["u"]]=x
        except Exception:pass
    recs=[];seen=set()
    with sync_playwright() as p:
        b=p.chromium.launch(headless=True,executable_path=chromium_path(),
                            args=["--no-sandbox","--disable-dev-shm-usage","--ignore-certificate-errors"])
        ctx=b.new_context(user_agent=UA,ignore_https_errors=True)
        pg=ctx.new_page()
        # 过阿里云WAF：访问列表页，等挑战cookie自动写入、PDF链接出现
        pg.goto(LIST,wait_until="domcontentloaded",timeout=30000)
        waf=False
        for _ in range(15):
            time.sleep(2)
            try:
                if pg.eval_on_selector_all("a[href*='.pdf']","e=>e.length")>3:waf=True;break
            except:pass
        if not waf:
            print("伟创 WAF 未过（云端IP被拦）：保留旧 manifest，本次跳过");b.close();return
        print("伟创 WAF 已过，开始翻页收集")
        empty_streak=0
        pn=1
        while pn<=80 and empty_streak<2:
            url=LIST if pn==1 else LIST+"?page=%d"%pn
            try:pg.goto(url,wait_until="domcontentloaded",timeout=25000)
            except:pass
            time.sleep(1.5)
            rows=pg.evaluate("""()=>{
              const out=[];
              document.querySelectorAll("a[href*='.pdf']").forEach(a=>{
                const tr=a.closest('tr')||a.closest('li')||a.closest('div')||a.parentElement;
                const txt=tr?tr.innerText:'';
                const dm=txt.match(/20\\d{2}[-/.]\\d{1,2}[-/.]\\d{1,2}/);
                out.push({u:a.href,t:(a.innerText||'').trim(),d:dm?dm[0]:''});
              });
              return out;
            }""")
            newcnt=0
            for r in rows:
                u=r["u"]
                if not u or u in seen:continue
                seen.add(u);newcnt+=1
                fn="vc_%s.pdf"%hashlib.md5(u.encode()).hexdigest()[:8];fp=os.path.join(DST,fn)
                ox=old.get(u)
                if ox and (ox.get("pages") or 0)>0:
                    recs.append(ox);continue
                if not(os.path.exists(fp) and os.path.getsize(fp)>10000):
                    try:
                        resp=ctx.request.get(u,headers={"Referer":LIST})
                        raw=resp.body()
                        if resp.status!=200 or raw[:4]!=b"%PDF":
                            print("  失败",r["t"][:24],resp.status);continue
                        open(fp,"wb").write(raw)
                    except Exception as e:
                        print("  下载异常",r["t"][:24],str(e)[:40]);continue
                recs.append({"t":r["t"],"d":r["d"],"u":u,"fn":fn,"pages":pages_of(fp),"size":os.path.getsize(fp)})
            if newcnt==0:empty_streak+=1
            else:empty_streak=0
            print("  第%d页 新%d 累计%d"%(pn,newcnt,len(recs)))
            pn+=1
        b.close()
    # 合并：本次 + 旧 manifest 全部（保留历史，不依赖磁盘pdfs）
    merged={r["u"]:r for r in recs}
    for u,ox in old.items():
        if u not in merged:merged[u]=ox
    out=list(merged.values())
    json.dump(out,open("veichi_manifest.json","w",encoding="utf-8"),ensure_ascii=False,indent=1)
    print("伟创落盘 %d 个（本次发现%d，合并历史后%d）"%(len(recs),len(recs),len(out)))
if __name__=="__main__":run()
