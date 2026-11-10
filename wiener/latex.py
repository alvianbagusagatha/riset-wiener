"""Keluaran LaTeX (.tex) siap tempel ke naskah. Butuh \\usepackage{amsmath}."""

from __future__ import annotations

from pathlib import Path

from .analisis import HasilGraf
from .pola import KOLOM_POLA, HasilPola


def _ribuan(x) -> str:
    if isinstance(x, int):
        s = f"{x:,}".replace(",", ".")
        return s
    return str(x)


def _tabel_distribusi(dist, nama_tex: str, simbol_W: str, label: str) -> str:
    baris = [r"\begin{table}[htbp]", r"\centering",
             rf"\caption{{Distribusi jarak ${nama_tex}$}}", rf"\label{{{label}}}",
             r"\begin{tabular}{rrr}", r"\hline",
             r"$t$ & $N_t$ & $t \cdot N_t$ \\", r"\hline"]
    for t, N, tN in dist.baris_tabel():
        baris.append(rf"{t} & {_ribuan(N)} & {_ribuan(tN)} \\")
    baris += [r"\hline",
              rf"Jumlah & {_ribuan(dist.total_pasangan)} & {_ribuan(dist.W)} \\",
              r"\hline", r"\end{tabular}", r"\end{table}", "",
              r"\begin{equation}",
              rf"{simbol_W} = \sum_{{t \geq 1}} t \cdot N_t = {_ribuan(dist.W)}",
              r"\end{equation}", ""]
    return "\n".join(baris)


def latex_graf(h: HasilGraf) -> str:
    G = h.graf
    nt = G.nama_tex or G.nama.replace("_", r"\_")
    kode = G.kode.replace("_", "-")
    bag = [f"% Hasil komputasi untuk {G.nama} — dibuat otomatis oleh program wiener",
           r"% Membutuhkan \usepackage{amsmath}", ""]
    bag.append(_tabel_distribusi(h.distribusi, nt, f"W({nt})", f"tab:jarak-{kode}"))
    bag += [r"\begin{equation}", rf"\tau({nt}) = {_ribuan(h.tau)}", r"\end{equation}", ""]
    e = h.enumerasi
    if e is not None:
        bag += [r"\begin{table}[htbp]", r"\centering",
                rf"\caption{{Sebaran indeks Wiener spanning tree ${nt}$}}",
                rf"\label{{tab:sebaran-{kode}}}", r"\begin{tabular}{rr}", r"\hline",
                r"$W(T)$ & Banyak pohon \\", r"\hline"]
        for w, c in e.sebaran.items():
            bag.append(rf"{w} & {_ribuan(c)} \\")
        bag += [r"\hline", rf"Jumlah & {_ribuan(e.banyak)} \\", r"\hline",
                r"\end{tabular}", r"\end{table}", "",
                r"\begin{equation}",
                rf"\min_{{T}} W(T) = {e.w_min} \ ({_ribuan(e.banyak_min)}\ \text{{pohon}}), \qquad "
                rf"\max_{{T}} W(T) = {e.w_maks} \ ({_ribuan(e.banyak_maks)}\ \text{{pohon}})",
                r"\end{equation}", ""]
        if h.contoh_min is not None:
            bag.append(_tabel_distribusi(h.contoh_min.distribusi, rf"T_{{\min}} \subseteq {nt}",
                                         r"W(T_{\min})", f"tab:jarak-min-{kode}"))
        if h.contoh_maks is not None:
            bag.append(_tabel_distribusi(h.contoh_maks.distribusi, rf"T_{{\max}} \subseteq {nt}",
                                         r"W(T_{\max})", f"tab:jarak-maks-{kode}"))
    elif h.contoh_min is not None:
        bag += [f"% {h.catatan_enumerasi}", r"\begin{equation}",
                rf"\min_{{T \text{{ ditemukan}}}} W(T) = {h.contoh_min.W}", r"\end{equation}", ""]
        bag.append(_tabel_distribusi(h.contoh_min.distribusi, rf"T \subseteq {nt}",
                                     r"W(T)", f"tab:jarak-min-{kode}"))
    return "\n".join(bag)


def _rumus_tex(r, g: str) -> str:
    kiri = r.kolom.tex.format(g=g)
    if r.kolom.kunci in ("wmin", "wmaks"):
        kiri = kiri.replace("_{T}", rf"_{{T \in \mathcal{{T}}({g})}}")
    if len(r.potongan) == 1:
        pt = r.potongan[0]
        return (r"\begin{equation}" + "\n" + rf"{kiri} = {pt.tex}, \qquad n \geq {pt.n0}"
                + "\n" + r"\end{equation}")
    kasus = []
    for pt in r.potongan:
        if pt.modulus == 2:
            syarat = r"n \text{ genap}" if pt.sisa == 0 else r"n \text{ ganjil}"
        else:
            syarat = rf"n \equiv {pt.sisa} \pmod{{{pt.modulus}}}"
        kasus.append(rf"  {pt.tex}, & {syarat},\ n \geq {pt.n0}")
    return (r"\begin{equation}" + "\n" + rf"{kiri} = \begin{{cases}}" + "\n"
            + " \\\\\n".join(kasus) + "\n" + r"\end{cases}" + "\n" + r"\end{equation}")


def latex_pola(hp: HasilPola) -> str:
    g = hp.tex
    bag = [f"% Pola {hp.nama_lengkap}, n = {hp.dari}..{hp.sampai} — dibuat otomatis oleh program wiener",
           r"% Membutuhkan \usepackage{amsmath}", "",
           r"\begin{table}[htbp]", r"\centering", r"\small",
           rf"\caption{{Pola ${g}$ untuk $n = {hp.dari}, \dots, {hp.sampai}$}}",
           rf"\label{{tab:pola-{hp.kode}}}",
           r"\begin{tabular}{r" + "r" * len(KOLOM_POLA) + "}", r"\hline"]
    kepala = ["$n$"] + [f"${k.tex.format(g=g)}$" for k in KOLOM_POLA]
    bag.append(" & ".join(kepala) + r" \\")
    bag.append(r"\hline")
    for r in hp.baris:
        sel = [str(r["n"])] + [_ribuan(r[k.kunci]) if r.get(k.kunci) is not None else "--"
                               for k in KOLOM_POLA]
        bag.append(" & ".join(sel) + r" \\")
    bag += [r"\hline", r"\end{tabular}", r"\end{table}", ""]
    bag.append("% CATATAN: rumus berikut diperoleh dari komputasi (interpolasi dan verifikasi pada data),")
    bag.append("% sehingga masih berstatus dugaan dan perlu dibuktikan secara matematis.")
    for r in hp.rumus:
        if r.ditemukan:
            bag.append(f"% {r.kolom.judul}")
            bag.append(_rumus_tex(r, g))
            faktor = [pt for pt in r.potongan if pt.tex_faktor]
            if faktor:
                bag.append("% bentuk terfaktor: " + "; ".join(
                    f"{pt.label_kelas}: {pt.tex_faktor}" for pt in faktor))
            bag.append("")
        else:
            bag.append(f"% {r.kolom.judul}: tidak ditemukan polinom berderajat <= 4.")
            bag.append("")
    return "\n".join(bag)


def simpan_tex(teks: str, jalur: Path) -> Path:
    jalur.parent.mkdir(parents=True, exist_ok=True)
    jalur.write_text(teks, encoding="utf-8")
    return jalur
