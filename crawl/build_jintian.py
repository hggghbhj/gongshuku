# -*- coding: utf-8 -*-
import json,os,re,glob,subprocess
from urllib.parse import unquote,quote
p="/home/user/Doubao/chats/38443037035314434/gsk-crawl/"
meta=json.load(open(p+"jintian_meta.json",encoding="utf-8"))
purls=json.load(open(p+"jintian_pdfs.json",encoding="utf-8"))
# URL -> 本地文件序号（解码归一化）
def norm(u):
    u=unquote(u).lower().replace("http://","").replace("https://","")
    return u
url2idx={}
for i,it in enumerate(purls):
    url2idx[norm(it["h"])]=i

def pages_of(fp):
    try:
        r=subprocess.run(["pdfinfo",fp],capture_output=True,text=True,timeout=30)
        return int([l for l in r.stdout.splitlines() if l.startswith("Pages:")][0].split()[1])
    except:return 0

def parse_model(title):
    t=title.replace(".pdf","")
    # 特殊命名
    special={
      "永磁电机合订版":"永磁电机合订版(JTP/JTF/JTY)","金田永磁电机一体机":"永磁电机一体机(JTB)",
      "智慧供水全系列":"智慧供水全系列","软起动接线示意图":"软起动接线示意图",
    }
    for k,v in special.items():
        if k in t:return v
    # 标准型号
    m=re.search(r"((?:JTE|JT|JRG|TH|WT|SM|MQ|BH)[- ]?[0-9A-Za-z-]+)",t)
    if m:
        x=m.group(1).upper().replace(" ","").rstrip("-")
        x=re.sub(r"说明书.*$","",x)
        return x
    # 纯数字系列（386F6、930E、330S2 等）
    m=re.search(r"(\d{3}[A-Z]?\d?(?:S|H|E|F|N)?)",t)
    if m:return m.group(1)
    return t.split("说明书")[0][:20]

def parse_ver(title):
    m=re.search(r"[Vv]\s?(\d+\.\d+)",title)
    if m:return "V"+m.group(1)
    m=re.search(r"([A-G])版",title)
    if m:return m.group(1)+"版"
    return ""

def parse_type(title,pg):
    if "接线示意图" in title or "电路" in title:return "接线图"
    if "单页" in title:return "单页手册"
    if "英文" in title:return "说明书(英文)"
    if "合订" in title:return "说明书合订本"
    if "一体机" in title:return "说明书"
    if "柜" in title:return "说明书"
    return "说明书"

recs=[];skipped=[]
for e in meta:
    u=e["h"];title=e["title"];date=e["date"]
    idx=url2idx.get(norm(u))
    if idx is None:
        skipped.append((title,"无本地文件"));continue
    fp=p+"pdfs/jintian/jt_%03d.pdf"%idx
    if not os.path.exists(fp):
        skipped.append((title,"文件缺失"));continue
    pg=pages_of(fp);sz=os.path.getsize(fp)
    model=parse_model(title);ver=parse_ver(title);ty=parse_type(title,pg)
    lang="英文" if "英文" in title else "中文"
    # 日期标准化
    d=""
    m=re.search(r"(20\d{2})-(\d{1,2})-(\d{1,2})",date)
    if m:d="%s-%02d-%02d"%(m.group(1),int(m.group(2)),int(m.group(3)))
    # 去重：JTE320 官网 V4.2 比库内 V2.06 新保留；JTE330 官网 V2.0 旧但保留(不同型号命名)
    # 生成标题（已含“金田”则不重复加前缀）
    clean=title.replace(".pdf","").strip()
    if clean.startswith("金田"):
        t=clean
    else:
        t="金田 %s"%clean
    kw=model
    rec={"t":t,"b":"金田","d":d,"ty":ty,"v":ver,"l":lang,
         "url":"http://jtdrive.com/downs/sms","pdf":u,
         "size":str(round(sz/1024))+"KB","kw":kw,
         "sum":"金田官方说明书 %s %s %s %d页"%(model,ver,lang,pg),
         "src":"金田官网 jtdrive.com"}
    recs.append(rec)
json.dump(recs,open(p+"kv_jintian.json","w",encoding="utf-8"),ensure_ascii=False,indent=1)
print("金田记录:",len(recs),"跳过:",len(skipped))
for s in skipped:print("  跳过",s)
print("--- 样例 ---")
for r in recs[:8]:print(" ",r["t"][:38],"|",r["v"],"|",r["d"],"|",r["kw"])
print("...")
for r in recs[-6:]:print(" ",r["t"][:38],"|",r["v"],"|",r["kw"])
