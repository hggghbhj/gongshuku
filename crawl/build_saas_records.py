# -*- coding: utf-8 -*-
"""从下载结果生成标准记录：去重(内容hash/URL/型号) + 解析型号/版本/日期 + 对齐baseline。"""
import json,os,re,sys,hashlib,urllib.parse,datetime
sys.path.insert(0,".")
from gsk_common import BASELINE,norm_url,mk,url_in_lib
brand=sys.argv[1]; resdir=sys.argv[2]; signedfile=sys.argv[3]; sitehome=sys.argv[4]; outfile=sys.argv[5]
res=json.load(open(os.path.join(resdir,"_dl_results.json"),encoding="utf-8"))
signed=json.load(open(signedfile,encoding="utf-8"))
orig_by_fn={}
for orig,_ in signed:
    fn=urllib.parse.unquote(orig.split("/file/")[-1].split("?")[0])
    orig_by_fn[fn]=orig
# baseline 该品牌型号集合
def brand_models(b):
    out=set()
    for d in BASELINE:
        if d.get("b")==b:
            out.add(mk(d.get("t","")))
    return out

# 库内该品牌记录，供型号+版本精细比对
brand_lib=[d for d in BASELINE if d.get("b")==brand]
def lib_has_manual(model):
    """库内是否已有同型号的完整手册(非样本/彩页)。返回库内日期或None"""
    key=mk(model)
    if len(key)<4:return None
    for d in brand_lib:
        t=mk(d.get("t",""))
        if key in t:
            title=d.get("t","")
            if re.search(r"样本|彩页|综合|sample|catalog|brochure",title,re.I):
                continue  # 库内是样本，不影响手册收录
            return d.get("d","") or ""
    return None
def parse_model(fn):
    s=fn.replace(".pdf","").replace(".PDF","")
    s=re.sub(r"^20\d{2}\s*版\s*","",s)
    s=re.sub(r"中文版|标准中文|中文","",s)
    # 旁路式软起动 620 / 6200
    m=re.search(r"旁路式软起动说明书\s*(\d{3,4})",s)
    if m:return "旁路式软起动 "+m.group(1)
    # 下划线/连字符连接的多型号 pi7800_7600
    m=re.match(r"^([a-z]{1,5}[-]?[0-9][0-9a-z]*(?:[_-][0-9a-z]+)*)",s,re.I)
    if m:return m.group(1)
    # 纯数字型号 630/6300（在“系列/说明书”前）
    m=re.search(r"(\d{3,4})\s*系列",s)
    if m:return m.group(1)
    # profinet 通讯扩展卡
    if "profinet" in s.lower():return "Profinet通讯扩展卡"
    if "adsd" in s.lower():
        m=re.match(r"^(adsd-[a-z0-9-]+)",s,re.I)
        if m:return m.group(1)
    return s.split("说明书")[0].split("系列")[0][:20]
def parse_date(fn):
    m=re.search(r"(20\d{2})[-年]?\s?(\d{1,2})[-月]?\s?(\d{1,2})",fn)
    if m:
        try:
            y,mo,da=int(m.group(1)),int(m.group(2)),int(m.group(3))
            if 1<=mo<=12 and 1<=da<=31:return "%04d-%02d-%02d"%(y,mo,da)
        except:pass
    m=re.search(r"(20\d{2})(\d{2})(\d{2})",fn)
    if m:
        y,mo,da=int(m.group(1)),int(m.group(2)),int(m.group(3))
        if 1<=mo<=12 and 1<=da<=31:return "%04d-%02d-%02d"%(y,mo,da)
    return ""
def parse_ver(fn):
    m=re.search(r"[vV](\d+\.\d+[a-z]?)",fn)
    return ("v"+m.group(1)) if m else ""
def cat_of(fn):
    low=fn
    if re.search(r"软起动|软启动|soft",low):return "软起动器"
    if re.search(r"制动单元|制动",low):return "制动单元"
    if re.search(r"通讯|通信|扩展卡|profinet|rs485|485",low):return "通讯附件"
    if re.search(r"中频|电磁搅拌",low):return "中频电源"
    if re.search(r"光伏|水泵",low):return "变频器"
    if re.search(r"变频器|变频",low):return "变频器"
    return "变频器"
def lang_of(fn):
    return "英文" if re.search(r"[A-Za-z]{5,}",fn) and not re.search(r"中文|说明书|手册|指南",fn) else "中文"
seen_hash=set(); seen_url=set(); seen_model=set(); recs=[]; dropped=[]
for r in res:
    if not r["ok"] or r["cls"]!="manual":continue
    fn=r["fn"]; orig=orig_by_fn.get(fn)
    if not orig:dropped.append((fn,"无URL映射"));continue
    # 内容hash
    data=open(r["dest"],"rb").read()
    h=hashlib.sha256(data).hexdigest()
    if h in seen_hash:dropped.append((fn,"内容重复"));continue
    seen_hash.add(h)
    if norm_url(orig) in seen_url or url_in_lib(orig):dropped.append((fn,"URL已在库"));continue
    seen_url.add(norm_url(orig))
    model=parse_model(fn)
    cat=cat_of(fn); ver=parse_ver(fn); date=parse_date(fn)
    title=fn.replace(".pdf","").strip()
    # 同型号去重：同型号保留版本/日期最新一份
    pages=(r["meta"] or {}).get("pages")
    rec={"t":"%s %s %s%s"%(brand,model,"使用说明书" if cat=="变频器" else cat+"说明书",(" "+ver) if ver else ""),
      "b":brand,"d":date,"ty":"使用手册","v":ver,"l":lang_of(fn),
      "url":sitehome,"pdf":orig,
      "size":str(round(r["size"]/1024))+"KB",
      "kw":"%s %s %s %s"%(brand,model,cat,fn),
      "sum":"%s %s 说明书（官网下载中心免费PDF，共%s页，%s）"%(brand,model,pages,date),
      "src":"官网:"+sitehome}
    recs.append(rec)
# 型号级去重（同品牌内保留最新），并与库内比对（库内样本不冲突；官网更新则保留）
best={}
for r in recs:
    model=parse_model(r["kw"])
    key=mk(model)
    libdate=lib_has_manual(model)
    if libdate is not None and (r["d"] or "") and r["d"]<=libdate:
        dropped.append((r["t"],"库内已有同型号手册 %s"%libdate));continue
    if libdate is not None and not r["d"]:
        # 无日期且库内有手册，保守跳过（避免更旧的重复）
        dropped.append((r["t"],"库内已有同型号手册(无日期)"));continue
    cur=best.get(key)
    if not cur or (r["d"] or "0")>=(cur["d"] or "0"):
        if cur:dropped.append((cur["t"],"同品牌同型号旧版"))
        best[key]=r
    else:dropped.append((r["t"],"同品牌同型号旧版"))
recs=list(best.values())
json.dump(recs,open(outfile,"w",encoding="utf-8"),ensure_ascii=False,indent=1)
print("品牌 %s 生成记录 %d 条"%(brand,len(recs)))
print("--- 剔除 ---")
for f,why in dropped:print("  %-60s %s"%(f[:60],why))
print("--- 记录 ---")
for r in recs:print("  %-45s %s p%s"%(r["t"][:45],r["d"],r["size"]))
