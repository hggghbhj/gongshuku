// 工书库「访问驱动」边缘自检（不依赖 Cloudflare Cron Trigger 权限）。
// 由站点页面在访客打开时异步 ping 一次；用边缘缓存锁节流：同一节点每小时最多真正检查一次。
// 检查在后台 ctx.waitUntil 执行，不阻塞访问者；最近一次结果缓存 1 小时供查询。
// 支持 ?force=1 强制立即跑一次；GET / POST / OPTIONS 均可。
const LOCK_KEY = 'https://gsk-health.local/lock';
const RESULT_KEY = 'https://gsk-health.local/result';
const TTL = 3600;

async function runFullHealth(origin, full){
  const r = await fetch(origin + '/api/health' + (full ? '?full=1' : ''), {
    headers: { 'Accept': 'application/json' },
    cf: { cacheTtl: 0, cacheEverything: false }
  });
  const d = await r.json();
  const badItems = (d.pdfChecks.items || []).filter(x => !x.ok);
  // 按完整 PDF URL 标记坏链，供首页 BAD_URLS 把异常链接排到后面
  const badUrls = {};
  for(const x of badItems){
    if(x.url) badUrls[x.url] = x.knownWaf ? '官网WAF拦截（已知限制）' : (x.status || x.error || '链接异常');
  }
  const result = {
    time: new Date().toISOString(),
    overall: d.overall,
    assetsOk: d.staticAssets.ok,
    pdfOk: d.pdfChecks.ok + '/' + d.pdfChecks.total,
    bad: badItems.map(x => {
      if(x.knownWaf) return x.brand + '（官网WAF，已知限制）';
      return x.brand + '(' + x.host + '):' + (x.status || x.error || '失败');
    }),
    badUrls: badUrls,
    durationMs: d.durationMs
  };
  console.log('[health] ' + JSON.stringify(result));
  return result;
}

async function handle({ request, waitUntil }){
  const url = new URL(request.url);
  const force = url.searchParams.has('force');
  const cache = caches.default;

  const prevResp = await cache.match(RESULT_KEY).catch(()=>null);
  let prev = null;
  if(prevResp){ prev = await prevResp.json().catch(()=>null); }

  const lock = await cache.match(LOCK_KEY).catch(()=>null);
  const isPost = request.method === 'POST';
  const sync = url.searchParams.has('sync');

  const doRun = async (full)=>{
    try{
      const result = await runFullHealth(url.origin, full);
      await cache.put(RESULT_KEY, new Response(JSON.stringify(result), {
        headers: { 'Content-Type':'application/json;charset=utf-8', 'Cache-Control':'public, max-age='+TTL }
      })).catch(()=>{});
      return result;
    }catch(e){
      console.log('[health] error ' + String(e && e.message || e));
      return { error: String(e && e.message || e) };
    }
  };

  // 同步模式：前台跑完完整检查并返回（手动查看/诊断用，约 7-10 秒）
  if(sync){
    const result = await doRun(true);
    await cache.put(LOCK_KEY, new Response('1', {
      headers: { 'Content-Type':'text/plain', 'Cache-Control':'public, max-age='+TTL }
    })).catch(()=>{});
    return new Response(JSON.stringify({service:'gongshuku', mode:'sync', result}, null, 2), {
      headers: { 'Content-Type':'application/json;charset=utf-8', 'Cache-Control':'no-store', 'Access-Control-Allow-Origin':'*' }
    });
  }

  // 访问驱动（POST，由 sendBeacon 发出，浏览器发完即断开、不读响应）：
  // 立刻把「锁判断 + 检查 + 写结果」全部放入 waitUntil，响应瞬间返回；即使客户端断开，后台也会跑完。
  if(isPost){
    const needRun = force || !lock;
    if(needRun){
      waitUntil((async ()=>{
        try{
          await cache.put(LOCK_KEY, new Response('1', {
            headers: { 'Content-Type':'text/plain', 'Cache-Control':'public, max-age='+TTL }
          })).catch(()=>{});
          await doRun(false);
        }catch(e){ console.log('[health] post-bg error ' + String(e && e.message || e)); }
      })());
    }
    return new Response(JSON.stringify({service:'gongshuku', triggered:needRun, accepted:true}, null, 2), {
      headers: { 'Content-Type':'application/json;charset=utf-8', 'Cache-Control':'no-store', 'Access-Control-Allow-Origin':'*' }
    });
  }

  // GET 手动查看：返回最近结果；锁过期时后台触发（不阻塞）
  let triggered = false;
  if(force || !lock){
    await cache.put(LOCK_KEY, new Response('1', {
      headers: { 'Content-Type':'text/plain', 'Cache-Control':'public, max-age='+TTL }
    })).catch(()=>{});
    triggered = true;
    waitUntil(doRun(true));
  }

  const out = {
    service: 'gongshuku',
    triggered: triggered,
    note: triggered ? '已在后台启动本轮检查，稍后再查可见新结果' : '本节点一小时内已检查，返回最近结果',
    lastResult: prev,
    tip: '手动立即检查可访问 /api/cron-health?sync=1'
  };
  return new Response(JSON.stringify(out, null, 2), {
    headers: { 'Content-Type':'application/json;charset=utf-8', 'Cache-Control':'no-store', 'Access-Control-Allow-Origin':'*' }
  });
}

export async function onRequestGet(args){ return handle(args); }
export async function onRequestPost(args){ return handle(args); }
export async function onRequestOptions(){
  return new Response(null, { status:204, headers:{
    'Access-Control-Allow-Origin':'*','Access-Control-Allow-Methods':'GET,POST,OPTIONS','Access-Control-Max-Age':'86400'
  }});
}
