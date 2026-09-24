# -*- coding: utf-8 -*-
"""认证：优先 Global API Key（CF_EMAIL+CF_GLOBALKEY），其次 API Token（CF_API_TOKEN）。"""
import os
def auth_headers():
    tok=os.environ.get("CF_API_TOKEN","")
    gk=os.environ.get("CF_GLOBALKEY","")
    email=os.environ.get("CF_EMAIL","1934046256@qq.com")
    if gk:
        return {"X-Auth-Email":email,"X-Auth-Key":gk}
    if tok:
        return {"Authorization":"Bearer "+tok}
    raise SystemExit("请设置 CF_GLOBALKEY（+CF_EMAIL）或 CF_API_TOKEN")
