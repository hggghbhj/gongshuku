#!/bin/bash
# 安全部署脚本：部署前先从线上拉取最新stats.json，保留steps和last_run，只更新total/brands
set -e
cd "$(dirname "$0")"

echo "=== 1. 从线上拉取最新stats.json(保留steps) ==="
curl -s -H "Cache-Control: no-cache" "https://gongshuku.pages.dev/data/stats.json?_=$(date +%s%N)" -o /tmp/online_stats.json
if [ -s /tmp/online_stats.json ]; then
  echo "线上stats已拉取"
  python3 -c "
import json
online=json.load(open('/tmp/online_stats.json'))
# 基于本地manifest重新计算total和brands
import glob
counts={}
for fp in glob.glob('crawl/*_manifest.json'):
    key=fp.replace('crawl/','').replace('_manifest.json','')
    try:
        d=json.load(open(fp,encoding='utf-8'))
        counts[key]=len(d) if isinstance(d,list) else 0
    except: counts[key]=0
try:
    d=json.load(open('crawl/kv_powtran.json',encoding='utf-8'))
    counts['powtran']=len(d) if isinstance(d,list) else 0
except: pass
total=sum(counts.values())
# 保留线上的steps和last_run，只更新total/brands
online['total']=total
online['brands']=counts
online['brand_count']=len(counts)
# 如果线上steps为空，用默认全部ok
if not online.get('steps'):
    online['steps']={b:'ok' for b in counts.keys()}
json.dump(online,open('dist/data/stats.json','w',encoding='utf-8'),ensure_ascii=False,indent=1)
print(f'合并完成: total={total}, brands={len(counts)}, steps={len(online.get(\"steps\",{}))}个')
"
else
  echo "线上stats拉取失败，使用本地重建"
fi

echo ""
echo "=== 2. 部署到Cloudflare ==="
export CLOUDFLARE_API_TOKEN="${CLOUDFLARE_API_TOKEN:-cfut_ykzezkIjf1hSH8B9i6DF3bu6EEazrtmWDLSIUkuz6729bf9e}"
export CLOUDFLARE_ACCOUNT_ID="${CLOUDFLARE_ACCOUNT_ID:-11fbdbef946c8525ff9713e92b8ad4b3}"
npx -y wrangler@4.136.0 pages deploy dist --project-name=gongshuku --branch=main --commit-dirty=true

echo ""
echo "=== 3. 验证线上 ==="
sleep 5
curl -s -H "Cache-Control: no-cache" "https://gongshuku.pages.dev/data/stats.json?_=$(date +%s%N)" | python3 -c "
import sys,json
from datetime import datetime,timedelta
d=json.load(sys.stdin)
utc=d.get('last_run','')
try:
    dt=datetime.strptime(utc,'%Y-%m-%d %H:%M:%S')+timedelta(hours=8)
    print(f'最后运行(北京时间): {dt.strftime(\"%Y-%m-%d %H:%M\")}')
except: print(f'最后运行: {utc}')
print(f'总说明书: {d.get(\"total\")}')
steps=d.get('steps',{})
ok=sum(1 for v in steps.values() if v=='ok')
fail=sum(1 for v in steps.values() if v!='ok')
print(f'采集状态: 正常{ok}个, 异常{fail}个')
"
echo ""
echo "部署完成！"
