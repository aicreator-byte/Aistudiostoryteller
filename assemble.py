"""Tahap 4: Editing otomatis — gabung adegan + narasi + subtitle karaoke (ASS)
+ normalisasi loudness standar YouTube. Tanpa CapCut."""
from __future__ import annotations
from core import OUT, run

def _fmt(t: float) -> str:
    h = int(t // 3600); m = int((t % 3600) // 60); s = t % 60
    return f"{h}:{m:02d}:{s:05.2f}"

def karaoke_ass(scenes: list[dict], path: str, vertikal: bool = True):
    """scenes: [{words:[{w,s,e}], t0: offset detik}] -> file .ass karaoke."""
    fs = 64 if vertikal else 48
    head = ("[Script Info]\nScriptType: v4.00+\nPlayResX: 1080\nPlayResY: 1920\n\n"
            "[V4+ Styles]\nFormat: Name, Fontname, Fontsize, PrimaryColour, "
            "OutlineColour, BackColour, Bold, Alignment, MarginV\n"
            f"Style: Default,Arial,{fs},&H00FFFFFF,&H80000000,&H80000000,1,2,120\n\n"
            "[Events]\nFormat: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text\n")
    lines = [head]
    for sc in scenes:
        words = sc["words"]; t0 = sc["t0"]
        if not words: continue
        # kelompokkan 6 kata per baris karaoke
        for i in range(0, len(words), 6):
            chunk = words[i:i+6]
            start = t0 + chunk[0]["s"]; end = t0 + chunk[-1]["e"]
            k = "".join(f"{{\\k{int((w['e']-w['s'])*100)}}}{w['w']} " for w in chunk)
            lines.append(f"Dialogue: 0,{_fmt(start)},{_fmt(end)},Default,,0,0,0,,{k.strip()}\n")
    open(path, "w").write("".join(lines))
    return path

def assemble_dialogue(name: str, scene_mp4s: list[str], dialogue_mp3: str,
                      srt_path: str, vertikal: bool = True, res: int = 1080) -> str:
    """Mode dialog (master prompt): gabung klip TANPA audio asli + 1 trek dialog
    + subtitle SRT. Return mp4 final."""
    lst_v = OUT / f"{name}_v.txt"
    lst_v.write_text("".join(f"file '{p}'\n" for p in scene_mp4s))
    silent = str(OUT / f"{name}_silent.mp4")
    final = str(OUT / f"{name}_FINAL.mp4")
    if vertikal:
        W, H = (720, 1280) if res == 720 else (1080, 1920)
    else:
        W, H = (1280, 720) if res == 720 else (1920, 1080)
    scale_f = f",scale={W}:{H}" if res == 720 else ""
    run(["ffmpeg", "-y", "-v", "error", "-f", "concat", "-safe", "0",
         "-i", str(lst_v), "-c", "copy", "-an", silent], timeout=120)
    srt_esc = srt_path.replace("'", r"'\''")
    run(["ffmpeg", "-y", "-v", "error", "-i", silent, "-i", dialogue_mp3,
         "-filter_complex",
         f"[0:v]subtitles='{srt_esc}'{scale_f}[v];[1:a]loudnorm=I=-16:TP=-1.5:LRA=11[a]",
         "-map", "[v]", "-map", "[a]", "-c:v", "libx264", "-pix_fmt", "yuv420p",
         "-crf", "30", "-maxrate", "1.2M", "-bufsize", "3M", "-preset", "veryfast",
         "-c:a", "aac", "-b:a", "96k",
         "-movflags", "+faststart", "-shortest", final],
        timeout=300)
    return final

def assemble(name: str, scene_mp4s: list[str], narasi_mp3s: list[str],
             scenes_words: list[dict], vertikal: bool = True, res: int = 1080) -> str:
    """Gabung -> mux audio -> subtitle karaoke -> loudnorm. Return mp4 final.
    res: 1080 atau 720 (tinggi video vertikal / lebar horizontal)."""
    lst_v = OUT / f"{name}_v.txt"; lst_a = OUT / f"{name}_a.txt"
    lst_v.write_text("".join(f"file '{p}'\n" for p in scene_mp4s))
    lst_a.write_text("".join(f"file '{p}'\n" for p in narasi_mp3s))
    silent = str(OUT / f"{name}_silent.mp4")
    audio = str(OUT / f"{name}_narasi.mp3")
    ass = karaoke_ass(scenes_words, str(OUT / f"{name}.ass"), vertikal)
    final = str(OUT / f"{name}_FINAL.mp4")
    if vertikal:
        W, H = (720, 1280) if res == 720 else (1080, 1920)
    else:
        W, H = (1280, 720) if res == 720 else (1920, 1080)
    scale_f = f",scale={W}:{H}" if res == 720 else ""

    run(["ffmpeg", "-y", "-v", "error", "-f", "concat", "-safe", "0",
         "-i", str(lst_v), "-c", "copy", silent], timeout=120)
    run(["ffmpeg", "-y", "-v", "error", "-f", "concat", "-safe", "0",
         "-i", str(lst_a), "-c", "copy", audio], timeout=60)
    # mux + burn subtitle + loudnorm (-16 LUFS, standar YouTube)
    run(["ffmpeg", "-y", "-v", "error", "-i", silent, "-i", audio,
         "-filter_complex",
         f"[0:v]ass='{ass}'{scale_f}[v];[1:a]loudnorm=I=-16:TP=-1.5:LRA=11[a]",
         "-map", "[v]", "-map", "[a]", "-c:v", "libx264", "-pix_fmt", "yuv420p",
         "-crf", "30", "-maxrate", "1.2M", "-bufsize", "3M", "-preset", "veryfast",
         "-c:a", "aac", "-b:a", "96k",
         "-movflags", "+faststart", "-shortest", final],
        timeout=300)
    return final
