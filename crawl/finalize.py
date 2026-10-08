# -*- coding: utf-8 -*-
import json,re,hashlib
docs=json.load(open("baseline.json",encoding="utf-8"))
jc=[d for d in docs if d.get("b") and "精创" in d["b"]]
det={d["id"]:d for d in json.load(open("elitech_details.json",encoding="utf-8"))}
wc=json.load(open("white_check.json",encoding="utf-8"))
def mk(s):return re.sub(r"[^A-Z0-9]","",(s or "").upper())
def model_tokens(s):
    out=set()
    for t in re.findall(r"[A-Za-z]{2,6}[-]?[0-9][0-9A-Za-z+]*",(s or "").upper()):
        k=mk(t)
        if len(k)>=4:out.add(k)
    return out
# 候选明细：i -> (model, cat, date, pdf, url, size, pages, sha)
cand={r["i"]:r for r in wc if r.get("status")=="ok"}
# 手工补 #45-47 判定（#45 冷云平台软件；#46 冷库灯；#47 HETL-DTU）
# 对每个候选做型号级去重：库里是否已有同型号（按主型号前缀，如 RC-4 家族）
def lib_has_model(tokens, title):
    hits=[]
    for d in jc:
        blob=mk(d.get("t","")+" "+d.get("kw",""))
        for k in tokens:
            # 主型号（数字部分）出现在库内即视为同型号
            if k in blob:
                hits.append((d["t"],d.get("d","")));break
    return hits
KEEP=[];SKIP=[]
for i in sorted(cand):
    r=cand[i]
    model=r["model"]
    toks=model_tokens(model)
    # 特殊：软件平台/通用手册/无明确型号
    soft = any(w in model for w in ["冷云","平台"])
    hits=lib_has_model(toks,model) if not soft else []
    r["libHits"]=hits
    if hits:
        SKIP.append((i,model,"库内已有同型号: "+hits[0][0][:30]))
    else:
        KEEP.append(r)
print("=== 最终新增（全新型号/库内没有）===",len(KEEP))
for r in KEEP:print(f'  {r["i"]:>2} [{r["cat"]}] {r["model"][:36]} {r["date"]} 页{r.get("pages")}')
print("\n=== 跳过（同型号已有手册）===",len(SKIP))
for i,m,why in SKIP:print(f"  {i:>2} {m[:34]}  <- {why}")
json.dump({"keep":KEEP},open("final_keep.json","w",encoding="utf-8"),ensure_ascii=False,indent=1)
