import importlib.util
from pathlib import Path
import threading
from urllib.error import HTTPError
from urllib.request import urlopen
import http.server

def test_fault_is_one_response_and_never_changes_files(tmp_path):
    from scripts.accessibility_preview import handler_for
    (tmp_path/'data').mkdir();source=tmp_path/'data/report.json';source.write_text('{"fixed":true}')
    (tmp_path/'index.html').write_text('<main>test</main>')
    server=http.server.ThreadingHTTPServer(('127.0.0.1',0),handler_for(tmp_path,'report.json'))
    threading.Thread(target=server.serve_forever,daemon=True).start()
    base=f'http://127.0.0.1:{server.server_port}'
    try:
        assert urlopen(base+'/').status==200
        try:urlopen(base+'/data/report.json?first=1')
        except HTTPError as e:assert e.code==503
        else:raise AssertionError('Expected injected failure')
        assert urlopen(base+'/data/report.json').read()==b'{"fixed":true}'
        assert source.read_text()=='{"fixed":true}'
    finally:server.shutdown();server.server_close()
