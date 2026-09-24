# -*- coding: utf-8 -*-
import json,re,time,urllib.request,os
BASE="https://www.e-elitech.com"
UA="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/120.0 Safari/537.36"
items=json.load(open("elitech_toc_items.json",encoding="utf-8"))
OUT="elitech_details.json"
done={}
if os.path.exists(OUT):
    for r in json.load(open(OUT,encoding="utf-8")):done[r["id"]]=r
def get(url,refer=None,retry=2):
    h={"User-Agent":UA,"Referer":refer or BASE+"/index.php?v=new_manual"}
    for k in range(retry+1):
        try:
            req=urllib.request.Request(url,headers=h)
            data=urllib.request.urlopen(req,timeout=25).read()
            if len(data)>500:return data.decode("utf-8","ignore")
        except Exception as e:
            time.sleep(0.6*(k+1))
    return ""
results=list(done.values())
new=0
for idx,it in enumerate(items):
    if it["id"] in done:continue
    url=BASE+"/index.php?v=new_manual_show&id="+it["id"]
    html=get(url)
    rec={"id":it["id"],"title":it["title"],"cats":it["cats"],"model":"","date":"","pdf":"","down":"","ok":False}
    if html:
        m=re.search(r'产品型号[:：]\s*(.*?)</span>',html,re.S)
        if m:rec["model"]=re.sub(r"\s+"," ",re.sub(r"<[^>]+>","",m.group(1))).strip()
        m=re.search(r'更新时间[：:]\s*([0-9]{4}-[0-9]{2}-[0-9]{2})',html)
        if m:rec["date"]=m.group(1)
        # 在线查看 真实PDF
        mp=re.search(r'href="(https://[^"]*?\.pdf)"[^>]*>\s*在线查看',html)
        if not mp:mp=re.search(r'href="(/uploadfile/[^"]*?\.pdf)"',html)
        if mp:
            u=mp.group(1)
            rec["pdf"]=u if u.startswith("http") else BASE+u
            rec["ok"]=True
        md=re.search(r'href="(https://[^"]*?f=down[^"]*?)"',html)
        if md:rec["down"]=md.group(1)
    results.append(rec);new+=1
    if new%25==0:
        json.dump(results,open(OUT,"w",encoding="utf-8"),ensure_ascii=False)
        print(f"进度 {idx+1}/{len(items)}  新抓 {new}  有PDF {sum(1 for r in results if r['ok'])}")
    time.sleep(0.3)
json.dump(results,open(OUT,"w",encoding="utf-8"),ensure_ascii=False)
ok=sum(1 for r in results if r["ok"])
print(f"\n完成: 总 {len(results)}  有PDF {ok}  无PDF/空 {len(results)-ok}")
