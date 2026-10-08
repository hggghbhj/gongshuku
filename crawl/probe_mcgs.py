# -*- coding: utf-8 -*-
from playwright.sync_api import sync_playwright
from pw_util import chromium_path
import time
UA="Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/120 Safari/537.36"
with sync_playwright() as p:
    b=p.chromium.launch(headless=True,executable_path=chromium_path(),args=["--no-sandbox","--disable-dev-shm-usage"])
    pg=b.new_page(user_agent=UA)
    api=[]
    pg.on("request",lambda r: api.append((r.method,r.url)) if any(k in r.url.lower() for k in ["list","down","api","page","query","getfile","search"]) and "mcgs" in r.url.lower() else None)
    pg.goto("https://www.mcgspro.com/downloads.html",wait_until="domcontentloaded",timeout=25000)
    time.sleep(4)
    # 表格行
    info=pg.evaluate("""()=>{
      const rows=[...document.querySelectorAll('table tr,.el-table__row,li')];
      const out=[];
      document.querySelectorAll('a').forEach(a=>{
        if(a.href&&(a.href.endsWith('.pdf')||a.href.endsWith('.zip')||a.href.endsWith('.doc')||a.href.endsWith('.docx'))){
          out.push({t:(a.innerText||'').trim().slice(0,30),u:a.href});
        }
      });
      return {fileLinks:out.slice(0,10), totalA:document.querySelectorAll('a').length};
    }""")
    print("=== 文件链接 ===")
    for x in info["fileLinks"]:print("  ",x)
    print("总a标签:",info["totalA"])
    print("=== 列表接口 ===")
    seen=set()
    for m,u in api:
        if u not in seen:seen.add(u);print("  ",m,u[:110])
    # 表格文本样例
    tbl=pg.evaluate("()=>{const t=document.querySelector('table');return t?t.innerText.slice(0,300):'no table';}")
    print("=== 表格样例 ===");print(tbl)
    b.close()
