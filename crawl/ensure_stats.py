# -*- coding: utf-8 -*-
"""确保 dist/data/stats.json 存在，不存在则创建兜底模板。"""
import json, os, sys
from datetime import datetime, timezone, timedelta

ROOT = os.path.dirname(os.path.abspath(__file__))
STATS = os.path.join(ROOT, "..", "dist", "data", "stats.json")
BJ = timezone(timedelta(hours=8))

if os.path.exists(STATS):
    print("stats.json已存在")
    sys.exit(0)

os.makedirs(os.path.dirname(STATS), exist_ok=True)
tpl = {
    "last_run": datetime.now(BJ).strftime("%Y-%m-%d %H:%M:%S"),
    "last_new": 0,
    "total": 0,
    "brands": {},
    "brand_count": 0,
    "steps": {},
    "cron": "每3小时自动采集",
    "error": "兜底模板",
}
with open(STATS, "w", encoding="utf-8") as f:
    json.dump(tpl, f, ensure_ascii=False)
print("已创建兜底stats.json")
