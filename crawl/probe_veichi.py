# -*- coding: utf-8 -*-
from playwright.sync_api import sync_playwright
from pw_util import chromium_path
import time,json
UA="Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/120 Safari/537.36"
api_calls=[]
with sync_playwright() as p:
    b=p.chromium.launch(headless=True,executable_path=chromium_path(),args=["--no-sandbox","--disable-dev-shm-usage"])
    ctx=b.new_context(user_agent=UA)
    pg=ctx.new_page()
    def on_req(r):
        u=r.url
        if any(k in u for k in ["list","down","api","search","getfile","upload","query","data"]) and "veichi" in u:
            api_calls.append((r.method,u))
    pg.on("request",on_req)
    pg.goto("https://www.veichi.cn/service/datadownload",wait_until="domcontentloaded",timeout=30000)
    # 等WAF挑战自动通过
    for i in range(15):
        time.sleep(2)
        try:
            pdfs=pg.eval_on_selector_all("a[href*='.pdf']","els=>els.map(a=>a.href)")
            if pdfs:
                print("WAF已过，PDF链接数:",len(pdfs));break
        except:pass
    print("=== 页面里的PDF直链 ===")
    for u in pdfs[:8]:print(" ",u)
    print("=== 抓到的列表类接口请求 ===")
    seen=set()
    for m,u in api_calls:
        if u not in seen:seen.add(u);print(" ",m,u[:120])
    b.close()
