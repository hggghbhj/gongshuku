# -*- coding: utf-8 -*-
"""欧姆龙OMRON说明书采集器
欧姆龙中国资料下载中心，提取PDF直链。
"""
import os,json,time,re,urllib.request,ssl
from pathlib import Path

BASE=Path(__file__).parent
PDF_DIR=BASE/"pdfs"/"omron"
MANIFEST=BASE/"omron_manifest.json"
PDF_DIR.mkdir(parents=True,exist_ok=True)

UA="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0 Safari/537.36"
ctx=ssl.create_default_context(); ctx.check_hostname=False; ctx.verify_mode=ssl.CERT_NONE

def fetch(url,timeout=20):
    req=urllib.request.Request(url,headers={"User-Agent":UA,"Accept":"*/*"})
    with urllib.request.urlopen(req,timeout=timeout,context=ctx) as r:
        return r.read()

def load_manifest():
    if MANIFEST.exists():
        return json.loads(MANIFEST.read_text(encoding="utf-8"))
    return {}

def save_manifest(m):
    MANIFEST.write_text(json.dumps(m,ensure_ascii=False,indent=1),encoding="utf-8")

def pdf_ok(fp):
    try:
        return fp.stat().st_size>2000 and open(fp,"rb").read(5)==b"%PDF-"
    except:return False

def main():
    m=load_manifest()
    new=0
    # 欧姆龙中国下载页面
    list_urls=[
        "https://www.omron.com.cn/ec/products/category",
        "https://www.omron.com.cn/ec/support/manual/",
        "https://www.omron.com.cn/ec/support/",
    ]
    for lu in list_urls:
        try:
            html=fetch(lu,timeout=15).decode("utf-8","ignore")
            pdfs=re.findall(r'href="([^"]+\.pdf)"',html,re.I)
            for p in pdfs:
                if p.startswith("/"):
                    p="https://www.omron.com.cn"+p
                if not p.startswith("http"):continue
                fn=re.sub(r'[^\w\-.]','_',p.split("/")[-1])[:80]
                if not fn.endswith(".pdf"):fn+=".pdf"
                fp=PDF_DIR/fn
                if fp.exists() and pdf_ok(fp):continue
                try:
                    data=fetch(p,timeout=30)
                    if len(data)<2000 or data[:5]!=b"%PDF-":continue
                    fp.write_bytes(data)
                    m[fn]={"url":p,"ok":True,"size":len(data)}
                    new+=1;time.sleep(0.3)
                except:pass
        except Exception as e:
            print(f"  欧姆龙列表失败 {lu}: {e}")
    save_manifest(m)
    print(f"欧姆龙: 新增{new} 总{len(m)}")

if __name__=="__main__":
    main()
