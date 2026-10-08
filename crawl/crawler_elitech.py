# -*- coding: utf-8 -*-
"""精创Elitech采集器：纯接口 ajax_manual(分类->产品) + ajax_manual_show(产品->PDF直链)，dl.e-elitech.com 直链下载。
URL hash 全局去重，同一份说明书跨产品不重复。幂等。"""
import urllib.request,urllib.parse,json,os,time,subprocess,re,hashlib
BASE="https://www.e-elitech.com/index.php"
DST="pdfs/elitech";os.makedirs(DST,exist_ok=True)
HEAD={"User-Agent":"Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/120 Safari/537.36",
 "X-Requested-With":"XMLHttpRequest","Referer":"https://www.e-elitech.com/index.php?v=new_manual"}
CATS=[("114","冷媒秤"),("115","数字压力表"),("116","冷媒检漏仪"),("117","温湿度计"),("118","温控器"),
 ("119","机组电控箱"),("120","温湿度记录仪"),("201","其他仪表工具"),("121","冷链温湿度监测仪"),
 ("216","管道模块"),("187","用户手册"),("122","其它")]
def post(v,d):
    body=urllib.parse.urlencode(d).encode()
    req=urllib.request.Request(BASE+"?v="+v,data=body,headers=HEAD,method="POST")
    with urllib.request.urlopen(req,timeout=30) as r:
        t=r.read().decode("utf-8","ignore")
    try:
        j=json.loads(t)
        if isinstance(j,str):t=j
    except Exception:pass
    return t
def get(url):
    req=urllib.request.Request(url,headers={"User-Agent":HEAD["User-Agent"],"Referer":"https://www.e-elitech.com/"})
    with urllib.request.urlopen(req,timeout=90) as r:
        return r.read()
def pages_of(fp):
    r=subprocess.run(["pdfinfo",fp],capture_output=True,text=True)
    for l in r.stdout.splitlines():
        if l.startswith("Pages:"):return int(l.split()[1])
    return 0
def run():
    # 云端增量：加载上一版 manifest（按URL），已记录的复用（含页数/fn），不重复下载、不重新 pdfinfo
    old={}
    if os.path.exists("elitech_manifest.json"):
        try:
            for x in json.load(open("elitech_manifest.json",encoding="utf-8")):
                if x.get("u"):old[x["u"]]=x
        except Exception:pass
    # 先收集所有产品（分类->产品）
    products={}
    for cid,cname in CATS:
        try:lst=post("ajax_manual",{"id":cid})
        except Exception as e:print("  分类%s失败 %s"%(cname,str(e)[:40]));continue
        for pid,name in re.findall(r'data-id="(\d+)"[^>]*>\s*<a[^>]*>([^<]+)',lst):
            products[pid]=(name.strip().replace("\\/","/"),cname)
    print("产品总数(去重):",len(products))
    recs={}  # key=urlhash -> rec
    n=0
    for pid,(name,cname) in products.items():
        n+=1
        try:det=post("ajax_manual_show",{"id":pid})
        except Exception as e:print("  产品%s失败 %s"%(name,str(e)[:30]));continue
        urls=list(dict.fromkeys(re.findall(r'https?://dl\.e-elitech\.com/(?:uploadfile|upload)/[^"\'\s<>]+?\.pdf',det)))
        mtime=re.search(r'更新时间[：:]\s*([0-9\-: ]+)',det)
        date=mtime.group(1)[:10] if mtime else ""
        for u in urls:
            u=u.replace("\\/","/")
            key=hashlib.md5(u.encode()).hexdigest()[:10]
            fn="ec_%s.pdf"%key;fp=os.path.join(DST,fn)
            ox=old.get(u)
            if ox and (ox.get("pages") or 0)>0:
                recs[key]=ox;continue
            if not(os.path.exists(fp) and os.path.getsize(fp)>10000):
                try:
                    raw=get(u)
                    if raw[:4]!=b"%PDF":print("  非PDF",name[:18]);continue
                    open(fp,"wb").write(raw)
                except Exception as e:print("  下载失败",name[:18],str(e)[:36]);continue
            if key not in recs:
                recs[key]={"t":"精创 %s %s"%(name,cname),"model":name,"cat":cname,"u":u,"fn":fn,
                  "pages":pages_of(fp),"size":os.path.getsize(fp),"d":date,"pids":[pid]}
        if n%50==0:print("  处理%d/%d 唯一PDF%d"%(n,len(products),len(recs)))
        time.sleep(0.15)
    out=list(recs.values())
    # 回填上一版已记录但本次接口未列出的历史URL（官网接口波动，保留历史只增不丢，不依赖磁盘文件）
    have_fn={r["fn"] for r in out}
    for u,ox in old.items():
        fn=ox.get("fn")
        if fn and fn not in have_fn:
            out.append(ox);have_fn.add(fn)
    json.dump(out,open("elitech_manifest.json","w",encoding="utf-8"),ensure_ascii=False,indent=1)
    print("精创PDF落盘 %d 个（%d 产品）"%(len(out),len(products)))
if __name__=="__main__":run()
