#!/usr/bin/env python3
"""上润 wideplus.com 采集器 - 压力变送器/液位计/数显仪表说明书"""
import os, re, json, time, hashlib
import urllib.request, urllib.parse

BASE = "https://www.wideplus.com"
YUN = "https://yun.wideplus.com"
OUT = os.path.join(os.path.dirname(__file__), "..", "pdfs", "wideplus")
MANIFEST = os.path.join(os.path.dirname(__file__), "wideplus_manifest.json")
CATS = [2, 3, 4, 8, 9, 10, 11, 12, 13]

def fetch(url, timeout=20):
    req = urllib.request.Request(url, headers={
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
        "Referer": BASE + "/",
    })
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return r.read()

def get_list():
    """从各分类页提取PDF列表"""
    items = []
    for cat in CATS:
        try:
            html = fetch(f"{BASE}/companyfile/{cat}/", timeout=15).decode("utf-8", errors="ignore")
        except Exception as e:
            print(f"  cat={cat} 列表获取失败: {e}")
            continue
        pdfs = re.findall(r'href=["\'](https://yun\.wideplus\.com/[^"\']*\.pdf)["\']', html, re.I)
        for url in pdfs:
            name = urllib.parse.unquote(os.path.basename(url))
            name = re.sub(r'\.pdf$', '', name, flags=re.I)
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
    print(f"上润: 发现 {len(items)} 个PDF")
    new_count = 0
    for it in items:
        if it["url"] in existing:
            continue
        fname = hashlib.md5(it["url"].encode()).hexdigest()[:12] + ".pdf"
        fpath = os.path.join(OUT, fname)
        try:
            # 中文URL编码
            encoded_url = urllib.parse.quote(it["url"], safe="/:()（）《》_-.,")
            data = fetch(encoded_url, timeout=30)
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
                "type": "使用手册",
            })
            new_count += 1
            print(f"  + {it['name'][:45]} ({pages}页)")
        except Exception as e:
            print(f"  失败: {it['name'][:40]} - {e}")
        time.sleep(0.3)

    with open(MANIFEST, "w", encoding="utf-8") as f:
        json.dump(manifest, f, ensure_ascii=False, indent=2)
    print(f"上润完成: 新增{new_count}, 累计{len(manifest)}")

if __name__ == "__main__":
    main()
