#!/usr/bin/env python3
# 广州数控 gsk.com.cn 数控系统手册采集器
# 下载页 https://www.gsk.com.cn/zlxz/index_15.aspx?lcid=18
import json, os, re, time, subprocess
from urllib.parse import quote

UA = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
BASE = 'https://www.gsk.com.cn'
PAGE = f'{BASE}/zlxz/index_15.aspx?lcid=18'
OUT = 'pdfs/gskcnc'
MANIFEST = 'gskcnc_manifest.json'

def fetch(url, timeout=120, encode=True):
    # URL编码中文和空格（仅对下载URL编码，不对页面URL编码）
    if encode and url.startswith('http') and 'uploadfiles' in url:
        parts = url.split('/')
        encoded = '/'.join(quote(p, safe=":.-_()（）《》") if i > 2 else p for i, p in enumerate(parts))
        url = encoded
    r = subprocess.run(['curl', '-s', '-L', '--max-time', str(timeout),
        '-A', UA, '-e', PAGE, url],
        capture_output=True, timeout=timeout+5)
    return r.stdout

def get_pages(path):
    try:
        r = subprocess.run(['pdfinfo', path], capture_output=True, text=True, timeout=15)
        for line in r.stdout.splitlines():
            if line.startswith('Pages:'):
                return int(line.split(':')[1].strip())
    except: pass
    try:
        from pypdf import PdfReader
        return len(PdfReader(path).pages)
    except: pass
    return 0

def main():
    os.makedirs(OUT, exist_ok=True)
    manifest = []
    if os.path.exists(MANIFEST):
        manifest = json.load(open(MANIFEST, encoding='utf-8'))
    seen = {x['url'] for x in manifest}

    print('抓取广州数控下载页...')
    html = fetch(PAGE, timeout=30, encode=False).decode('utf-8', errors='ignore')

    # 提取PDF链接和名称（同一个URL可能有多个a标签，取最长名称）
    items = {}
    matches = re.findall(r'<a[^>]*href=["\']([^"\']*\.pdf)["\'][^>]*>(.*?)</a>', html, re.S|re.I)
    for url, content in matches:
        name = re.sub(r'<[^>]+>', '', content).strip()
        if not name or len(name) < 2 or name == '下载':
            name = os.path.basename(url).replace('.pdf', '')
        if url.startswith('/'):
            url = BASE + url
        elif not url.startswith('http'):
            url = BASE + '/' + url
        # 取最长的名称
        if url not in items or len(name) > len(items[url]):
            items[url] = name[:80]

    print(f'发现 {len(items)} 个PDF')

    for url, name in items.items():
        if url in seen:
            continue
        print(f'  下载 {name[:40]}...')
        try:
            data = fetch(url, timeout=180)
            if not data.startswith(b'%PDF'):
                print(f'    非PDF({len(data)}字节)，跳过')
                continue
            fname = re.sub(r'[\\/:*?"<>|]', '_', name[:40]) + '.pdf'
            fpath = os.path.join(OUT, fname)
            with open(fpath, 'wb') as f:
                f.write(data)
            pages = get_pages(fpath)
            if pages == 0:
                print(f'    0页，跳过')
                os.remove(fpath)
                continue
            manifest.append({'name': name, 'url': url, 'pages': pages,
                           'type': '使用手册', 'size': len(data),
                           'brand': '广州数控', 'src': 'gsk.com.cn'})
            seen.add(url)
            print(f'    OK {pages}页 {len(data)//1024}KB')
        except Exception as e:
            print(f'    失败: {e}')
        time.sleep(0.3)

    json.dump(manifest, open(MANIFEST, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
    print(f'完成: {len(manifest)} 份')

if __name__ == '__main__':
    main()
