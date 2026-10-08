#!/usr/bin/env python3
# 申乐 shenler.cn 继电器手册采集器
# 下载中心页含PDF直链（华为云OSS）
import json, os, re, time, subprocess

UA = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
BASE = 'https://www.shenler.cn'
OUT = 'pdfs/shenler'
MANIFEST = 'shenler_manifest.json'
PAGES = [
    '/产品/下载中心/插座说明书',
    '/产品/下载中心/继电器说明书',
    '/产品/下载中心/固态继电器说明书',
]

def fetch(url, timeout=60):
    r = subprocess.run(['curl', '-s', '-L', '--max-time', str(timeout),
        '-A', UA, '-e', f'{BASE}/', url],
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

    all_items = {}
    for page_path in PAGES:
        url = BASE + page_path
        print(f'抓取 {page_path}...')
        try:
            html = fetch(url, timeout=20).decode('utf-8', errors='ignore')
        except:
            continue
        if len(html) < 1000:
            continue
        # 找PDF链接和名称
        matches = re.findall(r'<a[^>]*href=["\']([^"\']*\.pdf)["\'][^>]*>(.*?)</a>', html, re.S|re.I)
        for pdf_url, content in matches:
            name = re.sub(r'<[^>]+>', '', content).strip()
            if not name or len(name) < 2:
                name = os.path.basename(pdf_url).replace('.pdf', '')
            if pdf_url not in all_items:
                all_items[pdf_url] = name[:80]
        # 也找直接的PDF链接
        pdfs = re.findall(r'href=["\']([^"\']*\.pdf)["\']', html, re.I)
        for p in pdfs:
            if p not in all_items:
                all_items[p] = os.path.basename(p).replace('.pdf', '')[:60]
        print(f'  累计 {len(all_items)} 个PDF')
        time.sleep(0.5)

    print(f'共发现 {len(all_items)} 个PDF')

    for url, name in all_items.items():
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
            ftype = '产品说明书'
            if '插座' in name:
                ftype = '插座说明书'
            elif '固态' in name:
                ftype = '固态继电器说明书'
            manifest.append({'name': name, 'url': url, 'pages': pages,
                           'type': ftype, 'size': len(data),
                           'brand': '申乐', 'src': 'shenler.cn'})
            seen.add(url)
            print(f'    OK {pages}页 {len(data)//1024}KB')
        except Exception as e:
            print(f'    失败: {e}')
        time.sleep(0.3)

    json.dump(manifest, open(MANIFEST, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
    print(f'完成: {len(manifest)} 份')

if __name__ == '__main__':
    main()
