"""Tahap 2b: Suara narator via gTTS (gratis, tanpa key).
Word timing diestimasi proporsional panjang kata — cukup akurat untuk karaoke."""
from __future__ import annotations
from gtts import gTTS
from core import OUT, audio_duration

def synthesize(text: str, name: str, lang: str = "id") -> tuple[str, list[dict]]:
    mp3 = str(OUT / f"{name}.mp3")
    gTTS(text, lang=lang).save(mp3)
    dur = audio_duration(mp3)
    words = text.split()
    total = sum(len(w) for w in words) or 1
    out, t = [], 0.0
    for w in words:
        d = dur * len(w) / total
        out.append({"w": w, "s": round(t, 2), "e": round(t + d, 2)})
        t += d
    return mp3, out
