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
    "S7-1200":1224,"S7-1500":7863,"S7-200 SMART":7759,"S7-300":40,"S7-400":111,
    "S7-200":2,"G系列变频器":7895,"V系列变频器":7896,"S系列变频器":1124,
    "MICROMASTER":1064,"ET200":171,"工业以太网":409,"PROFINET":489,
    "PROFIBUS":584,"LOGO!":1186,"SIMATIC Panel":357,"SIMATIC WinCC":366,
    "工业自动化软件":352,"SIMOTION":884,"SINUMERIK":1203,"交流电机":977,
    "DCS PCS7":818,"监视控制设备":1192,"接触器组件":866,
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
    try:
        req=urllib.request.Request(url,headers=HEADERS)
        with urllib.request.urlopen(req,timeout=180,context=ctx) as r:
            data=r.read()
            if len(data)<1000 or b"%PDF" not in data[:2048]:
                return None
            with open(local_path,"wb") as f:
                f.write(data)
            return str(local_path)
    except:
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
        time.sleep(0.2)
        if (i+1)%20==0:
            MANIFEST.write_text(json.dumps(manifest,ensure_ascii=False,indent=2),encoding="utf-8")
    
    MANIFEST.write_text(json.dumps(manifest,ensure_ascii=False,indent=2),encoding="utf-8")
    print(f"\n=== 完成: 成功{success}, 失败{fail}, 跳过{skip}, 总计{len(manifest)} ===")

if __name__=="__main__":
    main()
