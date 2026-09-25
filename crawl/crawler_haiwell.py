#!/usr/bin/env python3
# 海为 haiwell.com 产品手册采集器
# 下载页 https://haiwell.com/download/download.php?class2=392 (产品手册)
import json, os, re, time, subprocess
from pypdf import PdfReader

UA = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
BASE = 'https://haiwell.com'
OUT = 'pdfs/haiwell'
MANIFEST = 'haiwell_manifest.json'

def fetch(url, timeout=20):
    r = subprocess.run(['curl','-s','-L','--max-time',str(timeout),
        '-A',UA,'-H',f'Referer: {BASE}/download/',url],
        capture_output=True, timeout=timeout+5)
    return r.stdout

def get_pages(path):
    try:
        return len(PdfReader(path).pages)
    except:
        return 0

def main():
    os.makedirs(OUT, exist_ok=True)
    manifest = []
    if os.path.exists(MANIFEST):
        manifest = json.load(open(MANIFEST, encoding='utf-8'))
    seen = {x['url'] for x in manifest}

    # 产品手册分类页（可能有多页）
    all_ids = set()
    for page in range(1, 6):
        url = f'{BASE}/download/download.php?class2=392&page={page}'
        print(f'抓取产品手册第{page}页...')
        try:
            html = fetch(url).decode('utf-8', errors='ignore')
        except:
            break
        ids = re.findall(r'showdownload\.php\?id=(\d+)', html)
        new_ids = set(ids) - all_ids
        if not new_ids and page > 1:
            break
        all_ids.update(ids)
        print(f'  发现 {len(new_ids)} 个新详情页')
        time.sleep(0.3)

    # 使用说明分类页
    for page in range(1, 6):
        url = f'{BASE}/download/download.php?class2=111&page={page}'
        print(f'抓取使用说明第{page}页...')
        try:
            html = fetch(url).decode('utf-8', errors='ignore')
        except:
            break
        ids = re.findall(r'showdownload\.php\?id=(\d+)', html)
        new_ids = set(ids) - all_ids
        if not new_ids and page > 1:
            break
        all_ids.update(ids)
        print(f'  发现 {len(new_ids)} 个新详情页')
        time.sleep(0.3)

    print(f'共发现 {len(all_ids)} 个详情页')

    # 遍历详情页获取下载链接
    for did in sorted(all_ids, key=int):
        detail_url = f'{BASE}/download/showdownload.php?id={did}'
        try:
            html = fetch(detail_url).decode('utf-8', errors='ignore')
        except:
            continue

        # 提取标题
        title_m = re.search(r'<title>(.*?)</title>', html, re.I)
        title = title_m.group(1).strip() if title_m else f'海为{did}'
        title = title.replace('Haiwell（海为）', '').replace('-工业物联网|国产PLC|HMI|SCADA', '').strip()

        # 提取下载链接
        dodown = re.findall(r'href=["\']([^"\']*dodown[^"\']*)["\']', html, re.I)
        if not dodown:
            print(f'  {did} {title}: 无下载链接，跳过')
            continue

        down_url = dodown[0].replace('&amp;', '&')
        if not down_url.startswith('http'):
            down_url = BASE + down_url

        if down_url in seen:
            continue

        print(f'  下载 {did} {title}...')
        try:
            data = fetch(down_url, timeout=30)
            if not data.startswith(b'%PDF'):
                # 可能是zip或其他格式
                if data.startswith(b'PK'):
                    print(f'    ZIP文件，跳过')
                    continue
                print(f'    非PDF ({len(data)}字节)，跳过')
                continue
            fname = re.sub(r'[\\/:*?"<>|]', '_', title)[:50]
            fpath = os.path.join(OUT, f'{fname}.pdf')
            with open(fpath, 'wb') as f:
                f.write(data)
            pages = get_pages(fpath)
            if pages == 0:
                print(f'    0页，跳过')
                os.remove(fpath)
                continue
            manifest.append({'name': title, 'url': down_url, 'pages': pages,
                           'type': '产品手册', 'size': len(data),
                           'brand': '海为', 'src': 'haiwell.com'})
            seen.add(down_url)
            print(f'    OK {pages}页 {len(data)//1024}KB')
        except Exception as e:
            print(f'    失败: {e}')
        time.sleep(0.5)

    json.dump(manifest, open(MANIFEST, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
    print(f'完成: {len(manifest)} 份')

if __name__ == '__main__':
    main()
