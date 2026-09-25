#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""上海亚泰仪表 采集器"""
import os, re, json, subprocess, hashlib, urllib.parse
from pathlib import Path

BASE = Path(__file__).parent
PDF_DIR = BASE / "pdfs" / "yatai"
PDF_DIR.mkdir(parents=True, exist_ok=True)
MANIFEST = BASE / "yatai_manifest.json"
BASE_URL = "http://www.yatai.sh.cn"

def fetch(url, timeout=30):
    try:
        r = subprocess.run(["curl","-s","-L","--max-time",str(timeout),
            "-A","Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
            url], capture_output=True, timeout=timeout+5)
        return r.stdout
    except: return b""

def get_pages(fp):
    try:
        from pypdf import PdfReader
        return len(PdfReader(str(fp)).pages)
    except:
        try:
            r = subprocess.run(["pdfinfo",str(fp)],capture_output=True,text=True,timeout=10)
            m = re.search(r"Pages:\s+(\d+)", r.stdout)
            return int(m.group(1)) if m else 0
        except: return 0

def main():
    manifest = []
    if MANIFEST.exists():
        manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    existing = {x["url"] for x in manifest}
    new_count = 0

    # 产品说明书页（多页）
    for page in range(1, 6):
        url = f"{BASE_URL}/ProductSpecifications/index.aspx?page={page}" if page > 1 else f"{BASE_URL}/ProductSpecifications/index.aspx"
        html = fetch(url).decode("utf-8", errors="ignore")
        if not html:
            print(f"  页{page} 获取失败")
            continue
        # 提取 dt 块
        blocks = re.findall(r'<dt class="clearfix dt">(.*?)</dt>', html, re.S)
        print(f"  页{page}: {len(blocks)}个条目")
        for block in blocks:
            m = re.search(r'<a href="([^"]+\.pdf)"[^>]*>([^<]+)</a>', block)
            if not m: continue
            pdf_path, name = m.group(1), m.group(2).strip()
            pdf_url = BASE_URL + pdf_path if pdf_path.startswith("/") else pdf_path
            if pdf_url in existing: continue
            # 下载
            fname = re.sub(r'[\\/:*?"<>|]', "_", name)[:80] + ".pdf"
            fp = PDF_DIR / fname
            data = fetch(pdf_url, timeout=60)
            if not data or not data.startswith(b"%PDF"):
                print(f"  跳过(非PDF): {name}")
                continue
            if len(data) < 1000:
                print(f"  跳过(太小): {name}")
                continue
            fp.write_bytes(data)
            pages = get_pages(fp)
            if pages == 0:
                print(f"  跳过(0页): {name}")
                fp.unlink(missing_ok=True)
                continue
            manifest.append({"name":name,"url":pdf_url,"file":f"pdfs/yatai/{fname}","size":len(data),"pages":pages})
            existing.add(pdf_url)
            new_count += 1
            print(f"  + {name} ({pages}页, {len(data)//1024}KB)")

    MANIFEST.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"\n亚泰: 新增{new_count}, 累计{len(manifest)}")

if __name__ == "__main__":
    main()
