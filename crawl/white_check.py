import json,glob,subprocess,os,re
v=json.load(open("verified_pdfs.json"))
out=[]
for r in v:
    if not r.get("file"):continue
    f=r["file"]
    try:
        info=subprocess.run(["pdfinfo",f],capture_output=True,text=True,timeout=20).stdout
        mp=re.search(r"Pages:\s+(\d+)",info)
        pages=int(mp.group(1)) if mp else 0
        # 提取前3页+全文字符数
        txt=subprocess.run(["pdftotext","-f","1","-l","5",f,"-"],capture_output=True,text=True,timeout=30).stdout
        nchar=len(re.sub(r"\s+","",txt))
        # 图片对象数
        raw=open(f,"rb").read()
        nimg=raw.count(b"/Image")+raw.count(b"/XObject")
        r["pages"]=pages;r["text5"]=nchar;r["hasImg"]=nimg
        if pages==0:r["flag"]="打不开/0页"
        elif nchar<20 and nimg<3:r["flag"]="疑似白页(无文字无图)"
        elif nchar<20:r["flag"]="扫描件(图)"
        else:r["flag"]="正常"
    except Exception as e:
        r["flag"]="解析异常:"+str(e)[:40]
    out.append(r)
json.dump(out,open("white_check.json","w",encoding="utf-8"),ensure_ascii=False,indent=1)
for r in out:
    print(f'{r["i"]:>2} {r["flag"]:<18} 页{r.get("pages","?"):>3} 字{r.get("text5",0):>6} 图{r.get("hasImg",0):>3}  {r["model"][:26]}')
