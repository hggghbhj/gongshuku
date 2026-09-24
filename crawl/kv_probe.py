#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# 只读探测 KV 结构。用法:
#   CF_GLOBALKEY=xxx CF_EMAIL=1934046256@qq.com python3 kv_probe.py
#   或 CF_API_TOKEN=xxx python3 kv_probe.py
import os,sys,json,urllib.request,urllib.parse
sys.path.insert(0,".")
from kv_auth import auth_headers
ACCT="11fbdbef946c8525ff9713e92b8ad4b3"; NS="06a3f1ba397c48789f57db119175299e"
B="https://api.cloudflare.com/client/v4"
def get(path):
    req=urllib.request.Request(B+path,headers=auth_headers())
    with urllib.request.urlopen(req,timeout=60) as r:return r.read().decode("utf-8","ignore")
# 1) 验证：能读到账号即认证有效
try:
    a=json.loads(get("/accounts/%s"%ACCT))
    print("认证成功:",a["result"].get("name"),"|",a["result"].get("id"))
except Exception as e:
    print("认证失败:",e);sys.exit(1)
# 2) 列 keys
keys=[];cursor=""
while True:
    p="/accounts/%s/storage/kv/namespaces/%s/keys?limit=1000"%(ACCT,NS)
    if cursor:p+="&cursor="+cursor
    r=json.loads(get(p))
    if not r.get("success"):print("列keys失败:",r.get("errors"));break
    keys+=[k["name"] for k in r["result"]]
    cursor=r.get("result_info",{}).get("cursor")
    if not cursor:break
print("\nKV keys (%d):"%len(keys))
for k in keys:
    try:
        raw=get("/accounts/%s/storage/kv/namespaces/%s/values/%s"%(ACCT,NS,urllib.parse.quote(k,safe="")))
        tag="?"
        try:
            obj=json.loads(raw)
            if isinstance(obj,list):tag="数组 %d 项"%len(obj)
            elif isinstance(obj,dict):
                tag="对象 keys="+str(list(obj.keys())[:8])
                if isinstance(obj.get("docs"),list):tag+=" docs=%d"%len(obj["docs"])
        except Exception:tag="文本 %d 字节"%len(raw)
        print("  - %s  [%s]"%(k,tag))
    except Exception as e:
        print("  - %s  [读取失败 %s]"%(k,e))
