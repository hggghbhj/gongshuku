from playwright.sync_api import sync_playwright
from pw_util import chromium_path
import time
UA="Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/120 Safari/537.36"
with sync_playwright() as p:
    b=p.chromium.launch(headless=True,executable_path=chromium_path(),args=["--no-sandbox","--disable-dev-shm-usage"])
    pg=b.new_page(user_agent=UA)
    pg.goto("https://www.gongbei.com",wait_until="domcontentloaded",timeout=25000)
    time.sleep(4)
    links=pg.evaluate("()=>[...document.querySelectorAll('a')].map(a=>({t:a.innerText.trim().slice(0,20),h:a.href})).filter(x=>x.t&&x.h&&x.h!=='#'&&!x.h.includes('javascript')).slice(0,20)")
    print("=== 工贝链接 ===")
    for l in links:print("  ",l["t"],"->",l["h"][:80])
    b.close()
