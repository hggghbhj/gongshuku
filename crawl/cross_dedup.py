# -*- coding: utf-8 -*-
import json,re,os,time,hashlib,urllib.request
UA="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/120.0 Safari/537.36"
docs=json.load(open("baseline.json",encoding="utf-8"))
jc=[d for d in docs if d.get("b") and "精创" in d["b"]]
wc=json.load(open("white_check.json",encoding="utf-8"))
cands=[r for r in wc if r.get("status")=="ok" and r.get("final")!="渲染失败(打不开)"]
def mk(s):return re.sub(r"[^A-Z0-9]","",(s or "").upper())
def keys(model):
    # 提取候选里的所有型号token
    ts=re.findall(r"[A-Za-z]{1,6}[-]?[0-9][0-9A-Za-z+]*",(model or "").upper())
    out=set()
    for t in ts:
        k=mk(t)
        if len(k)>=4:out.add(k)
    # 特殊名
    for name in ["冷云","ALOG","LOGET","TLOG"]:
        if name in (model or "").upper():out.add(mk(name))
    return out
def dl_hash(url,dest):
    try:
        req=urllib.request.Request(url,headers={"User-Agent":UA,"Referer":"https://www.e-elitech.com/"})
        data=urllib.request.urlopen(req,timeout=40).read()
        if len(data)<1000 or not data.startswith(b"%PDF"):return None,len(data),False
        return hashlib.sha256(data).hexdigest(),len(data),True
    except Exception as e:return None,0,False
# 候选hash
cand_hash={}
for r in cands:
    if os.path.exists(r["file"]):
        cand_hash[r["i"]]=hashlib.sha256(open(r["file"],"rb").read()).hexdigest()
os.makedirs("cur_pdfs",exist_ok=True)
report=[]
for r in cands:
    ks=keys(r["model"])
    # 现有库匹配型号
    match=[]
    for d in jc:
        blob=mk(d.get("t","")+" "+d.get("kw",""))
        if any(k in blob for k in ks):match.append(d)
    dup=None;checked=0
    for d in match:
        fn="cur_pdfs/"+hashlib.md5(d["pdf"].encode()).hexdigest()[:10]+".pdf"
        if not os.path.exists(fn):
            h,sz,ok=dl_hash(d["pdf"],fn)
            if ok:open(fn,"wb").write(b"")  # placeholder; real data re-fetch below
            time.sleep(0.2)
        # 真正下载
        if os.path.getsize(fn)<1000:
            try:
                req=urllib.request.Request(d["pdf"],headers={"User-Agent":UA,"Referer":"https://www.e-elitech.com/"})
                data=urllib.request.urlopen(req,timeout=40).read()
                if data.startswith(b"%PDF"):open(fn,"wb").write(data)
            except Exception:pass
        if os.path.getsize(fn)>1000:
            checked+=1
            h=hashlib.sha256(open(fn,"rb").read()).hexdigest()
            if h==cand_hash.get(r["i"]):
                dup={"cur_t":d["t"],"pdf":d["pdf"]};break
    r["sameModelInLib"]=len(match);r["checked"]=checked;r["dupOfLib"]=dup
    tag="重复(跳过)" if dup else ("同型号不同版本(保留新版)" if match else "全新型号(新增)")
    report.append((r["i"],r["model"][:26],r["cat"],len(match),tag))
    print(f'{r["i"]:>2} 库内同型号{len(match):>2} 比对{checked:>2}  {tag}  {r["model"][:26]}')
json.dump(cands,open("dedup_final.json","w",encoding="utf-8"),ensure_ascii=False,indent=1)
keep=[r for r in cands if not r["dupOfLib"]]
print("\n=== 去重结论 ===")
print("候选有效:",len(cands),"内容与库重复:",len([r for r in cands if r["dupOfLib"]]),"最终保留新增:",len(keep))
