#!/usr/bin/env python3
"""四方电气 SIMPHOENIX 手册采集器
手册页PDF直链: https://www.simphoenix.com/uploads/xxx.pdf
"""
import json, os, time, urllib.request, urllib.parse, subprocess, re, sys

BASE = os.path.dirname(os.path.abspath(__file__))
PDF_DIR = os.path.join(BASE, '..', 'pdfs', 'simphoenix')
MANIFEST = os.path.join(BASE, 'simphoenix_manifest.json')
MANUAL_PAGE = 'https://www.simphoenix.com/download/manual/'
HEADERS = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
           'Referer': 'https://www.simphoenix.com/'}

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
    print(f'四方电气: 已有 {len(old)} 条记录')

    # 抓取手册页所有PDF链接
    try:
        req = urllib.request.Request(MANUAL_PAGE, headers=HEADERS)
        html = urllib.request.urlopen(req, timeout=30).read().decode('utf-8', errors='ignore')
    except Exception as e:
        print(f'抓取页面失败: {e}')
        return {'brand': 'simphoenix', 'new': 0, 'fail': 0, 'total': len(old)}

    pdfs = re.findall(r'href=["\']([^"\']*\.pdf)["\']', html, re.I)
    # 同时提取PDF旁边的标题文本
    all_docs = {}
    for url in pdfs:
        if url.startswith('//'):
            url = 'https:' + url
        elif url.startswith('/'):
            url = 'https://www.simphoenix.com' + url
        elif not url.startswith('http'):
            url = 'https://www.simphoenix.com/' + url
        if 'simphoenix' not in url: continue
        name = url.split('/')[-1].replace('.pdf','').replace('%20',' ').replace('_',' ')
        if url not in all_docs:
            all_docs[url] = {'name': name[:80], 'url': url, 'type': '用户手册'}
    print(f'发现 {len(all_docs)} 个PDF')

    to_download = [d for d in all_docs.values() if d['url'] not in old or old[d['url']].get('pages',0)==0]
    print(f'待下载: {len(to_download)} 个')

    manifest = list(old.values())
    ok, fail = 0, 0
    for d in to_download:
        safe_name = re.sub(r'[\\/:*?"<>|]','_',d['name'][:50])
        dest = os.path.join(PDF_DIR, f'{safe_name}_{abs(hash(d["url"]))%100000}.pdf')
        try:
            encoded = urllib.parse.quote(d['url'], safe=":/?=&%")
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
                'brand': '四方电气', 'src': 'simphoenix.com',
            })
            ok += 1
        except Exception as e:
            fail += 1
        time.sleep(0.2)

    json.dump(manifest, open(MANIFEST,'w',encoding='utf-8'), ensure_ascii=False, indent=1)
    print(f'四方电气完成: 新增{ok}, 失败{fail}, 总计{len(manifest)}')
    return {'brand': 'simphoenix', 'new': ok, 'fail': fail, 'total': len(manifest)}

if __name__ == '__main__':
    run()
