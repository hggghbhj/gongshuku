from playwright.sync_api import sync_playwright
from pw_util import chromium_path
import time
UA="Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/120 Safari/537.36"
with sync_playwright() as p:
    b=p.chromium.launch(headless=True,executable_path=chromium_path(),args=["--no-sandbox","--disable-dev-shm-usage"])
    pg=b.new_page(user_agent=UA)
    apis=[]
    pg.on("response",lambda r: apis.append(r.url) if (".pdf" in r.url.lower() or "download" in r.url.lower() or "api" in r.url.lower() or "ajax" in r.url.lower()) and "co-trust" in r.url.lower() and r.status<400 else None)
    pg.goto("https://www.co-trust.com/Download/",wait_until="domcontentloaded",timeout=25000)
    time.sleep(5)
    print("文本:",pg.evaluate("()=>document.body.innerText.slice(0,300)"))
    links=pg.evaluate("()=>[...document.querySelectorAll('a')].map(a=>({t:a.innerText.trim().slice(0,25),h:a.href})).filter(x=>x.t&&x.h&&('.pdf' in x.h.toLowerCase()||'Download' in x.h||'download' in x.h||'edit_file' in x.h)).slice(0,15)")
    print("=== 相关链接 ===")
    for l in links:print("  ",l["t"],"->",l["h"][:100])
    print("=== API/PDF响应 ===")
    for u in list(dict.fromkeys(apis))[:8]:print("  ",u[:130])
    b.close()
