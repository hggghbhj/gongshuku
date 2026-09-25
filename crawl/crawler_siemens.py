#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""西门子 Siemens 采集器 - playwright访问文档页获取PDF链接后下载"""
import os, re, json, time, subprocess, requests
from pathlib import Path
from playwright.sync_api import sync_playwright

BASE = Path(__file__).parent
PDF_DIR = BASE / "pdfs" / "siemens"
PDF_DIR.mkdir(parents=True, exist_ok=True)
MANIFEST = BASE / "siemens_manifest.json"

# 已知的西门子热门文档ID列表（中文手册）
KNOWN_DOCS = [
    ("109759862", "SIMATIC S7-1200 可编程控制器系统手册"),
    ("109741593", "SIMATIC S7-1200 Programmable controller"),
    ("109983341", "S7-1200 固件更新 V4.7"),
    ("109772940", "SIMATIC S7-1200 Automatisierungssystem"),
    ("109971987", "Sistema de automação S7-1200"),
    ("81318674", "Programming Guidelines for S7-1200/S7-1500"),
    ("109792862", "S7-1200 Handling library"),
    ("39710145", "SIMATIC S7-1200 easy book"),
]

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
    print("西门子 开始采集(playwright)...")
    
    with sync_playwright() as p:
        browser = p.chromium.launch(
            executable_path="/usr/local/bin/chromium",
            args=["--no-sandbox", "--disable-dev-shm-usage", "--ignore-certificate-errors"]
        )
        context = browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            accept_downloads=True
        )
        page = context.new_page()
        
        new_count = 0
        for doc_id, doc_name in KNOWN_DOCS:
            url = f"https://support.industry.siemens.com/cs/document/{doc_id}/"
            print(f"\n  文档 {doc_id}: {doc_name}")
            try:
                page.goto(url, timeout=45000, wait_until="domcontentloaded")
                time.sleep(12)
                # 用简单正则从HTML提取PDF链接
                html = page.content()
                pdf_links = list(dict.fromkeys(re.findall(r'https://[^"\s]+\.pdf', html, re.I)))
                print(f"    找到 {len(pdf_links)} 个PDF链接")
                # 下载PDF
                for pdf_url in pdf_links:
                    if pdf_url in existing:
                        print(f"    跳过(已存在)")
                        continue
                    try:
                        # 用playwright的request下载（带cookie）
                        response = page.request.get(pdf_url, timeout=60000)
                        if response.ok:
                            data = response.body()
                            if data.startswith(b"%PDF") and len(data) > 2000:
                                fname = pdf_url.split("/")[-1].split("?")[0]
                                fname = re.sub(r'[\\/:*?"<>|]', "_", fname)[:100]
                                fp = PDF_DIR / fname
                                fp.write_bytes(data)
                                pages = get_pages_count(fp)
                                if pages > 0:
                                    name = fname.replace(".pdf","").replace(".PDF","")
                                    manifest.append({
                                        "name": name,
                                        "url": pdf_url,
                                        "file": f"pdfs/siemens/{fname}",
                                        "size": len(data),
                                        "pages": pages
                                    })
                                    existing.add(pdf_url)
                                    new_count += 1
                                    print(f"    + 成功: {name} ({pages}页, {len(data)//1024}KB)")
                                    MANIFEST.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
                                else:
                                    print(f"    - 0页，删除")
                                    fp.unlink(missing_ok=True)
                            else:
                                print(f"    - 非PDF或太小")
                        else:
                            print(f"    - HTTP {response.status}")
                    except Exception as e:
                        print(f"    - 下载失败: {str(e)[:60]}")
            except Exception as e:
                print(f"    页面访问失败: {str(e)[:60]}")
        
        browser.close()
    
    MANIFEST.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"\n西门子: 新增{new_count}, 累计{len(manifest)}")

if __name__ == "__main__":
    main()
