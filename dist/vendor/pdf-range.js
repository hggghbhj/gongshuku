// 工书库 PDF 分块加载：强制 PDF.js 从第一个字节起用 Range，并主动并行预取，
// 消除慢网络下「一块请求等一块」的串行往返延迟。reader.html / viewer.html 共用。
//
// 关键：预取只下载并缓存 ArrayBuffer，绝不提前 onDataRange；
// 必须等 PDF.js 调用 requestDataRange(begin,end) 后，再把对应数据 onDataRange 给它，
// 否则 PDF.js 会丢弃「未请求就到达」的数据而永久等待。
(function(){
  const RANGE_CHUNK = 262144;   // 256KB
  const INIT_PREFETCH = 8;      // 首块就绪后，并行预取接下来 8 块（覆盖前约 2.25MB）
  const SLIDE_AHEAD = 4;        // 每按需请求一块，把窗口向前推 4 块
  const MAX_CONCURRENCY = 8;

  function fetchChunk(url, begin, end){
    return fetch(url, { headers: { 'Range': 'bytes=' + begin + '-' + (end - 1) } }).then(function(r){
      if(!r.ok && r.status !== 206) throw new Error('chunk ' + r.status);
      return r.arrayBuffer();
    });
  }

  function makeRangeTransport(pdfjsLib, url){
    return new Promise(function(resolve, reject){
      let T = null;
      const abortCtl = new AbortController();
      fetch(url, { headers: { 'Range': 'bytes=0-' + (RANGE_CHUNK - 1) }, signal: abortCtl.signal }).then(function(r){
        if(r.status !== 206){ reject(new Error('no-range')); return; }
        const cr = r.headers.get('Content-Range') || '';
        const m = /\/(\d+)\s*$/.exec(cr);
        const total = m ? parseInt(m[1], 10) : -1;
        if(total < 0){ reject(new Error('no-length')); return; }

        const tailStart = Math.floor((total - 1) / RANGE_CHUNK) * RANGE_CHUNK;
        const tailEnd = total;
        const inflight = { n: 0 };
        const dataCache = {};   // key=begin_end -> Promise(ArrayBuffer)，只下载、不投递
        let aheadEnd = 0;
        let queue = null;

        // 仅下载并缓存（不 onDataRange）
        function downloadBlock(begin, end){
          const key = begin + '_' + end;
          if(dataCache[key]) return dataCache[key];
          inflight.n++;
          const p = fetchChunk(url, begin, end).then(function(ab){
            inflight.n--;
            return ab;
          }).catch(function(e){
            inflight.n--;
            // 一次性重试
            return fetchChunk(url, begin, end).catch(function(e2){ throw e2; });
          });
          dataCache[key] = p;
          return p;
        }

        // 并行预取 [fromBegin, untilBegin)
        function prefetchRange(fromBegin, untilBegin){
          let b = fromBegin;
          function pump(){
            while(b < untilBegin && inflight.n < MAX_CONCURRENCY){
              const begin = b;
              const end = Math.min(begin + RANGE_CHUNK, total);
              b = end;
              const key = begin + '_' + end;
              if(!dataCache[key]) downloadBlock(begin, end).catch(function(){});
            }
            if(b < untilBegin){ setTimeout(pump, 150); }
          }
          pump();
        }

        r.arrayBuffer().then(function(ab){
          const initial = new Uint8Array(ab);
          T = new pdfjsLib.PDFDataRangeTransport(total, initial);

          // 预取末块（XRef）
          if(tailStart > RANGE_CHUNK){
            downloadBlock(tailStart, tailEnd).catch(function(){});
          }
          // 前向并行预取
          aheadEnd = Math.min(RANGE_CHUNK * (1 + INIT_PREFETCH), tailStart > RANGE_CHUNK ? tailStart : total);
          prefetchRange(RANGE_CHUNK, aheadEnd);

          // PDF.js 真正请求某块时：确保已下载，然后把数据投递（仅投递它请求的范围）
          T.requestDataRange = function(begin, end){
            const key = begin + '_' + end;
            if(!dataCache[key]) downloadBlock(begin, end);
            // 滑动窗口：顺手预取后续块
            const wantEnd = Math.min(end + RANGE_CHUNK * SLIDE_AHEAD, total);
            if(wantEnd > aheadEnd){
              prefetchRange(aheadEnd, wantEnd);
              aheadEnd = wantEnd;
            }
            dataCache[key].then(function(data){
              try { T.onDataRange(begin, new Uint8Array(data)); } catch(e){}
            }).catch(function(e){
              if(T.onError){ try { T.onError(e); } catch(_){} }
            });
          };
          T.abort = function(){ try { abortCtl.abort(); } catch(e){} };
          T.transportReady();
          resolve(T);
        }).catch(reject);
      }).catch(reject);
    });
  }

  // 统一加载入口：优先 Range 传输，服务器不支持时回退普通 url 模式。
  async function getPdfTask(pdfjsLib, url, extra){
    const base = Object.assign({
      cMapUrl: 'vendor/cmaps/',
      cMapPacked: true,
      isEvalSupported: false,
      disableAutoFetch: false,
      disableStream: false,
      rangeChunkSize: RANGE_CHUNK
    }, extra || {});
    let transport = null;
    try { transport = await makeRangeTransport(pdfjsLib, url); } catch(e){ transport = null; }
    if(transport){
      return pdfjsLib.getDocument(Object.assign({ range: transport }, base));
    }
    return pdfjsLib.getDocument(Object.assign({ url: url, disableRange: false }, base));
  }

  window.GskRange = { RANGE_CHUNK: RANGE_CHUNK, makeRangeTransport: makeRangeTransport, getPdfTask: getPdfTask };
})();
