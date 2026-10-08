#!/usr/bin/env python3
"""鼎阳科技SIGLENT采集器 - OSS直链PDF"""
import json, urllib.request, urllib.parse, os, re, time
from pathlib import Path

BASE = Path(__file__).parent
PDF_DIR = BASE / "pdfs" / "siglent"
PDF_DIR.mkdir(parents=True, exist_ok=True)
MANIFEST = BASE / "siglent_manifest.json"

def fetch(url, timeout=60):
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0", "Referer": "https://www.siglent.com/"})
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
    
    # 从下载页抓取所有PDF链接
    all_pdfs = set()
    try:
        html = fetch("https://www.siglent.com/support/resource/?current=siglent-manual-download").decode("utf-8", errors="ignore")
        pdfs = re.findall(r'https://siglent\.oss-cn-shenzhen\.aliyuncs\.com/[^"\']+\.pdf', html)
        all_pdfs.update(pdfs)
        print(f"页面抓取: {len(pdfs)}个PDF")
    except Exception as e:
        print(f"页面抓取失败: {e}")
    
    # 已知的OSS目录（尝试列举常见类别）
    categories = ["Oscilloscope", "Signal%20Generator", "RF%20Generator", "Spectrum%20Analyzer", 
                  "Modular%20Instrument", "Vector%20Network%20Analyzer", "Power%20Supply",
                  "Multimeter", "Accessory", "Software"]
    
    new_count = 0
    for url in sorted(all_pdfs):
        if url in existing:
            continue
        fname = urllib.parse.unquote(url.split("/")[-1])
        fname = re.sub(r'[\\/:*?"<>|]', "_", fname)[:100]
        fp = PDF_DIR / fname
        try:
            data = fetch(url, timeout=60)
            if not data or not data.startswith(b"%PDF"):
                print(f"  跳过(非PDF): {fname}")
                continue
            if len(data) < 2000:
                print(f"  跳过(太小): {fname}")
                continue
            pages = get_pages(data)
            if pages == 0:
                print(f"  跳过(0页): {fname}")
                continue
            fp.write_bytes(data)
            name = fname.replace(".pdf","").replace(".PDF","")
            manifest.append({"name": name, "url": url, "file": f"pdfs/siglent/{fname}", "size": len(data), "pages": pages})
            existing.add(url)
            new_count += 1
            MANIFEST.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
            print(f"  + {name} ({pages}页, {len(data)//1024}KB)")
        except Exception as e:
            print(f"  失败: {fname} - {e}")
    
    MANIFEST.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"\n鼎阳科技: 新增{new_count}, 累计{len(manifest)}")

if __name__ == "__main__":
    main()
