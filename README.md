# 🎬 Storyteller AI Studio

Pipeline video storytelling faceless — dari ide jadi MP4 siap upload.
UI/alur terinspirasi MarkasAI Storytelling Studio.

**Alur:** Beranda → Rancang videomu (brief) → Periksa skrip → Daftar adegan →
Studio (render + ekspor + SEO) → Channel & kalender konten.

## Fitur

- 6 template (sejarah, mitos, sains, motivasi, dongeng anak, fakta dunia)
- 19 gaya visual, format Short 9:16 / Long 16:9
- Naskah per adegan via LLM (editable)
- Video per adegan: foto asli (image search) + animasi Ken Burns via FFmpeg
- Voice-over via gTTS (gratis)
- Subtitle karaoke (.ass burned-in), loudnorm -16 LUFS (standar YouTube)
- Ekspor 1080p/720p, 30fps, faststart; subtitle .srt terpisah
- Auto SEO: opsi judul, deskripsi, tags (copy-paste)
- Channel + kalender konten bulanan

## Kebutuhan

- Python 3.10+, FFmpeg + FFprobe
- `pip install gtts`
- NVIDIA NIM API key (gratis): set env `NVIDIA_API_KEY`
- CLI `image-search` (opsional — tanpa ini, adegan pakai pola mock)

## Jalan cepat

```bash
export NVIDIA_API_KEY="nvapi-..."
python3 app.py
# buka http://127.0.0.1:8091
```

## Struktur

| File | Peran |
|---|---|
| `app.py` | Web server stdlib + seluruh UI (GET-only, path params) |
| `core.py` | LLM (NVIDIA NIM), helper FFmpeg, path output |
| `script.py` | Naskah per adegan |
| `voice.py` | TTS gTTS + estimasi word timing |
| `video.py` | Gambar + Ken Burns per adegan |
| `assemble.py` | Gabung + karaoke + loudnorm + ekspor |
| `seo.py` | Judul/deskripsi/tags |
| `plan.py`, `pipeline.py` | Utilitas CLI |

## Batasan

- "Video AI" per adegan = slideshow Ken Burns, bukan generasi video AI
  (butuh API berbayar seperti Seedance/MiniMax/Wan).
- Pilihan narator pria/wanita belum membedakan suara (keterbatasan gTTS).
- Tanpa upload file & tanpa auto-upload YouTube (butuh OAuth).
- Jobs tersimpan di `output/jobs.json`.
