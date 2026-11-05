"""Gambar graf dan spanning tree (PNG 300 dpi dan PDF) dengan matplotlib."""

from __future__ import annotations

import math
import re
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402

from .graf import Graf  # noqa: E402
from .jarak import matriks_jarak  # noqa: E402

MERAH = "#d62728"
HITAM = "#111111"
ABU = "#9a9a9a"


def label_tex(nama: str) -> str:
    """x1 -> $x_{1}$ sehingga tampil sebagai x₁."""
    m = re.fullmatch(r"([A-Za-z]+)_?(\d+)_(\d+)", nama)
    if m:                                   # x1_3 -> x_{1,3}
        return rf"${m.group(1)}_{{{m.group(2)},{m.group(3)}}}$"
    m = re.fullmatch(r"([A-Za-z]+)_?(\d+)", nama)
    if m:
        return rf"${m.group(1)}_{{{m.group(2)}}}$"
    return rf"${nama}$" if re.fullmatch(r"[A-Za-z]+", nama) else nama


def warna_titik(G: Graf, nama: str) -> str:
    # titik x (lingkaran dalam / baris atas) merah, lainnya hitam
    return MERAH if nama.startswith("x") else HITAM


def posisi_graf(G: Graf) -> dict[str, tuple[float, float]]:
    if G.posisi is not None:
        return G.posisi
    n = G.banyak_titik
    if n == 1:
        return {G.titik[0]: (0.0, 0.0)}
    # MDS klasik dari matriks jarak (deterministik), cadangan: lingkaran
    D = np.array(matriks_jarak(G), dtype=float)
    if (D < 0).any():
        D[D < 0] = D.max() + 1
    J = np.eye(n) - np.ones((n, n)) / n
    B = -0.5 * J @ (D ** 2) @ J
    nilai, vektor = np.linalg.eigh(B)
    urut = np.argsort(nilai)[::-1][:2]
    if nilai[urut[-1]] <= 1e-9:
        return {t: (math.cos(math.pi / 2 - 2 * math.pi * i / n), math.sin(math.pi / 2 - 2 * math.pi * i / n))
                for i, t in enumerate(G.titik)}
    X = vektor[:, urut] * np.sqrt(nilai[urut])
    # sedikit relaksasi pegas agar titik tidak menumpuk
    for _ in range(200):
        selisih = X[:, None, :] - X[None, :, :]
        jarak = np.linalg.norm(selisih, axis=2) + np.eye(n)
        target = np.where(D > 0, D, 1)
        gaya = ((target - jarak) / jarak / target ** 2)[:, :, None] * selisih
        np.fill_diagonal(gaya[:, :, 0], 0)
        np.fill_diagonal(gaya[:, :, 1], 0)
        X += 0.05 * gaya.sum(axis=1)
    return {t: (float(X[i, 0]), float(X[i, 1])) for i, t in enumerate(G.titik)}


def _arah_label(G: Graf, pos: dict) -> dict[str, tuple[float, float]]:
    xs = np.array([p[0] for p in pos.values()])
    ys = np.array([p[1] for p in pos.values()])
    cx, cy = xs.mean(), ys.mean()
    rmaks = max(1e-9, float(np.max(np.hypot(xs - cx, ys - cy))))
    arah = {}
    for t, (x, y) in pos.items():
        if G.tata_letak == "tangga":
            arah[t] = (0.0, 1.0) if t.startswith("x") else (0.0, -1.0)
            continue
        if G.tata_letak == "lintasan" or (np.ptp(ys) < 1e-9):
            arah[t] = (0.0, -1.0)
            continue
        if G.tata_letak == "kipas":
            arah[t] = (0.0, 1.0) if t == "c" else (0.0, -1.0)
            continue
        dx, dy = x - cx, y - cy
        r = math.hypot(dx, dy)
        if r < 0.1 * rmaks:
            arah[t] = (0.7, 0.7)
            continue
        dx, dy = dx / r, dy / r
        if G.tata_letak == "lingkaran-ganda" and r < 0.8 * rmaks:
            dx, dy = -dx, -dy          # titik lingkaran dalam: label ke arah pusat
        arah[t] = (dx, dy)
    return arah


def _skala(pos) -> float:
    xs = [p[0] for p in pos.values()]
    ys = [p[1] for p in pos.values()]
    return max(max(xs) - min(xs), max(ys) - min(ys), 1.0)


def _gambar_ke_sumbu(ax, G: Graf, pos, sisi_pohon=None, label=True, ukuran_titik=60,
                     tebal_pohon=2.8, ukuran_font=11):
    pohon = set(sisi_pohon) if sisi_pohon is not None else None
    for e in G.sisi:
        (x1, y1), (x2, y2) = pos[G.titik[e[0]]], pos[G.titik[e[1]]]
        if pohon is None:
            ax.plot([x1, x2], [y1, y2], color=HITAM, lw=1.4, zorder=1, solid_capstyle="round")
        elif e in pohon:
            ax.plot([x1, x2], [y1, y2], color=HITAM, lw=tebal_pohon, zorder=2, solid_capstyle="round")
        else:
            ax.plot([x1, x2], [y1, y2], color=ABU, lw=1.0, ls=(0, (4, 3)), zorder=1)
    for t in G.titik:
        x, y = pos[t]
        ax.scatter([x], [y], s=ukuran_titik, color=warna_titik(G, t), zorder=3,
                   edgecolors="white", linewidths=0.8)
    if label:
        arah = _arah_label(G, pos)
        jarak_label = 0.075 * _skala(pos)
        letak = []
        for t in G.titik:
            x, y = pos[t]
            dx, dy = arah[t]
            lx, ly = x + dx * jarak_label, y + dy * jarak_label
            letak.append((lx + dx * 0.3 * jarak_label, ly + dy * 0.3 * jarak_label))
            ax.text(lx, ly, label_tex(t), ha="center", va="center",
                    fontsize=ukuran_font, color=warna_titik(G, t), zorder=4)
        # sertakan letak label dalam batas sumbu agar tidak bertabrakan dengan judul
        ax.update_datalim(letak)
        ax.autoscale_view()
    ax.set_aspect("equal")
    ax.axis("off")
    ax.margins(0.12)


def _ukuran_gambar(pos, dasar=6.0):
    xs = [p[0] for p in pos.values()]
    ys = [p[1] for p in pos.values()]
    lebar = max(xs) - min(xs) or 1.0
    tinggi = max(ys) - min(ys) or 0.3
    rasio = min(max(tinggi / lebar, 0.25), 1.6)
    return (dasar, max(2.2, dasar * rasio))


def _simpan(fig, jalur_dasar: Path) -> list[Path]:
    jalur_dasar.parent.mkdir(parents=True, exist_ok=True)
    png = jalur_dasar.with_suffix(".png")
    pdf = jalur_dasar.with_suffix(".pdf")
    fig.savefig(png, dpi=300, bbox_inches="tight")
    fig.savefig(pdf, bbox_inches="tight")
    plt.close(fig)
    return [png, pdf]


def gambar_graf(G: Graf, jalur_dasar: Path, judul: str | None = None) -> list[Path]:
    pos = posisi_graf(G)
    fig, ax = plt.subplots(figsize=_ukuran_gambar(pos))
    _gambar_ke_sumbu(ax, G, pos)
    if judul:
        ax.set_title(judul, fontsize=13)
    return _simpan(fig, jalur_dasar)


def gambar_pohon(G: Graf, sisi_pohon, jalur_dasar: Path, judul: str | None = None) -> list[Path]:
    pos = posisi_graf(G)
    fig, ax = plt.subplots(figsize=_ukuran_gambar(pos))
    _gambar_ke_sumbu(ax, G, pos, sisi_pohon=sisi_pohon)
    if judul:
        ax.set_title(judul, fontsize=13)
    return _simpan(fig, jalur_dasar)


def gambar_kisi(G: Graf, daftar, jalur_dasar: Path, judul: str | None = None) -> list[Path]:
    """Semua spanning tree dalam satu kisi; nomor sama dengan daftar di Excel."""
    pos = posisi_graf(G)
    k = len(daftar)
    kolom = max(1, math.ceil(math.sqrt(k * 1.3)))
    baris = math.ceil(k / kolom)
    lebar_sel = 1.9
    w, h = _ukuran_gambar(pos, dasar=lebar_sel)
    fig, sumbu = plt.subplots(baris, kolom, figsize=(kolom * w, baris * (h + 0.35)), squeeze=False)
    tampil_label = G.banyak_titik <= 8
    for idx, ax in enumerate(sumbu.flat):
        if idx >= k:
            ax.axis("off")
            continue
        t = daftar[idx]
        _gambar_ke_sumbu(ax, G, pos, sisi_pohon=t.sisi, label=tampil_label, ukuran_titik=14,
                         tebal_pohon=1.8, ukuran_font=6)
        ax.set_title(f"No. {t.nomor}  (W = {t.W})", fontsize=7)
    if judul:
        fig.suptitle(judul, fontsize=12)
    fig.tight_layout()
    return _simpan(fig, jalur_dasar)


def gambar_kisi_pdf(G: Graf, daftar, jalur_pdf: Path, judul: str | None = None,
                    kolom: int = 6, baris: int = 8) -> Path:
    """Semua spanning tree dalam PDF bergaya kisi, beberapa halaman (48 pohon per halaman).

    Setiap halaman digambar pada SATU sumbu (semua sisi dalam satu LineCollection), sehingga
    ribuan pohon tetap cepat."""
    from matplotlib.backends.backend_pdf import PdfPages
    from matplotlib.collections import LineCollection

    pos = posisi_graf(G)
    xy = np.array([pos[t] for t in G.titik], dtype=float)
    xy -= xy.min(axis=0)
    rentang = xy.max(axis=0)
    rentang[rentang == 0] = 1.0
    skala = 0.78 / rentang.max()
    xy = xy * skala + (1 - rentang * skala) / 2          # pusatkan dalam sel 1 x 1
    xy[:, 1] = xy[:, 1] * 0.86                            # sisakan ruang judul sel
    warna = [warna_titik(G, t) for t in G.titik]
    sisi = list(G.sisi)
    per_hal = kolom * baris
    total = max(1, -(-len(daftar) // per_hal))
    jalur_pdf.parent.mkdir(parents=True, exist_ok=True)
    with PdfPages(jalur_pdf) as pdf:
        for hal in range(total):
            fig = plt.figure(figsize=(8.27, 11.69))           # A4 tegak
            ax = fig.add_axes((0.03, 0.03, 0.94, 0.91))
            seg_p, seg_b, titik_x, titik_y, warna_t = [], [], [], [], []
            for idx, t in enumerate(daftar[hal * per_hal:(hal + 1) * per_hal]):
                c, r = idx % kolom, idx // kolom
                ox, oy = c * 1.0, (baris - 1 - r) * 1.0
                pohon = set(t.sisi)
                for a, b in sisi:
                    seg = [(xy[a, 0] + ox, xy[a, 1] + oy), (xy[b, 0] + ox, xy[b, 1] + oy)]
                    (seg_p if (a, b) in pohon else seg_b).append(seg)
                titik_x.extend(xy[:, 0] + ox)
                titik_y.extend(xy[:, 1] + oy)
                warna_t.extend(warna)
                ax.text(ox + 0.5, oy + 0.93, f"No. {t.nomor}  (W = {t.W})", ha="center", va="center", fontsize=6.5)
            ax.add_collection(LineCollection(seg_b, colors=ABU, linewidths=0.5, linestyles=(0, (3, 2))))
            ax.add_collection(LineCollection(seg_p, colors=HITAM, linewidths=1.4))
            ax.scatter(titik_x, titik_y, s=7, c=warna_t, zorder=3, linewidths=0)
            ax.set_xlim(0, kolom)
            ax.set_ylim(0, baris)
            ax.set_aspect("equal")
            ax.axis("off")
            fig.suptitle(f"{judul or ''}   — halaman {hal + 1}/{total}", fontsize=10)
            pdf.savefig(fig)
            plt.close(fig)
    return jalur_pdf
