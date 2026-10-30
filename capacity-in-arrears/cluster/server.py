"""Test service for the cluster experiment. Standard library only.

One FIFO queue, one worker. Each request costs WORK_MS of CPU time. By default the
worker still does the work for a request whose client has gone (wasted work).
Environment:
  PORT         listen port (default 8080)
  WORK_MS      CPU milliseconds per request (default 100, so one core serves 10 req/s)
  START_DELAY  seconds to sleep before listening: emulates provisioning dead time
  MAX_QUEUE_S  admission bound: reject with 503 when the queue holds more than this many
               seconds of work (0 = no bound)
  DEADLINE_S   if > 0, skip queued requests older than this (deadline-aware service)
"""
import asyncio
import os
import time
from collections import deque

PORT = int(os.environ.get('PORT', '8080'))
WORK = float(os.environ.get('WORK_MS', '100')) / 1000.0
START_DELAY = float(os.environ.get('START_DELAY', '0'))
MAX_QUEUE_S = float(os.environ.get('MAX_QUEUE_S', '0'))
DEADLINE_S = float(os.environ.get('DEADLINE_S', '0'))
queue = deque()


def burn(seconds):
    end = time.process_time() + seconds
    while time.process_time() < end:
        pass


async def handle(reader, writer):
    try:
        await reader.readuntil(b'\r\n\r\n')
        if MAX_QUEUE_S > 0 and len(queue) * WORK > MAX_QUEUE_S:
            writer.write(b'HTTP/1.0 503 Busy\r\nContent-Length: 0\r\n\r\n')
        else:
            done = asyncio.get_running_loop().create_future()
            queue.append((time.monotonic(), done))
            await done
            writer.write(b'HTTP/1.0 200 OK\r\nContent-Length: 2\r\n\r\nok')
        await writer.drain()
    except Exception:
        pass
    finally:
        try:
            writer.close()
        except Exception:
            pass


async def worker():
    while True:
        if not queue:
            await asyncio.sleep(0.002)
            continue
        arrived, done = queue.popleft()
        if not (DEADLINE_S > 0 and time.monotonic() - arrived > DEADLINE_S):
            burn(WORK)
        if not done.done():
            done.set_result(None)
        await asyncio.sleep(0)


async def main():
    if START_DELAY > 0:
        time.sleep(START_DELAY)
    server = await asyncio.start_server(handle, '0.0.0.0', PORT, backlog=8192)
    asyncio.get_running_loop().create_task(worker())
    async with server:
        await server.serve_forever()

if __name__ == '__main__':
    asyncio.run(main())
