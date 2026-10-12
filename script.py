"""Tahap 2a: Naskah per adegan. Judul+hook -> daftar adegan (storyboard + prompt video + narasi)."""
from __future__ import annotations
from core import llm, parse_json, JSON_MODEL

SYS = ("Kamu penulis naskah video storytelling faceless berbahasa Indonesia. "
       "Jawab HANYA JSON valid, tanpa teks lain.")

def make_script(judul: str, hook: str, ide: str, durasi_target: int = 60,
                gaya: str = "sinematik") -> list[dict]:
    n_adegan = max(3, min(10, durasi_target // 8))
    prompt = f"""Tulis naskah video {"Shorts" if durasi_target<=70 else "panjang"} (~{durasi_target} detik).
Judul: {judul}
Hook: {hook}
Ide: {ide}
Bagi jadi {n_adegan} adegan. Setiap adegan: {{"visual": "STORYBOARD: komposisi, framing, gaya {gaya}, tokoh konsisten, 1 kalimat Inggris",
"video": "PROMPT VIDEO AI: gerakan kamera + motion subjek + mood/suasana, 1-2 kalimat Inggris, tanpa dialog",
"narasi": "teks dibacakan 1-2 kalimat Indonesia (maks ~25 kata)"}}.
Narasi total pas untuk {durasi_target} detik (±150 kata per menit).
Output: array JSON saja."""
    last = None
    for mt in (4000, 6000, 8000):
        try:
            scenes = parse_json(llm(prompt, SYS, max_tokens=mt, model=JSON_MODEL), want=list)
            break
        except ValueError as e:
            last = e
    else:
        raise last
    # normalisasi key
    out = []
    for s in scenes:
        out.append({"visual": s.get("visual", ""),
                    "video": s.get("video", ""),
                    "narasi": s.get("narasi", "")})
    return out
