# -*- coding: utf-8 -*-
import json,re,subprocess
recs=json.load(open("elitech_new_records.json",encoding="utf-8"))
wc=json.load(open("white_check.json",encoding="utf-8"))
files={r["i"]:r["file"] for r in wc if r.get("status")=="ok"}
# 按 pdf 匹配 i
def detect_lang(fp):
    try:
        txt=subprocess.run(["pdftotext","-f","1","-l","3",fp,"-"],capture_output=True,text=True,timeout=20).stdout
    except Exception:return "中文"
    cn=len(re.findall(r"[一-鿿]",txt))
    en=len(re.findall(r"[A-Za-z]",txt))
    if cn>=10:return "中文"
    if en>=50 and cn<10:return "英文"
    return "中文"  # 扫描件/无文字，默认内贸中文
for r in recs:
    # 找到对应 i
    for i,fp in files.items():
        if wc[i-1] if False else None:pass
    pass
# 直接用 pdf 反查
for r in recs:
    for w in wc:
        if w.get("status")=="ok" and w.get("url")==r["pdf"]:
            lang=detect_lang(w["file"]);r["l"]=lang
            # 扫描件无文字的 ERS-210 大文件按中文；英文用户手册小文件保留英文
            if r["pdf"].endswith("2026061711501802wkv1.pdf"):r["l"]="英文"
            break
json.dump(recs,open("elitech_new_records.json","w",encoding="utf-8"),ensure_ascii=False,indent=1)
for r in recs:print(f'  [{r["l"]}] {r["t"][:42]}')
