"""Aggregator fal.ai — puluhan model video (Kling, Hailuo, Luma, Pika, Veo...)
via 1 key. Env: FAL_KEY, FAL_MODEL.
BELUM TERVERIFIKASI live (butuh key) — ditulis dari dokumentasi publik."""
from __future__ import annotations
import os
from vid_common import req_json, download, poll_until

def generate(name: str, visual: str, durasi: float, vertikal: bool, mp4: str) -> str:
    key = os.getenv("FAL_KEY", "").strip()
    if not key:
        raise RuntimeError("FAL_KEY kosong")
    model = os.getenv("FAL_MODEL",
                      "fal-ai/kling-video/v2.1/standard/text-to-video").strip()
    aspect = "9:16" if vertikal else "16:9"
    h = {"Authorization": f"Key {key}", "Content-Type": "application/json"}
    sub = req_json("POST", f"https://queue.fal.run/{model}", h,
                   {"prompt": visual[:1500], "aspect_ratio": aspect,
                    "duration": "10" if durasi > 7 else "5"})
    rid = sub.get("request_id")
    if not rid:
        raise RuntimeError(f"fal: tanpa request_id: {str(sub)[:120]}")
    status_url = f"https://queue.fal.run/{model}/requests/{rid}/status"
    state: dict = {}
    def done():
        state.update(req_json("GET", status_url, h))
        return state.get("status") in ("COMPLETED", "FAILED")
    poll_until(done)
    if state.get("status") != "COMPLETED":
        raise RuntimeError(f"fal gagal: {str(state)[:150]}")
    res = req_json("GET", f"https://queue.fal.run/{model}/requests/{rid}", h)
    vurl = (res.get("video") or {}).get("url")
    if not vurl:
        raise RuntimeError(f"fal: tanpa video url: {str(res)[:150]}")
    download(vurl, mp4)
    return mp4
