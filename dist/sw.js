/* 工书库 Service Worker：外壳离线缓存，数据分片 network-first；跨域 PDF 直链走网络。 */
const CACHE='gongshuku-v'+"20260923-1000";
const SHELL=['./index.html','./data/docs-1.js?v=20260923-1000','./data/docs-2.js?v=20260923-1000','./data/docs-3.js?v=20260923-1000','./manifest.webmanifest','./icon-192.png','./icon-512.png','./icon-maskable-192.png','./icon-maskable-512.png','./viewer.html','./reader.html','./vendor/pdf.min.js','./vendor/pdf.worker.min.js'];
self.addEventListener('install',function(e){
  e.waitUntil(caches.open(CACHE).then(function(c){return c.addAll(SHELL).catch(function(){return c.add('./index.html');});}).then(function(){return self.skipWaiting();}));
});
self.addEventListener('activate',function(e){
  e.waitUntil(caches.keys().then(function(ks){return Promise.all(ks.filter(function(k){return k!==CACHE;}).map(function(k){return caches.delete(k);}));}).then(function(){return self.clients.claim();}));
});
self.addEventListener('fetch',function(e){
  const req=e.request;if(req.method!=='GET')return;
  let u;try{u=new URL(req.url);}catch(err){return;}
  if(u.origin!==self.location.origin)return;
  if(u.pathname.indexOf('/api/')===0)return; // 云端接口（latest/tick/refresh）始终走网络，不缓存
  if(u.pathname.indexOf('/manuals/')===0)return; // 托管的 PDF 体积大，直接走网络不进 SW 缓存，避免占满手机存储
  if(u.pathname.indexOf('/data/')===0){
    // 数据分片：network-first，在线总是最新库（每3小时更新的关键），失败才回退缓存，离线可用
    e.respondWith(fetch(req).then(function(r){if(r&&r.status===200){const c=r.clone();caches.open(CACHE).then(function(x){x.put(req,c);}).catch(function(){});}return r;}).catch(function(){return caches.match(req);}));
    return;
  }
  if(req.mode==='navigate'){
    e.respondWith(fetch(req).then(function(r){const c=r.clone();caches.open(CACHE).then(function(x){x.put(req,c);}).catch(function(){});return r;}).catch(function(){return caches.match('./index.html');}));
    return;
  }
  e.respondWith(caches.match(req).then(function(hit){if(hit)return hit;
    return fetch(req).then(function(r){if(r&&r.status===200){const c=r.clone();caches.open(CACHE).then(function(x){x.put(req,c);}).catch(function(){});}return r;}).catch(function(){return hit;});
  }));
});
