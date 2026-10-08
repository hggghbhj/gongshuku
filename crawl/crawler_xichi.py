#!/usr/bin/env python3
# 西驰电气 xichi.com 软启动器/变频器手册采集器
# 下载页 http://www.xichi.com/service/smsxz/
import json, os, re, time, subprocess

UA = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
BASE = 'http://www.xichi.com'
PAGE = f'{BASE}/service/smsxz/'
OUT = 'pdfs/xichi'
MANIFEST = 'xichi_manifest.json'

def fetch(url, timeout=120):
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

    print('抓取西驰下载页...')
    html = fetch(PAGE, timeout=30).decode('utf-8', errors='ignore')

    # 提取下载链接和名称
    items = []
    # 匹配表格行：名称 + 下载链接
    rows = re.findall(r'<tr[^>]*>(.*?)</tr>', html, re.S|re.I)
    for row in rows:
        name_match = re.search(r'<td[^>]*>([^<]+)</td>', row)
        link_match = re.search(r'href=["\']([^"\']*downfile[^"\']*)["\']', row, re.I)
        if name_match and link_match:
            name = name_match.group(1).strip()
            url = link_match.group(1)
            if url.startswith('/'):
                url = BASE + url
            elif not url.startswith('http'):
                url = BASE + '/' + url
            if name and len(name) > 2:
                items.append((name[:60], url))

    # 如果表格匹配失败，用通用方式
    if not items:
        links = re.findall(r'href=["\']([^"\']*downfile[^"\']*)["\']', html, re.I)
        for i, url in enumerate(links):
            if url.startswith('/'):
                url = BASE + url
            items.append((f'西驰说明书{i+1}', url))

    print(f'发现 {len(items)} 个PDF')

    for name, url in items:
        if url in seen:
            continue
        print(f'  下载 {name}...')
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
                           'type': '使用说明书', 'size': len(data),
                           'brand': '西驰电气', 'src': 'xichi.com'})
            seen.add(url)
            print(f'    OK {pages}页 {len(data)//1024}KB')
        except Exception as e:
            print(f'    失败: {e}')
        time.sleep(0.5)

    json.dump(manifest, open(MANIFEST, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
    print(f'完成: {len(manifest)} 份')

if __name__ == '__main__':
    main()
