#!/usr/bin/env python3
"""良信 lazzen.com 采集器 - 断路器/接触器说明书"""
import os, re, json, time, hashlib
import urllib.request

BASE = "https://www.lazzen.com"
OUT = os.path.join(os.path.dirname(__file__), "..", "pdfs", "lazzen")
MANIFEST = os.path.join(os.path.dirname(__file__), "lazzen_manifest.json")

def fetch(url, timeout=20):
    req = urllib.request.Request(url, headers={
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
        "Referer": BASE + "/support/downloads/product-manual",
    })
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return r.read()

def get_list():
    """从说明书页提取PDF列表"""
    try:
        html = fetch(BASE + "/support/downloads/product-manual", timeout=15).decode("utf-8", errors="ignore")
    except Exception as e:
        print(f"  列表获取失败: {e}")
        return []
    items = []
    # 找所有PDF链接
    pdfs = re.findall(r'href=["\'](/Public/Uploads/[^"\']*\.pdf)["\']', html, re.I)
    for pdf in pdfs:
        url = BASE + pdf
        # 找附近的名称
        idx = html.find(pdf)
        context = html[max(0,idx-500):idx+50]
        # 提取中文名称
        names = re.findall(r'[\u4e00-\u9fa5][\u4e00-\u9fa5A-Za-z0-9\-\~\(\)（）、\s]{4,60}', context)
        name = names[-1] if names else os.path.basename(pdf)
        name = re.sub(r'\s+', ' ', name).strip()
        items.append({"name": name, "url": url})
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
    print(f"良信: 发现 {len(items)} 个PDF")
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
                "type": "产品说明书",
            })
            new_count += 1
            print(f"  + {it['name'][:45]} ({pages}页)")
        except Exception as e:
            print(f"  失败: {it['name'][:40]} - {e}")
        time.sleep(0.3)

    with open(MANIFEST, "w", encoding="utf-8") as f:
        json.dump(manifest, f, ensure_ascii=False, indent=2)
    print(f"良信完成: 新增{new_count}, 累计{len(manifest)}")

if __name__ == "__main__":
    main()
