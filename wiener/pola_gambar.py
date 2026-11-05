"""Keluarga graf G_n dari graf yang digambar — untuk graf APA PUN.

Ada dua cara membentuk G_n dari gambar:

1. Tebak dari nama titik ("indeks"). Titik bernama huruf+angka (x1, y1, x2, …) dibaca sebagai
   salinan ke-i dari blok berulang. Gambar boleh berupa dua salinan pertama (x1, y1, x2, y2)
   ATAU satu anggota utuh (mis. CL_5 dengan x1..x5, y1..y5). Program menebak aturan sisinya
   (selisih indeks) dan apakah rantainya tertutup (seperti siklus) atau terbuka (seperti
   lintasan). Titik tanpa angka (mis. c) adalah titik pusat bersama.

2. Operasi graf baku pada graf G yang digambar (nama titik bebas):
   G □ P_n, G □ C_n, rantai/cincin n salinan G, amalgamasi n salinan G pada satu titik,
   korona C_n ⊙ G, G ⊙ K̄_n (n anting di setiap titik), dan G + K̄_n (join).
"""

from __future__ import annotations

import math
import re
from collections.abc import Callable
from dataclasses import dataclass, field

from .graf import Graf, buat_graf, graf_dari_gambar

_POLA_NAMA = re.compile(r"^([A-Za-z_]+?)_?(\d+)$")

Posisi = dict[str, tuple[float, float]]


@dataclass
class KeluargaGambar:
    nama: str                    # mis. "G"
    n_min: int
    deskripsi: str
    _buat: Callable[[int], tuple[list[str], list[tuple[str, str]], Posisi | None, str]]
    peringatan: list[str] = field(default_factory=list)
    n_gambar: int | None = None  # n anggota yang digambar (mode indeks)
    label: str = ""

    @property
    def tex(self) -> str:
        return f"{self.nama}_n"

    def ringkasan(self) -> str:
        return self.deskripsi

    def buat(self, n: int) -> Graf:
        if n < self.n_min:
            raise ValueError(f"Keluarga ini memerlukan n ≥ {self.n_min}.")
        titik, sisi, posisi, tata_letak = self._buat(n)
        return buat_graf(f"{self.nama}_{n}", f"{self.nama}_n{n}", titik, sisi, posisi, tata_letak,
                         keluarga=self.nama, n=n, nama_tex=f"{self.nama}_{{{n}}}")


def _nama_keluarga(nama: str) -> str:
    return re.sub(r"[^A-Za-z]", "", nama or "") or "G"


# ---------------------------------------------------------------------------
# 1. Tebak pola dari nama titik
# ---------------------------------------------------------------------------

PESAN_TIDAK_BERATURAN = (
    "Gambar ini tidak memperlihatkan bagian yang berulang, baik dari nama titik maupun dari letaknya "
    "(kolom, baris, atau melingkar), sehingga tidak jelas bagaimana graf bertambah besar ketika n naik. "
    "Pilihan: (1) gambar minimal dua salinan bagian yang berulang dengan letak sejajar (berkolom/berbaris) "
    "atau beri nama per salinan (x1, y1 | x2, y2 | …); (2) pilih operasi graf di atas (mis. G □ Pₙ, "
    "amalgamasi) dengan gambar Anda sebagai G — cara ini selalu bisa untuk graf apa pun.")


def keluarga_dari_indeks(titik: list[dict], sisi: list, ujung: str = "otomatis",
                         nama: str = "G") -> KeluargaGambar:
    """Tafsiran pertama dari tebak_semua (lihat di sana)."""
    semua = tebak_semua(titik, sisi, ujung, nama)
    if not semua:
        raise ValueError(PESAN_TIDAK_BERATURAN)
    return semua[0]


def tebak_semua(titik: list[dict], sisi: list, ujung: str = "otomatis", nama: str = "G") -> list[KeluargaGambar]:
    """Semua cara gambar ini bisa tumbuh menjadi keluarga Gₙ, tanpa duplikat. Urutan dicoba:
    1. nama titik per salinan (x1, y1, x2, y2, …),
    2. nomor berurutan per blok (v1–v3 | v4–v6 | …),
    3. letak titik: setiap KOLOM satu salinan (tumbuh ke samping),
    4. letak titik: setiap BARIS satu salinan (tumbuh ke bawah),
    5. letak titik: setiap JARI-JARI satu salinan (melingkar)."""
    if not titik:
        raise ValueError("Gambar masih kosong.")
    graf_dari_gambar("gambar", titik, sisi)                # validasi nama & sisi
    hasil: list[KeluargaGambar] = []
    tanda_tangan = set()

    def tambah(kel):
        try:
            n0 = max(kel.n_min, 4)
            sig = tuple(_sidik(kel.buat(n)) for n in (n0, n0 + 1))
        except ValueError:
            return
        if sig not in tanda_tangan:
            tanda_tangan.add(sig)
            hasil.append(kel)

    try:
        kel = _tebak_indeks(titik, sisi, ujung, nama)
        kel.label = "Dari nama titik"
        tambah(kel)
    except ValueError:
        pass
    for kel in _tebak_blok(titik, sisi, ujung, nama):
        tambah(kel)
    for kel in _tebak_letak(titik, sisi, ujung, nama):
        tambah(kel)
    return hasil


def _sidik(G) -> tuple:
    from .jarak import distribusi_jarak
    d = distribusi_jarak(G, dengan_pasangan=False)
    return G.banyak_titik, G.banyak_sisi, d.W, tuple(sorted(G.derajat()))


def _tafsir(titik: list[dict], sisi: list, salinan: list[list[str]], pusat: list[str], ujung: str, nama: str,
            nama_akhir) -> KeluargaGambar:
    """Tafsirkan gambar dengan pembagian salinan yang diberikan: salinan[i] = nama titik salinan ke-(i+1),
    terurut menurut posisi di dalam salinan. nama_akhir(p, i) -> nama titik keluaran."""
    huruf = "abcdefghijklmnopqrstuvwxyz"
    ganti = {}
    for i, kel in enumerate(salinan, start=1):
        if len(kel) > len(huruf):
            raise ValueError("terlalu banyak titik per salinan")
        for p, t in enumerate(kel):
            ganti[t] = f"{huruf[p]}{i}"
    nama_pusat = {}
    for j, c in enumerate(pusat):
        nama_pusat[c] = "h" + huruf[j % 26] * (j // 26 + 1) + "q"           # huruf saja, unik
        ganti[c] = nama_pusat[c]
    titik_b = [{**t, "nama": ganti[str(t["nama"])]} for t in titik]
    sisi_b = [[ganti[a], ganti[b]] for a, b in sisi]
    dalam = _tebak_indeks(titik_b, sisi_b, ujung, nama)
    # nama keluaran titik pusat: nama asli, kecuali bentrok dengan pola nama titik berulang (v1, v2_3, …)
    balik_pusat = {}
    for j, c in enumerate(pusat):
        baru = c
        if re.fullmatch(r"[A-Za-z]+\d+(_\d+)?", c):
            baru = "c" if len(pusat) == 1 else f"c{j + 1}"
        balik_pusat[nama_pusat[c]] = baru

    def akhir(t):
        if t in balik_pusat:
            return balik_pusat[t]
        m = _POLA_NAMA.match(t)
        return nama_akhir(huruf.index(m.group(1)), int(m.group(2)))

    def kunci(t):
        if t in balik_pusat:
            return (0, 0, 0)
        m = _POLA_NAMA.match(t)
        return (1, int(m.group(2)), huruf.index(m.group(1)))

    def buat(n):
        tt, ss, pos, tl = dalam._buat(n)
        return ([akhir(t) for t in sorted(tt, key=kunci)], [(akhir(x), akhir(y)) for x, y in ss],
                {akhir(t): xy for t, xy in pos.items()} if pos else None, tl)

    return KeluargaGambar(nama=dalam.nama, n_min=dalam.n_min, deskripsi=dalam.deskripsi, _buat=buat,
                          peringatan=dalam.peringatan, n_gambar=dalam.n_gambar)


def _rantai_info(kel: KeluargaGambar) -> str:
    return next((b for b in kel.deskripsi.split(", ") if b.startswith("rantai")), "")


def _tebak_blok(titik: list[dict], sisi: list, ujung: str, nama: str) -> list[KeluargaGambar]:
    """v1..vk dibaca sebagai salinan berisi b titik bernomor berurutan (b = 2, 3, …)."""
    berhuruf, pusat = {}, []
    for t in titik:
        m = _POLA_NAMA.match(str(t["nama"]))
        if m:
            berhuruf[str(t["nama"])] = (m.group(1), int(m.group(2)))
        else:
            pusat.append(str(t["nama"]))
    huruf_set = {h for h, _ in berhuruf.values()}
    if len(huruf_set) != 1:
        return []
    v = huruf_set.pop()
    k = len(berhuruf)
    if sorted(i for _, i in berhuruf.values()) != list(range(1, k + 1)):
        return []
    urut = sorted(berhuruf, key=lambda t: berhuruf[t][1])
    hasil = []
    for b in range(2, k // 2 + 1):
        if k % b:
            continue
        salinan = [urut[j:j + b] for j in range(0, k, b)]
        try:
            kel = _tafsir(titik, sisi, salinan, pusat, ujung, nama,
                          lambda p, i, b=b: f"{v}{(i - 1) * b + p + 1}")
        except ValueError:
            continue
        kel.label = f"Nomor titik per blok {b} ({v}1–{v}{b} | {v}{b + 1}–{v}{2 * b} | …)"
        kel.deskripsi = (f"setiap {b} nomor berurutan = satu salinan, gambar Anda = {kel.nama}_{k // b}, "
                         + _rantai_info(kel))
        hasil.append(kel)
    return hasil


def _kelompok_1d(nilai: dict[str, float]) -> list[list[str]] | None:
    """Kelompokkan titik menurut satu koordinat (kolom atau baris) dengan memotong celah besar."""
    item = sorted(nilai.items(), key=lambda kv: kv[1])
    if len(item) < 2:
        return None
    celah = [b[1] - a[1] for a, b in zip(item, item[1:])]
    ambang = max(25.0, 0.4 * max(celah))
    kelompok = [[item[0][0]]]
    for (t, _), c in zip(item[1:], celah):
        if c > ambang:
            kelompok.append([t])
        else:
            kelompok[-1].append(t)
    return kelompok if len(kelompok) >= 2 else None


def _tebak_letak(titik: list[dict], sisi: list, ujung: str, nama: str) -> list[KeluargaGambar]:
    pos = {str(t["nama"]): (float(t["x"]), float(t["y"])) for t in titik}
    hasil = []

    def nama_akhir(b):
        return (lambda p, i: f"v{i}") if b == 1 else (lambda p, i: f"v{p + 1}_{i}")

    # kolom (tumbuh ke samping) dan baris (tumbuh ke bawah)
    for sumbu, lain, label, arah in ((0, 1, "Setiap kolom = satu salinan (tumbuh ke samping)", "kolom"),
                                     (1, 0, "Setiap baris = satu salinan (tumbuh ke bawah)", "baris")):
        kel_ = _kelompok_1d({t: xy[sumbu] for t, xy in pos.items()})
        if not kel_:
            continue
        salinan = [sorted(k, key=lambda t: pos[t][lain]) for k in kel_]
        b = max(len(k) for k in salinan)
        try:
            kel = _tafsir(titik, sisi, salinan, [], ujung, nama, nama_akhir(b))
        except ValueError:
            continue
        kel.label = label
        kel.deskripsi = (f"setiap {arah} = satu salinan ({b} titik), gambar Anda = {kel.nama}_{len(salinan)}, "
                         + _rantai_info(kel))
        hasil.append(kel)

    # melingkar: setiap jari-jari (sudut) = satu salinan, titik dekat pusat = titik pusat
    if len(pos) >= 4:
        cx = sum(x for x, _ in pos.values()) / len(pos)
        cy = sum(y for _, y in pos.values()) / len(pos)
        r = {t: math.hypot(x - cx, y - cy) for t, (x, y) in pos.items()}
        rmaks = max(r.values()) or 1
        pusat = [t for t in pos if r[t] < 0.25 * rmaks]
        luar = {t: math.atan2(pos[t][0] - cx, -(pos[t][1] - cy)) % (2 * math.pi) for t in pos if t not in pusat}
        if len(luar) >= 3 and len(pusat) <= 2:
            item = sorted(luar.items(), key=lambda kv: kv[1])
            celah = [b[1] - a[1] for a, b in zip(item, item[1:])] + [item[0][1] + 2 * math.pi - item[-1][1]]
            ambang = max(0.2, 0.45 * max(celah))
            potong = [j for j, c in enumerate(celah) if c > ambang]
            if len(potong) >= 3:
                kelompok = []
                for a_, b_ in zip(potong, potong[1:] + [potong[0] + len(item)]):
                    kelompok.append([item[(j + 1) % len(item)][0] for j in range(a_, b_)])
                kelompok.sort(key=lambda k: min(luar[t] for t in k))
                salinan = [sorted(k, key=lambda t: r[t]) for k in kelompok]
                b = max(len(k) for k in salinan)
                try:
                    kel = _tafsir(titik, sisi, salinan, pusat, ujung, nama, nama_akhir(b))
                    kel.label = "Setiap jari-jari = satu salinan (melingkar)"
                    kel.deskripsi = (f"setiap jari-jari = satu salinan ({b} titik)"
                                     + (f", titik pusat {', '.join(pusat)}" if pusat else "")
                                     + f", gambar Anda = {kel.nama}_{len(salinan)}, " + _rantai_info(kel))
                    hasil.append(kel)
                except ValueError:
                    pass
    return hasil


def _tebak_indeks(titik: list[dict], sisi: list, ujung: str = "otomatis",
                  nama: str = "G") -> KeluargaGambar:
    nama = _nama_keluarga(nama)
    if not titik:
        raise ValueError("Gambar masih kosong.")
    G0 = graf_dari_gambar("gambar", titik, sisi)          # validasi nama & sisi ganda
    pos0 = G0.posisi
    jenis: dict[str, dict[int, str]] = {}                 # huruf -> {indeks: nama titik}
    pusat: list[str] = []
    for t in G0.titik:
        m = _POLA_NAMA.match(t)
        if m:
            jenis.setdefault(m.group(1), {})[int(m.group(2))] = t
        elif re.fullmatch(r"[A-Za-z_]+", t):
            pusat.append(t)
        else:
            raise ValueError(f"Nama titik '{t}' tidak bisa dibaca sebagai huruf+angka.")
    if not jenis:
        raise ValueError("Tidak ada titik bernama huruf+angka (mis. x1, x2, y1, y2), sehingga pola tidak "
                         "bisa ditebak dari nama titik. Pilih salah satu operasi graf, atau ganti nama titik.")
    bentrok = set(pusat) & set(jenis)
    if bentrok:
        raise ValueError(f"Nama {', '.join(sorted(bentrok))} dipakai sebagai titik pusat sekaligus jenis titik.")
    banyak = {}
    for h, idx in jenis.items():
        if sorted(idx) != list(range(1, len(idx) + 1)):
            raise ValueError(f"Indeks titik {h} harus berurutan mulai dari 1 (ditemukan: "
                             f"{', '.join(map(str, sorted(idx)))}).")
        banyak[h] = len(idx)
    k = min(banyak.values())
    if k < 2:
        raise ValueError("Setiap jenis titik perlu paling sedikit indeks 1 dan 2 (dua salinan).")
    lebih = {h: c - k for h, c in banyak.items()}
    if max(lebih.values()) > 2:
        raise ValueError("Banyak titik tiap jenis terlalu berbeda (selisih lebih dari 2); pola tidak jelas.")
    huruf = sorted(jenis)

    info = {}
    for h, idx in jenis.items():
        for i, t in idx.items():
            info[t] = (h, i)
    tetap, ke_pusat, kelas = set(), set(), set()
    for a, b in ((G0.titik[i], G0.titik[j]) for i, j in G0.sisi):
        if a in pusat and b in pusat:
            tetap.add(tuple(sorted((a, b))))
        elif a in pusat or b in pusat:
            c, t = (a, b) if a in pusat else (b, a)
            ke_pusat.add((c, *info[t]))
        else:
            (ha, ia), (hb, ib) = info[a], info[b]
            if (ha, ia) > (hb, ib):
                (ha, ia), (hb, ib) = (hb, ib), (ha, ia)
            kelas.add((ha, hb, ib - ia, ia))

    # titik pusat: terhubung ke SEMUA salinan suatu jenis, atau ke indeks tertentu (awal/akhir)
    pusat_semua, pusat_khusus = set(), set()
    for c in pusat:
        for h in huruf:
            idx = {i for cc, hh, i in ke_pusat if cc == c and hh == h}
            if not idx:
                continue
            if idx == set(range(1, banyak[h] + 1)):
                pusat_semua.add((c, h))
            else:
                for i in idx:
                    pusat_khusus.add((c, h, "awal", i) if i <= (banyak[h] + 1) / 2
                                     else (c, h, "akhir", banyak[h] - i))

    kelas_buka = {(ha, hb, o) for ha, hb, o, _ in kelas}
    semua_rata = all(v == 0 for v in lebih.values())
    sisi_huruf = [((ha, ia), (hb, ia + o)) for ha, hb, o, ia in kelas]

    def kelas_tertutup(sigma):
        """Kelas sisi rantai tertutup; sigma = permutasi huruf saat melewati sambungan n -> 1
        (identitas = siklus biasa, x<->y = terpilin seperti tangga Möbius)."""
        inv = {v: h for h, v in sigma.items()}
        hasil = set()
        for (ha, ia), (hb, ib) in sisi_huruf:
            calon = []
            for (p, i), (q, j) in (((ha, ia), (hb, ib)), ((hb, ib), (ha, ia))):
                calon += [(abs(j - i), 0, (p, q, j - i)),
                          (abs(j + k - i), 1, (p, inv[q], j + k - i)),
                          (abs(j - k - i), 1, (p, sigma[q], j - k - i))]
            hasil.add(min(calon)[2])
        return hasil

    def sisi_buka(n):
        hasil = set()
        for ha, hb, o in kelas_buka:
            for i in range(1, n + lebih[ha] + 1):
                j = i + o
                if 1 <= j <= n + lebih[hb] and (ha, i) != (hb, j):
                    hasil.add(frozenset((f"{ha}{i}", f"{hb}{j}")))
        return hasil

    def sisi_tertutup(n, kls, sigma):
        inv = {v: h for h, v in sigma.items()}
        hasil = set()
        for ha, hb, o in kls:
            for i in range(1, n + 1):
                j, h = i + o, hb
                while j > n:
                    j, h = j - n, sigma[h]
                while j < 1:
                    j, h = j + n, inv[h]
                if (ha, i) != (h, j):
                    hasil.add(frozenset((f"{ha}{i}", f"{h}{j}")))
        return hasil

    def sisi_pusat(n, siklik):
        hasil = {frozenset(e) for e in tetap}
        for c, h in pusat_semua:
            for i in range(1, n + lebih[h] + 1):
                hasil.add(frozenset((c, f"{h}{i}")))
        if not siklik:
            for c, h, dari, d in pusat_khusus:
                i = d if dari == "awal" else n + lebih[h] - d
                if 1 <= i <= n + lebih[h]:
                    hasil.add(frozenset((c, f"{h}{i}")))
        return hasil

    digambar = {frozenset((G0.titik[i], G0.titik[j])) for i, j in G0.sisi}
    cocok_buka = (sisi_buka(k) | sisi_pusat(k, False)) == digambar
    maks_buka = max((abs(o) for _, _, o in kelas_buka), default=0)
    # rantai tertutup: coba siklus biasa dulu, lalu sambungan terpilin (permutasi huruf)
    cocok_siklik, sigma_pilih, kelas_siklik, maks_siklik = False, None, set(), 0
    if semua_rata and not pusat_khusus and len(huruf) <= 5:
        from itertools import permutations
        terbaik = None
        for perm in permutations(huruf):
            sigma = dict(zip(huruf, perm))
            kls = kelas_tertutup(sigma)
            if (sisi_tertutup(k, kls, sigma) | sisi_pusat(k, True)) != digambar:
                continue
            nilai = (max((abs(o) for _, _, o in kls), default=0), perm != tuple(huruf))
            if terbaik is None or nilai < terbaik[0]:
                terbaik = (nilai, sigma, kls)
        if terbaik is not None:
            cocok_siklik = True
            (maks_siklik, _), sigma_pilih, kelas_siklik = terbaik

    peringatan = []
    if ujung == "tertutup":
        if not cocok_siklik:
            raise ValueError("Gambar ini tidak cocok dengan rantai tertutup. Coba pilih 'Terbuka' atau 'Otomatis'.")
        siklik = True
    elif ujung == "terbuka":
        if not cocok_buka:
            raise ValueError("Gambar ini tidak cocok dengan rantai terbuka. Coba pilih 'Tertutup' atau 'Otomatis'.")
        siklik = False
    else:
        if cocok_siklik and (not cocok_buka or maks_siklik < maks_buka):
            siklik = True
        elif cocok_buka:
            siklik = False
            if k == 2 and cocok_siklik:
                peringatan.append("Dari dua salinan saja tidak terlihat apakah rantai tertutup; dianggap terbuka. "
                                  "Pilih 'Tertutup' bila salinan terakhir harus tersambung ke salinan pertama.")
        else:
            raise ValueError("Pola sisi tidak beraturan, sehingga aturan perulangannya tidak bisa ditebak. "
                             "Pastikan setiap salinan memiliki sisi yang sama, atau pilih operasi graf lain.")
    if not kelas_buka and not pusat_semua:
        peringatan.append("Tidak ada sisi antarsalinan maupun ke titik pusat, sehingga G_n tidak terhubung.")

    maks_o = maks_siklik if siklik else maks_buka
    n_min = max(3, 2 * maks_o + 1) if siklik else 2

    # tata letak
    def tata_letak(n):
        pos: Posisi = {}
        if siklik:
            if k >= 3:
                cx = sum(p[0] for p in pos0.values()) / len(pos0)
                cy = sum(p[1] for p in pos0.values()) / len(pos0)
                jarak = {h: sum(math.hypot(pos0[t][0] - cx, pos0[t][1] - cy) for t in jenis[h].values())
                         / len(jenis[h]) for h in huruf}
                urut = sorted(huruf, key=lambda h: jarak[h])
            else:
                urut = huruf
            for r_i, h in enumerate(urut):
                r = 1.0 + 0.8 * r_i
                for i in range(1, n + 1):
                    sud = math.pi / 2 - 2 * math.pi * (i - 1) / n
                    pos[f"{h}{i}"] = (r * math.cos(sud), r * math.sin(sud))
            for j, c in enumerate(pusat):
                sud = 2 * math.pi * j / max(1, len(pusat))
                pos[c] = (0.0, 0.0) if len(pusat) == 1 else (0.35 * math.cos(sud), 0.35 * math.sin(sud))
            return pos, ("lingkaran-ganda" if len(huruf) > 1 else "lingkaran")
        langkah = [(pos0[jenis[h][i + 1]][0] - pos0[jenis[h][i]][0], pos0[jenis[h][i + 1]][1] - pos0[jenis[h][i]][1])
                   for h in huruf for i in range(1, banyak[h])]
        dx = sum(s[0] for s in langkah) / len(langkah)
        dy = sum(s[1] for s in langkah) / len(langkah)
        if math.hypot(dx, dy) < 1e-6:
            dx, dy = 1.5, 0.0
        for h in huruf:
            x0, y0 = pos0[jenis[h][1]]
            for i in range(1, n + lebih[h] + 1):
                pos[f"{h}{i}"] = (x0 + (i - 1) * dx, y0 + (i - 1) * dy)
        for c in pusat:
            x, y = pos0[c]
            pos[c] = (x + (n - k) / 2 * dx, y + (n - k) / 2 * dy)
        return pos, "bebas"

    def buat(n):
        titik_n = list(pusat) + [f"{h}{i}" for h in huruf for i in range(1, n + lebih[h] + 1)]
        es = (sisi_tertutup(n, kelas_siklik, sigma_pilih) if siklik else sisi_buka(n)) | sisi_pusat(n, siklik)
        sisi_n = [tuple(sorted(e)) for e in es]
        pos, tl = tata_letak(n)
        return titik_n, sisi_n, pos, tl

    bagian = [f"{len(huruf)} jenis titik ({', '.join(huruf)})"]
    if pusat:
        bagian.append(f"titik pusat {', '.join(pusat)}")
    bagian.append(f"aturan sisi: {len(kelas_siklik if siklik else kelas_buka)} pola")
    terpilin = siklik and any(h != v for h, v in sigma_pilih.items())
    if terpilin:
        tukar = ", ".join(f"{h}→{v}" for h, v in sigma_pilih.items() if h != v)
        bagian.append(f"rantai tertutup terpilin seperti tangga Möbius ({tukar} di sambungan)")
    else:
        bagian.append("rantai tertutup (seperti siklus)" if siklik else "rantai terbuka (seperti lintasan)")
    if k > 2:
        bagian.append(f"gambar Anda = {nama}_{k}")
    return KeluargaGambar(nama=nama, n_min=n_min, deskripsi="Pola dari nama titik: " + ", ".join(bagian),
                          _buat=buat, peringatan=peringatan, n_gambar=k)


def keluarga_dari_gambar(titik: list[dict], sisi: list, tertutup: bool, nama: str = "G") -> KeluargaGambar:
    """Kompatibilitas: dua salinan pertama dengan rantai tertutup/terbuka."""
    return keluarga_dari_indeks(titik, sisi, "tertutup" if tertutup else "terbuka", nama)


# ---------------------------------------------------------------------------
# 2. Operasi graf baku pada G yang digambar
# ---------------------------------------------------------------------------

@dataclass
class Operasi:
    kode: str
    label: str
    keterangan: str
    n_min: int
    parameter: tuple[str, ...] = ()     # "a", "b" (titik sambung), "s" (titik bersama)


OPERASI = {o.kode: o for o in [
    Operasi("indeks", "Tebak otomatis dari gambar (bagian yang berulang)",
            "Program mencari bagian yang berulang dari nama titik (x1, y1 | x2, y2 | …) atau dari letak "
            "titik (kolom, baris, atau melingkar). Gambar dua salinan atau satu anggota utuh. Bila ada "
            "beberapa kemungkinan, Anda memilih cara graf bertambah besar.", 2),
    Operasi("kali_p", "G □ Pₙ — hasil kali Kartesius dengan lintasan",
            "n salinan G berjajar; setiap titik terhubung ke kembarannya di salinan sebelah. "
            "Contoh: G = P₂ menghasilkan tangga Lₙ.", 1),
    Operasi("kali_c", "G □ Cₙ — hasil kali Kartesius dengan siklus",
            "Seperti G □ Pₙ, tetapi salinan terakhir juga terhubung ke salinan pertama. "
            "Contoh: G = P₂ menghasilkan CLₙ.", 3),
    Operasi("rantai", "Rantai n salinan G",
            "Salinan ke-i dan ke-(i+1) dihubungkan oleh satu sisi dari titik a (salinan i) ke titik b "
            "(salinan i+1).", 1, ("a", "b")),
    Operasi("cincin", "Cincin n salinan G (rantai tertutup)",
            "Seperti rantai, ditambah sisi dari titik a salinan terakhir ke titik b salinan pertama.", 3, ("a", "b")),
    Operasi("amalgamasi", "Amalgamasi: n salinan G berbagi satu titik",
            "Semua salinan G memakai satu titik s bersama. Contoh: G = C₃ menghasilkan graf persahabatan.",
            1, ("s",)),
    Operasi("korona_c", "Korona Cₙ ⊙ G",
            "Setiap titik siklus Cₙ dihubungkan ke semua titik satu salinan G.", 3),
    Operasi("anting", "G ⊙ K̄ₙ — n titik anting di setiap titik G",
            "Setiap titik G mendapat n titik berderajat satu.", 1),
    Operasi("join", "G + K̄ₙ — join dengan n titik baru",
            "n titik baru, masing-masing terhubung ke semua titik G.", 1),
]}


def _nm(v: str, i: int) -> str:
    return f"{v}{i}" if v.isalpha() else f"{v}_{i}"


def _huruf_bebas(G0: Graf, pilihan=("s", "z", "q", "w", "u", "p")) -> str:
    awalan = {re.match(r"[A-Za-z_]*", t).group(0) for t in G0.titik}
    return next((h for h in pilihan if h not in awalan), "baru")


def keluarga_operasi(kode: str, titik: list[dict], sisi: list, nama: str = "G",
                     a: str | None = None, b: str | None = None, s: str | None = None) -> KeluargaGambar:
    if kode == "indeks":
        return keluarga_dari_indeks(titik, sisi, "otomatis", nama)
    if kode not in OPERASI:
        raise ValueError(f"Operasi '{kode}' tidak dikenal.")
    op = OPERASI[kode]
    nama = _nama_keluarga(nama)
    G0 = graf_dari_gambar("G", titik, sisi)
    V = G0.titik
    E = [(V[i], V[j]) for i, j in G0.sisi]
    pos0 = G0.posisi
    xs = [p[0] for p in pos0.values()]
    ys = [p[1] for p in pos0.values()]
    lebar, tinggi = max(xs) - min(xs), max(ys) - min(ys)
    cx, cy = (max(xs) + min(xs)) / 2, (max(ys) + min(ys)) / 2
    jeda = max(0.6 * lebar, 0.8)
    for p_nama, nilai in (("a", a), ("b", b), ("s", s)):
        if p_nama in op.parameter and nilai not in V:
            raise ValueError(f"Pilih titik {p_nama} yang ada pada gambar.")
    peringatan = []
    if not E:
        peringatan.append("Graf G belum memiliki sisi.")

    def salinan_berjajar(n):
        return {_nm(v, i): (pos0[v][0] + (i - 1) * (lebar + jeda), pos0[v][1]) for i in range(1, n + 1) for v in V}

    def salinan_melingkar(n, r_tambah=0.0):
        R = max(1.4, n * (max(lebar, tinggi) + jeda) / (2 * math.pi)) + r_tambah
        pos = {}
        for i in range(1, n + 1):
            sud = math.pi / 2 - 2 * math.pi * (i - 1) / n
            for v in V:
                pos[_nm(v, i)] = (R * math.cos(sud) + pos0[v][0] - cx, R * math.sin(sud) + pos0[v][1] - cy)
        return pos

    if kode in ("kali_p", "kali_c", "rantai", "cincin"):
        tertutup = kode in ("kali_c", "cincin")

        def buat(n):
            tt = [_nm(v, i) for v in V for i in range(1, n + 1)]
            ss = [(_nm(u, i), _nm(v, i)) for i in range(1, n + 1) for u, v in E]
            pasang = [(i, i + 1) for i in range(1, n)] + ([(n, 1)] if tertutup and n >= 3 else [])
            for i, j in pasang:
                if kode.startswith("kali"):
                    ss += [(_nm(v, i), _nm(v, j)) for v in V]
                else:
                    ss.append((_nm(a, i), _nm(b, j)))
            pos = salinan_melingkar(n) if tertutup else salinan_berjajar(n)
            return tt, ss, pos, "bebas"
    elif kode == "amalgamasi":
        lain = [v for v in V if v != s]

        def buat(n):
            tt = [s] + [_nm(v, i) for i in range(1, n + 1) for v in lain]
            ss = []
            for i in range(1, n + 1):
                ss += [(s if u == s else _nm(u, i), s if v == s else _nm(v, i)) for u, v in E]
            pos = {s: (0.0, 0.0)}
            sx, sy = pos0[s]
            for i in range(1, n + 1):
                sud = 2 * math.pi * (i - 1) / n
                c, si_ = math.cos(sud), math.sin(sud)
                for v in lain:
                    x, y = pos0[v][0] - sx, pos0[v][1] - sy
                    pos[_nm(v, i)] = (x * c - y * si_, x * si_ + y * c)
            return tt, ss, pos, "bebas"
    elif kode == "korona_c":
        h = _huruf_bebas(G0)

        def buat(n):
            pusat = [f"{h}{i}" for i in range(1, n + 1)]
            tt = pusat + [_nm(v, i) for i in range(1, n + 1) for v in V]
            ss = [(pusat[i], pusat[(i + 1) % n]) for i in range(n)]
            for i in range(1, n + 1):
                ss += [(_nm(u, i), _nm(v, i)) for u, v in E]
                ss += [(pusat[i - 1], _nm(v, i)) for v in V]
            pos = salinan_melingkar(n, r_tambah=max(lebar, tinggi) + 1.0)
            R = max(1.0, n * 0.6 / math.pi)
            for i in range(1, n + 1):
                sud = math.pi / 2 - 2 * math.pi * (i - 1) / n
                pos[pusat[i - 1]] = (R * math.cos(sud), R * math.sin(sud))
            return tt, ss, pos, "bebas"
    elif kode == "anting":
        def buat(n):
            tt = list(V) + [f"{v}_{j}" for v in V for j in range(1, n + 1)]
            ss = list(E) + [(v, f"{v}_{j}") for v in V for j in range(1, n + 1)]
            pos = dict(pos0)
            for v in V:
                arah = math.atan2(pos0[v][1] - cy, pos0[v][0] - cx) if (pos0[v][0], pos0[v][1]) != (cx, cy) else 0
                for j in range(1, n + 1):
                    sud = arah + (j - (n + 1) / 2) * (math.pi / 2.5) / max(1, n)
                    pos[f"{v}_{j}"] = (pos0[v][0] + 0.45 * math.cos(sud), pos0[v][1] + 0.45 * math.sin(sud))
            return tt, ss, pos, "bebas"
    elif kode == "join":
        h = _huruf_bebas(G0, ("u", "w", "z", "q", "p"))

        def buat(n):
            baru = [f"{h}{j}" for j in range(1, n + 1)]
            tt = list(V) + baru
            ss = list(E) + [(v, u) for u in baru for v in V]
            pos = dict(pos0)
            for j, u in enumerate(baru):
                pos[u] = (cx + (j - (n - 1) / 2) * max(0.8, lebar / max(1, n - 1)), min(ys) - 1.4)
            return tt, ss, pos, "bebas"
    else:  # pragma: no cover
        raise ValueError(kode)

    return KeluargaGambar(nama=nama, n_min=op.n_min, deskripsi=f"{op.label} dengan G = graf gambar "
                          f"({len(V)} titik, {len(E)} sisi)", _buat=buat, peringatan=peringatan)
