"""Pencarian cepat spanning tree dengan indeks Wiener terkecil, tanpa enumerasi semua pohon.

Untuk graf dengan τ sangat besar (miliaran pohon atau lebih) enumerasi lengkap butuh berhari-hari.
Modul ini mencari `banyak` pohon dengan W(T) terkecil secara heuristik:

1. Benih: pohon BFS (pohon jarak terpendek) dari setiap titik, dengan dua urutan tetangga.
   Pohon ber-W kecil cenderung mirip pohon jarak terpendek dari titik pusat.
2. Pencarian terbaik-dahulu pada graf "tukar sisi": tetangga sebuah pohon T adalah T − e + f
   (f sisi di luar pohon, e sisi pada siklus yang dibentuk f). Pohon dengan W terkecil yang belum
   diperluas selalu diperluas lebih dulu.
3. Berhenti bila setiap pohon di antara `banyak` terkecil yang ditemukan sudah diperluas (tidak ada
   tukar satu sisi yang menghasilkan pohon baru yang lebih kecil), atau batas waktu tercapai.

Mencari W(T) minimum adalah masalah NP-hard, jadi hasilnya TIDAK dijamin minimum mutlak; dalam
uji terhadap enumerasi lengkap hasilnya sama atau sangat dekat (lihat tests/test_wiener.py).
"""

from __future__ import annotations

import heapq
import time
from dataclasses import dataclass

import numpy as np

from .enumerasi import _wiener_pohon, njit
from .graf import Graf


@njit(cache=True)
def _tetangga_tukar(pohon, eu, ev, nv, m, out_e, out_f, out_w):
    """Semua pohon T − e + f beserta W-nya. Mengisi out_*; mengembalikan banyaknya."""
    perlu = nv - 1
    di_pohon = np.zeros(m, np.bool_)
    letak = np.full(m, -1, np.int64)
    for t in range(perlu):
        di_pohon[pohon[t]] = True
        letak[pohon[t]] = t
    kepala = np.full(nv, -1, np.int64)
    berikut = np.empty(2 * perlu, np.int64)
    tujuan = np.empty(2 * perlu, np.int64)
    sisi_ke = np.empty(2 * perlu, np.int64)
    for t in range(perlu):
        e = pohon[t]
        a = eu[e]
        b = ev[e]
        tujuan[2 * t] = b
        sisi_ke[2 * t] = e
        berikut[2 * t] = kepala[a]
        kepala[a] = 2 * t
        tujuan[2 * t + 1] = a
        sisi_ke[2 * t + 1] = e
        berikut[2 * t + 1] = kepala[b]
        kepala[b] = 2 * t + 1
    induk = np.full(nv, -1, np.int64)
    induk_sisi = np.full(nv, -1, np.int64)
    dalam = np.zeros(nv, np.int64)
    antre = np.empty(nv, np.int64)
    antre[0] = 0
    induk[0] = 0
    ekor = 1
    p = 0
    while p < ekor:
        u = antre[p]
        p += 1
        s = kepala[u]
        while s >= 0:
            w = tujuan[s]
            if induk[w] < 0:
                induk[w] = u
                induk_sisi[w] = sisi_ke[s]
                dalam[w] = dalam[u] + 1
                antre[ekor] = w
                ekor += 1
            s = berikut[s]
    k_kepala = np.empty(nv, np.int64)
    k_berikut = np.empty(2 * nv, np.int64)
    k_tujuan = np.empty(2 * nv, np.int64)
    k_urutan = np.empty(nv, np.int64)
    k_induk = np.empty(nv, np.int64)
    k_ukuran = np.empty(nv, np.int64)
    baru = pohon.copy()
    k = 0
    for f in range(m):
        if di_pohon[f]:
            continue
        a = eu[f]
        b = ev[f]
        while a != b:                       # sisi pada lintasan a–b di pohon = siklus f
            if dalam[a] >= dalam[b]:
                e = induk_sisi[a]
                a = induk[a]
            else:
                e = induk_sisi[b]
                b = induk[b]
            t = letak[e]
            baru[t] = f
            out_w[k] = _wiener_pohon(baru, eu, ev, nv, k_kepala, k_berikut, k_tujuan,
                                     k_urutan, k_induk, k_ukuran)
            baru[t] = e
            out_e[k] = e
            out_f[k] = f
            k += 1
    return k


@njit(cache=True)
def _w_pohon(pohon, eu, ev, nv):
    return _wiener_pohon(pohon, eu, ev, nv, np.empty(nv, np.int64), np.empty(2 * nv, np.int64),
                         np.empty(2 * nv, np.int64), np.empty(nv, np.int64), np.empty(nv, np.int64),
                         np.empty(nv, np.int64))


@dataclass
class HasilPencarian:
    pohon: list[list[tuple[int, int]]]     # urut menurut W (sisi dalam indeks titik)
    w: list[int]
    diperluas: int                          # banyak pohon yang tetangganya diperiksa
    diperiksa: int                          # banyak pohon yang W-nya dihitung
    tuntas: bool                            # True: berhenti karena kriteria, bukan batas waktu
    waktu: float


def _benih(G: Graf) -> list[list[int]]:
    """Pohon BFS dari setiap titik (dua urutan tetangga), sebagai daftar indeks sisi."""
    indeks = {}
    for i, (a, b) in enumerate(G.sisi):
        indeks[(a, b)] = indeks[(b, a)] = i
    adj = G.tetangga()
    hasil = []
    for akar in range(G.banyak_titik):
        for balik in (False, True):
            lihat = {akar}
            antre = [akar]
            sisi = []
            for u in antre:
                for w in sorted(adj[u], reverse=balik):
                    if w not in lihat:
                        lihat.add(w)
                        antre.append(w)
                        sisi.append(indeks[(u, w)])
            hasil.append(sisi)
    return hasil


def cari_pohon_terkecil(G: Graf, banyak: int = 5000, batas_waktu: float = 25.0,
                        callback=None) -> HasilPencarian:
    """Cari `banyak` spanning tree berbeda dengan W(T) terkecil (heuristik, lihat docstring modul).

    callback(diperluas, banyak) opsional untuk progres.
    """
    mulai = time.perf_counter()
    nv, m = G.banyak_titik, G.banyak_sisi
    if nv <= 1:
        return HasilPencarian([[]], [0], 0, 1, True, 0.0)
    eu = np.array([a for a, _ in G.sisi], dtype=np.int64)
    ev = np.array([b for _, b in G.sisi], dtype=np.int64)
    bit = [1 << i for i in range(m)]
    kapasitas = max(1, (m - nv + 1) * (nv - 1))
    out_e = np.empty(kapasitas, np.int64)
    out_f = np.empty(kapasitas, np.int64)
    out_w = np.empty(kapasitas, np.int64)

    def urai(kunci: int) -> list[int]:
        sisi = []
        while kunci:
            rendah = kunci & -kunci
            sisi.append(rendah.bit_length() - 1)
            kunci ^= rendah
        return sisi

    ditemukan: dict[int, int] = {}          # kunci (bitmask sisi) -> W
    calon: list[tuple[int, int]] = []       # heap (W, kunci) yang belum diperluas
    teratas: list[int] = []                 # max-heap (-W) berisi `banyak` W terkecil

    def batas() -> float:
        return -teratas[0] if len(teratas) >= banyak else float("inf")

    def catat(kunci: int, w: int) -> None:
        ditemukan[kunci] = w
        heapq.heappush(calon, (w, kunci))
        if len(teratas) < banyak:
            heapq.heappush(teratas, -w)
        elif w < -teratas[0]:
            heapq.heapreplace(teratas, -w)

    for sisi in _benih(G):
        kunci = sum(bit[i] for i in sisi)
        if kunci not in ditemukan:
            catat(kunci, int(_w_pohon(np.array(sisi, dtype=np.int64), eu, ev, nv)))

    diperluas = 0
    diperiksa = len(ditemukan)
    tuntas = True
    while calon:
        w, kunci = heapq.heappop(calon)
        if w > batas():
            break                            # semua pohon di `banyak` terkecil sudah diperluas
        k = _tetangga_tukar(np.array(urai(kunci), dtype=np.int64), eu, ev, nv, m, out_e, out_f, out_w)
        diperiksa += k
        for i in range(k):
            w2 = int(out_w[i])
            if w2 >= batas() and len(teratas) >= banyak:
                continue                     # tidak mungkin masuk `banyak` terkecil
            kunci2 = kunci ^ bit[out_e[i]] ^ bit[out_f[i]]
            if kunci2 not in ditemukan:
                catat(kunci2, w2)
        diperluas += 1
        if diperluas % 200 == 0:
            if callback is not None:
                callback(min(diperluas, banyak), banyak)
            if time.perf_counter() - mulai > batas_waktu:
                tuntas = False
                break

    terpilih = sorted(ditemukan.items(), key=lambda kv: (kv[1], kv[0]))[:banyak]
    pohon = [[(int(eu[i]), int(ev[i])) for i in urai(kunci)] for kunci, _ in terpilih]
    if callback is not None:
        callback(banyak, banyak)
    return HasilPencarian(pohon=pohon, w=[w for _, w in terpilih], diperluas=diperluas,
                          diperiksa=diperiksa, tuntas=tuntas, waktu=time.perf_counter() - mulai)
