#!/usr/bin/env python3
"""汇川 inovance 说明书采集器
搜索API: https://www.inovance.com/portal-front/api/home/search?key=XXX&showChannel=2
PDF直链: https://www.inovance.com/filevault-ext/...
"""
import json, os, time, urllib.request, urllib.parse, subprocess, sys

BASE = os.path.dirname(os.path.abspath(__file__))
PDF_DIR = os.path.join(BASE, '..', 'pdfs', 'inovance')
MANIFEST = os.path.join(BASE, 'inovance_manifest.json')
SEARCH_API = 'https://www.inovance.com/portal-front/api/home/search?key={kw}&showChannel=2'
PDF_BASE = 'https://www.inovance.com'
HEADERS = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
           'Referer': 'https://www.inovance.com/'}

# 搜索关键词（产品系列+通用文档类型）
KEYWORDS = [
    # 变频器系列
    'MD200','MD290','MD310','MD320','MD380','MD500','MD500E','MD510','MD520','MD810','MD880',
    'CP320','CP600','CP700','MD210','MD310','MD480','MD800','MD900',
    # 伺服系列
    'SV660','SV630','SV520','SV510','IS620','IS620F','IS620N','IS810','MS1','MS1H','MH1',
    # PLC系列
    'H3U','H5U','H1U','H2U','H0U','AM400','AM600','AC700','AC800','GL10','GR10','Easy',
    # HMI/触摸屏
    'IT6000','IT7000','INOTOUCH','IT5000',
    # 通用文档类型
    '用户手册','快速入门','选型手册','安装手册','调试手册','功能手册','硬件手册',
    '变频器','伺服','PLC','运动控制','触摸屏','通讯','总线',
]

def http_get(url, timeout=20):
    req = urllib.request.Request(url, headers=HEADERS)
    return urllib.request.urlopen(req, timeout=timeout).read()

def search(kw):
    url = SEARCH_API.format(kw=urllib.parse.quote(kw))
    try:
        data = json.loads(http_get(url, timeout=15))
        return data.get('data', {}).get('doc', {})
    except Exception as e:
        print(f'  搜索[{kw}]失败: {e}')
        return {}

# 只采集说明书类文档，跳过图纸/认证/彩页
ALLOWED_TYPES = {'用户手册','快速入门','选型手册','安装手册','调试手册','功能手册','硬件手册',
                 '参数手册','通信手册','通讯手册','编程手册','排障手册','维护手册','应用手册',
                 '设备手册','系统手册','指令手册','安全指南','Others'}

def extract_docs(doc_data):
    """从嵌套doc结构提取所有PDF文档"""
    results = []
    for cat_id, cat in doc_data.items():
        if not isinstance(cat, dict): continue
        for sub_name, sub_list in cat.items():
            if not isinstance(sub_list, list): continue
            if sub_name not in ALLOWED_TYPES: continue
            for item in sub_list:
                if not isinstance(item, dict): continue
                url = item.get('docUrl', '')
                if not url or not url.endswith('.pdf'): continue
                name = item.get('docName', '') or item.get('highTitle', '')
                # 去掉HTML标签
                name = name.replace('<font class=\'keyword-highlight\'>','').replace('</font>','')
                results.append({
                    'name': name.strip(),
                    'url': url,
                    'type': sub_name,
                    'cat': str(cat_id),
                    'size': item.get('fileSize', 0),
                    'version': item.get('docEition', ''),
                    'date': item.get('createTime', ''),
                })
    return results

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

def download_pdf(url, dest):
    # 编码非ASCII和空格，保留路径常见字符
    encoded = urllib.parse.quote(url, safe="/()（）《》_-.,")
    full = PDF_BASE + encoded
    try:
        data = http_get(full, timeout=60)
        if len(data) < 1000 or data[:4] != b'%PDF':
            return False, 0
        with open(dest, 'wb') as f:
            f.write(data)
        pages = get_pdf_pages(dest)
        if pages == 0:
            os.remove(dest)
            return False, 0
        return True, pages
    except Exception as e:
        return False, 0

def run():
    os.makedirs(PDF_DIR, exist_ok=True)
    old = {}
    if os.path.exists(MANIFEST):
        for item in json.load(open(MANIFEST, encoding='utf-8')):
            old[item['url']] = item
    print(f'汇川: 已有 {len(old)} 条记录')

    # 多关键词搜索，去重
    all_docs = {}
    for kw in KEYWORDS:
        doc_data = search(kw)
        docs = extract_docs(doc_data)
        new_count = 0
        for d in docs:
            if d['url'] not in all_docs:
                all_docs[d['url']] = d
                new_count += 1
        print(f'  搜索[{kw}]: {len(docs)}条, 新增去重后 {new_count}条, 累计 {len(all_docs)}条')
        time.sleep(0.3)

    # 过滤已下载且健康的
    to_download = []
    for url, d in all_docs.items():
        if url in old and old[url].get('pages', 0) > 0:
            continue
        to_download.append(d)
    print(f'待下载: {len(to_download)} 个PDF')

    manifest = list(old.values())
    ok, fail = 0, 0
    for i, d in enumerate(to_download):
        safe_name = d['name'][:60].replace('/','_').replace('\\','_').replace(':','_')
        dest = os.path.join(PDF_DIR, f'{safe_name}_{abs(hash(d["url"]))%100000}.pdf')
        success, pages = download_pdf(d['url'], dest)
        if success:
            manifest.append({
                'name': d['name'], 'url': d['url'], 'pages': pages,
                'type': d['type'], 'date': d['date'], 'size': os.path.getsize(dest),
                'brand': '汇川', 'src': 'inovance.com',
            })
            ok += 1
            if (i+1) % 10 == 0:
                print(f'  进度 {i+1}/{len(to_download)}, 成功{ok} 失败{fail}')
        else:
            fail += 1
        time.sleep(0.2)

    json.dump(manifest, open(MANIFEST, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
    print(f'汇川完成: 新增{ok}, 失败{fail}, 总计{len(manifest)}')
    return {'brand': 'inovance', 'new': ok, 'fail': fail, 'total': len(manifest)}

if __name__ == '__main__':
    run()
