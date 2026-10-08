# -*- coding: utf-8 -*-
import urllib.request,urllib.error,socket
socket.setdefaulttimeout(15)
UA="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/120.0 Safari/537.36"
sites={
"艾莫迅":"http://www.amsamotion.com/",
"艾莫迅OSS":"https://oss.amsamotion.com/",
"科思cocis":"http://www.cocis.com/",
"科思cocis2":"https://www.cocis.com/",
"信捷":"http://www.xinje.com/",
"英威腾":"http://www.invt.com/",
"汇川":"http://www.inovance.com/",
"昆仑通态":"http://www.mcgs.com.cn/",
"台达":"http://www.delta-china.com/",
"伟创":"http://www.vicruns.com/",
"正弦":"http://www.sinee.cn/",
"普传":"http://www.powtran.com/",
"海利普":"http://www.holip.com/",
"森兰":"http://www.senlan.cn/",
"易驱":"http://www.easydrive.cn/",
"显控":"http://www.samkoon.com/",
"合信":"http://www.cotion.cn/",
"coolmay":"http://www.coolmay.com/",
"欧瑞":"http://www.euradrives.com/",
"易能":"http://www.encansh.com/",
"金田jtebp":"http://www.jtebp.com/",
}
for name,u in sites.items():
    try:
        req=urllib.request.Request(u,headers={"User-Agent":UA})
        r=urllib.request.urlopen(req,timeout=12)
        data=r.read()
        print(f"{name:12} {r.status} {len(data):>8}  {u}")
    except urllib.error.HTTPError as e:
        print(f"{name:12} HTTP{e.code} {len(e.read()):>8}  {u}")
    except Exception as e:
        print(f"{name:12} 失败 {type(e).__name__}  {u}")
