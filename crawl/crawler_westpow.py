#!/usr/bin/env python3
# 西安西普 westpow.com 软启动器手册采集器
# 下载页 https://www.westpow.com/download-center
import json, os, re, time, subprocess

UA = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
PAGE = 'https://www.westpow.com/download-center'
OUT = 'pdfs/westpow'
MANIFEST = 'westpow_manifest.json'

def fetch(url, timeout=60):
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

    print('抓取西普下载页...')
    html = fetch(PAGE, timeout=30).decode('utf-8', errors='ignore')

    # 提取PDF链接和名称（从a标签）
    items = {}
    matches = re.findall(r'<a[^>]*href=["\']([^"\']*\.pdf)["\'][^>]*>(.*?)</a>', html, re.S|re.I)
    for url, content in matches:
        name = re.sub(r'<[^>]+>', '', content).strip()
        if not name or len(name) < 2:
            name = os.path.basename(url).replace('.pdf', '')
        if url not in items:
            items[url] = name[:80]

    # 如果a标签没提取到名称，从页面上下文找
    if not items:
        pdfs = re.findall(r'href=["\']([^"\']*\.pdf)["\']', html, re.I)
        for url in pdfs:
            if url not in items:
                items[url] = os.path.basename(url).replace('.pdf', '')

    print(f'发现 {len(items)} 个PDF')

    for url, name in items.items():
        if url in seen:
            continue
        print(f'  下载 {name[:50]}...')
        try:
            data = fetch(url, timeout=120)
            if not data.startswith(b'%PDF'):
                print(f'    非PDF({len(data)}字节)，跳过')
                continue
            fname = re.sub(r'[\\/:*?"<>|]', '_', name[:50]) + '.pdf'
            fpath = os.path.join(OUT, fname)
            with open(fpath, 'wb') as f:
                f.write(data)
            pages = get_pages(fpath)
            if pages == 0:
                print(f'    0页，跳过')
                os.remove(fpath)
                continue
            manifest.append({'name': name, 'url': url, 'pages': pages,
                           'type': '说明书', 'size': len(data),
                           'brand': '西安西普', 'src': 'westpow.com'})
            seen.add(url)
            print(f'    OK {pages}页 {len(data)//1024}KB')
        except Exception as e:
            print(f'    失败: {e}')
        time.sleep(0.3)

    json.dump(manifest, open(MANIFEST, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
    print(f'完成: {len(manifest)} 份')

if __name__ == '__main__':
    main()
