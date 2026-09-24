from playwright.sync_api import sync_playwright
from pw_util import chromium_path
import time
UA="Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/120 Safari/537.36"
with sync_playwright() as p:
    b=p.chromium.launch(headless=True,executable_path=chromium_path(),args=["--no-sandbox","--disable-dev-shm-usage"])
    pg=b.new_page(user_agent=UA)
    dls=[]
    pg.on("response",lambda r: dls.append(r.url) if (".pdf" in r.url.lower() or "download" in r.url.lower()) and r.status<400 else None)
    pg.goto("https://www.samkoon.com.cn/xiankongDownDetail.html?id=34",wait_until="domcontentloaded",timeout=25000)
    time.sleep(4)
    print("标题:",pg.evaluate("()=>document.title"))
    print("文本:",pg.evaluate("()=>document.body.innerText.slice(0,200)"))
    links=pg.evaluate("()=>[...document.querySelectorAll('a')].map(a=>a.href).filter(h=>h&&('.pdf' in h.toLowerCase()||'download' in h.toLowerCase()||'upload' in h.toLowerCase())).slice(0,5)")
    print("PDF链接:",links)
    print("响应:",dls[:3])
    b.close()
