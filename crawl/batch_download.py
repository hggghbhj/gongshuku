# -*- coding: utf-8 -*-
"""批量下载manifest里记录了URL但本地没有的PDF。并发下载，验证%PDF头。"""
import json, os, glob, time, urllib.request, ssl
from concurrent.futures import ThreadPoolExecutor, as_completed
from urllib.parse import urlparse

ROOT = os.path.dirname(os.path.abspath(__file__))
PDFS = os.path.join(ROOT, "pdfs")
ctx = ssl.create_default_context()
ctx.check_hostname = False
ctx.verify_mode = ssl.CERT_NONE

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                  "(KHTML, like Gecko) Chrome/120.0 Safari/537.36",
}

# 按品牌加Referer
REFERERS = {
    "xinje": "https://www.xinje.com/",
    "leisai": "https://www.leisai.com/",
    "invt": "https://www.invt.com.cn/",
    "sinee": "https://www.sinee.cn/",
    "oura": "https://www.ouradrive.com/",
    "hcfa": "https://www.hcfa.cn/",
    "elitech": "https://www.e-elitech.com/",
    "coolmay": "https://www.coolmay.com/",
}

def encode_url(url):
    """对中文URL路径进行百分号编码。"""
    parsed = urlparse(url)
    if parsed.path:
        from urllib.parse import quote, urlunparse
        path = quote(parsed.path, safe="/%")
        return urlunparse((parsed.scheme, parsed.netloc, path,
                          parsed.params, parsed.query, parsed.fragment))
    return url

# manifest文件 -> 品牌目录名
DIR_MAP = {
    "elitech": "elitech", "leisai": "leisai", "xinje": "xinje",
    "sinee": "sinee", "oura": "oura", "hcfa": "hcfa", "invt": "invt",
    "coolmay": "coolmay", "easydrive": "easydrive", "amsamotion": "amsamotion",
    "mcgs": "mcgs", "senlan": "senlan", "veichi": "veichi",
    "abb_motor": "abb", "gongkong": "gongkong", "mitsubishi": "mitsubishi",
    "siemens": "siemens", "growatt": "growatt", "fotek": "fotek",
    "tengen": "tengen", "meanwell": "meanwell", "santak": "santak",
    "simphoenix": "simphoenix", "gtake": "gtake", "hiconics": "hiconics",
    "ema": "ema", "banner": "banner", "sanyou": "sanyou", "yudian": "yudian",
    "cincon": "cincon", "hollysys": "hollysys", "hongfa": "hongfa",
    "haiwell": "haiwell", "hongrun": "hongrun", "wideplus": "wideplus",
    "anthone": "anthone", "lazzen": "lazzen", "yankong": "yankong",
    "huceen": "huceen", "mege": "mege", "lanbao": "lanbao",
    "alpha": "alpha", "xichi": "xichi", "anbangxin": "anbangxin",
    "huazhong": "huazhong", "gskcnc": "gskcnc", "microsensor": "microsensor",
    "delixi": "delixi", "fuling": "fuling", "shenler": "shenler",
    "huibang": "huibang", "kaimin": "kaimin", "gclsi": "gclsi",
    "yatai": "yatai", "chint": "chint", "airtac": "airtac",
    "jelpc": "jelpc", "siglent": "siglent", "hantek": "hantek",
    "moons": "moons", "schneider": "schneider", "gwinstek": "gwinstek",
    "cocis": "cocis", "powtran": "powtran", "jintian": "jintian",
    "inovance": "inovance", "enc": "enc", "cotion": "cotion",
    "gongbei": "gongbei",
}

def get_field(r, *names):
    for n in names:
        v = r.get(n)
        if v: return v
    return ""

def collect_tasks():
    """收集所有待下载任务。"""
    tasks = []
    for mp in sorted(glob.glob(os.path.join(ROOT, "*_manifest.json"))):
        key = os.path.basename(mp).replace("_manifest.json", "")
        brand_dir = DIR_MAP.get(key, key)
        try:
            data = json.load(open(mp, encoding="utf-8"))
        except: continue
        for r in data:
            url = get_field(r, "u", "url", "durl")
            fn = get_field(r, "fn", "pdf")
            if not url or not fn:
                continue
            # fn可能是完整路径 pdfs/xxx/yyy.pdf，也可能是文件名
            if "/" in fn:
                local = os.path.join(ROOT, fn)
            else:
                local = os.path.join(PDFS, brand_dir, fn)
            # 已存在且>1KB就跳过
            if os.path.exists(local) and os.path.getsize(local) > 1000:
                continue
            tasks.append((url, local, key))
    return tasks

def download_one(task):
    url, local, brand = task
    os.makedirs(os.path.dirname(local), exist_ok=True)
    enc_url = encode_url(url)
    headers = dict(HEADERS)
    if brand in REFERERS:
        headers["Referer"] = REFERERS[brand]
    for attempt in range(2):
        try:
            req = urllib.request.Request(enc_url, headers=headers)
            with urllib.request.urlopen(req, timeout=60, context=ctx) as r:
                data = r.read()
            if len(data) < 1000 or b"%PDF" not in data[:2048]:
                return (brand, "notpdf", url)
            with open(local, "wb") as f:
                f.write(data)
            return (brand, "ok", local)
        except Exception as e:
            if attempt == 0:
                time.sleep(1)
            else:
                return (brand, "fail:" + str(e)[:60], url)
    return (brand, "fail", url)

def main():
    tasks = collect_tasks()
    print(f"待下载: {len(tasks)} 个")
    from collections import Counter
    brand_counts = Counter(t[2] for t in tasks)
    print("各品牌:", dict(brand_counts.most_common(15)))

    ok = 0; fail = 0
    fail_by_brand = Counter()
    with ThreadPoolExecutor(max_workers=8) as ex:
        futures = {ex.submit(download_one, t): t for t in tasks}
        for i, fut in enumerate(as_completed(futures)):
            brand, status, info = fut.result()
            if status == "ok":
                ok += 1
            else:
                fail += 1
                fail_by_brand[brand] += 1
            if (i+1) % 50 == 0:
                print(f"  进度 {i+1}/{len(tasks)} | 成功{ok} 失败{fail}")
    print(f"\n=== 完成: 成功{ok}, 失败{fail} ===")
    print("失败品牌:", dict(fail_by_brand.most_common(15)))

if __name__ == "__main__":
    main()
