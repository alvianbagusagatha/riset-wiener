"""Analisis lengkap satu graf: titik, sisi, jarak, τ, dan spanning tree."""

from __future__ import annotations

from dataclasses import dataclass

from .enumerasi import ADA_NUMBA, HasilEnumerasi, enumerasi_spanning_tree
from .graf import Graf
from .jarak import DistribusiJarak, distribusi_jarak, wiener_pohon_rumus_sisi
from .matriks_pohon import banyak_spanning_tree
from .terkecil import cari_pohon_terkecil

BATAS_ENUMERASI_BAWAAN = None   # None = tanpa batas (CLI --batas: di atasnya dipakai mode cepat)
BATAS_DAFTAR_POHON = 5000      # daftar pohon (Excel, galeri): semua jika τ ≤ 5000, selebihnya 5000 W terkecil
BATAS_SIMPAN_PENUH = 50_000    # τ ≤ ini: semua pohon disimpan saat enumerasi lalu diurutkan
BATAS_GAMBAR_KISI = 100        # gambar kisi semua pohon jika τ ≤ 100
BATAS_DETIK_OTOMATIS = 20      # mode otomatis: enumerasi lengkap hanya bila perkiraannya ≤ ini


def laju_enumerasi() -> float:
    """Perkiraan kasar banyak pohon per detik pada komputer ini."""
    if not ADA_NUMBA:
        return 50_000.0
    import numba
    return 350_000.0 * numba.get_num_threads()


def perkiraan_detik(tau: int) -> float:
    return tau / laju_enumerasi()


@dataclass
class InfoPohon:
    nomor: int                      # nomor pada daftar (0 = tidak termasuk daftar)
    sisi: list[tuple[int, int]]
    W: int
    distribusi: DistribusiJarak


@dataclass
class HasilGraf:
    graf: Graf
    derajat: list[int]
    distribusi: DistribusiJarak
    tau: int
    enumerasi: HasilEnumerasi | None      # None pada mode cepat (sebaran W lengkap tidak dihitung)
    catatan_enumerasi: str | None
    contoh_min: InfoPohon | None
    contoh_maks: InfoPohon | None         # None pada mode cepat
    daftar: list[InfoPohon] | None
    daftar_lengkap: bool = True           # True: daftar berisi SEMUA τ pohon
    mode: str = "lengkap"                 # "lengkap" (semua pohon dienumerasi) atau "cepat"
    terverifikasi: bool = True            # daftar = W terkecil yang PASTI (dicek dengan sebaran W)
    keterangan_daftar: str = ""


def info_pohon(G: Graf, sisi: list[tuple[int, int]], nomor: int = 0) -> InfoPohon:
    T = G.subgraf_sisi(sisi)
    dist = distribusi_jarak(T)
    W = wiener_pohon_rumus_sisi(G.banyak_titik, sisi)
    if dist.W != W:
        raise RuntimeError("W(T) dari rumus sisi berbeda dengan W(T) dari distribusi jarak.")
    if dist.total_pasangan != dist.pasangan_seharusnya:
        raise RuntimeError("Σ N_t pohon tidak sama dengan C(|V|, 2).")
    return InfoPohon(nomor=nomor, sisi=sorted(sisi), W=W, distribusi=dist)


def _w_terkecil_pasti(sebaran: dict[int, int], k: int) -> list[int]:
    """k nilai W terkecil (dengan pengulangan) menurut sebaran W lengkap."""
    hasil: list[int] = []
    for w in sorted(sebaran):
        hasil += [w] * min(sebaran[w], k - len(hasil))
        if len(hasil) >= k:
            break
    return hasil


def _angka(x: int) -> str:
    return f"{x:,}".replace(",", ".")


def _lama(detik: float) -> str:
    for batas, satuan, bagi in ((60, "detik", 1), (3600, "menit", 60), (86400, "jam", 3600),
                                (86400 * 365, "hari", 86400)):
        if detik < batas:
            return f"{detik / bagi:.0f} {satuan}"
    return f"{detik / (86400 * 365):.0f} tahun"


def analisis_graf(G: Graf, batas: int | None = BATAS_ENUMERASI_BAWAAN, progres: bool = True,
                  callback=None, mode: str = "otomatis") -> HasilGraf:
    """Analisis lengkap satu graf.

    mode: "otomatis" — enumerasi semua pohon bila perkiraannya ≤ BATAS_DETIK_OTOMATIS detik
                       (dan τ ≤ batas, bila batas diisi), selain itu mode cepat;
          "lengkap"  — selalu enumerasi semua pohon (bisa sangat lama);
          "cepat"    — tanpa enumerasi lengkap: hanya cari BATAS_DAFTAR_POHON pohon W terkecil.
    Daftar pohon (galeri/Excel) selalu: semua pohon bila τ ≤ BATAS_DAFTAR_POHON, selebihnya
    BATAS_DAFTAR_POHON pohon dengan W terkecil, urut menurut W.
    """
    dist = distribusi_jarak(G)
    if dist.terhubung and dist.total_pasangan != dist.pasangan_seharusnya:
        raise RuntimeError("Σ N_t tidak sama dengan C(|V|, 2).")
    tau = banyak_spanning_tree(G)
    k = min(tau, BATAS_DAFTAR_POHON)
    hasil = HasilGraf(graf=G, derajat=G.derajat(), distribusi=dist, tau=tau, enumerasi=None,
                      catatan_enumerasi=None, contoh_min=None, contoh_maks=None, daftar=None)
    if tau == 0:
        hasil.catatan_enumerasi = "Graf tidak terhubung sehingga tidak memiliki spanning tree (τ = 0)."
        return hasil

    if mode == "otomatis":
        lengkap = perkiraan_detik(tau) <= BATAS_DETIK_OTOMATIS and (batas is None or tau <= batas)
    else:
        lengkap = mode == "lengkap"
    lengkap = lengkap or tau <= BATAS_SIMPAN_PENUH       # τ kecil: enumerasi selalu sekejap

    if lengkap:
        enum = enumerasi_spanning_tree(G, tau=tau, simpan_daftar=tau <= BATAS_SIMPAN_PENUH,
                                       progres=progres, callback=callback)
        hasil.enumerasi = enum
        if enum.daftar is not None:                       # semua pohon tersimpan: urutkan, ambil k
            sisi_pohon = enum.daftar
            enum.daftar = None
        else:                                             # τ besar: cari, lalu cek dengan sebaran W
            cari = cari_pohon_terkecil(G, k)
            sisi_pohon = cari.pohon
            hasil.terverifikasi = cari.w == _w_terkecil_pasti(enum.sebaran, k)
    else:
        cari = cari_pohon_terkecil(G, k, callback=callback)
        sisi_pohon = cari.pohon
        hasil.mode = "cepat"
        hasil.terverifikasi = False

    if len(sisi_pohon) > k:                               # urutkan menurut W dulu (murah), baru hitung detail
        from .jarak import wiener_pohon_rumus_sisi as _w
        sisi_pohon = sorted(sisi_pohon, key=lambda s: _w(G.banyak_titik, s))[:k]
    pohon = [info_pohon(G, s) for s in sisi_pohon]
    pohon.sort(key=lambda p: p.W)                          # stabil: urutan semula dipertahankan
    for no, p in enumerate(pohon, start=1):
        p.nomor = no
    hasil.daftar = pohon
    hasil.daftar_lengkap = len(pohon) == tau
    hasil.contoh_min = pohon[0]
    if hasil.enumerasi is not None:
        e = hasil.enumerasi
        if pohon[0].W != e.w_min:
            hasil.contoh_min = info_pohon(G, e.contoh_min)
        hasil.contoh_maks = next((p for p in pohon if p.W == e.w_maks), None) or info_pohon(G, e.contoh_maks)

    if hasil.daftar_lengkap:
        hasil.keterangan_daftar = f"Semua {_angka(tau)} spanning tree, urut menurut W."
    elif hasil.mode == "lengkap" and hasil.terverifikasi:
        hasil.keterangan_daftar = (f"{_angka(k)} spanning tree dengan W terkecil dari τ = {_angka(tau)} pohon, "
                                   "urut menurut W (pasti: dicek dengan sebaran W semua pohon).")
    elif hasil.mode == "lengkap":
        hasil.keterangan_daftar = (f"{_angka(k)} spanning tree dengan W terkecil yang ditemukan dari "
                                   f"τ = {_angka(tau)} pohon (BELUM cocok penuh dengan sebaran W semua pohon).")
    else:
        hasil.keterangan_daftar = (f"{_angka(k)} spanning tree dengan W terkecil yang ditemukan dari "
                                   f"τ = {_angka(tau)} pohon, urut menurut W (mode cepat: tidak semua pohon "
                                   "dihitung, jadi belum dijamin minimum mutlak).")
        hasil.catatan_enumerasi = (f"Mode cepat: τ = {_angka(tau)} terlalu banyak untuk dihitung satu per satu "
                                   f"(±{_lama(perkiraan_detik(tau))}). Yang dihitung: {_angka(k)} pohon dengan W "
                                   "terkecil yang ditemukan oleh pencarian. Sebaran W dan W maksimum semua pohon "
                                   "tidak dihitung.")
    return hasil


def format_angka(x) -> str:
    """Pemisah ribuan gaya Indonesia: 2620860 -> 2.620.860."""
    if isinstance(x, int):
        return f"{x:,}".replace(",", ".")
    return str(x)
