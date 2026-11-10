"""Galeri dan animasi spanning tree untuk aplikasi Streamlit (komponen kustom CCv2, hanya tampilan)."""

from __future__ import annotations

import re

import streamlit as st

from wiener.analisis import HasilGraf
from wiener.gambar import posisi_graf

LEBAR = 1000
TEPI = 70

_HTML = """
<div class="galeri">
  <div class="bar">
    <div class="tab" role="tablist" aria-label="Tampilan">
      <button type="button" data-v="grid">Galeri</button>
      <button type="button" data-v="anim">Animasi</button>
    </div>
    <label class="saring-l">Saring <select class="saring"></select></label>
    <span class="info"></span>
  </div>
  <div class="isi"></div>
</div>
"""

_CSS = """
.galeri { font-family: var(--st-font); color: var(--st-text-color); font-size: 0.9rem; }
.bar { display: flex; flex-wrap: wrap; gap: 10px 16px; align-items: center; margin-bottom: 12px; }
.tab { display: inline-flex; background: var(--st-secondary-background-color); border-radius: 999px; padding: 3px; }
.tab button { border: 0; background: transparent; color: var(--st-text-color); font: inherit; padding: 5px 16px;
  border-radius: 999px; cursor: pointer; transition: background .2s, color .2s; }
.tab button.aktif { background: var(--st-primary-color); color: #fff; box-shadow: 0 2px 8px rgba(0,0,0,.15); }
select, .kontrol button {
  font: inherit; color: var(--st-text-color); background: var(--st-secondary-background-color);
  border: 1px solid var(--st-border-color); border-radius: var(--st-base-radius); padding: 4px 10px; cursor: pointer;
}
.saring-l { display: inline-flex; gap: 8px; align-items: center; }
.info { opacity: .75; margin-left: auto; }
.kisi { display: grid; grid-template-columns: repeat(auto-fill, minmax(150px, 1fr)); gap: 12px; }
.kartu {
  background: var(--st-secondary-background-color); border: 1px solid var(--st-border-color);
  border-radius: calc(var(--st-base-radius) * 1.5); padding: 8px 8px 6px; cursor: pointer;
  opacity: 0; transform: translateY(8px) scale(.98); animation: muncul .45s ease forwards;
  transition: transform .2s ease, box-shadow .2s ease, border-color .2s ease;
}
.kartu:hover { transform: translateY(-3px); box-shadow: 0 8px 22px rgba(0,0,0,.18); border-color: var(--st-primary-color); }
.kartu svg { width: 100%; height: auto; display: block; }
.kartu { position: relative; }
.kartu .cap { display: flex; justify-content: space-between; gap: 6px; font-size: .78rem; margin-top: 4px;
  opacity: .9; white-space: nowrap; }
.kartu .lencana { position: absolute; top: 6px; right: 6px; }
.lencana { font-size: .68rem; padding: 1px 7px; border-radius: 999px; font-weight: 600; white-space: nowrap; }
.lencana.min { background: var(--st-green-background-color); color: var(--st-green-text-color); }
.lencana.maks { background: var(--st-orange-background-color); color: var(--st-orange-text-color); }
@keyframes muncul { to { opacity: 1; transform: none; } }
.halaman { display: flex; gap: 8px; align-items: center; justify-content: center; margin-top: 14px; }
.halaman button { font: inherit; color: var(--st-text-color); background: var(--st-secondary-background-color);
  border: 1px solid var(--st-border-color); border-radius: var(--st-base-radius); padding: 4px 12px; cursor: pointer; }
.halaman button:disabled { opacity: .4; cursor: default; }
.panggung { background: var(--st-secondary-background-color); border: 1px solid var(--st-border-color);
  border-radius: calc(var(--st-base-radius) * 2); padding: 12px; }
.panggung svg { width: 100%; height: auto; display: block; max-height: 62vh; }
.judul-anim { display: flex; align-items: baseline; gap: 12px; flex-wrap: wrap; margin: 2px 4px 8px; }
.judul-anim .no { font-weight: 700; font-size: 1.15rem; }
.judul-anim .w { font-size: 1.15rem; color: var(--st-primary-color); font-weight: 700; }
.kontrol { display: flex; flex-wrap: wrap; gap: 8px; align-items: center; margin-top: 10px; }
.kontrol input[type=range] { flex: 1; min-width: 160px; accent-color: var(--st-primary-color); }
.kontrol .main { background: var(--st-primary-color); color: #fff; border-color: var(--st-primary-color); min-width: 92px; }
.s-buang { stroke: var(--st-text-color); opacity: .22; stroke-width: 2; stroke-dasharray: 7 6; }
.s-pohon { stroke: var(--st-primary-color); stroke-width: 6; stroke-linecap: round; }
.kartu .s-pohon { stroke-width: 9; }
.kartu .s-buang { stroke-width: 3; stroke-dasharray: 10 9; }
.tumbuh { stroke-dasharray: var(--p); stroke-dashoffset: var(--p); animation: tumbuh .5s ease forwards; }
@keyframes tumbuh { to { stroke-dashoffset: 0; } }
.t { fill: var(--st-text-color); stroke: var(--st-secondary-background-color); stroke-width: 3; }
.t.merah { fill: #d62728; }
.panggung .t { animation: denyut .5s ease both; }
@keyframes denyut { from { r: 4; } }
.lbl { fill: var(--st-text-color); font-size: 26px; font-style: italic; pointer-events: none; }
.lbl.merah { fill: #d62728; }
.kosong { padding: 30px; text-align: center; opacity: .7; }
"""

_JS = """
const SIMPAN = new WeakMap();
const PER_HALAMAN = 36;
const KECEPATAN = { lambat: 2600, sedang: 1500, cepat: 650 };

function labelSvg(nama) {
  let m = /^([A-Za-z]+)_?(\\d+)_(\\d+)$/.exec(nama);
  if (m) return `${m[1]}<tspan dy="8" font-size="18">${m[2]},${m[3]}</tspan>`;
  m = /^([A-Za-z]+)_?(\\d+)$/.exec(nama);
  if (m) return `${m[1]}<tspan dy="8" font-size="18">${m[2]}</tspan>`;
  return nama;
}

function urutanBfs(data, pohon) {
  const adj = new Map();
  for (const e of pohon.s) {
    const [a, b] = data.sisi[e];
    if (!adj.has(a)) adj.set(a, []);
    if (!adj.has(b)) adj.set(b, []);
    adj.get(a).push([b, e]); adj.get(b).push([a, e]);
  }
  const lihat = new Set([0]), antre = [0], urut = [];
  while (antre.length) {
    const u = antre.shift();
    for (const [w, e] of adj.get(u) || []) if (!lihat.has(w)) { lihat.add(w); antre.push(w); urut.push(e); }
  }
  for (const e of pohon.s) if (!urut.includes(e)) urut.push(e);
  return urut;
}

function svgPohon(data, pohon, opsi) {
  const { tinggi } = data;
  const diPohon = new Set(pohon.s);
  let s = "";
  data.sisi.forEach(([a, b], i) => {
    if (diPohon.has(i)) return;
    const p = data.titik[a], q = data.titik[b];
    s += `<line class="s-buang" x1="${p.x}" y1="${p.y}" x2="${q.x}" y2="${q.y}"/>`;
  });
  const urut = opsi.animasi ? urutanBfs(data, pohon) : pohon.s;
  const jeda = opsi.animasi ? Math.min(120, 900 / Math.max(1, urut.length)) : 0;
  urut.forEach((i, k) => {
    const [a, b] = data.sisi[i];
    const p = data.titik[a], q = data.titik[b];
    if (opsi.animasi) {
      const L = Math.hypot(q.x - p.x, q.y - p.y).toFixed(1);
      s += `<line class="s-pohon tumbuh" style="--p:${L};animation-delay:${(k * jeda).toFixed(0)}ms" x1="${p.x}" y1="${p.y}" x2="${q.x}" y2="${q.y}"/>`;
    } else {
      s += `<line class="s-pohon" x1="${p.x}" y1="${p.y}" x2="${q.x}" y2="${q.y}"/>`;
    }
  });
  const r = opsi.animasi ? 13 : 16;
  data.titik.forEach((t) => {
    s += `<circle class="t${t.m ? " merah" : ""}" cx="${t.x}" cy="${t.y}" r="${r}"/>`;
    if (opsi.label) s += `<text class="lbl${t.m ? " merah" : ""}" x="${t.x + t.lx}" y="${t.y + t.ly}" text-anchor="middle" dominant-baseline="middle">${labelSvg(t.n)}</text>`;
  });
  return `<svg viewBox="0 0 ${data.lebar} ${tinggi}" role="img" aria-label="Spanning tree nomor ${pohon.no}">${s}</svg>`;
}

function lencana(data, w) {
  if (w === data.wmin) return `<span class="lencana min">${data.label_min || "minimum"}</span>`;
  if (w === data.wmaks) return '<span class="lencana maks">maksimum</span>';
  return "";
}

export default function (component) {
  const { data, parentElement } = component;
  if (!data) return;
  const isi = parentElement.querySelector(".isi");
  const saring = parentElement.querySelector(".saring");
  const info = parentElement.querySelector(".info");
  const tombolTab = parentElement.querySelectorAll(".tab button");

  let s = SIMPAN.get(parentElement);
  if (!s || s.id !== data.id) {
    if (s && s.timer) clearInterval(s.timer);
    s = { id: data.id, view: "grid", filter: "semua", page: 0, idx: 0, main: false, timer: null, laju: "sedang" };
    SIMPAN.set(parentElement, s);
    const opsi = [`<option value="semua">Semua W (${data.pohon.length} pohon)</option>`];
    const hitung = new Map();
    data.pohon.forEach((p) => hitung.set(p.w, (hitung.get(p.w) || 0) + 1));
    [...hitung.keys()].sort((a, b) => a - b).forEach((w) => {
      const tanda = w === data.wmin ? ` · ${data.label_min || "minimum"}` : w === data.wmaks ? " · maksimum" : "";
      opsi.push(`<option value="${w}">W = ${w} (${hitung.get(w)} pohon)${tanda}</option>`);
    });
    saring.innerHTML = opsi.join("");
  }

  const daftar = () => (s.filter === "semua" ? data.pohon : data.pohon.filter((p) => String(p.w) === s.filter));

  function berhenti() { if (s.timer) clearInterval(s.timer); s.timer = null; s.main = false; }

  function mulai() {
    berhenti();
    s.main = true;
    s.timer = setInterval(() => { s.idx = (s.idx + 1) % daftar().length; gambarAnim(); }, KECEPATAN[s.laju]);
  }

  function gambarGrid() {
    const d = daftar();
    const jumlahHal = Math.max(1, Math.ceil(d.length / PER_HALAMAN));
    s.page = Math.min(s.page, jumlahHal - 1);
    const awal = s.page * PER_HALAMAN;
    const potong = d.slice(awal, awal + PER_HALAMAN);
    let h = '<div class="kisi">';
    potong.forEach((p, k) => {
      h += `<div class="kartu" data-i="${awal + k}" style="animation-delay:${k * 18}ms" title="Klik untuk melihat animasi">` +
        svgPohon(data, p, { label: false }) +
        `${lencana(data, p.w)}<div class="cap"><span>No. ${p.no}</span><span>W = ${p.w}</span></div></div>`;
    });
    h += "</div>";
    if (jumlahHal > 1) {
      h += `<div class="halaman"><button type="button" class="sebelum" ${s.page === 0 ? "disabled" : ""}>‹ Sebelumnya</button>` +
        `<span>Halaman ${s.page + 1} dari ${jumlahHal}</span>` +
        `<button type="button" class="berikut" ${s.page >= jumlahHal - 1 ? "disabled" : ""}>Berikutnya ›</button></div>`;
    }
    isi.innerHTML = h;
    isi.querySelectorAll(".kartu").forEach((el) => {
      el.onclick = () => { s.idx = Number(el.dataset.i); s.view = "anim"; berhenti(); gambar(); };
    });
    const sb = isi.querySelector(".sebelum"), bk = isi.querySelector(".berikut");
    if (sb) sb.onclick = () => { s.page--; gambarGrid(); };
    if (bk) bk.onclick = () => { s.page++; gambarGrid(); };
    info.textContent = data.lengkap ? `τ = ${data.tau_teks}` : data.catatan;
  }

  function gambarAnim() {
    const d = daftar();
    if (!d.length) { isi.innerHTML = '<div class="kosong">Tidak ada pohon.</div>'; return; }
    s.idx = Math.min(s.idx, d.length - 1);
    const p = d[s.idx];
    const ada = isi.querySelector(".panggung");
    const panggung = `<div class="judul-anim"><span class="no">${p.judul || "Spanning tree No. " + p.no}</span>` +
      `<span class="w">W(T) = ${p.w}</span>${lencana(data, p.w)}<span style="opacity:.7">${s.idx + 1} / ${d.length}</span></div>` +
      svgPohon(data, p, { label: true, animasi: true });
    if (ada) {
      ada.innerHTML = panggung;
      const geser = isi.querySelector("input[type=range]");
      geser.max = d.length - 1; geser.value = s.idx;
      isi.querySelector(".main").textContent = s.main ? "⏸ Jeda" : "▶ Putar";
      return;
    }
    isi.innerHTML = `<div class="panggung">${panggung}</div>` +
      `<div class="kontrol">` +
      `<button type="button" class="awal" title="Pohon pertama">⏮</button>` +
      `<button type="button" class="mundur" title="Sebelumnya">◀</button>` +
      `<button type="button" class="main">${s.main ? "⏸ Jeda" : "▶ Putar"}</button>` +
      `<button type="button" class="maju" title="Berikutnya">▶</button>` +
      `<button type="button" class="akhir" title="Pohon terakhir">⏭</button>` +
      `<input type="range" min="0" max="${d.length - 1}" value="${s.idx}" aria-label="Pilih pohon"/>` +
      `<select class="laju" aria-label="Kecepatan"><option value="lambat">Lambat</option>` +
      `<option value="sedang">Sedang</option><option value="cepat">Cepat</option></select></div>`;
    const laju = isi.querySelector(".laju");
    laju.value = s.laju;
    laju.onchange = () => { s.laju = laju.value; if (s.main) mulai(); };
    isi.querySelector(".main").onclick = () => { if (s.main) berhenti(); else mulai(); gambarAnim(); };
    isi.querySelector(".maju").onclick = () => { berhenti(); s.idx = (s.idx + 1) % daftar().length; gambarAnim(); };
    isi.querySelector(".mundur").onclick = () => { berhenti(); s.idx = (s.idx - 1 + daftar().length) % daftar().length; gambarAnim(); };
    isi.querySelector(".awal").onclick = () => { berhenti(); s.idx = 0; gambarAnim(); };
    isi.querySelector(".akhir").onclick = () => { berhenti(); s.idx = daftar().length - 1; gambarAnim(); };
    isi.querySelector("input[type=range]").oninput = (e) => { berhenti(); s.idx = Number(e.target.value); gambarAnim(); };
    info.textContent = data.lengkap ? `τ = ${data.tau_teks}` : data.catatan;
  }

  function gambar() {
    tombolTab.forEach((b) => b.classList.toggle("aktif", b.dataset.v === s.view));
    if (s.view === "grid") { berhenti(); gambarGrid(); } else gambarAnim();
  }

  tombolTab.forEach((b) => { b.onclick = () => { s.view = b.dataset.v; s.idx = s.view === "anim" ? s.idx : 0; gambar(); }; });
  saring.value = s.filter;
  saring.onchange = () => { s.filter = saring.value; s.page = 0; s.idx = 0; gambar(); };
  gambar();
  return () => berhenti();
}
"""

_GALERI = st.components.v2.component("galeri_pohon_wiener", html=_HTML, css=_CSS, js=_JS)


def data_galeri(h: HasilGraf) -> dict | None:
    G, e = h.graf, h.enumerasi
    if not h.daftar:
        return None
    pos = posisi_graf(G)
    xs = [p[0] for p in pos.values()]
    ys = [p[1] for p in pos.values()]
    lebar_g, tinggi_g = max(xs) - min(xs), max(ys) - min(ys)
    skala = (LEBAR - 2 * TEPI) / max(lebar_g, tinggi_g * 1.25, 1e-9)
    tinggi = max(320, int(tinggi_g * skala + 2 * TEPI))
    cx = (max(xs) + min(xs)) / 2
    cy = (max(ys) + min(ys)) / 2
    koord = {t: (LEBAR / 2 + (pos[t][0] - cx) * skala, tinggi / 2 - (pos[t][1] - cy) * skala) for t in G.titik}
    rmaks = max(((x - LEBAR / 2) ** 2 + (y - tinggi / 2) ** 2) ** 0.5 for x, y in koord.values()) or 1
    titik = []
    for t in G.titik:
        x, y = koord[t]
        dx, dy = x - LEBAR / 2, y - tinggi / 2
        r = (dx * dx + dy * dy) ** 0.5
        if G.tata_letak == "tangga":
            lx, ly = 0.0, (-34.0 if t.startswith("x") else 34.0)
        elif r < 0.1 * rmaks:
            lx, ly = 26.0, -26.0
        else:
            arah = -1 if G.tata_letak == "lingkaran-ganda" and r < 0.8 * rmaks else 1   # lingkaran dalam: ke pusat
            lx, ly = arah * 36 * dx / r, arah * 36 * dy / r
        titik.append({"n": t, "x": round(x, 1), "y": round(y, 1), "m": t.startswith("x"),
                      "lx": round(lx, 1), "ly": round(ly, 1)})
    indeks = {e_: i for i, e_ in enumerate(G.sisi)}
    pohon = [{"no": p.nomor, "w": p.W, "s": [indeks[x] for x in p.sisi]} for p in h.daftar]
    catatan = "" if h.daftar_lengkap else (
        f"{len(h.daftar):,} W terkecil dari τ = {h.tau:,} pohon".replace(",", ".")
        + (" · mode cepat" if h.mode == "cepat" else ""))
    ident = re.sub(r"\W", "", f"{G.kode}{h.tau}{len(pohon)}{h.mode}{e.waktu if e else id(h)}")
    return {"id": ident, "lebar": LEBAR, "tinggi": tinggi, "titik": titik, "sisi": [list(x) for x in G.sisi],
            "pohon": pohon, "wmin": e.w_min if e else h.contoh_min.W, "wmaks": e.w_maks if e else None,
            "label_min": "minimum" if e else "terkecil",
            "lengkap": h.daftar_lengkap, "tau_teks": f"{h.tau:,}".replace(",", "."), "catatan": catatan}


def galeri_pohon(h: HasilGraf, key: str = "galeri_pohon") -> None:
    data = data_galeri(h)
    if data is not None:
        _GALERI(key=key, data=data)
