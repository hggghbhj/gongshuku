# -*- coding: utf-8 -*-
"""工书库 通用官网爬取/校验/去重工具。所有品牌爬虫共用。"""
import re,os,json,time,hashlib,urllib.request,urllib.parse,urllib.error,subprocess
UA="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
BASEDIR=os.path.dirname(os.path.abspath(__file__))
BASELINE=json.load(open(os.path.join(BASEDIR,"baseline.json"),encoding="utf-8"))

def http_get(url,referer=None,timeout=25,retries=2,head=None):
    h={"User-Agent":UA,"Accept":"text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
       "Accept-Language":"zh-CN,zh;q=0.9"}
    if referer:h["Referer"]=referer
    if head:h.update(head)
    last=None
    for i in range(retries+1):
        try:
            req=urllib.request.Request(url,headers=h)
            with urllib.request.urlopen(req,timeout=timeout) as r:
                data=r.read()
                enc=r.headers.get_content_charset() or "utf-8"
                try:txt=data.decode(enc)
                except:txt=data.decode("utf-8","ignore")
                return r.status,txt,r.headers
        except urllib.error.HTTPError as e:
            last=e
            if e.code in (403,502):
                # 尝试简单 cookie challenge
                body=e.read().decode("utf-8","ignore")
                m=re.findall(r"document\.cookie='(\w+)=([^;']+)'",body)
                if m and i==0:
                    cookie="; ".join("%s=%s"%(k,v) for k,v in m)
                    h["Cookie"]=cookie;time.sleep(0.5);continue
            time.sleep(1)
        except Exception as e:
            last=e;time.sleep(1)
    raise last

def pdf_links(html,page_url):
    """从HTML提取所有PDF链接（含相对路径，返回绝对URL）"""
    out=set()
    for m in re.findall(r'["\']([^"\']+?\.pdf)["\']',html,re.I):
        out.add(urllib.parse.urljoin(page_url,m))
    # 也匹配 href=xxx.pdf（无引号）
    for m in re.findall(r'href=([^\s>]+\.pdf)',html,re.I):
        out.add(urllib.parse.urljoin(page_url,m.strip('"\'')))
    return sorted(out)

def enc_url(url):
    p=urllib.parse.urlsplit(url)
    return urllib.parse.urlunsplit((p.scheme,p.netloc,urllib.parse.quote(p.path,safe="/%"),
        urllib.parse.quote(p.query,safe="/=&?%"),p.fragment))

def download_pdf(url,dest,referer=None,timeout=60):
    h={"User-Agent":UA,"Referer":referer or urllib.parse.urljoin(url,"/")}
    req=urllib.request.Request(enc_url(url),headers=h)
    with urllib.request.urlopen(req,timeout=timeout) as r:
        data=r.read()
    if len(data)<1000 or not data[:4].startswith(b"%PDF"):return False,len(data),"非PDF"
    os.makedirs(os.path.dirname(dest),exist_ok=True)
    open(dest,"wb").write(data)
    return True,len(data),data[:5]

def pdf_meta(path):
    """返回页数/白页判定。坏PDF返回None。"""
    try:
        info=subprocess.run(["pdfinfo",path],capture_output=True,text=True,timeout=30).stdout
        pages=int(re.search(r"Pages:\s+(\d+)",info).group(1))
    except Exception:return None
    # 渲染首页检测非白
    try:
        os.system("pdftoppm -f 1 -l 1 -r 40 -png '%s' /tmp/_gsk_pg >/dev/null 2>&1"%path.replace("'","'\\''"))
        import glob
        from PIL import Image;import numpy as np
        fs=glob.glob("/tmp/_gsk_pg*")
        if not fs:return {"pages":pages,"white":None}
        a=np.array(Image.open(fs[0]).convert("L"))
        white=float((a<235).mean())
        for f in fs:os.remove(f)
        return {"pages":pages,"white":white}
    except Exception:return {"pages":pages,"white":None}

def norm_url(u):
    u=u.lower().replace("http://","https://").replace("www.","")
    u=u.split("?")[0].rstrip("/")
    return u

def mk(s):return re.sub(r"[^A-Z0-9\u4e00-\u9fa5]","",(s or "").upper())

def url_in_lib(url):
    n=norm_url(url)
    for d in BASELINE:
        if norm_url(d.get("pdf",""))==n:return True
    return False

def model_in_lib(model,brand=None):
    """型号是否已在库（按主型号token）。返回命中条数。"""
    blob=[]
    for d in BASELINE:
        if brand and d.get("b")!=brand:continue
        blob.append(d)
    ts=set()
    for t in re.findall(r"[A-Za-z]{2,6}[-]?[0-9][0-9A-Za-z+]*",(model or "").upper()):
        k=mk(t)
        if len(k)>=4:ts.add(k)
    hits=0
    for d in blob:
        b=mk(d.get("t","")+" "+d.get("kw",""))
        if any(k in b for k in ts):hits+=1
    return hits

def make_record(brand,title,model,category,date,pdf,url,size,pages,lang,src,kw_extra=""):
    def kw_for(c):
        return {"温控器":"温控器 温度控制器 制冷 冷库 冷柜","变频器":"变频器 变频调速 传动",
        "PLC":"PLC 可编程控制器","触摸屏":"HMI 触摸屏 人机界面","伺服":"伺服 电机 驱动器",
        "记录仪":"记录仪 数据采集","压力表":"压力表 数字压力表","冷媒秤":"冷媒秤 制冷 加注",
        "检漏仪":"检漏仪 冷媒检漏","保护器":"电机保护器 保护装置"}.get(c,"")
    return {"t":title,"b":brand,"d":date or "","ty":"使用手册","v":"","l":lang or "中文",
        "url":url or pdf,"pdf":pdf,"size":(str(round(size/1024))+"KB" if size else ""),
        "kw":brand+" "+model+" "+kw_for(category)+" "+kw_extra,
        "sum":"%s %s 说明书，官网免费在线PDF，共%s页。"%(brand,model,pages or "?"),
        "src":src}
