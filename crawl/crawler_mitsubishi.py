# -*- coding: utf-8 -*-
"""三菱电机说明书采集器
用playwright访问下载中心分类页，提取PDF直链，用urllib下载
"""
import os,json,time,re,urllib.request,ssl,subprocess
from pathlib import Path
from playwright.sync_api import sync_playwright

BASE=Path(__file__).parent
PDF_DIR=BASE/"pdfs"/"mitsubishi"
MANIFEST=BASE/"mitsubishi_manifest.json"
PDF_DIR.mkdir(parents=True,exist_ok=True)

# 55个产品分类
CATEGORIES={
    "MELSEC iQ-R系列":"/plcr","MELSEC iQ-F系列":"/plcf","MELSEC-Q系列":"/plcq",
    "MELSEC-L系列":"/plcl","MELSEC-F系列":"/plc_fx","MELSEC-A系列":"/plca",
    "MELSEC-QS/WS系列":"/plcqsws","可编程控制器MELSEC":"/mxc",
    "人机界面GOT":"/got","交流伺服MELSERVO":"/servo","变频器FR-FREQROL":"/inv",
    "工业机器人MELFA":"/robot","运动控制器":"/ssc","简单应用控制器":"/sac",
    "网络相关产品":"/plcnet","FA传感器MELSENSOR":"/sensor","传感器解决方案":"/iqss",
    "CNC数控系统":"/cnc","低压断路器":"/lvcb","接触器和马达启动器":"/lvsw",
    "减速电机":"/gear","电能管理测量仪":"/pmd","保护继电器":"/pror",
    "过程自动化":"/process","安全解决方案":"/safety","节能支持设备":"/ems",
    "工业计算机MELIPC":"/melipc","嵌入式系统":"/ccpu","e-F@ctory":"/efactory",
    "工程软件":"/plceng","GX Works3":"/gx_works","GX Works2":"/gx_works2",
    "MX Component":"/plceng","RT ToolBox3":"/robot","FR Configurator2":"/inv",
    "3D模拟器":"/3dsim","SCADA软件":"/scada","教育教材":"/school_text",
    "其他":"/renewals","服务":"/support",
}

HEADERS={
    "User-Agent":"Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
    "Referer":"https://www.mitsubishielectric.com/",
}
ctx=ssl.create_default_context()
ctx.check_hostname=False
ctx.verify_mode=ssl.CERT_NONE

def download_pdf(url,filename):
    local_path=PDF_DIR/filename
    if local_path.exists() and local_path.stat().st_size>1000:
        return str(local_path)
    if url.startswith("/"):
        url="https://dl.mitsubishielectric.com"+url
    try:
        req=urllib.request.Request(url,headers=HEADERS)
        with urllib.request.urlopen(req,timeout=120,context=ctx) as r:
            data=r.read()
            if len(data)<1000 or b"%PDF" not in data[:2048]:
                return None
            with open(local_path,"wb") as f:
                f.write(data)
            time.sleep(0.3)
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
    print("=== 三菱电机说明书采集 ===")
    manifest=[]
    if MANIFEST.exists():
        try: manifest=json.loads(MANIFEST.read_text(encoding="utf-8"))
        except: manifest=[]
    existing_urls={r.get("url") for r in manifest}
    print(f"已有 {len(manifest)} 条记录")

    all_pdfs={}
    with sync_playwright() as p:
        browser=p.chromium.launch(executable_path="/usr/local/bin/chromium",
            args=["--no-sandbox","--disable-dev-shm-usage"])
        page=browser.new_page()

        for cat_name,kisyu in CATEGORIES.items():
            url=f"https://www.mitsubishielectric.com/fa/download/search.page?mode=catalog&kisyu={kisyu}"
            try:
                page.goto(url,timeout=30000)
                page.wait_for_timeout(2000)
                pdf_links=page.query_selector_all("a[href*='.pdf']")
                new_count=0
                for link in pdf_links:
                    href=link.get_attribute("href")
                    text=link.inner_text().strip()
                    if href and href not in all_pdfs:
                        all_pdfs[href]={"url":href,"title":text or href.split("/")[-1],"category":cat_name}
                        new_count+=1
                print(f"  {cat_name}: {len(pdf_links)}个PDF, 新增{new_count}")
            except Exception as e:
                print(f"  {cat_name}: 失败 - {e}")
            time.sleep(1)

        browser.close()

    print(f"\n共收集 {len(all_pdfs)} 个唯一PDF")

    success=fail=skip=0
    for i,(url,info) in enumerate(all_pdfs.items()):
        if url in existing_urls:
            skip+=1; continue
        filename=re.sub(r'[\\/:*?"<>|]','_',info["title"] or url.split("/")[-1])[:80]
        if not filename.endswith(".pdf"):
            filename+=".pdf"
        path=download_pdf(url,filename)
        if path:
            pages=get_pdf_pages(path)
            size=os.path.getsize(path)
            manifest.append({
                "name":info["title"],"url":url if url.startswith("http") else "https://dl.mitsubishielectric.com"+url,
                "pdf":f"pdfs/mitsubishi/{os.path.basename(path)}","size":size,"pages":pages,
                "category":info["category"],"brand":"mitsubishi",
            })
            success+=1
            print(f"  [{i+1}/{len(all_pdfs)}] OK: {info['title'][:40]} ({pages}页, {size//1024}KB)")
        else:
            fail+=1
            print(f"  [{i+1}/{len(all_pdfs)}] FAIL: {info['title'][:40]}")
        if (i+1)%20==0:
            MANIFEST.write_text(json.dumps(manifest,ensure_ascii=False,indent=2),encoding="utf-8")

    MANIFEST.write_text(json.dumps(manifest,ensure_ascii=False,indent=2),encoding="utf-8")
    print(f"\n=== 完成: 成功{success}, 失败{fail}, 跳过{skip}, 总计{len(manifest)} ===")

if __name__=="__main__":
    main()
