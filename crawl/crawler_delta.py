# -*- coding: utf-8 -*-
"""台达电子说明书采集器（playwright版）
下载中心: https://downloadcenter.delta-china.com.cn/
"""
import os,json,time,re,urllib.request,ssl
from pathlib import Path
from playwright.sync_api import sync_playwright

BASE=Path(__file__).parent
PDF_DIR=BASE/"pdfs"/"delta"
MANIFEST=BASE/"delta_manifest.json"
PDF_DIR.mkdir(parents=True,exist_ok=True)

UA="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0 Safari/537.36"
ctx=ssl.create_default_context(); ctx.check_hostname=False; ctx.verify_mode=ssl.CERT_NONE

def fetch(url,timeout=30,referer=None):
    h={"User-Agent":UA}
    if referer:h["Referer"]=referer
    req=urllib.request.Request(url,headers=h)
    with urllib.request.urlopen(req,timeout=timeout,context=ctx) as r:
        return r.read()

def load_manifest():
    return json.loads(MANIFEST.read_text(encoding="utf-8")) if MANIFEST.exists() else {}

def save_manifest(m):
    MANIFEST.write_text(json.dumps(m,ensure_ascii=False,indent=1),encoding="utf-8")

def pdf_ok(fp):
    try:return fp.stat().st_size>2000 and open(fp,"rb").read(5)==b"%PDF-"
    except:return False

def main():
    m=load_manifest(); new=0; fail=0
    pdf_urls=set()
    with sync_playwright() as p:
        br=p.chromium.launch(executable_path="/usr/local/bin/chromium",
            args=["--no-sandbox","--disable-dev-shm-usage","--ignore-certificate-errors"])
        pg=br.new_page(user_agent=UA)
        # 工业自动化分类
        urls=[
            "https://downloadcenter.delta-china.com.cn/zh-CN/DownloadCenter?CID=06",
            "https://downloadcenter.delta-china.com.cn/DownloadCenter?v=1",
        ]
        for u in urls:
            try:
                pg.goto(u,timeout=30000,wait_until="networkidle")
                time.sleep(3)
                # 滚动加载
                for _ in range(5):
                    pg.mouse.wheel(0,3000);time.sleep(1)
                links=pg.eval_on_selector_all("a[href*='.pdf'], a[href*='download']",
                    "els=>els.map(e=>e.href)")
                for l in links:
                    if ".pdf" in l.lower() or "download" in l.lower():
                        pdf_urls.add(l)
            except Exception as e:
                print(f"  台达页面失败 {u}: {e}")
        br.close()
    print(f"  台达发现 {len(pdf_urls)} 个链接")
    for p in pdf_urls:
        try:
            fn="delta_DID"+re.search(r'DID=(\d+)',p).group(1) if 'DID=' in p else re.sub(r'[^\w\-.]','_',p.split("/")[-1].split("?")[0])[:60]
            if not fn.endswith(".pdf"):fn+=".pdf"
            fp=PDF_DIR/fn
            if fp.exists() and pdf_ok(fp):continue
            # counter.aspx会302跳转到实际PDF
            req=urllib.request.Request(p,headers={"User-Agent":UA,"Referer":"https://downloadcenter.delta-china.com.cn/"})
            with urllib.request.urlopen(req,timeout=30,context=ctx) as r:
                data=r.read()
            if len(data)<2000 or data[:5]!=b"%PDF-":continue
            fp.write_bytes(data)
            m[fn]={"url":p,"ok":True,"size":len(data)}
            new+=1;time.sleep(0.3)
        except:fail+=1
    save_manifest(m)
    print(f"台达: 新增{new} 总{len(m)} 失败{fail}")

if __name__=="__main__":
    main()
