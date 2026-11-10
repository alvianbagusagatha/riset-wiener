"""Keluaran Excel (.xlsx) dengan openpyxl."""

from __future__ import annotations

from pathlib import Path

from openpyxl import Workbook
from openpyxl.styles import Alignment, Font
from openpyxl.utils import get_column_letter

from .analisis import HasilGraf, InfoPohon
from .pola import CATATAN_BUKTI, KOLOM_POLA, HasilPola

TEBAL = Font(bold=True)
KANAN = Alignment(horizontal="right")
KIRI_BUNGKUS = Alignment(horizontal="left", vertical="top", wrap_text=True)


def _sel(nilai):
    """Bilangan sangat besar ditulis sebagai teks agar tidak kehilangan ketelitian di Excel."""
    if isinstance(nilai, int) and abs(nilai) >= 10 ** 15:
        return str(nilai)
    return nilai


class _Penulis:
    def __init__(self, ws):
        self.ws = ws
        self.baris = 1
        self.lebar: dict[int, int] = {}

    def tulis(self, nilai: list, tebal=False, angka_kanan=True):
        for k, v in enumerate(nilai, start=1):
            c = self.ws.cell(row=self.baris, column=k, value=_sel(v))
            if tebal:
                c.font = TEBAL
            if isinstance(v, (int, float)) and not isinstance(v, bool) and angka_kanan:
                c.alignment = KANAN
            elif isinstance(v, str) and len(v) > 60:
                c.alignment = KIRI_BUNGKUS
            panjang = min(len(str(v)) if v is not None else 0, 80)
            self.lebar[k] = max(self.lebar.get(k, 8), panjang + 2)
        self.baris += 1

    def info(self, label: str, nilai):
        c = self.ws.cell(row=self.baris, column=1, value=label)
        c.font = TEBAL
        c2 = self.ws.cell(row=self.baris, column=2, value=_sel(nilai))
        if isinstance(nilai, (int, float)):
            c2.alignment = KANAN
        else:
            c2.alignment = KIRI_BUNGKUS
        self.lebar[1] = max(self.lebar.get(1, 8), len(label) + 2)
        self.lebar[2] = max(self.lebar.get(2, 8), min(len(str(nilai)), 80) + 2)
        self.baris += 1

    def kosong(self, k=1):
        self.baris += k

    def tabel(self, header: list[str], isi: list[list]):
        self.tulis(header, tebal=True)
        for b in isi:
            self.tulis(b)

    def rapikan(self):
        for k, w in self.lebar.items():
            self.ws.column_dimensions[get_column_letter(k)].width = w


def _tulis_distribusi(p: _Penulis, dist, judul_W: str):
    p.tabel(["t", "N_t", "t·N_t"], [list(b) for b in dist.baris_tabel()])
    p.tulis(["Total", dist.total_pasangan, dist.W if dist.W is not None else "-"], tebal=True)
    p.kosong()
    p.info("Total pasangan Σ N_t", dist.total_pasangan)
    p.info("C(|V|, 2)", dist.pasangan_seharusnya)
    p.info("Cocok", "ya" if dist.total_pasangan == dist.pasangan_seharusnya else "TIDAK")
    p.info(judul_W, dist.W if dist.W is not None else "tidak terdefinisi (graf tidak terhubung)")
    p.info("Diameter", dist.diameter if dist.diameter is not None else "-")
    if dist.pasangan is not None:
        p.kosong()
        p.tabel(["t", "Banyak", "Pasangan titik berjarak t"],
                [[t, len(ps), ", ".join(f"{a}{b}" for a, b in ps)] for t, ps in dist.pasangan.items()])


def _tulis_contoh(ws, h: HasilGraf, pohon: InfoPohon | None, jenis: str):
    p = _Penulis(ws)
    if pohon is None:
        p.info("Keterangan", h.catatan_enumerasi or "Enumerasi tidak dilakukan.")
        p.rapikan()
        return
    G = h.graf
    e = h.enumerasi
    p.info("Graf", G.nama)
    if e is None:
        p.info(f"W {jenis} yang ditemukan (mode cepat)", pohon.W)
        p.info("Keterangan", h.catatan_enumerasi)
    else:
        p.info(f"W {jenis}", pohon.W)
        p.info(f"Banyak pohon dengan W = {pohon.W}",
               e.banyak_min if jenis == "minimum" else e.banyak_maks)
    if h.daftar is not None:
        p.info("Nomor pada daftar", pohon.nomor if pohon.nomor else "tidak termasuk daftar")
    p.info("Sisi pohon", ", ".join(G.nama_sisi(s) for s in pohon.sisi))
    dibuang = sorted(set(G.sisi) - set(pohon.sisi))
    p.info("Sisi yang dibuang", ", ".join(G.nama_sisi(s) for s in dibuang))
    p.kosong()
    _tulis_distribusi(p, pohon.distribusi, "W(T) = Σ t·N_t")
    p.rapikan()


def simpan_excel_graf(h: HasilGraf, jalur: Path) -> Path:
    G = h.graf
    wb = Workbook()

    ws = wb.active
    ws.title = "Graf"
    p = _Penulis(ws)
    p.info("Nama graf", G.nama)
    p.info("|V|", G.banyak_titik)
    p.info("|E|", G.banyak_sisi)
    p.info("V(G)", "{" + ", ".join(G.titik) + "}")
    p.info("E(G)", "{" + ", ".join(G.nama_sisi(s) for s in G.sisi) + "}")
    p.info("W(G)", h.distribusi.W if h.distribusi.W is not None else "graf tidak terhubung")
    p.info("τ(G) (Teorema Matriks-Pohon)", h.tau)
    if G.peringatan:
        p.info("Peringatan", "; ".join(G.peringatan))
    p.kosong()
    p.tabel(["Titik", "Derajat"], [[t, d] for t, d in zip(G.titik, h.derajat)])
    p.tulis(["Jumlah derajat", sum(h.derajat)], tebal=True)
    p.rapikan()

    p = _Penulis(wb.create_sheet("Distribusi jarak"))
    _tulis_distribusi(p, h.distribusi, "W(G) = Σ t·N_t")
    p.rapikan()

    p = _Penulis(wb.create_sheet("Sebaran W spanning tree"))
    p.info("τ(G) (Teorema Matriks-Pohon)", h.tau)
    e = h.enumerasi
    if e is None:
        p.info("Keterangan", h.catatan_enumerasi)
    else:
        p.info("Banyak pohon hasil enumerasi", e.banyak)
        p.info("Sama dengan τ", "ya" if e.banyak == h.tau else "TIDAK")
        p.info("W minimum", e.w_min)
        p.info("Banyak pohon minimum", e.banyak_min)
        p.info("W maksimum", e.w_maks)
        p.info("Banyak pohon maksimum", e.banyak_maks)
        p.info("Banyak nilai W berbeda", len(e.sebaran))
        p.info("Waktu enumerasi (detik)", round(e.waktu, 3))
        p.info("Metode", e.metode)
        p.kosong()
        p.tabel(["W", "Banyak pohon"], [[w, c] for w, c in e.sebaran.items()])
        p.tulis(["Total", e.banyak], tebal=True)
    p.rapikan()

    _tulis_contoh(wb.create_sheet("Contoh minimum"), h, h.contoh_min, "minimum")
    _tulis_contoh(wb.create_sheet("Contoh maksimum"), h, h.contoh_maks, "maksimum")

    if h.daftar is not None:
        p = _Penulis(wb.create_sheet("Daftar spanning tree" if h.daftar_lengkap else "W terkecil"))
        if not h.daftar_lengkap:
            p.info("Keterangan", h.keterangan_daftar)
            p.kosong()
        D = max((max(t.distribusi.N) for t in h.daftar if t.distribusi.N), default=1)
        header = ["No", "Sisi"] + [f"N_{t}" for t in range(1, D + 1)] + ["W"]
        isi = []
        for t in h.daftar:
            isi.append([t.nomor, ", ".join(G.nama_sisi(s) for s in t.sisi)]
                       + [t.distribusi.N.get(k, 0) for k in range(1, D + 1)] + [t.W])
        p.tabel(header, isi)
        p.rapikan()

    jalur.parent.mkdir(parents=True, exist_ok=True)
    wb.save(jalur)
    return jalur


def simpan_excel_pola(hp: HasilPola, jalur: Path) -> Path:
    wb = Workbook()
    ws = wb.active
    ws.title = "Pola n"
    p = _Penulis(ws)
    p.info("Keluarga", hp.nama_lengkap)
    p.info("Rentang", f"n = {hp.dari} sampai {hp.sampai}")
    p.kosong()
    header = ["n"] + [k.judul for k in KOLOM_POLA]
    p.tabel(header, [[r["n"]] + [r.get(k.kunci) if r.get(k.kunci) is not None else "-"
                                 for k in KOLOM_POLA] for r in hp.baris])
    if hp.baris_tambahan:
        p.kosong()
        p.tulis(["Titik verifikasi tambahan (kolom tanpa enumerasi)"], tebal=True)
        murah = [k for k in KOLOM_POLA if k.murah]
        p.tabel(["n"] + [k.judul for k in murah],
                [[r["n"]] + [r[k.kunci] for k in murah] for r in hp.baris_tambahan])
    for c in hp.catatan:
        p.info("Catatan", c)
    p.rapikan()

    p = _Penulis(wb.create_sheet("Rumus"))
    p.tabel(["Kolom", "Ditemukan", "Pembagian", "Kelas", "Rumus", "Bentuk terfaktor",
             "Berlaku untuk", "Pengecualian", "Interpolasi pada n", "Diverifikasi pada n"], [])
    for r in hp.rumus:
        if not r.ditemukan:
            p.tulis([r.kolom.judul, "tidak", "-", "-", r.pesan, "", "", "", "", ""])
            continue
        pembagian = {1: "satu rumus", 2: "paritas n", 4: "n mod 4"}[r.modulus]
        for pt in r.potongan:
            p.tulis([r.kolom.judul, "ya", pembagian, pt.label_kelas, pt.teks, pt.teks_faktor or "",
                     f"n ≥ {pt.n0}", ", ".join(map(str, pt.pengecualian)) or "-",
                     ", ".join(map(str, pt.n_interpolasi)), ", ".join(map(str, pt.n_verifikasi))],
                    angka_kanan=False)
    p.kosong()
    p.info("Catatan", CATATAN_BUKTI)
    p.rapikan()

    p = _Penulis(wb.create_sheet("Selisih berhingga"))
    for r in hp.rumus:
        p.tulis([f"{r.kolom.judul}" + ("" if r.ditemukan else " (tidak ditemukan polinom)")], tebal=True)
        blok = [(pt.label_kelas, pt.selisih_n, pt.selisih) for pt in r.potongan] if r.ditemukan \
            else [("semua n", r.selisih_n, r.selisih)]
        for label, ns, tabel in blok:
            p.tulis([label, "n"] + ns, tebal=True)
            for tingkat, isi in enumerate(tabel):
                nama = "nilai" if tingkat == 0 else f"selisih {tingkat}"
                p.tulis(["", nama] + isi)
        p.kosong()
    p.rapikan()

    jalur.parent.mkdir(parents=True, exist_ok=True)
    wb.save(jalur)
    return jalur
