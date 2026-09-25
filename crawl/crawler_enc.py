#!/usr/bin/env python3
"""易能电气 enc.net.cn 说明书采集器
PC版下载页含PDF直链，单页无翻页
"""
import json, os, time, urllib.request, subprocess, re, sys

BASE = os.path.dirname(os.path.abspath(__file__))
PDF_DIR = os.path.join(BASE, '..', 'pdfs', 'enc')
MANIFEST = os.path.join(BASE, 'enc_manifest.json')
DOWNLOAD_PAGE = 'http://www.enc.net.cn/service/filedownlaod/productType/index.html'
HEADERS = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}

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
    print(f'易能: 已有 {len(old)} 条记录')

    all_docs = {}
    with sync_playwright() as p:
        browser = p.chromium.launch(executable_path=chromium_path(),
            args=['--no-sandbox','--disable-dev-shm-usage','--ignore-certificate-errors'])
        context = browser.new_context(user_agent=HEADERS['User-Agent'])
        page = context.new_page()
        page.goto(DOWNLOAD_PAGE, wait_until='domcontentloaded', timeout=30000)
        page.wait_for_timeout(3000)

        items = page.eval_on_selector_all('a[href$=".pdf"]',
            '''els => {
                const seen = new Set();
                const result = [];
                for(const e of els) {
                    if(seen.has(e.href)) continue;
                    seen.add(e.href);
                    let parent = e.parentElement;
                    let text = parent ? parent.innerText.trim() : '';
                    let name = text.split('\\n')[0] || e.innerText.trim() || e.href.split('/').pop();
                    result.push({href: e.href, name: name.substring(0,80)});
                }
                return result;
            }''')
        for item in items:
            all_docs[item['href']] = {'name': item['name'], 'url': item['href'], 'type': '使用手册'}
        browser.close()

    print(f'发现 {len(all_docs)} 个PDF')
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
                'brand': '易能', 'src': 'enc.net.cn',
            })
            ok += 1
            print(f'  OK: {d["name"][:30]} ({pages}页)')
        except Exception as e:
            fail += 1
            print(f'  FAIL: {d["name"][:30]} - {e}')
        time.sleep(0.2)

    json.dump(manifest, open(MANIFEST,'w',encoding='utf-8'), ensure_ascii=False, indent=1)
    print(f'易能完成: 新增{ok}, 失败{fail}, 总计{len(manifest)}')
    return {'brand': 'enc', 'new': ok, 'fail': fail, 'total': len(manifest)}

if __name__ == '__main__':
    run()
