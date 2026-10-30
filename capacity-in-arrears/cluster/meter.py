"""Demand meter for the signal runs (Part 3, F3 and F4). Standard library only.

The load generator reports, once a second, how many first attempts and how many attempts
in all it sent: GET /report?first=N&all=M. KEDA's metrics-api scaler reads GET /metrics,
which returns {"first": r1, "ingress": r2}, each a per-second rate averaged over the last
WINDOW seconds (default 30, the averaging window of the loop model).
Environment: PORT (default 8081), WINDOW (default 30).
"""
import json
import os
import time
from collections import deque
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs, urlparse

PORT = int(os.environ.get('PORT', '8081'))
WINDOW = float(os.environ.get('WINDOW', '30'))
reports = deque()                                   # (time, first, all)


def rates(now):
    while reports and reports[0][0] < now - WINDOW:
        reports.popleft()
    return {'first': sum(r[1] for r in reports) / WINDOW, 'ingress': sum(r[2] for r in reports) / WINDOW}


class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        u = urlparse(self.path)
        if u.path == '/report':
            q = parse_qs(u.query)
            reports.append((time.monotonic(), float(q.get('first', ['0'])[0]), float(q.get('all', ['0'])[0])))
            body = b'ok'
        elif u.path == '/metrics':
            body = json.dumps(rates(time.monotonic())).encode()
        else:
            self.send_response(404)
            self.end_headers()
            return
        self.send_response(200)
        self.send_header('Content-Type', 'application/json')
        self.send_header('Content-Length', str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, *args):
        pass


if __name__ == '__main__':
    ThreadingHTTPServer(('0.0.0.0', PORT), Handler).serve_forever()
