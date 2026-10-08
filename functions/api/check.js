// 轻量心跳：前端每 60 秒调用一次。fire-and-forget 触发 /api/cron-health（其内部按边缘节点节流为每小时一次）。
// 立即返回 204，不阻塞、不影响页面。
export async function onRequestOptions(){
  return new Response(null, { status:204, headers:{
    'Access-Control-Allow-Origin':'*','Access-Control-Allow-Methods':'GET,OPTIONS','Access-Control-Max-Age':'86400'
  }});
}
export async function onRequestGet({ request, waitUntil }){
  const origin = new URL(request.url).origin;
  try{
    if(waitUntil){
      waitUntil(fetch(origin + '/api/cron-health', { method:'POST' }).catch(()=>{}));
    }
  }catch(e){}
  return new Response(null, { status:204, headers:{
    'Cache-Control':'no-store',
    'Access-Control-Allow-Origin':'*'
  }});
}
