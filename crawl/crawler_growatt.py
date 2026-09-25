#!/usr/bin/env python3
# 古瑞瓦特 growatt.com 光伏逆变器手册采集器
# 下载页 https://www.growatt.com/support/download?page=N
import json, os, re, time, subprocess

UA = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
BASE = 'https://www.growatt.com'
OUT = 'pdfs/growatt'
MANIFEST = 'growatt_manifest.json'

def fetch(url, timeout=60):
    r = subprocess.run(['curl', '-s', '-L', '--max-time', str(timeout),
        '-A', UA, '-e', f'{BASE}/support/download', url],
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

    # 翻页获取所有PDF
    all_items = {}
    for page in range(1, 20):
        url = f'{BASE}/support/download?page={page}'
        print(f'抓取第{page}页...')
        html = fetch(url, timeout=20).decode('utf-8', errors='ignore')
        if len(html) < 1000:
            break
        matches = re.findall(r'<a[^>]*href=["\']([^"\']*\.pdf)["\'][^>]*>(.*?)</a>', html, re.S|re.I)
        if not matches:
            break
        new_count = 0
        for pdf_url, content in matches:
            name = re.sub(r'<[^>]+>', '', content).strip()
            if not name or len(name) < 2:
                name = os.path.basename(pdf_url).replace('.pdf', '')
            if pdf_url.startswith('/'):
                pdf_url = BASE + pdf_url
            if pdf_url not in all_items:
                all_items[pdf_url] = name[:80]
                new_count += 1
        print(f'  本页{len(matches)}个，新增{new_count}个，累计{len(all_items)}')
        if new_count == 0:
            break
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
            ftype = '用户手册'
            if '规格' in name or '参数' in name or 'datasheet' in name.lower():
                ftype = '技术规格'
            elif '安装' in name or 'quick' in name.lower():
                ftype = '安装指导'
            manifest.append({'name': name, 'url': url, 'pages': pages,
                           'type': ftype, 'size': len(data),
                           'brand': '古瑞瓦特', 'src': 'growatt.com'})
            seen.add(url)
            print(f'    OK {pages}页 {len(data)//1024}KB')
        except Exception as e:
            print(f'    失败: {e}')
        time.sleep(0.3)

    json.dump(manifest, open(MANIFEST, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
    print(f'完成: {len(manifest)} 份')

if __name__ == '__main__':
    main()
