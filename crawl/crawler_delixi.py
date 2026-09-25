#!/usr/bin/env python3
# 德力西变频器 delixidrive.com 手册采集器
# 下载页 https://www.delixidrive.com/list-26-1.html (说明书)
import json, os, re, time, subprocess

UA = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
BASE = 'https://www.delixidrive.com'
LIST_URL = f'{BASE}/list-26-1.html'
OUT = 'pdfs/delixi'
MANIFEST = 'delixi_manifest.json'

def fetch(url, timeout=60, referer=None):
    cmd = ['curl', '-s', '-L', '--max-time', str(timeout), '-A', UA]
    if referer:
        cmd += ['-e', referer]
    cmd.append(url)
    r = subprocess.run(cmd, capture_output=True, timeout=timeout+5)
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

    # 抓取列表页（多页）
    all_detail_urls = []
    for page in range(1, 6):
        url = f'{BASE}/list-26-{page}.html'
        print(f'抓取列表页 {page}...')
        html = fetch(url, timeout=20).decode('utf-8', errors='ignore')
        if len(html) < 1000:
            break
        matches = re.findall(r'href=["\'](https://www\.delixidrive\.com/show-\d+-\d+-1\.html)["\']', html)
        new_urls = [u for u in matches if u not in all_detail_urls]
        all_detail_urls.extend(new_urls)
        print(f'  本页 {len(new_urls)} 个详情页，累计 {len(all_detail_urls)}')
        if len(new_urls) == 0:
            break
        time.sleep(0.5)

    print(f'共 {len(all_detail_urls)} 个详情页')

    for detail_url in all_detail_urls:
        try:
            html = fetch(detail_url, timeout=20).decode('utf-8', errors='ignore')
            # 提取标题
            title_m = re.search(r'<title>(.*?)</title>', html, re.S)
            title = title_m.group(1).strip() if title_m else os.path.basename(detail_url)
            title = re.sub(r'[-_].*$', '', title).strip()
            # 提取下载API链接
            down_ids = re.findall(r'href=["\'](/index\.php\?s=api&c=file&m=down&id=[a-f0-9]+)["\']', html)
            if not down_ids:
                print(f'  无下载链接: {title[:40]}')
                continue
            for i, down_path in enumerate(down_ids):
                down_url = BASE + down_path
                if down_url in seen:
                    continue
                name = title if i == 0 else f'{title}_{i+1}'
                print(f'  下载 {name[:50]}...')
                data = fetch(down_url, timeout=180, referer=detail_url)
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
                manifest.append({'name': name, 'url': down_url, 'pages': pages,
                               'type': '说明书', 'size': len(data),
                               'brand': '德力西', 'src': 'delixidrive.com'})
                seen.add(down_url)
                print(f'    OK {pages}页 {len(data)//1024}KB')
        except Exception as e:
            print(f'  失败: {e}')
        time.sleep(0.3)

    json.dump(manifest, open(MANIFEST, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
    print(f'完成: {len(manifest)} 份')

if __name__ == '__main__':
    main()
