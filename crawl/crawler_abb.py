#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""ABB采集器：从ABB Library WebFeed获取文档列表，批量下载PDF"""
import urllib.request, ssl, re, json, os, time, subprocess
from urllib.parse import quote

ctx = ssl.create_default_context()
ctx.check_hostname = False
ctx.verify_mode = ssl.CERT_NONE
HEADERS = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0 Safari/537.36'}

MANIFEST = 'abb_manifest.json'
PDF_DIR = 'pdfs/abb'
os.makedirs(PDF_DIR, exist_ok=True)

# 分类ID列表（主要产品分类）
CATEGORY_IDS = [
    'Root',  # 全部
]

def fetch(url):
    req = urllib.request.Request(url, headers=HEADERS)
    with urllib.request.urlopen(req, timeout=20, context=ctx) as r:
        return r.read()

def get_feed(category_id, lang='zh'):
    """获取WebFeed XML"""
    url = f'https://search.abb.com/library/WebFeed.ashx?categoryID={category_id}&LanguageCode={lang}'
    xml = fetch(url).decode('utf-8', errors='ignore')
    return xml

def parse_feed(xml):
    """解析XML，提取文档列表"""
    items = re.findall(r'<item>(.*?)</item>', xml, re.DOTALL)
    docs = []
    for item in items:
        title_m = re.search(r'<title><!\[CDATA\[(.*?)\]\]></title>', item, re.DOTALL)
        link_m = re.search(r'<link>([^<]+)</link>', item)
        date_m = re.search(r'<pubDate>([^<]+)</pubDate>', item)
        
        title = title_m.group(1).strip() if title_m else ''
        link = link_m.group(1).replace('&amp;', '&') if link_m else ''
        
        # 只保留PDF文档
        if 'pdf' not in title.lower():
            continue
        
        # 提取DocumentID
        docid_m = re.search(r'DocumentID=([^&]+)', link)
        docid = docid_m.group(1) if docid_m else ''
        
        docs.append({
            'title': title,
            'link': link,
            'docid': docid,
            'date': date_m.group(1) if date_m else '',
        })
    return docs

def get_pdf_url(download_url):
    """从Download.aspx页面提取PDF URL"""
    try:
        html = fetch(download_url).decode('utf-8', errors='ignore')
        # 找PDF链接（处理控制字符）
        pdf_m = re.search(r'(https?://[a-z0-9.]*library\.e\.abb\.com/public/[a-f0-9]+/[^\s"\'<>\\]+\.pdf\?x-sign=[^\s"\'<>\\]+)', html, re.I)
        if pdf_m:
            url = pdf_m.group(1).replace('&amp;', '&')
            # 清理控制字符
            url = re.sub(r'[\x00-\x1f\x7f-\x9f]', '', url)
            return url
    except Exception as e:
        pass
    return None

def download_pdf(pdf_url, docid):
    """下载PDF并校验"""
    try:
        data = fetch(pdf_url)
        if not data.startswith(b'%PDF'):
            return None, 'notpdf'
        if len(data) < 5000:
            return None, 'tiny'
        
        fn = f'abb_{docid}.pdf'
        fp = os.path.join(PDF_DIR, fn)
        with open(fp, 'wb') as f:
            f.write(data)
        
        # 获取页数
        try:
            result = subprocess.run(['pdfinfo', fp], capture_output=True, text=True, timeout=10)
            pages_m = re.search(r'Pages:\s+(\d+)', result.stdout)
            pages = int(pages_m.group(1)) if pages_m else 0
        except:
            pages = 0
        
        return {
            'fn': fn,
            'size': len(data),
            'pages': pages,
        }, None
    except Exception as e:
        return None, str(e)[:50]

def main():
    # 加载已有manifest
    if os.path.exists(MANIFEST):
        with open(MANIFEST, 'r', encoding='utf-8') as f:
            manifest = json.load(f)
    else:
        manifest = []
    
    existing_ids = {m['docid'] for m in manifest}
    
    # 获取文档列表
    all_docs = []
    for cat_id in CATEGORY_IDS:
        print(f"获取分类: {cat_id}")
        xml = get_feed(cat_id, lang='zh')
        docs = parse_feed(xml)
        print(f"  找到 {len(docs)} 个文档")
        all_docs.extend(docs)
    
    # 去重
    seen = set()
    unique_docs = []
    for d in all_docs:
        if d['docid'] and d['docid'] not in seen:
            seen.add(d['docid'])
            unique_docs.append(d)
    
    print(f"\n总计: {len(unique_docs)} 个唯一文档")
    print(f"已存在: {len(existing_ids)} 个")
    print(f"新增: {len(unique_docs) - len(existing_ids & {d['docid'] for d in unique_docs})} 个")
    
    # 下载新文档
    success = 0
    fail = 0
    skip = 0
    
    for i, doc in enumerate(unique_docs):
        if doc['docid'] in existing_ids:
            skip += 1
            continue
        
        print(f"[{i+1}/{len(unique_docs)}] {doc['title'][:40]}...")
        
        # 获取PDF URL
        pdf_url = get_pdf_url(doc['link'])
        if not pdf_url:
            print(f"  失败: 找不到PDF链接")
            fail += 1
            continue
        
        # 下载PDF
        result, err = download_pdf(pdf_url, doc['docid'])
        if result:
            manifest.append({
                'docid': doc['docid'],
                'name': doc['title'],
                'url': pdf_url,
                'fn': result['fn'],
                'size': result['size'],
                'pages': result['pages'],
                'date': doc['date'],
                'cat': 'ABB',
            })
            print(f"  OK ({result['pages']}页, {result['size']//1024}KB)")
            success += 1
        else:
            print(f"  失败: {err}")
            fail += 1
        
        time.sleep(0.5)  # 避免限流
    
    # 保存manifest
    with open(MANIFEST, 'w', encoding='utf-8') as f:
        json.dump(manifest, f, ensure_ascii=False, indent=2)
    
    print(f"\n完成: 成功{success}, 失败{fail}, 跳过{skip}, 总计{len(manifest)}")

if __name__ == '__main__':
    main()
