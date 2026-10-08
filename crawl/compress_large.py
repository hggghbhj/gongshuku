# -*- coding: utf-8 -*-
"""压缩 dist/pdfs 中超过25MB的PDF，压不下去的移出到备份目录。"""
import os, subprocess, sys
from concurrent.futures import ThreadPoolExecutor, as_completed

ROOT = os.path.dirname(os.path.abspath(__file__))
DIST = os.path.join(ROOT, "..", "dist")
BACKUP = os.path.join(ROOT, "pdfs_large_backup")
LIMIT = 25 * 1024 * 1024

def find_large():
    out = []
    for root, _, files in os.walk(os.path.join(DIST, "pdfs")):
        for f in files:
            if f.endswith(".pdf"):
                fp = os.path.join(root, f)
                if os.path.getsize(fp) > LIMIT:
                    out.append(fp)
    return out

def compress(fp):
    tmp = fp + ".tmp"
    try:
        subprocess.run(["gs", "-sDEVICE=pdfwrite", "-dCompatibilityLevel=1.4",
            "-dPDFSETTINGS=/ebook", "-dNOPAUSE", "-dQUIET", "-dBATCH",
            "-sOutputFile=" + tmp, fp], timeout=120, check=True)
        if os.path.exists(tmp) and os.path.getsize(tmp) > 1000:
            if os.path.getsize(tmp) < LIMIT:
                os.replace(tmp, fp)
                return "ok"
            os.remove(tmp)
            return "large"
        return "fail"
    except Exception:
        if os.path.exists(tmp):
            os.remove(tmp)
        return "fail"

def move_out(fp):
    rel = os.path.relpath(fp, os.path.join(DIST, "pdfs"))
    dst = os.path.join(BACKUP, rel)
    os.makedirs(os.path.dirname(dst), exist_ok=True)
    os.rename(fp, dst)

def main():
    pdfs = find_large()
    print(f"待压缩: {len(pdfs)}")
    if not pdfs:
        print("无超限文件")
        return
    results = {"ok": 0, "large": 0, "fail": 0}
    still_large = []
    with ThreadPoolExecutor(max_workers=4) as ex:
        futs = {ex.submit(compress, fp): fp for fp in pdfs}
        for f in as_completed(futs):
            r = f.result()
            results[r] += 1
            if r in ("large", "fail"):
                still_large.append(futs[f])
    print(f"压缩成功={results['ok']} 仍超限={results['large']} 失败={results['fail']}")
    for fp in still_large:
        move_out(fp)
        print("  移出:", os.path.relpath(fp, DIST))
    print(f"移出 {len(still_large)} 个到备份目录")

if __name__ == "__main__":
    main()
