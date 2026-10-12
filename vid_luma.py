"""Langsung: Luma Dream Machine. Env: LUMA_API_KEY, LUMA_MODEL.
BELUM TERVERIFIKASI live (butuh key) — ditulis dari dokumentasi publik."""
from __future__ import annotations
import os
from vid_common import req_json, download, poll_until

def generate(name: str, visual: str, durasi: float, vertikal: bool, mp4: str) -> str:
    key = os.getenv("LUMA_API_KEY", "").strip()
    if not key:
        raise RuntimeError("LUMA_API_KEY kosong")
    model = os.getenv("LUMA_MODEL", "ray-2").strip()
    h = {"Authorization": f"Bearer {key}", "Content-Type": "application/json"}
    sub = req_json("POST", "https://api.lumalabs.ai/dream-machine/v1/generations", h,
                   {"model": model, "prompt": visual[:1500],
                    "aspect_ratio": "9:16" if vertikal else "16:9",
                    "duration": "9s" if durasi > 7 else "5s",
                    "loop": False})
    gid = sub.get("id")
    if not gid:
        raise RuntimeError(f"luma: tanpa generation id: {str(sub)[:150]}")
    state: dict = {}
    def done():
        state.update(req_json(
            "GET", f"https://api.lumalabs.ai/dream-machine/v1/generations/{gid}", h))
        return state.get("state") in ("completed", "failed")
    poll_until(done, timeout_s=900)
    if state.get("state") != "completed":
        raise RuntimeError(f"luma gagal: {str(state)[:150]}")
    vurl = ((state.get("assets") or {}).get("video"))
    if not vurl:
        raise RuntimeError(f"luma: tanpa video url: {str(state)[:150]}")
    download(vurl, mp4)
    return mp4
