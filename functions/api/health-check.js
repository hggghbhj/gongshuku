// 工书库 PDF 健康检测 API
// 用法：/api/health-check?mode=fast
// 定时触发：cron-job.org 每小时访问此URL
// 结果存储在 caches.default，网页从 /data/health_report.json 读取

const CACHE_KEY = 'https://health-cache.local/report';

async function getDocsList() {
  // 从 docs-3.js 提取PDF列表
  try {
    const resp = await fetch('https://gongshuku.pages.dev/data/docs-3.js');
    const text = await resp.text();
    // 提取 JSON 数组
    const start = text.indexOf('[');
    const end = text.lastIndexOf(']');
    const json = text.slice(start, end + 1);
    return JSON.parse(json);
  } catch (e) {
    return [];
  }
}

function refererFor(u) {
  const referers = {
    'xinje.com': 'https://www.xinje.com/web/downloadCenter/index',
    'sinee.cn': 'https://www.sinee.cn/',
    'euradrives.com': 'https://www.euradrives.com/service/down.html',
    'hcfa.cn': 'https://www.hcfa.cn/',
    'coolmay.com': 'http://www.coolmay.com/',
    'e-elitech.com': 'https://www.e-elitech.com/',
    'leisai.com': 'https://www.leisai.com/downloads.html',
    'powtran.com': 'https://www.powtran.com/',
    'jtdrive.com': 'http://jtdrive.com/downs/sms',
    'invt.com.cn': 'https://www.invt.com.cn/dowload-15',
    'mitsubishielectric.com': 'https://www.mitsubishielectric.com/fa/download/',
    'siemens.com.cn': 'https://www.ad.siemens.com.cn/download/',
    'aliyuncs.com': 'https://www.ad.siemens.com.cn/download/',
    'siglent.com': 'https://www.siglent.com/',
  };
  for (const k in referers) {
    if (u.includes(k)) return referers[k];
  }
  try { return new URL(u).origin + '/'; } catch (e) { return ''; }
}

async function checkPdf(url) {
  try {
    const resp = await fetch(url, {
      method: 'HEAD',
      headers: {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
        'Referer': refererFor(url),
      },
      redirect: 'follow',
      signal: AbortSignal.timeout(8000),
    });
    return { ok: resp.ok || resp.status === 200, status: resp.status };
  } catch (e) {
    return { ok: false, error: e.message };
  }
}

export async function onRequestGet({ request }) {
  const url = new URL(request.url);
  const mode = url.searchParams.get('mode') || 'fast';
  
  // 快速模式：每个品牌抽2份检测
  // 完整模式：检测所有PDF（太慢，不推荐）
  
  const docs = await getDocsList();
  if (!docs.length) {
    return new Response(JSON.stringify({ error: 'no docs' }), {
      status: 500,
      headers: { 'Content-Type': 'application/json' },
    });
  }
  
  // 按品牌分组，每个品牌抽2份
  const brands = {};
  for (const d of docs) {
    const b = d.b || '未知';
    if (!brands[b]) brands[b] = [];
    if (brands[b].length < 2 && d.pdf) {
      brands[b].push(d.pdf);
    }
  }
  
  const samples = Object.values(brands).flat();
  let ok = 0;
  let fail = 0;
  const badBrands = {};
  
  // 并发检测，每批10个
  const batchSize = 10;
  for (let i = 0; i < samples.length; i += batchSize) {
    const batch = samples.slice(i, i + batchSize);
    const results = await Promise.all(batch.map(url => checkPdf(url)));
    for (let j = 0; j < results.length; j++) {
      if (results[j].ok) {
        ok++;
      } else {
        fail++;
        // 找到对应的品牌
        const doc = docs.find(d => d.pdf === batch[j]);
        if (doc) {
          const b = doc.b || '未知';
          badBrands[b] = (badBrands[b] || 0) + 1;
        }
      }
    }
  }
  
  const report = {
    scan_time: new Date().toISOString().replace('T', ' ').slice(0, 19),
    total: docs.length,
    ok: docs.length - fail,
    fail: fail,
    sample_checked: samples.length,
    bad_by_brand: badBrands,
    note: `快速抽样检测（每品牌2份，共${samples.length}份）`,
  };
  
  // 存储到缓存
  const cache = caches.default;
  await cache.put(CACHE_KEY, new Response(JSON.stringify(report), {
    headers: { 'Content-Type': 'application/json', 'Cache-Control': 'public, max-age=3600' },
  }));
  
  return new Response(JSON.stringify(report, null, 2), {
    headers: { 'Content-Type': 'application/json; charset=utf-8' },
  });
}
