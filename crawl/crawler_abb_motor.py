#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""ABB电机采集器：从ABB电机手册页面下载中文使用手册"""
import urllib.request, ssl, re, json, os, subprocess
from urllib.parse import quote

ctx = ssl.create_default_context()
ctx.check_hostname = False
ctx.verify_mode = ssl.CERT_NONE
HEADERS = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0 Safari/537.36'}

MANIFEST = 'abb_motor_manifest.json'
PDF_DIR = 'pdfs/abb'
os.makedirs(PDF_DIR, exist_ok=True)

BASE_URL = 'https://motorswechat.abb.com.cn'
LIST_URL = BASE_URL + '/motor/center/manual/'

def fetch(url):
    req = urllib.request.Request(url, headers=HEADERS)
    with urllib.request.urlopen(req, timeout=20, context=ctx) as r:
        return r.read()

def get_manual_list():
    """获取手册列表"""
    html = fetch(LIST_URL).decode('utf-8', errors='ignore')
    # 找PDF链接
    links = re.findall(r'href=["\']([^"\']*\.pdf)["\']', html, re.I)
    manuals = []
    for link in links:
        if link.startswith('/'):
            url = BASE_URL + quote(link)
            name = link.split('/')[-1].replace('.pdf', '')
        else:
            url = quote(link)
            name = link.split('/')[-1].replace('.pdf', '')
        manuals.append({'name': name, 'url': url})
    return manuals

def download_pdf(manual):
    """下载PDF并校验"""
    try:
        data = fetch(manual['url'])
        if not data.startswith(b'%PDF'):
            return None, 'notpdf'
        if len(data) < 5000:
            return None, 'tiny'
        
        fn = 'abb_' + re.sub(r'[^a-zA-Z0-9]', '_', manual['name'])[:50] + '.pdf'
        fp = os.path.join(PDF_DIR, fn)
        with open(fp, 'wb') as f:
            f.write(data)
        
        # 获取页数
        try:
            result = subprocess.run(['pdfinfo', fp], capture_output=True, text=True, timeout=10)
            pages_m = re.search(r'Pages:\s+(\d+)', result.stdout)
            pages = int(pages_m.group(1)) if pages_m else 0
        except:
            pages = 0
        
        return {
            'fn': fn,
            'size': len(data),
            'pages': pages,
        }, None
    except Exception as e:
        return None, str(e)[:50]

def main():
    # 加载已有manifest
    if os.path.exists(MANIFEST):
        with open(MANIFEST, 'r', encoding='utf-8') as f:
            manifest = json.load(f)
    else:
        manifest = []
    
    existing_names = {m['name'] for m in manifest}
    
    # 获取手册列表
    manuals = get_manual_list()
    print(f"找到 {len(manuals)} 个手册")
    
    # 下载
    success = 0
    fail = 0
    skip = 0
    
    for i, manual in enumerate(manuals):
        if manual['name'] in existing_names:
            skip += 1
            continue
        
        print(f"[{i+1}/{len(manuals)}] {manual['name'][:40]}...")
        
        result, err = download_pdf(manual)
        if result:
            manifest.append({
                'name': manual['name'],
                'url': manual['url'],
                'fn': result['fn'],
                'size': result['size'],
                'pages': result['pages'],
                'cat': 'ABB电机',
            })
            print(f"  OK ({result['pages']}页, {result['size']//1024}KB)")
            success += 1
        else:
            print(f"  失败: {err}")
            fail += 1
    
    # 保存manifest
    with open(MANIFEST, 'w', encoding='utf-8') as f:
        json.dump(manifest, f, ensure_ascii=False, indent=2)
    
    print(f"\n完成: 成功{success}, 失败{fail}, 跳过{skip}, 总计{len(manifest)}")

if __name__ == '__main__':
    main()
