# -*- coding: utf-8 -*-
"""把各品牌 manifest 转成前端 DOCS 记录，输出 docs-3.js（官网免费直链数据）。"""
import json,os,re

BRANDS={
 "coolmay":{"b":"顾美科技","page":"http://www.coolmay.com","ty_default":"使用手册"},
 "elitech":{"b":"精创电气","page":"https://www.e-elitech.com/index.php?v=new_manual","ty_default":"说明书"},
 "xinje":{"b":"信捷电气","page":"https://www.xinje.com/web/downloadCenter/index","ty_default":"产品手册"},
 "leisai":{"b":"雷赛智能","page":"https://www.leisai.com/downloads.html","ty_default":"产品手册"},
 "sinee":{"b":"正弦电气","page":"https://www.sinee.cn/47/","ty_default":"用户手册"},
 "oura":{"b":"欧瑞传动","page":"https://www.euradrives.com/service/down.html","ty_default":"用户手册"},
 "hcfa":{"b":"禾川科技","page":"https://www.hcfa.cn/service/index.html","ty_default":"说明书"},
 "jintian":{"b":"金田科技","page":"http://jtdrive.com/downs/sms","ty_default":"说明书"},
 "invt":{"b":"英威腾","page":"https://www.invt.com.cn/dowload-15","ty_default":"说明书"},
 "veichi":{"b":"伟创电气","page":"https://www.veichi.cn/service/datadownload","ty_default":"用户手册"},
 "mcgs":{"b":"昆仑通态","page":"https://www.mcgspro.com/downloads.html","ty_default":"用户手册"},
 "amsamotion":{"b":"艾莫迅","page":"https://www.amsamotion.com/download.html","ty_default":"产品手册"},
 "senlan":{"b":"森兰","page":"http://www.chinavvvf.com/list-57-1.html","ty_default":"用户手册"},
 "easydrive":{"b":"易驱电气","page":"https://www.szeasydrive.com/download/","ty_default":"用户手册"},
 "inovance":{"b":"汇川技术","page":"https://www.inovance.com/portal-front/home/search","ty_default":"用户手册"},
 "enc":{"b":"易能电气","page":"http://www.enc.net.cn/service/filedownlaod/productType/index.html","ty_default":"使用手册"},
 "cotion":{"b":"合信技术","page":"https://www.co-trust.com/Download/index.html","ty_default":"用户手册"},
 "gongbei":{"b":"工贝电子","page":"https://jngbdz.com/","ty_default":"产品说明书"},
 "meanwell":{"b":"明纬电源","page":"https://www.meanwell.com.cn/productManual.aspx","ty_default":"产品手册"},
 "santak":{"b":"山特UPS","page":"https://www.santak.com.cn/page/santak-downloads.html","ty_default":"使用手册"},
 "simphoenix":{"b":"四方电气","page":"https://www.simphoenix.com/download/manual/","ty_default":"用户手册"},
 "gtake":{"b":"吉泰科","page":"https://www.gtake.com/downloads/","ty_default":"用户手册"},
 "tengen":{"b":"天正电气","page":"https://www.tengen.com/Download.html","ty_default":"产品手册"},
 "hiconics":{"b":"合康新能","page":"https://www.hiconics.com/category/download1.html","ty_default":"产品手册"},
 "ema":{"b":"伊玛电子","page":"https://www.ema-electronic.com/downloadsms.html","ty_default":"产品手册"},
 "banner":{"b":"邦纳","page":"https://www.bannerengineering.com.cn/cn/zh/products/wireless-sensor-networks/reference-library/manuals.html","ty_default":"产品手册"},
 "sanyou":{"b":"三友","page":"https://www.sanyourelay.com/pc/download","ty_default":"产品手册"},
 "yudian":{"b":"宇电","page":"https://www.yudian.com/down/10039.html","ty_default":"产品手册"},
 "cincon":{"b":"Cincon","page":"https://www.cincon.com/user-manual_en.php","ty_default":"用户手册"},
 "hollysys":{"b":"和利时","page":"https://www.hollysys.com/download/products","ty_default":"产品手册"},
 "hongfa":{"b":"宏发","page":"https://www.hongfa.com/en/service/down","ty_default":"产品手册"},
 "haiwell":{"b":"海为","page":"https://haiwell.com/download/download.php?class2=392","ty_default":"产品手册"},
 "hongrun":{"b":"虹润仪表","page":"https://www.hrgs.com.cn/download/?tag=8","ty_default":"说明书"},
 "wideplus":{"b":"上润仪表","page":"https://www.wideplus.com/companyfile/2/","ty_default":"使用手册"},
 "anthone":{"b":"安东仪表","page":"https://anthone.com.cn/index.php/Server/data_download.html","ty_default":"说明书"},
 "lazzen":{"b":"良信电器","page":"https://www.lazzen.com/support/downloads/product-manual","ty_default":"产品说明书"},
 "yankong":{"b":"研控自动化","page":"https://www.yankong.com/download.html","ty_default":"产品手册"},
 "huceen":{"b":"汇辰自动化","page":"https://www.huceen.cn/download/list-274-cn.html","ty_default":"产品手册"},
 "mege":{"b":"米格电机","page":"https://www.mege.cn/index.php?ac=Article&at=List&tid=42","ty_default":"产品样册"},
 "lanbao":{"b":"兰宝传感","page":"http://www.shlanbao.cn/download.html","ty_default":"产品手册"},
 "alpha":{"b":"阿尔法电气","page":"http://www.szalpha.cn/zw/download/index.aspx","ty_default":"用户手册"},
 "xichi":{"b":"西驰电气","page":"http://www.xichi.com/service/smsxz/","ty_default":"使用说明书"},
 "anbangxin":{"b":"安邦信","page":"http://www.anbangxin.com/page_7/","ty_default":"说明书"},
 "huazhong":{"b":"华中数控","page":"https://huazhongcnc.com/portal/list/index/cid/73.html","ty_default":"用户手册"},
 "gskcnc":{"b":"广州数控","page":"https://www.gsk.com.cn/zlxz/index_15.aspx?lcid=18","ty_default":"使用手册"},
 "westpow":{"b":"西安西普","page":"https://www.westpow.com/download-center","ty_default":"说明书"},
 "microsensor":{"b":"麦克传感器","page":"https://www.microsensor.cn/download","ty_default":"产品说明书"},
 "growatt":{"b":"古瑞瓦特","page":"https://www.growatt.com/support/download","ty_default":"产品手册"},
 "delixi":{"b":"德力西变频器","page":"https://www.delixidrive.com/list-26-1.html","ty_default":"使用说明书"},
 "fuling":{"b":"富凌电气","page":"https://www.chinafuling.com/download-3.html","ty_default":"使用手册"},
 "shenler":{"b":"申乐电气","page":"https://www.shenler.cn/","ty_default":"产品手册"},
 "huibang":{"b":"汇邦科技","page":"https://www.hbkj.com.cn/download-39-0-1.html","ty_default":"说明书"},
 "kaimin":{"b":"开民电器","page":"http://www.cnkaimin.net/downlist/T1","ty_default":"使用说明书"},
 "gclsi":{"b":"协鑫集成","page":"https://www.gclsi.com/download.html","ty_default":"安装手册"},
 "people":{"b":"人民电器","page":"https://www.chinapeople.com","ty_default":"说明书"},
 "fotek":{"b":"阳明电机","page":"https://www.fotek.com.tw/zh-cn/download","ty_default":"说明书"},
 "airtac":{"b":"亚德客","page":"https://www.airtac.com/download","ty_default":"产品手册"},
 "chint":{"b":"正泰电器","page":"http://m.chint.com/kunlun/","ty_default":"产品样本"},
 "jelpc":{"b":"佳尔灵气动","page":"https://www.jelpc.com/download/","ty_default":"产品目录"},
 "yatai":{"b":"亚泰仪表","page":"http://www.yatai.sh.cn","ty_default":"使用说明书"},
 "siglent":{"b":"鼎阳科技","page":"https://www.siglent.com/support/resource/","ty_default":"用户手册"},
}
def clean_title(t,b):
    t=re.sub(r'\.pdf$','',t or '',flags=re.I).strip()
    t=re.sub(r'\s+',' ',t)
    return t
def models(t):
    # 提取常见型号 token
    cands=re.findall(r'[A-Za-z]{1,6}[-]?[A-Za-z0-9]{1,3}[\-\dA-Za-z]{0,12}',t)
    out=[]
    for c in cands:
        if len(c)>=3 and re.search(r'\d',c):out.append(c)
    return ",".join(dict.fromkeys(out[:6]))
def norm(s):
    return re.sub(r'\s+','',(s or '').lower())
def rec(b,page,ty,t,d,v,u,size,pages,cat=""):
    t=clean_title(t,b)
    kw=(b+" "+t+" "+cat+" "+models(t)).strip()
    return {"t":t,"b":b,"d":d or "","ty":ty or "说明书","v":v or "","l":"中文",
      "url":page,"pdf":u,"size":size or "","kw":kw,
      "sum":"%s %s（%d页），来源品牌官网，免费在线查看。"%(b,cat or ty,pages or 0),
      "src":"官网直链","pages":pages or 0,
      "_sx":norm(" ".join([t,b,kw,cat]))}

out=[]
def load(brand):
    fn=brand+"_manifest.json"
    if os.path.exists(fn):
        return json.load(open(fn,encoding="utf-8"))
    return []

# 各品牌
for x in load("elitech"):
    info=BRANDS["elitech"]
    out.append(rec(info["b"],info["page"],"说明书",x.get("t"),x.get("d"),"",x.get("u"),"",x.get("pages"),x.get("cat","")))
for x in load("xinje"):
    info=BRANDS["xinje"]
    out.append(rec(info["b"],info["page"],"产品手册",x.get("t"),x.get("d"),x.get("v"),x.get("u"),x.get("size_h",""),x.get("pages")))
for x in load("leisai"):
    info=BRANDS["leisai"]
    out.append(rec(info["b"],info["page"],"选型手册" if "选型" in (x.get("cat") or "") else "产品手册",x.get("t"),x.get("d"),x.get("v"),x.get("u"),"",x.get("pages"),x.get("cat","")))
for x in load("sinee"):
    info=BRANDS["sinee"]
    ty="宣传样本" if "宣传" in (x.get("cat") or "") else "用户手册"
    out.append(rec(info["b"],info["page"],ty,x.get("t"),x.get("d",""),"",x.get("u"),"",x.get("pages"),x.get("cat","")))
for x in load("oura"):
    info=BRANDS["oura"]
    ty="宣传资料" if "宣传" in (x.get("cat") or "") else "用户手册"
    out.append(rec(info["b"],info["page"],ty,x.get("t"),x.get("d",""),"",x.get("u"),"",x.get("pages"),x.get("cat","")))
for x in load("hcfa"):
    info=BRANDS["hcfa"]
    out.append(rec(info["b"],info["page"],"说明书",x.get("t"),"","",x.get("u"),"",x.get("pages")))
for x in load("invt"):
    info=BRANDS["invt"]
    cat=x.get("cat","") or ""
    out.append(rec(info["b"],info["page"],cat or "说明书",x.get("t"),x.get("d"),x.get("v"),x.get("u"),"",x.get("pages"),cat))
# 金田链接清单是 jintian_pw_links.json
jt=json.load(open("jintian_pw_links.json",encoding="utf-8")) if os.path.exists("jintian_pw_links.json") else []
# 若有 manifest 补充页数
jt_pages={}
if os.path.exists("jintian_manifest.json"):
    for x in json.load(open("jintian_manifest.json",encoding="utf-8")):jt_pages[x.get("u","")]=x.get("pages",0)
for x in jt:
    info=BRANDS["jintian"]
    out.append(rec(info["b"],info["page"],"说明书",x.get("t"),x.get("d",""),"",x.get("u"),"",jt_pages.get(x.get("u",""),0)))
for x in load("coolmay"):
    info=BRANDS["coolmay"]
    cat=x.get("cat","")
    ty="宣传画册" if "画册" in cat or "宣传" in cat else "用户手册"
    out.append(rec(info["b"],info["page"],ty,x.get("t"),"","",x.get("u"),"",x.get("pages"),cat))
for x in load("veichi"):
    info=BRANDS["veichi"]
    out.append(rec(info["b"],info["page"],"用户手册",x.get("t"),x.get("d"),"",x.get("u"),"",x.get("pages")))
for x in load("mcgs"):
    info=BRANDS["mcgs"]
    out.append(rec(info["b"],info["page"],"用户手册",x.get("t"),x.get("d"),"",x.get("u"),"",x.get("pages"),x.get("cat","")))
for x in load("amsamotion"):
    info=BRANDS["amsamotion"]
    out.append(rec(info["b"],info["page"],"产品手册",x.get("t"),"","",x.get("u"),"",x.get("pages")))
for x in load("senlan"):
    info=BRANDS["senlan"]
    out.append(rec(info["b"],info["page"],"用户手册",x.get("t"),"","",x.get("u"),"",x.get("pages")))
for x in load("easydrive"):
    info=BRANDS["easydrive"]
    out.append(rec(info["b"],info["page"],"用户手册",x.get("t"),"","",x.get("u"),"",x.get("pages")))
for x in load("inovance"):
    info=BRANDS["inovance"]
    out.append(rec(info["b"],info["page"],x.get("type","用户手册"),x.get("name"),x.get("date",""),"",x.get("url"),"",x.get("pages"),x.get("type","")))
for x in load("enc"):
    info=BRANDS["enc"]
    out.append(rec(info["b"],info["page"],x.get("type","使用手册"),x.get("name"),"","",x.get("url"),"",x.get("pages")))
for x in load("cotion"):
    info=BRANDS["cotion"]
    out.append(rec(info["b"],info["page"],x.get("type","用户手册"),x.get("name"),"","",x.get("url"),"",x.get("pages"),x.get("type","")))
for x in load("gongbei"):
    info=BRANDS["gongbei"]
    out.append(rec(info["b"],info["page"],x.get("type","产品说明书"),x.get("name"),"","",x.get("url"),"",x.get("pages")))
for x in load("meanwell"):
    info=BRANDS["meanwell"]
    out.append(rec(info["b"],info["page"],x.get("type","产品手册"),x.get("name"),"","",x.get("url"),"",x.get("pages")))
for x in load("santak"):
    info=BRANDS["santak"]
    out.append(rec(info["b"],info["page"],x.get("type","使用手册"),x.get("name"),"","",x.get("url"),"",x.get("pages")))
for x in load("simphoenix"):
    info=BRANDS["simphoenix"]
    out.append(rec(info["b"],info["page"],x.get("type","用户手册"),x.get("name"),"","",x.get("url"),"",x.get("pages")))
for x in load("gtake"):
    info=BRANDS["gtake"]
    out.append(rec(info["b"],info["page"],x.get("type","用户手册"),x.get("name"),"","",x.get("url"),"",x.get("pages")))
for x in load("tengen"):
    info=BRANDS["tengen"]
    out.append(rec(info["b"],info["page"],x.get("type","产品手册"),x.get("name"),"","",x.get("url"),"",x.get("pages")))
for x in load("hiconics"):
    info=BRANDS["hiconics"]
    out.append(rec(info["b"],info["page"],x.get("type","产品手册"),x.get("name"),"","",x.get("url"),"",x.get("pages")))
for x in load("ema"):
    info=BRANDS["ema"]
    out.append(rec(info["b"],info["page"],x.get("type","产品手册"),x.get("name"),"","",x.get("url"),"",x.get("pages")))
for x in load("banner"):
    info=BRANDS["banner"]
    out.append(rec(info["b"],info["page"],x.get("type","产品手册"),x.get("name"),"","",x.get("url"),"",x.get("pages")))
for x in load("sanyou"):
    info=BRANDS["sanyou"]
    out.append(rec(info["b"],info["page"],x.get("type","产品手册"),x.get("name"),"","",x.get("url"),"",x.get("pages")))
for x in load("yudian"):
    info=BRANDS["yudian"]
    out.append(rec(info["b"],info["page"],x.get("type","产品手册"),x.get("name"),"","",x.get("url"),"",x.get("pages")))
for x in load("cincon"):
    info=BRANDS["cincon"]
    out.append(rec(info["b"],info["page"],x.get("type","用户手册"),x.get("name"),"","",x.get("url"),"",x.get("pages")))
for x in load("hollysys"):
    info=BRANDS["hollysys"]
    out.append(rec(info["b"],info["page"],x.get("type","产品手册"),x.get("name"),"","",x.get("url"),"",x.get("pages")))
for x in load("hongfa"):
    info=BRANDS["hongfa"]
    out.append(rec(info["b"],info["page"],x.get("type","产品手册"),x.get("name"),"","",x.get("url"),"",x.get("pages")))
for x in load("haiwell"):
    info=BRANDS["haiwell"]
    out.append(rec(info["b"],info["page"],x.get("type","产品手册"),x.get("name"),"","",x.get("url"),"",x.get("pages")))
for x in load("hongrun"):
    info=BRANDS["hongrun"]
    out.append(rec(info["b"],info["page"],x.get("type","说明书"),x.get("name"),"","",x.get("url"),"",x.get("pages")))
for x in load("wideplus"):
    info=BRANDS["wideplus"]
    out.append(rec(info["b"],info["page"],x.get("type","使用手册"),x.get("name"),"","",x.get("url"),"",x.get("pages")))
for x in load("anthone"):
    info=BRANDS["anthone"]
    out.append(rec(info["b"],info["page"],x.get("type","说明书"),x.get("name"),"","",x.get("url"),"",x.get("pages")))
for x in load("lazzen"):
    info=BRANDS["lazzen"]
    out.append(rec(info["b"],info["page"],x.get("type","产品说明书"),x.get("name"),"","",x.get("url"),"",x.get("pages")))
for x in load("yankong"):
    info=BRANDS["yankong"]
    out.append(rec(info["b"],info["page"],x.get("type","产品手册"),x.get("name"),"","",x.get("url"),"",x.get("pages")))
for x in load("huceen"):
    info=BRANDS["huceen"]
    out.append(rec(info["b"],info["page"],x.get("type","产品手册"),x.get("name"),"","",x.get("url"),"",x.get("pages")))
for x in load("mege"):
    info=BRANDS["mege"]
    out.append(rec(info["b"],info["page"],x.get("type","产品样册"),x.get("name"),"","",x.get("url"),"",x.get("pages")))
for x in load("lanbao"):
    info=BRANDS["lanbao"]
    out.append(rec(info["b"],info["page"],x.get("type","产品手册"),x.get("name"),"","",x.get("url"),"",x.get("pages")))
for x in load("alpha"):
    info=BRANDS["alpha"]
    out.append(rec(info["b"],info["page"],x.get("type","用户手册"),x.get("name"),"","",x.get("url"),"",x.get("pages")))
for x in load("xichi"):
    info=BRANDS["xichi"]
    out.append(rec(info["b"],info["page"],x.get("type","使用说明书"),x.get("name"),"","",x.get("url"),"",x.get("pages")))
for x in load("anbangxin"):
    info=BRANDS["anbangxin"]
    out.append(rec(info["b"],info["page"],x.get("type","说明书"),x.get("name"),"","",x.get("url"),"",x.get("pages")))
for x in load("huazhong"):
    info=BRANDS["huazhong"]
    out.append(rec(info["b"],info["page"],x.get("type","用户手册"),x.get("name"),"","",x.get("url"),"",x.get("pages")))
for x in load("gskcnc"):
    info=BRANDS["gskcnc"]
    out.append(rec(info["b"],info["page"],x.get("type","使用手册"),x.get("name"),"","",x.get("url"),"",x.get("pages")))
for x in load("westpow"):
    info=BRANDS["westpow"]
    out.append(rec(info["b"],info["page"],x.get("type","说明书"),x.get("name"),"","",x.get("url"),"",x.get("pages")))
for x in load("microsensor"):
    info=BRANDS["microsensor"]
    out.append(rec(info["b"],info["page"],x.get("type","产品说明书"),x.get("name"),"","",x.get("url"),"",x.get("pages")))
for x in load("growatt"):
    info=BRANDS["growatt"]
    out.append(rec(info["b"],info["page"],x.get("type","产品手册"),x.get("name"),"","",x.get("url"),"",x.get("pages")))
for x in load("delixi"):
    info=BRANDS["delixi"]
    out.append(rec(info["b"],info["page"],x.get("type","使用说明书"),x.get("name"),"","",x.get("url"),"",x.get("pages")))
for x in load("fuling"):
    info=BRANDS["fuling"]
    out.append(rec(info["b"],info["page"],x.get("type","使用手册"),x.get("name"),"","",x.get("url"),"",x.get("pages")))
for x in load("shenler"):
    info=BRANDS["shenler"]
    out.append(rec(info["b"],info["page"],x.get("type","产品手册"),x.get("name"),"","",x.get("url"),"",x.get("pages")))
for x in load("huibang"):
    info=BRANDS["huibang"]
    out.append(rec(info["b"],info["page"],x.get("type","说明书"),x.get("name"),"","",x.get("url"),"",x.get("pages")))
for x in load("kaimin"):
    info=BRANDS["kaimin"]
    out.append(rec(info["b"],info["page"],x.get("type","使用说明书"),x.get("name"),"","",x.get("url"),"",x.get("pages")))
for x in load("gclsi"):
    info=BRANDS["gclsi"]
    out.append(rec(info["b"],info["page"],x.get("type","安装手册"),x.get("name"),"","",x.get("url"),"",x.get("pages")))
for x in load("people"):
    info=BRANDS["people"]
    out.append(rec(info["b"],info["page"],x.get("type","说明书"),x.get("name"),"","",x.get("url"),"",x.get("pages")))
for x in load("fotek"):
    info=BRANDS["fotek"]
    out.append(rec(info["b"],info["page"],x.get("type","说明书"),x.get("name"),"","",x.get("url"),"",x.get("pages")))
for x in load("airtac"):
    info=BRANDS["airtac"]
    out.append(rec(info["b"],info["page"],x.get("type","产品手册"),x.get("name"),"","",x.get("url"),"",x.get("pages")))
for x in load("chint"):
    info=BRANDS["chint"]
    out.append(rec(info["b"],info["page"],x.get("type","产品样本"),x.get("name"),"","",x.get("url"),"",x.get("pages")))
for x in load("jelpc"):
    info=BRANDS["jelpc"]
    out.append(rec(info["b"],info["page"],x.get("type","产品目录"),x.get("name"),"","",x.get("url"),"",x.get("pages")))
for x in load("yatai"):
    info=BRANDS["yatai"]
    out.append(rec(info["b"],info["page"],x.get("type","使用说明书"),x.get("name"),"","",x.get("url"),"",x.get("pages")))
for x in load("siglent"):
    info=BRANDS["siglent"]
    out.append(rec(info["b"],info["page"],x.get("type","用户手册"),x.get("name"),"","",x.get("url"),"",x.get("pages")))
# 普传：kv_powtran.json 已是标准格式，补充 _sx/src
if os.path.exists("kv_powtran.json"):
    for x in json.load(open("kv_powtran.json",encoding="utf-8")):
        r=dict(x);r["src"]="官网直链";r["pages"]=0
        r["_sx"]=norm(" ".join([r.get("t",""),r.get("b",""),r.get("kw","")]))
        out.append(r)

# 去重（按 pdf URL）
seen=set();uniq=[]
for r in out:
    k=r.get("pdf","")
    if k in seen:continue
    seen.add(k);uniq.append(r)
json.dump(uniq,open("docs_new_records.json","w",encoding="utf-8"),ensure_ascii=False,indent=1)
# 写 JS 分片
with open("docs-3.js","w",encoding="utf-8") as f:
    f.write("/* 工书库数据分片3：品牌官网免费直链（自动采集，每3小时增量更新） */\n")
    f.write("DOCS=DOCS.concat(")
    json.dump(uniq,f,ensure_ascii=False,separators=(",",":"))
    f.write(");\n")
from collections import Counter
print("生成官网直链记录:",len(uniq))
print(dict(Counter(r["b"] for r in uniq)))
print("docs-3.js 大小: %.2f MB"%(os.path.getsize("docs-3.js")/1048576))
