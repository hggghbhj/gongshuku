from playwright.sync_api import sync_playwright
from pw_util import chromium_path
import time
UA="Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/120 Safari/537.36"
with sync_playwright() as p:
    b=p.chromium.launch(headless=True,executable_path=chromium_path(),args=["--no-sandbox","--disable-dev-shm-usage"])
    pg=b.new_page(user_agent=UA,accept_downloads=True)
    dls=[]
    pg.on("download",lambda d:dls.append(d.url))
    pg.on("request",lambda r: dls.append(r.url) if "download" in r.url.lower() or ".ashx" in r.url.lower() or ".pdf" in r.url.lower() else None)
    pg.goto("https://downloadcenter.delta-china.com.cn",wait_until="domcontentloaded",timeout=30000)
    time.sleep(4)
    # 点第一个下载按钮
    pg.evaluate("""()=>{
      const btns=[...document.querySelectorAll('a,button,span')];
      const d=btns.find(e=>/下载|Download/.test(e.innerText)&&e.offsetParent!==null);
      if(d)d.click();
    }""")
    time.sleep(3)
    print("=== 下载相关请求 ===")
    for u in list(dict.fromkeys(dls))[:8]:print("  ",u[:140])
    b.close()
