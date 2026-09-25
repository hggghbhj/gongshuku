# -*- coding: utf-8 -*-
"""工书库·云端采集编排（GitHub Actions 专用）。
顺序跑各品牌采集器（manifest 驱动增量，只下载新发现的说明书）-> build_docs 生成 docs-3.js。
运行前后对比 manifest 记录数统计本次新增，写入 dist/data/stats.json 供网站前端展示。
"""
import subprocess,os,time,sys,json,glob
HERE=os.path.dirname(os.path.abspath(__file__));os.chdir(HERE)
STEPS=[
 ("顾美",["python3","crawler_coolmay.py"]),
 ("精创",["python3","crawler_elitech.py"]),
 ("信捷",["python3","crawler_xinje.py"]),
 ("雷赛",["python3","crawler_leisai.py"]),
 ("正弦",["python3","crawler_sinee.py"]),
 ("欧瑞",["python3","crawler_oura.py"]),
 ("禾川",["python3","crawler_hcfa.py"]),
 ("英威腾",["python3","crawler_invt.py"]),
 ("伟创",["python3","crawler_veichi.py"]),
 ("昆仑通态",["python3","crawler_mcgs.py"]),
 ("艾莫迅",["python3","crawler_amsamotion.py"]),
 ("森兰",["python3","crawler_senlan.py"]),
 ("易驱",["python3","crawler_easydrive.py"]),
 ("易能",["python3","crawler_enc.py"]),
 ("合信",["python3","crawler_cotion.py"]),
 ("工贝",["python3","crawler_gongbei.py"]),
 ("明纬",["python3","crawler_meanwell.py"]),
 ("山特",["python3","crawler_santak.py"]),
 ("四方电气",["python3","crawler_simphoenix.py"]),
 ("吉泰科",["python3","crawler_gtake.py"]),
 ("天正",["python3","crawler_tengen.py"]),
 ("合康新能",["python3","crawler_hiconics.py"]),
 ("伊玛电子",["python3","crawler_ema.py"]),
 ("邦纳",["python3","crawler_banner.py"]),
 ("三友",["python3","crawler_sanyou.py"]),
 ("宇电",["python3","crawler_yudian.py"]),
 ("Cincon",["python3","crawler_cincon.py"]),
 ("和利时",["python3","crawler_hollysys.py"]),
 ("宏发",["python3","crawler_hongfa.py"]),
 ("海为",["python3","crawler_haiwell.py"]),
 ("虹润",["python3","crawler_hongrun.py"]),
 ("上润",["python3","crawler_wideplus.py"]),
 ("安东",["python3","crawler_anthone.py"]),
 ("良信",["python3","crawler_lazzen.py"]),
 ("研控",["python3","crawler_yankong.py"]),
 ("汇辰",["python3","crawler_huceen.py"]),
 ("米格",["python3","crawler_mege.py"]),
 ("兰宝",["python3","crawler_lanbao.py"]),
 ("阿尔法",["python3","crawler_alpha.py"]),
 ("汇川",["python3","crawler_inovance.py"]),
 ("金田链接",["python3","crawl_jintian_pw.py","--links-only"]),
]
def count_manifests():
    """统计所有 manifest 的记录数（按品牌key）"""
    counts={}
    for fp in glob.glob("*_manifest.json"):
        key=fp.replace("_manifest.json","")
        try:
            d=json.load(open(fp,encoding="utf-8"))
            counts[key]=len(d) if isinstance(d,list) else 0
        except Exception:counts[key]=0
    # 普传 kv_powtran.json
    try:
        d=json.load(open("kv_powtran.json",encoding="utf-8"))
        counts["powtran"]=len(d) if isinstance(d,list) else 0
    except Exception:pass
    return counts
def main():
    only=sys.argv[1:]
    before=count_manifests()
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
    after=count_manifests()
    # 统计新增
    new_by_brand={}
    total_new=0
    for k in after:
        diff=after[k]-before.get(k,0)
        if diff>0:
            new_by_brand[k]=diff
            total_new+=diff
    total=sum(after.values())
    stats={
        "last_run":time.strftime("%Y-%m-%d %H:%M:%S",time.localtime()),
        "last_new":total_new,
        "new_by_brand":new_by_brand,
        "total":total,
        "brands":after,
        "cron":"每3小时自动采集（北京时间 8:17/11:17/14:17/17:17/20:17/23:17/2:17/5:17）",
        "steps":summary,
    }
    os.makedirs("../dist/data",exist_ok=True)
    json.dump(stats,open("../dist/data/stats.json","w",encoding="utf-8"),ensure_ascii=False,indent=1)
    json.dump({"steps":summary,"last_new":total_new,"total":total},open("cloud_crawl_state.json","w",encoding="utf-8"),ensure_ascii=False,indent=1)
    print("本次新增 %d 份，累计 %d 份。新增明细: %s"%(total_new,total,new_by_brand))
    print("云端采集编排完成:",summary)
if __name__=="__main__":main()
