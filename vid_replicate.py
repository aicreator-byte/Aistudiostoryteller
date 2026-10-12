"""Aggregator Replicate — banyak model video via 1 token.
Env: REPLICATE_API_TOKEN, REPLICATE_MODEL (format owner/nama).
BELUM TERVERIFIKASI live (butuh key) — ditulis dari dokumentasi publik."""
from __future__ import annotations
import os
from vid_common import req_json, download, poll_until

def generate(name: str, visual: str, durasi: float, vertikal: bool, mp4: str) -> str:
    key = os.getenv("REPLICATE_API_TOKEN", "").strip()
    if not key:
        raise RuntimeError("REPLICATE_API_TOKEN kosong")
    model = os.getenv("REPLICATE_MODEL", "kwaivg/kling-v2.1").strip()
    h = {"Authorization": f"Token {key}", "Content-Type": "application/json"}
    pred = req_json(
        "POST", f"https://api.replicate.com/v1/models/{model}/predictions", h,
        {"input": {"prompt": visual[:1500],
                   "aspect_ratio": "9:16" if vertikal else "16:9"}})
    get_url = (pred.get("urls") or {}).get("get")
    if not get_url:
        raise RuntimeError(f"replicate: tanpa poll url: {str(pred)[:150]}")
    state: dict = {}
    def done():
        state.update(req_json("GET", get_url, h))
        return state.get("status") in ("succeeded", "failed", "canceled")
    poll_until(done, timeout_s=900)
    if state.get("status") != "succeeded":
        raise RuntimeError(f"replicate gagal: {state.get('status')}: {str(state.get('error'))[:120]}")
    out = state.get("output")
    vurl = out[0] if isinstance(out, list) else out
    if not vurl:
        raise RuntimeError(f"replicate: tanpa output url: {str(state)[:150]}")
    download(vurl, mp4)
    return mp4
