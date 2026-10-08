import http.server,socketserver,os,urllib.parse,threading
DST="/home/user/Doubao/chats/38443037035314434/gsk-crawl/pdfs/jintian"
os.makedirs(DST,exist_ok=True)
LOG="/home/user/Doubao/chats/38443037035314434/gsk-crawl/receiver.log"
class H(http.server.BaseHTTPRequestHandler):
    def log_message(self,*a):pass
    def do_GET(self):
        self.send_response(200);self.send_header("Access-Control-Allow-Origin","*");self.end_headers()
        self.wfile.write(b"ok")
    def do_POST(self):
        q=urllib.parse.urlparse(self.path)
        p=urllib.parse.parse_qs(q.query)
        name=p.get("name",["x.pdf"])[0]
        n=int(self.headers.get("Content-Length",0))
        data=self.rfile.read(n)
        if not name.startswith("jt_") or not name.endswith(".pdf") or len(name)>16:
            self.send_response(400);self.end_headers();return
        fp=os.path.join(DST,name)
        if data[:4]!=b"%PDF":
            self.send_response(422);self.send_header("Access-Control-Allow-Origin","*");self.end_headers()
            self.wfile.write(b"not pdf");return
        with open(fp,"wb") as f:f.write(data)
        self.send_response(200);self.send_header("Access-Control-Allow-Origin","*");self.end_headers()
        self.wfile.write(("saved %d"%len(data)).encode())
        with open(LOG,"a") as l:l.write("%s %d\n"%(name,len(data)))
    def do_OPTIONS(self):
        self.send_response(200)
        self.send_header("Access-Control-Allow-Origin","*")
        self.send_header("Access-Control-Allow-Methods","GET,POST,OPTIONS")
        self.send_header("Access-Control-Allow-Headers","*");self.end_headers()
class TS(socketserver.ThreadingMixIn,socketserver.TCPServer):
    allow_reuse_address=True;daemon_threads=True
TS(("127.0.0.1",8899),H).serve_forever()
