# -*- coding: utf-8 -*-
"""无锡科思 COCIS 采集器
官网下载页: https://www.chinacocis.com/download
文件托管: https://aosspic10001.websiteonline.cn/proc9f479/other/
"""
import urllib.request, ssl, os, json, re, io, time
import libarchive
from playwright.sync_api import sync_playwright

HERE = os.path.dirname(os.path.abspath(__file__))
os.chdir(HERE)
PDF_DIR = "pdfs/cocis"
MANIFEST = "cocis_manifest.json"
os.makedirs(PDF_DIR, exist_ok=True)

ctx = ssl.create_default_context()
ctx.check_hostname = False
ctx.verify_mode = ssl.CERT_NONE
HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
    'Referer': 'https://www.chinacocis.com/download'
}

def load_manifest():
    if os.path.exists(MANIFEST):
        with open(MANIFEST, 'r', encoding='utf-8') as f:
            return json.load(f)
    return []

def save_manifest(data):
    with open(MANIFEST, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

def get_file_list():
    """用playwright获取下载列表"""
    files = []
    with sync_playwright() as p:
        browser = p.chromium.launch(executable_path="/usr/local/bin/chromium",
            args=["--no-sandbox", "--disable-dev-shm-usage", "--ignore-certificate-errors"])
        page = browser.new_page()
        page.goto("https://www.chinacocis.com/download", timeout=30000)
        page.wait_for_timeout(3000)
        
        # 找所有下载链接
        links = page.query_selector_all("a[href*='aosspic10001.websiteonline.cn']")
        for link in links:
            href = link.get_attribute('href')
            text = link.inner_text().strip().lstrip('※').strip()
            if href and text:
                files.append({'name': text, 'url': href})
        
        browser.close()
    return files

def download_and_extract(url, name):
    """下载压缩包并提取PDF"""
    try:
        req = urllib.request.Request(url, headers=HEADERS)
        with urllib.request.urlopen(req, timeout=60, context=ctx) as r:
            data = r.read()
        
        # 用libarchive解压（支持rar/zip等）
        pdf_data = None
        pdf_name = None
        with libarchive.memory_reader(data) as archive:
            for entry in archive:
                if entry.name.lower().endswith('.pdf'):
                    pdf_name = entry.name
                    pdf_data = b''.join(entry.get_blocks())
                    break
        
        if not pdf_data:
            return None, "无PDF"
        
        # 校验PDF头
        if not pdf_data.startswith(b'%PDF'):
            return None, "非PDF"
        
        # 保存PDF
        safe_name = re.sub(r'[\\/:*?"<>|]', '_', name)
        pdf_path = os.path.join(PDF_DIR, f"{safe_name}.pdf")
        with open(pdf_path, 'wb') as f:
            f.write(pdf_data)
        
        # 获取页数
        pages = 0
        try:
            import subprocess
            result = subprocess.run(['pdfinfo', pdf_path], capture_output=True, text=True, timeout=10)
            for line in result.stdout.split('\n'):
                if line.startswith('Pages:'):
                    pages = int(line.split(':')[1].strip())
                    break
        except:
            pass
        
        return {
            'name': name,
            'url': url,
            'pdf_name': os.path.basename(pdf_name) if pdf_name else '',
            'size': len(pdf_data),
            'pages': pages,
            'category': '工业控制'
        }, None
    except Exception as e:
        return None, str(e)[:50]

def main():
    manifest = load_manifest()
    existing_urls = {m['url'] for m in manifest}
    
    print("获取无锡科思下载列表...")
    files = get_file_list()
    print(f"找到 {len(files)} 个文件")
    
    success = 0
    fail = 0
    skip = 0
    
    for i, f in enumerate(files):
        name = f['name']
        url = f['url']
        
        if url in existing_urls:
            skip += 1
            print(f"[{i+1}/{len(files)}] 跳过: {name[:30]}")
            continue
        
        print(f"[{i+1}/{len(files)}] 下载: {name[:40]}...", end=' ')
        result, err = download_and_extract(url, name)
        
        if result:
            manifest.append(result)
            success += 1
            print(f"OK ({result['pages']}页, {result['size']//1024}KB)")
        else:
            fail += 1
            print(f"FAIL: {err}")
        
        time.sleep(0.5)
    
    save_manifest(manifest)
    print(f"\n完成: 成功{success}, 失败{fail}, 跳过{skip}, 总计{len(manifest)}")

if __name__ == '__main__':
    main()
