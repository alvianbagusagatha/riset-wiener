"""Tabel pola untuk rentang n dan pencarian rumus polinom secara otomatis.

Untuk setiap kolom dicari polinom p(n) berderajat ≤ 4 dengan interpolasi pecahan eksak
(fractions.Fraction). Polinom diinterpolasi dari d+1 titik data pertama, lalu WAJIB
cocok pada semua titik data sisanya (titik verifikasi, minimal satu). Urutan percobaan:
  1. satu rumus untuk semua n,
  2. dipisah menurut paritas n,
  3. dipisah menurut n mod 4.
Pengecualian di n kecil diizinkan (dilaporkan sebagai "berlaku untuk n ≥ n0").

Kolom yang murah dihitung (|V|, |E|, W(G), τ) juga dihitung untuk beberapa n tambahan
di atas rentang agar verifikasi lebih kuat.

CATATAN: rumus yang ditemukan adalah dugaan hasil komputasi dan masih perlu dibuktikan
secara matematis.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from fractions import Fraction

from .analisis import BATAS_ENUMERASI_BAWAAN
from .enumerasi import enumerasi_spanning_tree
from .graf import KELUARGA, graf_keluarga
from .jarak import distribusi_jarak
from .matriks_pohon import banyak_spanning_tree

CATATAN_BUKTI = ("Rumus di atas diperoleh dari komputasi (interpolasi dan verifikasi pada data), "
                 "sehingga masih berstatus dugaan dan perlu dibuktikan secara matematis.")


@dataclass
class Kolom:
    kunci: str
    judul: str          # judul tabel
    tex: str            # simbol LaTeX; {g} diganti nama keluarga, mis. CL_n
    murah: bool         # dapat dihitung untuk n tambahan tanpa enumerasi


KOLOM_POLA = [
    Kolom("V", "|V|", r"|V({g})|", True),
    Kolom("E", "|E|", r"|E({g})|", True),
    Kolom("W", "W(G)", r"W({g})", True),
    Kolom("tau", "τ", r"\tau({g})", True),
    Kolom("wmin", "W ST minimum", r"\min_{{T}} W(T)", False),
    Kolom("wmaks", "W ST maksimum", r"\max_{{T}} W(T)", False),
    Kolom("nmin", "Banyak pohon minimum", r"N_{{\min}}({g})", False),
    Kolom("nmaks", "Banyak pohon maksimum", r"N_{{\max}}({g})", False),
]


# ---------------------------------------------------------------------------
# Polinom pecahan eksak
# ---------------------------------------------------------------------------

def interpolasi(titik: list[tuple[int, int]]) -> list[Fraction]:
    """Koefisien c0..cd polinom yang melalui d+1 titik (Vandermonde, pecahan eksak)."""
    d = len(titik) - 1
    A = [[Fraction(n) ** j for j in range(d + 1)] + [Fraction(y)] for n, y in titik]
    for kol in range(d + 1):
        piv = next(r for r in range(kol, d + 1) if A[r][kol] != 0)
        A[kol], A[piv] = A[piv], A[kol]
        for r in range(d + 1):
            if r != kol and A[r][kol] != 0:
                f = A[r][kol] / A[kol][kol]
                A[r] = [a - f * b for a, b in zip(A[r], A[kol])]
    koef = [A[i][d + 1] / A[i][i] for i in range(d + 1)]
    while len(koef) > 1 and koef[-1] == 0:
        koef.pop()
    return koef


def nilai_polinom(koef: list[Fraction], n: int) -> Fraction:
    hasil = Fraction(0)
    for c in reversed(koef):
        hasil = hasil * n + c
    return hasil


_SUPER = {2: "²", 3: "³", 4: "⁴"}


def _suku(a: int, k: int, var: str, tex: bool) -> str:
    """Suku a·n^k tanpa tanda (nilai mutlak)."""
    a = abs(a)
    if k == 0:
        return str(a)
    pangkat = "" if k == 1 else (f"^{{{k}}}" if tex else _SUPER.get(k, f"^{k}"))
    koef = "" if a == 1 else str(a)
    return f"{koef}{var}{pangkat}"


def _gabung(a: list[int], var: str, tex: bool) -> str:
    minus = " - " if tex else " − "
    potong = []
    for k in range(len(a) - 1, -1, -1):
        if a[k] == 0:
            continue
        s = _suku(a[k], k, var, tex)
        if not potong:
            potong.append(("-" if tex else "−") + s if a[k] < 0 else s)
        else:
            potong.append((minus if a[k] < 0 else " + ") + s)
    return "".join(potong) or "0"


def _bilangan_bulat(koef: list[Fraction]) -> tuple[list[int], int]:
    D = 1
    for c in koef:
        D = D * c.denominator // math.gcd(D, c.denominator)
    return [int(c * D) for c in koef], D


def format_polinom(koef: list[Fraction], var: str = "n", tex: bool = False) -> str:
    a, D = _bilangan_bulat(koef)
    isi = _gabung(a, var, tex)
    if D == 1:
        return isi
    if tex:
        return rf"\frac{{{isi}}}{{{D}}}"
    banyak_suku = sum(1 for x in a if x != 0)
    return f"({isi})/{D}" if banyak_suku > 1 else f"{isi}/{D}"


def format_terfaktor(koef: list[Fraction], var: str = "n", tex: bool = False) -> str | None:
    """Bentuk dengan faktor n^j dan FPB koefisien dikeluarkan, mis. n(4n² − 1)/3.
    None jika tidak ada yang bisa difaktorkan."""
    a, D = _bilangan_bulat(koef)
    if all(x == 0 for x in a):
        return None
    j = next(k for k, x in enumerate(a) if x != 0)
    g = 0
    for x in a:
        g = math.gcd(g, x)
    sisa = [x // g for x in a[j:]]
    if sum(1 for x in sisa if x != 0) <= 1 or (j == 0 and g == 1):
        return None
    pecahan = Fraction(g, D)
    luar = "" if j == 0 else (var if j == 1 else (f"{var}^{{{j}}}" if tex else f"{var}{_SUPER.get(j, '^' + str(j))}"))
    dalam = _gabung(sisa, var, tex)
    pembilang_k = pecahan.numerator
    k_str = "" if pembilang_k == 1 else str(pembilang_k)
    badan = f"{k_str}{luar}({dalam})"
    if pecahan.denominator == 1:
        return badan
    if tex:
        return rf"\frac{{{badan}}}{{{pecahan.denominator}}}"
    return f"{badan}/{pecahan.denominator}"


def tabel_selisih(nilai: list[int], tingkat_maks: int = 5) -> list[list[int]]:
    """[nilai, Δ¹, Δ², ...] sampai selisih nol semua atau tingkat_maks."""
    baris = [list(nilai)]
    while len(baris) <= tingkat_maks and len(baris[-1]) > 1:
        s = [b - a for a, b in zip(baris[-1], baris[-1][1:])]
        baris.append(s)
        if all(x == 0 for x in s):
            break
    return baris


# ---------------------------------------------------------------------------
# Pencarian rumus
# ---------------------------------------------------------------------------

@dataclass
class Potongan:
    modulus: int
    sisa: int
    label_kelas: str
    koef: list[Fraction]
    n0: int
    pengecualian: list[int]
    n_interpolasi: list[int]
    n_verifikasi: list[int]
    teks: str
    teks_faktor: str | None
    tex: str
    tex_faktor: str | None
    selisih_n: list[int]
    selisih: list[list[int]]

    @property
    def derajat(self) -> int:
        return len(self.koef) - 1


@dataclass
class HasilRumus:
    kolom: Kolom
    ditemukan: bool
    modulus: int | None
    potongan: list[Potongan]
    pesan: str
    selisih_n: list[int] = field(default_factory=list)       # untuk kolom tanpa rumus
    selisih: list[list[int]] = field(default_factory=list)


def _label_kelas(modulus: int, sisa: int) -> str:
    if modulus == 1:
        return "semua n"
    if modulus == 2:
        return "n genap" if sisa == 0 else "n ganjil"
    return f"n ≡ {sisa} (mod {modulus})"


def _cocokkan_kelas(titik: list[tuple[int, int]], derajat_maks: int, pengecualian_maks: int):
    p = len(titik)
    for s in range(0, min(pengecualian_maks, p - 2) + 1):
        data = titik[s:]
        for d in range(0, min(derajat_maks, len(data) - 2) + 1):
            koef = interpolasi(data[:d + 1])
            if len(koef) - 1 < d:
                continue      # sudah tertangkap pada derajat lebih rendah
            if all(nilai_polinom(koef, n) == y for n, y in data[d + 1:]):
                return s, d, koef
    return None


def cari_rumus(data: dict[int, int], kolom: Kolom, derajat_maks: int = 4,
               pengecualian_maks: int = 3) -> HasilRumus:
    titik = sorted((n, int(y)) for n, y in data.items() if y is not None)
    for modulus in (1, 2, 4):
        kelas = {r: [(n, y) for n, y in titik if n % modulus == r] for r in range(modulus)}
        if any(len(v) < 2 for v in kelas.values()):
            break
        potongan = []
        for r, t in kelas.items():
            hasil = _cocokkan_kelas(t, derajat_maks, pengecualian_maks)
            if hasil is None:
                potongan = None
                break
            s, d, koef = hasil
            dipakai = t[s:]
            nilai = [y for _, y in dipakai]
            potongan.append(Potongan(
                modulus=modulus, sisa=r, label_kelas=_label_kelas(modulus, r), koef=koef,
                n0=dipakai[0][0], pengecualian=[n for n, _ in t[:s]],
                n_interpolasi=[n for n, _ in dipakai[:d + 1]],
                n_verifikasi=[n for n, _ in dipakai[d + 1:]],
                teks=format_polinom(koef), teks_faktor=format_terfaktor(koef),
                tex=format_polinom(koef, tex=True), tex_faktor=format_terfaktor(koef, tex=True),
                selisih_n=[n for n, _ in dipakai],
                selisih=tabel_selisih(nilai, tingkat_maks=min(len(koef), 5) if len(koef) > 0 else 1)))
        if potongan is not None:
            bagian = []
            for pt in potongan:
                syarat = pt.label_kelas if modulus > 1 else ""
                syarat = (syarat + ", " if syarat else "") + f"n ≥ {pt.n0}"
                bagian.append(f"{pt.teks}  ({syarat})")
            pesan = f"{kolom.judul} = " + ";  ".join(bagian)
            return HasilRumus(kolom, True, modulus, potongan, pesan)
    nilai = [y for _, y in titik]
    pesan = (f"{kolom.judul}: tidak ditemukan polinom berderajat ≤ {derajat_maks} "
             "(juga setelah dipisah menurut paritas dan n mod 4). "
             "Kemungkinan pertumbuhannya bukan polinom, misalnya eksponensial.")
    return HasilRumus(kolom, False, None, [], pesan, selisih_n=[n for n, _ in titik],
                      selisih=tabel_selisih(nilai, tingkat_maks=5))


# ---------------------------------------------------------------------------
# Tabel pola untuk satu keluarga
# ---------------------------------------------------------------------------

@dataclass
class HasilPola:
    kode: str
    nama_lengkap: str
    tex: str
    dari: int
    sampai: int
    baris: list[dict]             # satu dict per n (dari..sampai), semua kolom
    baris_tambahan: list[dict]    # n di atas rentang, hanya kolom murah
    rumus: list[HasilRumus]
    catatan: list[str]


def _kolom_murah(G) -> dict:
    dist = distribusi_jarak(G, dengan_pasangan=False)
    return {"V": G.banyak_titik, "E": G.banyak_sisi, "W": dist.W,
            "tau": banyak_spanning_tree(G)}


def analisis_pola_fungsi(kode: str, nama_lengkap: str, tex: str, buat, n_min: int, dari: int,
                         sampai: int, batas: int | None = BATAS_ENUMERASI_BAWAAN, tambahan: int = 6,
                         progres: bool = True, callback=None, callback_pohon=None,
                         derajat_maks: int = 4, pengecualian_maks: int = 3) -> HasilPola:
    """Tabel pola dan pencarian rumus untuk keluarga apa pun: buat(n) -> Graf."""
    dari = max(dari, n_min)
    if sampai < dari:
        raise ValueError("Nilai 'sampai' harus ≥ 'dari'.")
    baris, catatan = [], []
    for n in range(dari, sampai + 1):
        G = buat(n)
        r = {"n": n, **_kolom_murah(G)}
        if r["tau"] == 0:
            r.update(wmin=None, wmaks=None, nmin=None, nmaks=None, waktu=None)
            catatan.append(f"n = {n}: graf tidak terhubung (τ = 0).")
        elif batas is None or r["tau"] <= batas:
            cb = (lambda s_, t_, n_=n: callback_pohon(n_, s_, t_)) if callback_pohon else None
            e = enumerasi_spanning_tree(G, tau=r["tau"], progres=progres, callback=cb)
            r.update(wmin=e.w_min, wmaks=e.w_maks, nmin=e.banyak_min, nmaks=e.banyak_maks,
                     waktu=e.waktu)
        else:
            r.update(wmin=None, wmaks=None, nmin=None, nmaks=None, waktu=None)
            catatan.append(f"n = {n}: τ melebihi batas enumerasi, kolom spanning tree dikosongkan.")
        baris.append(r)
        if callback is not None:
            callback(n, dari, sampai)
    baris_tambahan = []
    for n in range(sampai + 1, sampai + 1 + max(0, tambahan)):
        baris_tambahan.append({"n": n, **_kolom_murah(buat(n))})

    rumus = []
    for kol in KOLOM_POLA:
        data = {r["n"]: r[kol.kunci] for r in baris if r.get(kol.kunci) is not None}
        if kol.murah:
            data.update({r["n"]: r[kol.kunci] for r in baris_tambahan if r.get(kol.kunci) is not None})
        rumus.append(cari_rumus(data, kol, derajat_maks, pengecualian_maks))
    return HasilPola(kode=kode, nama_lengkap=nama_lengkap, tex=tex, dari=dari, sampai=sampai,
                     baris=baris, baris_tambahan=baris_tambahan, rumus=rumus, catatan=catatan)


def analisis_pola(kode: str, dari: int, sampai: int, batas: int | None = BATAS_ENUMERASI_BAWAAN,
                  tambahan: int = 6, progres: bool = True, callback=None, callback_pohon=None,
                  derajat_maks: int = 4, pengecualian_maks: int = 3) -> HasilPola:
    """Pola untuk keluarga bawaan (CL, L, M, ...)."""
    kunci = kode.upper().replace("_", "").replace(",", "")
    if kunci not in KELUARGA:
        raise ValueError(f"Keluarga graf '{kode}' tidak dikenal. Pilihan: {', '.join(KELUARGA)}.")
    info = KELUARGA[kunci]
    return analisis_pola_fungsi(info.kode, info.nama_lengkap, info.tex, lambda n: graf_keluarga(kunci, n),
                                info.n_min, dari, sampai, batas, tambahan, progres, callback,
                                callback_pohon, derajat_maks, pengecualian_maks)
