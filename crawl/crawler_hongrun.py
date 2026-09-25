#!/usr/bin/env python3
"""虹润 hrgs.com.cn 采集器 - 温控器/仪表说明书"""
import os, re, json, time, hashlib
import urllib.request, urllib.parse

BASE = "https://www.hrgs.com.cn"
OUT = os.path.join(os.path.dirname(__file__), "..", "pdfs", "hongrun")
MANIFEST = os.path.join(os.path.dirname(__file__), "hongrun_manifest.json")
TAGS = [8, 9]  # 8=说明书, 9=通信协议

def fetch(url, timeout=20):
    req = urllib.request.Request(url, headers={
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
        "Referer": BASE + "/download/",
    })
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return r.read()

def get_list():
    """从下载页提取PDF列表"""
    items = []
    for tag in TAGS:
        try:
            html = fetch(f"{BASE}/download/?tag={tag}", timeout=15).decode("utf-8", errors="ignore")
        except Exception as e:
            print(f"  tag={tag} 列表获取失败: {e}")
            continue
        # 找列表项
        lis = re.findall(r'<li[^>]*>(.*?)</li>', html, re.S)
        for li in lis:
            pdf = re.search(r'href=["\']([^"\']*\.pdf)["\']', li, re.I)
            if not pdf:
                continue
            url = pdf.group(1)
            if url.startswith("/"):
                url = BASE + url
            text = re.sub(r'<[^>]+>', ' ', li).strip()
            text = re.sub(r'\s+', ' ', text)
            # 去掉日期和发布者
            name = re.sub(r'^\d+月\d+日\s+\d+年\s*', '', text)
            name = re.sub(r'\s*发布者[：:].*$', '', name).strip()
            if not name:
                name = os.path.basename(url)
            items.append({"name": name, "url": url})
        time.sleep(0.5)
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
    print(f"虹润: 发现 {len(items)} 个PDF")
    new_count = 0
    for it in items:
        if it["url"] in existing:
            continue
        fname = hashlib.md5(it["url"].encode()).hexdigest()[:12] + ".pdf"
        fpath = os.path.join(OUT, fname)
        try:
            data = fetch(it["url"], timeout=30)
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
                "type": "说明书",
            })
            new_count += 1
            print(f"  + {it['name'][:45]} ({pages}页)")
        except Exception as e:
            print(f"  失败: {it['name'][:40]} - {e}")
        time.sleep(0.3)

    with open(MANIFEST, "w", encoding="utf-8") as f:
        json.dump(manifest, f, ensure_ascii=False, indent=2)
    print(f"虹润完成: 新增{new_count}, 累计{len(manifest)}")

if __name__ == "__main__":
    main()
