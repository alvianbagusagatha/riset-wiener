"""Struktur data graf, keluarga graf, dan pembaca graf kustom.

Menambah keluarga graf baru cukup dengan menulis SATU fungsi dan memberinya
dekorator ``@keluarga(...)``. Contoh:

    @keluarga("S", n_min=3, nama_lengkap="Graf matahari S_n", tex="S_n")
    def graf_matahari(n):
        titik = [f"v{i}" for i in range(1, n + 1)] + [f"u{i}" for i in range(1, n + 1)]
        sisi = [...]                      # daftar pasangan NAMA titik
        return titik, sisi, posisi_atau_None, "bebas"

Fungsi mengembalikan (titik, sisi, posisi, tata_letak):
- titik     : daftar nama titik (urutan ini dipakai di semua tabel)
- sisi      : daftar pasangan nama titik
- posisi    : dict nama -> (x, y) untuk gambar, atau None (tata letak otomatis)
- tata_letak: "lingkaran-ganda", "tangga", "lingkaran", "lintasan", "kipas",
              atau "bebas" (hanya memengaruhi letak label pada gambar)
"""

from __future__ import annotations

import math
import re
from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class Graf:
    nama: str                      # nama tampilan, mis. "CL_7"
    kode: str                      # nama folder keluaran, mis. "CL_n7"
    titik: list[str]
    sisi: list[tuple[int, int]]    # pasangan indeks titik, i < j
    posisi: dict[str, tuple[float, float]] | None = None
    tata_letak: str = "bebas"
    keluarga: str | None = None
    n: int | None = None
    nama_tex: str | None = None    # mis. "CL_{7}"
    peringatan: list[str] = field(default_factory=list)

    @property
    def banyak_titik(self) -> int:
        return len(self.titik)

    @property
    def banyak_sisi(self) -> int:
        return len(self.sisi)

    def tetangga(self) -> list[list[int]]:
        adj: list[list[int]] = [[] for _ in self.titik]
        for a, b in self.sisi:
            adj[a].append(b)
            adj[b].append(a)
        return adj

    def derajat(self) -> list[int]:
        return [len(t) for t in self.tetangga()]

    def nama_sisi(self, e: tuple[int, int]) -> str:
        return f"{self.titik[e[0]]}{self.titik[e[1]]}"

    def subgraf_sisi(self, sisi: list[tuple[int, int]]) -> "Graf":
        """Graf rentang (titik sama) dengan himpunan sisi tertentu, mis. sebuah spanning tree."""
        return Graf(nama=self.nama, kode=self.kode, titik=self.titik, sisi=list(sisi),
                    posisi=self.posisi, tata_letak=self.tata_letak,
                    keluarga=self.keluarga, n=self.n, nama_tex=self.nama_tex)


def buat_graf(nama: str, kode: str, titik: list[str], sisi_nama: list[tuple[str, str]],
              posisi=None, tata_letak="bebas", keluarga=None, n=None, nama_tex=None) -> Graf:
    indeks = {t: i for i, t in enumerate(titik)}
    if len(indeks) != len(titik):
        raise ValueError("Nama titik ganda dalam definisi graf.")
    terlihat: set[tuple[int, int]] = set()
    sisi: list[tuple[int, int]] = []
    for a, b in sisi_nama:
        if a not in indeks or b not in indeks:
            raise ValueError(f"Sisi {a}-{b} memakai titik yang tidak terdaftar.")
        i, j = sorted((indeks[a], indeks[b]))
        if i == j or (i, j) in terlihat:
            continue
        terlihat.add((i, j))
        sisi.append((i, j))
    return Graf(nama=nama, kode=kode, titik=list(titik), sisi=sisi, posisi=posisi,
                tata_letak=tata_letak, keluarga=keluarga, n=n, nama_tex=nama_tex)


# ---------------------------------------------------------------------------
# Daftar keluarga graf
# ---------------------------------------------------------------------------

@dataclass
class InfoKeluarga:
    kode: str
    fungsi: object
    n_min: int
    nama_lengkap: str
    tex: str             # nama LaTeX dengan n generik, mis. "CL_n"


KELUARGA: dict[str, InfoKeluarga] = {}


def keluarga(kode: str, n_min: int, nama_lengkap: str, tex: str):
    """Dekorator untuk mendaftarkan sebuah keluarga graf."""
    def daftar(fungsi):
        KELUARGA[kode.upper()] = InfoKeluarga(kode, fungsi, n_min, nama_lengkap, tex)
        return fungsi
    return daftar


def graf_keluarga(kode: str, n: int) -> Graf:
    kunci = kode.upper().replace("_", "").replace(",", "")
    if kunci not in KELUARGA:
        pilihan = ", ".join(KELUARGA)
        raise ValueError(f"Keluarga graf '{kode}' tidak dikenal. Pilihan: {pilihan}.")
    info = KELUARGA[kunci]
    if n < info.n_min:
        raise ValueError(f"{info.nama_lengkap} memerlukan n ≥ {info.n_min} (diberikan n = {n}).")
    titik, sisi, posisi, tata_letak = info.fungsi(n)
    nama = info.tex.replace("{1,n}", f"{{1,{n}}}").replace("_n", f"_{n}")
    nama_tampil = nama if "," in nama else nama.replace("{", "").replace("}", "")
    nama_tex = info.tex.replace("{1,n}", f"{{1,{n}}}").replace("_n", f"_{{{n}}}")
    return buat_graf(nama_tampil, f"{info.kode}_n{n}", titik, sisi, posisi, tata_letak,
                     keluarga=info.kode, n=n, nama_tex=nama_tex)


def _sudut(i: int, n: int) -> float:
    """Sudut titik ke-i (mulai 1): titik 1 di atas, lalu searah jarum jam."""
    return math.pi / 2 - 2 * math.pi * (i - 1) / n


def _lingkaran(nama: list[str], r: float, cx=0.0, cy=0.0) -> dict:
    n = len(nama)
    return {v: (cx + r * math.cos(_sudut(i, n)), cy + r * math.sin(_sudut(i, n)))
            for i, v in enumerate(nama, start=1)}


@keluarga("CL", n_min=3, nama_lengkap="Circular ladder CL_n", tex="CL_n")
def graf_circular_ladder(n: int):
    x = [f"x{i}" for i in range(1, n + 1)]
    y = [f"y{i}" for i in range(1, n + 1)]
    sisi = []
    for i in range(n):
        sisi.append((x[i], x[(i + 1) % n]))
        sisi.append((y[i], y[(i + 1) % n]))
        sisi.append((x[i], y[i]))
    posisi = {**_lingkaran(x, 1.0), **_lingkaran(y, 2.0)}
    return x + y, sisi, posisi, "lingkaran-ganda"


@keluarga("L", n_min=2, nama_lengkap="Graf tangga L_n", tex="L_n")
def graf_tangga(n: int):
    x = [f"x{i}" for i in range(1, n + 1)]
    y = [f"y{i}" for i in range(1, n + 1)]
    sisi = []
    for i in range(n):
        if i + 1 < n:
            sisi.append((x[i], x[i + 1]))
            sisi.append((y[i], y[i + 1]))
        sisi.append((x[i], y[i]))
    posisi = {**{v: (float(i), 1.0) for i, v in enumerate(x)},
              **{v: (float(i), 0.0) for i, v in enumerate(y)}}
    return x + y, sisi, posisi, "tangga"


@keluarga("M", n_min=3, nama_lengkap="Möbius ladder M_n", tex="M_n")
def graf_mobius_ladder(n: int):
    titik, sisi, _, _ = graf_tangga(n)
    sisi = sisi + [(f"x{n}", "y1"), (f"y{n}", "x1")]
    x = [f"x{i}" for i in range(1, n + 1)]
    y = [f"y{i}" for i in range(1, n + 1)]
    posisi = {**_lingkaran(x, 1.0), **_lingkaran(y, 2.0)}
    return titik, sisi, posisi, "lingkaran-ganda"


@keluarga("C", n_min=3, nama_lengkap="Siklus C_n", tex="C_n")
def graf_siklus(n: int):
    v = [f"v{i}" for i in range(1, n + 1)]
    sisi = [(v[i], v[(i + 1) % n]) for i in range(n)]
    return v, sisi, _lingkaran(v, 1.0), "lingkaran"


@keluarga("P", n_min=2, nama_lengkap="Lintasan P_n", tex="P_n")
def graf_lintasan(n: int):
    v = [f"v{i}" for i in range(1, n + 1)]
    sisi = [(v[i], v[i + 1]) for i in range(n - 1)]
    return v, sisi, {t: (float(i), 0.0) for i, t in enumerate(v)}, "lintasan"


@keluarga("K1N", n_min=1, nama_lengkap="Graf bintang K_{1,n}", tex="K_{1,n}")
def graf_bintang(n: int):
    v = [f"v{i}" for i in range(1, n + 1)]
    sisi = [("c", t) for t in v]
    return ["c"] + v, sisi, {"c": (0.0, 0.0), **_lingkaran(v, 1.0)}, "lingkaran"


@keluarga("W", n_min=3, nama_lengkap="Graf roda W_n (pusat c + siklus C_n)", tex="W_n")
def graf_roda(n: int):
    v = [f"v{i}" for i in range(1, n + 1)]
    sisi = [(v[i], v[(i + 1) % n]) for i in range(n)] + [("c", t) for t in v]
    return ["c"] + v, sisi, {"c": (0.0, 0.0), **_lingkaran(v, 1.0)}, "lingkaran"


@keluarga("F", n_min=2, nama_lengkap="Graf kipas F_n (pusat c + lintasan P_n)", tex="F_n")
def graf_kipas(n: int):
    v = [f"v{i}" for i in range(1, n + 1)]
    sisi = [(v[i], v[i + 1]) for i in range(n - 1)] + [("c", t) for t in v]
    posisi = {"c": (0.0, max(1.5, n / 3))}
    posisi.update({t: (i - (n - 1) / 2, 0.0) for i, t in enumerate(v)})
    return ["c"] + v, sisi, posisi, "kipas"


@keluarga("K", n_min=1, nama_lengkap="Graf lengkap K_n", tex="K_n")
def graf_lengkap(n: int):
    v = [f"v{i}" for i in range(1, n + 1)]
    sisi = [(v[i], v[j]) for i in range(n) for j in range(i + 1, n)]
    return v, sisi, _lingkaran(v, 1.0), "lingkaran"


# ---------------------------------------------------------------------------
# Graf kustom
# ---------------------------------------------------------------------------

def _kunci_alami(nama: str):
    return [int(b) if b.isdigit() else b for b in re.split(r"(\d+)", nama)]


def baca_graf_kustom(teks: str, nama: str = "kustom") -> Graf:
    """Membaca daftar sisi seperti "x1-x2, x2-x3, x1-y1" (pemisah koma, titik koma,
    atau baris baru; baris yang diawali # diabaikan). Sisi ganda dan gelung diabaikan
    dengan peringatan. Kesalahan format menghasilkan ValueError berbahasa Indonesia."""
    peringatan: list[str] = []
    pasangan: list[tuple[str, str]] = []
    terlihat: set[frozenset] = set()
    baris_baris = teks.replace("\r", "\n").split("\n")
    for no_baris, baris in enumerate(baris_baris, start=1):
        baris = baris.split("#", 1)[0]
        for token in re.split(r"[,;]", baris):
            token = token.strip()
            if not token:
                continue
            bagian = [b.strip() for b in re.split(r"\s*[-–—]\s*", token)]
            if len(bagian) != 2 or not bagian[0] or not bagian[1]:
                raise ValueError(
                    f"Baris {no_baris}: sisi '{token}' tidak dikenali. "
                    "Tulis setiap sisi sebagai dua nama titik yang dipisah tanda hubung, mis. x1-x2.")
            a, b = bagian
            if not re.fullmatch(r"[A-Za-z0-9_]+", a) or not re.fullmatch(r"[A-Za-z0-9_]+", b):
                raise ValueError(
                    f"Baris {no_baris}: nama titik pada '{token}' hanya boleh berisi huruf, angka, atau _.")
            if a == b:
                peringatan.append(f"Gelung {a}-{b} diabaikan.")
                continue
            kunci = frozenset((a, b))
            if kunci in terlihat:
                peringatan.append(f"Sisi ganda {a}-{b} diabaikan.")
                continue
            terlihat.add(kunci)
            pasangan.append((a, b))
    if not pasangan:
        raise ValueError("Tidak ada sisi yang valid. Contoh format: x1-x2, x2-x3, x1-y1")
    titik = sorted({t for p in pasangan for t in p}, key=_kunci_alami)
    kode = re.sub(r"[^A-Za-z0-9_]+", "_", nama).strip("_") or "kustom"
    g = buat_graf(nama, kode, titik, pasangan, None, "bebas")
    g.peringatan = peringatan
    return g


def graf_dari_gambar(nama: str, titik: list[dict], sisi: list, tata_letak: str = "bebas") -> Graf:
    """Graf dari editor gambar: titik = [{"nama", "x", "y"}] (koordinat layar, y ke bawah),
    sisi = [[nama_a, nama_b], ...]. Posisi gambar dipakai pada gambar keluaran."""
    if not titik:
        raise ValueError("Gambar masih kosong. Tambahkan titik dan sisi terlebih dahulu.")
    nama_titik = [str(t["nama"]) for t in titik]
    for t in nama_titik:
        if not re.fullmatch(r"[A-Za-z0-9_]+", t):
            raise ValueError(f"Nama titik '{t}' hanya boleh berisi huruf, angka, atau _.")
    if len(set(nama_titik)) != len(nama_titik):
        raise ValueError("Ada nama titik yang sama. Ganti salah satunya (klik dua kali pada titik).")
    posisi = {str(t["nama"]): (float(t["x"]) / 100, -float(t["y"]) / 100) for t in titik}
    pasangan = [(str(a), str(b)) for a, b in sisi]
    kode = re.sub(r"[^A-Za-z0-9_]+", "_", nama).strip("_") or "gambar"
    return buat_graf(nama, kode, nama_titik, pasangan, posisi, tata_letak)


def baca_berkas_kustom(jalur: str | Path) -> Graf:
    jalur = Path(jalur)
    if not jalur.exists():
        raise ValueError(f"Berkas '{jalur}' tidak ditemukan.")
    teks = jalur.read_text(encoding="utf-8-sig")
    return baca_graf_kustom(teks, nama=f"kustom_{jalur.stem}")
