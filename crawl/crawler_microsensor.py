#!/usr/bin/env python3
# 麦克传感器 microsensor.cn 手册采集器
# API: https://www.microsensor.cn/index/download/searchFiles
import json, os, re, time, subprocess

UA = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
API = 'https://www.microsensor.cn/index/download/searchFiles'
OUT = 'pdfs/microsensor'
MANIFEST = 'microsensor_manifest.json'

def fetch(url, timeout=60, referer=None):
    cmd = ['curl', '-s', '-L', '--max-time', str(timeout), '-A', UA]
    if referer:
        cmd += ['-e', referer]
    cmd.append(url)
    r = subprocess.run(cmd, capture_output=True, timeout=timeout+5)
    return r.stdout

def post_api(page, limit=50):
    r = subprocess.run(['curl', '-s', '-L', '--max-time', '30',
        '-A', UA, '-H', 'Content-Type: application/json',
        '-H', 'Referer: https://www.microsensor.cn/download',
        '-X', 'POST', API,
        '-d', json.dumps({'page': page, 'limit': limit})],
        capture_output=True, timeout=35)
    try:
        return json.loads(r.stdout.decode('utf-8', errors='ignore'))
    except:
        return None

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

    # 获取所有文件列表
    all_files = []
    for page in range(1, 20):
        print(f'获取API第{page}页...')
        data = post_api(page)
        if not data or not data.get('result'):
            break
        items = data.get('resource', [])
        if not items:
            break
        all_files.extend(items)
        print(f'  本页{len(items)}条，累计{len(all_files)}')
        if len(items) < 50:
            break
        time.sleep(0.5)

    print(f'共发现 {len(all_files)} 个文件')

    for item in all_files:
        url = item.get('file', '')
        name = item.get('title', '')
        if not url or not name:
            continue
        if url in seen:
            continue
        # 只下载PDF
        if not url.lower().endswith('.pdf'):
            continue
        print(f'  下载 {name[:50]}...')
        try:
            data = fetch(url, timeout=120, referer='https://www.microsensor.cn/download')
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
            # 判断类型
            ftype = '说明书'
            if '选型' in name or '样本' in name or 'catalog' in name.lower():
                ftype = '选型资料'
            manifest.append({'name': name, 'url': url, 'pages': pages,
                           'type': ftype, 'size': len(data),
                           'brand': '麦克传感器', 'src': 'microsensor.cn'})
            seen.add(url)
            print(f'    OK {pages}页 {len(data)//1024}KB')
        except Exception as e:
            print(f'    失败: {e}')
        time.sleep(0.3)

    json.dump(manifest, open(MANIFEST, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
    print(f'完成: {len(manifest)} 份')

if __name__ == '__main__':
    main()
