#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""阳明电机 fotek.com.tw 采集器 - 定时器/计数器/温控器/传感器说明书"""
import os, re, json, subprocess, hashlib
from pathlib import Path

BASE = Path(__file__).parent
PDF_DIR = BASE / "pdfs" / "fotek"
PDF_DIR.mkdir(parents=True, exist_ok=True)
MANIFEST = BASE / "fotek_manifest.json"
LIST_URL = "https://www.fotek.com.tw/zh-cn/download"
BASE_URL = "https://www.fotek.com.tw"

def fetch(url, timeout=30):
    try:
        r = subprocess.run(["curl","-s","-L","--max-time",str(timeout),
            "-A","Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
            "-e",BASE_URL+"/",url], capture_output=True, timeout=timeout+5)
        return r.stdout
    except: return b""

def get_pages(html):
    """提取分页链接"""
    pages = set()
    for m in re.finditer(r'href="([^"]*download[^"]*page[^"]*)"', html, re.I):
        pages.add(m.group(1))
    return sorted(pages)

def get_pdf_links(html):
    """从页面提取PDF下载链接和名称"""
    items = []
    for m in re.finditer(r'href="(https://www\.fotek\.com\.tw/zh-cn/download/\d+)"[^>]*>([^<]+)</a>', html):
        url, name = m.group(1), m.group(2).strip()
        if name.lower().endswith('.pdf'):
            items.append((url, name))
    return items

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
    print("阳明电机 开始采集...")
    # 获取列表页
    html = fetch(LIST_URL, timeout=20).decode("utf-8", errors="ignore")
    items = get_pdf_links(html)
    print(f"  列表页发现 {len(items)} 个PDF")
    # 检查分页
    pages = get_pages(html)
    for p in pages[:3]:  # 最多抓3页
        url = p if p.startswith("http") else BASE_URL + p
        html2 = fetch(url, timeout=20).decode("utf-8", errors="ignore")
        new_items = get_pdf_links(html2)
        print(f"  分页 {p}: {len(new_items)} 个PDF")
        items.extend(new_items)
    # 去重
    seen = set()
    uniq = []
    for url, name in items:
        if url not in seen:
            seen.add(url)
            uniq.append((url, name))
    print(f"  去重后共 {len(uniq)} 个PDF")
    new_count = 0
    for url, name in uniq:
        if url in existing:
            continue
        fname = re.sub(r'[\\/:*?"<>|]', "_", name)[:80]
        if not fname.lower().endswith('.pdf'):
            fname += ".pdf"
        fp = PDF_DIR / fname
        data = fetch(url, timeout=60)
        if not data or not data.startswith(b"%PDF"):
            print(f"  跳过(非PDF): {name}")
            continue
        if len(data) < 2000:
            print(f"  跳过(太小): {name}")
            continue
        fp.write_bytes(data)
        pages = get_pages_count(fp)
        if pages == 0:
            print(f"  跳过(0页): {name}")
            fp.unlink(missing_ok=True)
            continue
        manifest.append({"name": name.replace(".pdf",""), "url": url, "file": f"pdfs/fotek/{fname}", "size": len(data), "pages": pages})
        existing.add(url)
        new_count += 1
        print(f"  + {name} ({pages}页, {len(data)//1024}KB)")
    MANIFEST.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"\n阳明电机: 新增{new_count}, 累计{len(manifest)}")

if __name__ == "__main__":
    main()
