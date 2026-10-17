"""Storyboard panel-per-klip (teknik Sawit EP1): 1 panel = 1 klip video.
Setiap prompt panel mengulang deskripsi LOCK karakter secara VERBATIM —
inilah yang membuat wajah/pakaian konsisten antar klip saat di-chaining.
Dipakai asisten untuk generate via media pipeline (frame-chaining)."""
from __future__ import annotations

def make_panels(characters: list[dict], scenes: list[dict],
                style: str = "photorealistic luxury lifestyle vlog",
                orient: str = "Vertical 9:16 cinematic shot") -> list[dict]:
    """characters: [{nama, lock, ...}], scenes: [{visual, video, dialog, ...}].
    Return [{n, prompt, dialog}] — prompt siap copy ke generator video."""
    lock_text = "; ".join(f"{c['nama']}: {c['lock']}" for c in characters)
    panels = []
    for i, s in enumerate(scenes):
        action = s.get("video") or s.get("visual", "")
        prompt = f"{orient}, {action}, {lock_text}, {style}"
        panels.append({"n": i + 1, "prompt": prompt,
                       "dialog": s.get("dialog", [])})
    return panels

def panels_markdown(panels: list[dict], judul: str = "") -> str:
    """Ekspor panel sebagai markdown (copy-paste ke generator)."""
    out = [f"# Storyboard — {judul}", ""]
    for p in panels:
        out.append(f"## Panel {p['n']}")
        out.append(f"**Prompt:** {p['prompt']}")
        if p["dialog"]:
            for d in p["dialog"]:
                out.append(f"- Dialog [{d.get('speaker')}] @{d.get('start')}s: \"{d.get('text')}\"")
        out.append("")
    return "\n".join(out)

def panels_for_vlog(n_panel: int, aksi_list: list[str], characters: list[dict],
                    style: str = "photorealistic luxury lifestyle vlog") -> list[dict]:
    """Jalur cepat vlog: daftar aksi per panel + karakter terkunci.
    aksi_list: 1 kalimat Inggris per panel (tanpa deskripsi karakter)."""
    scenes = [{"video": a} for a in aksi_list[:n_panel]]
    return make_panels(characters, scenes, style=style)
