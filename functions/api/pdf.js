// 工书库 PDF 代理：服务端请求官网 PDF（绕过浏览器 CORS / 注入 Referer / 支持 Range 分页）
// 用法：/api/pdf?u=<encodeURIComponent(官网PDF地址)>
// 策略：
//   - Range 请求：优先从边缘缓存切片（毫秒级）；未命中则直接转发上游 Range（只取所需块，秒回，不等完整文件），
//     同时后台异步预热完整 PDF 缓存，下次起全部命中。
//   - 完整 GET：命中缓存直接返回；未命中流式转发，后台写缓存。
//   - dl.e-elitech.com 自动镜像到 www.e-elitech.com；5xx 自动重试。
const REFERERS = {
  'xinje.com': 'https://www.xinje.com/web/downloadCenter/index',
  'sinee.cn': 'https://www.sinee.cn/',
  'zxdq.oss-cn-shenzhen.aliyuncs.com': 'https://www.sinee.cn/',
  'euradrives.com': 'https://www.euradrives.com/service/down.html',
  'hcfa.cn': 'https://www.hcfa.cn/',
  'hcfa.cc': 'https://www.hcfa.cn/',
  'coolmay.com': 'http://www.coolmay.com/',
  'e-elitech.com': 'https://www.e-elitech.com/',
  'leisai.com': 'https://www.leisai.com/downloads.html',
  'powtran.com': 'https://www.powtran.com/',
  'thefastfile.com': 'https://www.powtran.com/',
  'jtdrive.com': 'http://jtdrive.com/downs/sms',
  'invt.com.cn': 'https://www.invt.com.cn/dowload-15',
  'invt.com': 'https://www.invt.com.cn/dowload-15',
  'jngbdz.com': 'https://jngbdz.com/',
};
function refererFor(u){
  for(const k in REFERERS){ if(u.includes(k)) return REFERERS[k]; }
  try{ return new URL(u).origin+'/'; }catch(e){ return ''; }
}
const ALLOWED_HOST = /(dl\.e-elitech\.com|www\.e-elitech\.com|cdn\.xinje\.com|xinje\.com|sinee\.cn|zxdq\.oss-cn-shenzhen|euradrives\.com|hcfa\.cc|hcfa\.cn|coolmay\.com|leisai\.com|powtran\.com|thefastfile\.com|jtdrive\.com|invt\.com|jngbdz\.com|elitech)/i;
const MAX_CACHE_BYTES = 25 * 1024 * 1024;

// dl.e-elitech.com 与 www.e-elitech.com 完全镜像，前者在 Cloudflare 节点间歇 520，统一改写为 www
function normalizeUrl(u){
  return u.replace(/^https?:\/\/dl\.e-elitech\.com\//i, 'https://www.e-elitech.com/');
}

function corsHeaders(extra){
  const h = {
    'Access-Control-Allow-Origin': '*',
    'Access-Control-Allow-Methods': 'GET, HEAD, OPTIONS',
    'Access-Control-Allow-Headers': 'Range, If-Range, Content-Type, Accept',
    'Access-Control-Expose-Headers': 'Content-Length, Content-Range, Accept-Ranges, Content-Type, Last-Modified, ETag, X-Cache',
    'Access-Control-Max-Age': '86400',
  };
  if(extra) for(const k in extra) h[k]=extra[k];
  return h;
}
function baseReqHeaders(u){
  return {
    'User-Agent':'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0 Safari/537.36',
    'Referer': refererFor(u),
    'Accept':'application/pdf,*/*',
  };
}

export async function onRequestOptions(){
  return new Response(null, { status:204, headers: corsHeaders() });
}

async function fetchOnce(u, headers){
  return fetch(u, {headers, redirect:'follow'});
}
// 上游 fetch（5xx / Cloudflare 520/521/522/524 重试 + 备用域名）
async function fetchWithRetry(u, headers){
  const alts = [];
  // e-elitech 两个子域互为镜像，任一在 Cloudflare 节点间歇 520 时切换
  if(/^https:\/\/www\.e-elitech\.com\//.test(u)) alts.push(u.replace('https://www.e-elitech.com/','https://dl.e-elitech.com/'));
  if(/^https:\/\/dl\.e-elitech\.com\//.test(u)) alts.push(u.replace('https://dl.e-elitech.com/','https://www.e-elitech.com/'));
  const candidates = [u, ...alts];
  let lastErr=null;
  const delays=[200, 600, 1200];
  for(let i=0;i<candidates.length;i++){
    const target = candidates[i];
    const hh = {...headers};
    if(!hh['Referer'] && !hh.Referer) hh['Referer'] = refererFor(target);
    for(let attempt=0; attempt<3; attempt++){
      try{
        const r = await fetchOnce(target, hh);
        if(r.status < 500) return r;
        try{ r.body && r.body.cancel && r.body.cancel(); }catch(e){}
        if(attempt<2) await new Promise(x=>setTimeout(x, delays[attempt]||1000));
      }catch(e){
        lastErr=e;
        if(attempt<2) await new Promise(x=>setTimeout(x, delays[attempt]||800));
      }
    }
  }
  if(lastErr) throw lastErr;
  return new Response('upstream error', {status:502});
}

function parseRange(range, total){
  const m = /bytes=(\d*)-(\d*)/.exec(range||'');
  if(!m) return null;
  let start = m[1]==='' ? null : parseInt(m[1],10);
  let end = m[2]==='' ? null : parseInt(m[2],10);
  if(start===null){ const n=end||0; start=Math.max(0,total-n); end=total-1; }
  else if(end===null){ end=total-1; }
  end=Math.min(end,total-1);
  if(start>end || start<0) return null;
  return {start,end};
}
function buildSlice(buf, start, end, total){
  return new Response(buf.slice(start, end+1), {status:206, headers:corsHeaders({
    'Content-Type':'application/pdf',
    'Content-Length':String(end-start+1),
    'Content-Range':`bytes ${start}-${end}/${total}`,
    'Accept-Ranges':'bytes',
    'Cache-Control':'public, max-age=86400',
    'X-Cache':'HIT'
  })});
}

// 后台预热完整 PDF（不阻塞当前响应）；Module 级去重，避免并发块请求重复回源
const warming = new Set();
function warmFull(u, cache, fullKey){
  const id = String(u);
  if(warming.has(id)) return Promise.resolve();
  warming.add(id);
  return (async ()=>{
    try{
      const exists = await cache.match(fullKey).catch(()=>null);
      if(exists) return;
      const r = await fetchWithRetry(u, baseReqHeaders(u));
      if(!r.ok || r.status!==200) return;
      const buf = await r.arrayBuffer();
      if(!buf || buf.byteLength < 200 || buf.byteLength > MAX_CACHE_BYTES) return;
      const h = new Headers();
      h.set('Content-Type','application/pdf');
      h.set('Content-Length',String(buf.byteLength));
      h.set('Accept-Ranges','bytes');
      h.set('Cache-Control','public, max-age=86400');
      const etag=r.headers.get('etag'); if(etag) h.set('ETag',etag);
      const lm=r.headers.get('last-modified'); if(lm) h.set('Last-Modified',lm);
      await cache.put(fullKey, new Response(buf, {status:200, headers:h}));
    }catch(e){}
    finally{ warming.delete(id); }
  })();
}

async function handleGet({ request, waitUntil }){
  const u0 = new URL(request.url).searchParams.get('u');
  if(!u0) return new Response('missing u', {status:400, headers:corsHeaders({'Content-Type':'text/plain;charset=utf-8'})});
  if(!/^https?:\/\//.test(u0) || !ALLOWED_HOST.test(u0)) {
    return new Response('host not allowed', {status:403, headers:corsHeaders({'Content-Type':'text/plain;charset=utf-8'})});
  }
  const u = normalizeUrl(u0);
  const range = request.headers.get('range');
  const cache = caches.default;
  const fullKey = new Request('https://pdf-cache.local/'+u, {method:'GET'});

  // ---------- Range 请求 ----------
  if(range){
    // 1) 缓存命中：直接切片（毫秒级）
    const cached = await cache.match(fullKey).catch(()=>null);
    if(cached){
      const buf = await cached.arrayBuffer().catch(()=>null);
      if(buf){
        const total = buf.byteLength;
        const pr = parseRange(range, total);
        if(pr) return buildSlice(buf, pr.start, pr.end, total);
      }
    }
    // 2) 未命中：直接转发上游 Range，只取所需块（秒回，不等完整下载）
    const upH = baseReqHeaders(u);
    upH['Range'] = range;
    const ifRange = request.headers.get('if-range'); if(ifRange) upH['If-Range']=ifRange;
    const up = await fetchWithRetry(u, upH).catch(()=>null);
    if(up && (up.ok || up.status===206)){
      const h = corsHeaders({'Content-Type':'application/pdf','Accept-Ranges':'bytes','Cache-Control':'public, max-age=86400','X-Cache':'MISS'});
      for(const hn of ['content-length','content-range','last-modified','etag']){
        const v=up.headers.get(hn); if(v) h[hn.charAt(0).toUpperCase()+hn.slice(1)]=v;
      }
      // 不在此处后台预热完整文件：前端已并行预取所需 Range 块，完整下载会和 Range 争抢上游连接、拖慢慢网络首屏。
      // 完整缓存只在用户点「下载」（完整 GET）时建立。
      return new Response(up.body, {status:up.status, headers:h});
    }
    return new Response('upstream unavailable', {status:502, headers:corsHeaders({'Content-Type':'text/plain;charset=utf-8'})});
  }

  // ---------- 完整 GET ----------
  const cached = await cache.match(fullKey).catch(()=>null);
  if(cached){
    const h = new Headers(cached.headers);
    h.set('Access-Control-Allow-Origin','*');
    h.set('X-Cache','HIT');
    return new Response(cached.body, {status:200, headers:h});
  }
  const up = await fetchWithRetry(u, baseReqHeaders(u));
  if(!(up.ok || up.status===206)){
    return new Response('upstream '+up.status, {status:up.status, headers:corsHeaders({'Content-Type':'text/plain;charset=utf-8'})});
  }
  const h = corsHeaders({'Content-Type':'application/pdf','Accept-Ranges':'bytes','Cache-Control':'public, max-age=86400','X-Cache':'MISS'});
  for(const hn of ['content-length','last-modified','etag']){
    const v=up.headers.get(hn); if(v) h[hn.charAt(0).toUpperCase()+hn.slice(1)]=v;
  }
  // 后台写缓存（小/中文件），不阻塞流式响应
  if(waitUntil){
    waitUntil((async()=>{
      try{
        const buf = await up.clone().arrayBuffer();
        if(buf.byteLength>=200 && buf.byteLength<=MAX_CACHE_BYTES){
          const hh=new Headers();
          hh.set('Content-Type','application/pdf');
          hh.set('Content-Length',String(buf.byteLength));
          hh.set('Accept-Ranges','bytes');
          hh.set('Cache-Control','public, max-age=86400');
          await cache.put(fullKey, new Response(buf,{status:200,headers:hh}));
        }
      }catch(e){}
    })());
  }
  return new Response(up.body, {status:200, headers:h});
}

export async function onRequestHead({ request }){
  const u0 = new URL(request.url).searchParams.get('u');
  if(!u0) return new Response(null, {status:400, headers:corsHeaders()});
  if(!/^https?:\/\//.test(u0) || !ALLOWED_HOST.test(u0)){
    return new Response(null, {status:403, headers:corsHeaders()});
  }
  const u = normalizeUrl(u0);
  try {
    const up = await fetchWithRetry(u, {...baseReqHeaders(u)});
    const h = corsHeaders({'Content-Type':'application/pdf','Accept-Ranges':'bytes'});
    const cl = up.headers.get('content-length'); if(cl) h['Content-Length']=cl;
    return new Response(null, {status:up.status, headers:h});
  }catch(e){
    return new Response(null, {status:502, headers:corsHeaders()});
  }
}

export async function onRequestGet(arg){
  try { return await handleGet(arg); }
  catch(e) {
    return new Response('proxy error: '+String(e&&e.message||e), {
      status:502, headers:corsHeaders({'Content-Type':'text/plain;charset=utf-8'})
    });
  }
}
