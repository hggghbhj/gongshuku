# -*- coding: utf-8 -*-
"""金田无人值守采集器（playwright 无头浏览器，过 WAF）。
可重复运行：遍历6页收集链接 -> 逐 PDF 用挑战标签过 WAF -> 主标签 fetch 回传接收器。
用法: python3 crawl_jintian_pw.py [limit]   limit 仅测前N个
"""
from playwright.sync_api import sync_playwright
import time,sys,json,os
LIST="http://jtdrive.com/downs/sms"
UA="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120 Safari/537.36"
_a=sys.argv[1:]
LINKS_ONLY="--links-only" in _a
_a=[x for x in _a if x!="--links-only"]
limit=int(_a[0]) if _a else 0

def pass_waf(page,url=LIST):
    page.goto(url,wait_until="domcontentloaded",timeout=30000)
    for i in range(18):
        time.sleep(2)
        try:
            if page.eval_on_selector_all("a[href*='.pdf']","els=>els.length")>0:
                return True
        except:pass
    return False

def collect(main):
    """遍历6页收集 (href, title, date)"""
    out=[]
    for pgno in range(1,7):
        url=LIST if pgno==1 else "%s/page/%d"%(LIST,pgno)
        if pgno>1:
            # 页内点击，避免直接导航被弹回；直接goto也可能成功，先试goto
            pass_waf(main,url)
        rows=main.eval_on_selector_all(".down-list li", """els=>els.map(li=>{
            const a=li.querySelector('.down-btn a[href*=".pdf"]');
            const t=li.querySelector('.down-info');
            const sp=li.querySelector('.down-btn span');
            return {u:a?a.href:null,t:t?t.innerText.trim():'',d:sp?sp.innerText.trim():''};
        })""")
        for r in rows:
            if r["u"] and r["u"] not in [x["u"] for x in out]:
                out.append(r)
        print("  第%d页 %d 条"%(pgno,len(rows)))
    return out

def main_run():
    with sync_playwright() as p:
        b=p.chromium.launch(headless=True,executable_path="/usr/local/bin/chromium",
                            args=["--no-sandbox","--disable-dev-shm-usage"])
        ctx=b.new_context(user_agent=UA,accept_downloads=True)
        main=ctx.new_page()
        if not pass_waf(main):
            # 云端 IP 常被 WAF 拦：不崩溃、不阻断，保留上一版链接清单（已持久化），下次再试
            print("下载页 WAF 未过（云端IP可能被拦）：保留现有 jintian_pw_links.json，本次仅跳过")
            b.close();return
        print("下载页 WAF 已过")
        items=collect(main)
        print("共收集",len(items),"个PDF")
        if limit:items=items[:limit]
        json.dump(items,open("jintian_pw_links.json","w",encoding="utf-8"),ensure_ascii=False,indent=1)
        if LINKS_ONLY:
            print("--links-only：链接清单已刷新，跳过逐PDF下载验证")
            b.close();return
        chal=ctx.new_page()  # 挑战标签
        ok=0;fail=[]
        for i,it in enumerate(items):
            name="jt_%03d.pdf"%i
            dst="pdfs/jintian/"+name
            if os.path.exists(dst) and os.path.getsize(dst)>10000:
                # 已存在则跳过（幂等）
                ok+=1;continue
            done=False
            for attempt in range(3):
                try:
                    # 挑战标签导航过 wp-content challenge
                    try:chal.goto(it["u"],wait_until="commit",timeout=20000)
                    except:pass
                    time.sleep(5)
                    # 主标签确保在下载页
                    if "downs" not in main.url:pass_waf(main)
                    r=main.evaluate("""async(arg)=>{
                      for(let k=0;k<4;k++){
                        const r=await fetch(arg.u,{credentials:'include'});
                        if(r.status===200){
                          const buf=await r.arrayBuffer();
                          const pr=await fetch('http://127.0.0.1:8899/save?brand=jintian&name='+arg.name,{method:'POST',body:buf});
                          return pr.status+':'+await pr.text();
                        }
                        await new Promise(x=>setTimeout(x,1000));
                      }
                      return 'FETCHFAIL';
                    }""",{"u":it["u"],"name":name})
                    if r and r.startswith("200"):
                        done=True;break
                except Exception as e:
                    time.sleep(2)
            if done and os.path.exists(dst) and os.path.getsize(dst)>10000:
                ok+=1;print("  [%d/%d] %s OK %dKB"%(i+1,len(items),name,os.path.getsize(dst)//1024))
            else:
                fail.append((name,it["t"][:30]));print("  [%d/%d] %s 失败 %s"%(i+1,len(items),name,r))
        print("完成: %d/%d 成功, %d 失败"%(ok,len(items),len(fail)))
        if fail:print("失败清单:",fail)
        b.close()

if __name__=="__main__":
    main_run()
