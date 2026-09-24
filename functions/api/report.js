// 工书库预览结果上报：reader/viewer 渲染成功/失败时 POST，不返回敏感信息，仅记录到函数日志。
export async function onRequestOptions(){
  return new Response(null, { status:204, headers:{
    'Access-Control-Allow-Origin':'*',
    'Access-Control-Allow-Methods':'POST,OPTIONS',
    'Access-Control-Allow-Headers':'Content-Type',
    'Access-Control-Max-Age':'86400'
  }});
}

export async function onRequestPost({ request }){
  try{
    const data = await request.json().catch(()=>({}));
    // 只记录非敏感字段：URL 的域名/路径、是否成功、原因、页数，不记录任何凭证
    const safe = {
      ok: !!data.ok,
      reason: data.reason || '',
      pages: data.pages || 0,
      brand: (data.brand||'').slice(0,40),
      title: (data.title||'').slice(0,80),
      host: (()=>{ try{ return new URL(data.url||'').hostname; }catch(e){ return ''; } })(),
      t: new Date().toISOString()
    };
    console.log('preview-report', JSON.stringify(safe));
    return new Response(JSON.stringify({logged:true}), {
      status:200, headers:{'Content-Type':'application/json','Access-Control-Allow-Origin':'*','Cache-Control':'no-store'}
    });
  }catch(e){
    return new Response('{"logged":false}', {
      status:200, headers:{'Content-Type':'application/json','Access-Control-Allow-Origin':'*','Cache-Control':'no-store'}
    });
  }
}

// 其它方法不处理
export async function onRequestGet(){
  return new Response('POST only', {status:405, headers:{'Allow':'POST,OPTIONS','Access-Control-Allow-Origin':'*'}});
}
