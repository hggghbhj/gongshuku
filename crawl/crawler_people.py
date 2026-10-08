#!/usr/bin/env python3
"""人民电器 chinapeople.com 采集器 - 断路器/接触器说明书"""
import os, re, json, time, hashlib
import urllib.request

BASE = "https://www.chinapeople.com"
OUT = os.path.join(os.path.dirname(__file__), "..", "pdfs", "people")
MANIFEST = os.path.join(os.path.dirname(__file__), "people_manifest.json")
PAGES = [148, 320, 322, 172]  # 框架断路器/塑壳/漏电/小型

def fetch(url, timeout=20):
    req = urllib.request.Request(url, headers={
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
        "Referer": BASE + "/",
    })
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return r.read()

def get_list():
    """从各说明书页提取PDF列表"""
    items = []
    for page in PAGES:
        try:
            html = fetch(f"{BASE}/productsms_{page}.html", timeout=15).decode("utf-8", errors="ignore")
        except Exception as e:
            print(f"  page={page} 获取失败: {e}")
            continue
        # 找表格行
        rows = re.findall(r'<tr[^>]*>(.*?)</tr>', html, re.S)
        for row in rows:
            pdf = re.search(r'href=["\'](chanpin/[^"\']*\.pdf)["\']', row, re.I)
            if not pdf:
                continue
            url = BASE + "/" + pdf.group(1)
            text = re.sub(r'<[^>]+>', ' ', row).strip()
            text = re.sub(r'\s+', ' ', text)
            name = re.sub(r'\s*点击下载.*$', '', text).strip()
            name = re.sub(r'\s*下载.*$', '', name).strip()
            if not name:
                name = os.path.basename(url)
            items.append({"name": name, "url": url})
        time.sleep(0.3)
    # 去重
    seen = set()
    unique = []
    for it in items:
        if it["url"] not in seen:
            seen.add(it["url"])
            unique.append(it)
    return unique

def main():
    os.makedirs(OUT, exist_ok=True)
    manifest = []
    if os.path.exists(MANIFEST):
        with open(MANIFEST, "r", encoding="utf-8") as f:
            manifest = json.load(f)
    existing = {m["url"] for m in manifest}

    items = get_list()
    print(f"人民电器: 发现 {len(items)} 个PDF")
    new_count = 0
    for it in items:
        if it["url"] in existing:
            continue
        fname = hashlib.md5(it["url"].encode()).hexdigest()[:12] + ".pdf"
        fpath = os.path.join(OUT, fname)
        try:
            data = fetch(it["url"], timeout=15)
            if not data.startswith(b"%PDF"):
                print(f"  跳过(非PDF): {it['name'][:40]}")
                continue
            with open(fpath, "wb") as f:
                f.write(data)
            # 页数
            pages = 0
            try:
                import pypdf
                pages = len(pypdf.PdfReader(fpath).pages)
            except:
                pass
            manifest.append({
                "name": it["name"],
                "url": it["url"],
                "file": fname,
                "size": len(data),
                "pages": pages,
                "type": "使用说明书",
            })
            new_count += 1
            # 增量保存
            with open(MANIFEST, "w", encoding="utf-8") as f:
                json.dump(manifest, f, ensure_ascii=False, indent=2)
            print(f"  + {it['name'][:45]} ({pages}页)")
        except Exception as e:
            print(f"  失败: {it['name'][:40]} - {e}")
        time.sleep(0.2)

    with open(MANIFEST, "w", encoding="utf-8") as f:
        json.dump(manifest, f, ensure_ascii=False, indent=2)
    print(f"人民电器完成: 新增{new_count}, 累计{len(manifest)}")

if __name__ == "__main__":
    main()
