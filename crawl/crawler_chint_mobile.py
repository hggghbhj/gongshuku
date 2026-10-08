#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""正泰电器 m.chint.com 移动站采集器 - 断路器/接触器说明书"""
import os, re, json, subprocess, time
from pathlib import Path

BASE = Path(__file__).parent
PDF_DIR = BASE / "pdfs" / "chint"
PDF_DIR.mkdir(parents=True, exist_ok=True)
MANIFEST = BASE / "chint_manifest.json"
BASE_URL = "http://m.chint.com"

def fetch(url, timeout=30):
    try:
        r = subprocess.run(["curl","-s","-L","--max-time",str(timeout),
            "-A","Mozilla/5.0 (iPhone; CPU iPhone OS 15_0 like Mac OS X) AppleWebKit/605.1.15",
            "-e",BASE_URL+"/",url], capture_output=True, timeout=timeout+5)
        return r.stdout
    except: return b""

def get_pages_count(fp):
    try:
        r = subprocess.run(["pdfinfo", str(fp)], capture_output=True, text=True, timeout=15)
        for l in r.stdout.splitlines():
            if l.startswith("Pages:"):
                return int(l.split()[1])
    except: pass
    return 0

def main():
    existing = set()
    manifest = []
    if MANIFEST.exists():
        manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
        existing = {x["url"] for x in manifest}
    print("正泰电器(移动站) 开始采集...")
    
    # 产品分类列表 (classid, classtwoid, proid)
    # 先从首页获取所有分类
    all_pdfs = []
    # 已知的分类范围，遍历常见的proid
    for proid in range(1, 60):
        url = f"{BASE_URL}/kunlun/m/index.php?m=product&a=down&classid=9&classtwoid=19&proid={proid}"
        html = fetch(url, timeout=15).decode("utf-8", errors="ignore")
        # 提取PDF链接
        pdfs = re.findall(r'rel="([^"]*\.pdf)"[^>]*>([^<]*)', html)
        if pdfs:
            print(f"  proid={proid}: {len(pdfs)} 个PDF")
            for rel, name in pdfs:
                pdf_url = BASE_URL + rel if rel.startswith("/") else rel
                all_pdfs.append((pdf_url, name.strip()))
        time.sleep(0.2)
    
    # 也试试其他classid
    for classid in [7, 8, 9, 10, 11, 12]:
        for classtwoid in range(15, 25):
            url = f"{BASE_URL}/kunlun/m/index.php?m=product&a=down&classid={classid}&classtwoid={classtwoid}&proid=1"
            html = fetch(url, timeout=10).decode("utf-8", errors="ignore")
            pdfs = re.findall(r'rel="([^"]*\.pdf)"[^>]*>([^<]*)', html)
            if pdfs:
                print(f"  classid={classid}, classtwoid={classtwoid}: {len(pdfs)} 个PDF")
                for rel, name in pdfs:
                    pdf_url = BASE_URL + rel if rel.startswith("/") else rel
                    all_pdfs.append((pdf_url, name.strip()))
            time.sleep(0.1)
    
    # 去重
    seen = set()
    uniq = []
    for url, name in all_pdfs:
        if url not in seen:
            seen.add(url)
            uniq.append((url, name))
    print(f"  去重后共 {len(uniq)} 个PDF")
    
    # 下载
    new_count = 0
    for url, name in uniq:
        if url in existing:
            continue
        fname = re.sub(r'[\\/:*?"<>|]', "_", name if name else url.split("/")[-1])[:100]
        if not fname.lower().endswith('.pdf'):
            fname += ".pdf"
        fp = PDF_DIR / fname
        data = fetch(url, timeout=60)
        if not data or not data.startswith(b"%PDF"):
            print(f"  跳过(非PDF): {name[:40]}")
            continue
        if len(data) < 2000:
            print(f"  跳过(太小): {name[:40]}")
            continue
        fp.write_bytes(data)
        pages = get_pages_count(fp)
        if pages == 0:
            print(f"  跳过(0页): {name[:40]}")
            fp.unlink(missing_ok=True)
            continue
        manifest.append({"name": name.replace(".pdf","") if name else fname, "url": url, "file": f"pdfs/chint/{fname}", "size": len(data), "pages": pages})
        existing.add(url)
        new_count += 1
        MANIFEST.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"  + {name[:40]} ({pages}页, {len(data)//1024}KB)")
    
    MANIFEST.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"\n正泰电器: 新增{new_count}, 累计{len(manifest)}")

if __name__ == "__main__":
    main()
