"""Deteksi graf (titik dan sisi) dari gambar: foto gambar tangan, hasil pindai, atau tangkapan layar.

Cara kerja (OpenCV, tanpa internet):
1. Gambar diubah menjadi topeng tinta (ambang adaptif; latar gelap dibalik otomatis).
2. Tebal goresan garis diperkirakan dari transformasi jarak.
3. Lubang kecil (lingkaran titik yang tidak diisi, huruf di dalam lingkaran) diisi.
4. Operasi "opening" dengan cakram sedikit lebih tebal dari garis menghapus garis dan huruf,
   sehingga yang tersisa hanya titik-titik (bulatan tebal) -> TITIK.
5. Dua titik dihubungkan jika hampir seluruh ruas lurus di antara keduanya berwarna tinta -> SISI.
   Ruas yang melewati titik lain diabaikan (yang benar adalah dua sisi terpisah).

Paling andal untuk: titik berupa bulatan penuh/lingkaran yang jelas lebih tebal dari garis, dan
sisi berupa garis (hampir) lurus. Label huruf tidak dibaca; titik diberi nama v1, v2, … dan
dapat diganti di editor.
"""

from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np

LEBAR_KANVAS, TINGGI_KANVAS, TEPI = 800, 520, 50


@dataclass
class HasilDeteksi:
    titik: list[dict]                    # [{"nama", "x", "y"}] koordinat kanvas editor
    sisi: list[list[str]]
    tebal_garis: float
    peringatan: list[str] = field(default_factory=list)

    def isi_editor(self) -> dict:
        return {"titik": self.titik, "sisi": self.sisi, "tata_letak": "bebas"}


def _cv2():
    try:
        import cv2
    except ImportError as e:  # pragma: no cover
        raise RuntimeError("Fitur unggah gambar memerlukan OpenCV: pip install opencv-python-headless") from e
    return cv2


def _baca(data: bytes):
    cv2 = _cv2()
    arr = np.frombuffer(data, dtype=np.uint8)
    img = cv2.imdecode(arr, cv2.IMREAD_UNCHANGED)
    if img is None:
        raise ValueError("Berkas tidak dapat dibaca sebagai gambar (gunakan PNG atau JPG).")
    if img.ndim == 3 and img.shape[2] == 4:          # transparansi -> latar putih
        alfa = img[:, :, 3:4].astype(np.float32) / 255
        img = (img[:, :, :3] * alfa + 255 * (1 - alfa)).astype(np.uint8)
    if img.ndim == 3:
        img = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    return img


def _topeng_tinta(abu: np.ndarray) -> np.ndarray:
    cv2 = _cv2()
    h, w = abu.shape
    skala = 1000 / max(h, w)
    if skala < 1:
        abu = cv2.resize(abu, (int(w * skala), int(h * skala)), interpolation=cv2.INTER_AREA)
    elif skala > 1.6:
        abu = cv2.resize(abu, (int(w * skala), int(h * skala)), interpolation=cv2.INTER_CUBIC)
    if np.median(abu) < 110:                          # latar gelap (mis. mode gelap) -> balik
        abu = 255 - abu
    abu = cv2.GaussianBlur(abu, (3, 3), 0)
    blok = max(31, (max(abu.shape) // 12) | 1)
    tinta = cv2.adaptiveThreshold(abu, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY_INV, blok, 12)
    # buang bintik derau kecil
    n, lab, stat, _ = cv2.connectedComponentsWithStats(tinta, connectivity=8)
    kecil = stat[:, cv2.CC_STAT_AREA] < 12
    kecil[0] = False
    tinta[kecil[lab]] = 0
    return tinta


def _tebal_garis(tinta: np.ndarray) -> float:
    cv2 = _cv2()
    dt = cv2.distanceTransform(tinta, cv2.DIST_L2, 5)
    puncak = (dt >= cv2.dilate(dt, np.ones((3, 3), np.uint8))) & (dt > 0.5)
    nilai = dt[puncak]
    if nilai.size == 0:
        return 2.0
    return float(max(1.5, 2 * np.percentile(nilai, 40)))


def _isi_lubang_kecil(tinta: np.ndarray, luas_maks: float) -> np.ndarray:
    cv2 = _cv2()
    latar = (tinta == 0).astype(np.uint8)
    n, lab, stat, _ = cv2.connectedComponentsWithStats(latar, connectivity=4)
    h, w = tinta.shape
    hasil = tinta.copy()
    for k in range(1, n):
        x, y, bw, bh, luas = stat[k]
        menyentuh_tepi = x == 0 or y == 0 or x + bw >= w or y + bh >= h
        if menyentuh_tepi or luas > luas_maks:
            continue
        if max(bw, bh) > 2.5 * min(bw, bh) + 2:      # lubang memanjang (mis. antara dua garis), lewati
            continue
        hasil[lab == k] = 255
    return hasil


def deteksi_graf(data: bytes) -> HasilDeteksi:
    """Deteksi titik dan sisi dari isi berkas gambar (bytes PNG/JPG)."""
    cv2 = _cv2()
    tinta = _topeng_tinta(_baca(data))
    if tinta.sum() == 0:
        raise ValueError("Gambar tampak kosong; tidak ada goresan yang terdeteksi.")
    w_garis = _tebal_garis(tinta)
    terisi = _isi_lubang_kecil(tinta, luas_maks=np.pi * (6 * w_garis) ** 2)

    # titik = bagian yang lebih tebal dari garis biasa
    d = int(round(2.3 * w_garis)) | 1
    d = max(d, 5)
    cakram = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (d, d))
    gumpal = cv2.morphologyEx(terisi, cv2.MORPH_OPEN, cakram)
    n, lab, stat, pusat = cv2.connectedComponentsWithStats(gumpal, connectivity=8)
    dt = cv2.distanceTransform(terisi, cv2.DIST_L2, 5)
    calon = []   # (x, y, jari-jari, ketebalan = jari-jari lingkaran terbesar di dalamnya)
    for k in range(1, n):
        x, y, bw, bh, luas = stat[k]
        if luas < 0.6 * d * d:
            continue
        if max(bw, bh) > 3 * min(bw, bh):            # terlalu lonjong untuk sebuah titik
            continue
        r = float(np.sqrt(luas / np.pi))
        tebal = float(dt[y:y + bh, x:x + bw][lab[y:y + bh, x:x + bw] == k].max())
        calon.append((float(pusat[k][0]), float(pusat[k][1]), r, tebal))
    peringatan = []
    if not calon:
        raise ValueError("Tidak ada titik yang terdeteksi. Pastikan titik digambar sebagai bulatan "
                         "yang lebih tebal dari garis sisi.")
    # gumpalan jauh lebih kecil dari titik pada umumnya biasanya huruf label yang menimpa garis
    if len(calon) >= 3:
        median_tebal = float(np.median([c[3] for c in calon]))
        sisa = [c for c in calon if c[3] >= 0.78 * median_tebal]
        if len(sisa) < len(calon):
            peringatan.append(f"{len(calon) - len(sisa)} gumpalan kecil diabaikan (kemungkinan huruf label "
                              "yang menimpa garis).")
        calon = sisa
    if len(calon) > 150:
        peringatan.append(f"Terdeteksi {len(calon)} calon titik; hanya 150 terbesar yang dipakai.")
        calon = sorted(calon, key=lambda c: -c[2])[:150]

    # sisi: ruas lurus antar-titik yang (hampir) seluruhnya tinta
    toleransi = cv2.dilate(tinta, cv2.getStructuringElement(
        cv2.MORPH_ELLIPSE, (int(2 * w_garis) | 1, int(2 * w_garis) | 1)))
    H, Wd = tinta.shape
    sisi_idx = []
    m = len(calon)
    for i in range(m):
        xi, yi, ri, _ = calon[i]
        for j in range(i + 1, m):
            xj, yj, rj, _ = calon[j]
            panjang = float(np.hypot(xj - xi, yj - yi))
            bebas = panjang - 1.15 * (ri + rj)
            if bebas < 2:
                continue
            ux, uy = (xj - xi) / panjang, (yj - yi) / panjang
            t = np.linspace(1.15 * ri, panjang - 1.15 * rj, max(8, int(bebas / 2)))
            px = np.clip(np.round(xi + ux * t).astype(int), 0, Wd - 1)
            py = np.clip(np.round(yi + uy * t).astype(int), 0, H - 1)
            if toleransi[py, px].mean() / 255 < 0.92:
                continue
            # ruas yang melewati titik lain bukan satu sisi
            lewat = False
            for k in range(m):
                if k in (i, j):
                    continue
                xk, yk, rk, _ = calon[k]
                s = (xk - xi) * ux + (yk - yi) * uy
                if 0 < s < panjang and abs((xk - xi) * uy - (yk - yi) * ux) < rk + 0.5 * w_garis:
                    lewat = True
                    break
            if not lewat:
                sisi_idx.append((i, j))

    # buang gumpalan kecil tanpa sisi (biasanya huruf/angka berlubang pada label)
    derajat = [0] * m
    for i, j in sisi_idx:
        derajat[i] += 1
        derajat[j] += 1
    tebal_tipikal = np.median([calon[k][3] for k in range(m) if derajat[k] > 0]) if any(derajat) else None
    simpan = [k for k in range(m)
              if derajat[k] > 0 or tebal_tipikal is None or calon[k][3] >= 0.85 * tebal_tipikal]
    dibuang = m - len(simpan)
    if dibuang:
        peringatan.append(f"{dibuang} gumpalan kecil tanpa sisi diabaikan (kemungkinan huruf label).")

    # urutkan titik: atas ke bawah, kiri ke kanan; beri nama v1, v2, ...
    simpan.sort(key=lambda k: (round(calon[k][1] / (3 * w_garis + 1)), calon[k][0]))
    nomor = {k: i + 1 for i, k in enumerate(simpan)}
    xs = [calon[k][0] for k in simpan]
    ys = [calon[k][1] for k in simpan]
    lebar, tinggi = max(xs) - min(xs), max(ys) - min(ys)
    pilihan = [s for s in ((LEBAR_KANVAS - 2 * TEPI) / lebar if lebar > 1 else None,
                           (TINGGI_KANVAS - 2 * TEPI) / tinggi if tinggi > 1 else None) if s]
    skala = min(pilihan) if pilihan else 1.0
    cx, cy = (max(xs) + min(xs)) / 2, (max(ys) + min(ys)) / 2
    titik = [{"nama": f"v{nomor[k]}",
              "x": round(LEBAR_KANVAS / 2 + (calon[k][0] - cx) * skala, 1),
              "y": round(TINGGI_KANVAS / 2 + (calon[k][1] - cy) * skala, 1)} for k in simpan]
    sisi = [[f"v{nomor[i]}", f"v{nomor[j]}"] for i, j in sisi_idx if i in nomor and j in nomor]
    return HasilDeteksi(titik=titik, sisi=sisi, tebal_garis=w_garis, peringatan=peringatan)
