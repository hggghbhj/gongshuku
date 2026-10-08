#!/usr/bin/env python3
"""宇电 Yudian 仪表下载中心采集器
多下载分类页，PDF直链: https://www.yudian.com/UserFiles/upload/file/日期/xxx.pdf
"""
import json, os, time, urllib.request, urllib.parse, subprocess, re, sys

BASE = os.path.dirname(os.path.abspath(__file__))
PDF_DIR = os.path.join(BASE, '..', 'pdfs', 'yudian')
MANIFEST = os.path.join(BASE, 'yudian_manifest.json')
PAGES = [
    'https://www.yudian.com/down/10039.html',
    'https://www.yudian.com/down/10040.html',
    'https://www.yudian.com/down/10042.html',
    'https://www.yudian.com/down/10043.html',
    'https://www.yudian.com/down/10044.html',
    'https://www.yudian.com/down/10041.html',
]
HEADERS = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
           'Referer': 'https://www.yudian.com/'}

def get_pdf_pages(fp):
    try:
        from pypdf import PdfReader
        return len(PdfReader(fp).pages)
    except:
        try:
            r = subprocess.run(['pdfinfo', fp], capture_output=True, text=True, timeout=15)
            for line in r.stdout.splitlines():
                if line.startswith('Pages:'):
                    return int(line.split(':')[1].strip())
        except: pass
    return 0

def run():
    os.makedirs(PDF_DIR, exist_ok=True)
    old = {}
    if os.path.exists(MANIFEST):
        for item in json.load(open(MANIFEST, encoding='utf-8')):
            old[item['url']] = item
    print(f'宇电: 已有 {len(old)} 条记录')

    all_docs = {}
    for page_url in PAGES:
        try:
            req = urllib.request.Request(page_url, headers=HEADERS)
            html = urllib.request.urlopen(req, timeout=30).read().decode('utf-8', errors='ignore')
            pdfs = re.findall(r'href=["\']([^"\']*\.pdf)["\']', html, re.I)
            for url in pdfs:
                if url.startswith('//'):
                    url = 'https:' + url
                elif url.startswith('/'):
                    url = 'https://www.yudian.com' + url
                elif not url.startswith('http'):
                    url = 'https://www.yudian.com/' + url
                if 'yudian' not in url: continue
                name = url.split('/')[-1].replace('.pdf','').replace('%20',' ').strip()
                if url not in all_docs:
                    all_docs[url] = {'name': name[:80], 'url': url, 'type': '产品手册'}
        except Exception as e:
            print(f'抓取 {page_url} 失败: {e}')
    print(f'发现 {len(all_docs)} 个PDF')

    to_download = [d for d in all_docs.values() if d['url'] not in old or old[d['url']].get('pages',0)==0]
    print(f'待下载: {len(to_download)} 个')

    manifest = list(old.values())
    ok, fail = 0, 0
    for d in to_download:
        safe_name = re.sub(r'[\\/:*?"<>|]','_',d['name'][:50])
        dest = os.path.join(PDF_DIR, f'{safe_name}_{abs(hash(d["url"]))%100000}.pdf')
        try:
            encoded = urllib.parse.quote(d['url'], safe=":/?=&%()（）《》_-.,")
            req = urllib.request.Request(encoded, headers=HEADERS)
            data = urllib.request.urlopen(req, timeout=60).read()
            if len(data) < 1000 or data[:4] != b'%PDF':
                fail += 1; continue
            with open(dest,'wb') as f: f.write(data)
            pages = get_pdf_pages(dest)
            if pages == 0:
                os.remove(dest); fail += 1; continue
            manifest.append({
                'name': d['name'], 'url': d['url'], 'pages': pages,
                'type': d['type'], 'size': os.path.getsize(dest),
                'brand': '宇电', 'src': 'yudian.com',
            })
            ok += 1
        except Exception as e:
            fail += 1
        time.sleep(0.2)

    json.dump(manifest, open(MANIFEST,'w',encoding='utf-8'), ensure_ascii=False, indent=1)
    print(f'宇电完成: 新增{ok}, 失败{fail}, 总计{len(manifest)}')
    return {'brand': 'yudian', 'new': ok, 'fail': fail, 'total': len(manifest)}

if __name__ == '__main__':
    run()
