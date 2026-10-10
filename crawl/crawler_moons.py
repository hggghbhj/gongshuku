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
    
    # 3. 并行遍历分类获取产品，再访问详情页提取PDF
    all_pdfs = {}
    from concurrent.futures import ThreadPoolExecutor,as_completed
    def process_code(code):
        result={}
        try:
            products = json.loads(fetch(f"https://www.moons.com.cn/support-training/downloads/products?type=baseProduct&code={code}").decode("utf-8"))
            for prod in products:
                prod_url = prod.get("url", "")
                if not prod_url:continue
                try:
                    html = fetch("https://www.moons.com.cn" + prod_url,timeout=15).decode("utf-8", errors="ignore")
                    for pdf in re.findall(r'href="(/medias/[^"]+\.pdf[^"]*)"',html):
                        fname=pdf.split("/")[-1].split("?")[0]
                        result[fname]="https://www.moons.com.cn"+pdf
                except:pass
        except:pass
        return result
    sel_codes=codes[:50]
    with ThreadPoolExecutor(max_workers=8) as ex:
        futs=[ex.submit(process_code,c) for c in sel_codes]
        done=0
        for f in as_completed(futs):
            all_pdfs.update(f.result());done+=1
            if done%10==0:print(f"  分类 {done}/{len(sel_codes)} PDF{len(all_pdfs)}")
    
    print(f"找到 {len(all_pdfs)} 个PDF")
    
    # 4. 并行下载PDF
    to_dl=[(f,u) for f,u in sorted(all_pdfs.items()) if u not in existing]
    print(f"需下载: {len(to_dl)}")
    new_count=0
    def dl(item):
        fname,url=item
        fname_clean=re.sub(r'[\\/:*?"<>|]','_',fname)[:100]
        try:
            data=fetch(url,timeout=40)
            if not data or not data.startswith(b"%PDF") or len(data)<2000:return None
            pages=get_pages(data)
            if pages==0:return None
            return fname_clean,data,pages
        except:return None
    done=0
    with ThreadPoolExecutor(max_workers=8) as ex:
        for f in as_completed([ex.submit(dl,x) for x in to_dl]):
            r=f.result();done+=1
            if r:
                fname_clean,data,pages=r
                fp=PDF_DIR/fname_clean
                fp.write_bytes(data)
                name=fname_clean.replace(".pdf","").replace(".PDF","")
                # 找原始URL
                url=all_pdfs.get(fname_clean)
                manifest.append({"name":name,"url":url,"file":f"pdfs/moons/{fname_clean}","size":len(data),"pages":pages})
                existing.add(url);new_count+=1
            if done%100==0:
                MANIFEST.write_text(json.dumps(manifest,ensure_ascii=False,indent=2),encoding="utf-8")
                print(f"  下载进度 {done}/{len(to_dl)} 新增{new_count}")
    
    MANIFEST.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"\n鸣志: 新增{new_count}, 累计{len(manifest)}")

if __name__ == "__main__":
    main()
