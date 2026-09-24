# -*- coding: utf-8 -*-
import json,re,time,urllib.request
BASE="https://www.e-elitech.com"
UA="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/120.0 Safari/537.36"
CATS=[("114","冷媒秤"),("115","数字压力表"),("116","冷媒检漏仪"),("117","温湿度计"),("118","温控器"),("119","机组电控箱"),("120","温湿度记录仪"),("201","其他仪表工具"),("121","冷链温湿度监测仪"),("216","管道模块"),("187","用户手册"),("122","其它")]
def post(v,data):
    body=urllib.parse.urlencode(data).encode()
    req=urllib.request.Request(BASE+"/index.php?v="+v,data=body,headers={
        "User-Agent":UA,"X-Requested-With":"XMLHttpRequest",
        "Referer":BASE+"/index.php?v=new_manual","Origin":BASE,
        "Content-Type":"application/x-www-form-urlencoded"})
    return urllib.request.urlopen(req,timeout=30).read().decode("utf-8","ignore")
def clean(x):return re.sub(r"\s+"," ",re.sub(r"<[^>]+>","",x)).strip()
all_items={}
for cid,cname in CATS:
    try:
        raw=post("ajax_manual",{"id":cid})
        html=json.loads(raw)
        rows=re.findall(r'data-id="(\d+)"[^>]*>\s*<a[^>]*>(.*?)</a>',html,re.S)
        n=0
        for i,t in rows:
            title=clean(t)
            if i not in all_items:
                all_items[i]={"id":i,"title":title,"cats":[cname]}
            else:
                if cname not in all_items[i]["cats"]:all_items[i]["cats"].append(cname)
            n+=1
        print(f"{cid} {cname}: {n} 条目")
    except Exception as e:
        print(f"{cid} {cname}: 错误 {e}")
    time.sleep(0.4)
items=list(all_items.values())
print("\n官网说明书唯一条目总数:",len(items))
json.dump(items,open("elitech_toc_items.json","w",encoding="utf-8"),ensure_ascii=False,indent=1)
# 按分类统计
from collections import Counter
c=Counter()
for it in items:
    for x in it["cats"]:c[x]+=1
print(dict(c))
