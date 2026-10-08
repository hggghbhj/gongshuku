# -*- coding: utf-8 -*-
"""通用采集接收器：浏览器内 fetch 的 PDF 回传到本机。
POST /save?brand=<brand>&name=<file.pdf>  body=PDF bytes
幂等：已存在且 %PDF 头且大小一致则跳过。GET /health 健康检查。"""
import http.server,socketserver,os,urllib.parse,re
ROOT="/home/user/Doubao/chats/38443037035314434/gsk-crawl/pdfs"
LOG="/home/user/Doubao/chats/38443037035314434/gsk-crawl/receiver.log"
SAFE=re.compile(r"^[A-Za-z0-9_\-\.]+\.pdf$")
BRAND_SAFE=re.compile(r"^[A-Za-z0-9_\-]+$")
class H(http.server.BaseHTTPRequestHandler):
    def log_message(self,*a):pass
    def _cors(self):self.send_header("Access-Control-Allow-Origin","*")
    def do_GET(self):
        if self.path.startswith("/health"):
            self.send_response(200);self._cors();self.end_headers()
            self.wfile.write(b"ok");return
        self.send_response(404);self.end_headers()
    def do_POST(self):
        q=urllib.parse.urlparse(self.path)
        p=urllib.parse.parse_qs(q.query)
        brand=p.get("brand",["x"])[0]
        name=p.get("name",["x.pdf"])[0]
        if not BRAND_SAFE.match(brand) or not SAFE.match(name) or len(name)>60:
            self.send_response(400);self._cors();self.end_headers();self.wfile.write(b"bad name");return
        d=os.path.join(ROOT,brand);os.makedirs(d,exist_ok=True)
        n=int(self.headers.get("Content-Length",0))
        data=self.rfile.read(n)
        fp=os.path.join(d,name)
        if data[:4]!=b"%PDF":
            self.send_response(422);self._cors();self.end_headers();self.wfile.write(b"not pdf");return
        if os.path.exists(fp) and os.path.getsize(fp)==len(data):
            self.send_response(200);self._cors();self.end_headers();self.wfile.write(b"exists");return
        with open(fp,"wb") as f:f.write(data)
        self.send_response(200);self._cors();self.end_headers()
        self.wfile.write(("saved %d"%len(data)).encode())
        with open(LOG,"a") as l:l.write("%s/%s %d\n"%(brand,name,len(data)))
    def do_OPTIONS(self):
        self.send_response(200);self._cors()
        self.send_header("Access-Control-Allow-Methods","GET,POST,OPTIONS")
        self.send_header("Access-Control-Allow-Headers","*");self.end_headers()
class TS(socketserver.ThreadingMixIn,socketserver.TCPServer):
    allow_reuse_address=True;daemon_threads=True
TS(("127.0.0.1",8899),H).serve_forever()
