#!/usr/bin/env python3
# 米格电机 mege.cn 产品样册采集器
# 下载页 https://www.mege.cn/index.php?ac=Article&at=List&tid=42
import json, os, re, time, subprocess

UA = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
BASE = 'https://www.mege.cn'
PAGE = f'{BASE}/index.php?ac=Article&at=List&tid=42'
OUT = 'pdfs/mege'
MANIFEST = 'mege_manifest.json'

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

    print('抓取米格下载页...')
    html = fetch(PAGE, timeout=30).decode('utf-8', errors='ignore')

    # 提取PDF链接
    pdfs = re.findall(r'href=["\']([^"\']*\.pdf)["\']', html, re.I)
    # 提取名称（页面中的样册名称，只取短名称）
    names = re.findall(r'>(米格[^<]{2,20}(?:样册|手册))<', html)
    names = [n.strip() for n in names if n.strip() and len(n.strip()) < 25]
    if not names:
        names = ['米格伺服电机样册', '米格步进电机样册', '米格主轴电机样册',
                 '米格低压伺服电机样册', '米格新能源汽车电机样册']

    print(f'发现 {len(set(pdfs))} 个PDF, {len(names)} 个名称')

    items = {}
    for i, pdf_path in enumerate(set(pdfs)):
        if pdf_path.startswith('//'):
            url = 'https:' + pdf_path
        elif pdf_path.startswith('/'):
            url = BASE + pdf_path
        elif not pdf_path.startswith('http'):
            url = BASE + '/' + pdf_path
        else:
            url = pdf_path
        name = names[i] if i < len(names) else f'米格电机样册{i+1}'
        items[url] = name

    for url, name in items.items():
        if url in seen:
            continue
        print(f'  下载 {name}...')
        try:
            data = fetch(url, timeout=120)
            if not data.startswith(b'%PDF'):
                print(f'    非PDF({len(data)}字节)，跳过')
                continue
            fname = os.path.basename(url)
            fpath = os.path.join(OUT, fname)
            with open(fpath, 'wb') as f:
                f.write(data)
            pages = get_pages(fpath)
            if pages == 0:
                print(f'    0页，跳过')
                os.remove(fpath)
                continue
            manifest.append({'name': name, 'url': url, 'pages': pages,
                           'type': '产品样册', 'size': len(data),
                           'brand': '米格电机', 'src': 'mege.cn'})
            seen.add(url)
            print(f'    OK {pages}页 {len(data)//1024}KB')
        except Exception as e:
            print(f'    失败: {e}')
        time.sleep(0.5)

    json.dump(manifest, open(MANIFEST, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
    print(f'完成: {len(manifest)} 份')

if __name__ == '__main__':
    main()
