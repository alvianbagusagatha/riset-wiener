"""Pengujian keluarga graf dari gambar dan deteksi graf dari gambar unggahan."""

from __future__ import annotations

import io
import math
import random
import re

import networkx as nx
import numpy as np
import pytest

from wiener.graf import graf_keluarga
from wiener.jarak import distribusi_jarak
from wiener.matriks_pohon import banyak_spanning_tree
from wiener.pola import analisis_pola_fungsi
from wiener.pola_gambar import keluarga_dari_gambar


def T(nama, x, y):
    return {"nama": nama, "x": x, "y": y}


TANGGA = ([T("x1", 100, 100), T("y1", 100, 200), T("x2", 200, 100), T("y2", 200, 200)],
          [["x1", "y1"], ["x2", "y2"], ["x1", "x2"], ["y1", "y2"]])
RODA = ([T("c", 150, 50), T("v1", 100, 200), T("v2", 200, 200)], [["c", "v1"], ["c", "v2"], ["v1", "v2"]])


def sama(G, H) -> bool:
    a, b = nx.Graph(), nx.Graph()
    a.add_nodes_from(G.titik)
    a.add_edges_from((G.titik[i], G.titik[j]) for i, j in G.sisi)
    b.add_nodes_from(H.titik)
    b.add_edges_from((H.titik[i], H.titik[j]) for i, j in H.sisi)
    return set(a.nodes) == set(b.nodes) and {frozenset(e) for e in a.edges} == {frozenset(e) for e in b.edges}


# --------------------------------------------------------------------- keluarga dari gambar

@pytest.mark.parametrize("tertutup,kode", [(True, "CL"), (False, "L")])
def test_gambar_tangga_sama_dengan_keluarga_bawaan(tertutup, kode):
    kel = keluarga_dari_gambar(*TANGGA, tertutup=tertutup)
    for n in range(3, 9):
        assert sama(kel.buat(n), graf_keluarga(kode, n))


@pytest.mark.parametrize("tertutup,kode", [(True, "W"), (False, "F")])
def test_gambar_roda_dan_kipas(tertutup, kode):
    kel = keluarga_dari_gambar(*RODA, tertutup=tertutup)
    assert "titik pusat c" in kel.ringkasan()
    for n in range(3, 8):
        assert sama(kel.buat(n), graf_keluarga(kode, n))


def test_pola_dari_gambar_menemukan_rumus_CL():
    kel = keluarga_dari_gambar(*TANGGA, tertutup=True)
    hp = analisis_pola_fungsi("G", "uji", kel.tex, kel.buat, kel.n_min, 3, 10, progres=False)
    r = {x.kolom.kunci: x for x in hp.rumus}
    assert [p.teks for p in r["W"].potongan] == ["(n³ + 2n²)/2", "(n³ + 2n² − n)/2"]
    assert r["wmin"].potongan[0].teks == "(2n³ + 6n² − 5n)/3"
    assert r["wmaks"].potongan[0].teks == "(4n³ − n)/3"
    assert not r["tau"].ditemukan


def test_gambar_pola_salah():
    with pytest.raises(ValueError):
        keluarga_dari_gambar([], [], True)
    with pytest.raises(ValueError):          # indeks 3 tidak diizinkan
        keluarga_dari_gambar([T("x1", 0, 0), T("x3", 1, 1)], [["x1", "x3"]], True)
    with pytest.raises(ValueError):          # tidak ada titik berindeks
        keluarga_dari_gambar([T("a", 0, 0), T("b", 1, 1)], [["a", "b"]], True)


def test_pola_tidak_terhubung_tidak_error():
    kel = keluarga_dari_gambar([T("x1", 0, 0), T("x2", 100, 0)], [], tertutup=False)
    assert kel.peringatan
    hp = analisis_pola_fungsi("G", "uji", kel.tex, kel.buat, kel.n_min, 3, 5, progres=False)
    assert all(b["tau"] == 0 and b["wmin"] is None for b in hp.baris)


# --------------------------------------------------------------------- deteksi dari gambar

cv2 = pytest.importorskip("cv2")


def _deteksi_sama(data: bytes, G) -> bool:
    from wiener.deteksi_gambar import deteksi_graf

    h = deteksi_graf(data)
    A = nx.Graph()
    A.add_nodes_from(t["nama"] for t in h.titik)
    A.add_edges_from(h.sisi)
    B = nx.Graph()
    B.add_nodes_from(range(G.banyak_titik))
    B.add_edges_from(G.sisi)
    return nx.is_isomorphic(A, B)


@pytest.mark.parametrize("kode,n", [("CL", 4), ("CL", 7), ("L", 5), ("W", 6), ("K", 5), ("M", 5), ("F", 5)])
def test_deteksi_gambar_keluaran_program(tmp_path, kode, n):
    from wiener.gambar import gambar_graf

    G = graf_keluarga(kode, n)
    png = gambar_graf(G, tmp_path / "g")[0]
    assert _deteksi_sama(png.read_bytes(), G)


def _gambar_tangan(G, lingkaran_kosong: bool, seed: int) -> bytes:
    from PIL import Image, ImageDraw

    from wiener.gambar import posisi_graf

    rnd = random.Random(seed)
    pos = posisi_graf(G)
    xs = [p[0] for p in pos.values()]
    ys = [p[1] for p in pos.values()]
    W, H = 1200, 900
    s = min((W - 200) / (max(xs) - min(xs) or 1), (H - 200) / (max(ys) - min(ys) or 1))
    P = {t: (100 + (x - min(xs)) * s, H - 100 - (y - min(ys)) * s) for t, (x, y) in pos.items()}
    img = Image.new("L", (W, H), 235)
    d = ImageDraw.Draw(img)
    for a, b in G.sisi:
        (x1, y1), (x2, y2) = P[G.titik[a]], P[G.titik[b]]
        titik = []
        for i in range(31):
            t = i / 30
            titik.append((x1 + (x2 - x1) * t + rnd.uniform(-1, 1), y1 + (y2 - y1) * t + rnd.uniform(-1, 1)))
        d.line(titik, fill=40, width=4)
    for x, y in P.values():
        if lingkaran_kosong:
            d.ellipse([x - 16, y - 16, x + 16, y + 16], fill=235, outline=40, width=4)
        else:
            d.ellipse([x - 12, y - 12, x + 12, y + 12], fill=40)
    a = np.array(img, dtype=float) + np.random.default_rng(seed).normal(0, 6, (H, W))
    buf = io.BytesIO()
    Image.fromarray(np.clip(a, 0, 255).astype(np.uint8)).save(buf, "JPEG", quality=80)
    return buf.getvalue()


@pytest.mark.parametrize("kode,n", [("CL", 5), ("L", 4), ("W", 5), ("C", 6)])
@pytest.mark.parametrize("kosong", [False, True])
def test_deteksi_gambar_tangan(kode, n, kosong):
    G = graf_keluarga(kode, n)
    assert _deteksi_sama(_gambar_tangan(G, kosong, seed=n), G)


def test_deteksi_gambar_kosong_atau_rusak():
    from PIL import Image

    from wiener.deteksi_gambar import deteksi_graf

    buf = io.BytesIO()
    Image.new("L", (300, 200), 255).save(buf, "PNG")
    with pytest.raises(ValueError):
        deteksi_graf(buf.getvalue())
    with pytest.raises(ValueError):
        deteksi_graf(b"bukan gambar")


def test_hasil_deteksi_bisa_dihitung(tmp_path):
    """Gambar -> deteksi -> graf -> W dan τ sama dengan graf aslinya."""
    from wiener.deteksi_gambar import deteksi_graf
    from wiener.gambar import gambar_graf
    from wiener.graf import graf_dari_gambar

    G = graf_keluarga("CL", 6)
    h = deteksi_graf(gambar_graf(G, tmp_path / "g")[0].read_bytes())
    H = graf_dari_gambar("deteksi", h.titik, h.sisi)
    assert distribusi_jarak(H).W == distribusi_jarak(G).W
    assert banyak_spanning_tree(H) == banyak_spanning_tree(G)
    assert math.isclose(len(h.titik), G.banyak_titik)


# --------------------------------------------------------------------- semua graf: tebak pola & operasi

def _isi_dari(G):
    return ([{"nama": t, "x": G.posisi[t][0] * 100, "y": -G.posisi[t][1] * 100} for t in G.titik],
            [[G.titik[a], G.titik[b]] for a, b in G.sisi])


@pytest.mark.parametrize("kode,n0", [("CL", 5), ("CL", 3), ("L", 4), ("M", 5), ("M", 4), ("W", 6), ("F", 5),
                                     ("C", 6), ("P", 5), ("K1N", 4)])
def test_tebak_pola_dari_anggota_utuh(kode, n0):
    """Menggambar SATU anggota utuh sudah cukup untuk menebak seluruh keluarga (termasuk Möbius)."""
    from wiener.pola_gambar import keluarga_dari_indeks

    kel = keluarga_dari_indeks(*_isi_dari(graf_keluarga(kode, n0)))
    for n in range(max(kel.n_min, 3), 10):
        assert sama(kel.buat(n), graf_keluarga(kode, n)), (kode, n)


def test_tebak_pola_ular_segitiga():
    from wiener.pola_gambar import keluarga_dari_indeks

    t = [T(f"v{i}", i * 100, 200) for i in range(1, 5)] + [T(f"u{i}", i * 100 + 50, 100) for i in range(1, 4)]
    s = ([[f"v{i}", f"v{i + 1}"] for i in range(1, 4)] + [[f"v{i}", f"u{i}"] for i in range(1, 4)]
         + [[f"u{i}", f"v{i + 1}"] for i in range(1, 4)])
    G = keluarga_dari_indeks(t, s).buat(6)          # ular segitiga dengan 6 segitiga
    assert (G.banyak_titik, G.banyak_sisi) == (13, 18)
    assert banyak_spanning_tree(G) == 3 ** 6


def test_tebak_pola_tidak_beraturan():
    from wiener.pola_gambar import keluarga_dari_indeks

    with pytest.raises(ValueError, match="tidak memperlihatkan bagian yang berulang"):
        keluarga_dari_indeks([T(f"v{i}", i, 0) for i in range(1, 6)],
                             [["v1", "v2"], ["v2", "v3"], ["v3", "v4"], ["v4", "v5"], ["v1", "v3"]])


P2 = ([T("a", 0, 0), T("b", 0, 100)], [["a", "b"]])
C3 = ([T("a", 0, 0), T("b", 100, 0), T("c", 50, 80)], [["a", "b"], ["b", "c"], ["c", "a"]])
K1 = ([T("a", 0, 0)], [])


def _w_tau(G):
    return distribusi_jarak(G).W, banyak_spanning_tree(G)


@pytest.mark.parametrize("kode,keluarga", [("kali_c", "CL"), ("kali_p", "L")])
def test_operasi_hasil_kali(kode, keluarga):
    from wiener.pola_gambar import keluarga_operasi

    kel = keluarga_operasi(kode, *P2)
    for n in range(3, 9):
        assert _w_tau(kel.buat(n)) == _w_tau(graf_keluarga(keluarga, n))


def test_operasi_lain():
    from wiener.pola_gambar import keluarga_operasi

    persahabatan = keluarga_operasi("amalgamasi", *C3, s="a")
    assert [banyak_spanning_tree(persahabatan.buat(n)) for n in range(1, 6)] == [3 ** n for n in range(1, 6)]
    matahari = keluarga_operasi("korona_c", *K1)            # Cₙ ⊙ K₁: τ = n
    assert [banyak_spanning_tree(matahari.buat(n)) for n in range(3, 8)] == list(range(3, 8))
    bintang = keluarga_operasi("join", *K1)                  # K₁ + K̄ₙ = K₁,ₙ
    assert all(_w_tau(bintang.buat(n)) == _w_tau(graf_keluarga("K1N", n)) for n in range(1, 6))
    anting = keluarga_operasi("anting", *P2)
    assert [(g.banyak_titik, g.banyak_sisi) for g in map(anting.buat, (1, 2, 3))] == [(4, 3), (6, 5), (8, 7)]
    rantai = keluarga_operasi("rantai", *C3, a="c", b="a")
    assert [banyak_spanning_tree(rantai.buat(n)) for n in (1, 2, 3)] == [3, 9, 27]
    cincin = keluarga_operasi("cincin", *P2, a="a", b="a")  # cincin P₂: siklus Cₙ ber-anting
    assert banyak_spanning_tree(cincin.buat(5)) == 5
    with pytest.raises(ValueError):
        keluarga_operasi("amalgamasi", *C3, s="tidak_ada")


def test_pola_dari_operasi_menemukan_rumus():
    from wiener.pola_gambar import keluarga_operasi

    kel = keluarga_operasi("kali_c", *P2)
    hp = analisis_pola_fungsi("G", "uji", kel.tex, kel.buat, kel.n_min, 3, 10, progres=False)
    r = {x.kolom.kunci: x for x in hp.rumus}
    assert r["wmaks"].potongan[0].teks == "(4n³ − n)/3"


def test_pdf_semua_pohon(tmp_path):
    from wiener.analisis import analisis_graf
    from wiener.gambar import gambar_kisi_pdf

    h = analisis_graf(graf_keluarga("CL", 4), progres=False)
    pdf = gambar_kisi_pdf(h.graf, h.daftar, tmp_path / "semua.pdf", "uji")
    assert pdf.exists() and pdf.read_bytes()[:4] == b"%PDF"
    halaman = len(re.findall(rb"/Type\s*/Page\b", pdf.read_bytes()))
    assert halaman == 8          # 384 pohon / 48 per halaman


def test_tebak_pola_nomor_berurutan_per_blok():
    """v1..v9 bernomor per kolom (grid 3×3) dikenali sebagai blok 3 titik -> grid 3×n = P3 □ Pn."""
    from wiener.pola_gambar import keluarga_dari_indeks, keluarga_operasi

    t = [T(f"v{i}", 165 + 185 * ((i - 1) // 3), 125 + 110 * ((i - 1) % 3)) for i in range(1, 10)]
    s = [["v1", "v2"], ["v2", "v3"], ["v1", "v4"], ["v2", "v5"], ["v3", "v6"], ["v4", "v5"], ["v5", "v6"],
         ["v4", "v7"], ["v5", "v8"], ["v7", "v8"], ["v8", "v9"], ["v6", "v9"]]
    kel = keluarga_dari_indeks(t, s)
    assert "blok 3" in kel.label
    G4 = kel.buat(4)
    assert G4.titik == [f"v{i}" for i in range(1, 13)]
    grid = keluarga_operasi("kali_p", [T("a", 0, 0), T("b", 0, 1), T("c", 0, 2)], [["a", "b"], ["b", "c"]])
    for n in range(2, 8):
        assert _w_tau(kel.buat(n)) == _w_tau(grid.buat(n))
    assert banyak_spanning_tree(kel.buat(3)) == 192


def _grid(r):
    from wiener.pola_gambar import keluarga_operasi
    return keluarga_operasi("kali_p", [T(f"a{i}", 0, 100 * i) for i in range(r)],
                            [[f"a{i}", f"a{i + 1}"] for i in range(r - 1)])


def test_tebak_dari_letak_grid_campur_nomor():
    """Grid 4 baris x 3 kolom dengan penomoran campur (v1–v9 per kolom, v10–v12 per baris):
    dikenali dari letak titik, dengan DUA tafsiran: tambah kolom (grid 4×n) atau tambah baris (grid 3×n)."""
    from wiener.pola_gambar import tebak_semua

    x = {1: 230, 2: 390, 3: 550}
    y = {1: 50, 2: 130, 3: 210, 4: 290}
    letak = {"v1": (1, 1), "v2": (1, 2), "v3": (1, 3), "v4": (2, 1), "v5": (2, 2), "v6": (2, 3), "v7": (3, 1),
             "v8": (3, 2), "v9": (3, 3), "v10": (1, 4), "v11": (2, 4), "v12": (3, 4)}
    t = [T(v, x[k] + (8 if v in ("v8", "v12") else 0), y[b] + (12 if v in ("v2", "v11") else 0))
         for v, (k, b) in letak.items()]
    s = [["v1", "v4"], ["v4", "v7"], ["v1", "v2"], ["v2", "v5"], ["v4", "v5"], ["v5", "v8"], ["v7", "v8"],
         ["v2", "v3"], ["v5", "v6"], ["v8", "v9"], ["v3", "v6"], ["v6", "v9"], ["v3", "v10"], ["v6", "v11"],
         ["v9", "v12"], ["v10", "v11"], ["v11", "v12"]]
    semua = tebak_semua(t, s)
    label = [k.label for k in semua]
    assert any("kolom" in l for l in label) and any("baris" in l for l in label)
    kolom = next(k for k in semua if "kolom" in k.label)
    baris = next(k for k in semua if "baris" in k.label)
    for n in range(2, 7):
        assert _w_tau(kolom.buat(n)) == _w_tau(_grid(4).buat(n))
        assert _w_tau(baris.buat(n)) == _w_tau(_grid(3).buat(n))


@pytest.mark.parametrize("kode,n0", [("CL", 5), ("L", 4), ("W", 6), ("M", 5), ("C", 6), ("P", 5)])
def test_tebak_dari_letak_nama_acak(kode, n0):
    """Nama titik diacak (tanpa pola), keluarga tetap dikenali dari letak titik."""
    from wiener.pola_gambar import tebak_semua

    G = graf_keluarga(kode, n0)
    acak = list(range(1, G.banyak_titik + 1))
    random.Random(7).shuffle(acak)
    nm = {t: f"v{acak[i]}" for i, t in enumerate(G.titik)}
    t = [T(nm[v], 400 + 150 * G.posisi[v][0], 260 - 150 * G.posisi[v][1]) for v in G.titik]
    s = [[nm[G.titik[a]], nm[G.titik[b]]] for a, b in G.sisi]
    semua = tebak_semua(t, s)
    assert any(all(_w_tau(k.buat(n)) == _w_tau(graf_keluarga(kode, n)) for n in range(max(k.n_min, 3), 8))
               for k in semua)
