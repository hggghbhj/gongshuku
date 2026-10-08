# -*- coding: utf-8 -*-
"""并行压缩pdfs_large_backup里的大文件，压到25MB以下的移回dist/pdfs。"""
import os, subprocess
from concurrent.futures import ThreadPoolExecutor, as_completed

ROOT = os.path.dirname(os.path.abspath(__file__))
LARGE = os.path.join(ROOT, "pdfs_large_backup")
DIST = os.path.join(ROOT, "..", "dist")
LIMIT = 25 * 1024 * 1024

def compress_one(fp):
    rel = os.path.relpath(fp, LARGE)
    tmp = fp + ".tmp"
    try:
        subprocess.run(["gs", "-sDEVICE=pdfwrite", "-dCompatibilityLevel=1.4",
            "-dPDFSETTINGS=/ebook", "-dNOPAUSE", "-dQUIET", "-dBATCH",
            "-sOutputFile=" + tmp, fp], timeout=300, check=True, capture_output=True)
        if os.path.exists(tmp) and os.path.getsize(tmp) > 1000:
            if os.path.getsize(tmp) < LIMIT:
                # 移回dist
                dst = os.path.join(DIST, "pdfs", rel)
                os.makedirs(os.path.dirname(dst), exist_ok=True)
                os.replace(tmp, dst)
                return ("ok", rel)
            else:
                os.remove(tmp)
                return ("still_large", rel)
        return ("fail", rel)
    except Exception as e:
        if os.path.exists(tmp):
            os.remove(tmp)
        return ("fail", rel + " " + str(e)[:40])

def main():
    pdfs = []
    for root, _, files in os.walk(LARGE):
        for f in files:
            if f.endswith(".pdf"):
                pdfs.append(os.path.join(root, f))
    print(f"待压缩: {len(pdfs)}")
    ok = 0; fail = 0
    with ThreadPoolExecutor(max_workers=4) as ex:
        futs = {ex.submit(compress_one, fp): fp for fp in pdfs}
        for i, fut in enumerate(as_completed(futs)):
            status, rel = fut.result()
            if status == "ok":
                ok += 1
            else:
                fail += 1
            if (i+1) % 20 == 0:
                print(f"  进度 {i+1}/{len(pdfs)} | 成功{ok} 失败{fail}")
    print(f"=== 压缩完成: 成功{ok}, 失败{fail} ===")

if __name__ == "__main__":
    main()
