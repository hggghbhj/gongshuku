#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""亚德客 airtac 采集器 - 气动元件说明书
产品PDF在 www2.airtac.com/upload/，中文URL需编码
"""
import os, re, json, subprocess, time, urllib.request, urllib.parse, ssl
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed

BASE = Path(__file__).parent
PDF_DIR = BASE / "pdfs" / "airtac"
PDF_DIR.mkdir(parents=True, exist_ok=True)
MANIFEST = BASE / "airtac_manifest.json"
UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
ctx = ssl.create_default_context(); ctx.check_hostname=False; ctx.verify_mode=ssl.CERT_NONE

def enc_url(u):
    p=urllib.parse.urlparse(u)
    return urllib.parse.urlunparse(p._replace(path=urllib.parse.quote(p.path)))

def fetch(url, timeout=20, referer=None):
    h={"User-Agent":UA}
    if referer:h["Referer"]=referer
    req=urllib.request.Request(enc_url(url),headers=h)
    with urllib.request.urlopen(req,timeout=timeout,context=ctx) as r:
        return r.read()

def get_pages(fp):
    try:
        r=subprocess.run(["pdfinfo",str(fp)],capture_output=True,text=True,timeout=15)
        for l in r.stdout.splitlines():
            if l.startswith("Pages:"):return int(l.split()[1])
    except:pass
    return 0

def collect_product_links():
    """从多个分类入口收集产品页面链接"""
    cat_pages=[
        "https://wwww.airtac.com/pro_xz2.aspx?c_kind=4&c_kind2=131",
        "https://wwww.airtac.com/pro_xz1.aspx?c_kind=4&c_kind2=131",
    ]
    prods=set()
    for cp in cat_pages:
        try:
            html=fetch(cp,timeout=20).decode("utf-8","ignore")
            for m in re.findall(r'href="((?:pro|pro2)\.aspx\?[^"]+)"',html):
                prods.add("https://wwww.airtac.com/"+m)
        except Exception as e:
            print("  分类页失败:",e)
    return prods

def extract_pdfs(prod_url):
    """访问产品页提取PDF链接"""
    try:
        html=fetch(prod_url,timeout=15,referer="https://wwww.airtac.com/").decode("utf-8","ignore")
        return set(re.findall(r'href="(https?://[^" ]+\.[Pp][Dd][Ff])"',html))
    except:return set()

def load_manifest():
    if MANIFEST.exists():
        data=json.loads(MANIFEST.read_text(encoding="utf-8"))
        if isinstance(data,list):return data
    return []

def save_manifest(m):
    MANIFEST.write_text(json.dumps(m,ensure_ascii=False,indent=1),encoding="utf-8")

def main():
    manifest=load_manifest()
    existing={x["url"] for x in manifest}
    print("亚德客 开始采集...")
    # 1. 收集产品链接
    prods=collect_product_links()
    print(f"  发现 {len(prods)} 个产品页")
    # 2. 并行提取PDF链接
    all_pdfs=set()
    with ThreadPoolExecutor(max_workers=6) as ex:
        futs=[ex.submit(extract_pdfs,u) for u in prods]
        for f in as_completed(futs):
            all_pdfs.update(f.result())
    print(f"  共发现 {len(all_pdfs)} 个PDF链接")
    # 3. 下载
    new_count=0
    for url in sorted(all_pdfs):
        if url in existing:continue
        fname=re.sub(r'[\\/:*?"<>|]','_',url.split("/")[-1])[:100]
        fp=PDF_DIR/fname
        try:
            data=fetch(url,timeout=40,referer="https://wwww.airtac.com/")
            if not data or not data.startswith(b"%PDF") or len(data)<2000:
                continue
            fp.write_bytes(data)
            pages=get_pages(fp)
            if pages==0:
                fp.unlink(missing_ok=True);continue
            name=fname.rsplit(".",1)[0]
            manifest.append({"name":name,"url":url,"file":f"pdfs/airtac/{fname}","size":len(data),"pages":pages})
            existing.add(url);new_count+=1
            if new_count%10==0:print(f"  已下载 {new_count}...")
        except Exception as e:
            pass
    save_manifest(manifest)
    print(f"亚德客: 新增{new_count}, 累计{len(manifest)}")

if __name__=="__main__":
    main()
