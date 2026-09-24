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
    # 一条记录的结构（标题+链接+日期）
    sample=pg.evaluate("""()=>{
      const a=document.querySelector("a[href*='.pdf']");
      if(!a)return null;
      let row=a.closest('tr')||a.closest('li')||a.closest('div')||a.parentElement;
      return {href:a.href, text:a.innerText.trim(), rowText:row?row.innerText.trim().slice(0,120):''};
    }""")
    print("=== 一条记录结构 ==="); print(sample)
    # 分页控件
    pgx=pg.evaluate("""()=>{
      const out=[];
      document.querySelectorAll('a').forEach(a=>{
        const t=(a.innerText||'').trim();
        if(/下一页|下页|>|^[0-9]+$/.test(t)&&a.href)out.push({t:t.slice(0,10),href:a.href.slice(-40)});
      });
      return out.slice(0,15);
    }""")
    print("=== 分页链接 ==="); 
    for x in pgx:print("  ",x)
    # 总条数线索
    total=pg.evaluate("""()=>{const m=document.body.innerText.match(/共\\s*\\d+\\s*[条页]/);return m?m[0]:'未找到';}""")
    print("=== 总数线索 ===",total)
    b.close()
