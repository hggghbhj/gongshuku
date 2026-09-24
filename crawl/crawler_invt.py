#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""英威腾 INVT 官网说明书采集器（纯接口，幂等可重复运行）。
- 下载页：https://www.invt.com.cn/dowload-15（旧 download.html 会 301 到此）
- 列表：POST /home/download/productlist.html  body=page&limit&catId&type
- 直链：https://files.invt.com.cn/upload/download/...（SSL 证书链不全，需不校验；中文路径需 quote）
- files 域偶发阿里云 WAF，urllib 带 Referer 重试即可；只下手册类 PDF，排除证书/图/方案/报告。
"""
import json,os,ssl,subprocess,time,hashlib,urllib.request,urllib.parse,sys,re

BASE="https://www.invt.com.cn"
HERE=os.path.dirname(os.path.abspath(__file__))
OUT=os.path.join(HERE,"pdfs","invt");os.makedirs(OUT,exist_ok=True)
MAN=os.path.join(HERE,"invt_manifest.json")
SSLCTX=ssl.create_default_context();SSLCTX.check_hostname=False;SSLCTX.verify_mode=ssl.CERT_NONE
UA="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0 Safari/537.36"
# 只收录手册/说明书类（产品证书/图纸/方案/报告/单页排除）
KEEP_CAT={"产品手册","用户手册","软件手册","硬件手册","编程手册","安装调试手册",
          "选型手册","快速使用指南","产品说明书","其他"}
MANUAL_KW=["手册","说明书","指南"]

def http(url,data=None,referer="https://www.invt.com.cn/dowload-15",tries=4):
    h={"User-Agent":UA,"Referer":referer,"X-Requested-With":"XMLHttpRequest"}
    last=None
    for i in range(tries):
        try:
            if data is not None:
                h["Content-Type"]="application/x-www-form-urlencoded"
                req=urllib.request.Request(url,data=urllib.parse.urlencode(data).encode(),headers=h)
            else:
                req=urllib.request.Request(url,headers=h)
            return urllib.request.urlopen(req,timeout=45,context=SSLCTX).read()
        except Exception as e:
            last=e;time.sleep(2+i*2)
    raise last

def safe_url(u):
    p=urllib.parse.urlsplit(u)
    return urllib.parse.urlunsplit((p.scheme,p.netloc,urllib.parse.quote(p.path),p.query,p.fragment))

def pdf_pages(path):
    try:
        r=subprocess.run(["pdfinfo",path],capture_output=True,text=True,timeout=20)
        for line in r.stdout.splitlines():
            if line.startswith("Pages"):return int(line.split(":",1)[1].strip())
    except Exception:pass
    return 0

def fetch_list():
    # 一次拉全；若被 WAF 拦截（返回非 JSON）则重试
    for i in range(5):
        raw=http(BASE+"/home/download/productlist.html",
                 {"page":"1","limit":"3000","catId":"16","type":"1"})
        txt=raw.decode("utf-8-sig","ignore").strip()
        if txt.startswith("{"):
            return json.loads(txt)["Rows"]
        time.sleep(3)
    raise RuntimeError("列表接口持续被 WAF 拦截")

def main(limit=0):
    rows=fetch_list()
    # 筛选手册类 PDF
    pick=[]
    for r in rows:
        if (r.get("fileExt") or "").upper()!="PDF":continue
        cat=r.get("catName") or ""
        u=r.get("downloadUrl") or ""
        if not u or not u.lower().split("?")[0].endswith(".pdf"):continue
        title=r.get("downame") or ""
        if cat in KEEP_CAT or any(k in title for k in MANUAL_KW):
            # 排除明确的证书/图纸/方案/报告
            if any(k in cat for k in ["证书","2D","3D","方案","报告","单页"]):continue
            if any(k in title for k in ["UL证书","CE-","TUV","一致性证书","Mark Cert","Cert"]):continue
            pick.append(r)
    # 按 URL 去重
    seen=set();uniq=[]
    for r in pick:
        if r["downloadUrl"] in seen:continue
        seen.add(r["downloadUrl"]);uniq.append(r)
    print("列表共 %d，手册类PDF %d"%(len(rows),len(uniq)))
    if limit:uniq=uniq[:limit]

    # 读已有 manifest（幂等）
    manifest=[]
    if os.path.exists(MAN):
        try:manifest=json.load(open(MAN,encoding="utf-8"))
        except Exception:manifest=[]
    have={m.get("u") for m in manifest}
    new_n=skip_n=fail_n=0
    for idx,r in enumerate(uniq,1):
        u=r["downloadUrl"];title=r.get("downame","").strip()
        h=hashlib.md5(u.encode()).hexdigest()[:8]
        fn="invt_%s.pdf"%h;fp=os.path.join(OUT,fn)
        if u in have:
            # 已在持久化 manifest：直接复用，不依赖磁盘文件、不重复下载、不重新 pdfinfo
            skip_n+=1;continue
        try:
            data=http(safe_url(u),referer="https://www.invt.com.cn/",tries=3)
            if not data.startswith(b"%PDF") or len(data)<5000:
                raise RuntimeError("notpdf/%d"%len(data))
            tmp=fp+".tmp";open(tmp,"wb").write(data);os.replace(tmp,fp)
            pages=pdf_pages(fp)
            if pages<=0:raise RuntimeError("0pages")
            manifest.append({"t":title,"u":u,"fn":fn,"cat":r.get("catName"),
                "v":r.get("version") or "","d":(r.get("releaseTime") or "").replace(".","-"),
                "size":len(data),"pages":pages,"id":r.get("id")})
            have.add(u);new_n+=1
            if idx%10==0 or idx<=5:
                print("  [%d/%d] %s %d页 %s"%(idx,len(uniq),fn,pages,title[:34]))
        except Exception as e:
            fail_n+=1
            print("  失败 %s %s: %s"%(fn,title[:30],str(e)[:60]))
    # 去重写 manifest
    dd={}
    for m in manifest:
        dd[m["u"]]=m
    manifest=list(dd.values())
    json.dump(manifest,open(MAN,"w",encoding="utf-8"),ensure_ascii=False,indent=1)
    print("英威腾累计 %d（本次新增 %d，复用 %d，失败 %d）"%(
        len(manifest),new_n,skip_n,fail_n))
    return fail_n

if __name__=="__main__":
    lim=int(sys.argv[1]) if len(sys.argv)>1 else 0
    sys.exit(0 if main(lim)==0 else 1)
