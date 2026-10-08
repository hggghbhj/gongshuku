# -*- coding: utf-8 -*-
"""把docs-3.js里已下载的PDF外链批量改成本地路径。
优先从manifest的fn字段建立URL->本地文件映射，再用URL basename兜底。"""
import json, re, os, glob
from urllib.parse import unquote, urlparse, quote, urlunparse

ROOT = os.path.dirname(os.path.abspath(__file__))
DIST = os.path.join(ROOT, "..", "dist")
DOCS3 = os.path.join(DIST, "data", "docs-3.js")

# 复用batch_download的DIR_MAP
import importlib.util
spec = importlib.util.spec_from_file_location("bd", os.path.join(ROOT, "batch_download.py"))
bd = importlib.util.module_from_spec(spec)
spec.loader.exec_module(bd)
DIR_MAP = bd.DIR_MAP

def encode_url(url):
    parsed = urlparse(url)
    if parsed.path:
        path = quote(parsed.path, safe="/%")
        return urlunparse((parsed.scheme, parsed.netloc, path,
                          parsed.params, parsed.query, parsed.fragment))
    return url

def build_manifest_map():
    """从manifest建立 URL -> 本地web路径 的映射。"""
    m = {}
    for mp in glob.glob(os.path.join(ROOT, "*_manifest.json")):
        key = os.path.basename(mp).replace("_manifest.json", "")
        bdir = DIR_MAP.get(key, key)
        try:
            data = json.load(open(mp, encoding="utf-8"))
        except: continue
        for r in data:
            url = r.get("u") or r.get("url") or r.get("durl") or ""
            fn = r.get("fn") or r.get("pdf") or ""
            if not url: continue
            if fn:
                if "/" in fn:
                    webpath = "/" + fn
                else:
                    webpath = f"/pdfs/{bdir}/{fn}"
            else:
                # 没有fn，用URL basename
                base = os.path.basename(unquote(urlparse(url).path))
                webpath = f"/pdfs/{bdir}/{base}" if base else ""
            # 验证文件存在
            if webpath:
                local = os.path.join(DIST, webpath.lstrip("/"))
                if os.path.exists(local):
                    m[url] = webpath
                    m[encode_url(url)] = webpath
    return m

def find_local_fallback(brand, url):
    """兜底：从URL提取文件名匹配。"""
    d = DIR_MAP.get(brand, brand)
    bdir = os.path.join(DIST, "pdfs", d)
    if not os.path.isdir(bdir):
        return None
    files = os.listdir(bdir)
    path = unquote(urlparse(url).path)
    base = os.path.basename(path)
    if base in files:
        return f"/pdfs/{d}/{base}"
    m = re.search(r"id=(\d+)", url)
    if m:
        prefix = m.group(1) + "_"
        for f in files:
            if f.startswith(prefix) and f.endswith(".pdf"):
                return f"/pdfs/{d}/{f}"
    if base and len(base) > 5:
        key = base[:20]
        for f in files:
            if key in f:
                return f"/pdfs/{d}/{f}"
    return None

def main():
    manifest_map = build_manifest_map()
    print("manifest URL映射:", len(manifest_map))

    s = open(DOCS3, encoding="utf-8").read()
    m = re.search(r"DOCS=DOCS\.concat\((\[.*\])\);", s, re.DOTALL)
    docs = json.loads(m.group(1))
    changed = 0
    still_ext = 0
    for d in docs:
        pdf = d.get("pdf", "")
        if pdf.startswith("/pdfs/"):
            continue
        # 优先用manifest映射
        local = manifest_map.get(pdf) or manifest_map.get(encode_url(pdf))
        if not local:
            local = find_local_fallback(d.get("b", ""), pdf)
        if local:
            d["pdf"] = local
            changed += 1
        else:
            still_ext += 1

    out = "/* 工书库数据分片3 */\nDOCS=DOCS.concat("
    out += json.dumps(docs, ensure_ascii=False, separators=(",", ":"))
    out += ");\n"
    open(DOCS3, "w", encoding="utf-8").write(out)
    print(f"改成本地路径: {changed}")
    print(f"仍外链: {still_ext}")
    total_local = sum(1 for d in docs if d.get("pdf", "").startswith("/pdfs/"))
    print(f"本地路径总数: {total_local}/{len(docs)}")
    from collections import Counter
    ext_brands = Counter()
    for d in docs:
        if not d.get("pdf", "").startswith("/pdfs/"):
            ext_brands[d.get("b", "?")] += 1
    print("仍外链TOP10:", ext_brands.most_common(10))

if __name__ == "__main__":
    main()
