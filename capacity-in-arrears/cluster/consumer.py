"""Queue consumer for the queue-consumer runs (Part 2). Standard library only.

Sleeps START_DELAY seconds, emulating the provisioning dead time, then takes RATE
messages from the broker once a second: a fixed per-pod rate c. A pod that is deleted
loses at most the batch it holds.
Environment: BROKER (default http://broker:8090), RATE (default 10), START_DELAY (default 90).
"""
import os
import time
import urllib.request

BROKER = os.environ.get('BROKER', 'http://broker:8090')
RATE = int(os.environ.get('RATE', '10'))
START_DELAY = float(os.environ.get('START_DELAY', '90'))

if __name__ == '__main__':
    time.sleep(START_DELAY)
    nxt = time.monotonic()
    while True:
        try:
            urllib.request.urlopen('%s/take?n=%d' % (BROKER, RATE), timeout=2).read()
        except Exception:
            pass
        nxt += 1.0
        time.sleep(max(0.0, nxt - time.monotonic()))
