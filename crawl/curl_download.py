# -*- coding: utf-8 -*-
import json, subprocess, os, hashlib, re

d = json.load(open('dist/data/health_report.json'))
fails = [f for f in d.get('failures',[]) if f.get('brand') in ('海为','和利时','西安西普','三友','宏发','阿尔法电气')]

os.makedirs('dist/pdfs', exist_ok=True)
ok = 0; fail = 0; changed = False

s = open('dist/data/docs-3.js', encoding='utf-8').read()
m = re.search(r'DOCS=DOCS\.concat\((\[.*\])\);', s, re.DOTALL)
docs = json.loads(m.group(1))

for f in fails:
    url = f['url']; brand = f['brand']; title = f['title']
    bdir = 'dist/pdfs/' + re.sub(r'[^\w一-鿒]', '_', brand)
    os.makedirs(bdir, exist_ok=True)
    h = hashlib.md5(url.encode()).hexdigest()[:8]
    fname = re.sub(r'[^\w一-鿒.-]', '_', title)[:50] + '_' + h + '.pdf'
    fpath = os.path.join(bdir, fname)
    if os.path.exists(fpath) and os.path.getsize(fpath) > 1000:
        ok += 1; continue

    r = subprocess.run(
        ['curl', '-sL', '--max-time', '20', '-o', fpath,
         '-H', 'User-Agent: Mozilla/5.0 (Windows NT 10.0; Win64; x64)',
         '-w', '%{http_code}', url],
        capture_output=True, text=True)
    code = r.stdout.strip()
    if code == '200' and os.path.exists(fpath) and os.path.getsize(fpath) > 1000:
        head = open(fpath, 'rb').read(5)
        if head == b'%PDF':
            local = '/pdfs/' + os.path.basename(bdir) + '/' + fname
            for doc in docs:
                if doc.get('pdf') == url:
                    doc['pdf'] = local; changed = True
            ok += 1
            print('✅', brand, '|', title[:25], '|', os.path.getsize(fpath)//1024, 'KB')
        else:
            os.remove(fpath); fail += 1
    else:
        if os.path.exists(fpath): os.remove(fpath)
        fail += 1

if changed:
    out = '/* 工书库数据分片3 */\nDOCS=DOCS.concat(' + json.dumps(docs, ensure_ascii=False, separators=(',',':')) + ');\n'
    open('dist/data/docs-3.js', 'w', encoding='utf-8').write(out)

print('=== 结果: 成功', ok, '失败', fail, '===')
