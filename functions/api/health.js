// 工书库云端健康自检：访问 /api/health 立即检查所有核心组件
// ?full=1 检查全部域名（默认只检查静态资源+核心域名）
// 走代理的域名通过 /api/pdf 真实链路检查（与用户预览路径一致）；直连域名直接检查。
const DIRECT_HOSTS = ['gongkong.com','gongkong.tv','danfoss.com','amsamotion.com'];
const SAMPLES = [
  {host:'uploadfile.gongkong.com',brand:'三菱电机',url:'https://uploadfile.gongkong.com/Upload/gongkong/technicalDataAttachment/202609/20/63982badf077489c87365e4e90f649d8.pdf'},
  {host:'assets.danfoss.com',brand:'丹佛斯',url:'https://assets.danfoss.com/documents/197727/AN00008642701001-000102.pdf'},
  {host:'www.invt.com',brand:'英威腾',url:'https://www.invt.com/uploads/file1/20260907/IMS21B-A%20Manual_Frame%20Sizes%20200-263_EN_V1.0.pdf'},
  {host:'mp4.gongkong.com',brand:'爱里富',url:'https://mp4.gongkong.com/2026/file/alif-2026080700003.pdf'},
  {host:'sc19.gongkong.com',brand:'大恒图像',url:'https://sc19.gongkong.com/Upload/gongkong/technicalDataAttachment/202203/02/792b015e64a943eeb8165d3ab0ac2491.pdf'},
  {host:'download.gongkong.com',brand:'金蝶',url:'https://download.gongkong.com/fsfiles/technicalData/201706/2017060714022000001.pdf'},
  {host:'fs.gongkong.com',brand:'滨特尔',url:'https://fs.gongkong.com/files/technicalData/201308/2013080818023200002.pdf'},
  {host:'oss.amsamotion.com',brand:'艾莫迅',url:'https://oss.amsamotion.com/uploads/USB-LORA产品手册-VER1.3-260912.pdf'},
  {host:'jngbdz.com',brand:'工贝电子',url:'https://jngbdz.com/file/PLC_1200/【工贝电子】工贝1200信号板和扩展模块用户手册.pdf'},
  {host:'www.e-elitech.com',brand:'精创',url:'https://www.e-elitech.com/uploadfile/2022/07/05/202207052256144iePZF.pdf'},
  {host:'dl.e-elitech.com',brand:'精创电气(镜像)',url:'https://www.e-elitech.com/uploadfile/2020/10/23/202010230913442SRZy8.pdf'},
  {host:'cdn.xinje.com',brand:'信捷电气',url:'https://cdn.xinje.com/XS系列PLCopen标准控制器用户手册【软件篇】（XS Studio）（PS06 20260918 1.8）-2026.9.18.pdf'},
  {host:'www.leisai.com',brand:'雷赛智能',url:'https://www.leisai.com/upload/file/2026/06/15/雷赛智能简介2026.pdf'},
  {host:'zxdq.oss-cn-shenzhen.aliyuncs.com',brand:'正弦电气',url:'https://zxdq.oss-cn-shenzhen.aliyuncs.com/Upload/pdf/202508/31010310-ES760_SC.pdf'},
  {host:'website.hcfa.cc',brand:'禾川科技',url:'https://website.hcfa.cc:20080/upload/%E4%BA%A7%E5%93%81%E4%B8%AD%E5%BF%83/%E7%89%B9%E6%AE%8A%E6%9C%BA%E5%9E%8B/%E8%A1%8C%E4%B8%9A%E5%AE%9A%E5%88%B6%E6%9C%BA/%E7%BA%BA%E7%BB%87%E8%A1%8C%E4%B8%9A/E630%E7%B3%BB%E5%88%97%E5%8F%98%E9%A2%91%E5%99%A8/E630%E7%B3%BB%E5%88%97%E7%BA%BA%E7%BB%87%E4%B8%93%E7%94%A8%E8%B6%85%E5%90%AF%E5%8A%A8%E5%8F%98%E9%A2%91%E5%99%A8%E5%AE%89%E8%A3%85%E4%BD%BF%E7%94%A8%E8%AF%B4%E6%98%8E%E4%B9%A6V1.0%20%E4%B8%AD%E8%8B%B1%E6%96%87.pdf'},
  {host:'jtdrive.com',brand:'金田科技(WAF)',url:'http://jtdrive.com/wp-content/uploads/2025/12/930E%E8%AF%B4%E6%98%8E%E4%B9%A6-V1.0.pdf'},
  {host:'www.coolmay.com',brand:'顾美科技',url:'http://www.coolmay.com/uploads/files/20241210/729ad44dbd4feca7da24d36979703fbe.pdf'}
];

function isDirect(host){
  return DIRECT_HOSTS.some(d => host===d || host.endsWith('.'+d));
}

// 只拉前 2KB 验证 PDF 头
async function checkOnce(targetUrl, timeoutMs){
  const start = Date.now();
  const ctrl = new AbortController();
  const timer = setTimeout(()=>ctrl.abort(), timeoutMs);
  try{
    const r = await fetch(targetUrl, {
      headers: {'Accept':'application/pdf,*/*','Range':'bytes=0-2047'},
      redirect:'follow', signal: ctrl.signal
    });
    clearTimeout(timer);
    if(r.status!==200 && r.status!==206){
      return {ok:false, status:r.status, ms:Date.now()-start};
    }
    const buf = await r.arrayBuffer();
    const head = new Uint8Array(buf.slice(0,5));
    const isPdf = head[0]===0x25 && head[1]===0x50 && head[2]===0x44 && head[3]===0x46;
    return {ok:isPdf, status:r.status, bytes:buf.byteLength, ms:Date.now()-start};
  }catch(e){
    clearTimeout(timer);
    const aborted = e.name==='AbortError';
    return {ok:false, error: aborted?'timeout':String(e.message||e).slice(0,60), ms:Date.now()-start};
  }
}

async function checkPdf(sample, origin){
  const host = sample.host;
  const useProxy = !isDirect(host);
  const target = useProxy
    ? origin + '/api/pdf?u=' + encodeURIComponent(sample.url)
    : sample.url;
  // 金田官网有 WAF，简单代理难突破，单次短超时并标注 knownWaf，不拖累整体
  const knownWaf = host.includes('jtdrive');
  if(knownWaf){
    const r = await checkOnce(target, 7000);
    return {host, brand:sample.brand, url:sample.url, via: useProxy?'proxy':'direct', knownWaf:true, attempts:1, ...r};
  }
  // 普通样本：首次 9 秒，失败再快速重试 1 次（共 2 次），控制总预算在 ~16 秒
  let last = await checkOnce(target, 9000);
  if(last.ok){ last.attempts=1; last.via = useProxy?'proxy':'direct'; return {host, brand:sample.brand, url:sample.url, ...last}; }
  await new Promise(x=>setTimeout(x, 400));
  last = await checkOnce(target, 7000);
  last.attempts = 2;
  return {host, brand:sample.brand, url:sample.url, via: useProxy?'proxy':'direct', ...last};
}

async function checkAsset(url, base){
  const start = Date.now();
  try{
    const r = await fetch(new URL(url, base), {method:'GET'});
    return {ok:r.ok, status:r.status, bytes:r.headers.get('content-length')||'?', ms:Date.now()-start};
  }catch(e){
    return {ok:false, error:String(e.message||e).slice(0,50), ms:Date.now()-start};
  }
}

export async function onRequestGet({ request }){
  const url = new URL(request.url);
  const full = url.searchParams.has('full');
  const base = url.origin;
  const t0 = Date.now();

  // 1. 静态资源
  const assets = {};
  const assetList = [
    ['pdfjs','vendor/pdf.min.js'],
    ['pdfjsWorker','vendor/pdf.worker.min.js'],
    ['rangeLoader','vendor/pdf-range.js'],
    ['cmap_gb','vendor/cmaps/Adobe-GB1-UCS2.bcmap'],
    ['cmap_unigb','vendor/cmaps/UniGB-UCS2-H.bcmap'],
    ['reader','reader'],
    ['viewer','viewer'],
    ['sw','sw.js'],
  ];
  await Promise.all(assetList.map(async ([k,u])=>{
    assets[k] = await checkAsset(u, base);
  }));

  // 2. PDF 链接（默认只查核心域名，full=1 查全部）
  const coreHosts = ['gongkong','danfoss','e-elitech','xinje','leisai','invt','hcfa','jtdrive','coolmay','sinee','amsamotion','jngbdz'];
  const targets = full ? SAMPLES : SAMPLES.filter(s=>coreHosts.some(c=>s.host.includes(c)));

  const pdfResults = await Promise.all(targets.map(s=>checkPdf(s, base)));

  const assetOk = Object.values(assets).every(a=>a.ok);
  const pdfOk = pdfResults.filter(r=>r.ok).length;
  const pdfBad = pdfResults.filter(r=>!r.ok);

  // 金田 WAF 是已知限制，单独标注不算"严重故障"
  const hardBad = pdfBad.filter(r=>!r.host.includes('jtdrive'));
  const result = {
    service:'gongshuku',
    time:new Date().toISOString(),
    mode: full?'full':'core',
    durationMs: Date.now()-t0,
    overall: assetOk && pdfBad.length===0 ? 'healthy'
      : (assetOk && hardBad.length===0 ? 'degraded'
      : (hardBad.length >= pdfResults.length/2 ? 'critical' : 'degraded')),
    staticAssets:{ok:assetOk, items:assets},
    pdfChecks:{ total:pdfResults.length, ok:pdfOk, bad:pdfBad.length, items:pdfResults },
  };

  const accept = request.headers.get('accept')||'';
  if(accept.includes('text/html')){
    const rows = pdfResults.map(r=>{
      let note;
      if(r.ok){ note=`✅ ${r.via==='proxy'?'代理':'直连'} ${r.attempts>1?'重试'+r.attempts+'次':''}`; }
      else if(r.knownWaf){ note='⚠️ 官网WAF拦截（已知限制，需特殊通道）'; }
      else { note=`❌ ${r.status||r.error||'失败'}`; }
      const cls = r.ok?'ok':(r.knownWaf?'warn':'bad');
      return `<tr class="${cls}"><td>${r.brand}</td><td>${r.host}</td><td>${note}</td><td>${r.ms}ms</td></tr>`;
    }).join('');
    const arows = Object.entries(assets).map(([k,v])=>
      `<tr class="${v.ok?'ok':'bad'}"><td>${k}</td><td>${v.ok?'✅':'❌'} ${v.status}</td><td>${v.ms}ms</td></tr>`
    ).join('');
    const color = result.overall==='healthy'?'#0f766e':(result.overall==='degraded'?'#d97706':'#dc2626');
    const html = `<!DOCTYPE html><html lang="zh-CN"><head><meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>工书库 · 云端自检</title>
<style>body{font-family:-apple-system,"Microsoft YaHei",sans-serif;margin:0;padding:16px;background:#f4f6f5;color:#15201e}
h1{font-size:20px}h2{font-size:16px;margin-top:24px}
.badge{display:inline-block;padding:6px 16px;border-radius:20px;color:#fff;font-weight:700;font-size:14px;background:${color}}
table{width:100%;border-collapse:collapse;background:#fff;border-radius:10px;overflow:hidden;font-size:13px}
th,td{padding:9px 10px;text-align:left;border-bottom:1px solid #eef2f1}
th{background:#eef3f2;font-size:12px}
tr.ok td:nth-child(3){color:#0f766e}tr.bad{background:#fef2f2}tr.bad td:nth-child(3){color:#dc2626}tr.warn{background:#fffbeb}tr.warn td:nth-child(3){color:#b45309}
.mut{color:#6b7b78;font-size:12px;margin-top:8px}
</style></head><body>
<h1>工书库云端自检</h1>
<span class="badge">${result.overall==='healthy'?'✅ 全部正常':result.overall==='degraded'?'⚠️ 部分异常（不影响多数品牌）':'❌ 严重故障'}</span>
<p class="mut">${result.time} · ${result.mode}模式 · 耗时 ${result.durationMs}ms · PDF 正常 ${pdfOk}/${pdfResults.length}
${full?' · <a href="/api/health">只看核心</a>':' · <a href="/api/health?full=1">检查全部域名</a>'}</p>
<h2>静态资源</h2><table><tr><th>组件</th><th>状态</th><th>耗时</th></tr>${arows}</table>
<h2>PDF 链接可用性（真实预览链路）</h2><table><tr><th>品牌</th><th>域名</th><th>状态</th><th>耗时</th></tr>${rows}</table>
<p class="mut">本自检在 Cloudflare 云端运行，无需人工操作；每个链接失败会自动重试 2 次。金田官网有 WAF 拦截属已知限制。</p>
</body></html>`;
    return new Response(html, {headers:{'Content-Type':'text/html;charset=utf-8','Cache-Control':'no-store'}});
  }

  return new Response(JSON.stringify(result,null,2), {
    headers:{'Content-Type':'application/json;charset=utf-8','Cache-Control':'no-store'}
  });
}
