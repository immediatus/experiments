"""Open-loop load generator with client timeouts and retries. Standard library only.

usage: loadgen.py HOST PORT --rate 20 --spike 10 --spike-start 30 --spike-len 60
                  --timeout 10 --retries 2 --duration 600 --out run.csv
Writes one CSV row per second: t, first attempts sent, all attempts sent, successes,
timeouts, rejections (503), requests given up. A retry is sent at once after a timeout
or a rejection, up to --retries times. With --meter HOST:PORT it also reports each second's
first attempts and attempts in all to the demand meter (meter.py), which KEDA reads.
"""
import argparse
import asyncio
import random
import time


async def attempt(host, port, timeout):
    try:
        reader, writer = await asyncio.wait_for(asyncio.open_connection(host, port), timeout)
    except Exception:
        return 'timeout'
    try:
        writer.write(b'GET / HTTP/1.0\r\n\r\n')
        line = await asyncio.wait_for(reader.readline(), timeout)
        return 'ok' if b' 200 ' in line else ('reject' if b' 503 ' in line else 'timeout')
    except Exception:
        return 'timeout'
    finally:
        try:
            writer.close()
        except Exception:
            pass


async def request(a, stats, t0):
    for n in range(a.retries + 1):
        sec = int(time.monotonic() - t0)
        row = stats.setdefault(sec, [0, 0, 0, 0, 0, 0])
        row[0] += n == 0
        row[1] += 1
        start = time.monotonic()
        res = await attempt(a.host, a.port, a.timeout)
        if res == 'timeout' and time.monotonic() - start < a.timeout:
            await asyncio.sleep(a.timeout - (time.monotonic() - start))
        row = stats.setdefault(int(time.monotonic() - t0), [0, 0, 0, 0, 0, 0])
        if res == 'ok':
            row[2] += 1
            return
        row[3 if res == 'timeout' else 4] += 1
    row[5] += 1


async def report(a, stats, t0):
    """Once a second, send the previous second's counts to the meter."""
    host, port = a.meter.split(':')
    sec = 1
    while time.monotonic() - t0 < a.duration:
        await asyncio.sleep(max(0.0, t0 + sec - time.monotonic()))
        row = stats.get(sec - 1, [0] * 6)
        try:
            reader, writer = await asyncio.wait_for(asyncio.open_connection(host, int(port)), 2)
            writer.write(b'GET /report?first=%d&all=%d HTTP/1.0\r\n\r\n' % (row[0], row[1]))
            await asyncio.wait_for(reader.read(), 2)
            writer.close()
        except Exception:
            pass
        sec += 1


async def main(a):
    rng = random.Random(a.seed)
    stats, t0, tasks = {}, time.monotonic(), set()
    if a.meter:
        asyncio.ensure_future(report(a, stats, t0))
    while True:
        now = time.monotonic() - t0
        if now >= a.duration:
            break
        rate = a.rate * (a.spike if a.spike_start <= now < a.spike_start + a.spike_len else 1.0)
        await asyncio.sleep(rng.expovariate(rate))
        t = asyncio.ensure_future(request(a, stats, t0))
        tasks.add(t)
        t.add_done_callback(tasks.discard)
    if tasks:
        await asyncio.wait(tasks, timeout=a.timeout * (a.retries + 1) + 1)
    with open(a.out, 'w', encoding='utf-8') as f:
        f.write('t,first,attempts,ok,timeouts,rejects,given_up\n')
        for s in range(int(a.duration) + 1):
            f.write('%d,%s\n' % (s, ','.join(str(int(x)) for x in stats.get(s, [0] * 6))))
    last_bad = max([s for s, r in stats.items() if r[3] or r[4]] or [-1])
    tot = [sum(r[i] for r in stats.values()) for i in range(6)]
    print('first=%d attempts=%d ok=%d timeouts=%d rejects=%d given_up=%d last_timeout_or_reject_at=%ds' % (*tot, last_bad))

if __name__ == '__main__':
    p = argparse.ArgumentParser()
    p.add_argument('host')
    p.add_argument('port', type=int)
    p.add_argument('--rate', type=float, default=20.0)
    p.add_argument('--spike', type=float, default=1.0)
    p.add_argument('--spike-start', type=float, default=30.0)
    p.add_argument('--spike-len', type=float, default=60.0)
    p.add_argument('--timeout', type=float, default=10.0)
    p.add_argument('--retries', type=int, default=2)
    p.add_argument('--duration', type=float, default=600.0)
    p.add_argument('--seed', type=int, default=1)
    p.add_argument('--out', default='run.csv')
    p.add_argument('--meter', default='', help='HOST:PORT of meter.py; empty means no reports')
    asyncio.run(main(p.parse_args()))
