# -*- coding: utf-8 -*-
import urllib.request,urllib.error,re,http.cookiejar,time
UA="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
cj=http.cookiejar.CookieJar()
op=urllib.request.build_opener(urllib.request.HTTPCookieProcessor(cj))
op.addheaders=[("User-Agent",UA),("Accept","text/html,application/xhtml+xml,*/*;q=0.8"),
("Accept-Language","zh-CN,zh;q=0.9"),("Upgrade-Insecure-Requests","1")]
u="http://www.jtebp.com/"
def raw():
    try:
        r=op.open(u,timeout=25);return r.status,r.read().decode("utf-8","ignore")
    except urllib.error.HTTPError as e:return e.code,e.read().decode("utf-8","ignore")
st,body=raw()
print("首次:",st,repr(body[:300]))
for name in ["wtime","wtoken"]:
    m=re.search(name+r"=([^;'\"]+)",body)
    if m:
        c=http.cookiejar.Cookie(0,name,m.group(1),None,False,"www.jtebp.com",True,False,"/",True,
        False,int(time.time())+3600,False,None,None,{},False)
        cj.set_cookie(c)
print("cookies:",[x.name+"="+x.value for x in cj])
time.sleep(1)
st2,body2=raw()
print("二次:",st2,"大小:",len(body2),repr(body2[:200]))
if st2==200 and len(body2)>500:
    open("jt_home.html","w",encoding="utf-8").write(body2)
    links=sorted(set(re.findall(r'href=["\']?([^"\' >]+)',body2)))
    for l in links:
        if any(k in l for k in ['down','zl','xz','file','pdf','list','show','support','product']):print(" 链接:",l[:90])
