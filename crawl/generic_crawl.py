# -*- coding: utf-8 -*-
"""工书库·通用说明书采集器
只需在 BRAND_SITES 中配置「品牌名 + 下载页URL（可多个）」，脚本自动：
  1. 抓取下载页，提取所有 PDF 链接及链接文本标题
  2. 自动探测分页（?page=N / /page/N / 下一页），逐页抓取
  3. 校验 PDF 可访问（HEAD 请求，记录状态码）
  4. 按 URL + 标题双重去重，不重复采集
  5. 增量更新 <key>_manifest.json，已存在的 URL 跳过
用法：
  python3 generic_crawl.py              # 跑全部配置
  python3 generic_crawl.py 汇川 信捷     # 只跑指定品牌
  python3 generic_crawl.py --max-pages 5   # 限制每个站点最多翻页数
"""
import os, re, sys, json, time, urllib.parse
from datetime import datetime
import gsk_common as g

HERE = os.path.dirname(os.path.abspath(__file__))
os.chdir(HERE)

# ============================================================
# 品牌站点配置：key -> {品牌名, 下载页URL列表, 可选参数}
# 新增品牌只需在这里加一条，无需再写专门爬虫。
# ============================================================
BRAND_SITES = {
    "alpha": {
        "b": "阿尔法电气",
        "start": ["http://www.szalpha.cn/zw/download/index.aspx"],
        "referer": "http://www.szalpha.cn/zw/download/index.aspx",
    },
    "xichi": {
        "b": "西驰电气",
        "start": ["http://www.xichi.com/service/smsxz/"],
    },
    "anbangxin": {
        "b": "安邦信",
        "start": ["http://www.anbangxin.com/page_7/"],
    },
    "huibang": {
        "b": "汇邦科技",
        "start": ["https://www.hbkj.com.cn/download-39-0-1.html"],
    },
    "huceen": {
        "b": "汇辰自动化",
        "start": ["https://www.huceen.cn/download/list-274-cn.html"],
    },
    "mege": {
        "b": "米格电机",
        "start": ["https://www.mege.cn/index.php?ac=Article&at=List&tid=42"],
    },
    "huazhong": {
        "b": "华中数控",
        "start": ["https://huazhongcnc.com/portal/list/index/cid/73.html"],
    },
    "gskcnc": {
        "b": "广州数控",
        "start": ["https://www.gsk.com.cn/zlxz/index_15.aspx?lcid=18"],
    },
    "microsensor": {
        "b": "麦克传感器",
        "start": ["https://www.microsensor.cn/download"],
    },
    "fuling": {
        "b": "富凌电气",
        "start": ["https://www.chinafuling.com/download-3.html"],
    },
    "gclsi": {
        "b": "协鑫集成",
        "start": ["https://www.gclsi.com/download.html"],
    },
    "yatai": {
        "b": "亚泰仪表",
        "start": ["http://www.yatai.sh.cn/"],
    },
    "lanbao": {
        "b": "兰宝传感",
        "start": ["http://www.shlanbao.cn/download.html"],
    },
    "enc": {
        "b": "易能电气",
        "start": ["http://www.enc.net.cn/service/filedownlaod/productType/index.html"],
    },
    "easydrive": {
        "b": "易驱电气",
        "start": ["https://www.szeasydrive.com/download/"],
    },
    "senlan": {
        "b": "森兰",
        "start": ["http://www.chinavvvf.com/list-57-1.html"],
    },
    "simphoenix": {
        "b": "四方电气",
        "start": ["https://www.simphoenix.com/download/manual/"],
    },
    "gtake": {
        "b": "吉泰科",
        "start": ["https://www.gtake.com/downloads/"],
    },
    "hiconics": {
        "b": "合康新能",
        "start": ["https://www.hiconics.com/category/download1.html"],
    },
    "ema": {
        "b": "伊玛电子",
        "start": ["https://www.ema-electronic.com/downloadsms.html"],
    },
    "sanyou": {
        "b": "三友",
        "start": ["https://www.sanyourelay.com/pc/download"],
    },
    "cincon": {
        "b": "Cincon",
        "start": ["https://www.cincon.com/user-manual_en.php"],
    },
    "hongfa": {
        "b": "宏发",
        "start": ["https://www.hongfa.com/en/service/down"],
    },
    "lazzen": {
        "b": "良信电器",
        "start": ["https://www.lazzen.com/support/downloads/product-manual"],
    },
    "yankong": {
        "b": "研控自动化",
        "start": ["https://www.yankong.com/download.html"],
    },
    "coolmay": {
        "b": "顾美科技",
        "start": ["http://www.coolmay.com"],
    },
    "anthone": {
        "b": "安东仪表",
        "start": ["https://anthone.com.cn/index.php/Server/data_download.html"],
    },
    "haiwell": {
        "b": "海为",
        "start": ["https://haiwell.com/download/download.php?class1=32"],
    },
    "growatt": {
        "b": "古瑞瓦特",
        "start": ["https://www.growatt.com/support/download"],
    },
    "delixi": {
        "b": "德力西变频器",
        "start": ["https://www.delixidrive.com/list-26-1.html"],
    },
    "shenler": {
        "b": "申乐电气",
        "start": ["https://www.shenler.cn/"],
    },
    "jelpc": {
        "b": "佳尔灵气动",
        "start": ["https://www.jelpc.com/download/"],
    },
    "veichi": {
        "b": "伟创电气",
        "start": ["https://www.veichi.cn/service/datadownload"],
    },
    "sinee": {
        "b": "正弦电气",
        "start": ["https://www.sinee.cn/47/"],
    },
    "oura": {
        "b": "欧瑞传动",
        "start": ["https://www.euradrives.com/service/down.html"],
    },
    "hcfa": {
        "b": "禾川科技",
        "start": ["https://www.hcfa.cn/service/index.html"],
    },
    "invt": {
        "b": "英威腾",
        "start": ["https://www.invt.com.cn/dowload-15"],
    },
    "mcgs": {
        "b": "昆仑通态",
        "start": ["https://www.mcgspro.com/downloads.html"],
    },
    "amsamotion": {
        "b": "艾莫迅",
        "start": ["https://www.amsamotion.com/download.html"],
    },
    "cotion": {
        "b": "合信技术",
        "start": ["https://www.co-trust.com/Download/index.html"],
    },
    "gongbei": {
        "b": "工贝电子",
        "start": ["https://jngbdz.com/"],
    },
    "meanwell": {
        "b": "明纬电源",
        "start": ["https://www.meanwell.com.cn/productManual.aspx"],
    },
    "santak": {
        "b": "山特UPS",
        "start": ["https://www.santak.com.cn/page/santak-downloads.html"],
    },
    "tengen": {
        "b": "天正电气",
        "start": ["https://www.tengen.com/Download.html"],
    },
    "yudian": {
        "b": "宇电",
        "start": ["https://www.yudian.com/down/10039.html"],
    },
    "hongrun": {
        "b": "虹润仪表",
        "start": ["https://www.hrgs.com.cn/download/?tag=8"],
    },
    "wideplus": {
        "b": "上润仪表",
        "start": ["https://www.wideplus.com/companyfile/2/"],
    },
    "hollysys": {
        "b": "和利时",
        "start": ["https://www.hollysys.com/download/products"],
    },
    "airtac": {
        "b": "亚德客",
        "start": ["https://www.airtac.com/download"],
    },
    "fotek": {
        "b": "阳明电机",
        "start": ["https://www.fotek.com.tw/zh-cn/download"],
    },
    "leisai": {
        "b": "雷赛智能",
        "start": ["https://www.leisai.com/downloads.html"],
    },
    "moons": {
        "b": "鸣志",
        "start": ["https://www.moons.com.cn/support-training/downloads"],
    },
    "hantek": {
        "b": "汉泰克",
        "start": ["https://www.hantek.com.cn/download"],
    },
    "siglent": {
        "b": "鼎阳科技",
        "start": ["https://www.siglent.com/support/resource/"],
    },
    "gwinstek": {
        "b": "固纬电子",
        "start": ["https://www.gwinstek.com.cn/down/208"],
    },
    # ===== 批量补充：市面上叫得上号的工业品牌 =====
    "zctech": {
        "b": "众辰电子",
        "start": ["https://www.zctech.com/service/download/"],
    },
    "lanht": {
        "b": "蓝海华腾",
        "start": ["https://www.lanht.com/download/"],
    },
    "delta": {
        "b": "台达电子",
        "start": ["https://downloadcenter.delta-china.com.cn/zh-CN/DownloadCenter"],
    },
    "vb": {
        "b": "丰炜科技",
        "start": ["https://www.vb.com.tw/download"],
    },
    "fatek": {
        "b": "永宏电机",
        "start": ["https://www.fatek.com/download.php"],
    },
    "shihlin": {
        "b": "士林电机",
        "start": ["https://www.shihlin-electric.com.cn/download"],
    },
    "advantech": {
        "b": "研华科技",
        "start": ["https://www.advantech.com.cn/support/download"],
    },
    "omron": {
        "b": "欧姆龙",
        "start": ["https://www.omron.com.cn/cn/support/download/"],
    },
    "panasonic": {
        "b": "松下电器",
        "start": ["https://industrial.panasonic.cn/cn/pss/fa/"],
    },
    "fujielectric": {
        "b": "富士电机",
        "start": ["https://www.fujielectric.com.cn/support/download/"],
    },
    "yaskawa": {
        "b": "安川电机",
        "start": ["https://www.yaskawa.com.cn/support/download/"],
    },
    "fanuc": {
        "b": "发那科",
        "start": ["https://wwwfanuc.com.cn/service/download/"],
    },
    "rockwell": {
        "b": "罗克韦尔AB",
        "start": ["https://www.rockwellautomation.com/zh-cn/support/downloads.html"],
    },
    "honeywell": {
        "b": "霍尼韦尔",
        "start": ["https://www.honeywell.com.cn/zh-cn/support/"],
    },
    "yokogawa": {
        "b": "横河电机",
        "start": ["https://www.yokogawa.com/cn/zh/support/downloads/"],
    },
    "keyence": {
        "b": "基恩士",
        "start": ["https://www.keyence.com.cn/download/"],
    },
    "pepperl": {
        "b": "倍加福",
        "start": ["https://www.pepperl-fuchs.com/cn/zh/software/"],
    },
    "balluff": {
        "b": "巴鲁夫",
        "start": ["https://www.balluff.com.cn/zh-cn/support/downloads/"],
    },
    "sick": {
        "b": "西克SICK",
        "start": ["https://www.sick.com/cn/zh/downloads/"],
    },
    "endress": {
        "b": "恩德斯豪斯E+H",
        "start": ["https://www.endress.com.cn/support/downloads"],
    },
    "weinview": {
        "b": "威纶通",
        "start": ["https://www.weintek.com/Download/Document/"],
    },
    "kinco": {
        "b": "步科股份",
        "start": ["https://www.kinco.cn/service/download"],
    },
    "samkoon": {
        "b": "显控科技",
        "start": ["https://www.samkoon.com/download/"],
    },
    "flexem": {
        "b": "繁易电子",
        "start": ["https://www.flexem.com/download/"],
    },
    "dwg": {
        "b": "迪文科技",
        "start": ["https://www.dwin.com.cn/download/"],
    },
    "chint": {
        "b": "正泰电器",
        "start": ["https://www.chint.com/download/"],
    },
    "cs-east": {
        "b": "常熟开关",
        "start": ["https://www.cs-electric.com/download/"],
    },
    "mingway": {
        "b": "金升阳",
        "start": ["https://www.mornsun.cn/download/"],
    },
    "hengfu": {
        "b": "衡孚电源",
        "start": ["https://www.hengfu.com.cn/download/"],
    },
    "smc": {
        "b": "SMC气动",
        "start": ["https://www.smc.com.cn/download/"],
    },
    "festo": {
        "b": "费斯托FESTO",
        "start": ["https://www.festo.com.cn/zh/c/service/downloads/"],
    },
    "chelic": {
        "b": "气立可",
        "start": ["https://www.chelic.com.cn/download/"],
    },
    "knd": {
        "b": "凯恩帝数控",
        "start": ["https://www.knd.com.cn/download/"],
    },
    "jingdiao": {
        "b": "北京精雕",
        "start": ["https://www.jingdiao.com/download/"],
    },
    "cqinst": {
        "b": "重庆川仪",
        "start": ["https://www.cqinst.com/download/"],
    },
    "invt_servo": {
        "b": "汇川技术",
        "start": ["https://www.inovance.com/cn/service/download/"],
    },
    "lenze": {
        "b": "伦茨传动",
        "start": ["https://www.lenze.com.cn/support/download/"],
    },
    "boschrexroth": {
        "b": "博世力士乐",
        "start": ["https://www.boschrexroth.com.cn/zh/service/download/"],
    },
    "parker": {
        "b": "派克汉尼汾",
        "start": ["https://www.parker.com.cn/zh/service/download/"],
    },
    "norgren": {
        "b": "诺冠气动",
        "start": ["https://www.norgren.com/cn/zh/support/downloads/"],
    },
    "camozzi": {
        "b": "康茂盛气动",
        "start": ["https://www.camozzi.com.cn/download/"],
    },
    "werner": {
        "b": "魏德米勒",
        "start": ["https://www.weidmueller.com.cn/support/download/"],
    },
    "phoenix": {
        "b": "菲尼克斯电气",
        "start": ["https://www.phoenixcontact.com.cn/download/"],
    },
    "wago": {
        "b": "万可电子",
        "start": ["https://www.wago.com/cn/zh/support/downloads/"],
    },
    "rs_pro": {
        "b": "欧姆龙自动化",
        "start": ["https://www.omron-ap.com.cn/support/download/"],
    },
    "delta_industrial": {
        "b": "台达自动化",
        "start": ["https://www.deltaww.com.cn/cn/SAAS/download"],
    },
    "hinox": {
        "b": "海纳科技",
        "start": ["https://www.hinox.com.cn/download/"],
    },
    "sunye": {
        "b": "日业电气",
        "start": ["https://www.sunye.com.cn/download/"],
    },
    "kongberg": {
        "b": "康士伯",
        "start": ["https://www.km.kongsberg.com/cn/support/download/"],
    },
    "berger": {
        "b": "百格拉",
        "start": ["https://www.bergerlahr.com.cn/download/"],
    },
    "esitron": {
        "b": "埃斯顿自动化",
        "start": ["https://www.estun.com/download/"],
    },
    "googol": {
        "b": "固高自动化",
        "start": ["https://www.googoltech.com.cn/download/"],
    },
    "spii": {
        "b": "众为兴",
        "start": ["https://www.spii.com.cn/download/"],
    },
}

# 标题中应过滤的无关词（下载页常见噪声）
NOISE_TITLES = {"下载", "资料下载", "说明书下载", "download", "点击下载", "下载地址",
                "查看", "更多", "pdf", "PDF", "文档", "手册", "资料", "文件下载"}


def strip_tags(s):
    s = re.sub(r"<[^>]+>", "", s or "")
    s = re.sub(r"&nbsp;", " ", s)
    s = re.sub(r"&amp;", "&", s)
    return re.sub(r"\s+", " ", s).strip()


def extract_pdf_with_titles(html, page_url):
    """从 HTML 提取 (pdf_url, title) 列表，标题优先取 <a> 标签内文本。"""
    found = {}
    # 1) 完整 <a href="xxx.pdf">标题</a>（含跨行、单双引号）
    for m in re.finditer(r'<a\b[^>]*?href=["\']([^"\']+?\.pdf(?:\?[^"\']*)?)["\'][^>]*>(.*?)</a>',
                         html, re.I | re.S):
        u, t = m.group(1), strip_tags(m.group(2))
        u = urllib.parse.urljoin(page_url, u)
        if u not in found or (len(t) > len(found[u]) and t):
            found[u] = t
    # 2) 仅在 JS/字符串中出现的 PDF（无 <a> 包裹）
    for m in re.finditer(r'["\']([^"\']+?\.pdf(?:\?[^"\']*)?)["\']', html, re.I):
        u = urllib.parse.urljoin(page_url, m.group(1))
        if u not in found:
            found[u] = ""
    # 3) 无引号 href
    for m in re.finditer(r'href=([^\s>]+\.pdf(?:\?[^\s>]*)?)', html, re.I):
        u = urllib.parse.urljoin(page_url, m.group(1).strip("'\""))
        if u not in found:
            found[u] = ""
    out = []
    for u, t in found.items():
        if t in NOISE_TITLES or len(t) < 2:
            # 用文件名兜底
            path = urllib.parse.unquote(urllib.parse.urlparse(u).path)
            t = os.path.basename(path).replace(".pdf", "").replace(".PDF", "")
            t = re.sub(r"[_\-]+", " ", t).strip()
        out.append((u, t[:80]))
    return out


def find_next_pages(html, page_url, max_pages):
    """探测页面中真实存在的分页链接（下一页/页码），不盲目构造404 URL。"""
    cands = set()
    # 1) “下一页 / 下页 / Next / » / > / ›”链接
    for m in re.finditer(r'<a\b[^>]*?href=["\']([^"\']+)["\'][^>]*>(?:[^<]{0,15})(?:下一页|下页|Next|»|>|›)',
                         html, re.I):
        u = m.group(1)
        if not u.startswith(("javascript:", "#")):
            cands.add(urllib.parse.urljoin(page_url, u))
    # 2) 明确的数字页码链接（路径含 page/p/list）
    for m in re.finditer(r'<a\b[^>]*?href=["\']([^"\']*(?:page|/p/|list_)[^"\']*)["\'][^>]*>\s*\d+\s*</a>',
                         html, re.I):
        cands.add(urllib.parse.urljoin(page_url, m.group(1)))
    # 3) 仅当页面本身已含 page 参数时，才推断下一个 page=N
    p = urllib.parse.urlparse(page_url)
    qs = urllib.parse.parse_qs(p.query)
    if "page" in qs:
        try:
            cur = int(qs["page"][0])
            if cur < max_pages:
                nq = dict(qs)
                nq["page"] = [str(cur + 1)]
                cands.add(urllib.parse.urlunparse(p._replace(
                    query=urllib.parse.urlencode(nq, doseq=True))))
        except Exception:
            pass
    return cands


def check_pdf_head(url, referer, timeout=15):
    """HEAD 请求校验 PDF 可访问，返回 (ok, status, size)。"""
    import urllib.request, urllib.error
    h = {"User-Agent": g.UA, "Referer": referer or urllib.parse.urljoin(url, "/"),
         "Accept": "application/pdf,*/*"}
    try:
        req = urllib.request.Request(g.enc_url(url), headers=h, method="HEAD")
        with urllib.request.urlopen(req, timeout=timeout) as r:
            cl = r.headers.get("Content-Length", "")
            ct = r.headers.get("Content-Type", "")
            ok = r.status == 200 and ("pdf" in ct.lower() or cl.isdigit())
            return ok, r.status, int(cl) if cl.isdigit() else 0
    except urllib.error.HTTPError as e:
        # 部分服务器不支持 HEAD，退回 GET 只读首字节
        if e.code in (403, 405, 501):
            try:
                req = urllib.request.Request(g.enc_url(url), headers=h)
                with urllib.request.urlopen(req, timeout=timeout) as r:
                    r.read(1024)
                    cl = r.headers.get("Content-Length", "")
                    return True, r.status, int(cl) if cl.isdigit() else 0
            except Exception:
                return False, e.code, 0
        return False, e.code, 0
    except Exception as e:
        return False, 0, 0


def title_key(t):
    """标题归一化，用于跨 URL 去重（去掉空格/标点/大小写差异）。"""
    return re.sub(r"[^A-Za-z0-9\u4e00-\u9fa5]", "", (t or "").lower())


def crawl_brand(key, cfg, max_pages):
    brand = cfg["b"]
    referer = cfg.get("referer", "")
    manifest_path = f"{key}_manifest.json"
    manifest = []
    if os.path.exists(manifest_path):
        try:
            manifest = json.load(open(manifest_path, encoding="utf-8"))
        except Exception:
            manifest = []
    seen_urls = {x.get("url") or x.get("u") for x in manifest}
    seen_titles = {title_key(x.get("name") or x.get("t")) for x in manifest}

    visited = set()
    queue = list(cfg["start"])
    new_items = []
    page_count = 0
    brand_t0 = time.time()
    BRAND_BUDGET = 100  # 每个品牌最多耗时100秒，防止卡死整个流程
    while queue and page_count < max_pages and time.time() - brand_t0 < BRAND_BUDGET:
        url = queue.pop(0)
        if url in visited:
            continue
        visited.add(url)
        page_count += 1
        try:
            status, html, _ = g.http_get(url, referer=referer or url, timeout=12, retries=1)
        except Exception as e:
            print(f"  [第{page_count}页] 抓取失败 {url}: {e}")
            continue
        # 提取 PDF
        items = extract_pdf_with_titles(html, url)
        for pdf_url, title in items:
            if pdf_url in seen_urls:
                continue
            if title_key(title) in seen_titles:
                continue
            seen_urls.add(pdf_url)
            seen_titles.add(title_key(title))
            new_items.append((pdf_url, title))
        # 分页
        if page_count < max_pages:
            for nxt in find_next_pages(html, url, max_pages):
                if nxt not in visited and nxt not in queue:
                    queue.append(nxt)
        time.sleep(0.3)

    print(f"  浏览 {page_count} 页，发现 {len(new_items)} 个新 PDF，校验中...")
    added = 0
    bad = 0
    for pdf_url, title in new_items:
        if time.time() - brand_t0 >= BRAND_BUDGET:
            print("  品牌时间预算用尽，剩余 PDF 标记为未校验")
            break
        ok, sc, size = check_pdf_head(pdf_url, referer or pdf_url, timeout=10)
        if not ok:
            bad += 1
            # 仍记录，但标注不可访问，不静默跳过
            manifest.append({"name": title, "url": pdf_url, "pages": 0,
                             "type": "说明书", "size": 0, "brand": brand,
                             "src": urllib.parse.urlparse(pdf_url).netloc,
                             "status": f"不可访问({sc})", "date": ""})
            continue
        manifest.append({"name": title, "url": pdf_url, "pages": 0,
                         "type": "说明书", "size": size, "brand": brand,
                         "src": urllib.parse.urlparse(pdf_url).netloc,
                         "status": "ok", "date": ""})
        added += 1
        time.sleep(0.15)

    json.dump(manifest, open(manifest_path, "w", encoding="utf-8"),
              ensure_ascii=False, indent=1)
    print(f"  完成：新增可访问 {added}，不可访问 {bad}，品牌累计 {len(manifest)} 份")
    return added, bad


def main():
    args = sys.argv[1:]
    max_pages = 8
    if "--max-pages" in args:
        i = args.index("--max-pages")
        max_pages = int(args[i + 1])
        args = args[:i] + args[i + 2:]
    only = args

    total_added = 0
    total_bad = 0
    ran = 0
    for key, cfg in BRAND_SITES.items():
        if only and cfg["b"] not in only and key not in only:
            continue
        ran += 1
        print(f"【{cfg['b']}】采集中...")
        try:
            a, b = crawl_brand(key, cfg, max_pages)
            total_added += a
            total_bad += b
        except Exception as e:
            print(f"  品牌采集异常: {e}")
    print("=" * 50)
    print(f"通用采集完成：共 {ran} 个品牌，新增可访问 {total_added} 份，"
          f"不可访问 {total_bad} 份。")


if __name__ == "__main__":
    main()
