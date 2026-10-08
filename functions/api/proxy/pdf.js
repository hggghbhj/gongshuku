// 代理需要Referer的PDF链接
export async function onRequestGet({ request }) {
  const url = new URL(request.url);
  const target = url.searchParams.get('url');
  if (!target) return new Response('Missing url', { status: 400 });

  // 安全检查：只允许http/https
  if (!target.startsWith('http://') && !target.startsWith('https://')) {
    return new Response('Invalid url', { status: 400 });
  }

  try {
    const targetHost = new URL(target).hostname;
    const referer = new URL(target).origin + '/';

    const resp = await fetch(target, {
      headers: {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
        'Referer': referer,
        'Accept': 'application/pdf,*/*'
      },
      redirect: 'follow'
    });

    // 流式返回
    const headers = new Headers(resp.headers);
    headers.set('Access-Control-Allow-Origin', '*');
    headers.set('Cache-Control', 'public, max-age=3600');
    return new Response(resp.body, {
      status: resp.status,
      headers
    });
  } catch (e) {
    return new Response('Fetch error: ' + e.message, { status: 502 });
  }
}
