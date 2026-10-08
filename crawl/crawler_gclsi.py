#!/usr/bin/env python3
# 协鑫集成 gclsi.com 光伏组件手册采集器
# 下载页 https://www.gclsi.com/download.html
import json, os, re, time, subprocess

UA = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
BASE = 'https://www.gclsi.com'
OUT = 'pdfs/gclsi'
MANIFEST = 'gclsi_manifest.json'

def fetch(url, timeout=60):
    r = subprocess.run(['curl', '-s', '-L', '--max-time', str(timeout),
        '-A', UA, '-e', f'{BASE}/download.html', url],
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

    # 获取下载页
    url = f'{BASE}/download.html'
    print(f'抓取下载页...')
    html = fetch(url, timeout=30).decode('utf-8', errors='ignore')
    pdfs = re.findall(r'href=["\']([^"\']*\.pdf)["\']', html, re.I)
    print(f'发现 {len(pdfs)} 个PDF链接')

    all_items = {}
    for p in pdfs:
        if p.startswith('/'):
            p = BASE + p
        elif not p.startswith('http'):
            p = BASE + '/' + p
        name = os.path.basename(p).replace('.pdf', '').strip()
        if p not in all_items:
            all_items[p] = name[:80]

    print(f'去重后 {len(all_items)} 个PDF')

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
            ftype = '安装手册'
            if '质保' in name or 'warranty' in name.lower():
                ftype = '质保书'
            elif '白皮书' in name or 'whitepaper' in name.lower():
                ftype = '白皮书'
            manifest.append({'name': name, 'url': url, 'pages': pages,
                           'type': ftype, 'size': len(data),
                           'brand': '协鑫集成', 'src': 'gclsi.com'})
            seen.add(url)
            print(f'    OK {pages}页 {len(data)//1024}KB')
        except Exception as e:
            print(f'    失败: {e}')
        time.sleep(0.3)

    json.dump(manifest, open(MANIFEST, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
    print(f'完成: {len(manifest)} 份')

if __name__ == '__main__':
    main()
