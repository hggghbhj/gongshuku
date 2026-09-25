#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""亚德客 airtac.com 采集器 - 气动元件说明书"""
import os, re, json, subprocess, time
from pathlib import Path

BASE = Path(__file__).parent
PDF_DIR = BASE / "pdfs" / "airtac"
PDF_DIR.mkdir(parents=True, exist_ok=True)
MANIFEST = BASE / "airtac_manifest.json"
BASE_URL = "https://www.airtac.com"
PDF_BASE = "https://www2.airtac.com"

def fetch(url, timeout=30):
    import urllib.parse
    parsed = urllib.parse.urlparse(url)
    if any(ord(ch) > 127 for ch in parsed.path):
        url = urllib.parse.urlunparse(parsed._replace(path=urllib.parse.quote(parsed.path)))
    try:
        r = subprocess.run(["curl","-s","-L","--max-time",str(timeout),
            "-A","Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
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
    print("亚德客 开始采集...")
    # 1. 抓取下载页，提取所有产品分类链接
    html = fetch(BASE_URL + "/download", timeout=20).decode("utf-8", errors="ignore")
    cat_links = re.findall(r'href="(pro\.aspx\?c_kind=[^"]+)"', html)
    cat_links = [x.strip() for x in dict.fromkeys(cat_links)]  # 去重
    print(f"  发现 {len(cat_links)} 个产品分类")
    # 2. 逐个访问产品页，提取PDF链接
    all_pdfs = []
    for i, cat in enumerate(cat_links[:30]):  # 最多抓30个分类
        url = BASE_URL + "/" + cat
        html2 = fetch(url, timeout=15).decode("utf-8", errors="ignore")
        pdfs = re.findall(r'href="(https?://[^" ]+\.[Pp][Dd][Ff])"', html2)
        if pdfs:
            print(f"  分类{i+1}: {len(pdfs)} 个PDF")
            all_pdfs.extend(pdfs)
        time.sleep(0.3)
    # 去重
    all_pdfs = list(dict.fromkeys(all_pdfs))
    print(f"  去重后共 {len(all_pdfs)} 个PDF")
    # 3. 下载PDF
    bad_urls = set()
    BAD_FILE = BASE / "airtac_bad_urls.json"
    if BAD_FILE.exists():
        bad_urls = set(json.loads(BAD_FILE.read_text(encoding="utf-8")))
    new_count = 0
    for url in all_pdfs:
        if url in existing or url in bad_urls:
            continue
        fname = url.split("/")[-1]
        fname = re.sub(r'[\\/:*?"<>|]', "_", fname)[:100]
        fp = PDF_DIR / fname
        data = fetch(url, timeout=60)
        if not data or not data.startswith(b"%PDF"):
            print(f"  跳过(非PDF): {fname}")
            bad_urls.add(url)
            continue
        if len(data) < 2000:
            print(f"  跳过(太小): {fname}")
            bad_urls.add(url)
            continue
        fp.write_bytes(data)
        pages = get_pages_count(fp)
        if pages == 0:
            print(f"  跳过(0页): {fname}")
            fp.unlink(missing_ok=True)
            bad_urls.add(url)
            continue
        name = fname.replace(".PDF","").replace(".pdf","")
        manifest.append({"name": name, "url": url, "file": f"pdfs/airtac/{fname}", "size": len(data), "pages": pages})
        existing.add(url)
        new_count += 1
        MANIFEST.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"  + {name} ({pages}页, {len(data)//1024}KB)")
    BAD_FILE.write_text(json.dumps(list(bad_urls), ensure_ascii=False, indent=2), encoding="utf-8")
    MANIFEST.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"\n亚德客: 新增{new_count}, 累计{len(manifest)}, 坏链接{len(bad_urls)}个")

if __name__ == "__main__":
    main()
