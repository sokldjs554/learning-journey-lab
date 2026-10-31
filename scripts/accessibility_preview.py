"""Loopback-only preview with one deliberate response failure; never edits data."""
import argparse
import http.server
from pathlib import Path
import threading
from urllib.parse import urlsplit
ROOT=Path(__file__).resolve().parents[1]
ASSETS=('report.json','ednet_report.json','experiment-readiness.json')

def handler_for(web_root,fault_asset):
    if fault_asset not in ASSETS:raise ValueError('Unknown fault asset')
    pending=True
    guard=threading.Lock()
    class Preview(http.server.SimpleHTTPRequestHandler):
        def __init__(self,*args,**kwargs):super().__init__(*args,directory=str(web_root),**kwargs)
        def do_GET(self):
            nonlocal pending
            with guard:
                fail=pending and urlsplit(self.path).path=='/data/'+fault_asset
                if fail:pending=False
            if fail:
                self.send_response(503);self.send_header('Content-Type','text/plain; charset=utf-8');self.send_header('Cache-Control','no-store');self.end_headers();self.wfile.write(b'Deliberate local accessibility test failure; retry loads the unchanged file.');return
            super().do_GET()
        def end_headers(self):
            self.send_header('Cache-Control','no-store')
            super().end_headers()
    return Preview

def main():
    parser=argparse.ArgumentParser(description='실제 화면 읽기 도구로 오류 안내·재시도를 확인하는 로컬 전용 서버')
    parser.add_argument('--fault-once',choices=ASSETS,default='report.json')
    parser.add_argument('--port',type=int,default=8767)
    args=parser.parse_args()
    server=http.server.ThreadingHTTPServer(('127.0.0.1',args.port),handler_for(ROOT/'web',args.fault_once))
    print(f'로컬 검사: http://127.0.0.1:{server.server_port} / {args.fault_once} 첫 요청만 의도적으로 실패. 파일 수정 없음. 종료: Ctrl+C',flush=True)
    try:server.serve_forever()
    except KeyboardInterrupt:pass
    finally:server.server_close()
if __name__=='__main__':main()
