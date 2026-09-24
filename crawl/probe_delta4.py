from playwright.sync_api import sync_playwright
from pw_util import chromium_path
import time
UA="Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/120 Safari/537.36"
with sync_playwright() as p:
    b=p.chromium.launch(headless=True,executable_path=chromium_path(),args=["--no-sandbox","--disable-dev-shm-usage"])
    ctx=b.new_context(user_agent=UA,accept_downloads=True)
    pg=ctx.new_page()
    dls=[]
    pg.on("download",lambda d:dls.append(d.url))
    pg.on("response",lambda r: dls.append(r.url) if (".pdf" in r.url.lower() or "download" in r.url.lower()) and r.status<400 else None)
    try:
        pg.goto("https://downloadcenter.delta-china.com.cn/downloadCenterCounter.aspx?DID=41224&DocPath=1&hl=zh-cn",wait_until="domcontentloaded",timeout=25000)
        time.sleep(5)
    except Exception as e:print("导航:",str(e)[:50])
    print("下载URL:",dls[:3])
    print("页面文本:",pg.evaluate("()=>document.body.innerText.slice(0,150)"))
    b.close()
