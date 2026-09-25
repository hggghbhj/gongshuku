#!/usr/bin/env python3
# 兰宝传感 shlanbao.cn 产品手册采集器
# 下载页 http://www.shlanbao.cn/download.html
import json, os, re, time, subprocess

UA = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
BASE = 'http://www.shlanbao.cn'
PAGE = f'{BASE}/download.html'
OUT = 'pdfs/lanbao'
MANIFEST = 'lanbao_manifest.json'

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

    print('抓取兰宝下载页...')
    html = fetch(PAGE, timeout=30).decode('utf-8', errors='ignore')

    # 提取所有PDF链接（包括不带.pdf后缀的OSS链接）
    all_urls = re.findall(r'https?://[^"\'\s>]+\.pdf', html, re.I)
    # 也提取OSS下载链接（不带.pdf后缀但包含file/）
    oss_urls = re.findall(r'https?://[^"\'\s>]*thefastfile\.com[^"\'\s>]*file/[^"\'\s>]+', html)
    all_urls.extend(oss_urls)

    # 提取名称
    items = {}
    for url in set(all_urls):
        # 从URL提取名称
        fname = os.path.basename(url).replace('.pdf', '').replace('%20', ' ').replace('-cn', '')
        name = f'兰宝 {fname}'
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
                           'type': '产品手册', 'size': len(data),
                           'brand': '兰宝传感', 'src': 'shlanbao.cn'})
            seen.add(url)
            print(f'    OK {pages}页 {len(data)//1024}KB')
        except Exception as e:
            print(f'    失败: {e}')
        time.sleep(0.5)

    json.dump(manifest, open(MANIFEST, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
    print(f'完成: {len(manifest)} 份')

if __name__ == '__main__':
    main()
