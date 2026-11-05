"""Enumerasi SEMUA spanning tree dan indeks Wiener tiap pohon.

Algoritma: backtracking per sisi (sertakan / abaikan) dengan union-find tanpa path
compression tetapi dengan rollback (union by size). Banyak sisi yang boleh diabaikan
dibatasi |E| − (|V| − 1), sehingga cabang yang sisa sisinya tidak cukup langsung
dipangkas. Setiap pohon yang lengkap langsung dihitung W(T) dengan rumus sisi
W(T) = Σ n1(e)·n2(e) (ukuran subpohon, O(|V|)), lalu dicatat ke histogram — pohon
tidak disimpan, kecuali bila diminta daftar lengkap (τ kecil).

Agar progres bisa ditampilkan dan semua inti CPU terpakai, keputusan untuk K sisi
pertama dijadikan "awalan" (prefiks). Setiap awalan adalah sub-masalah terpisah yang
dikerjakan paralel oleh Numba (prange). Karena τ sudah diketahui dari Teorema
Matriks-Pohon, progres = pohon ditemukan / τ.
"""

from __future__ import annotations

import os
import time
import warnings
from dataclasses import dataclass

import numpy as np

try:
    from numba import njit, prange
    import numba
    ADA_NUMBA = True
except ImportError:  # pragma: no cover - diuji manual tanpa numba
    ADA_NUMBA = False

    def njit(*args, **kwargs):
        if len(args) == 1 and callable(args[0]):
            return args[0]
        return lambda f: f

    prange = range

from .graf import Graf

_PERINGATAN_TANPA_NUMBA = (
    "Numba tidak terpasang: enumerasi memakai Python murni dan akan JAUH lebih lambat "
    "(puluhan hingga ratusan kali). Pasang dengan: pip install numba"
)


# ---------------------------------------------------------------------------
# Inti (kompatibel Numba dan Python murni)
# ---------------------------------------------------------------------------

@njit(cache=True)
def _akar(induk, x):
    while induk[x] != x:
        x = induk[x]
    return x


@njit(cache=True)
def _wiener_pohon(pohon, eu, ev, nv, kepala, berikut, tujuan, urutan, induk_t, ukuran):
    """W(T) dengan rumus sisi; semua larik kerja sudah dialokasikan pemanggil."""
    for i in range(nv):
        kepala[i] = -1
        induk_t[i] = -1
        ukuran[i] = 1
    for idx in range(nv - 1):
        e = pohon[idx]
        a = eu[e]
        b = ev[e]
        tujuan[2 * idx] = b
        berikut[2 * idx] = kepala[a]
        kepala[a] = 2 * idx
        tujuan[2 * idx + 1] = a
        berikut[2 * idx + 1] = kepala[b]
        kepala[b] = 2 * idx + 1
    urutan[0] = 0
    induk_t[0] = 0
    ekor = 1
    p = 0
    while p < ekor:
        u = urutan[p]
        p += 1
        s = kepala[u]
        while s >= 0:
            w = tujuan[s]
            if induk_t[w] < 0:
                induk_t[w] = u
                urutan[ekor] = w
                ekor += 1
            s = berikut[s]
    W = 0
    for p in range(nv - 1, 0, -1):
        u = urutan[p]
        ukuran[induk_t[u]] += ukuran[u]
        W += ukuran[u] * (nv - ukuran[u])
    return W


@njit(cache=True)
def _catat(pohon, eu, ev, nv, kerja, hist, hasil, cmin, cmaks, simpan):
    kepala, berikut, tujuan, urutan, induk_t, ukuran = kerja
    W = _wiener_pohon(pohon, eu, ev, nv, kepala, berikut, tujuan, urutan, induk_t, ukuran)
    hist[W] += 1
    hasil[0] += 1
    if W < hasil[1]:
        hasil[1] = W
        for t in range(nv - 1):
            cmin[t] = pohon[t]
    if W > hasil[2]:
        hasil[2] = W
        for t in range(nv - 1):
            cmaks[t] = pohon[t]
    if simpan.shape[0] > 0:
        pos = hasil[3]
        for t in range(nv - 1):
            simpan[pos, t] = pohon[t]
        hasil[3] = pos + 1


@njit(cache=True)
def _enumerasi_awalan(eu, ev, nv, bit_awalan, K, hist, hasil, cmin, cmaks, simpan):
    """Enumerasi semua pohon yang konsisten dengan keputusan K sisi pertama.

    hasil = [banyak pohon, W minimum, W maksimum, posisi simpan]."""
    m = eu.shape[0]
    perlu = nv - 1
    jatah_abaikan = m - perlu

    induk = np.empty(nv, np.int64)
    besar = np.ones(nv, np.int64)
    for i in range(nv):
        induk[i] = i
    rollback = np.empty(max(perlu, 1), np.int64)
    pohon = np.empty(max(perlu, 1), np.int64)
    kerja = (np.empty(nv, np.int64), np.empty(2 * nv, np.int64), np.empty(2 * nv, np.int64),
             np.empty(nv, np.int64), np.empty(nv, np.int64), np.empty(nv, np.int64))

    k = 0   # banyak sisi disertakan
    s = 0   # banyak sisi diabaikan
    for j in range(K):
        if (bit_awalan >> j) & 1:
            a = _akar(induk, eu[j])
            b = _akar(induk, ev[j])
            if a == b:
                return
            if besar[a] < besar[b]:
                a, b = b, a
            induk[b] = a
            besar[a] += besar[b]
            rollback[k] = b
            pohon[k] = j
            k += 1
        else:
            s += 1
            if s > jatah_abaikan:
                return
    if k == perlu:
        _catat(pohon, eu, ev, nv, kerja, hist, hasil, cmin, cmaks, simpan)
        return
    if K >= m:
        return

    # status[i]: 0 = belum dicoba, 1 = sudah coba "sertakan", 2 = sudah coba "abaikan"
    status = np.zeros(m, np.int8)
    disertakan = np.zeros(m, np.bool_)
    diabaikan = np.zeros(m, np.bool_)
    i = K
    while i >= K:
        st = status[i]
        if st == 0:
            status[i] = 1
            a = _akar(induk, eu[i])
            b = _akar(induk, ev[i])
            if a != b:
                if besar[a] < besar[b]:
                    a, b = b, a
                induk[b] = a
                besar[a] += besar[b]
                rollback[k] = b
                pohon[k] = i
                k += 1
                disertakan[i] = True
                if k == perlu:
                    _catat(pohon, eu, ev, nv, kerja, hist, hasil, cmin, cmaks, simpan)
                elif i + 1 < m:
                    i += 1
                    status[i] = 0
        elif st == 1:
            if disertakan[i]:
                k -= 1
                b = rollback[k]
                a = induk[b]
                besar[a] -= besar[b]
                induk[b] = b
                disertakan[i] = False
            status[i] = 2
            # pemangkasan: hanya boleh mengabaikan jika sisa sisi masih cukup
            if s < jatah_abaikan:
                s += 1
                diabaikan[i] = True
                i += 1
                status[i] = 0
        else:
            if diabaikan[i]:
                s -= 1
                diabaikan[i] = False
            i -= 1


@njit(cache=True, parallel=True)
def _enumerasi_kumpulan(eu, ev, nv, daftar_awalan, K, hist2, hasil2, cmin2, cmaks2, simpan_kosong):
    for j in prange(daftar_awalan.shape[0]):
        _enumerasi_awalan(eu, ev, nv, daftar_awalan[j], K, hist2[j], hasil2[j],
                          cmin2[j], cmaks2[j], simpan_kosong)


# ---------------------------------------------------------------------------
# Pembungkus Python
# ---------------------------------------------------------------------------

@dataclass
class HasilEnumerasi:
    banyak: int
    sebaran: dict[int, int]                 # W -> banyak pohon
    w_min: int
    w_maks: int
    banyak_min: int
    banyak_maks: int
    contoh_min: list[tuple[int, int]]       # sisi (indeks titik) contoh pohon minimum
    contoh_maks: list[tuple[int, int]]
    daftar: list[list[tuple[int, int]]] | None   # semua pohon (urutan enumerasi) bila diminta
    waktu: float
    metode: str


def _urutan_sisi(G: Graf) -> list[int]:
    """Urutkan sisi secara lokal (menurut urutan BFS ujungnya) agar siklus cepat terdeteksi."""
    adj = G.tetangga()
    nomor = [-1] * G.banyak_titik
    urut = 0
    for akar in range(G.banyak_titik):
        if nomor[akar] >= 0:
            continue
        nomor[akar] = urut
        urut += 1
        antre = [akar]
        for u in antre:
            for w in sorted(adj[u]):
                if nomor[w] < 0:
                    nomor[w] = urut
                    urut += 1
                    antre.append(w)
    return sorted(range(G.banyak_sisi),
                  key=lambda e: (max(nomor[G.sisi[e][0]], nomor[G.sisi[e][1]]),
                                 min(nomor[G.sisi[e][0]], nomor[G.sisi[e][1]])))


def _buat_awalan(eu: np.ndarray, ev: np.ndarray, nv: int, target: int) -> tuple[np.ndarray, int]:
    """Bangun awalan valid (tanpa siklus, jatah abaikan tidak terlampaui) untuk K sisi pertama."""
    m = len(eu)
    perlu = nv - 1
    jatah = m - perlu
    # setiap awalan: (bit, label komponen, k, s)
    jenis = bytes if nv < 256 else tuple          # label komponen ringkas
    lapis = [(0, jenis(range(nv)), 0, 0)]
    K = 0
    while len(lapis) < target and K < min(m - 1, 40):
        baru = []
        a, b = int(eu[K]), int(ev[K])
        for bit, label, k, s in lapis:
            if k < perlu and label[a] != label[b]:
                la, lb = label[a], label[b]
                label2 = jenis(la if x == lb else x for x in label)
                baru.append((bit | (1 << K), label2, k + 1, s))
            if s < jatah:
                baru.append((bit, label, k, s + 1))
        lapis = baru
        K += 1
    return np.array([x[0] for x in lapis], dtype=np.int64), K


def enumerasi_spanning_tree(G: Graf, tau: int | None = None, simpan_daftar: bool = False,
                            progres: bool = True, callback=None) -> HasilEnumerasi:
    """Enumerasi semua spanning tree G.

    tau      : τ(G) dari Teorema Matriks-Pohon (untuk progres; dihitung jika None).
    simpan_daftar: simpan semua pohon (hanya untuk τ kecil).
    callback : fungsi(selesai, total) opsional, mis. untuk Streamlit.
    """
    from .matriks_pohon import banyak_spanning_tree

    if tau is None:
        tau = banyak_spanning_tree(G)
    nv, m = G.banyak_titik, G.banyak_sisi
    mulai = time.perf_counter()
    if not ADA_NUMBA:
        warnings.warn(_PERINGATAN_TANPA_NUMBA, RuntimeWarning, stacklevel=2)
    metode = "numba" if ADA_NUMBA else "python-murni"

    if tau == 0:
        return HasilEnumerasi(0, {}, 0, 0, 0, 0, [], [], [] if simpan_daftar else None,
                              0.0, metode)
    if nv == 1:
        return HasilEnumerasi(1, {0: 1}, 0, 0, 1, 1, [], [], [[]] if simpan_daftar else None,
                              0.0, metode)

    urutan = _urutan_sisi(G)
    eu = np.array([G.sisi[e][0] for e in urutan], dtype=np.int64)
    ev = np.array([G.sisi[e][1] for e in urutan], dtype=np.int64)
    perlu = nv - 1
    w_batas = (nv ** 3 - nv) // 6          # W lintasan P_|V| = batas atas W pohon mana pun
    BESAR = np.iinfo(np.int64).max

    hist = np.zeros(w_batas + 1, dtype=np.int64)
    total_min, total_maks = BESAR, -1
    cmin = np.zeros(perlu, dtype=np.int64)
    cmaks = np.zeros(perlu, dtype=np.int64)
    daftar = None

    bar = None
    if progres:
        try:
            from tqdm import tqdm
            bar = tqdm(total=tau, unit=" pohon", unit_scale=True, desc=f"Enumerasi {G.nama}",
                       dynamic_ncols=True, smoothing=0.1)
        except ImportError:
            bar = None

    if simpan_daftar:
        simpan = np.zeros((tau, perlu), dtype=np.int64)
        hasil = np.array([0, BESAR, -1, 0], dtype=np.int64)
        _enumerasi_awalan(eu, ev, nv, np.int64(0), 0, hist, hasil, cmin, cmaks, simpan)
        ditemukan = int(hasil[0])
        total_min, total_maks = int(hasil[1]), int(hasil[2])
        daftar = [[(int(eu[e]), int(ev[e])) for e in baris] for baris in simpan[:ditemukan]]
        if bar is not None:
            bar.update(ditemukan)
        if callback is not None:
            callback(ditemukan, tau)
    else:
        target = 1 if tau < 20000 else int(min(262144, max(256, tau // 20000)))
        awalan, K = _buat_awalan(eu, ev, nv, target)
        utas = numba.get_num_threads() if ADA_NUMBA else 1
        ukuran_kumpulan = max(8 * utas, 32)
        # batasi memori histogram per kumpulan (~200 MB)
        ukuran_kumpulan = int(max(1, min(ukuran_kumpulan, 25_000_000 // (w_batas + 1))))
        simpan_kosong = np.zeros((0, perlu), dtype=np.int64)
        ditemukan = 0
        for awal in range(0, len(awalan), ukuran_kumpulan):
            potong = awalan[awal:awal + ukuran_kumpulan]
            b = len(potong)
            hist2 = np.zeros((b, w_batas + 1), dtype=np.int64)
            hasil2 = np.zeros((b, 4), dtype=np.int64)
            hasil2[:, 1] = BESAR
            hasil2[:, 2] = -1
            cmin2 = np.zeros((b, perlu), dtype=np.int64)
            cmaks2 = np.zeros((b, perlu), dtype=np.int64)
            if ADA_NUMBA:
                _enumerasi_kumpulan(eu, ev, nv, potong, K, hist2, hasil2, cmin2, cmaks2, simpan_kosong)
            else:
                for j in range(b):
                    _enumerasi_awalan(eu, ev, nv, int(potong[j]), K, hist2[j], hasil2[j],
                                      cmin2[j], cmaks2[j], simpan_kosong)
            hist += hist2.sum(axis=0)
            for j in range(b):
                if hasil2[j, 0] == 0:
                    continue
                if hasil2[j, 1] < total_min:
                    total_min = int(hasil2[j, 1])
                    cmin[:] = cmin2[j]
                if hasil2[j, 2] > total_maks:
                    total_maks = int(hasil2[j, 2])
                    cmaks[:] = cmaks2[j]
            tambah = int(hasil2[:, 0].sum())
            ditemukan += tambah
            if bar is not None:
                bar.update(tambah)
            if callback is not None:
                callback(ditemukan, tau)
    if bar is not None:
        bar.close()

    nz = np.nonzero(hist)[0]
    sebaran = {int(w): int(hist[w]) for w in nz}
    banyak = int(sum(sebaran.values()))
    if banyak != tau:
        raise RuntimeError(f"Banyak pohon hasil enumerasi ({banyak}) ≠ τ Matriks-Pohon ({tau}).")
    return HasilEnumerasi(
        banyak=banyak, sebaran=sebaran, w_min=total_min, w_maks=total_maks,
        banyak_min=sebaran[total_min], banyak_maks=sebaran[total_maks],
        contoh_min=sorted((int(eu[e]), int(ev[e])) for e in cmin),
        contoh_maks=sorted((int(eu[e]), int(ev[e])) for e in cmaks),
        daftar=daftar, waktu=time.perf_counter() - mulai, metode=metode)


def info_numba() -> str:
    if not ADA_NUMBA:
        return "Numba tidak terpasang (Python murni)"
    return f"Numba {numba.__version__}, {numba.get_num_threads()} utas"
