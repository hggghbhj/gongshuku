# -*- coding: utf-8 -*-
"""西门子说明书采集器 - 高效版
直接从分类页提取文档，直接下载，不访问详情页
"""
import os,json,time,re,urllib.request,ssl,subprocess
from pathlib import Path

BASE=Path(__file__).parent
PDF_DIR=BASE/"pdfs"/"siemens"
MANIFEST=BASE/"siemens_manifest.json"
PDF_DIR.mkdir(parents=True,exist_ok=True)

PRODUCT_TYPES={
    # PLC和组件
    "S7-1500":7863,"S7-1200":1224,"S7-200 SMART":7759,"S7-200":2,"S7-300":40,"S7-400":111,
    "LOGO!":1186,"ET200":171,"S5":314,"工业自动化软件":352,"工业电源":7929,"WinAC":1187,"TDC":277,
    # HMI/面板
    "精智Comfort屏":7932,"精简Basic屏":7933,"精彩Smart屏":7934,"其它屏及组态软件":7935,
    "WinCC":366,"Portal WinCC":7930,"WinCC Unified":7931,"WinCC OA":1275,
    # 工业通讯
    "编程器/IPC":399,"工业以太网":409,"PROFINET":489,"PROFIBUS":584,"ASI":739,
    "工业无线通信":768,"工业远程通信":785,"物联网IOT":7975,
    # DCS/过程自动化
    "DCS PCS7":818,"过程安全系统":833,"SIMIT":7936,"PCS neo":7976,"工业安全":7879,
    # 仪表
    "压力测量":835,"流量测量":836,"物位测量":840,"温度测量":845,"阀门定位器":846,
    "过程调节器":847,"称重组件":848,"连续称重":851,"气体分析仪":855,"过程气相色谱仪":856,
    "记录仪":857,"过程保护仪表":858,"RFID":862,"机器视觉":863,"SIMATIC MV":7920,"工业信息安全":7885,
    # 变频器/驱动
    "SINAMICS S120":7953,"S220":7986,"S150":7954,"S210伺服":7955,"S200伺服":7956,
    "S120M伺服":7987,"S110伺服":7952,"G200":7993,"G120/G120C":7941,"G120X":7988,
    "G120XA":7989,"G220":7977,"G130":7944,"G150":7945,"G115D":7990,"G120D":7943,
    "G120P":7942,"G110":7939,"G110D":7940,"V20":7947,"V90伺服":7951,"V10":7946,
    "V50":7948,"V60伺服":7949,"V80伺服":7950,
    "SIMOTION":884,"分布式驱动变频器":1045,"ET200变频器":7957,"MICROMASTER":1064,
    "SIMODRIVE":1092,"MASTERDRIVES":1105,"直流调速器":1137,
    "交流电机":977,"减速电机":7922,"直流电机":1039,"驱动工程软件":1143,"驱动数字化":7991,
    # 数控系统
    "SINUMERIK 801":1195,"802C":1196,"802S":1197,"802D sl":1198,"808D":7870,
    "808D advanced":7881,"810D":1199,"828D":1225,"840Di":1200,"840D":1201,
    "电主轴":1202,"SINUMERIK全系列":1203,"SinuTrain":1204,"CNC":7918,"SINUMERIK ONE":7926,
    # 大型变频器
    "GH180":1129,"GM150":1130,"SM150":1131,"GL150":1132,"SL150":7893,
    "弗兰德减速机":1205,"弗兰德联轴器":1209,
    # 低压电器
    "软起动器":7937,"接触器组件":866,"智能马达保护器":870,"电机起动器":1191,
    "监视控制设备":1192,"行程开关":1240,"指令信号装置":880,"空气断路器":7980,
    "塑壳断路器":7981,"小型断路器":7982,"隔离开关":7983,"测量装置":7984,"低压数字化":7992,
    "工业服务":7974,"数字化":7925,"船舶应用":7882,
}
DOC_TYPES={"手册":1,"样本":2,"操作指南":7}

HEADERS={
    "User-Agent":"Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept":"text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language":"zh-CN,zh;q=0.9,en;q=0.8",
}
ctx=ssl.create_default_context()
ctx.check_hostname=False
ctx.verify_mode=ssl.CERT_NONE

def fetch(url,timeout=30):
    req=urllib.request.Request(url,headers=HEADERS)
    try:
        with urllib.request.urlopen(req,timeout=timeout,context=ctx) as r:
            return r.read()
    except:
        return None

def get_docs(product_id,doc_type_id):
    url=f"https://www.ad.siemens.com.cn/download/filter?productTypeId={product_id}&docTypeId={doc_type_id}"
    data=fetch(url)
    if not data: return []
    html=data.decode("utf-8",errors="ignore")
    docs={}
    # 提取文档ID和标题
    for m in re.finditer(r'documentdetail_(\d+)\.html[^>]*>([^<]{3,100})<',html):
        doc_id=m.group(1)
        title=m.group(2).strip()
        if doc_id not in docs:
            docs[doc_id]=title
    # 也提取只有ID的
    for m in re.finditer(r'documentdetail_(\d+)\.html',html):
        doc_id=m.group(1)
        if doc_id not in docs:
            docs[doc_id]=""
    return [{"id":k,"title":v} for k,v in docs.items()]

def download_pdf(doc_id,title=""):
    safe_title=re.sub(r'[\\/:*?"<>|]','_',title or doc_id)[:80]
    local_path=PDF_DIR/f"{safe_title}_{doc_id}.pdf"
    if local_path.exists() and local_path.stat().st_size>1000:
        return str(local_path)
    url=f"https://www.ad.siemens.com.cn/download/html/Download?downloadId={doc_id}&loginID=&srno=&sendtime=&ftype=cn"
    # 最多重试3次
    for attempt in range(3):
        try:
            req=urllib.request.Request(url,headers=HEADERS)
            with urllib.request.urlopen(req,timeout=180,context=ctx) as r:
                data=r.read()
                if len(data)<1000 or b"%PDF" not in data[:2048]:
                    return None
                with open(local_path,"wb") as f:
                    f.write(data)
                time.sleep(0.5)  # 下载后延迟0.5秒，避免限流
                return str(local_path)
        except Exception as e:
            if attempt<2:
                time.sleep(2*(attempt+1))  # 重试前等待2秒、4秒
            else:
                return None
    return None

def get_pdf_pages(path):
    try:
        r=subprocess.run(["pdfinfo",path],capture_output=True,text=True,timeout=15)
        for line in r.stdout.split("\n"):
            if line.startswith("Pages:"):
                return int(line.split(":")[1].strip())
    except: pass
    return 0

def main():
    print("=== 西门子说明书采集（高效版）===")
    manifest=[]
    if MANIFEST.exists():
        try: manifest=json.loads(MANIFEST.read_text(encoding="utf-8"))
        except: manifest=[]
    existing_ids={r.get("download_id") for r in manifest}
    print(f"已有 {len(manifest)} 条记录")
    
    # 收集所有文档
    all_docs={}
    for pname,pid in PRODUCT_TYPES.items():
        for dtype,did in DOC_TYPES.items():
            docs=get_docs(pid,did)
            new_count=0
            for d in docs:
                if d["id"] not in all_docs:
                    all_docs[d["id"]]={"id":d["id"],"title":d.get("title",""),"product":pname,"doc_type":dtype}
                    new_count+=1
            if docs:
                print(f"  {pname} - {dtype}: {len(docs)}个, 新增{new_count}")
            time.sleep(0.2)
    print(f"\n共收集 {len(all_docs)} 个唯一文档")
    
    # 直接下载
    success=fail=skip=0
    for i,(doc_id,info) in enumerate(all_docs.items()):
        if doc_id in existing_ids:
            skip+=1; continue
        title=info["title"] or f"西门子{info['product']}{info['doc_type']}"
        path=download_pdf(doc_id,title)
        if path:
            pages=get_pdf_pages(path)
            size=os.path.getsize(path)
            manifest.append({
                "name":title,"url":f"https://www.ad.siemens.com.cn/download/html/Download?downloadId={doc_id}&loginID=&srno=&sendtime=&ftype=cn",
                "pdf":f"pdfs/siemens/{os.path.basename(path)}","size":size,"pages":pages,
                "type":info["doc_type"],"product":info["product"],"download_id":doc_id,"brand":"siemens",
            })
            success+=1
            print(f"  [{i+1}/{len(all_docs)}] OK: {title[:45]} ({pages}页, {size//1024}KB)")
        else:
            fail+=1
            print(f"  [{i+1}/{len(all_docs)}] FAIL: {title[:45]}")
        time.sleep(1.0)  # 下载后延迟1秒，避免限流
        if (i+1)%20==0:
            MANIFEST.write_text(json.dumps(manifest,ensure_ascii=False,indent=2),encoding="utf-8")
    
    MANIFEST.write_text(json.dumps(manifest,ensure_ascii=False,indent=2),encoding="utf-8")
    print(f"\n=== 完成: 成功{success}, 失败{fail}, 跳过{skip}, 总计{len(manifest)} ===")

if __name__=="__main__":
    main()
