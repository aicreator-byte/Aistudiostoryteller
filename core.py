"""Bersama: LLM (NVIDIA NIM), path, helper FFmpeg."""
from __future__ import annotations
import json, os, subprocess, sys
from pathlib import Path
import urllib.request

BASE = Path(__file__).resolve().parent
OUT = BASE / "output"
OUT.mkdir(exist_ok=True)

def _load_dotenv():
    """Muat .env (KEY=VALUE) ke environ — stdlib only, tanpa python-dotenv.
    .env tidak di-commit (lihat .gitignore); pakai .env.example sebagai acuan."""
    try:
        for line in (BASE / ".env").read_text().splitlines():
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            k, v = line.split("=", 1)
            k, v = k.strip(), v.strip().strip("'\"")
            if k and k not in os.environ:
                os.environ[k] = v
    except FileNotFoundError:
        pass

def read_env_file() -> dict:
    """Baca .env jadi dict (untuk halaman Pengaturan)."""
    d: dict[str, str] = {}
    try:
        for line in (BASE / ".env").read_text().splitlines():
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            k, v = line.split("=", 1)
            d[k.strip()] = v.strip().strip("'\"")
    except FileNotFoundError:
        pass
    return d

def write_env_file(updates: dict[str, str]):
    """Tulis ulang .env. Nilai kosong = pertahankan yang lama."""
    data = read_env_file()
    for k, v in updates.items():
        if v:
            data[k] = v
    (BASE / ".env").write_text("".join(f"{k}={v}\n" for k, v in data.items()))

def reload_env():
    """Muat ulang .env + reset cache key (dipanggil setelah Pengaturan disimpan)."""
    global _NIM
    _load_dotenv()
    _NIM = None

_load_dotenv()

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
    try:
        sys.path.insert(0, "/opt/hatch/skills/skill-creator/bin")
        from dynamic_credentials import dynamic_credential_entry
        _NIM = str(dynamic_credential_entry("custom.nvidia-nim")["surrogate"]).strip()
    except Exception:
        _NIM = ""
    return _NIM

def _openrouter_key() -> str:
    env = os.getenv("OPENROUTER_API_KEY", "").strip()
    if env:
        return env
    try:
        sys.path.insert(0, "/opt/hatch/skills/skill-creator/bin")
        from dynamic_credentials import dynamic_credential_entry
        return str(dynamic_credential_entry("custom.openrouter")["surrogate"]).strip()
    except Exception:
        return ""

def _chat(base: str, key: str, model: str, prompt: str, system: str,
          max_tokens: int, timeout: int = 180) -> str:
    """Chat completions OpenAI-compatible via urllib (stdlib). Raise jika gagal."""
    msgs = []
    if system: msgs.append({"role": "system", "content": system})
    msgs.append({"role": "user", "content": prompt})
    req = urllib.request.Request(
        f"{base.rstrip('/')}/chat/completions",
        data=json.dumps({"model": model, "messages": msgs,
                         "temperature": 0.7, "max_tokens": max_tokens}).encode(),
        headers={"Content-Type": "application/json",
                 "Authorization": f"Bearer {key}",
                 "HTTP-Referer": "https://storyteller.local",
                 "X-Title": "Storyteller AI Studio"})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        if r.status != 200:
            raise RuntimeError(f"HTTP {r.status}")
        msg = json.load(r)["choices"][0]["message"]
        out = msg.get("content") or msg.get("reasoning_content") or ""
        if not out.strip():
            raise RuntimeError("respon kosong")
        return out

def _env_key(name: str) -> str:
    """Key dari .env/environ saja (untuk provider langsung)."""
    return os.getenv(name, "").strip()

def _chat_anthropic(key: str, model: str, prompt: str, system: str,
                    max_tokens: int, timeout: int = 180) -> str:
    body: dict = {"model": model, "max_tokens": max_tokens,
                  "messages": [{"role": "user", "content": prompt}]}
    if system:
        body["system"] = system
    req = urllib.request.Request(
        "https://api.anthropic.com/v1/messages",
        data=json.dumps(body).encode(),
        headers={"Content-Type": "application/json",
                 "x-api-key": key,
                 "anthropic-version": "2023-06-01"})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        d = json.load(r)
        parts = [b.get("text", "") for b in d.get("content", [])
                 if b.get("type") == "text"]
        out = "".join(parts).strip()
        if not out:
            raise RuntimeError("respon kosong")
        return out

def _chat_gemini(key: str, model: str, prompt: str, system: str,
                 max_tokens: int, timeout: int = 180) -> str:
    full = f"{system}\n\n{prompt}" if system else prompt
    body = {"contents": [{"role": "user", "parts": [{"text": full}]}],
            "generationConfig": {"maxOutputTokens": max_tokens,
                                 "temperature": 0.7}}
    req = urllib.request.Request(
        f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent",
        data=json.dumps(body).encode(),
        headers={"Content-Type": "application/json",
                 "x-goog-api-key": key})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        d = json.load(r)
        try:
            out = d["candidates"][0]["content"]["parts"][0]["text"].strip()
        except (KeyError, IndexError):
            out = ""
        if not out:
            raise RuntimeError("respon kosong / diblokir")
        return out

def _providers() -> list:
    """Rantai fallback LLM dari env LLM_CHAIN.
    Langsung: anthropic, openai, gemini, nvidia.
    Via router: openrouter, 9router, omniroute.
    Yang tak dikenal / tanpa key -> di-skip otomatis."""
    chain = [p.strip().lower() for p in
             os.getenv("LLM_CHAIN", "nvidia,openrouter").split(",") if p.strip()]
    provs = []
    for p in chain:
        if p == "anthropic":
            k = _env_key("ANTHROPIC_API_KEY")
            m = os.getenv("ANTHROPIC_MODEL", "claude-sonnet-4-20250514").strip()
            if k and m:
                provs.append(("anthropic", k, m))
        elif p == "openai":
            k = _env_key("OPENAI_API_KEY")
            m = os.getenv("OPENAI_MODEL", "gpt-4o").strip()
            if k and m:
                provs.append(("openai", "https://api.openai.com/v1", k, m))
        elif p == "gemini":
            k = _env_key("GEMINI_API_KEY") or _env_key("GOOGLE_API_KEY")
            m = os.getenv("GEMINI_MODEL", "gemini-2.5-flash").strip()
            if k and m:
                provs.append(("gemini", k, m))
        elif p == "nvidia":
            k = _nim_key()
            if k:
                provs.append(("nvidia", "https://integrate.api.nvidia.com/v1",
                              k, os.getenv("NIM_MODEL", "nvidia/nemotron-3-super-120b-a12b")))
        elif p == "openrouter":
            k = _openrouter_key()
            m = os.getenv("OPENROUTER_MODEL", "google/gemma-4-26b-a4b-it:free").strip()
            if k and m:
                provs.append(("openrouter", "https://openrouter.ai/api/v1", k, m))
        elif p == "9router":
            provs.append(("9router", "http://127.0.0.1:20128",
                          os.getenv("ROUTER9_KEY", "dummy"),
                          os.getenv("ROUTER9_MODEL", "")))
        elif p == "omniroute":
            provs.append(("omniroute",
                          os.getenv("OMNIROUTE_URL", "http://127.0.0.1:20129"),
                          os.getenv("OMNIROUTE_KEY", "dummy"),
                          os.getenv("OMNIROUTE_MODEL", "")))
    return provs

def llm(prompt: str, system: str = "", max_tokens: int = 1500,
        model: str | None = None) -> str:
    """Coba setiap provider berurutan; fallback otomatis saat gagal."""
    errs = []
    provs = _providers()
    if not provs:
        raise RuntimeError("tidak ada provider LLM aktif — cek LLM_CHAIN/.env")
    for prov in provs:
        name = prov[0]
        try:
            if name == "anthropic":
                _, key, defmodel = prov
                return _chat_anthropic(key, defmodel, prompt, system, max_tokens)
            if name == "gemini":
                _, key, defmodel = prov
                return _chat_gemini(key, defmodel, prompt, system, max_tokens)
            _, base, key, defmodel = prov
            # override model hanya valid untuk nvidia (id model NIM)
            use_model = model if (model and name == "nvidia") else defmodel
            return _chat(base, key, use_model, prompt, system, max_tokens)
        except Exception as e:
            errs.append(f"{name}: {str(e)[:70]}")
    raise RuntimeError("semua provider LLM gagal — " + " | ".join(errs))

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
