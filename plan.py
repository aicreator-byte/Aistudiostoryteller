"""Tahap 1: Rencana konten. Topik channel -> kalender 7-30 hari (judul, hook, format)."""
from __future__ import annotations
from core import llm, parse_json, JSON_MODEL

SYS = ("Kamu perencana konten YouTube faceless Indonesia. Jawab HANYA JSON valid, "
       "tanpa teks lain.")

def make_plan(topik: str, hari: int = 7, shorts_per_hari: int = 1,
              long_per_minggu: int = 1) -> list[dict]:
    prompt = f"""Buatkan rencana konten {hari} hari untuk channel YouTube faceless bertopik "{topik}".
Aturan: {shorts_per_hari} Short (<=60 detik) per hari, {long_per_minggu} video panjang per minggu.
Setiap item: {{"hari": 1, "format": "short"|"long", "judul": "...", "hook": "kalimat pembuka <=15 kata", "ide": "1 kalimat isi"}}.
Judul gaya YouTube Indonesia, clickbait sehat, tanpa clickbait bohong.
Output: array JSON saja."""
    return parse_json(llm(prompt, SYS, max_tokens=6000, model=JSON_MODEL), want=list)

if __name__ == "__main__":
    import sys
    plan = make_plan(sys.argv[1] if len(sys.argv) > 1 else "Asal Usul Nusantara", 7)
    for p in plan:
        print(f"Hari {p['hari']} [{p['format']}] {p['judul']}\n  hook: {p['hook']}")
