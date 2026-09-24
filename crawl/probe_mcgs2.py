# -*- coding: utf-8 -*-
from playwright.sync_api import sync_playwright
from pw_util import chromium_path
import time
UA="Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/120 Safari/537.36"
with sync_playwright() as p:
    b=p.chromium.launch(headless=True,executable_path=chromium_path(),args=["--no-sandbox","--disable-dev-shm-usage"])
    ctx=b.new_context(user_agent=UA,accept_downloads=True)
    pg=ctx.new_page()
    reqs=[]
    pg.on("request",lambda r: reqs.append(r.url) if (".pdf" in r.url or "download" in r.url.lower() or "/api/" in r.url and "files" not in r.url) else None)
    pg.goto("https://www.mcgspro.com/downloads.html",wait_until="domcontentloaded",timeout=25000)
    time.sleep(4)
    # 找第一个PDF行的下载按钮
    btn=pg.evaluate("""()=>{
      const rows=[...document.querySelectorAll('tr,li,.row')];
      for(const r of rows){
        if(r.innerText.includes('.pdf')||r.innerText.includes('手册')){
          const btns=r.querySelectorAll('a,button');
          for(const x of btns){if(x.innerText.includes('下载')||x.onclick||x.getAttribute('href'))return {txt:x.innerText.trim(),href:x.getAttribute('href'),tag:x.tagName};}
        }
      }return null;
    }""")
    print("下载按钮:",btn)
    # 直接点
    try:
        pg.evaluate("""()=>{
          const rows=[...document.querySelectorAll('tr,li,.row')];
          for(const r of rows){if(r.innerText.includes('手册')){const a=r.querySelector('a,button');if(a){a.click();return;}}}
        }""")
        time.sleep(2)
    except Exception as e:print("点击异常",e)
    print("=== 相关请求 ===")
    for u in reqs[:10]:print("  ",u[:120])
    b.close()
