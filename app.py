#!/usr/bin/env python3
"""Storyteller AI Studio — UI/alur ala MarkasAI Storytelling Studio:
Beranda (sapaan+template+daftar proyek) -> Rancang videomu (brief 4 langkah)
-> Periksa skripnya -> Daftar adegan (video AI per adegan + salin prompt)
-> Studio (voice-over + render + ekspor + SEO) -> Channel & kalender konten.
Mesin: NVIDIA NIM (naskah) + gTTS (suara) + image-search + Ken Burns (video)
+ FFmpeg (rakit, karaoke, loudnorm). GET-only (tunnel): semua via path param."""
from __future__ import annotations
import calendar, datetime, json, threading, uuid
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlparse, unquote, quote

import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from script import make_script
from voice import synthesize
from video import scene_for_narration
from assemble import assemble, karaoke_ass
from seo import make_seo
from core import OUT, audio_duration

JOBS: dict[str, dict] = {}
JOBS_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "output", "jobs.json")

def _meta() -> dict:
    m = JOBS.get("_meta")
    if not isinstance(m, dict):
        m = {"channels": {}, "plans": []}
        JOBS["_meta"] = m
    m.setdefault("channels", {}); m.setdefault("plans", [])
    return m

def _save_jobs():
    try:
        tmp = JOBS_FILE + ".tmp"
        with open(tmp, "w") as f:
            json.dump(JOBS, f)
        os.replace(tmp, JOBS_FILE)
    except Exception:
        pass

def _load_jobs():
    try:
        with open(JOBS_FILE) as f:
            data = json.load(f)
        if isinstance(data, dict):
            JOBS.update(data)
        _meta()
    except Exception:
        _meta()

def projects():
    return [(k, v) for k, v in JOBS.items() if k != "_meta" and isinstance(v, dict)]

# 19 gaya visual ala MarkasAI
STYLES = [
    ("stickman", "Stickman warna-warni"), ("kartun", "Kartun flat modern"),
    ("doodle", "Doodle papan tulis"), ("anime-kilong", "Anime kilong"),
    ("cat-air", "Cat air dongeng"), ("anime", "Anime sinematik"),
    ("noir", "Noir komik"), ("pixel", "Pixel retro"),
    ("ceria", "Animasi 2D ceria"), ("clay", "Clay animasi"),
    ("lowpoly", "Low-poly geometris"), ("diorama", "Diorama mini"),
    ("arsitek", "Arsitektur 3D epik"), ("city", "City animasi"),
    ("chroma", "Chroma noir"), ("realis", "Realita sinematik"),
    ("dokfoto", "Dokumenter foto"), ("anjing", "Anjing kota berjas"),
    ("epik", "Epik fantasi"),
]
STYLE_DESC = dict(STYLES)

TEMPLATES = [
    ("sejarah", "Sejarah singkat",
     "Ceritakan kisah nyata yang terlupakan dari sejarah: siapa tokohnya, konflik apa yang ia hadapi, dan akhir yang mengejutkan."),
    ("mitos", "Mitos dan legenda",
     "Angkat sebuah legenda nusantara yang jarang didengar: asal-usulnya, makhluk atau kutukannya, dan pesan moral di baliknya."),
    ("sains", "Sains ringan",
     "Jelaskan satu fenomena sains yang contraintuitif dengan cara sederhana: kenapa bisa terjadi dan contohnya dalam hidup sehari-hari."),
    ("motivasi", "Motivasi",
     "Kisah seseorang yang bangkit dari titik terendah: kegagalannya, momen baliknya, dan pelajaran yang bisa ditiru penonton."),
    ("dongeng", "Dongeng anak",
     "Dongeng anak penuh imajinasi: tokoh hewan yang pemberani, petualangan ajaib, dan akhir bahagia yang hangat."),
    ("fakta", "Fakta dunia",
     "Kumpulkan fakta-fakta dunia yang paling tidak masuk akal tentang topik ini: setiap fakta harus bikin penonton berkata 'hah, serius?'."),
]

CSS = """*{margin:0;box-sizing:border-box}body{font-family:system-ui,-apple-system,sans-serif;
background:#0a0c18;color:#eef0fa;padding:0 0 40px;max-width:860px;margin:0 auto}
.top{display:flex;justify-content:space-between;align-items:center;padding:14px 16px}
.top .logo{font-weight:800;font-size:1.05rem}
.top .logo span{color:#a78bfa}
.top nav a{color:#9aa0b8;text-decoration:none;font-size:.85rem;margin-left:14px}
.top nav a.on{color:#fff;font-weight:700}
.wrap{padding:0 16px}
h1{font-size:1.5rem;margin:6px 0}h2{font-size:1.05rem;margin:18px 0 8px}
.sub{color:#9aa0b8;font-size:.88rem;margin-bottom:10px}
.card{background:#12162b;border:1px solid #222a52;border-radius:16px;padding:16px;margin:12px 0}
.grad{background:linear-gradient(135deg,#6d5ef0,#3ec6b8)}
button{background:linear-gradient(135deg,#7c6cf0,#4fd1c5);color:#fff;border:0;border-radius:12px;
padding:12px 20px;font-weight:700;cursor:pointer;font-size:.95rem}
button.ghost{background:#1e2444}button.danger{background:#3a1d2b;color:#ff8fa3}
button.sm{padding:8px 14px;font-size:.82rem}
.row{display:flex;gap:10px;flex-wrap:wrap;margin:10px 0;align-items:center}
textarea,input[type=text]{width:100%;background:#0d1126;color:#fff;border:1px solid #2a3360;
border-radius:12px;padding:12px;font-size:.95rem;font-family:inherit}
textarea:focus,input:focus{outline:none;border-color:#7c6cf0}
.grid2{display:grid;grid-template-columns:1fr 1fr;gap:10px}
.grid3{display:grid;grid-template-columns:repeat(3,1fr);gap:8px}
.styles{display:grid;grid-template-columns:repeat(3,1fr);gap:8px;margin:10px 0}
.sty{background:#161b38;border:2px solid #232c5c;border-radius:12px;padding:14px 6px;
text-align:center;font-size:.74rem;cursor:pointer;color:#9aa0b8;line-height:1.3}
.sty.on{border-color:#7c6cf0;color:#fff;background:#1d2450}
.opt{background:#161b38;border:2px solid #232c5c;border-radius:12px;padding:12px 14px;
cursor:pointer;font-size:.85rem;color:#9aa0b8;text-align:center}
.opt.on{border-color:#7c6cf0;color:#fff;background:#1d2450}
.proj{display:flex;gap:12px;align-items:center;background:#12162b;border:1px solid #222a52;
border-radius:16px;padding:12px;margin:10px 0}
.thumb{width:84px;height:120px;border-radius:10px;flex:none;display:flex;align-items:center;
justify-content:center;font-size:1.6rem;background:linear-gradient(135deg,#2a2358,#123f3a)}
.proj .inf{flex:1;min-width:0}.proj .inf b{font-size:.95rem;display:block;white-space:nowrap;
overflow:hidden;text-overflow:ellipsis}
.badge{font-size:.7rem;background:#1e2444;padding:3px 10px;border-radius:12px;color:#9aa0b8;
display:inline-block;margin-top:6px}
.badge.ok{background:#123a24;color:#4fd1c5}.badge.run{background:#3a2f10;color:#f5c542}
.scene{border:1px solid #232c5c;border-radius:14px;padding:12px;margin:10px 0;background:#0e1228}
.scene h3{font-size:.92rem;margin-bottom:6px}
.scene .lbl{font-size:.68rem;color:#4fd1c5;text-transform:uppercase;letter-spacing:1px;margin:8px 0 4px}
.scene textarea{min-height:56px;font-size:.84rem}
.pbar{height:8px;background:#1e2444;border-radius:6px;overflow:hidden;margin:8px 0}
.pbar i{display:block;height:100%;background:linear-gradient(90deg,#7c6cf0,#4fd1c5);width:0}
video{width:100%;border-radius:14px;margin-top:8px;max-height:62vh;background:#000}
.tag{background:#1e2444;padding:3px 10px;border-radius:12px;font-size:.76rem;display:inline-block;margin:2px}
#prog{color:#4fd1c5;margin:10px 0}a{color:#4fd1c5;text-decoration:none}
.secttl{font-size:.8rem;font-weight:800;color:#a78bfa;text-transform:uppercase;letter-spacing:1px;margin:16px 0 6px}
.cal{display:grid;grid-template-columns:repeat(7,1fr);gap:4px;margin:10px 0}
.cal .dow{font-size:.68rem;color:#9aa0b8;text-align:center;padding:4px}
.cal .day{background:#12162b;border:1px solid #222a52;border-radius:8px;min-height:52px;
padding:4px;font-size:.68rem;color:#9aa0b8}
.cal .day b{color:#fff;font-size:.72rem}.cal .day .p{font-size:.62rem;color:#4fd1c5;margin-top:2px}
.cal .day.today{border-color:#7c6cf0}.cal .day.dim{opacity:.35}
.stepbar{display:flex;gap:6px;margin:14px 0}
.stp{flex:1;text-align:center;font-size:.7rem;padding:8px 2px;border-radius:10px;background:#141a36;color:#6b7194}
.stp.on{background:#232c66;color:#fff}.stp.done{background:#123a24;color:#4fd1c5}
.chip{font-size:.72rem;background:#1e2444;padding:4px 12px;border-radius:12px;color:#9aa0b8}
select{background:#0d1126;color:#fff;border:1px solid #2a3360;border-radius:10px;padding:10px}"""

def page(title, body, js="", nav="home"):
    navh = f"""<div class="top"><div class="logo">🎬 Storyteller <span>AI Studio</span></div>
<nav><a href="{{B}}/\" class="{'on' if nav=='home' else ''}">Beranda</a>
<a href="{{B}}/channel" class="{'on' if nav=='channel' else ''}">Channel</a>
<a href="{{B}}/pengaturan" class="{'on' if nav=='pengaturan' else ''}">⚙️ Pengaturan</a></nav></div>"""
    return f"""<!DOCTYPE html><html lang="id"><head><meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1"><title>{title}</title>
<style>{CSS}</style></head><body>{navh}<div class="wrap">{body}</div>
<script>var BASE=location.pathname.indexOf("/storyteller")==0?"/storyteller":"";
document.querySelectorAll('.top nav a').forEach(a=>{{a.setAttribute('href',a.getAttribute('href').replace('{{B}}',BASE));}});
{js}</script></body></html>"""

def enc(s: str) -> str:
    return quote(s or "", safe="")

def greeting() -> str:
    h = (datetime.datetime.now(datetime.timezone.utc).hour + 7) % 24
    if h < 10: return "Selamat pagi"
    if h < 15: return "Selamat siang"
    if h < 18: return "Selamat sore"
    return "Selamat malam"

def stepsbar(on: int) -> str:
    names = ["Skrip", "Adegan", "Studio"]
    return "<div class='stepbar'>" + "".join(
        f"<div class='stp {'on' if i==on else ''}'>{s}</div>"
        for i, s in enumerate(names)) + "</div>"

# ---------------------------------------------------------------- BERANDA
def v_home():
    tpl = "".join(
        f"<div class='opt' onclick=\"location.href=BASE+'/brief/{k}'\">{v}</div>"
        for k, v, _ in TEMPLATES)
    cards = []
    for jid, j in sorted(projects(), key=lambda x: x[1].get("dibuat", ""),
                         reverse=True)[:12]:
        n = len(j.get("scenes", []))
        done = sum(1 for s in j.get("scenes", []) if s.get("status") == "siap")
        st = ("<span class='badge ok'>siap render</span>" if j.get("final")
              else f"<span class='badge run'>{done}/{n} adegan</span>" if n
              else "<span class='badge'>skrip</span>")
        cards.append(f"""<div class="proj"><div class="thumb">🎬</div><div class="inf">
<b>{j.get('judul','(tanpa judul)')[:60]}</b>
<span class="chip">{STYLE_DESC.get(j.get('style'),'?')}</span>
<span class="chip">{'Short 9:16' if j.get('fmt')=='short' else 'Long 16:9'}</span>{st}
<div class="row"><button class="sm" onclick="location.href=BASE+'/adegan/{jid}'">Masuk Studio</button>
<button class="sm danger" onclick="if(confirm('Hapus proyek ini?'))location.href=BASE+'/hapus/{jid}'">Hapus</button></div>
</div></div>""")
    body = f"""<h1>{greeting()}, Di 👋</h1>
<p class="sub">Mau bikin video apa hari ini?</p>
<div class="card grad"><h2 style="margin-top:0">🎥 Buat projek baru</h2>
<p class="sub" style="color:#e6e1ff">Dari ide jadi video siap upload — AI yang menyusun semuanya.</p>
<button onclick="location.href=BASE+'/brief'">+ Projek baru</button></div>
<h2>📦 Template siap pakai</h2><div class="grid3">{tpl}</div>
<h2>🗂️ Projek saya</h2>
{''.join(cards) if cards else "<p class='sub'>Belum ada projek. Mulai dari template atau projek baru di atas.</p>"}"""
    return page("Beranda", body, nav="home")

# ---------------------------------------------------------------- BRIEF (Rancang videomu)
def v_brief(tpl=""):
    ide0 = ""
    if tpl:
        for k, v, ex in TEMPLATES:
            if k == tpl:
                ide0 = ex
    sty = "".join(
        f"<div class='sty' data-v='{k}' onclick='pickStyle(this)'>{v}</div>"
        for k, v in STYLES)
    body = f"""<h1>📝 Rancang videomu</h1><p class="sub">Jawab 4 hal, AI yang mengerjakan sisanya.</p>
<div class="card"><div class="secttl">1 · Apa ceritanya?</div>
<p class="sub">Tulis idemu dengan bahasamu sendiri.</p>
<textarea id="ide" rows="4" placeholder="Contoh: Bayangkan hidup sebagai pemburu bernama Arka di sabana Afrika puluhan ribu tahun lalu...">{ide0}</textarea>
<div class="secttl">2 · Seberapa panjang, untuk mana?</div>
<div class="grid2">
<div class="opt on" data-v="short" onclick="pick1(this,'fmt')">📱 Short 9:16<br><span style="font-size:.72rem">±60 dtk · Shorts/TikTok/Reels</span></div>
<div class="opt" data-v="long" onclick="pick1(this,'fmt')">🖥️ Long 16:9<br><span style="font-size:.72rem">±10 mnt · YouTube</span></div></div>
<div class="secttl">3 · Siapa yang bercerita?</div>
<div class="grid2">
<div class="opt on" data-v="pria" onclick="pick1(this,'voi')">🎙️ Narator pria</div>
<div class="opt" data-v="wanita" onclick="pick1(this,'voi')">🎙️ Narator wanita</div></div>
<div class="secttl">4 · Seperti apa tampilannya?</div>
<div class="styles" id="styles">{sty}</div>
<div class="secttl">Pemeran (tokoh konsisten)</div>
<input type="text" id="pemeran" placeholder="Contoh: Arka, pemburu purba berbaju kulit">
<p class="sub">Deskripsi ini disuntik ke setiap adegan agar tokoh tetap sama.</p>
<div class="row"><button onclick="go()">Susun skrip →</button>
<button class="ghost" onclick="location.href=BASE+'/'">Batal</button></div></div>"""
    js = """var style='stickman';
function pickStyle(el){document.querySelectorAll('#styles .sty').forEach(e=>e.classList.remove('on'));el.classList.add('on');style=el.dataset.v;}
document.querySelector('#styles .sty').classList.add('on');
function pick1(el){el.parentElement.querySelectorAll('.opt').forEach(e=>e.classList.remove('on'));el.classList.add('on');}
function go(){var ide=document.getElementById('ide').value.trim();if(!ide){alert('Tulis idemu dulu');return;}
var fmt=document.querySelector('.opt.on[data-v="short"],.opt.on[data-v="long"]').dataset.v;
var voiEl=document.querySelectorAll('.opt.on');var voi='pria';
voiEl.forEach(e=>{if(e.dataset.v=='pria'||e.dataset.v=='wanita')voi=e.dataset.v;});
var pem=document.getElementById('pemeran').value.trim()||'-';
location.href=BASE+'/mulai/'+style+'/'+fmt+'/'+voi+'/'+encodeURIComponent(pem)+'/'+encodeURIComponent(ide);}"""
    return page("Rancang video", body, js, nav="home")

def _new_job(style, fmt, voi, pemeran, ide):
    jid = uuid.uuid4().hex[:8]
    JOBS[jid] = {"status": "jalan", "progress": "mulai...",
                 "dibuat": datetime.datetime.now(datetime.timezone.utc).isoformat(),
                 "style": style if style in STYLE_DESC else "stickman",
                 "fmt": fmt if fmt in ("short", "long") else "short",
                 "voi": voi, "pemeran": pemeran, "ide": ide,
                 "judul": ide[:60], "scenes": [], "res": 1080}
    _save_jobs()
    threading.Thread(target=_gen_skrip, args=(jid,), daemon=True).start()
    return jid

# ---------------------------------------------------------------- SKRIP
def _gen_skrip(jid):
    j = JOBS[jid]
    try:
        j["progress"] = "AI menulis naskah per adegan..."
        vertikal = j["fmt"] == "short"
        scenes = make_script(j["judul"], j["ide"][:120], j["ide"],
                             60 if vertikal else 600, STYLE_DESC[j["style"]])
        char = "" if j["pemeran"] == "-" else f" Character: {j['pemeran']}, consistent appearance."
        for s in scenes:
            s["visual"] = f"{STYLE_DESC[j['style']]} style.{char} {s['visual']}"
            s.update(mp3=None, mp4=None, words=None, status="baru")
        j["scenes"] = scenes
        j["status"] = "selesai"; _save_jobs()
    except Exception as e:
        j["status"] = "gagal"; j["progress"] = str(e)[:200]; _save_jobs()

def v_skrip_wait(jid):
    return page("Skrip", stepsbar(0) +
        "<div class='card'><div id='prog'>✍️ AI menulis naskah per adegan...</div>"
        "<p class='sub'>Halaman pindah otomatis.</p></div>",
        f"setTimeout(()=>location.href=BASE+'/skrip/{jid}',3000);")

def v_skrip(jid):
    j = JOBS[jid]
    if j["status"] == "jalan":
        return page("Skrip", stepsbar(0) +
            f"<div class='card'><div id='prog'>{j['progress']}</div><p class='sub'>AI sedang menulis, halaman refresh otomatis.</p></div>",
            "setTimeout(()=>location.reload(),3000);")
    if j["status"] == "gagal":
        return page("Skrip", stepsbar(0) +
            f"<div class='card'>Gagal: {j['progress']}<br><br><button onclick=\"location.href=BASE+'/'\">← Beranda</button></div>")
    cards = []
    for i, s in enumerate(j["scenes"]):
        cards.append(f"""<div class="scene"><h3>Adegan {i+1}</h3>
<div class="lbl">Storyboard (visual statis)</div><textarea id="v{i}" rows="2">{s['visual']}</textarea>
<div class="lbl">Prompt video AI (gerakan kamera + motion)</div><textarea id="p{i}" rows="2">{s.get('video','')}</textarea>
<div class="lbl">Narasi</div><textarea id="n{i}" rows="3">{s['narasi']}</textarea>
<div class="row"><button class="ghost sm" onclick="save({i})">Simpan adegan {i+1}</button>
<span class="badge" id="b{i}">belum disimpan</span></div></div>""")
    n = len(j["scenes"])
    body = stepsbar(0) + f"""<h1>📖 Periksa skripnya</h1>
<p class="sub">{n} adegan · "{j.get('judul','')[:50]}" · ubah sesukamu, lalu lanjut.</p>
<div class="card"><button onclick="collect()">Lanjut ke Daftar Adegan →</button></div>
{''.join(cards)}
<div class="card"><button onclick="collect()">Lanjut ke Daftar Adegan →</button></div>"""
    js = f"""var N={n};
function val(id){{return encodeURIComponent(document.getElementById(id).value);}}
function save(i){{fetch(BASE+'/save/{jid}/'+i+'/'+val('v'+i)+'/'+val('n'+i)+'/'+val('p'+i)).then(()=>{{var b=document.getElementById('b'+i);
b.textContent='tersimpan';b.className='badge ok';}});}}
async function collect(){{for(let i=0;i<N;i++){{await fetch(BASE+'/save/{jid}/'+i+'/'+val('v'+i)+'/'+val('n'+i)+'/'+val('p'+i));}}location.href=BASE+'/adegan/{jid}';}}"""
    return page("Skrip", body, js)

# ---------------------------------------------------------------- ADEGAN (Daftar adegan)
def _gen_scene(jid, idx):
    j = JOBS[jid]
    s = j["scenes"][idx]
    try:
        s["status"] = "jalan"; _save_jobs()
        tag = f"{jid}_s{idx+1}"
        mp3, words = synthesize(s["narasi"], tag)
        mp4 = scene_for_narration(tag, s.get("video") or s["visual"], mp3,
                                  j["fmt"] == "short", storyboard=s["visual"])
        s.update(mp3=mp3, mp4=mp4, words=words, status="siap")
    except Exception as e:
        s["status"] = f"gagal: {str(e)[:80]}"
    _save_jobs()

def _gen_all(jid):
    j = JOBS[jid]
    for i in range(len(j["scenes"])):
        if j["scenes"][i]["status"] != "siap":
            _gen_scene(jid, i)

def v_adegan(jid):
    j = JOBS[jid]
    items = []
    for i, s in enumerate(j["scenes"]):
        st = s["status"]
        if st == "siap":
            badge = "<span class='badge ok'>siap</span>"
            vid = (f"<video controls playsinline preload='metadata' src='/storyteller/file/{os.path.basename(s['mp4'])}'></video>"
                   if s.get("mp4") else "")
            btn = (f"<button class='ghost sm' onclick=\"genS('{jid}',{i},this)\">🔁 Buat ulang</button>")
        elif st == "jalan":
            badge = "<span class='badge run'>membuat video...</span>"; vid = ""; btn = ""
        else:
            badge = "<span class='badge'>belum dibuat</span>"; vid = ""
            btn = (f"<button class='sm' onclick=\"genS('{jid}',{i},this)\">🎬 Buat dengan AI</button>")
        items.append(f"""<div class="scene" id="sc{i}"><h3>Adegan {i+1} {badge}</h3>
<p class="sub">{s['narasi'][:110]}...</p>{vid}
<div class="row">{btn}
<button class="ghost sm" onclick="salinPrompt({i})">📋 Salin prompt</button></div>
<textarea id="p{i}" style="display:none">{s.get('video') or s['visual']}</textarea></div>""")
    n = len(j["scenes"]); done = sum(1 for s in j["scenes"] if s["status"] == "siap")
    pct = int(done / n * 100) if n else 0
    nxt = (f"<button onclick=\"location.href=BASE+'/studio/{jid}'\">Lanjut ke Studio →</button>"
           if done == n and n else
           f"<button onclick=\"genAll('{jid}')\">⚡ Buat semua video ({n} adegan)</button> "
           f"<button class='ghost' onclick='location.reload()'>🔄 Refresh</button>")
    body = stepsbar(1) + f"""<h1>🎞️ Daftar adegan</h1>
<p class="sub">"{j.get('judul','')[:50]}" · {STYLE_DESC.get(j.get('style'),'?')}</p>
<div class="card"><div class="pbar"><i id="bar" style="width:{pct}%"></i></div>
<p class="sub" id="prog">{done}/{n} video siap</p><div class="row">{nxt}</div></div>
{''.join(items)}"""
    js = f"""var J='{jid}',N={n};
function salinPrompt(i){{var t=document.getElementById('p'+i).value;
navigator.clipboard.writeText(t).then(()=>alert('Prompt adegan '+(i+1)+' tersalin'));}}
function genS(j,i,btn){{btn.disabled=true;btn.textContent='Membuat...';
fetch(BASE+'/gen/'+j+'/'+i).then(()=>poll());}}
function genAll(j){{fetch(BASE+'/genall/'+j).then(()=>poll());}}
function poll(){{fetch(BASE+'/status/'+J).then(r=>r.json()).then(d=>{{
var pct=Math.round(d.done/d.total*100);
document.getElementById('bar').style.width=pct+'%';
document.getElementById('prog').textContent=d.done+'/'+d.total+' video siap';
if(d.done<d.total)setTimeout(poll,4000);else location.reload();}});}}
setTimeout(poll,3000);"""
    return page("Adegan", body, js)

# ---------------------------------------------------------------- STUDIO
def _assemble(jid):
    j = JOBS[jid]
    try:
        j["asm"] = "jalan"; j["progress"] = "Merakit video..."; _save_jobs()
        vertikal = j["fmt"] == "short"
        mp4s, mp3s, wl, t0 = [], [], [], 0.0
        for s in j["scenes"]:
            mp4s.append(s["mp3"] and s["mp4"]); mp3s.append(s["mp3"])
            wl.append({"words": s["words"], "t0": t0})
            t0 += audio_duration(s["mp3"])
        final = assemble(jid, mp4s, mp3s, wl, vertikal, res=j.get("res", 1080))
        srt = []; k = 1
        for w in wl:
            for g in [w["words"][i:i+8] for i in range(0, len(w["words"]), 8)]:
                if not g: continue
                def f(t):
                    ms = int(t*1000)
                    return f"{ms//3600000:02d}:{(ms//60000)%60:02d}:{(ms//1000)%60:02d},{ms%1000:03d}"
                srt.append(f"{k}\n{f(w['t0']+g[0]['s'])} --> {f(w['t0']+g[-1]['e'])}\n{' '.join(x['w'] for x in g)}\n")
                k += 1
        open(str(OUT / f"{jid}.srt"), "w").write("\n".join(srt))
        j["seo"] = make_seo(j["judul"], " ".join(s["narasi"] for s in j["scenes"]), int(t0))
        j["final"] = final; j["durasi"] = round(t0, 1)
        j["asm"] = "selesai"; _save_jobs()
    except Exception as e:
        j["asm"] = "gagal"; j["progress"] = str(e)[:200]; _save_jobs()

def v_studio(jid):
    j = JOBS[jid]
    head = stepsbar(2) + f"<h1>🎛️ Studio</h1><p class='sub'>\"{j.get('judul','')[:50]}\"</p>"
    if j.get("final"):
        seo = j.get("seo") or {}
        tags = "".join(f"<span class='tag'>{t}</span>" for t in seo.get("tags", [])[:20])
        judul = "".join(f"<li>{x}</li>" for x in seo.get("judul_opsional", []))
        vf = os.path.basename(j["final"])
        res = j.get("res", 1080)
        body = head + f"""<div class="card"><h2>✅ Video jadi!</h2>
<video controls playsinline src="/storyteller/file/{vf}"></video>
<p class="sub">{j['durasi']} detik · {len(j['scenes'])} adegan · {res}p · 30fps · subtitle karaoke · loudnorm -16 LUFS</p>
<div class="row"><a href="/storyteller/file/{vf}" download><button>⬇️ Unduh MP4</button></a>
<a href="/storyteller/file/{jid}.srt" download><button class="ghost">Unduh subtitle .srt</button></a>
<button class="ghost" onclick="if(confirm('Render ulang dengan resolusi lain?'))location.href=BASE+'/render-ulang/{jid}'">🔁 Render ulang</button></div></div>
<div class="card"><h2>🚀 Auto SEO — siap tempel ke YouTube</h2>
<div class="secttl">Opsi judul (klik untuk salin)</div><ul id="jl">{judul}</ul>
<div class="secttl">Deskripsi</div><p class="sub" id="ds">{seo.get('deskripsi','')[:400]}...</p>
<div class="row"><button class="ghost sm" onclick="salin('ds')">📋 Salin deskripsi</button>
<button class="ghost sm" onclick="salinTags()">📋 Salin tags</button></div>
<div class="secttl">Tags</div><div id="tg">{tags}</div></div>
<div class="card"><div class="row"><button class="ghost" onclick="location.href=BASE+'/'">← Beranda</button>
<button class="ghost" onclick="location.href=BASE+'/channel'">📅 Jadwalkan ke channel →</button></div></div>"""
        js = """function salin(id){navigator.clipboard.writeText(document.getElementById(id).textContent).then(()=>alert('Tersalin'));}
function salinTags(){var t=[...document.querySelectorAll('#tg .tag')].map(e=>e.textContent).join(',');
navigator.clipboard.writeText(t).then(()=>alert('Tags tersalin'));}
document.querySelectorAll('#jl li').forEach(li=>{li.style.cursor='pointer';
li.onclick=()=>navigator.clipboard.writeText(li.textContent).then(()=>alert('Judul tersalin'));});"""
        return page("Studio", body, js)
    if j.get("asm") == "jalan":
        return page("Studio", head +
            f"<div class='card'><div class='pbar'><i style='width:60%'></i></div><div id='prog'>{j.get('progress','Merakit...')}</div></div>",
            "setTimeout(()=>location.reload(),4000);")
    if j.get("asm") == "gagal":
        return page("Studio", head +
            f"<div class='card'>❌ Gagal: {j.get('progress','?')}<br><br><button onclick=\"location.href=BASE+'/render/{jid}/'+(window._res||1080)\">🔁 Coba lagi</button></div>")
    # pilih ekspor dulu, baru render
    res = j.get("res", 1080)
    body = head + f"""<div class="card"><h2>🎙️ Voice-over</h2>
<p class="sub">{len(j['scenes'])} narasi adegan sudah dibuat di tahap Adegan. Untuk buat ulang suara per adegan, kembali ke <a href="/storyteller/adegan/{jid}">Daftar adegan</a>.</p></div>
<div class="card"><h2>⚙️ Pengaturan ekspor</h2>
<div class="secttl">Resolusi</div><div class="row">
<div class="opt {'on' if res==1080 else ''}" data-v="1080" onclick="pickR(this)">1080p <span class="chip">Full HD</span></div>
<div class="opt {'on' if res==720 else ''}" data-v="720" onclick="pickR(this)">720p <span class="chip">HD ringan</span></div></div>
<div class="secttl">Lainnya (otomatis)</div>
<p class="sub"><span class="chip">30 fps</span> <span class="chip">Subtitle karaoke</span> <span class="chip">Loudnorm -16 LUFS</span> <span class="chip">Faststart</span></p>
<div class="row"><button onclick="render()">🎬 Render video</button></div></div>"""
    js = f"""var _res={res};
function pickR(el){{document.querySelectorAll('.opt').forEach(e=>e.classList.remove('on'));el.classList.add('on');_res=el.dataset.v;}}
function render(){{location.href=BASE+'/render/{jid}/'+_res;}}"""
    return page("Studio", body, js)

# ---------------------------------------------------------------- CHANNEL & KALENDER
def v_channel():
    m = _meta()
    chs = m["channels"]
    items = "".join(
        f"<div class='proj'><div class='thumb'>📺</div><div class='inf'><b>{c['nama']}</b>"
        f"<span class='chip'>{sum(1 for p in m['plans'] if p['cid']==cid)} video terjadwal</span>"
        f"<div class='row'><button class='sm' onclick=\"location.href=BASE+'/channel/{cid}'\">Buka kalender</button></div></div></div>"
        for cid, c in chs.items())
    body = f"""<h1>📺 Channel saya</h1><p class="sub">Kelola channel dan jadwal upload konten.</p>
<div class="card"><h2 style="margin-top:0">+ Channel baru</h2>
<div class="row"><input type="text" id="cn" placeholder="Nama channel, contoh: VastSpecies" style="flex:1">
<button onclick="buat()">Buat</button></div></div>
{items if items else "<p class='sub'>Belum ada channel.</p>"}
<div class="card"><button class="ghost" onclick="location.href=BASE+'/'">← Beranda</button></div>"""
    js = """function buat(){var n=document.getElementById('cn').value.trim();if(!n){alert('Isi nama channel');return;}
location.href=BASE+'/channel-buat/'+encodeURIComponent(n);}"""
    return page("Channel", body, js, nav="channel")

def v_calendar(cid, ym=""):
    m = _meta()
    c = m["channels"].get(cid)
    if not c:
        return page("Channel", "<div class='card'>Channel tidak ada. <a href='/channel'>← kembali</a></div>", nav="channel")
    today = datetime.date.today()
    if not ym or len(ym) != 7:
        ym = today.strftime("%Y-%m")
    y, mo = int(ym[:4]), int(ym[5:7])
    prevm = (datetime.date(y, mo, 1) - datetime.timedelta(days=1)).strftime("%Y-%m")
    nxt = (datetime.date(y, mo, 28) + datetime.timedelta(days=8)).strftime("%Y-%m")[:7]
    plans = [p for p in m["plans"] if p["cid"] == cid]
    bydate: dict[str, list] = {}
    for p in plans:
        bydate.setdefault(p["date"], []).append(p)
    cells = []
    for d in ["Sn", "Sl", "Rb", "Km", "Jm", "Sb", "Mn"]:
        cells.append(f"<div class='dow'>{d}</div>")
    for week in calendar.monthcalendar(y, mo):
        for dnum in week:
            if not dnum:
                cells.append("<div class='day dim'></div>"); continue
            ds = f"{y:04d}-{mo:02d}-{dnum:02d}"
            ps = "".join(f"<div class='p'>📌 {p['title'][:18]}</div>" for p in bydate.get(ds, []))
            cls = "today" if ds == today.isoformat() else ""
            cells.append(
                f"<div class='day {cls}' onclick=\"tanya('{ds}')\"><b>{dnum}</b>{ps}</div>")
    projs = "".join(
        f"<div class='opt' onclick=\"jadwal('{jid}')\">{j.get('judul','?')[:28]}</div>"
        for jid, j in projects() if j.get("final")) or "<p class='sub'>Belum ada video jadi.</p>"
    n_plan = len(plans); n_done = 0
    body = f"""<h1>📅 {c['nama']}</h1>
<p class="sub">{n_plan} rencana · {n_done} diproduksi · {n_plan-n_done} idle</p>
<div class="card"><div class="row">
<button class="ghost sm" onclick="location.href=BASE+'/channel/{cid}/{prevm}'">←</button>
<b>{calendar.month_name[mo]} {y}</b>
<button class="ghost sm" onclick="location.href=BASE+'/channel/{cid}/{nxt}'">→</button></div>
<div class="cal">{''.join(cells)}</div>
<p class="sub">Klik tanggal untuk menjadwalkan video.</p></div>
<div class="card"><h2>🎬 Video siap dijadwalkan</h2><div class="grid2">{projs}</div>
<p class="sub">Pilih video, lalu klik tanggal di kalender.</p></div>
<div class="card"><button class="ghost" onclick="location.href=BASE+'/channel'">← Semua channel</button></div>"""
    js = f"""var _vid='';
function jadwal(j){{_vid=j;alert('Video dipilih. Sekarang klik tanggal di kalender.');}}
function tanya(ds){{if(!_vid){{alert('Pilih video dulu di bawah.');return;}}
var t=prompt('Judul untuk '+ds+':','');if(t===null)return;
location.href=BASE+'/plan/{cid}/'+ds+'/'+encodeURIComponent(_vid)+'/'+encodeURIComponent(t||'-');}}"""
    return page("Kalender", body, js, nav="channel")

# ---------------------------------------------------------------- handler
def redir(path: str) -> str:
    return f"""<!DOCTYPE html><html><head><meta charset="UTF-8"></head><body>
<script>var BASE=location.pathname.indexOf("/storyteller")==0?"/storyteller":"";
location.href=BASE+'{path}';</script></body></html>"""

class H(BaseHTTPRequestHandler):
    def _send(self, html, code=200, ctype="text/html; charset=utf-8"):
        b = html.encode() if isinstance(html, str) else html
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(b)))
        self.end_headers()
        self.wfile.write(b)

    def do_GET(self):
        try:
            self._route()
        except BrokenPipeError:
            pass
        except Exception as e:
            try: self._send(f"<div class='card'>Error: {e}</div>", 500)
            except Exception: pass

    def _route(self):
        p = urlparse(self.path).path
        if p == "/" or p == "":
            self._send(v_home()); return
        if p == "/brief":
            self._send(v_brief()); return
        if p.startswith("/brief/"):
            self._send(v_brief(p[len("/brief/"):].split("/")[0])); return
        if p.startswith("/mulai/"):
            parts = p[len("/mulai/"):].split("/")
            if len(parts) >= 5:
                style, fmt, voi = parts[0], parts[1], parts[2]
                pemeran = unquote(parts[3]); ide = unquote("/".join(parts[4:]))
                jid = _new_job(style, fmt, voi, pemeran, ide)
                self._send(redir(f"/skripwait/{jid}")); return
            self._send("404", 404); return
        if p.startswith("/skripwait/"):
            self._send(v_skrip_wait(p.rsplit("/", 1)[-1])); return
        if p.startswith("/skrip/"):
            jid = p.rsplit("/", 1)[-1]
            self._send(v_skrip(jid) if jid in JOBS else "404", 404 if jid not in JOBS else 200); return
        if p.startswith("/save/"):
            parts = p[len("/save/"):].split("/")
            ok = False
            if len(parts) >= 4 and parts[0] in JOBS:
                j = JOBS[parts[0]]; idx = int(parts[1])
                if 0 <= idx < len(j.get("scenes", [])):
                    j["scenes"][idx]["visual"] = unquote(parts[2])
                    j["scenes"][idx]["narasi"] = unquote(parts[3])
                    if len(parts) >= 5:
                        j["scenes"][idx]["video"] = unquote(parts[4])
                    _save_jobs(); ok = True
            self._send('{"ok":true}' if ok else '{"ok":false}',
                       200 if ok else 404, "application/json"); return
        if p.startswith("/adegan/"):
            jid = p.rsplit("/", 1)[-1]
            self._send(v_adegan(jid) if jid in JOBS else "404",
                       200 if jid in JOBS else 404); return
        if p.startswith("/genall/"):
            jid = p.rsplit("/", 1)[-1]
            if jid in JOBS:
                threading.Thread(target=_gen_all, args=(jid,), daemon=True).start()
            self._send('{"ok":true}', ctype="application/json"); return
        if p.startswith("/gen/"):
            parts = p[len("/gen/"):].split("/")
            if len(parts) == 2 and parts[0] in JOBS:
                jid, idx = parts[0], int(parts[1])
                if 0 <= idx < len(JOBS[jid].get("scenes", [])):
                    threading.Thread(target=_gen_scene, args=(jid, idx), daemon=True).start()
            self._send('{"ok":true}', ctype="application/json"); return
        if p.startswith("/status/"):
            jid = p.rsplit("/", 1)[-1]
            j = JOBS.get(jid, {})
            sc = j.get("scenes", [])
            done = sum(1 for s in sc if s.get("status") == "siap")
            self._send(json.dumps({"done": done, "total": len(sc)}),
                       ctype="application/json"); return
        if p.startswith("/studio/"):
            jid = p.rsplit("/", 1)[-1]
            self._send(v_studio(jid) if jid in JOBS else "404",
                       200 if jid in JOBS else 404); return
        if p.startswith("/render-ulang/"):
            jid = p.rsplit("/", 1)[-1]
            if jid in JOBS:
                JOBS[jid].pop("final", None); JOBS[jid]["asm"] = None; _save_jobs()
            self._send(redir(f"/studio/{jid}")); return
        if p.startswith("/render/"):
            parts = p[len("/render/"):].split("/")
            if len(parts) == 2 and parts[0] in JOBS:
                jid = parts[0]
                try: res = int(parts[1])
                except ValueError: res = 1080
                JOBS[jid]["res"] = 720 if res == 720 else 1080
                JOBS[jid].pop("final", None); JOBS[jid]["asm"] = "jalan"
                threading.Thread(target=_assemble, args=(jid,), daemon=True).start()
                _save_jobs()
                self._send(redir(f"/studio/{jid}")); return
            self._send("404", 404); return
        if p.startswith("/hapus/"):
            jid = p.rsplit("/", 1)[-1]
            JOBS.pop(jid, None); _save_jobs()
            self._send(redir("/")); return
        if p == "/channel":
            self._send(v_channel()); return
        if p == "/pengaturan" or p == "/pengaturan/ok":
            self._send(v_pengaturan(saved=p.endswith("/ok"))); return
        if p.startswith("/simpan/"):
            blob = unquote(p[len("/simpan/"):])
            updates = {}
            for pair in blob.split("&"):
                if "=" in pair:
                    k, v = pair.split("=", 1)
                    if k.strip() and v:
                        updates[k.strip()] = v
            write_env_file(updates)
            reload_env()
            self._send(redir("/pengaturan/ok")); return
        if p.startswith("/channel-buat/"):
            nama = unquote(p[len("/channel-buat/"):].split("/")[0])
            if nama:
                cid = uuid.uuid4().hex[:8]
                _meta()["channels"][cid] = {"nama": nama}; _save_jobs()
                self._send(redir(f"/channel/{cid}")); return
            self._send(redir("/channel")); return
        if p.startswith("/channel/"):
            rest = p[len("/channel/"):].split("/")
            cid = rest[0]
            ym = rest[1] if len(rest) > 1 else ""
            self._send(v_calendar(cid, ym)); return
        if p.startswith("/plan/"):
            parts = p[len("/plan/"):].split("/")
            if len(parts) >= 4:
                cid, date, vid = parts[0], parts[1], parts[2]
                title = unquote("/".join(parts[3:]))
                m = _meta()
                if cid in m["channels"]:
                    m["plans"].append({"id": uuid.uuid4().hex[:6], "cid": cid,
                                      "date": date, "vid": vid,
                                      "title": title if title != "-" else
                                      (JOBS.get(vid, {}).get("judul", "?")[:40])})
                    _save_jobs()
                self._send(redir(f"/channel/{cid}")); return
            self._send("404", 404); return
        if p.startswith("/file/"):
            fn = p.rsplit("/", 1)[-1].replace("..", "")
            fp = os.path.join(OUT, fn)
            if not os.path.isfile(fp):
                self._send("tidak ada", 404); return
            ct = "video/mp4" if fn.endswith(".mp4") else "text/plain"
            self.send_response(200)
            self.send_header("Content-Type", ct)
            self.send_header("Content-Length", str(os.path.getsize(fp)))
            self.end_headers()
            with open(fp, "rb") as f:
                self.wfile.write(f.read())
            return
        self._send("404", 404)

    def log_message(self, *a):
        pass


# ---------------------------------------------------------------- PENGATURAN
from core import read_env_file, write_env_file, reload_env

PENGATURAN = [
    ("⚡ LLM langsung — tanpa router", [
        ("ANTHROPIC_API_KEY", "Anthropic API key (Claude)", "password", ""),
        ("ANTHROPIC_MODEL", "Model Claude", "text", ""),
        ("OPENAI_API_KEY", "OpenAI API key (GPT)", "password", ""),
        ("OPENAI_MODEL", "Model GPT", "text", ""),
        ("GEMINI_API_KEY", "Google API key (Gemini)", "password", ""),
        ("GEMINI_MODEL", "Model Gemini", "text", ""),
    ]),
    ("🤖 LLM — pembuat naskah & prompt video", [
        ("LLM_CHAIN", "Urutan fallback (koma)", "text",
         "cth: anthropic,openai,gemini,nvidia,openrouter"),
        ("NVIDIA_API_KEY", "NVIDIA API key", "password", ""),
        ("NIM_MODEL", "Model NVIDIA", "text", ""),
        ("OPENROUTER_API_KEY", "OpenRouter API key", "password", ""),
        ("OPENROUTER_MODEL", "Model OpenRouter", "text", ""),
    ]),
    ("🎬 Video AI — pembuat video per adegan", [
        ("VIDEO_CHAIN", "Urutan provider (koma)", "text",
         "cth: fal,minimax,kenburns — langsung: kling,minimax,runway,luma · aggregator: fal,replicate"),
        ("FAL_KEY", "fal.ai key (aggregator)", "password", ""),
        ("FAL_MODEL", "Model fal.ai", "text", ""),
        ("REPLICATE_API_TOKEN", "Replicate token (aggregator)", "password", ""),
        ("REPLICATE_MODEL", "Model Replicate", "text", ""),
        ("KLING_API_KEY", "Kling API key", "password", "stub — pakai fal/replicate untuk Kling"),
        ("MINIMAX_API_KEY", "MiniMax/Hailuo API key", "password", ""),
        ("RUNWAY_API_KEY", "Runway API key", "password", ""),
        ("LUMA_API_KEY", "Luma API key", "password", ""),
    ]),
]

def _mask(v: str) -> str:
    return v[:4] + "…" + v[-4:] if len(v) > 10 else ("••••" if v else "")

def v_pengaturan(saved=False):
    env = read_env_file()
    sects = []
    for title, fields in PENGATURAN:
        rows = []
        for key, label, typ, hint in fields:
            cur = env.get(key, "")
            if typ == "password":
                inp = (f"<input type='password' data-k='{key}' placeholder="
                       f"'{('tersimpan: '+_mask(cur)) if cur else 'belum diisi'}'>")
            else:
                inp = (f"<input type='text' data-k='{key}' value='{cur}' "
                       f"placeholder='{hint}'>")
            note = (f"<p class='sub'>{hint}</p>"
                    if typ == "text" and hint and not cur else "")
            soon = (f"<p class='sub'>⏳ {hint}</p>"
                    if typ == "password" and hint else "")
            rows.append(f"<div class='secttl'>{label} <span class='chip'>{key}</span></div>{inp}{note}{soon}")
        sects.append(f"<div class='card'><h2>{title}</h2>{''.join(rows)}</div>")
    ok = ("<div class='card grad'><b>✅ Tersimpan ke .env</b>"
          "<p class='sub' style='color:#e6e1ff'>Berlaku segera, tanpa restart.</p></div>"
          if saved else "")
    body = f"""<h1>⚙️ Pengaturan</h1>
<p class="sub">API key & urutan provider. Disimpan ke file <span class="chip">.env</span> (tidak ikut ke GitHub).</p>
{ok}{''.join(sects)}
<div class="card"><div class="row"><button onclick="simpan()">💾 Simpan</button>
<button class="ghost" onclick="location.href=BASE+'/'">Batal</button></div>
<p class="sub">Kolom key yang dikosongkan = pertahankan nilai lama.</p></div>"""
    js = """function simpan(){var ps=[];
document.querySelectorAll('[data-k]').forEach(e=>{var v=e.value.trim();
if(v)ps.push(encodeURIComponent(e.dataset.k+'='+v));});
if(!ps.length){alert('Tidak ada perubahan');return;}
location.href=BASE+'/simpan/'+ps.join('&');}"""
    return page("Pengaturan", body, js, nav="pengaturan")

if __name__ == "__main__":
    _load_jobs()
    ThreadingHTTPServer(("127.0.0.1", 8091), H).serve_forever()
