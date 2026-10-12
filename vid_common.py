"""Bersama untuk adapter video AI: HTTP JSON + unduh file. stdlib only."""
from __future__ import annotations
import json, time, urllib.request

def req_json(method: str, url: str, headers: dict, data: dict | None = None,
             timeout: int = 60) -> dict:
    req = urllib.request.Request(
        url, data=json.dumps(data).encode() if data is not None else None,
        headers=headers, method=method)
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.load(r)

def download(url: str, dest: str, timeout: int = 300):
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        body = r.read(200 * 1024 * 1024)
    if len(body) < 20_000:
        raise RuntimeError("unduhan video terlalu kecil / gagal")
    open(dest, "wb").write(body)

def poll_until(done_fn, timeout_s: int = 600, interval: int = 5):
    """Poll hingga done_fn() return True. Raise timeout."""
    t0 = time.time()
    while time.time() - t0 < timeout_s:
        if done_fn():
            return
        time.sleep(interval)
    raise RuntimeError("timeout menunggu video jadi")
