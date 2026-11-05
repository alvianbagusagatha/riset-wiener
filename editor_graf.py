"""Editor gambar graf untuk aplikasi Streamlit (komponen kustom CCv2).

Cara pakai di editor:
- Mode "Gambar": klik area kosong untuk menambah titik; klik dua titik untuk menambah
  (atau menghapus) sisi di antaranya; seret titik untuk memindahkannya.
- Mode "Hapus": klik titik atau sisi untuk menghapusnya.
- Mode "Nama": klik titik untuk mengganti namanya.
Koordinat gambar ikut dipakai pada gambar keluaran (PNG/PDF).
"""

from __future__ import annotations

import streamlit as st

from wiener.gambar import posisi_graf
from wiener.graf import Graf

LEBAR, TINGGI, TEPI = 800, 520, 60
KUNCI_SIMPAN = "_editor_graf"
GRAF_KOSONG = {"titik": [], "sisi": [], "tata_letak": "bebas"}

_HTML = """
<div class="editor">
  <div class="alat">
    <div class="grup" role="group" aria-label="Mode">
      <button type="button" data-mode="gambar" title="Tambah titik, sisi, dan geser titik">Gambar</button>
      <button type="button" data-mode="hapus" title="Klik titik atau sisi untuk menghapus">Hapus</button>
      <button type="button" data-mode="nama" title="Klik titik untuk mengganti nama">Nama</button>
    </div>
    <label>Awalan titik baru <input class="awalan" type="text" value="v" maxlength="8" /></label>
    <label><input class="kisi" type="checkbox" checked /> Rapikan ke kisi</label>
    <span class="pemisah"></span>
    <button type="button" class="urung" title="Batalkan langkah terakhir">Urungkan</button>
    <button type="button" class="kosong" title="Hapus semua titik dan sisi">Kosongkan</button>
  </div>
  <svg class="kanvas" viewBox="0 0 800 520" role="img" aria-label="Kanvas gambar graf"></svg>
  <div class="info"></div>
</div>
"""

_CSS = """
.editor { font-family: var(--st-font); color: var(--st-text-color); font-size: 0.9rem; }
.alat { display: flex; flex-wrap: wrap; gap: 8px 14px; align-items: center; margin-bottom: 8px; }
.grup { display: inline-flex; }
.grup button { border-radius: 0; margin-left: -1px; }
.grup button:first-child { border-radius: var(--st-button-radius) 0 0 var(--st-button-radius); }
.grup button:last-child { border-radius: 0 var(--st-button-radius) var(--st-button-radius) 0; }
button {
  font: inherit; padding: 4px 12px; cursor: pointer;
  border: 1px solid var(--st-border-color); border-radius: var(--st-button-radius);
  background: var(--st-secondary-background-color); color: var(--st-text-color);
}
button:hover { border-color: var(--st-primary-color); }
button.aktif { background: var(--st-primary-color); border-color: var(--st-primary-color); color: #fff; }
label { display: inline-flex; align-items: center; gap: 6px; }
input.awalan {
  width: 4.5em; font: inherit; padding: 3px 6px; color: var(--st-text-color);
  background: var(--st-background-color); border: 1px solid var(--st-border-color);
  border-radius: var(--st-base-radius);
}
.pemisah { flex: 1; }
.kanvas {
  display: block; width: 100%; height: auto; touch-action: none; user-select: none;
  background-color: var(--st-background-color);
  border: 1px solid var(--st-border-color); border-radius: var(--st-base-radius);
}
.kanvas.berkisi {
  background-image: radial-gradient(circle, var(--st-border-color) 1.2px, transparent 1.6px);
  background-size: 2.5% 3.84615%;
}
.kanvas[data-mode="gambar"] { cursor: crosshair; }
.kanvas[data-mode="hapus"], .kanvas[data-mode="nama"] { cursor: pointer; }
.sisi .garis { stroke: var(--st-text-color); stroke-width: 2.5; stroke-linecap: round; }
.sisi .kena { stroke: transparent; stroke-width: 16; }
.kanvas[data-mode="hapus"] .sisi:hover .garis { stroke: var(--st-red-color); stroke-width: 4; }
.titik circle { fill: var(--st-text-color); stroke: var(--st-background-color); stroke-width: 2; cursor: grab; }
.titik.merah circle { fill: #d62728; }
.titik:hover circle { stroke: var(--st-blue-color); stroke-width: 3; }
.titik.dipilih circle { stroke: var(--st-blue-color); stroke-width: 5; }
.kanvas[data-mode="hapus"] .titik:hover circle { fill: var(--st-red-color); }
.label { fill: var(--st-text-color); font-size: 17px; font-style: italic; pointer-events: none; }
.label.merah { fill: #d62728; }
.info { margin-top: 6px; opacity: 0.8; }
"""

_JS = """
const SIMPAN = new WeakMap();
const W = 800, H = 520, R = 11, KISI = 20;
const NAMA_SAH = /^[A-Za-z0-9_]+$/;

function salin(g) { return JSON.parse(JSON.stringify(g)); }

function labelSvg(nama) {
  const m = /^([A-Za-z]+)_?(\\d+)$/.exec(nama);
  if (m) return `${m[1]}<tspan dy="5" font-size="12">${m[2]}</tspan>`;
  return nama;
}

export default function (component) {
  const { data, parentElement, setStateValue } = component;
  const svg = parentElement.querySelector("svg.kanvas");
  const info = parentElement.querySelector(".info");
  const tombolMode = parentElement.querySelectorAll("[data-mode]");
  const inAwalan = parentElement.querySelector("input.awalan");
  const inKisi = parentElement.querySelector("input.kisi");
  if (!svg) return;

  let s = SIMPAN.get(parentElement);
  if (!s) {
    s = { versi: undefined, graf: null, riwayat: [], pilih: null, mode: "gambar", seret: null };
    SIMPAN.set(parentElement, s);
  }
  if (data && data.versi !== s.versi) {
    s.versi = data.versi;
    s.graf = salin(data.graf || { titik: [], sisi: [], tata_letak: "bebas" });
    s.riwayat = [];
    s.pilih = null;
  }

  const kirim = () => setStateValue("graf", { ...s.graf, versi: s.versi });
  const catat = () => { s.riwayat.push(salin(s.graf)); if (s.riwayat.length > 200) s.riwayat.shift(); };
  const cari = (nama) => s.graf.titik.find((t) => t.nama === nama);
  // titik kisi berada di tengah sel 20×20 (koordinat 10, 30, 50, ...)
  const rapikan = (v) => (inKisi.checked ? Math.round((v - KISI / 2) / KISI) * KISI + KISI / 2 : Math.round(v));
  const batas = (v, maks) => Math.min(maks - R - 2, Math.max(R + 2, v));

  function koordinat(e) {
    const pt = svg.createSVGPoint();
    pt.x = e.clientX; pt.y = e.clientY;
    const p = pt.matrixTransform(svg.getScreenCTM().inverse());
    return { x: p.x, y: p.y };
  }
  const titikDi = (e) => { const el = e.target.closest && e.target.closest("[data-titik]"); return el ? el.getAttribute("data-titik") : null; };
  const sisiDi = (e) => { const el = e.target.closest && e.target.closest("[data-sisi]"); return el ? Number(el.getAttribute("data-sisi")) : null; };

  function namaBaru() {
    let awal = (inAwalan.value || "").trim();
    if (!/^[A-Za-z_][A-Za-z0-9_]*$/.test(awal)) awal = "v";
    let k = 1;
    while (cari(awal + k)) k++;
    return awal + k;
  }

  function aturSisi(a, b) {
    const i = s.graf.sisi.findIndex(([p, q]) => (p === a && q === b) || (p === b && q === a));
    if (i >= 0) s.graf.sisi.splice(i, 1); else s.graf.sisi.push([a, b]);
  }

  function render() {
    const g = s.graf;
    const pos = new Map(g.titik.map((t) => [t.nama, t]));
    let isi = "";
    g.sisi.forEach(([a, b], i) => {
      const p = pos.get(a), q = pos.get(b);
      if (!p || !q) return;
      isi += `<g class="sisi" data-sisi="${i}">` +
        `<line class="kena" x1="${p.x}" y1="${p.y}" x2="${q.x}" y2="${q.y}"/>` +
        `<line class="garis" x1="${p.x}" y1="${p.y}" x2="${q.x}" y2="${q.y}"/></g>`;
    });
    let label = "";
    g.titik.forEach((t) => {
      const merah = t.nama.startsWith("x") ? " merah" : "";
      const dipilih = s.pilih === t.nama ? " dipilih" : "";
      isi += `<g class="titik${merah}${dipilih}" data-titik="${t.nama}"><circle cx="${t.x}" cy="${t.y}" r="${R}"/></g>`;
      label += `<text class="label${merah}" x="${t.x + 13}" y="${t.y - 13}">${labelSvg(t.nama)}</text>`;
    });
    svg.innerHTML = isi + label;
    svg.dataset.mode = s.mode;
    svg.classList.toggle("berkisi", inKisi.checked);
    tombolMode.forEach((b) => {
      const aktif = b.dataset.mode === s.mode;
      b.classList.toggle("aktif", aktif);
      b.setAttribute("aria-pressed", aktif ? "true" : "false");
    });
    const petunjuk = {
      gambar: s.pilih
        ? `Titik ${s.pilih} dipilih: klik titik lain untuk menambah/menghapus sisi, atau klik ${s.pilih} lagi untuk batal.`
        : "Klik area kosong untuk menambah titik, klik dua titik untuk menambah sisi, seret titik untuk memindahkan.",
      hapus: "Klik titik atau sisi untuk menghapusnya.",
      nama: "Klik titik untuk mengganti namanya.",
    }[s.mode];
    info.textContent = `|V| = ${g.titik.length}, |E| = ${g.sisi.length}  ·  ${petunjuk}`;
  }

  tombolMode.forEach((b) => { b.onclick = () => { s.mode = b.dataset.mode; s.pilih = null; render(); }; });
  inKisi.onchange = () => render();
  parentElement.querySelector("button.urung").onclick = () => {
    if (!s.riwayat.length) return;
    s.graf = s.riwayat.pop(); s.pilih = null; kirim(); render();
  };
  parentElement.querySelector("button.kosong").onclick = () => {
    if (!s.graf.titik.length) return;
    catat(); s.graf = { titik: [], sisi: [], tata_letak: "bebas" }; s.pilih = null; kirim(); render();
  };

  svg.onpointerdown = (e) => {
    if (e.button !== 0) return;
    const p = koordinat(e);
    const t = titikDi(e);
    if (s.mode === "hapus") {
      if (t !== null) {
        catat();
        s.graf.titik = s.graf.titik.filter((v) => v.nama !== t);
        s.graf.sisi = s.graf.sisi.filter(([a, b]) => a !== t && b !== t);
        kirim(); render();
      } else {
        const k = sisiDi(e);
        if (k !== null) { catat(); s.graf.sisi.splice(k, 1); kirim(); render(); }
      }
      return;
    }
    if (s.mode === "nama") {
      if (t === null) return;
      const baru = (window.prompt(`Nama baru untuk titik ${t} (huruf, angka, atau _):`, t) || "").trim();
      if (!baru || baru === t) return;
      if (!NAMA_SAH.test(baru)) { window.alert("Nama hanya boleh berisi huruf, angka, atau _."); return; }
      if (cari(baru)) { window.alert(`Nama ${baru} sudah dipakai.`); return; }
      catat();
      cari(t).nama = baru;
      s.graf.sisi = s.graf.sisi.map(([a, b]) => [a === t ? baru : a, b === t ? baru : b]);
      kirim(); render();
      return;
    }
    if (t !== null) {
      s.seret = { nama: t, x0: p.x, y0: p.y, bergerak: false, cadangan: salin(s.graf) };
      svg.setPointerCapture(e.pointerId);
    } else if (sisiDi(e) === null) {
      catat();
      s.graf.titik.push({ nama: namaBaru(), x: batas(rapikan(p.x), W), y: batas(rapikan(p.y), H) });
      s.pilih = null;
      kirim(); render();
    }
  };

  svg.onpointermove = (e) => {
    const sr = s.seret;
    if (!sr) return;
    const p = koordinat(e);
    if (!sr.bergerak && Math.hypot(p.x - sr.x0, p.y - sr.y0) < 5) return;
    sr.bergerak = true;
    const v = cari(sr.nama);
    v.x = batas(rapikan(p.x), W);
    v.y = batas(rapikan(p.y), H);
    render();
  };

  svg.onpointerup = () => {
    const sr = s.seret;
    s.seret = null;
    if (!sr) return;
    if (sr.bergerak) { s.riwayat.push(sr.cadangan); kirim(); return; }
    if (s.pilih === null) s.pilih = sr.nama;
    else if (s.pilih === sr.nama) s.pilih = null;
    else { catat(); aturSisi(s.pilih, sr.nama); s.pilih = sr.nama; kirim(); }
    render();
  };
  svg.onpointercancel = () => { s.seret = null; };

  render();
}
"""

_EDITOR = st.components.v2.component("editor_graf_wiener", html=_HTML, css=_CSS, js=_JS)


def graf_ke_gambar(G: Graf) -> dict:
    """Ubah Graf (mis. dari keluarga) menjadi isi editor, diskalakan ke kanvas."""
    pos = posisi_graf(G)
    xs = [p[0] for p in pos.values()]
    ys = [p[1] for p in pos.values()]
    lebar, tinggi = max(xs) - min(xs), max(ys) - min(ys)
    pilihan = []
    if lebar > 1e-9:
        pilihan.append((LEBAR - 2 * TEPI) / lebar)
    if tinggi > 1e-9:
        pilihan.append((TINGGI - 2 * TEPI) / tinggi)
    skala = min(pilihan) if pilihan else 1.0
    mx, my = (max(xs) + min(xs)) / 2, (max(ys) + min(ys)) / 2
    titik = [{"nama": t, "x": round(LEBAR / 2 + (pos[t][0] - mx) * skala, 1),
              "y": round(TINGGI / 2 - (pos[t][1] - my) * skala, 1)} for t in G.titik]
    sisi = [[G.titik[a], G.titik[b]] for a, b in G.sisi]
    return {"titik": titik, "sisi": sisi, "tata_letak": G.tata_letak}


def _kunci_simpan(key: str) -> str:
    return f"{KUNCI_SIMPAN}_{key}"


def muat_ke_editor(isi: dict, key: str = "editor_graf") -> None:
    """Ganti isi editor. Panggil SEBELUM editor dipasang (mis. dari on_click tombol)."""
    lama = st.session_state.get(_kunci_simpan(key), {"versi": 0})
    st.session_state[_kunci_simpan(key)] = {"versi": lama["versi"] + 1, "graf": isi}


def isi_editor(key: str = "editor_graf") -> dict:
    """Isi editor terakhir tanpa memasang editor."""
    return st.session_state.get(_kunci_simpan(key), {"graf": dict(GRAF_KOSONG)})["graf"]


def editor_graf(key: str = "editor_graf") -> dict:
    """Pasang editor dan kembalikan gambar terkini: {"titik", "sisi", "tata_letak"}."""
    simpan = st.session_state.setdefault(_kunci_simpan(key), {"versi": 0, "graf": dict(GRAF_KOSONG)})
    keadaan = st.session_state.get(key)
    terbaru = keadaan.get("graf") if keadaan is not None else None
    if terbaru and terbaru.get("versi") == simpan["versi"]:
        simpan["graf"] = {k: terbaru[k] for k in ("titik", "sisi", "tata_letak") if k in terbaru}
    _EDITOR(key=key, data={"graf": simpan["graf"], "versi": simpan["versi"]},
            on_graf_change=lambda: None)
    return simpan["graf"]


def teks_sisi(isi: dict) -> str:
    """Daftar sisi gambar dalam format teks (bisa disimpan sebagai .txt)."""
    return ", ".join(f"{a}-{b}" for a, b in isi.get("sisi", []))


# Contoh untuk tab pola: isi kanvas + cara membentuk G_n
def _t(nama, x, y):
    return {"nama": nama, "x": x, "y": y}


def _isi(titik, sisi):
    return {"titik": titik, "sisi": sisi, "tata_letak": "bebas"}


_P2 = _isi([_t("a", 400, 170), _t("b", 400, 350)], [["a", "b"]])
_C3 = _isi([_t("a", 400, 330), _t("b", 300, 160), _t("c", 500, 160)], [["a", "b"], ["b", "c"], ["c", "a"]])
_TANGGA2 = _isi([_t("x1", 330, 330), _t("y1", 330, 170), _t("x2", 470, 330), _t("y2", 470, 170)],
                [["x1", "y1"], ["x2", "y2"], ["x1", "x2"], ["y1", "y2"]])
_K2 = _isi([_t("a", 340, 260), _t("b", 460, 260)], [["a", "b"]])
# grid 4 baris x 3 kolom bernomor v1..v12 (nomor tidak berpola): ditebak dari letak titik
_NOMOR_GRID = [["v1", "v4", "v7"], ["v2", "v5", "v8"], ["v3", "v6", "v9"], ["v10", "v11", "v12"]]
_GRID43 = _isi([_t(v, 260 + 140 * k, 70 + 120 * b) for b, baris in enumerate(_NOMOR_GRID) for k, v in enumerate(baris)],
               [[baris[k], baris[k + 1]] for baris in _NOMOR_GRID for k in range(2)]
               + [[_NOMOR_GRID[b][k], _NOMOR_GRID[b + 1][k]] for b in range(3) for k in range(3)])

CONTOH_POLA = {
    "CLₙ dari dua salinan (x1, y1, x2, y2)": {"isi": _TANGGA2, "cara": "indeks", "ujung": "Tertutup"},
    "Lₙ dari dua salinan (x1, y1, x2, y2)": {"isi": _TANGGA2, "cara": "indeks", "ujung": "Terbuka"},
    "Tangga Möbius M₅ utuh (pola ditebak)": {"keluarga": ("M", 5), "cara": "indeks", "ujung": "Otomatis"},
    "Roda W₆ utuh (pola ditebak)": {"keluarga": ("W", 6), "cara": "indeks", "ujung": "Otomatis"},
    "P₂ □ Cₙ  (= CLₙ)": {"isi": _P2, "cara": "kali_c"},
    "Graf persahabatan: amalgamasi C₃": {"isi": _C3, "cara": "amalgamasi", "s": "a"},
    "Korona Cₙ ⊙ K₂": {"isi": _K2, "cara": "korona_c"},
    "Grid 4×3 bernomor v1..v12 (dua tafsiran)": {"isi": _GRID43, "cara": "indeks", "ujung": "Otomatis"},
}
