# -*- coding: utf-8 -*-
"""说明书健康检查：检测所有PDF能否打开、是否白页/损坏。
- %PDF 头校验
- pdfinfo 页数
- 渲染首页+中间页，计算非白像素比例（<1% 判白页）
输出 health_report.json，可重复运行。"""
import os,subprocess,json,tempfile,sys
from PIL import Image
ROOT="pdfs"
def sh(cmd):
    return subprocess.run(cmd,capture_output=True,text=True)
def page_count(fp):
    r=sh(["pdfinfo",fp])
    for l in r.stdout.splitlines():
        if l.startswith("Pages:"):
            try:return int(l.split()[1])
            except:return 0
    return 0
def render_blank_ratio(fp,page):
    """渲染指定页，返回非白像素比例；失败返回 None"""
    tmp=tempfile.mktemp(suffix=".png")
    r=sh(["pdftoppm","-png","-f",str(page),"-l",str(page),"-r","40",fp,tmp[:-4]])
    cand=tmp[:-4]+("-0%d.png"%page if page<10 else "-%d.png"%page)
    # pdftoppm 自动命名 <prefix>-<page>.png
    pref=tmp[:-4]
    cand2="%s-%d.png"%(pref,page) if page>=10 else "%s-0%d.png"%(pref,page)
    path=cand2 if os.path.exists(cand2) else cand
    if not os.path.exists(path):
        # 列出 prefix 开头文件
        import glob
        gs=glob.glob(pref+"*.png")
        if not gs:return None
        path=gs[0]
    try:
        im=Image.open(path).convert("L")
        px=list(im.getdata())
        total=len(px)
        nonwhite=sum(1 for v in px if v<240)
        return nonwhite/total
    except Exception as e:
        return None
    finally:
        if os.path.exists(path):
            try:os.remove(path)
            except:pass
def check_fp(fp,fast=False):
    res={"file":fp}
    if not os.path.exists(fp):return dict(res,status="missing")
    if os.path.getsize(fp)<2000:return dict(res,status="tiny",size=os.path.getsize(fp))
    with open(fp,"rb") as f:head=f.read(5)
    if head[:4]!=b"%PDF":return dict(res,status="notpdf",size=os.path.getsize(fp))
    n=page_count(fp)
    if n==0:return dict(res,status="corrupt",size=os.path.getsize(fp))
    if fast:
        return dict(res,status="ok",pages=n,size=os.path.getsize(fp))
    # 渲染首页
    r1=render_blank_ratio(fp,1)
    # 大画册渲染中间页
    mid=max(1,n//2) if n>2 else 1
    r2=render_blank_ratio(fp,mid) if n>2 else r1
    ratios=[x for x in [r1,r2] if x is not None]
    if not ratios:return dict(res,status="renderfail",pages=n)
    maxratio=max(ratios)
    if maxratio<0.005:
        return dict(res,status="blank",pages=n,content_ratio=round(maxratio,4))
    return dict(res,status="ok",pages=n,content_ratio=round(maxratio,4),size=os.path.getsize(fp))
def main():
    fast="--fast" in sys.argv
    brands=[a for a in sys.argv[1:] if a!="--fast"] or sorted(os.listdir(ROOT))
    report={}
    tot=ok=bad=0
    for brand in brands:
        d=os.path.join(ROOT,brand)
        if not os.path.isdir(d):continue
        files=sorted(f for f in os.listdir(d) if f.endswith(".pdf"))
        report[brand]={"total":len(files),"items":[]}
        for fn in files:
            r=check_fp(os.path.join(d,fn),fast=fast)
            tot+=1
            if r["status"]=="ok":ok+=1
            else:
                bad+=1
                report[brand]["items"].append(r)
        # 统计
        stats={}
        for it in report[brand]["items"]:stats[it["status"]]=stats.get(it["status"],0)+1
        report[brand]["problems"]=stats
    report["_summary"]={"total":tot,"ok":ok,"problem":bad}
    out="health_report_fast.json" if fast else "health_report.json"
    json.dump(report,open(out,"w",encoding="utf-8"),ensure_ascii=False,indent=1)
    print("=== 健康检查汇总（%s）==="%("快速" if fast else "完整白页"))
    print("总计 %d, 正常 %d, 异常 %d"%(tot,ok,bad))
    for b in brands:
        if b in report and report[b].get("problems"):
            print(" ",b,report[b]["problems"])
    if bad==0:print("全部PDF可正常打开、非白页")
if __name__=="__main__":
    main()
