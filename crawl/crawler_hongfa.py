#!/usr/bin/env python3
# 宏发继电器 hongfa.com 产品手册采集器
# 下载页 https://www.hongfa.com/en/service/down
import json, os, re, time, subprocess
from pypdf import PdfReader

UA = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
BASE = 'https://www.hongfa.com'
PDF_BASE = 'https://source.hongfa.com'
OUT = 'pdfs/hongfa'
MANIFEST = 'hongfa_manifest.json'

def fetch(url, timeout=20):
    r = subprocess.run(['curl','-s','-L','--max-time',str(timeout),
        '-A',UA,'-H',f'Referer: {BASE}',url],
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

    # 抓取下载页
    print('抓取宏发下载页...')
    try:
        html = fetch(f'{BASE}/en/service/down').decode('utf-8', errors='ignore')
    except Exception as e:
        print(f'下载页失败: {e}')
        return

    # 提取PDF链接
    pdfs = re.findall(r'file=["\']?([^"\'&> ]+\.pdf)', html, re.I)
    # 提取名称（从viewer链接附近的文本）
    names = re.findall(r'<a[^>]*href=["\'][^"\']*viewer\.html\?file=[^"\']*["\'][^>]*>([^<]+)</a>', html, re.I)
    if not names:
        names = re.findall(r'>([^<]{3,60})</a>', html)

    print(f'发现 {len(set(pdfs))} 个PDF')

    for i, pdf_path in enumerate(set(pdfs)):
        # 规范化路径
        pdf_path = pdf_path.replace('\\', '/')
        if not pdf_path.startswith('/'):
            pdf_path = '/' + pdf_path
        url = PDF_BASE + pdf_path
        if url in seen:
            continue

        # 从路径提取文件名作为名称
        fname = os.path.basename(pdf_path).replace('.pdf', '')
        name = f'宏发 {fname} 产品手册'
        # 尝试从names匹配
        if i < len(names):
            n = names[i].strip()
            if n and len(n) > 2:
                name = n

        print(f'  下载 {name}...')
        try:
            data = fetch(url, timeout=30)
            if not data.startswith(b'%PDF'):
                print(f'    非PDF，跳过')
                continue
            fpath = os.path.join(OUT, f'{fname}.pdf')
            with open(fpath, 'wb') as f:
                f.write(data)
            pages = get_pages(fpath)
            if pages == 0:
                print(f'    0页，跳过')
                os.remove(fpath)
                continue
            manifest.append({'name': name, 'url': url, 'pages': pages,
                           'type': '产品手册', 'size': len(data),
                           'brand': '宏发', 'src': 'hongfa.com'})
            seen.add(url)
            print(f'    OK {pages}页 {len(data)//1024}KB')
        except Exception as e:
            print(f'    失败: {e}')
        time.sleep(0.5)

    json.dump(manifest, open(MANIFEST, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
    print(f'完成: {len(manifest)} 份')

if __name__ == '__main__':
    main()
