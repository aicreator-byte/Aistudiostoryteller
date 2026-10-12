"""Tahap 5: SEO YouTube otomatis — 4 judul, deskripsi + bab, hashtag, tags."""
from __future__ import annotations
from core import llm, parse_json, JSON_MODEL

SYS = "Kamu ahli SEO YouTube Indonesia. Jawab HANYA JSON valid."

def make_seo(judul: str, ringkasan: str, durasi: int) -> dict:
    prompt = f"""Buatkan paket SEO YouTube Indonesia untuk video:
Judul kerja: {judul}
Isi: {ringkasan}
Durasi: {durasi} detik.
Wajib output SATU objek JSON dengan key persis: "judul_opsional" (array 4 string),
"deskripsi" (string: 2 paragraf + bab 00:00 + CTA), "hashtag" (array),
"tags" (array 15-25 string). Tanpa teks lain."""
    for _ in range(2):
        d = parse_json(llm(prompt, SYS, max_tokens=3000, model=JSON_MODEL), want=dict)
        if isinstance(d, dict) and "judul_opsional" in d and "tags" in d:
            return d
    # fallback minimal kalau LLM bandel
    return {"judul_opsional": [judul], "deskripsi": ringkasan,
            "hashtag": ["#shorts"], "tags": [judul]}
