#!/usr/bin/env python3
"""合信 co-trust.com 说明书采集器
下载页多分类标签，OSS直链PDF
"""
import json, os, time, urllib.request, urllib.parse, subprocess, re, sys

BASE = os.path.dirname(os.path.abspath(__file__))
PDF_DIR = os.path.join(BASE, '..', 'pdfs', 'cotion')
MANIFEST = os.path.join(BASE, 'cotion_manifest.json')
DOWNLOAD_PAGE = 'https://www.co-trust.com/Download/index.html'
HEADERS = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
           'Referer': 'https://www.co-trust.com/'}

TABS = ['全线产品选型手册','Simple系列PLC','CTH300系列PLC','CTH200/CTMC系列PLC',
        'CTSC系列PLC','伺服/变频器','HMI系列','MagicWorks PLC','MagicWorks HMI',
        'MagicWorks Tuner','MICO/OPC','其他软件/手册/驱动','库、设备描述文件','专用系统']

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
    print(f'合信: 已有 {len(old)} 条记录')

    all_docs = {}
    with sync_playwright() as p:
        browser = p.chromium.launch(executable_path=chromium_path(),
            args=['--no-sandbox','--disable-dev-shm-usage','--ignore-certificate-errors'])
        page = browser.new_page()
        page.goto(DOWNLOAD_PAGE, wait_until='domcontentloaded', timeout=30000)
        page.wait_for_timeout(4000)

        for tab in TABS:
            try:
                page.click(f'text={tab}', timeout=3000)
                page.wait_for_timeout(2000)
            except:
                continue
            # 获取PDF链接和名称
            items = page.eval_on_selector_all('a[href*=".pdf"]',
                '''els => els.map(e => ({href: e.href, text: e.innerText.trim(), 
                    parent: e.parentElement ? e.parentElement.innerText.trim().substring(0,100) : ""}))''')
            new_count = 0
            for item in items:
                url = item['href']
                if url in all_docs: continue
                # 名称从父元素提取
                name = item['text'] or ''
                if not name and item['parent']:
                    name = item['parent'].split('\n')[0]
                if not name:
                    name = url.split('/')[-1].replace('.pdf','')
                # 清理URL中的%!编码问题
                url = url.replace('%!P(MISSING)', 'P').replace('%!S(MISSING)', 'S')
                url = url.replace('%!C(MISSING)', 'C').replace('%!B(MISSING)', 'B')
                url = url.replace('%!c(MISSING)', 'c').replace('%!p(MISSING)', 'p')
                url = url.replace('%!R(MISSING)', 'R').replace('%!I(MISSING)', 'I')
                url = url.replace('%!L(MISSING)', 'L').replace('%!E(MISSING)', 'E')
                url = url.replace('%!M(MISSING)', 'M').replace('%!s(MISSING)', 's')
                url = url.replace('%!m(MISSING)', 'm').replace('%!i(MISSING)', 'i')
                all_docs[url] = {'name': name[:80], 'url': url, 'type': tab}
                new_count += 1
            print(f'  [{tab}]: {len(items)}个链接, 新增{new_count}, 累计{len(all_docs)}')

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
            req = urllib.request.Request(d['url'], headers=HEADERS)
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
                'brand': '合信', 'src': 'co-trust.com',
            })
            ok += 1
            print(f'  OK: {d["name"][:30]} ({pages}页)')
        except Exception as e:
            fail += 1
            print(f'  FAIL: {d["name"][:30]} - {str(e)[:40]}')
        time.sleep(0.2)

    json.dump(manifest, open(MANIFEST,'w',encoding='utf-8'), ensure_ascii=False, indent=1)
    print(f'合信完成: 新增{ok}, 失败{fail}, 总计{len(manifest)}')
    return {'brand': 'cotion', 'new': ok, 'fail': fail, 'total': len(manifest)}

if __name__ == '__main__':
    run()
