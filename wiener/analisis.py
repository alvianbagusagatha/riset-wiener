"""Analisis lengkap satu graf: titik, sisi, jarak, τ, dan spanning tree."""

from __future__ import annotations

from dataclasses import dataclass

from .enumerasi import HasilEnumerasi, enumerasi_spanning_tree, pohon_acak_seragam
from .graf import Graf
from .jarak import DistribusiJarak, distribusi_jarak, wiener_pohon_rumus_sisi
from .matriks_pohon import banyak_spanning_tree

BATAS_ENUMERASI_BAWAAN = None   # None = tanpa batas (semua pohon selalu dienumerasi)
BATAS_DAFTAR_POHON = 5000      # daftar pohon (Excel, galeri): semua jika τ ≤ 5000, selebihnya sampel 5000
BATAS_SIMPAN_PENUH = 50_000    # τ ≤ ini: sampel diambil dari daftar lengkap hasil enumerasi
BATAS_GAMBAR_KISI = 100        # gambar kisi semua pohon jika τ ≤ 100
BIBIT_SAMPEL = 2026            # sampel acak tetap sama setiap kali dihitung


@dataclass
class InfoPohon:
    nomor: int
    sisi: list[tuple[int, int]]
    W: int
    distribusi: DistribusiJarak


@dataclass
class HasilGraf:
    graf: Graf
    derajat: list[int]
    distribusi: DistribusiJarak
    tau: int
    enumerasi: HasilEnumerasi | None
    catatan_enumerasi: str | None
    contoh_min: InfoPohon | None
    contoh_maks: InfoPohon | None
    daftar: list[InfoPohon] | None
    daftar_lengkap: bool = True    # False: daftar hanya sampel BATAS_DAFTAR_POHON pohon dari τ


def _sampel(G: Graf, enum: HasilEnumerasi, tau: int) -> list[list[tuple[int, int]]]:
    """BATAS_DAFTAR_POHON pohon berbeda: contoh minimum & maksimum + sampel acak seragam."""
    wajib = [sorted(enum.contoh_min), sorted(enum.contoh_maks)]
    if enum.daftar is not None:                       # τ sedang: ambil acak dari daftar lengkap
        import random
        kunci_wajib = {frozenset(p) for p in wajib}
        sisa = [sorted(p) for p in enum.daftar if frozenset(p) not in kunci_wajib]
        pilih = random.Random(BIBIT_SAMPEL).sample(sisa, BATAS_DAFTAR_POHON - len(kunci_wajib))
        return [list(p) for p in {frozenset(p): p for p in wajib}.values()] + pilih
    return pohon_acak_seragam(G, BATAS_DAFTAR_POHON, seed=BIBIT_SAMPEL, sudah=wajib)


def info_pohon(G: Graf, sisi: list[tuple[int, int]], nomor: int = 0) -> InfoPohon:
    T = G.subgraf_sisi(sisi)
    dist = distribusi_jarak(T)
    W = wiener_pohon_rumus_sisi(G.banyak_titik, sisi)
    if dist.W != W:
        raise RuntimeError("W(T) dari rumus sisi berbeda dengan W(T) dari distribusi jarak.")
    if dist.total_pasangan != dist.pasangan_seharusnya:
        raise RuntimeError("Σ N_t pohon tidak sama dengan C(|V|, 2).")
    return InfoPohon(nomor=nomor, sisi=sorted(sisi), W=W, distribusi=dist)


def analisis_graf(G: Graf, batas: int | None = BATAS_ENUMERASI_BAWAAN, progres: bool = True,
                  callback=None) -> HasilGraf:
    dist = distribusi_jarak(G)
    if dist.terhubung and dist.total_pasangan != dist.pasangan_seharusnya:
        raise RuntimeError("Σ N_t tidak sama dengan C(|V|, 2).")
    tau = banyak_spanning_tree(G)

    enum = None
    catatan = None
    contoh_min = contoh_maks = None
    daftar = None
    if tau == 0:
        catatan = "Graf tidak terhubung sehingga tidak memiliki spanning tree (τ = 0)."
    elif batas is not None and tau > batas:
        catatan = (f"τ = {tau:,} melebihi batas enumerasi {batas:,}; enumerasi dilewati. "
                   "Naikkan batas dengan --batas jika ingin tetap dihitung.").replace(",", ".")
    else:
        simpan = tau <= BATAS_SIMPAN_PENUH
        enum = enumerasi_spanning_tree(G, tau=tau, simpan_daftar=simpan, progres=progres,
                                       callback=callback)
        contoh_min = info_pohon(G, enum.contoh_min)
        contoh_maks = info_pohon(G, enum.contoh_maks)
        lengkap = tau <= BATAS_DAFTAR_POHON
        sisi_pohon = enum.daftar if lengkap else _sampel(G, enum, tau)
        if sisi_pohon is not None:
            pohon = [info_pohon(G, s) for s in sisi_pohon]
            pohon.sort(key=lambda p: p.W)          # stabil: urutan enumerasi dipertahankan
            for no, p in enumerate(pohon, start=1):
                p.nomor = no
            daftar = pohon
            # contoh = pohon pertama yang mencapai min/maks pada daftar bernomor
            contoh_min = next(p for p in pohon if p.W == enum.w_min)
            contoh_maks = next(p for p in pohon if p.W == enum.w_maks)
        if not lengkap:
            enum.daftar = None                     # daftar lengkap τ sedang tidak perlu disimpan
    return HasilGraf(graf=G, derajat=G.derajat(), distribusi=dist, tau=tau, enumerasi=enum,
                     catatan_enumerasi=catatan, contoh_min=contoh_min, contoh_maks=contoh_maks,
                     daftar=daftar, daftar_lengkap=daftar is None or len(daftar) == tau)


def format_angka(x) -> str:
    """Pemisah ribuan gaya Indonesia: 2620860 -> 2.620.860."""
    if isinstance(x, int):
        return f"{x:,}".replace(",", ".")
    return str(x)
