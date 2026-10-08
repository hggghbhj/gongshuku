#!/usr/bin/env python3
"""
工书库说明书自动检测脚本 v2
检测所有PDF是否能正常打开在线预览，记录异常文件。
修复：URL中文编码、相对路径补全、Referer、SSL忽略
"""
import json, os, time, urllib.request, urllib.parse, ssl, sys
from concurrent.futures import ThreadPoolExecutor, as_completed

DOCS_FILE = "../dist/data/docs-3.js"
REPORT_FILE = "pdf_health_report.json"
TIMEOUT = 15
MAX_WORKERS = 10
BASE_URL = "https://gongshuku.pages.dev"

# Referer配置
REFERERS = {
    'xinje.com': 'https://www.xinje.com/web/downloadCenter/index',
    'sinee.cn': 'https://www.sinee.cn/',
    'euradrives.com': 'https://www.euradrives.com/service/down.html',
    'hcfa.cn': 'https://www.hcfa.cn/',
    'coolmay.com': 'http://www.coolmay.com/',
    'e-elitech.com': 'https://www.e-elitech.com/',
    'leisai.com': 'https://www.leisai.com/downloads.html',
    'powtran.com': 'https://www.powtran.com/',
    'invt.com.cn': 'https://www.invt.com.cn/dowload-15',
    'mitsubishielectric.com': 'https://www.mitsubishielectric.com/fa/download/',
    'siemens.com.cn': 'https://www.ad.siemens.com.cn/download/',
    'mcgspro.com': 'https://www.mcgspro.com/',
    'haiwell.com': 'https://haiwell.com/',
    'delixidrive.com': 'https://www.delixidrive.com/',
    'se.com': 'https://www.se.com/cn/zh/download/',
    'huceen.cn': 'https://www.huceen.cn/',
    'xichi.com': 'http://www.xichi.com/',
    'gwinstek.com.cn': 'https://www.gwinstek.com.cn/',
}

def get_referer(url):
    for k, v in REFERERS.items():
        if k in url:
            return v
    try:
        from urllib.parse import urlparse
        return urlparse(url).scheme + '://' + urlparse(url).netloc + '/'
    except:
        return ''

def fix_url(url):
    """修复URL：补全相对路径、编码中文"""
    if not url:
        return url
    # 相对路径补全
    if url.startswith('/'):
        url = BASE_URL + url
    # 编码中文和特殊字符
    try:
        from urllib.parse import urlparse, quote, unquote
        parsed = urlparse(url)
        # 只编码path部分，保留安全字符
        path = quote(parsed.path, safe="/:@!$&'()*+,;=-._~")
        url = parsed._replace(path=path).geturl()
    except:
        pass
    return url

def load_docs():
    with open(DOCS_FILE, 'r', encoding='utf-8') as f:
        content = f.read()
    start = content.find('[')
    end = content.rfind(']')
    return json.loads(content[start:end+1])

def check_pdf(doc):
    """检测单个PDF是否正常"""
    url = doc.get('pdf', '')
    if not url:
        return {'ok': False, 'reason': 'no_url', 'url': url}
    
    # 跳过压缩包
    fm = url.lower().split('?')[0].split('.')[-1] if '.' in url.lower().split('?')[0] else ''
    if fm in ['zip', 'rar', '7z', 'gz']:
        return {'ok': True, 'reason': 'archive', 'url': url}
    
    url = fix_url(url)
    
    try:
        ctx = ssl.create_default_context()
        ctx.check_hostname = False
        ctx.verify_mode = ssl.CERT_NONE
        
        req = urllib.request.Request(url, headers={
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
            'Accept': 'application/pdf,*/*',
            'Referer': get_referer(url),
            'Range': 'bytes=0-1023'
        })
        start_time = time.time()
        resp = urllib.request.urlopen(req, timeout=TIMEOUT, context=ctx)
        elapsed = time.time() - start_time
        
        status = resp.status
        content_type = resp.headers.get('Content-Type', '')
        content_length = resp.headers.get('Content-Length', '')
        first_bytes = resp.read(1024)
        
        is_pdf = first_bytes[:4] == b'%PDF'
        
        if status != 200 and status != 206:
            return {'ok': False, 'reason': f'http_{status}', 'url': url, 'elapsed': round(elapsed, 2)}
        if not is_pdf:
            return {'ok': False, 'reason': 'not_pdf', 'url': url, 'content_type': content_type, 'elapsed': round(elapsed, 2)}
        
        return {
            'ok': True, 
            'url': url, 
            'status': status,
            'content_type': content_type,
            'size': int(content_length) if content_length else 0,
            'elapsed': round(elapsed, 2)
        }
    except urllib.error.HTTPError as e:
        return {'ok': False, 'reason': f'http_{e.code}', 'url': url}
    except Exception as e:
        return {'ok': False, 'reason': f'error_{str(e)[:60]}', 'url': url}

def main():
    print("=== 工书库说明书自动检测 v2 ===")
    docs = load_docs()
    print(f"总文档数: {len(docs)}")
    
    pdf_docs = [d for d in docs if d.get('pdf')]
    print(f"待检测PDF: {len(pdf_docs)}份")
    print()
    
    results = []
    ok_count = 0
    fail_count = 0
    slow_count = 0
    
    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
        future_to_doc = {executor.submit(check_pdf, d): d for d in pdf_docs}
        for i, future in enumerate(as_completed(future_to_doc)):
            doc = future_to_doc[future]
            try:
                result = future.result()
                result['brand'] = doc.get('b', '')
                result['title'] = doc.get('t', '')
                results.append(result)
                
                if result['ok']:
                    ok_count += 1
                    if result.get('elapsed', 0) > 5:
                        slow_count += 1
                else:
                    fail_count += 1
                
                if (i+1) % 200 == 0:
                    print(f"进度: {i+1}/{len(pdf_docs)}, 正常:{ok_count}, 异常:{fail_count}, 慢:{slow_count}")
            except Exception as e:
                fail_count += 1
    
    # 生成报告
    report = {
        'scan_time': time.strftime('%Y-%m-%d %H:%M:%S'),
        'total': len(pdf_docs),
        'ok': ok_count,
        'fail': fail_count,
        'slow': slow_count,
        'failures': [r for r in results if not r['ok']],
        'slow_list': [r for r in results if r['ok'] and r.get('elapsed', 0) > 5],
        'by_brand': {}
    }
    
    from collections import Counter
    brand_ok = Counter()
    brand_fail = Counter()
    for r in results:
        brand = r.get('brand', '未知')
        if r['ok']:
            brand_ok[brand] += 1
        else:
            brand_fail[brand] += 1
    
    for brand in set(list(brand_ok.keys()) + list(brand_fail.keys())):
        report['by_brand'][brand] = {
            'ok': brand_ok.get(brand, 0),
            'fail': brand_fail.get(brand, 0)
        }
    
    with open(REPORT_FILE, 'w', encoding='utf-8') as f:
        json.dump(report, f, ensure_ascii=False, indent=2)
    
    print()
    print("=== 检测完成 ===")
    print(f"总检测: {len(pdf_docs)}份")
    print(f"正常: {ok_count}份")
    print(f"异常: {fail_count}份")
    print(f"慢速(>5秒): {slow_count}份")
    print(f"报告已保存: {REPORT_FILE}")
    
    if fail_count > 0:
        print()
        print("=== 异常品牌TOP10 ===")
        sorted_brands = sorted(report['by_brand'].items(), key=lambda x: -x[1]['fail'])
        for brand, stats in sorted_brands[:10]:
            if stats['fail'] > 0:
                print(f"  {brand}: 正常{stats['ok']}, 异常{stats['fail']}")
        
        print()
        print("=== 异常原因TOP10 ===")
        reasons = Counter(r['reason'] for r in report['failures'])
        for reason, count in reasons.most_common(10):
            print(f"  {reason}: {count}份")

if __name__ == '__main__':
    main()
