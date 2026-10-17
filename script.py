"""Tahap 2a: Naskah per adegan. Judul+hook -> daftar adegan (storyboard + prompt video + narasi + dialog).
Aturan master prompt: character bible TERKUNCI dulu, dialog tertulis lengkap sebelum generasi.
Mendukung: karakter hewan (fabel), mode tanpa dialog (kartun bisu), jumlah adegan fleksibel."""
from __future__ import annotations
from core import llm, parse_json, JSON_MODEL

SYS = ("Kamu penulis naskah video storytelling faceless berbahasa Indonesia. "
       "Jawab HANYA JSON valid, tanpa teks lain.")

# Kata Indonesia umum — untuk validasi prompt visual/video harus Inggris.
_ID_WORDS = {"yang", "dan", "dengan", "adalah", "sebuah", "untuk", "dari",
             "pada", "dalam", "kamera", "menangkap", "gerakan", "suara",
             "seorang", "para", "ini", "itu", "saat", "ketika", "sambil",
             "lalu", "sangat", "tanpa", "seperti", "akan", "telah", "sedang"}

def _is_english(text: str) -> bool:
    words = set(text.lower().split())
    return len(words & _ID_WORDS) == 0

def make_characters(judul: str, ide: str, n: int = 3,
                    jenis: str = "manusia") -> list[dict]:
    """Character bible: deskripsi visual TERKUNCI per karakter.
    jenis: "manusia" | "hewan" (fabel: hewan antropomorfik, tanpa rambut/pakaian manusia yg aneh).
    Return [{nama, usia, lock, suara}] — lock = 1 kalimat Inggris."""
    if jenis == "hewan":
        char_spec = ('1 kalimat Inggris: spesies hewan + ciri fisik hewan '
                     '(cangkang/bulu/kuping/ekor) + SATU item pakaian/aksesori yg masuk akal. '
                     'JANGAN beri rambut manusia. Contoh: "Slow green tortoise, big round shell, '
                     'wearing a small brown barista apron"')
    else:
        char_spec = ('1 kalimat Inggris: usia, wajah, rambut, pakaian, ciri fisik unik. '
                     'Contoh: "Indonesian woman 30 years old, round face, shoulder-length '
                     'black hair, yellow blouse and jeans"')
    prompt = f"""Buat {n} karakter untuk video.
Judul: {judul}
Ide: {ide}
Setiap karakter: {{"nama": "...", "usia": 30, "lock": "{char_spec}", "suara": "perempuan muda"|"perempuan dewasa"|"laki-laki dewasa"|"laki-laki tua"|"perempuan tua"}}.
Deskripsi lock harus SPESIFIK dan KONSISTEN.
PENTING: tulis field "lock" dalam Bahasa Inggris. Jangan campur Bahasa Indonesia.
Output: array JSON saja."""
    chars = parse_json(llm(prompt, SYS, max_tokens=2000, model=JSON_MODEL), want=list)
    # validasi: lock harus Inggris, retry sekali jika gagal
    if any(not _is_english(c.get("lock", "")) for c in chars):
        prompt += "\nULANGI: pastikan SEMUA field lock 100% Bahasa Inggris."
        chars = parse_json(llm(prompt, SYS, max_tokens=2000, model=JSON_MODEL), want=list)
    return chars

def make_script(judul: str, hook: str, ide: str, durasi_target: int = 60,
                gaya: str = "sinematik", characters: list[dict] | None = None,
                dialog_mode: bool = False, silent_mode: bool = False,
                n_adegan: int | None = None) -> list[dict]:
    """dialog_mode: dialog terjadwal per adegan. silent_mode: TANPA dialog/bicara,
    tiap adegan punya "sfx" (catatan efek suara). n_adegan: override jumlah adegan."""
    n_adegan = n_adegan or max(3, min(10, durasi_target // 8))
    dur_adegan = durasi_target / n_adegan
    char_block = ""
    if characters:
        locks = "\n".join(f"- {c['nama']}: {c['lock']}" for c in characters)
        char_block = f"\nKARAKTER TERKUNCI (pakai deskripsi ini PERSIS di setiap visual):\n{locks}\n"
    dialog_rule = ""
    if dialog_mode and not silent_mode:
        dialog_rule = (f'\nSetiap adegan WAJIB punya "dialog": array of '
            f'{{"speaker": "nama karakter", "start": detik_mulai_dalam_adegan, '
            f'"end": detik_selesai, "text": "kalimat PERSIS Indonesia"}}. '
            f'Aturan: kalimat PENDEK (maks 8 kata), JANGAN tumpang tindih, '
            f'setiap kalimat SELESAI sebelum detik {dur_adegan:.0f}, '
            f'sisakan jeda untuk ekspresi. Maks 3 dialog per adegan.')
    sfx_rule = ""
    if silent_mode:
        sfx_rule = ('\nMODE TANPA DIALOG: tidak ada karakter yang berbicara/bercakap. '
            'Ceritakan SEMUA lewat aksi visual dan ekspresi. '
            'Setiap adegan WAJIB punya "sfx": 1 kalimat Inggris berisi efek suara '
            'yang cocok (contoh: "door slam, crickets chirping").')
    fields = ('{"visual": "STORYBOARD 2-3 kalimat Inggris: subjek + LOCK karakter + '
              'komposisi + framing + lighting + mood", '
              '"video": "PROMPT VIDEO AI 1-2 kalimat Inggris: gerakan kamera + motion subjek + '
              'mood/suasana, tanpa dialog", '
              '"narasi": "1-2 kalimat Indonesia (maks ~25 kata)"'
              + (', "dialog": [...]' if dialog_mode and not silent_mode else '')
              + (', "sfx": "..."' if silent_mode else '') + '}')
    prompt = f"""Tulis naskah video {"Shorts" if durasi_target<=70 else "panjang"} (~{durasi_target} detik).
Judul: {judul}
Hook: {hook}
Ide: {ide}
{char_block}Bagi jadi {n_adegan} adegan (@~{dur_adegan:.0f} detik). Setiap adegan: {fields}.{dialog_rule}{sfx_rule}
PENTING: field "visual" dan "video" HARUS 100% Bahasa Inggris. Field "narasi" Bahasa Indonesia.
Narasi total pas untuk {durasi_target} detik (±150 kata per menit).
Output: array JSON saja."""
    last = None
    for mt in (4000, 6000, 8000):
        try:
            scenes = parse_json(llm(prompt, SYS, max_tokens=mt, model=JSON_MODEL), want=list)
            # validasi Inggris; retry sekali jika gagal
            bad = [s for s in scenes
                   if not _is_english(s.get("visual", "") + " " + s.get("video", ""))]
            if bad:
                raise ValueError("visual/video tidak Inggris, retry")
            break
        except ValueError as e:
            last = e
    else:
        raise last
    # normalisasi key + potong ke n_adegan (LLM kadang bikin lebih)
    out = []
    for s in scenes[:n_adegan]:
        d = {"visual": s.get("visual", ""),
             "video": s.get("video", ""),
             "narasi": s.get("narasi", "")}
        if dialog_mode and not silent_mode:
            d["dialog"] = [{"speaker": x.get("speaker", ""), "start": float(x.get("start", 0)),
                            "end": float(x.get("end", 0)), "text": x.get("text", "")}
                           for x in s.get("dialog", [])]
        if silent_mode:
            d["sfx"] = s.get("sfx", "")
            d["dialog"] = []
        out.append(d)
    return out
