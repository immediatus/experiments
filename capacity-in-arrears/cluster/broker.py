"""Message broker for the queue-consumer runs (Part 2). Standard library only.

Holds a backlog of identical messages. Demand is generated here, so the arrival schedule
does not depend on any client: RATE0 messages a second until STEP_AT seconds after start,
then RATE1. Arrivals are added every 0.1 s.
  GET /take?n=K   removes up to K messages and returns how many it removed
  GET /metrics    returns {"backlog": L, "t": seconds since start}; KEDA's metrics-api
                  scaler reads "backlog" as an AverageValue metric, so the HPA asks for
                  ceil(L / threshold) replicas, the external per-pod path of the post
Environment: PORT (default 8090), RATE0 (50), RATE1 (200), STEP_AT (600), START_BACKLOG
(messages present at start; default 0).
"""
import json
import os
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs, urlparse

PORT = int(os.environ.get('PORT', '8090'))
RATE0 = float(os.environ.get('RATE0', '50'))
RATE1 = float(os.environ.get('RATE1', '200'))
STEP_AT = float(os.environ.get('STEP_AT', '600'))
lock = threading.Lock()
state = {'backlog': float(os.environ.get('START_BACKLOG', '0')), 't0': time.monotonic()}


def produce():
    while True:
        time.sleep(0.1)
        t = time.monotonic() - state['t0']
        with lock:
            state['backlog'] += 0.1 * (RATE1 if t >= STEP_AT else RATE0)


class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        u = urlparse(self.path)
        if u.path == '/take':
            n = float(parse_qs(u.query).get('n', ['1'])[0])
            with lock:
                got = min(n, int(state['backlog']))
                state['backlog'] -= got
            body = str(int(got)).encode()
        elif u.path == '/metrics':
            with lock:
                body = json.dumps({'backlog': int(state['backlog']), 't': round(time.monotonic() - state['t0'])}).encode()
        else:
            self.send_response(404)
            self.end_headers()
            return
        self.send_response(200)
        self.send_header('Content-Length', str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, *args):
        pass


if __name__ == '__main__':
    threading.Thread(target=produce, daemon=True).start()
    ThreadingHTTPServer(('0.0.0.0', PORT), Handler).serve_forever()
