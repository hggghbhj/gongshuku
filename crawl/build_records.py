# -*- coding: utf-8 -*-
import json,re,subprocess
det={d["id"]:d for d in json.load(open("elitech_details.json",encoding="utf-8"))}
wc=json.load(open("white_check.json",encoding="utf-8"))
cand={r["i"]:r for r in wc if r.get("status")=="ok"}
SKIP={22:"BCD-20损坏",27:"EK-3010",28:"GSP-6",29:"GSP-6",30:"GSP-8A",31:"HLD-100+",
32:"Loget8库已有",33:"MTC-5060",34:"RC-18",35:"RC-4系列库已有",36:"RC-5库已有",
37:"RC-5+库已有",38:"RCW-360",39:"RCW-600",40:"STC-1000X",41:"STC-200",
42:"STC-9100",44:"TLOG系列库已有",47:"HETL-DTU-3"}
CAT2KW={"冷媒秤":"冷媒秤 制冷 加注 回收","温湿度计":"温湿度计 测温 测湿","温控器":"温控器 温度控制器 制冷 冷库 冷柜",
"机组电控箱":"机组电控箱 制冷 冷库 控制器","温湿度记录仪":"温湿度记录仪 数据记录仪",
"管道模块":"管道模块 DTU 通讯","用户手册":"用户手册 操作说明","其它":"制冷配件"}
CAT2KIND={"温湿度记录仪":"温湿度记录仪","温湿度计":"温湿度计","冷媒秤":"冷媒秤","温控器":"温控器",
"机组电控箱":"机组电控箱","管道模块":"管道模块","其它":"仪表工具","用户手册":"仪表工具"}
EN_MODELS={7,19,21}
def version_of(fp):
    try:
        txt=subprocess.run(["pdftotext","-f","1","-l","1",fp,"-"],capture_output=True,text=True,timeout=15).stdout
        m=re.search(r"V\d+\.\d+",txt);return m.group(0) if m else ""
    except Exception:return ""
recs=[]
for i in sorted(cand):
    if i in SKIP:continue
    r=cand[i]
    orig=None
    for d in det.values():
        if d.get("ok") and d.get("pdf")==r["url"]:orig=d;break
    model=r["model"];cat=r["cat"]
    en = i in EN_MODELS or (bool(re.search(r"[A-Za-z]{3,}",model)) and not re.search(r"[一-鿿]",model))
    if i==7:t="精创 ERS-210 无线冷媒秤英文用户手册"
    elif i==45:t="精创冷云平台使用指引（软件/平台手册）"
    elif i==23:t="精创 DTU-4 管道产品使用手册"
    elif i==46:t="精创 冷库灯 ledD-L-80mA-10W 说明书"
    else:t="精创 "+model+" "+CAT2KIND.get(cat,"仪表工具")+"说明书"
    rec={"t":t,"b":"精创","d":r["date"],"ty":"使用手册","v":version_of(r["file"]),
        "l":"英文" if en else "中文",
        "url":("https://www.e-elitech.com/index.php?v=new_manual_show&id="+orig["id"]) if orig else "",
        "pdf":r["url"],"size":(str(round(r["size"]/1024))+"KB" if r["size"] else ""),
        "kw":"精创 Elitech "+model+" "+CAT2KW.get(cat,"制冷 工控 仪表"),
        "sum":"精创(Elitech) "+model+" 说明书，精创官网免费在线PDF，共"+str(r.get("pages",""))+"页。",
        "src":"精创官网"}
    recs.append(rec)
json.dump(recs,open("elitech_new_records.json","w",encoding="utf-8"),ensure_ascii=False,indent=1)
print("最终新增记录:",len(recs))
for r in recs:print(f'  [{r["l"]}] {r["t"][:44]:44} {r["v"]:>6} {r["d"]} {r["size"]:>8}')
