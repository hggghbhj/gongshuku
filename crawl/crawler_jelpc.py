#!/usr/bin/env python3
"""佳尔灵JELPC气动采集器 - 综合目录PDF直链"""
import json, urllib.request, os
from pathlib import Path

BASE = Path(__file__).parent
PDF_DIR = BASE / "pdfs" / "jelpc"
PDF_DIR.mkdir(parents=True, exist_ok=True)
MANIFEST = BASE / "jelpc_manifest.json"

PDFS = [
    {"name": "佳尔灵气动综合目录(中文)", "url": "https://hqcdn.hqsmartcloud.com/jelpc/2026/07/20/rand/3693/chinese.pdf"},
    {"name": "JELPC Pneumatic Catalogue (English)", "url": "https://hqcdn.hqsmartcloud.com/jelpc/2024/12/20/rand/3970/english.pdf"},
]

def fetch(url, timeout=60):
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0", "Referer": "https://www.jelpc.com/"})
    return urllib.request.urlopen(req, timeout=timeout).read()

def get_pages(data):
    import tempfile, subprocess
    with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as f:
        f.write(data)
        fp = f.name
    try:
        r = subprocess.run(["pdfinfo", fp], capture_output=True, text=True, timeout=10)
        for line in r.stdout.splitlines():
            if line.startswith("Pages:"):
                return int(line.split(":")[1].strip())
    except: pass
    finally:
        os.unlink(fp)
    return 0

def main():
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8")) if MANIFEST.exists() else []
    existing = {x["url"] for x in manifest}
    new_count = 0
    for item in PDFS:
        if item["url"] in existing:
            continue
        print(f"下载: {item['name']}")
        try:
            data = fetch(item["url"])
            if not data.startswith(b"%PDF"):
                print(f"  跳过(非PDF)")
                continue
            pages = get_pages(data)
            if pages == 0:
                print(f"  跳过(0页)")
                continue
            fname = item["name"].replace(" ", "_")[:50] + ".pdf"
            (PDF_DIR / fname).write_bytes(data)
            manifest.append({"name": item["name"], "url": item["url"], "file": f"pdfs/jelpc/{fname}", "size": len(data), "pages": pages})
            existing.add(item["url"])
            new_count += 1
            print(f"  + {pages}页, {len(data)//1024}KB")
        except Exception as e:
            print(f"  失败: {e}")
    MANIFEST.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"\n佳尔灵: 新增{new_count}, 累计{len(manifest)}")

if __name__ == "__main__":
    main()
