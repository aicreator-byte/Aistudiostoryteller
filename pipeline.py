#!/usr/bin/env python3
"""Orkestrasi 5 tahap storyteller: rencana -> naskah -> suara -> video -> rakit -> SEO.
Pakai: python3 pipeline.py "Asal Usul Nusantara" --hari 7
   atau: python3 pipeline.py --video "Judul" "hook" "ide"   (1 video langsung)"""
from __future__ import annotations
import argparse, json, sys
from core import OUT, audio_duration
from plan import make_plan
from script import make_script
from voice import synthesize
from video import scene_for_narration
from assemble import assemble
from seo import make_seo

def build_video(judul: str, hook: str, ide: str, name: str,
                vertikal: bool = True, voice: str = "pria") -> dict:
    scenes = make_script(judul, hook, ide, 60 if vertikal else 600)
    mp4s, mp3s, words_list = [], [], []
    t0 = 0.0
    for i, sc in enumerate(scenes, 1):
        tag = f"{name}_s{i}"
        mp3, words = synthesize(sc["narasi"], tag)  # gTTS id, 1 suara
        mp4 = scene_for_narration(tag, sc["visual"], mp3, vertikal)
        mp4s.append(mp4); mp3s.append(mp3)
        words_list.append({"words": words, "t0": t0})
        t0 += audio_duration(mp3)
    final = assemble(name, mp4s, mp3s, words_list, vertikal)
    seo = make_seo(judul, " ".join(s["narasi"] for s in scenes), int(t0))
    meta = {"judul": judul, "hook": hook, "durasi": round(t0, 1),
            "adegan": len(scenes), "video": final, "seo": seo}
    (OUT / f"{name}_meta.json").write_text(json.dumps(meta, ensure_ascii=False, indent=1))
    return meta

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("topik", nargs="?", default="Asal Usul Nusantara")
    ap.add_argument("--hari", type=int, default=7)
    ap.add_argument("--video", nargs=3, metavar=("JUDUL", "HOOK", "IDE"))
    ap.add_argument("--landscape", action="store_true")
    a = ap.parse_args()
    vertikal = not a.landscape

    if a.video:
        judul, hook, ide = a.video
        m = build_video(judul, hook, ide, "video1", vertikal)
        print("FINAL:", m["video"], f"({m['durasi']}s, {m['adegan']} adegan)")
        print("Judul opsi 1:", m["seo"]["judul_opsional"][0])
        return

    plan = make_plan(a.topik, a.hari)
    (OUT / "rencana.json").write_text(json.dumps(plan, ensure_ascii=False, indent=1))
    print(f"Rencana {len(plan)} video tersimpan. Contoh:")
    for p in plan[:3]:
        print(f"  H{a.hari and p['hari']} [{p['format']}] {p['judul']}")

if __name__ == "__main__":
    main()
