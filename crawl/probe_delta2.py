# -*- coding: utf-8 -*-
from playwright.sync_api import sync_playwright
from pw_util import chromium_path
import time
UA="Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/120 Safari/537.36"
with sync_playwright() as p:
    b=p.chromium.launch(headless=True,executable_path=chromium_path(),args=["--no-sandbox","--disable-dev-shm-usage"])
    pg=b.new_page(user_agent=UA)
    apis=[]
    pg.on("request",lambda r: apis.append(r.url) if any(k in r.url.lower() for k in ["api","list","search","product","file","query","category","series"]) and "delta" in r.url.lower() else None)
    pg.goto("https://downloadcenter.delta-china.com.cn",wait_until="domcontentloaded",timeout=30000)
    time.sleep(4)
    # 点击"工业自动化"
    try:
        pg.evaluate("""()=>{const a=[...document.querySelectorAll('a,span,div,li')].find(e=>e.innerText.trim()==='工业自动化');if(a)a.click();}""")
        time.sleep(3)
    except:pass
    # 找可点击的产品系列链接
    links=pg.evaluate("""()=>{
      return [...document.querySelectorAll('a')].map(a=>({t:a.innerText.trim().slice(0,20),h:a.href})).filter(x=>x.t&&x.h&&x.h!=='#'&&!x.h.includes('javascript')).slice(0,15);
    }""")
    print("=== 可点击链接 ===")
    for l in links:print("  ",l["t"],"->",l["h"][:80])
    # 点第一个产品系列
    try:
        first=[l for l in links if 'downloadcenter' in l['h'] or 'filecenter' in l['h']]
        if first:
            pg.goto(first[0]['h'],wait_until="domcontentloaded",timeout=25000)
            time.sleep(3)
    except:pass
    print("=== 接口 ===")
    for u in list(dict.fromkeys(apis))[:15]:
        if '.js' not in u and '.css' not in u and 'static' not in u and 'Images' not in u:print("  ",u[:130])
    print("=== 当前URL ===",pg.url)
    b.close()
