#!/usr/bin/env python3
# 阿尔法电气 szalpha.cn 变频器手册采集器
# 下载页 http://www.szalpha.cn/zw/download/index.aspx
import json, os, re, time, subprocess

UA = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
BASE = 'http://www.szalpha.cn'
OUT = 'pdfs/alpha'
MANIFEST = 'alpha_manifest.json'
PAGES = [
    f'{BASE}/zw/download/index.aspx?page=1',
    f'{BASE}/zw/download/index.aspx?page=2',
]

def fetch(url, timeout=60):
    r = subprocess.run(['curl', '-s', '-L', '--max-time', str(timeout),
        '-A', UA, '-e', f'{BASE}/zw/download/index.aspx', url],
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
            html = fetch(page, timeout=30).decode('utf-8', errors='ignore')
        except Exception as e:
            print(f'  失败: {e}')
            continue
        # 提取PDF链接和名称
        matches = re.findall(r'<a[^>]*href=["\']([^"\']*\.pdf)["\'][^>]*>(.*?)</a>', html, re.S|re.I)
        for url, content in matches:
            name = re.sub(r'<[^>]+>', '', content).strip().replace('\u200d', '').strip()
            if not name or len(name) < 2:
                name = os.path.basename(url).replace('.pdf', '')
            if url.startswith('//'):
                url = 'http:' + url
            elif url.startswith('/'):
                url = BASE + url
            elif not url.startswith('http'):
                url = BASE + '/' + url.lstrip('/')
            if url not in items:
                items[url] = name[:60]

    print(f'发现 {len(items)} 个PDF')

    for url, name in items.items():
        if url in seen:
            continue
        print(f'  下载 {name}...')
        try:
            data = fetch(url, timeout=120)
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
                           'type': '用户手册', 'size': len(data),
                           'brand': '阿尔法电气', 'src': 'szalpha.cn'})
            seen.add(url)
            print(f'    OK {pages}页 {len(data)//1024}KB')
        except Exception as e:
            print(f'    失败: {e}')
        time.sleep(0.3)

    json.dump(manifest, open(MANIFEST, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
    print(f'完成: {len(manifest)} 份')

if __name__ == '__main__':
    main()
