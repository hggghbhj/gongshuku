# -*- coding: utf-8 -*-
from playwright.sync_api import sync_playwright
from pw_util import chromium_path
import time
UA="Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/120 Safari/537.36"
with sync_playwright() as p:
    b=p.chromium.launch(headless=True,executable_path=chromium_path(),args=["--no-sandbox","--disable-dev-shm-usage"])
    pg=b.new_page(user_agent=UA)
    apis=[]
    pg.on("request",lambda r: apis.append((r.method,r.url)) if any(k in r.url.lower() for k in ["api","list","search","download","product","file","query"]) and "delta" in r.url.lower() else None)
    pg.goto("https://downloadcenter.delta-china.com.cn",wait_until="domcontentloaded",timeout=30000)
    time.sleep(5)
    # 是否有登录弹窗/墙
    login_wall=pg.evaluate("""()=>{
      const t=document.body.innerText;
      return {hasLogin:/请登录|登录后|需要登录|登录以/.test(t), text:t.slice(0,200)};
    }""")
    print("登录墙:",login_wall["hasLogin"])
    print("页面文本:",login_wall["text"][:150])
    # 列表项
    items=pg.evaluate("""()=>{
      const rows=document.querySelectorAll('.item,.list-item,tr,.product-item,.download-item,[class*=item]');
      return rows.length;
    }""")
    print("列表项数:",items)
    print("=== 接口请求 ===")
    seen=set()
    for m,u in apis:
        if u not in seen and "static" not in u and ".js" not in u and ".css" not in u:
            seen.add(u);print("  ",m,u[:130])
    b.close()
