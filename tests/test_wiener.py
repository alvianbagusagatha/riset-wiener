"""Pengujian wajib. Jalankan:  python -m pytest -v"""

from __future__ import annotations

from fractions import Fraction
from functools import lru_cache
from math import comb

import networkx as nx
import numpy as np
import pytest

from wiener.analisis import analisis_graf
from wiener.enumerasi import enumerasi_spanning_tree
from wiener.graf import KELUARGA, baca_graf_kustom, graf_keluarga
from wiener.jarak import distribusi_jarak
from wiener.matriks_pohon import banyak_spanning_tree, determinan_bareiss
from wiener.pola import analisis_pola

TAU_CL = [75, 384, 1805, 8100, 35287, 150528, 632025, 2620860, 10759331, 43804800]
WMIN_CL = [29, 68, 125, 206, 315, 456, 633, 850, 1111, 1420]
WMAKS_CL = [35, 84, 165, 286, 455, 680, 969, 1330, 1771, 2300]


@lru_cache(maxsize=None)
def enumerasi_cl(n: int):
    G = graf_keluarga("CL", n)
    tau = banyak_spanning_tree(G)
    return tau, enumerasi_spanning_tree(G, tau=tau, progres=False)


@lru_cache(maxsize=None)
def pola_cl_3_12():
    return analisis_pola("CL", 3, 12, progres=False)


def ke_networkx(G):
    H = nx.Graph()
    H.add_nodes_from(range(G.banyak_titik))
    H.add_edges_from(G.sisi)
    return H


# --------------------------------------------------------------------- CL_3, CL_4, CL_7

def test_cl3():
    h = analisis_graf(graf_keluarga("CL", 3), progres=False)
    assert h.tau == 75
    assert h.distribusi.W == 21
    assert h.enumerasi.sebaran == {29: 3, 31: 18, 32: 24, 35: 30}
    assert h.enumerasi.w_min == 29 and h.enumerasi.w_maks == 35
    assert len(h.daftar) == 75
    assert [t.W for t in h.daftar] == sorted(t.W for t in h.daftar)


def test_cl4():
    h = analisis_graf(graf_keluarga("CL", 4), progres=False)
    assert h.tau == 384
    assert h.distribusi.W == 48
    assert h.enumerasi.sebaran == {68: 48, 70: 48, 72: 48, 74: 24, 76: 144, 84: 72}


def test_cl7():
    h = analisis_graf(graf_keluarga("CL", 7), progres=False)
    assert h.distribusi.W == 217
    assert [h.distribusi.N[t] for t in (1, 2, 3, 4)] == [21, 28, 28, 14]
    assert h.distribusi.diameter == 4
    assert h.tau == 35287
    e = h.enumerasi
    assert (e.w_min, e.banyak_min) == (315, 56)
    assert (e.w_maks, e.banyak_maks) == (455, 350)
    assert h.contoh_min.W == 315 and h.contoh_maks.W == 455
    # τ > 5000: galeri berisi sampel 5000 pohon berbeda, termasuk minimum & maksimum
    assert not h.daftar_lengkap and len(h.daftar) == 5000
    assert len({frozenset(t.sisi) for t in h.daftar}) == 5000
    assert h.daftar[0].W == 315 and h.daftar[-1].W == 455
    assert [t.nomor for t in h.daftar] == list(range(1, 5001))


def test_sampel_wilson_valid_dan_tetap():
    from wiener.enumerasi import pohon_acak_seragam
    from wiener.jarak import wiener_pohon_rumus_sisi
    G = graf_keluarga("CL", 9)
    a = pohon_acak_seragam(G, 300, seed=7)
    assert a == pohon_acak_seragam(G, 300, seed=7)              # sampel tetap
    assert len({frozenset(p) for p in a}) == 300
    sisi = set(G.sisi)
    for p in a:
        assert len(p) == G.banyak_titik - 1 and set(p) <= sisi
        assert distribusi_jarak(G.subgraf_sisi(p)).terhubung    # n-1 sisi + terhubung = pohon
        assert 0 < wiener_pohon_rumus_sisi(G.banyak_titik, p)


# --------------------------------------------------------------------- CL_n, n = 3..12

@pytest.mark.parametrize("n", range(3, 13))
def test_tau_matriks_pohon_cl(n):
    assert banyak_spanning_tree(graf_keluarga("CL", n)) == TAU_CL[n - 3]


@pytest.mark.parametrize("n", range(3, 13))
def test_enumerasi_cl(n):
    tau, e = enumerasi_cl(n)
    assert e.banyak == tau == TAU_CL[n - 3]          # τ Matriks-Pohon = banyak hasil enumerasi
    assert sum(e.sebaran.values()) == tau
    assert e.w_min == WMIN_CL[n - 3]
    assert e.w_maks == WMAKS_CL[n - 3]


@pytest.mark.parametrize("n", range(3, 13))
def test_contoh_pohon_konsisten(n):
    """Contoh pohon min/maks benar-benar spanning tree dengan W yang dilaporkan dan Σ N_t = C(|V|,2)."""
    G = graf_keluarga("CL", n)
    _, e = enumerasi_cl(n)
    for sisi, W in ((e.contoh_min, e.w_min), (e.contoh_maks, e.w_maks)):
        T = G.subgraf_sisi(sisi)
        assert len(sisi) == G.banyak_titik - 1 and set(sisi) <= set(G.sisi)
        d = distribusi_jarak(T)
        assert d.terhubung and d.W == W
        assert d.total_pasangan == comb(G.banyak_titik, 2)


# --------------------------------------------------------------------- pola dan rumus

def _rumus(hp, kunci):
    return next(r for r in hp.rumus if r.kolom.kunci == kunci)


def test_pola_W_graf():
    r = _rumus(pola_cl_3_12(), "W")
    assert r.ditemukan and r.modulus == 2
    genap, ganjil = r.potongan
    assert genap.koef == [0, 0, Fraction(1), Fraction(1, 2)]
    assert ganjil.koef == [0, Fraction(-1, 2), Fraction(1), Fraction(1, 2)]
    assert genap.teks == "(n³ + 2n²)/2"
    assert ganjil.teks == "(n³ + 2n² − n)/2"


def test_pola_W_minimum():
    r = _rumus(pola_cl_3_12(), "wmin")
    assert r.ditemukan and r.modulus == 1
    pt = r.potongan[0]
    assert pt.teks == "(2n³ + 6n² − 5n)/3"
    assert pt.n0 == 4 and pt.pengecualian == [3]


def test_pola_W_maksimum():
    r = _rumus(pola_cl_3_12(), "wmaks")
    assert r.ditemukan and r.modulus == 1
    pt = r.potongan[0]
    assert pt.teks == "(4n³ − n)/3"
    assert pt.teks_faktor == "n(4n² − 1)/3"
    assert pt.n0 == 3


def test_pola_tau_bukan_polinom():
    assert not _rumus(pola_cl_3_12(), "tau").ditemukan


def test_pola_V_E():
    hp = pola_cl_3_12()
    assert _rumus(hp, "V").potongan[0].teks == "2n"
    assert _rumus(hp, "E").potongan[0].teks == "3n"


# --------------------------------------------------------------------- semua keluarga & Σ N_t

KASUS = [(k, n) for k in KELUARGA for n in range(max(KELUARGA[k].n_min, 2), 8)]


@pytest.mark.parametrize("kode,n", KASUS)
def test_keluarga_uji_silang_networkx(kode, n):
    G = graf_keluarga(kode, n)
    H = ke_networkx(G)
    d = distribusi_jarak(G)
    assert d.total_pasangan == comb(G.banyak_titik, 2)
    assert d.W == int(nx.wiener_index(H))
    # τ pembanding: determinan floating point (numpy) dari Laplacian networkx
    A = nx.to_numpy_array(H, nodelist=range(G.banyak_titik))
    L = np.diag(A.sum(axis=1)) - A
    assert banyak_spanning_tree(G) == round(np.linalg.det(L[1:, 1:]))


@pytest.mark.parametrize("kode,n", [("CL", 3), ("L", 4), ("M", 4), ("W", 5), ("F", 5), ("K", 5), ("C", 6)])
def test_sebaran_uji_silang_networkx(kode, n):
    """Sebaran W dibandingkan dengan enumerasi pohon networkx (SpanningTreeIterator)."""
    G = graf_keluarga(kode, n)
    H = ke_networkx(G)
    harapan: dict[int, int] = {}
    for T in nx.SpanningTreeIterator(H):
        w = int(nx.wiener_index(T))
        harapan[w] = harapan.get(w, 0) + 1
    h = analisis_graf(G, progres=False)
    assert h.enumerasi.sebaran == dict(sorted(harapan.items()))
    for t in h.daftar:
        assert t.distribusi.total_pasangan == comb(G.banyak_titik, 2)


def test_jumlah_jarak_pohon_daftar():
    h = analisis_graf(graf_keluarga("L", 5), progres=False)
    assert len(h.daftar) == h.tau
    assert all(t.distribusi.total_pasangan == comb(10, 2) for t in h.daftar)


def test_ukuran_keluarga():
    for n in (3, 5, 8):
        assert (graf_keluarga("CL", n).banyak_titik, graf_keluarga("CL", n).banyak_sisi) == (2 * n, 3 * n)
        assert graf_keluarga("L", n).banyak_sisi == 3 * n - 2
        assert graf_keluarga("M", n).banyak_sisi == 3 * n


# --------------------------------------------------------------------- graf kustom & Bareiss

def test_kustom_dasar():
    G = baca_graf_kustom("x1-x2, x2-x3\nx3-x1, x1-y1")
    assert G.titik == ["x1", "x2", "x3", "y1"]
    assert G.banyak_sisi == 4
    assert banyak_spanning_tree(G) == 3


def test_kustom_ganda_dan_gelung():
    G = baca_graf_kustom("a-b, b-a, a-a, b-c")
    assert G.banyak_sisi == 2
    assert any("ganda" in p for p in G.peringatan)
    assert any("Gelung" in p for p in G.peringatan)


@pytest.mark.parametrize("teks", ["", "a-b-c", "ab", "a-", "a b-c?"])
def test_kustom_salah(teks):
    with pytest.raises(ValueError):
        baca_graf_kustom(teks)


def test_kustom_tidak_terhubung():
    h = analisis_graf(baca_graf_kustom("a-b, c-d"), progres=False)
    assert h.tau == 0 and h.enumerasi is None and h.distribusi.W is None


def test_bareiss():
    assert determinan_bareiss([[2, -1], [-1, 2]]) == 3
    assert determinan_bareiss([[0, 1], [1, 0]]) == -1
    assert determinan_bareiss([[1, 2], [2, 4]]) == 0
    # τ(K_n) = n^(n-2) (Cayley) — bilangan besar, tetap eksak
    assert banyak_spanning_tree(graf_keluarga("K", 30)) == 30 ** 28


# --------------------------------------------------------------------- editor gambar

def test_graf_dari_gambar():
    from wiener.graf import graf_dari_gambar
    titik = [{"nama": "v1", "x": 100, "y": 100}, {"nama": "v2", "x": 300, "y": 100},
             {"nama": "v3", "x": 200, "y": 250}, {"nama": "x1", "x": 400, "y": 100}]
    sisi = [["v1", "v2"], ["v2", "v3"], ["v3", "v1"], ["v2", "x1"], ["x1", "v2"]]
    G = graf_dari_gambar("segitiga plus", titik, sisi)
    assert G.banyak_titik == 4 and G.banyak_sisi == 4          # sisi ganda diabaikan
    assert G.kode == "segitiga_plus"
    assert G.posisi["v3"] == (2.0, -2.5)                       # sumbu y dibalik
    h = analisis_graf(G, progres=False)
    assert (h.distribusi.W, h.tau, h.enumerasi.w_min, h.enumerasi.w_maks) == (8, 3, 9, 10)


def test_graf_dari_gambar_salah():
    from wiener.graf import graf_dari_gambar
    with pytest.raises(ValueError):
        graf_dari_gambar("g", [], [])
    with pytest.raises(ValueError):
        graf_dari_gambar("g", [{"nama": "a", "x": 0, "y": 0}, {"nama": "a", "x": 1, "y": 1}], [])
