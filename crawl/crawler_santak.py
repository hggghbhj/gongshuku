#!/usr/bin/env python3
"""山特 SANTAK 下载中心采集器
OSS直链PDF: https://osscn.santak.com.cn/...
分类标签: 产品彩页/使用手册/用户许可协议等
"""
import json, os, time, urllib.request, urllib.parse, subprocess, re, sys

BASE = os.path.dirname(os.path.abspath(__file__))
PDF_DIR = os.path.join(BASE, '..', 'pdfs', 'santak')
MANIFEST = os.path.join(BASE, 'santak_manifest.json')
DOWNLOAD_PAGE = 'https://www.santak.com.cn/page/santak-downloads.html'
HEADERS = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
           'Referer': 'https://www.santak.com.cn/'}

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
    print(f'山特: 已有 {len(old)} 条记录')

    # 用playwright渲染页面，收集所有PDF
    try:
        sys.path.insert(0, BASE)
        from pw_util import chromium_path
        from playwright.sync_api import sync_playwright
    except ImportError:
        print('playwright不可用')
        return {'brand': 'santak', 'new': 0, 'fail': 0, 'total': len(old)}

    all_docs = {}
    with sync_playwright() as p:
        browser = p.chromium.launch(executable_path=chromium_path(),
            args=['--no-sandbox','--disable-dev-shm-usage','--ignore-certificate-errors'])
        page = browser.new_page()
        page.goto(DOWNLOAD_PAGE, wait_until='domcontentloaded', timeout=30000)
        page.wait_for_timeout(4000)

        # 找所有分类标签并点击
        tabs = page.eval_on_selector_all('[class*=tab], [class*=Tab], .nav-tab, .filter-item, li',
            'els => els.map(e => ({t:e.innerText.trim().substring(0,20), cls:e.className})).filter(x => x.t && /彩页|手册|协议|软件|批量/i.test(x.t))')
        print(f'找到 {len(tabs)} 个分类标签')

        # 先收集当前页面的PDF
        def collect_pdfs():
            pdfs = page.eval_on_selector_all('a[href*=".pdf"]', 'els => els.map(e => ({h:e.href, t:e.innerText.trim()}))')
            for item in pdfs:
                url = item['h']
                if url not in all_docs:
                    name = item['t'] or url.split('/')[-1].replace('.pdf','').replace('%20',' ')
                    all_docs[url] = {'name': name[:80], 'url': url, 'type': '使用手册'}

        collect_pdfs()
        print(f'当前页收集 {len(all_docs)} 个PDF')

        # 点击每个分类标签
        for tab in tabs:
            try:
                page.click(f'text={tab["t"]}', timeout=3000)
                page.wait_for_timeout(2000)
                collect_pdfs()
            except: pass

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
                'brand': '山特', 'src': 'santak.com.cn',
            })
            ok += 1
        except Exception as e:
            fail += 1
        time.sleep(0.2)

    json.dump(manifest, open(MANIFEST,'w',encoding='utf-8'), ensure_ascii=False, indent=1)
    print(f'山特完成: 新增{ok}, 失败{fail}, 总计{len(manifest)}')
    return {'brand': 'santak', 'new': ok, 'fail': fail, 'total': len(manifest)}

if __name__ == '__main__':
    run()
