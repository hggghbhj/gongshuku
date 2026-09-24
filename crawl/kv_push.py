#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# 第二步：合并新说明书进 KV（在 kv_probe 确认 DOC_KEY 后运行）
# 用法: CF_API_TOKEN=xxx python3 kv_push.py <数据.json> <KV里存文档的key名>
import os,sys,json,time,urllib.request,urllib.parse
ACCT="11fbdbef946c8525ff9713e92b8ad4b3"; NS="06a3f1ba397c48789f57db119175299e"
TOK=os.environ.get("CF_API_TOKEN","")
from kv_auth import auth_headers; B="https://api.cloudflare.com/client/v4"
data_file=sys.argv[1]; DOC_KEY=sys.argv[2]
new=json.load(open(data_file,encoding="utf-8"))
def req(method,path,body=None):
    h=auth_headers()
    if body is not None:h["Content-Type"]="application/json;charset=utf-8"
    r=urllib.request.Request(B+path,data=body,method=method,headers=h)
    with urllib.request.urlopen(r,timeout=90) as f:return f.read().decode("utf-8","ignore")
def val_get(k):
    return req("GET","/accounts/%s/storage/kv/namespaces/%s/values/%s"%(ACCT,NS,urllib.parse.quote(k,safe="")))
def val_put(k,body):
    return req("PUT","/accounts/%s/storage/kv/namespaces/%s/values/%s"%(ACCT,NS,urllib.parse.quote(k,safe="")),body)
raw=val_get(DOC_KEY); obj=json.loads(raw)
is_list=isinstance(obj,list)
docs=obj if is_list else obj.get("docs",[])
print("现有 %d 条，待加入 %d 条"%(len(docs),len(new)))
have=set(d.get("pdf") for d in docs)
add=[d for d in new if d.get("pdf") not in have]
merged=docs+add
print("实际新增 %d 条，合并后 %d 条"%(len(add),len(merged)))
if not add:raise SystemExit("无新增，退出")
payload=merged if is_list else dict(obj,docs=merged)
resp=val_put(DOC_KEY,json.dumps(payload,ensure_ascii=False).encode("utf-8"))
print("写入结果:",resp[:300])
time.sleep(5)
chk=json.loads(val_get(DOC_KEY))
n=len(chk) if isinstance(chk,list) else len(chk.get("docs",[]))
print("验证：KV 现共 %d 条"%n)
# 抽查新文档
cc=chk if isinstance(chk,list) else chk.get("docs",[])
print("精创云端条数:",len([d for d in cc if d.get("b")=="精创"]))
