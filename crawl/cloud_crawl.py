# -*- coding: utf-8 -*-
"""工书库·云端采集编排（GitHub Actions 专用）。
顺序跑各品牌采集器（manifest 驱动增量，只下载新发现的说明书）-> build_docs 生成 docs-3.js。

不做全量 PDF 健康检查：云端不保留完整 PDF 副本（pdfs 为临时目录），
网站在线健康由 Cloudflare 的 /api/health 访问驱动自检负责，两条线互不干扰。
可重复运行、幂等。
用法: python3 cloud_crawl.py            # 全部
      python3 cloud_crawl.py 精创 雷赛   # 只跑指定（中文名）
"""
import subprocess,os,time,sys,json
HERE=os.path.dirname(os.path.abspath(__file__));os.chdir(HERE)
# (显示名, 命令)；纯接口品牌快，playwright 品牌需 chromium
STEPS=[
 ("顾美",["python3","crawler_coolmay.py"]),
 ("精创",["python3","crawler_elitech.py"]),
 ("信捷",["python3","crawler_xinje.py"]),
 ("雷赛",["python3","crawler_leisai.py"]),
 ("正弦",["python3","crawler_sinee.py"]),
 ("欧瑞",["python3","crawler_oura.py"]),
 ("禾川",["python3","crawler_hcfa.py"]),
 ("英威腾",["python3","crawler_invt.py"]),
 ("金田链接",["python3","crawl_jintian_pw.py","--links-only"]),
]
def main():
    only=sys.argv[1:]
    summary={}
    for name,cmd in STEPS:
        if only and name not in only:continue
        t0=time.time()
        try:
            r=subprocess.run(cmd,capture_output=True,text=True,timeout=900)
            ok=r.returncode==0
            summary[name]="ok" if ok else "fail(rc=%d)"%r.returncode
            tail=(r.stdout or "").strip().splitlines()[-2:]
            print("【%s】%s %.0fs"%(name,"成功" if ok else "失败",time.time()-t0))
            for l in tail:print("   ",l)
            if not ok:print("   stderr:",(r.stderr or "")[-300:])
        except subprocess.TimeoutExpired:
            summary[name]="timeout";print("【%s】超时（下次重试）"%name)
    print("="*50);print("生成 docs-3.js ...")
    r=subprocess.run(["python3","build_docs.py"],capture_output=True,text=True)
    print(r.stdout.strip())
    if r.returncode!=0:
        print(r.stderr);sys.exit(1)
    json.dump({"steps":summary},open("cloud_crawl_state.json","w",encoding="utf-8"),ensure_ascii=False,indent=1)
    print("云端采集编排完成:",summary)
if __name__=="__main__":main()
