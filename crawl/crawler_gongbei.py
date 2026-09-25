#!/usr/bin/env python3
"""工贝电子 jngbdz.com 说明书采集器
产品详情页含PDF直链: https://jngbdz.com/file/...
"""
import json, os, time, urllib.request, urllib.parse, subprocess, re, sys

BASE = os.path.dirname(os.path.abspath(__file__))
PDF_DIR = os.path.join(BASE, '..', 'pdfs', 'gongbei')
MANIFEST = os.path.join(BASE, 'gongbei_manifest.json')
BASE_URL = 'https://jngbdz.com/'
HEADERS = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
           'Referer': 'https://jngbdz.com/'}

# 产品详情页
PRODUCT_PAGES = [
    'web-SR_ST.html', 'web-Smart-EM.html', 'web-GR_GT.html', 'web-KPLC.html',
    'web-200.html', 'web-200-EM.html', 'web-1200.html', 'web-IO.html',
    'web-HMI.html', 'web-cable.html', 'web-GS700.html', 'web-T100.html',
    'web-index.html',
]

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
    sys.path.insert(0, BASE)
    from pw_util import chromium_path
    from playwright.sync_api import sync_playwright

    os.makedirs(PDF_DIR, exist_ok=True)
    old = {}
    if os.path.exists(MANIFEST):
        for item in json.load(open(MANIFEST, encoding='utf-8')):
            old[item['url']] = item
    print(f'工贝: 已有 {len(old)} 条记录')

    all_docs = {}
    with sync_playwright() as p:
        browser = p.chromium.launch(executable_path=chromium_path(),
            args=['--no-sandbox','--disable-dev-shm-usage','--ignore-certificate-errors'])
        page = browser.new_page()

        for page_name in PRODUCT_PAGES:
            url = BASE_URL + page_name
            try:
                page.goto(url, wait_until='domcontentloaded', timeout=20000)
                page.wait_for_timeout(2000)
            except:
                continue
            html = page.content()
            pdfs = re.findall(r'href=["\']([^"\']*\.pdf)["\']', html, re.I)
            new_count = 0
            for pdf in pdfs:
                # 转相对路径为绝对URL
                if pdf.startswith('./'):
                    full = BASE_URL + pdf[2:]
                elif pdf.startswith('/'):
                    full = BASE_URL + pdf[1:]
                elif pdf.startswith('http'):
                    full = pdf
                else:
                    full = BASE_URL + pdf
                if full in all_docs: continue
                name = full.split('/')[-1].replace('.pdf','').replace('%20',' ')
                all_docs[full] = {'name': name[:80], 'url': full, 'type': page_name.replace('.html','')}
                new_count += 1
            if new_count > 0:
                print(f'  [{page_name}]: {len(pdfs)}个PDF, 新增{new_count}, 累计{len(all_docs)}')

        browser.close()

    print(f'共发现 {len(all_docs)} 个PDF')
    to_download = [d for d in all_docs.values() if d['url'] not in old or old[d['url']].get('pages',0)==0]
    print(f'待下载: {len(to_download)} 个')

    manifest = list(old.values())
    ok, fail = 0, 0
    for d in to_download:
        safe_name = re.sub(r'[\\/:*?"<>|]','_',d['name'][:50])
        dest = os.path.join(PDF_DIR, f'{safe_name}_{abs(hash(d["url"]))%100000}.pdf')
        try:
            # 编码中文URL
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
                'brand': '工贝电子', 'src': 'jngbdz.com',
            })
            ok += 1
            print(f'  OK: {d["name"][:30]} ({pages}页)')
        except Exception as e:
            fail += 1
            print(f'  FAIL: {d["name"][:30]} - {str(e)[:40]}')
        time.sleep(0.2)

    json.dump(manifest, open(MANIFEST,'w',encoding='utf-8'), ensure_ascii=False, indent=1)
    print(f'工贝完成: 新增{ok}, 失败{fail}, 总计{len(manifest)}')
    return {'brand': 'gongbei', 'new': ok, 'fail': fail, 'total': len(manifest)}

if __name__ == '__main__':
    run()
