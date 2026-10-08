// 返回最近一次云端自检发现的坏链地图（供首页 BAD_URLS 把异常链接排到后面）。
// 结果来自 /api/cron-health 按边缘节点缓存的最近检查；无数据则返回空 map。
const RESULT_KEY = 'https://gsk-health.local/result';
const CORS = {
  'Content-Type': 'application/json;charset=utf-8',
  'Cache-Control': 'no-store',
  'Access-Control-Allow-Origin': '*'
};
export async function onRequestOptions(){
  return new Response(null, { status:204, headers:{
    'Access-Control-Allow-Origin':'*','Access-Control-Allow-Methods':'GET,OPTIONS','Access-Control-Max-Age':'86400'
  }});
}
export async function onRequestGet(){
  try{
    const cached = await caches.default.match(RESULT_KEY).catch(()=>null);
    let bad = {};
    let time = null;
    if(cached){
      const r = await cached.json().catch(()=>null);
      if(r){
        const all = r.badUrls || {};
        // 只标记确定坏链：官网 WAF（已知限制）或 4xx/5xx 状态码；
        // 单纯 timeout / 网络抖动多为上游预热或间歇慢，二次访问即恢复，不标记以免误伤正常链接。
        for(const [u, reason] of Object.entries(all)){
          const rs = String(reason);
          if(/WAF|40[0-9]|41[0-9]|42[0-9]|50[0-9]|51[0-9]|52[0-9]|notpdf|corrupt/.test(rs)){
            bad[u] = rs;
          }
        }
        time = r.time || null;
      }
    }
    return new Response(JSON.stringify({ bad, time, count: Object.keys(bad).length }), { headers: CORS });
  }catch(e){
    return new Response(JSON.stringify({ bad:{}, count:0 }), { headers: CORS });
  }
}
