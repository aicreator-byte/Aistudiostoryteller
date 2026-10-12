"""Tahap 3: Video per adegan.
Gambar asli (image search, sesuai deskripsi visual) + animasi Ken Burns
(slow zoom) via FFmpeg — sinkron durasi narasi.
Fallback: mock pola bila gambar tidak didapat.
Format: 9:16 (Shorts) atau 16:9 (long)."""
from __future__ import annotations
import json, os, subprocess, urllib.request
from core import OUT, run, audio_duration

def _search_image(query: str) -> str | None:
    """Return direct image URL atau None."""
    try:
        out = subprocess.run(["/opt/hatch/bin/image-search", query[:150],
                              "--max-results", "3"],
                             capture_output=True, text=True, timeout=60)
        data = json.loads(out.stdout)
        for r in data.get("results", []):
            u = r.get("media_url") or ""
            if u.startswith("https://") and "?" not in u and "#" not in u:
                return u
            if u.startswith("https://"):
                return u.split("?")[0] if "?" in u else u
    except Exception:
        pass
    return None

def _download(url: str, dest: str) -> bool:
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=60) as r:
            if "image" not in r.headers.get("Content-Type", ""):
                return False
            body = r.read(15 * 1024 * 1024)
        if len(body) < 20_000:
            return False
        open(dest, "wb").write(body)
        # validasi bisa dibaca ffmpeg
        p = subprocess.run(["ffprobe", "-v", "error", "-show_entries",
                            "stream=width", "-of", "csv=p=0", dest],
                           capture_output=True, text=True, timeout=30)
        return bool(p.stdout.strip().isdigit())
    except Exception:
        return False

def _video_chain() -> list[str]:
    """Rantai provider video dari env VIDEO_CHAIN.
    Langsung: kling, minimax, runway, luma.
    Aggregator: fal, replicate.
    kenburns = slideshow foto+zoom (gratis, selalu jalan, fallback terakhir).
    Adapter yang gagal -> otomatis lanjut ke berikutnya."""
    return [p.strip().lower() for p in
            os.getenv("VIDEO_CHAIN", "kenburns").split(",") if p.strip()]

def _fit_duration(mp4: str, durasi: float) -> str:
    """Samakan durasi klip AI dengan durasi narasi (potong / loop)."""
    try:
        d = audio_duration(mp4)
    except Exception:
        return mp4
    if abs(d - durasi) < 0.4 or d <= 0:
        return mp4
    tmp = mp4.replace(".mp4", "_fit.mp4")
    try:
        if d > durasi:
            run(["ffmpeg", "-y", "-v", "error", "-i", mp4,
                 "-t", f"{durasi:.1f}", "-c", "copy", tmp], timeout=120)
        else:
            n = int(durasi // d) + 1
            run(["ffmpeg", "-y", "-v", "error", "-stream_loop", str(n),
                 "-i", mp4, "-t", f"{durasi:.1f}",
                 "-c:v", "libx264", "-pix_fmt", "yuv420p", tmp], timeout=180)
    except Exception:
        return mp4
    return tmp if os.path.exists(tmp) else mp4

def make_scene(name: str, visual: str, durasi: float, vertikal: bool = True) -> str:
    mp4 = str(OUT / f"{name}.mp4")
    w, h = (1080, 1920) if vertikal else (1920, 1080)
    for prov in _video_chain():
        if prov == "kenburns":
            return _kenburns(name, visual, durasi, w, h, mp4)
        # Adapter provider berbayar: file vid_<nama>.py dengan fungsi
        # generate(name, visual, durasi, vertikal, mp4) -> str path mp4.
        # Belum ada / gagal -> lanjut ke provider berikutnya.
        try:
            mod = __import__(f"vid_{prov}", fromlist=["generate"])
            raw = mod.generate(name, visual, durasi, vertikal, mp4)
            return _fit_duration(raw, durasi)
        except Exception:
            continue
    return _kenburns(name, visual, durasi, w, h, mp4)

def _kenburns(name: str, visual: str, durasi: float, w: int, h: int, mp4: str) -> str:
    img = str(OUT / f"{name}.jpg")
    url = _search_image(visual)
    if url and _download(url, img):
        frames = max(int(durasi * 30), 30)
        # Ken Burns: zoom pelan 1.0 -> 1.25
        run(["ffmpeg", "-y", "-v", "error", "-loop", "1", "-i", img,
             "-vf", f"scale={w*2}:-2,zoompan=z='1+0.25*on/{frames}':d={frames}:"
                    f"x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':s={w}x{h}:fps=30",
             "-t", f"{durasi:.1f}", "-c:v", "libx264", "-pix_fmt", "yuv420p",
             "-movflags", "+faststart", mp4], timeout=180)
    else:
        # fallback mock
        run(["ffmpeg", "-y", "-v", "error",
             "-f", "lavfi", "-i", f"testsrc2=size={w}x{h}:rate=30:duration={durasi:.1f}",
             "-c:v", "libx264", "-pix_fmt", "yuv420p", "-movflags", "+faststart",
             mp4], timeout=120)
    return mp4

def scene_for_narration(name: str, visual: str, mp3: str, vertikal: bool = True) -> str:
    return make_scene(name, visual, audio_duration(mp3), vertikal)
