"""Dialog per karakter: Piper TTS offline + pitch per karakter + mix di timestamp.
ATURAN: audio HANYA dari naskah dialog. Audio asli klip AI DIBUANG (no clash, no halusinasi)."""
from __future__ import annotations
import os, subprocess, wave
from core import OUT, run, audio_duration

VOICE = "/home/hatch/workspace/piper-voices/id_ID-news_tts-medium.onnx"
_PITCH = {"perempuan muda": 1.30, "perempuan dewasa": 1.22,
          "laki-laki dewasa": 0.90, "laki-laki tua": 0.80,
          "perempuan tua": 1.08}

def _pitch_of(characters: list[dict], speaker: str) -> float:
    for c in characters:
        if c.get("nama", "").lower() == speaker.lower():
            return _PITCH.get(c.get("suara", ""), 1.0)
    return 1.0

def build_dialogue_track(scenes: list[dict], characters: list[dict],
                         name: str, scene_dur: float) -> str:
    """scenes: [{dialog: [{speaker, start, end, text}], ...}] (start/end relatif per adegan).
    Return: mp3 full-durasi berisi semua dialog di timestamp absolut."""
    from piper import PiperVoice
    v = PiperVoice.load(VOICE)
    tmp = str(OUT / f"{name}_dlg"); os.makedirs(tmp, exist_ok=True)
    total = scene_dur * len(scenes)
    wavs = []
    i = 0
    for si, sc in enumerate(scenes):
        base = si * scene_dur
        for d in sc.get("dialog", []):
            text = d.get("text", "").strip()
            if not text:
                continue
            raw = f"{tmp}/raw{i}.wav"
            with wave.open(raw, "wb") as w:
                w.setnchannels(1); w.setsampwidth(2)
                w.setframerate(v.config.sample_rate)
                for chunk in v.synthesize(text):
                    w.writeframes(chunk.audio_int16_bytes)
            f = _pitch_of(characters, d.get("speaker", ""))
            fin = f"{tmp}/d{i}.wav"
            run(["ffmpeg", "-v", "error", "-y", "-i", raw, "-af",
                 f"asetrate=22050*{f},aresample=22050,atempo={1/f:.4f},aresample=44100",
                 fin], timeout=60)
            t0 = base + float(d.get("start", 0))
            dur = audio_duration(fin)
            win = float(d.get("end", t0)) - float(d.get("start", 0))
            if dur > win + 0.5:
                print(f"WARN dialog '{text[:30]}' dur={dur:.1f}s > window {win:.1f}s")
            wavs.append((fin, int(t0 * 1000)))
            i += 1
    if not wavs:
        # trek sunyi sepanjang video
        mp3 = str(OUT / f"{name}_dialog.mp3")
        run(["ffmpeg", "-v", "error", "-y", "-f", "lavfi",
             "-i", f"anullsrc=r=44100:cl=stereo:d={total:.1f}",
             "-t", f"{total:.1f}", mp3], timeout=60)
        return mp3
    inputs = [x for w, _ in wavs for x in ("-i", w)]
    fc = []
    for j, (_, ms) in enumerate(wavs):
        fc.append(f"[{j}:a]aformat=channel_layouts=stereo,adelay={ms}|{ms}[d{j}]")
    fc.append("".join(f"[d{j}]" for j in range(len(wavs))) +
              f"amix=inputs={len(wavs)}:normalize=0,apad,atrim=0:{total:.1f}[aout]")
    mp3 = str(OUT / f"{name}_dialog.mp3")
    run(["ffmpeg", "-v", "error", "-y", *inputs,
         "-filter_complex", ";".join(fc), "-map", "[aout]",
         "-c:a", "libmp3lame", "-q:a", "4", "-t", f"{total:.1f}", mp3],
        timeout=180)
    return mp3

def dialogue_subtitle(scenes: list[dict], scene_dur: float, path: str) -> str:
    """Subtitle SRT sederhana dari dialog (bukan karaoke)."""
    def fmt(t):
        h = int(t // 3600); m = int((t % 3600) // 60); s = t % 60
        return f"{h:02d}:{m:02d}:{s:06.3f}".replace(".", ",")
    lines = []
    n = 1
    for si, sc in enumerate(scenes):
        base = si * scene_dur
        for d in sc.get("dialog", []):
            text = d.get("text", "").strip()
            if not text:
                continue
            s0 = base + float(d.get("start", 0)); s1 = base + float(d.get("end", s0 + 2))
            lines.append(f"{n}\n{fmt(s0)} --> {fmt(s1)}\n{text}\n")
            n += 1
    open(path, "w").write("\n".join(lines))
    return path
