"""Langsung: MiniMax Hailuo video. Env: MINIMAX_API_KEY, MINIMAX_MODEL.
BELUM TERVERIFIKASI live (butuh key) — ditulis dari dokumentasi publik."""
from __future__ import annotations
import os
from vid_common import req_json, download, poll_until

def generate(name: str, visual: str, durasi: float, vertikal: bool, mp4: str) -> str:
    key = os.getenv("MINIMAX_API_KEY", "").strip()
    if not key:
        raise RuntimeError("MINIMAX_API_KEY kosong")
    model = os.getenv("MINIMAX_MODEL", "MiniMax-Hailuo-02").strip()
    h = {"Authorization": f"Bearer {key}", "Content-Type": "application/json"}
    sub = req_json("POST", "https://api.minimax.chat/v1/video_generation", h,
                   {"model": model, "prompt": visual[:1500],
                    "duration": 10 if durasi > 7 else 6,
                    "resolution": "768P"})
    task_id = sub.get("task_id")
    if not task_id:
        raise RuntimeError(f"minimax: tanpa task_id: {str(sub)[:150]}")
    state: dict = {}
    def done():
        state.update(req_json(
            "GET", f"https://api.minimax.chat/v1/query/video_generation?task_id={task_id}", h))
        return state.get("status") in ("Success", "Fail")
    poll_until(done, timeout_s=900)
    if state.get("status") != "Success":
        raise RuntimeError(f"minimax gagal: {str(state)[:150]}")
    vurl = (state.get("file") or {}).get("download_url") or state.get("video_url")
    if not vurl:
        raise RuntimeError(f"minimax: tanpa video url: {str(state)[:150]}")
    download(vurl, mp4)
    return mp4
