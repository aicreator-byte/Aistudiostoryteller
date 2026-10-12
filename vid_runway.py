"""Langsung: Runway video. Env: RUNWAY_API_KEY, RUNWAY_MODEL.
BELUM TERVERIFIKASI live (butuh key) — ditulis dari dokumentasi publik."""
from __future__ import annotations
import os
from vid_common import req_json, download, poll_until

def generate(name: str, visual: str, durasi: float, vertikal: bool, mp4: str) -> str:
    key = os.getenv("RUNWAY_API_KEY", "").strip()
    if not key:
        raise RuntimeError("RUNWAY_API_KEY kosong")
    model = os.getenv("RUNWAY_MODEL", "gen4_turbo").strip()
    ratio = "720:1280" if vertikal else "1280:720"
    h = {"Authorization": f"Bearer {key}", "Content-Type": "application/json",
         "X-Runway-Version": "2024-11-06"}
    sub = req_json("POST", "https://api.dev.runwayml.com/v1/text_to_video", h,
                   {"model": model, "promptText": visual[:1000],
                    "ratio": ratio, "duration": 10 if durasi > 7 else 5})
    tid = sub.get("id")
    if not tid:
        raise RuntimeError(f"runway: tanpa task id: {str(sub)[:150]}")
    state: dict = {}
    def done():
        state.update(req_json("GET", f"https://api.dev.runwayml.com/v1/tasks/{tid}", h))
        return state.get("status") in ("SUCCEEDED", "FAILED")
    poll_until(done, timeout_s=900)
    if state.get("status") != "SUCCEEDED":
        raise RuntimeError(f"runway gagal: {str(state)[:150]}")
    outs = state.get("output") or []
    vurl = outs[0] if outs else None
    if not vurl:
        raise RuntimeError(f"runway: tanpa output url: {str(state)[:150]}")
    download(vurl, mp4)
    return mp4
