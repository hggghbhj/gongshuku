# -*- coding: utf-8 -*-
from playwright.sync_api import sync_playwright
from pw_util import chromium_path
import time
UA="Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/120 Safari/537.36"
with sync_playwright() as p:
    b=p.chromium.launch(headless=True,executable_path=chromium_path(),args=["--no-sandbox","--disable-dev-shm-usage"])
    pg=b.new_page(user_agent=UA)
    pg.goto("https://www.veichi.cn/service/datadownload",wait_until="domcontentloaded",timeout=30000)
    for i in range(15):
        time.sleep(2)
        if pg.eval_on_selector_all("a[href*='.pdf']","e=>e.length")>3:break
    # 分页区域HTML
    pager=pg.evaluate("""()=>{
      const el=document.querySelector('.pagination,.pager,.page,#pagination,.pages');
      return el?el.outerHTML.slice(0,600):'no pager class';
    }""")
    print("=== 分页HTML ===");print(pager)
    # 当前页PDF数
    n1=pg.eval_on_selector_all("a[href*='.pdf']","e=>new Set(e.map(a=>a.href)).size")
    print("首页去重PDF数:",n1)
    # 试 ?page=2
    pg.goto("https://www.veichi.cn/service/datadownload?page=2",wait_until="domcontentloaded",timeout=30000)
    time.sleep(3)
    n2=pg.eval_on_selector_all("a[href*='.pdf']","e=>new Set(e.map(a=>a.href)).size")
    first2=pg.eval_on_selector_all("a[href*='.pdf']","e=>e[0]?e[0].href:''")
    print("?page=2 PDF数:",n2,"首条:",first2[-40:])
    b.close()
