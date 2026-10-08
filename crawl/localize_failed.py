# -*- coding: utf-8 -*-
"""把健康检查里异常的官网直链批量本地化下载到 dist/pdfs/，成功的改成本地路径。"""
import json, os, re, time, hashlib, urllib.request, ssl, sys

ROOT = os.path.dirname(os.path.abspath(__file__))
DIST = os.path.join(ROOT, "..", "dist")
PDFS = os.path.join(DIST, "pdfs")
REPORT = os.path.join(DIST, "data", "health_report.json")
DOCS3 = os.path.join(DIST, "data", "docs-3.js")

UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0 Safari/537.36"

# 明确死路的品牌不浪费时间
SKIP_BRANDS = {"金田科技", "普传"}  # WAF/限流，云端IP必拦

def safe_name(s):
    s = re.sub(r'[^\w一-鿒.-]', '_', s)
    return s[:80]

def download(url, timeout=20):
    ctx = ssl.create_default_context()
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE
    req = urllib.request.Request(url, headers={
        "User-Agent": UA,
        "Accept": "application/pdf,*/*",
        "Referer": url.rsplit("/", 3)[0] + "/",
    })
    with urllib.request.urlopen(req, timeout=timeout, context=ctx) as r:
        return r.read()

def main():
    rep = json.load(open(REPORT, encoding="utf-8"))
    fails = rep.get("failures", [])
    print(f"待处理异常链接: {len(fails)}")

    # 读 docs-3.js 现有数据
    s = open(DOCS3, encoding="utf-8").read()
    m = re.search(r'DOCS=DOCS\.concat\((\[.*\])\);', s, re.DOTALL)
    docs = json.loads(m.group(1)) if m else []
    print(f"docs-3.js 现有条目: {len(docs)}")

    ok_localized = 0
    still_fail = 0
    skipped = 0

    for i, f in enumerate(fails):
        url = f["url"]
        brand = f.get("brand", "unknown")
        title = f.get("title", "")
        if brand in SKIP_BRANDS:
            skipped += 1
            continue

        # 已经是本地路径的跳过
        if url.startswith("/pdfs/"):
            continue

        # 试下载（最多2次）
        data = None
        for attempt in range(2):
            try:
                data = download(url, timeout=25)
                break
            except Exception as e:
                if attempt == 1:
                    print(f"  [{i+1}/{len(fails)}] 失败 {brand} | {title[:30]} | {type(e).__name__}")
                time.sleep(1)

        if not data or not data.startswith(b"%PDF"):
            still_fail += 1
            continue

        # 存到本地
        bdir = os.path.join(PDFS, safe_name(brand))
        os.makedirs(bdir, exist_ok=True)
        h = hashlib.md5(url.encode()).hexdigest()[:10]
        fname = safe_name(title) + "_" + h + ".pdf"
        fpath = os.path.join(bdir, fname)
        if not os.path.exists(fpath):
            open(fpath, "wb").write(data)

        local_url = f"/pdfs/{safe_name(brand)}/{fname}"
        # 改 docs-3.js 里对应条目的 pdf 字段
        changed = False
        for d in docs:
            if d.get("pdf") == url:
                d["pdf"] = local_url
                changed = True
        if changed:
            ok_localized += 1
            print(f"  [{i+1}/{len(fails)}] ✅ 本地化 {brand} | {title[:30]} | {len(data)//1024}KB")

    # 回写 docs-3.js
    out = "/* 工书库数据分片3：品牌官网免费直链（自动采集，每3小时增量更新） */\n"
    out += "DOCS=DOCS.concat("
    out += json.dumps(docs, ensure_ascii=False, separators=(",", ":"))
    out += ");\n"
    open(DOCS3, "w", encoding="utf-8").write(out)

    print(f"\n=== 完成 ===")
    print(f"成功本地化: {ok_localized}")
    print(f"仍失败: {still_fail}")
    print(f"跳过(已知死路品牌): {skipped}")

if __name__ == "__main__":
    main()
