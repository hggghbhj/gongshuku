# -*- coding: utf-8 -*-
"""固纬电子(GWINSTEK)采集器：下载中心页面提取下载链接，直接下载PDF。
官网: https://www.gwinstek.com.cn/
下载页: /down/207(示波器), /down/208(手册指南), /down/209(电源), /down/259, /down/275
下载链接: /content/download.aspx?t=0&id=XXXX
"""
import os, json, hashlib, subprocess, time, re, urllib.request, urllib.parse

BASE = "https://www.gwinstek.com.cn"
DOWN_PAGES = ["/down/207", "/down/208", "/down/209", "/down/259", "/down/275"]
OUTDIR = "pdfs/gwinstek"
MANIFEST = "gwinstek_manifest.json"
os.makedirs(OUTDIR, exist_ok=True)

def load_manifest():
    if os.path.exists(MANIFEST):
        try: return json.load(open(MANIFEST, encoding="utf-8"))
        except: return []
    return []

def save_manifest(data):
    json.dump(data, open(MANIFEST, "w", encoding="utf-8"), ensure_ascii=False, indent=1)

def pdf_ok(path):
    try:
        r = subprocess.run(["pdfinfo", path], capture_output=True, text=True, timeout=15)
        return r.returncode == 0 and "Pages:" in r.stdout
    except: return False

def get_pdf_pages(path):
    try:
        r = subprocess.run(["pdfinfo", path], capture_output=True, text=True, timeout=15)
        for line in r.stdout.split("\n"):
            if line.startswith("Pages:"):
                return int(line.split(":")[1].strip())
    except: pass
    return 0

def fetch(url, timeout=30):
    req = urllib.request.Request(url, headers={
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
        "Referer": BASE + "/",
    })
    return urllib.request.urlopen(req, timeout=timeout).read()

def get_page_links(page_path):
    """从下载页提取所有下载链接和标题"""
    try:
        html = fetch(BASE + page_path).decode("utf-8", errors="ignore")
    except Exception as e:
        print(f"  页面获取失败 {page_path}: {e}")
        return []
    
    # 提取下载链接和对应的标题
    links = []
    # 匹配 <a href="/content/download.aspx?t=0&id=XXXX">标题</a>
    pattern = r'<a[^>]*href="(/content/download\.aspx\?t=0&id=(\d+))"[^>]*>(.*?)</a>'
    for m in re.finditer(pattern, html, re.DOTALL):
        url = BASE + m.group(1)
        doc_id = m.group(2)
        title = re.sub(r'<[^>]+>', '', m.group(3)).strip()
        if title and len(title) > 1:
            links.append({"id": doc_id, "url": url, "title": title, "page": page_path})
    
    # 去重
    seen = set()
    uniq = []
    for l in links:
        if l["id"] not in seen:
            seen.add(l["id"])
            uniq.append(l)
    return uniq

def download_pdf(item):
    """下载PDF，返回(本地路径, 文件名标题)或None"""
    doc_id = item["id"]
    url = item["url"]
    
    # 用id作为文件名的一部分
    fname = f"{doc_id}_{hashlib.md5(url.encode()).hexdigest()[:8]}.pdf"
    fpath = os.path.join(OUTDIR, fname)
    
    if os.path.exists(fpath) and pdf_ok(fpath):
        return fpath, item.get("title", "DOWNLOAD")
    
    try:
        req = urllib.request.Request(url, headers={
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
            "Referer": BASE + "/",
        })
        resp = urllib.request.urlopen(req, timeout=60)
        data = resp.read()
        
        # 从Content-Disposition提取文件名作为标题
        cd = resp.headers.get("Content-Disposition", "")
        filename = "DOWNLOAD"
        if "filename=" in cd:
            filename = cd.split("filename=")[1].strip('";\' ')
            if filename.lower().endswith(".pdf"):
                filename = filename[:-4]
            # URL解码
            try:
                filename = urllib.parse.unquote(filename)
            except: pass
        
        if len(data) < 1000 or data[:4] != b"%PDF":
            print(f"  非PDF或太小: {filename} ({len(data)} bytes)")
            return None
        
        with open(fpath, "wb") as f:
            f.write(data)
        
        if pdf_ok(fpath):
            return fpath, filename
        else:
            os.remove(fpath)
            print(f"  PDF损坏: {filename}")
            return None
    except Exception as e:
        print(f"  下载失败: {str(e)[:60]}")
        return None

def main():
    print("=== 固纬电子(GWINSTEK)采集器 ===")
    manifest = load_manifest()
    existing_ids = {item["id"] for item in manifest}
    print(f"已有manifest: {len(manifest)} 条")
    
    # 收集所有页面的下载链接
    all_links = []
    for page in DOWN_PAGES:
        print(f"抓取页面 {page}...")
        links = get_page_links(page)
        print(f"  找到 {len(links)} 个下载链接")
        all_links.extend(links)
        time.sleep(1)
    
    # 去重
    seen = set()
    uniq_links = []
    for l in all_links:
        if l["id"] not in seen:
            seen.add(l["id"])
            uniq_links.append(l)
    
    print(f"\n总计去重后: {len(uniq_links)} 个下载链接")
    print(f"已存在: {len(existing_ids)} 个")
    
    # 下载新文件（并行）
    new_count = 0
    fail_count = 0
    to_download=[item for item in uniq_links if item["id"] not in existing_ids]
    print(f"需检查: {len(to_download)} 个")
    from concurrent.futures import ThreadPoolExecutor,as_completed
    def work(item):
        return item, download_pdf(item)
    done=0
    with ThreadPoolExecutor(max_workers=8) as ex:
        futs=[ex.submit(work,item) for item in to_download]
        for f in as_completed(futs):
            item,result=f.result()
            done+=1
            if result:
                fpath, filename = result
                pages = get_pdf_pages(fpath)
                size = os.path.getsize(fpath)
                manifest.append({
                    "id": item["id"],
                    "name": filename,
                    "url": item["url"],
                    "brand": "固纬电子",
                    "type": "用户手册",
                    "size": size,
                    "pages": pages,
                    "page": item["page"],
                })
                new_count += 1
            else:
                fail_count += 1
            if done%50==0:
                save_manifest(manifest)
                print(f"  进度 {done}/{len(to_download)} 新增{new_count}")
    
    save_manifest(manifest)
    print(f"\n=== 完成 ===")
    print(f"新增: {new_count} 份")
    print(f"失败: {fail_count} 份")
    print(f"总计: {len(manifest)} 份")

if __name__ == "__main__":
    main()
