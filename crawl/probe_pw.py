# -*- coding: utf-8 -*-
import sys
from playwright.sync_api import sync_playwright
import time
UA="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120 Safari/537.36"
url=sys.argv[1]
with sync_playwright() as p:
    b=p.chromium.launch(headless=True,executable_path="/usr/local/bin/chromium",args=["--no-sandbox","--disable-dev-shm-usage"])
    pg=b.new_page(user_agent=UA)
    try:
        pg.goto(url,wait_until="networkidle",timeout=35000)
    except Exception as e:
        print("nav:",str(e)[:80])
    time.sleep(4)
    # 滚动触发懒加载
    for y in range(0,8000,800):
        pg.evaluate("(y)=>window.scrollTo(0,y)",y);time.sleep(0.3)
    time.sleep(2)
    links=pg.eval_on_selector_all("a[href]","""els=>els.map(a=>({h:a.href,t:(a.innerText||'').trim().slice(0,40)})).filter(x=>/\\.(pdf|zip|rar|docx?)(\\?|$)/i.test(x.h)||/下载|手册|说明|资料|download/i.test(x.t))""")
    print("文档/下载相关链接:",len(links))
    for x in links[:30]:
        print("  ",x["t"][:30],"|",x["h"][:95])
    # 同时 dump 所有 pdf（含 JS 变量）
    pdfs=pg.eval_on_selector_all("a[href$='.pdf'],a[href*='.pdf?']","els=>els.map(a=>a.href)")
    print("PDF直链:",len(pdfs))
    for x in pdfs[:15]:print("   ",x[:110])
    b.close()
