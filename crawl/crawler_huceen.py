#!/usr/bin/env python3
# 汇辰自动化 huceen.cn 手册采集器
# 下载页 https://www.huceen.cn/download/list-274-cn.html (3页)
import json, os, re, time, subprocess, urllib.request

UA = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
BASE = 'https://www.huceen.cn'
OUT = 'pdfs/huceen'
MANIFEST = 'huceen_manifest.json'
PAGES = [
    f'{BASE}/download/list-274-cn.html',
    f'{BASE}/download/list-274-2-cn.html',
    f'{BASE}/download/list-274-3-cn.html',
]

def fetch(url, timeout=30, referer=None):
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

    # 抓取所有页面的下载项
    items = {}  # id -> name
    for page in PAGES:
        print(f'抓取 {page}...')
        try:
            html = fetch(page).decode('utf-8', errors='ignore')
        except Exception as e:
            print(f'  失败: {e}')
            continue
        # 模式：<a href="...dodown&id=XXX" title="下载">名称</a>
        matches = re.findall(r'dodown&lang=cn&id=(\d+)"[^>]*>([^<]+)</a>', html)
        for fid, name in matches:
            name = name.strip()
            if name and name != '下载' and fid not in items:
                items[fid] = name

    print(f'发现 {len(items)} 个手册')

    for fid, name in items.items():
        url = f'{BASE}/app/system/entrance.php?m=include&c=access&a=dodown&lang=cn&id={fid}'
        if url in seen:
            continue
        print(f'  下载 {name}...')
        try:
            data = fetch(url, timeout=60, referer=PAGES[0])
            if not data.startswith(b'%PDF'):
                print(f'    非PDF({len(data)}字节)，跳过')
                continue
            fpath = os.path.join(OUT, f'huceen_{fid}.pdf')
            with open(fpath, 'wb') as f:
                f.write(data)
            pages = get_pages(fpath)
            if pages == 0:
                print(f'    0页，跳过')
                os.remove(fpath)
                continue
            manifest.append({'name': name, 'url': url, 'pages': pages,
                           'type': '产品手册', 'size': len(data),
                           'brand': '汇辰自动化', 'src': 'huceen.cn'})
            seen.add(url)
            print(f'    OK {pages}页 {len(data)//1024}KB')
        except Exception as e:
            print(f'    失败: {e}')
        time.sleep(0.5)

    json.dump(manifest, open(MANIFEST, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
    print(f'完成: {len(manifest)} 份')

if __name__ == '__main__':
    main()
