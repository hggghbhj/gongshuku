from playwright.sync_api import sync_playwright
from pw_util import chromium_path
import time
UA="Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/120 Safari/537.36"
with sync_playwright() as p:
    b=p.chromium.launch(headless=True,executable_path=chromium_path(),args=["--no-sandbox","--disable-dev-shm-usage"])
    pg=b.new_page(user_agent=UA)
    apis=[]
    pg.on("response",lambda r: apis.append((r.status,r.url)) if any(k in r.url.lower() for k in ["api","portal","search","list","query","doc","file","download","product"]) and "inovance" in r.url.lower() and r.status<400 else None)
    pg.goto("https://www.inovance.com/portal/allResult?key=MD800",wait_until="domcontentloaded",timeout=30000)
    time.sleep(6)
    print("标题:",pg.evaluate("()=>document.title"))
    print("登录墙:",pg.evaluate("()=>/请登录|登录后|需要登录/.test(document.body.innerText)"))
    print("=== API响应 ===")
    seen=set()
    for s,u in apis:
        if u not in seen and '.js' not in u and '.css' not in u and 'static' not in u and 'images' not in u:
            seen.add(u);print("  ",s,u[:140])
    b.close()
