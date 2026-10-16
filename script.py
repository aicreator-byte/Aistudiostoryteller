"""Tahap 2a: Naskah per adegan. Judul+hook -> daftar adegan (storyboard + prompt video + narasi + dialog).
Aturan master prompt: character bible TERKUNCI dulu, dialog tertulis lengkap sebelum generasi."""
from __future__ import annotations
from core import llm, parse_json, JSON_MODEL

SYS = ("Kamu penulis naskah video storytelling faceless berbahasa Indonesia. "
       "Jawab HANYA JSON valid, tanpa teks lain.")

def make_characters(judul: str, ide: str, n: int = 3) -> list[dict]:
    """Character bible: deskripsi visual TERKUNCI per karakter.
    Return [{nama, usia, lock, suara}] — lock = 1 kalimat Inggris
    (wajah, rambut, pakaian, ciri fisik), suara = 'perempuan muda'/'laki-laki dewasa'/'lansia'."""
    prompt = f"""Buat {n} karakter untuk drama pendek.
Judul: {judul}
Ide: {ide}
Setiap karakter: {{"nama": "...", "usia": 30, "lock": "1 kalimat Inggris: usia, wajah, rambut, pakaian, ciri fisik unik", "suara": "perempuan muda"|"perempuan dewasa"|"laki-laki dewasa"|"laki-laki tua"|"perempuan tua"}}.
Deskripsi lock harus SPESIFIK dan KONSISTEN (contoh: "Indonesian woman 30 years old, round face, shoulder-length black hair, yellow blouse and jeans").
Output: array JSON saja."""
    return parse_json(llm(prompt, SYS, max_tokens=2000, model=JSON_MODEL), want=list)

def make_script(judul: str, hook: str, ide: str, durasi_target: int = 60,
                gaya: str = "sinematik", characters: list[dict] | None = None,
                dialog_mode: bool = False) -> list[dict]:
    n_adegan = max(3, min(10, durasi_target // 8))
    dur_adegan = durasi_target / n_adegan
    char_block = ""
    if characters:
        locks = "\n".join(f"- {c['nama']}: {c['lock']}" for c in characters)
        char_block = f"\nKARAKTER TERKUNCI (pakai deskripsi ini PERSIS di setiap visual):\n{locks}\n"
    dialog_rule = ""
    if dialog_mode:
        dialog_rule = (f'\nSetiap adegan WAJIB punya "dialog": array of '
            f'{{"speaker": "nama karakter", "start": detik_mulai_dalam_adegan, '
            f'"end": detik_selesai, "text": "kalimat PERSIS Indonesia"}}. '
            f'Aturan: kalimat PENDEK (maks 8 kata), JANGAN tumpang tindih, '
            f'setiap kalimat SELESAI sebelum detik {dur_adegan:.0f}, '
            f'sisakan jeda untuk ekspresi. Maks 3 dialog per adegan.')
    prompt = f"""Tulis naskah video {"Shorts" if durasi_target<=70 else "panjang"} (~{durasi_target} detik).
Judul: {judul}
Hook: {hook}
Ide: {ide}
{char_block}Bagi jadi {n_adegan} adegan (@~{dur_adegan:.0f} detik). Setiap adegan: {{"visual": "STORYBOARD: subjek + LOCK karakter + komposisi + framing + lighting + mood, 2-3 kalimat Inggris",
"video": "PROMPT VIDEO AI: gerakan kamera + motion subjek + mood/suasana, 1-2 kalimat Inggris, tanpa dialog",
"narasi": "teks dibacakan 1-2 kalimat Indonesia (maks ~25 kata)"{', "dialog": [...]' if dialog_mode else ''}}}.{dialog_rule}
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
        d = {"visual": s.get("visual", ""),
             "video": s.get("video", ""),
             "narasi": s.get("narasi", "")}
        if dialog_mode:
            d["dialog"] = [{"speaker": x.get("speaker", ""), "start": float(x.get("start", 0)),
                            "end": float(x.get("end", 0)), "text": x.get("text", "")}
                           for x in s.get("dialog", [])]
        out.append(d)
    return out
