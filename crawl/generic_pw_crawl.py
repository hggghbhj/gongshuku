# -*- coding: utf-8 -*-
"""通用Playwright采集器：处理JS动态渲染的品牌下载页。
用法: python3 generic_pw_crawl.py
配置在 PW_BRANDS 列表中，每个品牌指定下载页URL和可选的分类点击。
不下载PDF到本地，只记录外链URL（reader.html走代理预览）。
"""
import json, os, time, hashlib, re, sys, subprocess
from urllib.parse import urljoin, urlparse

try:
    from playwright.sync_api import sync_playwright
    from pw_util import chromium_path
except ImportError:
    print("playwright未安装，请先 pip install playwright && playwright install chromium")
    sys.exit(1)

# Stealth反检测（可选，用于绕过WAF）
try:
    from playwright_stealth import Stealth
    HAS_STEALTH = True
except ImportError:
    HAS_STEALTH = False

UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"

# ===== 困难品牌配置：JS动态渲染、需无头浏览器 =====
PW_BRANDS = [
    {
        "key": "delta",
        "b": "台达电子",
        "url": "https://downloadcenter.delta-china.com.cn/zh-CN/DownloadCenter",
        "wait": 8,
        "pdf_selector": "a[href*='.pdf'], a[href*='.PDF']",
        "next_text": "下一页",
    },
    {
        "key": "weinview",
        "b": "威纶通",
        "url": "https://www.weintek.com/Download/Document/",
        "wait": 6,
        "pdf_selector": "a[href*='.pdf'], a[href*='.PDF']",
        "next_text": None,
    },
    {
        "key": "omron",
        "b": "欧姆龙",
        "url": "https://www.fa.omron.com.cn/document/q/V520",
        "wait": 8,
        "pdf_selector": "a[href*='.pdf'], a[href*='.PDF']",
        "next_text": "下一页",
    },
    {
        "key": "sick",
        "b": "西克SICK",
        "url": "https://www.sick.com/cn/zh/downloads/",
        "wait": 8,
        "pdf_selector": "a[href*='.pdf'], a[href*='.PDF']",
        "next_text": "下一页",
    },
    {
        "key": "smc",
        "b": "SMC气动",
        "url": "https://www.smc.com.cn/manuals/zh-cn/searchIndex/R",
        "wait": 6,
        "pdf_selector": "a[href*='.pdf'], a[href*='.PDF']",
        "next_text": "下一页",
    },
    {
        "key": "festo",
        "b": "费斯托FESTO",
        "url": "https://www.festo.com.cn/cn/zh/e/support/technical-documentation-id_1907109/",
        "wait": 6,
        "pdf_selector": "a[href*='.pdf'], a[href*='.PDF']",
        "next_text": "下一页",
    },
    {
        "key": "keyence",
        "b": "基恩士",
        "url": "https://www.keyence.com.cn/downloads/?mode=ma&type_id=tcm%3A115-347535&ad_local=side_manual",
        "wait": 8,
        "pdf_selector": "a[href*='.pdf'], a[href*='.PDF']",
        "next_text": None,
    },
    {
        "key": "samkoon",
        "b": "显控科技",
        "url": "https://www.samkoon.com/download/",
        "wait": 6,
        "pdf_selector": "a[href*='.pdf'], a[href*='.PDF']",
        "next_text": "下一页",
    },
    {
        "key": "flexem",
        "b": "繁易电子",
        "url": "https://www.flexem.com/download/",
        "wait": 6,
        "pdf_selector": "a[href*='.pdf'], a[href*='.PDF']",
        "next_text": None,
    },
    {
        "key": "estun",
        "b": "埃斯顿",
        "url": "https://www.estun.com/cn/support/download/",
        "wait": 6,
        "pdf_selector": "a[href*='.pdf'], a[href*='.PDF']",
        "next_text": None,
    },
    {
        "key": "googol",
        "b": "固高自动化",
        "url": "https://www.googoltech.com.cn/service/download/",
        "wait": 6,
        "pdf_selector": "a[href*='.pdf'], a[href*='.PDF']",
        "next_text": None,
    },
    {
        "key": "knd",
        "b": "凯恩帝数控",
        "url": "https://www.knd.com.cn/download/",
        "wait": 6,
        "pdf_selector": "a[href*='.pdf'], a[href*='.PDF']",
        "next_text": None,
    },
]


def check_pdf_head(url, timeout=10):
    """HEAD校验PDF可访问，返回(pages, size)或None"""
    try:
        import urllib.request
        req = urllib.request.Request(url, method="HEAD", headers={"User-Agent": UA})
        r = urllib.request.urlopen(req, timeout=timeout)
        ct = r.headers.get("Content-Type", "")
        cl = r.headers.get("Content-Length", "0")
        if "pdf" in ct.lower() or url.lower().endswith(".pdf"):
            return int(cl) if cl.isdigit() else 0
    except Exception:
        pass
    return None


def extract_pdfs(pg, base_url):
    """从渲染后的完整HTML中正则提取所有PDF URL（包括a标签、data属性、JS中的）"""
    html = pg.content()
    # 匹配所有 .pdf 链接（http开头或相对路径）
    import re as _re
    # 匹配引号中的PDF URL
    raw = _re.findall(r'["\']((?:https?://|/)[^"\'\s<>]+\.pdf(?:\?[^"\'\s<>]*)?)["\']', html, _re.I)
    items = []
    seen_u = set()
    for u in raw:
        if not u.startswith("http"):
            u = urljoin(base_url, u)
        if u in seen_u:
            continue
        seen_u.add(u)
        # 从URL推断标题
        fn = os.path.basename(u.split("?")[0])
        t = re.sub(r"\.pdf$", "", fn, flags=re.I)
        t = re.sub(r"[-_]+", " ", t).strip()
        items.append({"t": t, "u": u})
    return items


def crawl_brand(brand, p):
    """采集单个品牌：渲染页面+监听网络请求+正则提取HTML中的PDF"""
    key = brand["key"]
    bname = brand["b"]
    url = brand["url"]
    wait = brand.get("wait", 8)

    manifest_file = f"{key}_manifest.json"
    old = {}
    if os.path.exists(manifest_file):
        try:
            for x in json.load(open(manifest_file, encoding="utf-8")):
                k = x.get("u") or x.get("url") or ""
                if k:
                    old[k] = x
        except Exception:
            pass

    recs = list(old.values())
    seen = set(old.keys())
    captured = set()  # 网络监听到的PDF URL

    try:
        b = p.chromium.launch(headless=True, executable_path=chromium_path(),
                              args=["--no-sandbox", "--ignore-certificate-errors", "--disable-dev-shm-usage"])
        ctx = b.new_context(user_agent=UA, ignore_https_errors=True,
                           viewport={"width": 1280, "height": 900})
        pg = ctx.new_page()

        # 监听所有网络请求中的PDF URL
        def on_response(resp):
            u = resp.url
            if ".pdf" in u.lower() and not u.lower().endswith(".pdf.js"):
                captured.add(u)
        pg.on("response", on_response)

        pg.goto(url, wait_until="domcontentloaded", timeout=30000)
        time.sleep(wait)

        # 滚动触发懒加载
        for _ in range(3):
            pg.evaluate("window.scrollBy(0, 600)")
            time.sleep(1)

        # 提取HTML中的PDF链接
        items = extract_pdfs(pg, url)
        for it in items:
            captured.add(it["u"])

        b.close()

        # 校验并保存所有捕获到的PDF
        new_count = 0
        for u in captured:
            if u in seen:
                continue
            seen.add(u)
            sz = check_pdf_head(u)
            if sz is None:
                continue
            fn = os.path.basename(u.split("?")[0])
            t = re.sub(r"\.pdf$", "", fn, flags=re.I)
            t = re.sub(r"[-_]+", " ", t).strip()
            recs.append({"t": t, "u": u, "size": sz, "pages": 0,
                         "brand": bname, "src": "pw_crawl"})
            new_count += 1

        with open(manifest_file, "w", encoding="utf-8") as f:
            json.dump(recs, f, ensure_ascii=False, indent=1)
        return new_count, len(recs)

    except Exception as e:
        # 即使异常，也保存已捕获的
        with open(manifest_file, "w", encoding="utf-8") as f:
            json.dump(recs, f, ensure_ascii=False, indent=1)
        print(f"  [{bname}] 异常: {str(e)[:80]}")
        return 0, len(recs)


def main():
    total_new = 0
    print(f"通用Playwright采集器启动，共{len(PW_BRANDS)}个困难品牌 (stealth={HAS_STEALTH})")
    if HAS_STEALTH:
        pm = Stealth().use_sync(sync_playwright())
    else:
        pm = sync_playwright()
    with pm as p:
        for brand in PW_BRANDS:
            print(f"[{brand['b']}] 采集中...")
            try:
                new, total = crawl_brand(brand, p)
                total_new += new
                print(f"  完成: 新增{new}条, 累计{total}条")
            except Exception as e:
                print(f"  失败: {str(e)[:80]}")

    print(f"\n=== 通用Playwright采集完成: 新增{total_new}条 ===")


if __name__ == "__main__":
    main()
