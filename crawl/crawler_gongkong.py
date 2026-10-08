# -*- coding: utf-8 -*-
"""中国工控网 gongkong.com 免费PDF说明书采集器
从下载中心列表提取详情页，再从详情页提取PDF直链。
只采集免费PDF，按品牌分类，URL去重。
"""
import re,json,os,subprocess,urllib.request,urllib.parse,hashlib,time

UA="Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/120 Safari/537.36"
BASE="http://www.gongkong.com"
DST="pdfs/gongkong"
os.makedirs(DST,exist_ok=True)

# 已知品牌列表，用于从标题识别品牌
BRANDS = {
    "西门子": "siemens",
    "siemens": "siemens",
    "三菱": "mitsubishi",
    "mitsubishi": "mitsubishi",
    "欧姆龙": "omron",
    "omron": "omron",
    "台达": "delta",
    "delta": "delta",
    "施耐德": "schneider",
    "schneider": "schneider",
    "ABB": "abb",
    "abb": "abb",
    "富士": "fuji",
    "fuji": "fuji",
    "安川": "yaskawa",
    "yaskawa": "yaskawa",
    "松下": "panasonic",
    "panasonic": "panasonic",
    "信捷": "xinje",
    "xinje": "xinje",
    "汇川": "inovance",
    "inovance": "inovance",
    "威纶通": "weinview",
    "weinview": "weinview",
    "昆仑通态": "mcgs",
    "mcgs": "mcgs",
    "正泰": "chint",
    "chint": "chint",
    "德力西": "delixi",
    "delixi": "delixi",
    "亚德客": "airtac",
    "airtac": "airtac",
    "精创": "elitech",
    "elitech": "elitech",
    "雷赛": "leisai",
    "leisai": "leisai",
    "禾川": "hcfa",
    "hcfa": "hcfa",
    "英威腾": "invt",
    "invt": "invt",
}

def get_html(u):
    req=urllib.request.Request(u,headers={"User-Agent":UA})
    return urllib.request.urlopen(req,timeout=30).read().decode("utf-8","ignore")

def extract_pdf_from_detail(detail_url):
    """从详情页提取PDF直链和标题"""
    try:
        html = get_html(detail_url)
    except Exception as e:
        return None, str(e)
    
    # 提取pdf.js的file参数
    match = re.search(r'file=([^&\"]+)', html)
    if not match:
        return None, "无PDF链接"
    
    pdf_url = urllib.parse.unquote(match.group(1))
    
    # 提取标题
    title_match = re.search(r'<title>([^<]+)</title>', html)
    title = title_match.group(1).split('_')[0] if title_match else os.path.basename(pdf_url).split(".pdf")[0]
    
    return pdf_url, title

def identify_brand(title):
    """从标题识别品牌"""
    for brand_cn, brand_key in BRANDS.items():
        if brand_cn.lower() in title.lower():
            return brand_key
    return "other"

def pages_of(fp):
    r=subprocess.run(["pdfinfo",fp],capture_output=True,text=True)
    for l in r.stdout.splitlines():
        if l.startswith("Pages:"):return int(l.split()[1])
    return 0

def run():
    # 加载旧manifest
    old = {}
    if os.path.exists("gongkong_manifest.json"):
        try:
            for x in json.load(open("gongkong_manifest.json",encoding="utf-8")):
                if x.get("u"):
                    old[x["u"]] = x
        except Exception:
            pass
    
    recs = []
    seen_urls = set()
    new_count = 0
    
    # 按品牌关键词搜索
    search_keywords = [
        ("西门子", "siemens"),
        ("三菱", "mitsubishi"),
        ("欧姆龙", "omron"),
        ("台达", "delta"),
        ("施耐德", "schneider"),
        ("ABB", "abb"),
        ("富士", "fuji"),
        ("安川", "yaskawa"),
        ("松下", "panasonic"),
        ("信捷", "xinje"),
        ("汇川", "inovance"),
        ("威纶通", "weinview"),
        ("昆仑通态", "mcgs"),
        ("正泰", "chint"),
        ("德力西", "delixi"),
        ("亚德客", "airtac"),
        ("PLC", "plc"),
        ("变频器", "inverter"),
        ("伺服", "servo"),
        ("触摸屏", "hmi"),
    ]
    
    for keyword, brand in search_keywords:
        print(f"\n搜索: {keyword}")
        try:
            encoded_kw = urllib.parse.quote(keyword)
            list_url = f"{BASE}/technicaldata/Index?keyword={encoded_kw}&pageIndex=1&pageSize=20"
            html = get_html(list_url)
        except Exception as e:
            print(f"  搜索失败: {str(e)[:50]}")
            continue
        
        # 提取详情页链接
        detail_links = re.findall(r'href="(/download/\d+[^"]+)"', html)
        detail_links = list(set(detail_links))
        
        if not detail_links:
            print(f"  无结果")
            continue
        
        print(f"  发现{len(detail_links)}个详情页")
        
        # 逐个处理详情页
        for link in detail_links:
            detail_url = BASE + link
            pdf_url, result = extract_pdf_from_detail(detail_url)
            
            if not pdf_url:
                continue
            
            if pdf_url in seen_urls:
                continue
            seen_urls.add(pdf_url)
            
            # 检查是否已有
            old_item = old.get(pdf_url)
            if old_item and (old_item.get("pages") or 0) > 0:
                recs.append(old_item)
                continue
            
            # 识别品牌（优先用搜索关键词）
            detected_brand = identify_brand(result)
            if detected_brand == "other":
                detected_brand = brand
            
            # 下载PDF
            fn = "gk_%s.pdf" % hashlib.md5(pdf_url.encode()).hexdigest()[:8]
            fp = os.path.join(DST, fn)
            
            if not (os.path.exists(fp) and os.path.getsize(fp) > 10000):
                try:
                    req = urllib.request.Request(pdf_url, headers={"User-Agent": UA, "Referer": BASE + "/"})
                    raw = urllib.request.urlopen(req, timeout=60).read()
                    if raw[:4] != b"%PDF":
                        print(f"    非PDF: {result[:30]}")
                        continue
                    open(fp, "wb").write(raw)
                except Exception as e:
                    print(f"    下载失败: {result[:30]} {str(e)[:40]}")
                    continue
            
            pages = pages_of(fp)
            recs.append({
                "t": result,
                "u": pdf_url,
                "fn": fn,
                "pages": pages,
                "size": os.path.getsize(fp),
                "brand": detected_brand
            })
            new_count += 1
            print(f"    新增: [{detected_brand}] {result[:40]} ({pages}页)")
        
        time.sleep(1)  # 礼貌延迟
    
    # 也抓一下最新列表
    print("\n抓取最新列表...")
    for page in range(1, 10):
        try:
            list_url = f"{BASE}/technicaldata/Index?pageIndex={page}&pageSize=8&status=0&cid=0&bid=0&iid=0&pid=0&tid=0"
            html = get_html(list_url)
        except Exception as e:
            break
        
        detail_links = re.findall(r'href="(/download/\d+/[^"]+)"', html)
        detail_links = list(set(detail_links))
        
        if not detail_links:
            break
        
        for link in detail_links:
            detail_url = BASE + link
            pdf_url, result = extract_pdf_from_detail(detail_url)
            
            if not pdf_url or pdf_url in seen_urls:
                continue
            seen_urls.add(pdf_url)
            
            old_item = old.get(pdf_url)
            if old_item and (old_item.get("pages") or 0) > 0:
                recs.append(old_item)
                continue
            
            brand = identify_brand(result)
            fn = "gk_%s.pdf" % hashlib.md5(pdf_url.encode()).hexdigest()[:8]
            fp = os.path.join(DST, fn)
            
            if not (os.path.exists(fp) and os.path.getsize(fp) > 10000):
                try:
                    req = urllib.request.Request(pdf_url, headers={"User-Agent": UA, "Referer": BASE + "/"})
                    raw = urllib.request.urlopen(req, timeout=60).read()
                    if raw[:4] != b"%PDF":
                        continue
                    open(fp, "wb").write(raw)
                except Exception as e:
                    continue
            
            pages = pages_of(fp)
            recs.append({
                "t": result,
                "u": pdf_url,
                "fn": fn,
                "pages": pages,
                "size": os.path.getsize(fp),
                "brand": brand
            })
            new_count += 1
        
        print(f"  第{page}页完成，累计{len(recs)}份")
        time.sleep(1)
    
    # 保存manifest
    json.dump(recs, open("gongkong_manifest.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print(f"\n工控网说明书采集完成: {len(recs)}份 (本次新增下载{new_count}，复用{len(recs)-new_count})")

if __name__ == "__main__":
    run()
