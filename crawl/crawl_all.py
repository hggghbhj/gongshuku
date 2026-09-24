# -*- coding: utf-8 -*-
"""工书库·全网说明书自动采集主控（可无人值守、可重复运行）。
顺序执行各品牌采集器（幂等）-> 健康检查 -> 汇总增量报告 -> crawl_state.json。
用法:
  python3 crawl_all.py            # 跑全部品牌
  python3 crawl_all.py jintian    # 只跑指定品牌
每个品牌采集器约定：把 PDF 落到 pdfs/<brand>/，输出 <brand>_manifest.json。
"""
import subprocess,os,json,time,sys,datetime
HERE=os.path.dirname(os.path.abspath(__file__))
os.chdir(HERE)
# 品牌采集器注册表：品牌名 -> 脚本（顺序即执行顺序）
CRAWLERS=[
    ("coolmay","crawler_coolmay.py"),    # 直连静态站
    ("elitech","crawler_elitech.py"),    # 纯接口+PDF直链
    ("xinje","crawler_xinje.py"),        # 接口分页+CDN
    ("leisai","crawler_leisai.py"),      # 接口分页+直链
    ("sinee","crawler_sinee.py"),        # OSS+Referer
    ("oura","crawler_oura.py"),          # 直链+Referer
    ("hcfa","crawler_hcfa.py"),          # 翻页+request
    ("invt","crawler_invt.py"),          # 英威腾 纯接口(files域忽略SSL+Referer)
    ("jintian","crawl_jintian_pw.py"),   # WAF 无头浏览器
    # 新增品牌在此登记（普传/欧瑞/信捷...）
]
def ensure_receiver():
    import urllib.request
    try:
        urllib.request.urlopen("http://127.0.0.1:8899/health",timeout=3);return "running"
    except:pass
    # 未运行则后台拉起（脱离父进程，长期常驻）
    log=open("receiver.out","ab")
    subprocess.Popen(["python3","-u","crawl_receiver.py"],stdout=log,stderr=log,
                     start_new_session=True)
    import time
    for _ in range(8):
        time.sleep(1)
        try:
            urllib.request.urlopen("http://127.0.0.1:8899/health",timeout=2);return "started"
        except:pass
    return "FAILED"
def count_pdfs(brand):
    d=os.path.join("pdfs",brand)
    return len([f for f in os.listdir(d) if f.endswith(".pdf")]) if os.path.isdir(d) else 0
def main():
    only=sys.argv[1:]
    targets=[c for c in CRAWLERS if not only or c[0] in only]
    started=datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    recv=ensure_receiver()
    print("="*60)
    print("采集开始 %s  接收器:%s  品牌:%s"%(started,recv,[c[0] for c in targets]))
    print("="*60)
    before={b:count_pdfs(b) for b,_ in targets}
    results={}
    for brand,script in targets:
        if not os.path.exists(script):
            print("【%s】采集器缺失 %s，跳过"%(brand,script));results[brand]={"status":"missing"};continue
        t0=time.time()
        try:
            r=subprocess.run(["python3",script],capture_output=True,text=True,timeout=2400)
            tail=(r.stdout or "").strip().splitlines()[-3:]
            ok=r.returncode==0
            results[brand]={"status":"ok" if ok else "fail","rc":r.returncode,
                            "sec":round(time.time()-t0),"tail":tail,
                            "stderr":(r.stderr or "")[-300:]}
            print("【%s】%s %.0fs"%(brand,"成功" if ok else "失败(rc=%d)"%r.returncode,time.time()-t0))
            for l in tail:print("   ",l)
        except subprocess.TimeoutExpired:
            results[brand]={"status":"timeout"};print("【%s】超时"%brand)
    after={b:count_pdfs(b) for b,_ in targets}
    # 健康检查
    print("="*60);print("运行健康检查...")
    h=subprocess.run(["python3","healthcheck.py"],capture_output=True,text=True)  # 始终全库巡检
    print(h.stdout.strip())
    health=json.load(open("health_report.json",encoding="utf-8")) if os.path.exists("health_report.json") else {}
    # 状态
    state={"run_at":started,"receiver":recv,
           "pdf_counts":{b:{"before":before[b],"after":after[b],"new":after[b]-before[b]} for b,_ in targets},
           "health_summary":health.get("_summary",{}),
           "crawler_results":results}
    hist=[]
    if os.path.exists("crawl_state.json"):
        try:hist=json.load(open("crawl_state.json",encoding="utf-8")).get("history",[])
        except:pass
    hist.append(state)
    json.dump({"history":hist[-200:],"last":state},open("crawl_state.json","w",encoding="utf-8"),ensure_ascii=False,indent=1)
    print("="*60)
    print("新增:",{b:after[b]-before[b] for b,_ in targets})
    print("健康:",health.get("_summary",{}))
    print("状态已写 crawl_state.json")
if __name__=="__main__":main()
