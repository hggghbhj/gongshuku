#!/usr/bin/env python3
# 华中数控 huazhongcnc.com 数控系统手册采集器
# 下载页 https://huazhongcnc.com/portal/list/index/cid/73.html
import json, os, re, time, subprocess
from urllib.parse import quote, unquote

UA = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
BASE = 'https://huazhongcnc.com'
PAGE = f'{BASE}/portal/list/index/cid/73.html'
OUT = 'pdfs/huazhong'
MANIFEST = 'huazhong_manifest.json'

def fetch(url, timeout=120):
    # URL编码中文
    if url.startswith('http'):
        url = quote(url, safe=':/')
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

    print('抓取华中数控下载页...')
    html = fetch(PAGE, timeout=30).decode('utf-8', errors='ignore')

    # 提取PDF链接（从viewer.html?file=参数中提取）
    items = {}
    matches = re.findall(r'file=([^"\']+\.pdf)', html, re.I)
    for url in matches:
        # 提取名称
        name = os.path.basename(unquote(url)).replace('.pdf', '')
        if url.startswith('//'):
            url = 'https:' + url
        elif url.startswith('/'):
            url = BASE + url
        elif not url.startswith('http'):
            url = BASE + '/' + url
        if url not in items:
            items[url] = name[:80]

    # 也提取直接的PDF链接
    direct = re.findall(r'href=["\']([^"\']*\.pdf)["\']', html, re.I)
    for url in direct:
        name = os.path.basename(unquote(url)).replace('.pdf', '')
        if url.startswith('//'):
            url = 'https:' + url
        elif url.startswith('/'):
            url = BASE + url
        elif not url.startswith('http'):
            url = BASE + '/' + url
        if url not in items:
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
                           'type': '用户手册', 'size': len(data),
                           'brand': '华中数控', 'src': 'huazhongcnc.com'})
            seen.add(url)
            print(f'    OK {pages}页 {len(data)//1024}KB')
        except Exception as e:
            print(f'    失败: {e}')
        time.sleep(0.3)

    json.dump(manifest, open(MANIFEST, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
    print(f'完成: {len(manifest)} 份')

if __name__ == '__main__':
    main()
