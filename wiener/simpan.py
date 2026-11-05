"""Menyimpan semua keluaran ke folder hasil/<nama_graf>_n<n>/."""

from __future__ import annotations

from pathlib import Path

from .analisis import BATAS_GAMBAR_KISI, HasilGraf
from .excel import simpan_excel_graf, simpan_excel_pola
from .latex import latex_graf, latex_pola, simpan_tex
from .pola import HasilPola


def simpan_hasil_graf(h: HasilGraf, akar: str | Path = "hasil", gambar: bool = True) -> dict[str, list[Path]]:
    from . import gambar as gb

    G = h.graf
    folder = Path(akar) / G.kode
    folder.mkdir(parents=True, exist_ok=True)
    berkas: dict[str, list[Path]] = {}
    berkas["excel"] = [simpan_excel_graf(h, folder / f"{G.kode}.xlsx")]
    berkas["latex"] = [simpan_tex(latex_graf(h), folder / f"{G.kode}.tex")]
    if gambar:
        nt = f"${G.nama_tex}$" if G.nama_tex else G.nama.replace("_", " ")
        berkas["gambar"] = gb.gambar_graf(G, folder / f"{G.kode}_graf", judul=nt)
        if h.contoh_min is not None:
            berkas["gambar"] += gb.gambar_pohon(
                G, h.contoh_min.sisi, folder / f"{G.kode}_pohon_minimum",
                judul=f"Spanning tree minimum {nt}:  W = {h.contoh_min.W}")
            berkas["gambar"] += gb.gambar_pohon(
                G, h.contoh_maks.sisi, folder / f"{G.kode}_pohon_maksimum",
                judul=f"Spanning tree maksimum {nt}:  W = {h.contoh_maks.W}")
        if h.daftar is not None and h.tau <= BATAS_GAMBAR_KISI:
            berkas["gambar"] += gb.gambar_kisi(
                G, h.daftar, folder / f"{G.kode}_semua_pohon",
                judul=f"Semua {h.tau} spanning tree {nt} (urut menurut W)")
        elif h.daftar is not None and h.tau <= BATAS_PDF_SEMUA_POHON:
            berkas["gambar"].append(simpan_pdf_semua_pohon(h, akar))
    return berkas


BATAS_PDF_SEMUA_POHON = 1000     # PDF semua pohon dibuat otomatis jika τ ≤ 1000 (lebih besar: atas permintaan)


def simpan_pdf_semua_pohon(h: HasilGraf, akar: str | Path = "hasil") -> Path:
    """PDF berhalaman berisi SEMUA spanning tree (48 per halaman), nomor sama dengan Excel."""
    from . import gambar as gb

    G = h.graf
    return gb.gambar_kisi_pdf(G, h.daftar, Path(akar) / G.kode / f"{G.kode}_semua_pohon.pdf",
                              judul=f"Semua {h.tau} spanning tree {G.nama} (urut menurut W)")


def simpan_hasil_pola(hp: HasilPola, akar: str | Path = "hasil") -> dict[str, list[Path]]:
    kode = f"pola_{hp.kode}_n{hp.dari}-{hp.sampai}"
    folder = Path(akar) / kode
    folder.mkdir(parents=True, exist_ok=True)
    return {"excel": [simpan_excel_pola(hp, folder / f"{kode}.xlsx")],
            "latex": [simpan_tex(latex_pola(hp), folder / f"{kode}.tex")]}
