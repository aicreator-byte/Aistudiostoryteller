"""Tahap 3: Video per adegan.
Gambar asli (image search, sesuai deskripsi visual) + animasi Ken Burns
(slow zoom) via FFmpeg — sinkron durasi narasi.
Rantai fallback: cari ulang dengan kata kunci lebih luas -> bila tetap
kosong, latar sinematik dari warna & mood adegan (bukan pola generik).
Format: 9:16 (Shorts) atau 16:9 (long)."""
from __future__ import annotations
import json, os, re, subprocess, urllib.request
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

# Kata kunci Indonesia -> Inggris untuk pencarian ulang yang lebih luas.
_ID_EN = {
    "kamar": "bedroom", "ruang": "room", "dapur": "kitchen", "kantor": "office",
    "jalan": "street", "gang": "alley", "pasar": "market", "rumah": "house",
    "pantai": "beach", "laut": "ocean", "gunung": "mountain", "hutan": "forest",
    "sawah": "rice field", "langit": "sky", "kota": "city", "desa": "village",
    "malam": "night", "pagi": "morning", "sore": "afternoon", "senja": "sunset",
    "hujan": "rain", "api": "fire", "air": "water", "mobil": "car",
    "motor": "motorcycle", "perahu": "boat", "kapal": "ship", "anak": "child",
    "pria": "man", "wanita": "woman", "kakek": "old man", "nenek": "old woman",
    "wajah": "face", "bunga": "flower", "pohon": "tree", "batu": "stone",
    "tangga": "stairs", "pintu": "door", "jendela": "window", "meja": "table",
    "lampu": "lamp", "lilin": "candle", "istana": "palace", "kastil": "castle",
    "naga": "dragon", "hantu": "ghost", "raja": "king", "ratu": "queen",
    "pangeran": "prince", "putri": "princess", "dokter": "doctor", "sekolah": "school",
    "masjid": "mosque", "gereja": "church", "restoran": "restaurant", "kafe": "cafe",
    "kopi": "coffee", "makanan": "food", "uang": "money", "emas": "gold",
    "sungai": "river", "danau": "lake", "gurun": "desert", "salju": "snow",
    "awan": "cloud", "bintang": "stars", "bulan": "moon", "matahari": "sun",
    "badai": "storm", "petir": "lightning", "kabut": "fog", "asap": "smoke",
    "taman": "garden", "kebun": "garden", "kucing": "cat", "anjing": "dog",
    "burung": "bird", "ikan": "fish", "kuda": "horse",
}
_STOP = {"yang", "dan", "di", "ke", "dari", "dengan", "untuk", "pada", "sebuah",
        "seorang", "para", "ini", "itu", "adalah", "sebagai", "dalam", "saat",
        "ketika", "sambil", "lalu", "kemudian", "sangat", "lebih", "tanpa",
        "seperti", "akan", "telah", "sudah", "sedang", "tak", "tidak", "ada"}

def _broad_queries(visual: str) -> list[str]:
    """Urutan pencarian: teks asli -> kata kunci Inggris -> 2-3 kata terluas."""
    words = [w for w in re.findall(r"[a-z]+", visual.lower()) if w not in _STOP]
    mapped = [_ID_EN.get(w, w) for w in words]
    out = [visual.strip()]
    en = " ".join(mapped).strip()
    if en and en.lower() != visual.strip().lower():
        out.append(en)
    nouns = [w for w in mapped if w in set(_ID_EN.values())]
    broad = " ".join((nouns or mapped)[-3:]).strip()
    if broad and broad not in out:
        out.append(broad)
    return [q for q in out if q]

# Mood adegan -> pasangan warna latar sinematik (gelap -> terang).
_MOODS = [
    (("malam", "night", "gelap", "dark"), ("0x0a0f24", "0x1c2a4d")),
    (("senja", "sunset", "terbenam"), ("0x2b1a4d", "0xc9712f")),
    (("sedih", "sad", "duka", "muram"), ("0x182230", "0x3d4c5c")),
    (("bahagia", "happy", "ceria", "joy"), ("0x3d2d17", "0xc9a24e")),
    (("romantis", "romantic", "cinta", "love"), ("0x2e1a30", "0xa34e6e")),
    (("tegang", "tense", "horor", "horror", "seram", "misteri"), ("0x140b0b", "0x5c1515")),
    (("pagi", "morning", "fajar", "dawn"), ("0x2a3a4d", "0xd9c9a8")),
    (("hujan", "rain"), ("0x1d2833", "0x5c6e7e")),
    (("laut", "ocean", "sea", "pantai", "beach"), ("0x0a2b3d", "0x1f6e8c")),
    (("hutan", "forest", "taman", "garden"), ("0x0e2b1a", "0x2f5c3d")),
]

def _mood_colors(visual: str) -> tuple[str, str]:
    v = visual.lower()
    for keys, colors in _MOODS:
        if any(k in v for k in keys):
            return colors
    return ("0x14141d", "0x30303d")  # sinematik netral

def _mood_background(img: str, w: int, h: int, c0: str, c1: str) -> bool:
    """Latar gradien sinematik + vignette + grain halus."""
    try:
        run(["ffmpeg", "-y", "-v", "error", "-f", "lavfi",
             "-i", f"gradients=s={w}x{h}:c0={c0}:c1={c1}:speed=0.03",
             "-vframes", "1",
             "-vf", "vignette=PI/4.5,noise=alls=5:allf=t", img], timeout=60)
    except Exception:
        return False
    return os.path.exists(img)

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

def strip_audio(mp4: str) -> str:
    """Buang audio asli klip AI (aturan: audio HANYA dari naskah, no clash)."""
    out = mp4.replace(".mp4", "_noaud.mp4")
    try:
        run(["ffmpeg", "-y", "-v", "error", "-i", mp4, "-c", "copy",
             "-an", out], timeout=120)
    except Exception:
        return mp4
    return out if os.path.exists(out) else mp4

def make_scene(name: str, prompt: str, durasi: float, vertikal: bool = True,
               storyboard: str = "", strip: bool = False) -> str:
    """Buat klip adegan. prompt = prompt video AI; storyboard = deskripsi
    statis (Ken Burns pakai ini untuk cari foto; default = prompt).
    strip=True: buang audio asli klip (untuk dialog TTS terpisah)."""
    mp4 = str(OUT / f"{name}.mp4")
    w, h = (1080, 1920) if vertikal else (1920, 1080)
    sb = storyboard or prompt
    for prov in _video_chain():
        if prov == "kenburns":
            return _kenburns(name, sb, durasi, w, h, mp4)
        # Adapter provider berbayar: file vid_<nama>.py dengan fungsi
        # generate(name, prompt, durasi, vertikal, mp4) -> str path mp4.
        # Belum ada / gagal -> lanjut ke provider berikutnya.
        try:
            mod = __import__(f"vid_{prov}", fromlist=["generate"])
            raw = mod.generate(name, prompt, durasi, vertikal, mp4)
            raw = _fit_duration(raw, durasi)
            return strip_audio(raw) if strip else raw
        except Exception:
            continue
    return _kenburns(name, sb, durasi, w, h, mp4)

def _kenburns(name: str, visual: str, durasi: float, w: int, h: int, mp4: str) -> str:
    img = str(OUT / f"{name}.jpg")
    got = False
    for q in _broad_queries(visual):
        url = _search_image(q)
        if url and _download(url, img):
            got = True
            break
    if not got:
        # Cadangan: latar sinematik dari warna & mood adegan (bukan pola).
        c0, c1 = _mood_colors(visual)
        _mood_background(img, w, h, c0, c1)
    frames = max(int(durasi * 30), 30)
    # Ken Burns: zoom pelan 1.0 -> 1.25 (sama untuk foto maupun latar mood)
    run(["ffmpeg", "-y", "-v", "error", "-loop", "1", "-i", img,
         "-vf", f"scale={w*2}:-2,zoompan=z='1+0.25*on/{frames}':d={frames}:"
                f"x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':s={w}x{h}:fps=30",
         "-t", f"{durasi:.1f}", "-c:v", "libx264", "-pix_fmt", "yuv420p",
         "-movflags", "+faststart", mp4], timeout=180)
    return mp4

def scene_for_narration(name: str, prompt: str, mp3: str, vertikal: bool = True,
                        storyboard: str = "") -> str:
    return make_scene(name, prompt, audio_duration(mp3), vertikal, storyboard)
