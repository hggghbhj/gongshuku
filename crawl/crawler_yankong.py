#!/usr/bin/env python3
# 研控自动化 yankong.com 产品手册采集器
# 下载页 https://www.yankong.com/download.html
import json, os, re, time, subprocess

UA = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
BASE = 'https://www.yankong.com'
OUT = 'pdfs/yankong'
MANIFEST = 'yankong_manifest.json'
PAGES = [
    f'{BASE}/index.php/download-c1.html',
    f'{BASE}/index.php/download-c1-2.html',
    f'{BASE}/index.php/download-c2.html',
    f'{BASE}/index.php/download-c3.html',
]

def fetch(url, timeout=30):
    r = subprocess.run(['curl', '-s', '-L', '--max-time', str(timeout),
        '-A', UA, '-H', f'Referer: {BASE}/', url],
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

    items = {}  # url -> name
    for page in PAGES:
        print(f'抓取 {page}...')
        try:
            html = fetch(page).decode('utf-8', errors='ignore')
        except Exception as e:
            print(f'  失败: {e}')
            continue
        # 提取PDF链接和名称
        matches = re.findall(r'<a[^>]*href=["\']([^"\']*\.pdf)["\'][^>]*>([^<]*)</a>', html, re.I)
        for url, name in matches:
            name = name.strip()
            if not name or len(name) < 2:
                name = os.path.basename(url).replace('.pdf', '')
            if url.startswith('/'):
                url = BASE + url
            if url not in items:
                items[url] = name

    print(f'发现 {len(items)} 个PDF')

    for url, name in items.items():
        if url in seen:
            continue
        print(f'  下载 {name}...')
        try:
            data = fetch(url, timeout=60)
            if not data.startswith(b'%PDF'):
                print(f'    非PDF({len(data)}字节)，跳过')
                continue
            fname = os.path.basename(url)
            fpath = os.path.join(OUT, fname)
            with open(fpath, 'wb') as f:
                f.write(data)
            pages = get_pages(fpath)
            if pages == 0:
                print(f'    0页，跳过')
                os.remove(fpath)
                continue
            manifest.append({'name': name, 'url': url, 'pages': pages,
                           'type': '产品手册', 'size': len(data),
                           'brand': '研控自动化', 'src': 'yankong.com'})
            seen.add(url)
            print(f'    OK {pages}页 {len(data)//1024}KB')
        except Exception as e:
            print(f'    失败: {e}')
        time.sleep(0.3)

    json.dump(manifest, open(MANIFEST, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
    print(f'完成: {len(manifest)} 份')

if __name__ == '__main__':
    main()
