#!/usr/bin/env python3
"""鸣志MOONS采集器 - API+产品详情页PDF"""
import json, urllib.request, urllib.parse, os, re, time
from pathlib import Path

BASE = Path(__file__).parent
PDF_DIR = BASE / "pdfs" / "moons"
PDF_DIR.mkdir(parents=True, exist_ok=True)
MANIFEST = BASE / "moons_manifest.json"

def fetch(url, timeout=60):
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0", "Referer": "https://www.moons.com.cn/"})
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
    
    # 1. 获取分类树
    try:
        tree = json.loads(fetch("https://www.moons.com.cn/support-training/downloads/tree").decode("utf-8"))
        print(f"分类树获取成功")
    except Exception as e:
        print(f"分类树获取失败: {e}")
        tree = []
    
    # 2. 提取所有叶子分类code
    def extract_codes(node, codes):
        if node.get("children"):
            for child in node["children"]:
                extract_codes(child, codes)
        else:
            codes.append(node.get("id"))
    
    codes = []
    for root in tree:
        extract_codes(root, codes)
    print(f"找到 {len(codes)} 个叶子分类")
    
    # 3. 遍历分类获取产品列表，再访问产品详情页获取PDF
    all_pdfs = {}
    for i, code in enumerate(codes[:50]):  # 限制前50个分类避免超时
        if i % 10 == 0:
            print(f"  处理分类 {i+1}/{min(len(codes),50)}...")
        try:
            products = json.loads(fetch(f"https://www.moons.com.cn/support-training/downloads/products?type=baseProduct&code={code}").decode("utf-8"))
            for prod in products:
                prod_url = prod.get("url", "")
                if not prod_url:
                    continue
                # 访问产品详情页
                try:
                    html = fetch("https://www.moons.com.cn" + prod_url).decode("utf-8", errors="ignore")
                    # 提取PDF链接
                    pdfs = re.findall(r'href="(/medias/[^"]+\.pdf[^"]*)"', html)
                    for pdf in pdfs:
                        pdf_url = "https://www.moons.com.cn" + pdf
                        # 提取文件名
                        fname = pdf.split("/")[-1].split("?")[0]
                        if fname not in all_pdfs:
                            all_pdfs[fname] = pdf_url
                except:
                    pass
                time.sleep(0.2)
        except:
            pass
    
    print(f"找到 {len(all_pdfs)} 个PDF")
    
    # 4. 下载PDF
    new_count = 0
    for fname, url in sorted(all_pdfs.items()):
        if url in existing:
            continue
        fname_clean = re.sub(r'[\\/:*?"<>|]', "_", fname)[:100]
        fp = PDF_DIR / fname_clean
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
            manifest.append({"name": name, "url": url, "file": f"pdfs/moons/{fname_clean}", "size": len(data), "pages": pages})
            existing.add(url)
            new_count += 1
            MANIFEST.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
            print(f"  + {name} ({pages}页, {len(data)//1024}KB)")
        except Exception as e:
            print(f"  失败: {fname} - {e}")
    
    MANIFEST.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"\n鸣志: 新增{new_count}, 累计{len(manifest)}")

if __name__ == "__main__":
    main()
