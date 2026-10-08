#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""正泰电器 electric.chint.com 采集器 - playwright逐页点击下载"""
import os, re, json, time, subprocess
from pathlib import Path
from playwright.sync_api import sync_playwright

BASE = Path(__file__).parent
PDF_DIR = BASE / "pdfs" / "chint"
PDF_DIR.mkdir(parents=True, exist_ok=True)
MANIFEST = BASE / "chint_manifest.json"
BASE_URL = "http://electric.chint.com"

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
        existing = {x["name"] for x in manifest}
    print("正泰电器 开始采集(playwright逐页下载)...")
    
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
        for page_num in range(1, 8):  # 抓前7页
            url = f"{BASE_URL}/service/download/page/{page_num}.html"
            print(f"\n=== 第{page_num}页: {url} ===")
            try:
                page.goto(url, timeout=30000, wait_until="domcontentloaded")
                time.sleep(2)
                # 获取当前页所有下载按钮的数量
                count = page.evaluate("() => document.querySelectorAll('a[download]').length")
                print(f"  发现 {count} 个下载按钮")
                # 逐个点击下载
                for i in range(count):
                    # 重新获取下载按钮（因为页面可能变化）
                    btn_info = page.evaluate(f"""() => {{
                        const btns = document.querySelectorAll('a[download]');
                        if (btns[{i}]) {{
                            return {{name: btns[{i}].getAttribute('download'), exists: true}};
                        }}
                        return {{exists: false}};
                    }}""")
                    if not btn_info["exists"]:
                        continue
                    name = btn_info["name"]
                    if not name or not name.endswith('.pdf'):
                        continue
                    if name in existing:
                        print(f"  跳过(已存在): {name[:40]}")
                        continue
                    print(f"  下载: {name[:50]}")
                    try:
                        # 用class定位第i个下载按钮
                        btns = page.locator('a.fcc.gdt-more.ft14')
                        if btns.count() > i:
                            with page.expect_download(timeout=20000) as download_info:
                                btns.nth(i).click(timeout=15000)
                        else:
                            continue
                        download = download_info.value
                        fname = re.sub(r'[\\/:*?"<>|]', "_", name)[:100]
                        save_path = PDF_DIR / fname
                        download.save_as(str(save_path))
                        if save_path.exists() and save_path.stat().st_size > 2000:
                            data = save_path.read_bytes()
                            if data.startswith(b"%PDF"):
                                pages = get_pages_count(save_path)
                                if pages > 0:
                                    manifest.append({
                                        "name": name.replace(".pdf", ""),
                                        "url": download.url,
                                        "file": f"pdfs/chint/{fname}",
                                        "size": len(data),
                                        "pages": pages
                                    })
                                    existing.add(name)
                                    new_count += 1
                                    print(f"    + 成功 ({pages}页, {len(data)//1024}KB)")
                                    MANIFEST.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
                                    continue
                            print(f"    - 非PDF，删除")
                            save_path.unlink(missing_ok=True)
                        else:
                            print(f"    - 文件太小")
                            save_path.unlink(missing_ok=True)
                    except Exception as e:
                        print(f"    - 失败: {str(e)[:60]}")
                        continue
            except Exception as e:
                print(f"  页面访问失败: {e}")
                break
        
        browser.close()
    
    MANIFEST.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"\n正泰电器: 新增{new_count}, 累计{len(manifest)}")

if __name__ == "__main__":
    main()
