# -*- coding: utf-8 -*-
"""把dist/pdfs里超25MB的文件移到crawl/pdfs_large_backup，
并把docs-3.js对应条目改回官网外链（从manifest找URL）。"""
import json, re, os, glob, shutil

ROOT = os.path.dirname(os.path.abspath(__file__))
DIST = os.path.join(ROOT, "..", "dist")
LARGE = os.path.join(ROOT, "pdfs_large_backup")
DOCS3 = os.path.join(DIST, "data", "docs-3.js")
LIMIT = 25 * 1024 * 1024

# 建立本地路径 -> 官网URL的映射（从所有manifest）
def build_url_map():
    m = {}
    for mp in glob.glob(os.path.join(ROOT, "*_manifest.json")):
        try:
            data = json.load(open(mp, encoding="utf-8"))
        except: continue
        for r in data:
            pdf = r.get("pdf", "")
            url = r.get("url", "")
            if pdf and url:
                # pdf字段格式: pdfs/siemens/xxx.pdf
                m["/" + pdf] = url
    return m

def main():
    url_map = build_url_map()
    print("manifest URL映射:", len(url_map))

    # 找大文件
    moved = 0
    moved_paths = []
    for root, dirs, files in os.walk(os.path.join(DIST, "pdfs")):
        for f in files:
            fp = os.path.join(root, f)
            try:
                sz = os.path.getsize(fp)
            except: continue
            if sz > LIMIT:
                rel = os.path.relpath(fp, DIST)
                webpath = "/" + rel
                # 移到备份目录
                dst = os.path.join(LARGE, rel)
                os.makedirs(os.path.dirname(dst), exist_ok=True)
                shutil.move(fp, dst)
                moved_paths.append(webpath)
                moved += 1
    print("移出大文件:", moved)

    # 改docs-3.js
    s = open(DOCS3, encoding="utf-8").read()
    m = re.search(r"DOCS=DOCS\.concat\((\[.*\])\);", s, re.DOTALL)
    docs = json.loads(m.group(1))
    changed = 0
    for d in docs:
        pdf = d.get("pdf", "")
        if pdf in moved_paths:
            # 改回官网外链
            url = url_map.get(pdf)
            if url:
                d["pdf"] = url
                changed += 1
            else:
                # 找不到URL，保留路径但会404（文件在backup里）
                pass
    out = "/* 工书库数据分片3 */\nDOCS=DOCS.concat("
    out += json.dumps(docs, ensure_ascii=False, separators=(",", ":"))
    out += ");\n"
    open(DOCS3, "w", encoding="utf-8").write(out)
    print("改回外链:", changed)

    # 统计
    local = sum(1 for d in docs if d.get("pdf", "").startswith("/pdfs/"))
    print("现在本地路径:", local, "/", len(docs))

if __name__ == "__main__":
    main()
