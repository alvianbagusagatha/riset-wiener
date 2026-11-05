"""Antarmuka baris perintah program riset indeks Wiener.

Contoh:
    python wiener.py graf --keluarga CL --n 7
    python wiener.py graf --kustom sisi.txt
    python wiener.py graf --kustom "x1-x2, x2-x3, x3-x1"
    python wiener.py pola --keluarga CL --dari 3 --sampai 12
    python wiener.py keluarga
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

# agar karakter seperti τ, ≥, ₁ tampil benar di konsol Windows
for _aliran in (sys.stdout, sys.stderr):
    try:
        _aliran.reconfigure(encoding="utf-8")
    except (AttributeError, ValueError):
        pass

from wiener.analisis import BATAS_ENUMERASI_BAWAAN, analisis_graf, format_angka  # noqa: E402
from wiener.enumerasi import info_numba  # noqa: E402
from wiener.graf import KELUARGA, baca_berkas_kustom, baca_graf_kustom, graf_keluarga  # noqa: E402
from wiener.pola import CATATAN_BUKTI, KOLOM_POLA, analisis_pola  # noqa: E402
from wiener.simpan import simpan_hasil_graf, simpan_hasil_pola  # noqa: E402

GARIS = "─" * 64


def _cetak_tabel(header, isi):
    lebar = [max(len(str(x)) for x in kol) for kol in zip(header, *isi)] if isi else [len(h) for h in header]
    print("  ".join(str(h).rjust(w) for h, w in zip(header, lebar)))
    print("  ".join("─" * w for w in lebar))
    for b in isi:
        print("  ".join(str(x).rjust(w) for x, w in zip(b, lebar)))


def perintah_graf(arg) -> int:
    if arg.kustom:
        jalur = Path(arg.kustom)
        G = baca_berkas_kustom(jalur) if jalur.suffix.lower() == ".txt" or jalur.exists() \
            else baca_graf_kustom(arg.kustom)
    else:
        if arg.n is None:
            raise ValueError("Untuk --keluarga, nilai --n wajib diisi.")
        G = graf_keluarga(arg.keluarga, arg.n)
    for p in G.peringatan:
        print(f"Peringatan: {p}")

    print(GARIS)
    print(f"Graf {G.nama}   ({info_numba()})")
    print(GARIS)
    h = analisis_graf(G, batas=arg.batas, progres=not arg.tanpa_progres)
    d = h.distribusi
    print(f"|V| = {G.banyak_titik}, |E| = {G.banyak_sisi}")
    print("V(G) = {" + ", ".join(G.titik) + "}")
    if G.banyak_sisi <= 60:
        print("E(G) = {" + ", ".join(G.nama_sisi(s) for s in G.sisi) + "}")
    sebaran_derajat = {}
    for t, dg in zip(G.titik, h.derajat):
        sebaran_derajat.setdefault(dg, []).append(t)
    for dg, ts in sorted(sebaran_derajat.items()):
        print(f"Derajat {dg}: {len(ts)} titik")
    print()
    print("Distribusi jarak G:")
    _cetak_tabel(["t", "N_t", "t·N_t"], [list(b) for b in d.baris_tabel()])
    print(f"Σ N_t = {d.total_pasangan}  (C(|V|,2) = {d.pasangan_seharusnya})")
    if d.terhubung:
        print(f"W({G.nama}) = {d.W},  diameter = {d.diameter}")
    else:
        print("Graf tidak terhubung: W tidak terdefinisi.")
    print()
    print(f"τ({G.nama}) = {format_angka(h.tau)}  (Teorema Matriks-Pohon, eksak)")
    e = h.enumerasi
    if e is None:
        print(h.catatan_enumerasi)
    else:
        print(f"Enumerasi: {format_angka(e.banyak)} pohon dalam {e.waktu:.2f} detik "
              f"({'cocok' if e.banyak == h.tau else 'TIDAK cocok'} dengan τ)")
        print(f"W minimum = {e.w_min}  ({format_angka(e.banyak_min)} pohon)")
        print(f"W maksimum = {e.w_maks}  ({format_angka(e.banyak_maks)} pohon)")
        if len(e.sebaran) <= 40:
            print("Sebaran W spanning tree:")
            _cetak_tabel(["W", "banyak pohon"], [[w, format_angka(c)] for w, c in e.sebaran.items()])
        else:
            print(f"Sebaran W: {len(e.sebaran)} nilai berbeda (lihat Excel).")
        print("Contoh pohon minimum: " + ", ".join(G.nama_sisi(s) for s in h.contoh_min.sisi))
        print("Contoh pohon maksimum: " + ", ".join(G.nama_sisi(s) for s in h.contoh_maks.sisi))
    if not arg.tanpa_simpan:
        berkas = simpan_hasil_graf(h, akar=arg.keluaran, gambar=not arg.tanpa_gambar)
        folder = berkas["excel"][0].parent
        print()
        print(f"Keluaran disimpan di: {folder}")
        for jenis, daftar in berkas.items():
            for b in daftar:
                print(f"  [{jenis}] {b.name}")
    return 0


def perintah_pola(arg) -> int:
    print(GARIS)
    print(f"Pola keluarga {arg.keluarga}, n = {arg.dari}..{arg.sampai}   ({info_numba()})")
    print(GARIS)
    hp = analisis_pola(arg.keluarga, arg.dari, arg.sampai, batas=arg.batas, tambahan=arg.tambahan,
                       progres=not arg.tanpa_progres)
    header = ["n"] + [k.judul for k in KOLOM_POLA]
    isi = [[r["n"]] + [format_angka(r[k.kunci]) if r.get(k.kunci) is not None else "-" for k in KOLOM_POLA]
           for r in hp.baris]
    print()
    _cetak_tabel(header, isi)
    for c in hp.catatan:
        print("Catatan:", c)
    print()
    print("Rumus hasil pencarian otomatis:")
    for r in hp.rumus:
        if not r.ditemukan:
            print(f"• {r.kolom.judul}: tidak ditemukan polinom berderajat ≤ 4 "
                  "(juga setelah dipisah paritas dan mod 4).")
            continue
        print(f"• {r.kolom.judul}:")
        for pt in r.potongan:
            kelas = f"{pt.label_kelas}, " if pt.modulus > 1 else ""
            faktor = f"  = {pt.teks_faktor}" if pt.teks_faktor else ""
            kecuali = f"; pengecualian n = {', '.join(map(str, pt.pengecualian))}" if pt.pengecualian else ""
            print(f"    {pt.teks}{faktor}   [{kelas}n ≥ {pt.n0}{kecuali}; "
                  f"interpolasi {len(pt.n_interpolasi)} titik, cocok pada {len(pt.n_verifikasi)} titik lain "
                  f"s.d. n = {pt.n_verifikasi[-1]}]")
    print()
    print("Catatan:", CATATAN_BUKTI)
    if not arg.tanpa_simpan:
        berkas = simpan_hasil_pola(hp, akar=arg.keluaran)
        print()
        print(f"Keluaran disimpan di: {berkas['excel'][0].parent}")
        for jenis, daftar in berkas.items():
            for b in daftar:
                print(f"  [{jenis}] {b.name}")
    return 0


def perintah_keluarga(_arg) -> int:
    print("Keluarga graf yang tersedia:")
    for kode, info in KELUARGA.items():
        print(f"  {info.kode:<4} {info.nama_lengkap}  (n ≥ {info.n_min})")
    return 0


def buat_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="wiener.py",
        description="Riset indeks Wiener pada graf dan spanning tree-nya.")
    sub = p.add_subparsers(dest="perintah", required=True, metavar="PERINTAH")

    def opsi_umum(sp):
        sp.add_argument("--batas", type=int, default=BATAS_ENUMERASI_BAWAAN,
                        help="opsional: lewati enumerasi jika τ melebihi angka ini (bawaan: tanpa batas)")
        sp.add_argument("--keluaran", default="hasil", help="folder akar keluaran (bawaan: hasil)")
        sp.add_argument("--tanpa-simpan", action="store_true", help="jangan simpan berkas keluaran")
        sp.add_argument("--tanpa-progres", action="store_true", help="sembunyikan bilah progres")

    g = sub.add_parser("graf", help="analisis satu graf")
    sumber = g.add_mutually_exclusive_group(required=True)
    sumber.add_argument("--keluarga", help="kode keluarga: " + ", ".join(KELUARGA))
    sumber.add_argument("--kustom", help="berkas .txt berisi daftar sisi, atau teks seperti \"x1-x2, x2-x3\"")
    g.add_argument("--n", type=int, help="parameter n keluarga graf")
    g.add_argument("--tanpa-gambar", action="store_true", help="jangan buat gambar PNG/PDF")
    opsi_umum(g)
    g.set_defaults(fungsi=perintah_graf)

    q = sub.add_parser("pola", help="tabel pola dan pencarian rumus untuk rentang n")
    q.add_argument("--keluarga", required=True, help="kode keluarga: " + ", ".join(KELUARGA))
    q.add_argument("--dari", type=int, default=3)
    q.add_argument("--sampai", type=int, default=10)
    q.add_argument("--tambahan", type=int, default=6,
                   help="banyak n tambahan untuk verifikasi kolom |V|, |E|, W(G), τ (bawaan 6)")
    opsi_umum(q)
    q.set_defaults(fungsi=perintah_pola)

    k = sub.add_parser("keluarga", help="tampilkan daftar keluarga graf")
    k.set_defaults(fungsi=perintah_keluarga)
    return p


def main(argv=None) -> int:
    arg = buat_parser().parse_args(argv)
    try:
        return arg.fungsi(arg)
    except ValueError as e:
        print(f"Kesalahan: {e}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
