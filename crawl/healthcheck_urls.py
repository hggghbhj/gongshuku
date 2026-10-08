# -*- coding: utf-8 -*-
"""云端说明书URL健康检查 + 自动修复。
- 读取 docs-3.js 中所有PDF直链
- 发送HEAD/GET请求检测HTTP状态、Content-Type、Content-Length
- 异常链接写入 bad_links.json
- 对异常品牌自动重跑对应采集器修复
"""
import os,json,subprocess,time,sys,urllib.request,urllib.error,re,glob
HERE=os.path.dirname(os.path.abspath(__file__));os.chdir(HERE)

def load_docs():
    """从docs-3.js解析所有文档"""
    fp="docs-3.js"
    if not os.path.exists(fp):
        # 尝试从dist读取
        fp="../dist/data/docs-3.js"
    if not os.path.exists(fp):return []
    with open(fp,"r",encoding="utf-8") as f:
        txt=f.read()
    # 提取JSON数组
    m=re.search(r'\[.*\]',txt,re.DOTALL)
    if not m:return []
    try:return json.loads(m.group())
    except:return []

def check_url(url,timeout=15):
    """检测URL可访问性，返回(status, content_type, content_length)"""
    if not url or not url.startswith("http"):
        return "invalid",None,0
    headers={
        "User-Agent":"Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
        "Referer":"/".join(url.split("/")[:3])+"/",
    }
    # 先试HEAD
    try:
        req=urllib.request.Request(url,headers=headers,method="HEAD")
        r=urllib.request.urlopen(req,timeout=timeout)
        ct=r.headers.get("Content-Type","")
        cl=r.headers.get("Content-Length","0")
        return r.status,ct,int(cl) if cl.isdigit() else 0
    except urllib.error.HTTPError as e:
        # HEAD被拒，试GET Range
        try:
            headers["Range"]="bytes=0-1023"
            req=urllib.request.Request(url,headers=headers,method="GET")
            r=urllib.request.urlopen(req,timeout=timeout)
            ct=r.headers.get("Content-Type","")
            cl=r.headers.get("Content-Length","0") or r.headers.get("Content-Range","")
            return r.status,ct,int(cl) if str(cl).isdigit() else 1024
        except Exception as e2:
            return e.code if hasattr(e,'code') else "error",None,0
    except Exception as e:
        # HEAD失败，试GET
        try:
            req=urllib.request.Request(url,headers=headers,method="GET")
            r=urllib.request.urlopen(req,timeout=timeout)
            data=r.read(2048)  # 只读前2KB验证
            ct=r.headers.get("Content-Type","")
            cl=r.headers.get("Content-Length","0")
            return r.status,ct,int(cl) if cl.isdigit() else len(data)
        except urllib.error.HTTPError as e2:
            return e2.code,None,0
        except Exception as e3:
            return "error",None,0

def is_pdf_ok(status,ct,cl):
    """判断PDF是否正常"""
    if status!=200 and status!=206:return False
    if ct and "pdf" not in ct.lower() and "octet-stream" not in ct.lower() and "application" not in ct.lower():
        return False
    if cl and cl<2000:return False  # 太小可能是错误页
    return True

def find_crawler(brand):
    """根据品牌名找到对应采集器"""
    # 品牌名到采集器文件的映射
    mapping={
        "顾美":"crawler_coolmay.py","精创":"crawler_elitech.py","信捷":"crawler_xinje.py",
        "雷赛":"crawler_leisai.py","正弦":"crawler_sinee.py","欧瑞":"crawler_oura.py",
        "禾川":"crawler_hcfa.py","英威腾":"crawler_invt.py","伟创":"crawler_veichi.py",
        "昆仑通态":"crawler_mcgs.py","艾莫迅":"crawler_amsamotion.py","森兰":"crawler_senlan.py",
        "易驱":"crawler_easydrive.py","易能":"crawler_enc.py","合信":"crawler_cotion.py",
        "工贝":"crawler_gongbei.py","明纬":"crawler_meanwell.py","山特":"crawler_santak.py",
        "四方电气":"crawler_simphoenix.py","吉泰科":"crawler_gtake.py","天正":"crawler_tengen.py",
        "合康新能":"crawler_hiconics.py","伊玛电子":"crawler_ema.py","邦纳":"crawler_banner.py",
        "三友":"crawler_sanyou.py","宇电":"crawler_yudian.py","Cincon":"crawler_cincon.py",
        "和利时":"crawler_hollysys.py","宏发":"crawler_hongfa.py","海为":"crawler_haiwell.py",
        "虹润":"crawler_hongrun.py","上润":"crawler_wideplus.py","安东":"crawler_anthone.py",
        "良信":"crawler_lazzen.py","研控":"crawler_yankong.py","汇辰":"crawler_huceen.py",
        "米格":"crawler_mege.py","兰宝":"crawler_lanbao.py","阿尔法":"crawler_alpha.py",
        "西驰":"crawler_xichi.py","安邦信":"crawler_anbangxin.py","华中数控":"crawler_huazhong.py",
        "广州数控":"crawler_gskcnc.py","西安西普":"crawler_westpow.py","麦克传感器":"crawler_microsensor.py",
        "古瑞瓦特":"crawler_growatt.py","德力西变频器":"crawler_delixi.py","富凌电气":"crawler_fuling.py",
        "申乐电气":"crawler_shenler.py","汇邦科技":"crawler_huibang.py","开民电器":"crawler_kaimin.py",
        "协鑫集成":"crawler_gclsi.py","汇川":"crawler_inovance.py",
    }
    return mapping.get(brand)

def main():
    print("="*60)
    print("云端说明书URL健康检查")
    print("="*60)
    docs=load_docs()
    print(f"共加载 {len(docs)} 份文档")
    # 只检查有PDF直链的
    pdf_docs=[d for d in docs if d.get("pdf")]
    print(f"其中PDF直链 {len(pdf_docs)} 份")
    bad=[]
    bad_by_brand={}
    checked=0
    for i,d in enumerate(pdf_docs):
        url=d.get("pdf","")
        brand=d.get("b","未知")
        title=d.get("t","")[:40]
        status,ct,cl=check_url(url)
        checked+=1
        if not is_pdf_ok(status,ct,cl):
            reason=f"status={status},ct={ct},size={cl}"
            bad.append({"brand":brand,"title":title,"url":url,"reason":reason})
            bad_by_brand.setdefault(brand,[]).append(url)
            print(f"  [异常] {brand} | {title} | {reason}")
        if (i+1)%50==0:
            print(f"  已检查 {i+1}/{len(pdf_docs)}，异常 {len(bad)}")
        time.sleep(0.1)  # 避免请求过快
    print(f"\n检查完成：共 {checked} 份，异常 {len(bad)} 份")
    # 写入异常报告
    report={
        "check_time":time.strftime("%Y-%m-%d %H:%M:%S",time.localtime()),
        "total":checked,
        "bad_count":len(bad),
        "bad_by_brand":{k:len(v) for k,v in bad_by_brand.items()},
        "bad_links":bad,
    }
    with open("../dist/data/health_report.json","w",encoding="utf-8") as f:
        json.dump(report,f,ensure_ascii=False,indent=1)
    print(f"异常报告已写入 dist/data/health_report.json")
    # 自动修复：对异常品牌重跑采集器
    if bad_by_brand and "--no-fix" not in sys.argv:
        print("\n开始自动修复...")
        for brand,urls in bad_by_brand.items():
            crawler=find_crawler(brand)
            if not crawler:
                print(f"  [跳过] {brand}：无对应采集器")
                continue
            if not os.path.exists(crawler):
                print(f"  [跳过] {brand}：采集器 {crawler} 不存在")
                continue
            print(f"  [修复] {brand}：重跑 {crawler}（{len(urls)}个异常链接）")
            try:
                r=subprocess.run(["python3",crawler],capture_output=True,text=True,timeout=600)
                if r.returncode==0:
                    print(f"    成功")
                else:
                    print(f"    失败 rc={r.returncode}: {r.stderr[-200:]}")
            except subprocess.TimeoutExpired:
                print(f"    超时（10分钟）")
            except Exception as e:
                print(f"    错误: {e}")
        # 修复后重新生成docs-3.js
        print("\n重新生成 docs-3.js ...")
        r=subprocess.run(["python3","build_docs.py"],capture_output=True,text=True)
        if r.returncode==0:
            subprocess.run(["cp","docs-3.js","../dist/data/docs-3.js"])
            print("  完成")
        else:
            print(f"  失败: {r.stderr[-200:]}")
    print("\n健康检查+自动修复完成")

if __name__=="__main__":
    main()
