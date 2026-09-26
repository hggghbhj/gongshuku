#!/usr/bin/env python3
"""施耐德 Schneider 采集器：playwright过WAF + page.goto访问download-api + request context下载PDF。
分类：安装和用户指南(120246088490)、产品参数表(120246065965)、目录和宣传册(120245911031)。
幂等可重复运行，已下载且健康的文件跳过。
"""
import json,os,time,subprocess,re,hashlib,sys
from playwright.sync_api import sync_playwright

BRAND="schneider"
NAME="施耐德"
BASE="https://www.se.com/cn/zh/download/"
API_DOMAIN="https://www.schneider-electric.cn"
CATEGORIES={
    "120246088490":"安装和用户指南",
    "120246065965":"产品参数表",
    "120245911031":"目录和宣传册",
}
OUTDIR=f"pdfs/{BRAND}"
MANIFEST=f"{BRAND}_manifest.json"
MAX_PAGES=30  # 每页40条，最多1200条/分类
os.makedirs(OUTDIR,exist_ok=True)

def load_manifest():
    if os.path.exists(MANIFEST):
        try: return json.load(open(MANIFEST,encoding="utf-8"))
        except: return []
    return []

def save_manifest(m):
    json.dump(m,open(MANIFEST,"w",encoding="utf-8"),ensure_ascii=False,indent=1)

def pdf_ok(path):
    try:
        r=subprocess.run(["pdfinfo",path],capture_output=True,text=True,timeout=15)
        return r.returncode==0 and "Pages:" in r.stdout
    except: return False

def get_pages(path):
    try:
        r=subprocess.run(["pdfinfo",path],capture_output=True,text=True,timeout=15)
        for line in r.stdout.split("\n"):
            if line.startswith("Pages:"):
                return int(line.split(":")[1].strip())
    except: pass
    return 0

def run():
    manifest=load_manifest()
    existing={r["url"] for r in manifest}
    print(f"施耐德已有 {len(manifest)} 份，开始采集...")
    new_count=0
    fail_count=0
    with sync_playwright() as p:
        browser=p.chromium.launch(executable_path="/usr/local/bin/chromium",
            args=["--no-sandbox","--disable-dev-shm-usage"])
        context=browser.new_context(user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",locale="zh-CN")
        page=context.new_page()
        print("  打开下载页获取cookie...")
        page.goto(BASE,timeout=45000,wait_until="domcontentloaded")
        time.sleep(15)
        for cat_id,cat_name in CATEGORIES.items():
            print(f"  分类: {cat_name} ({cat_id})")
            for page_num in range(1,MAX_PAGES+1):
                api_url=f"{API_DOMAIN}/zh/download/download-api/getDocuments/?appSource=DDC_SE&categoryId={cat_id}&page={page_num}&pageSize=40"
                try:
                    page.goto(api_url,timeout=30000,wait_until="domcontentloaded")
                    time.sleep(2)
                    content=page.content()
                    json_str=re.sub(r"<[^>]+>","",content).strip()
                    # 处理HTML实体
                    json_str=json_str.replace("&amp;","&").replace("&lt;","<").replace("&gt;",">").replace("&quot;",'"')
                    result=json.loads(json_str)
                except Exception as e:
                    print(f"    第{page_num}页API失败: {str(e)[:60]}")
                    time.sleep(5)
                    break
                docs=result.get("documents",[])
                if not docs:
                    print(f"    第{page_num}页无数据，结束分类")
                    break
                print(f"    第{page_num}页: {len(docs)}条")
                for doc in docs:
                    files=doc.get("documentFiles",[])
                    if not files: continue
                    f=files[0]
                    if f.get("extension")!="pdf": continue
                    url=f.get("downloadFileURL","")
                    if not url or url in existing: continue
                    title=doc.get("title","")[:80]
                    ref=doc.get("reference","")
                    size=f.get("size","")
                    # 跳过大于50MB的文件
                    try:
                        size_mb=float(size.replace(" MB","").replace(" KB","").replace(" GB",""))
                        if "GB" in size or ("MB" in size and size_mb>50):
                            continue
                    except: pass
                    try:
                        resp=context.request.get(url,timeout=60000)
                        body=resp.body()
                        if body[:4]!=b"%PDF":
                            fail_count+=1
                            continue
                        fname=f"{ref}_{hashlib.md5(url.encode()).hexdigest()[:8]}.pdf"
                        fpath=os.path.join(OUTDIR,fname)
                        with open(fpath,"wb") as fp: fp.write(body)
                        pages=get_pages(fpath)
                        if pages==0:
                            os.remove(fpath)
                            fail_count+=1
                            continue
                        manifest.append({"name":title,"url":url,"brand":NAME,"type":cat_name,"reference":ref,"size":size,"pages":pages})
                        existing.add(url)
                        new_count+=1
                        if new_count%20==0:
                            save_manifest(manifest)
                            print(f"    已新增 {new_count} 份")
                    except Exception as e:
                        fail_count+=1
                    time.sleep(0.3)
                time.sleep(1)
        browser.close()
    save_manifest(manifest)
    print(f"施耐德采集完成: 新增{new_count}, 失败{fail_count}, 累计{len(manifest)}")

if __name__=="__main__":
    run()
