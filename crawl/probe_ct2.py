from playwright.sync_api import sync_playwright
from pw_util import chromium_path
import time
UA="Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/120 Safari/537.36"
with sync_playwright() as p:
    b=p.chromium.launch(headless=True,executable_path=chromium_path(),args=["--no-sandbox","--disable-dev-shm-usage"])
    pg=b.new_page(user_agent=UA)
    apis=[]
    pg.on("response",lambda r: apis.append(r.url) if (".pdf" in r.url.lower() or "download" in r.url.lower() or "ajax" in r.url.lower() or "api" in r.url.lower()) and "co-trust" in r.url.lower() and r.status<400 else None)
    pg.goto("https://www.co-trust.com/Download/",wait_until="domcontentloaded",timeout=25000)
    time.sleep(4)
    pg.evaluate("window.scrollTo(0,document.body.scrollHeight)")
    time.sleep(2)
    # 找所有含"下载"或PDF的元素
    info=pg.evaluate("""()=>{
      const all=[...document.querySelectorAll('a,div,li,span')];
      const dl=all.filter(e=>/下载|Download|\.pdf/i.test(e.innerText||'')&&e.offsetParent!==null).slice(0,10);
      return dl.map(e=>({t:(e.innerText||'').trim().slice(0,40),tag:e.tagName,h:e.href||''}));
    }""")
    print("=== 下载元素 ===")
    for x in info:print("  ",x["tag"],x["t"][:35],x["h"][:80] if x["h"] else "")
    print("=== API/PDF响应 ===")
    for u in list(dict.fromkeys(apis))[:8]:print("  ",u[:130])
    b.close()
