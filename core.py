"""Bersama: LLM (NVIDIA NIM), path, helper FFmpeg."""
from __future__ import annotations
import json, os, subprocess, sys
from pathlib import Path
import urllib.request

BASE = Path(__file__).resolve().parent
OUT = BASE / "output"
OUT.mkdir(exist_ok=True)

NIM_HOST = "integrate.api.nvidia.com"
NIM_MODEL = os.getenv("NIM_MODEL", "nvidia/nemotron-3-super-120b-a12b")
# model non-reasoning untuk tugas JSON (lebih patuh format)
JSON_MODEL = os.getenv("NIM_JSON_MODEL", "meta/llama-3.2-11b-vision-instruct")

_NIM = None
def _nim_key() -> str:
    global _NIM
    if _NIM: return _NIM
    env = os.getenv("NVIDIA_API_KEY", "").strip()
    if env:  # server generik: pakai env var langsung
        _NIM = env; return _NIM
    sys.path.insert(0, "/opt/hatch/skills/skill-creator/bin")
    from dynamic_credentials import dynamic_credential_entry
    _NIM = str(dynamic_credential_entry("custom.nvidia-nim")["surrogate"]).strip()
    return _NIM

def llm(prompt: str, system: str = "", max_tokens: int = 1500, model: str | None = None) -> str:
    msgs = []
    if system: msgs.append({"role": "system", "content": system})
    msgs.append({"role": "user", "content": prompt})
    req = urllib.request.Request(
        f"https://{NIM_HOST}/v1/chat/completions",
        data=json.dumps({"model": model or NIM_MODEL, "messages": msgs,
                         "temperature": 0.7, "max_tokens": max_tokens}).encode(),
        headers={"Content-Type": "application/json",
                 "Authorization": f"Bearer {_nim_key()}"})
    with urllib.request.urlopen(req, timeout=300) as r:
        msg = json.load(r)["choices"][0]["message"]
        # Nemotron/reasoning model: jawaban kadang di reasoning_content
        return msg.get("content") or msg.get("reasoning_content") or ""

def run(cmd: list[str], **kw) -> subprocess.CompletedProcess:
    return subprocess.run(cmd, capture_output=True, text=True, **kw)

def parse_json(text: str, want: type = None):
    """Ambil JSON dari output LLM, toleran fence/quote/reasoning.
    want=dict|list: prioritaskan tipe itu."""
    t = text.strip()
    if t.startswith("```"):
        t = "\n".join(t.split("\n")[1:])
        if t.rstrip().endswith("```"):
            t = t.rstrip()[:-3]
    t = t.strip()
    if t[:2] == "'{":
        t = t[1:]
    if t[-2:] == "}'":
        t = t[:-1]
    t = t.strip()
    if len(t) >= 2 and t[0] == t[-1] and t[0] in "\"'":
        t = t[1:-1].strip()
        if '\\n' in t and '\n' not in t:
            t = t.encode().decode("unicode_escape")

    def _scan(opn, cls):
        j = t.rfind(cls)
        if j < 0:
            return None
        i = t.find(opn)
        while 0 <= i < j:
            try:
                return json.loads(t[i:j + 1])
            except json.JSONDecodeError:
                i = t.find(opn, i + 1)
        return None

    order = [("{", "}"), ("[", "]")] if want is not dict else [("{", "}"), ("[", "]")]
    if want is list:
        order = [("[", "]"), ("{", "}")]
    for opn, cls in order:
        d = _scan(opn, cls)
        if d is not None and (want is None or isinstance(d, want)):
            return d
    raise ValueError("LLM tidak mengembalikan JSON valid")


def audio_duration(path: str) -> float:
    try:
        r = run(["ffprobe", "-v", "error", "-show_entries",
                 "format=duration", "-of", "csv=p=0", path], timeout=15)
        return float(r.stdout.strip())
    except Exception:
        return 5.0
