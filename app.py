"""Aplikasi klik (Streamlit). Jalankan dengan:  streamlit run app.py"""

from __future__ import annotations

import io
import json
import sys
import tempfile
import time
import zipfile
from pathlib import Path

import pandas as pd
import streamlit as st

# ---------------------------------------------------------------------------
# Kode baru tanpa restart. Saat aplikasi di-update sambil berjalan (mis. Streamlit
# Cloud setelah git push), Streamlit hanya menjalankan ulang app.py; modul lain
# (wiener, galeri_pohon, ...) tetap versi lama di memori. Di sini modul proyek
# dimuat ulang bila berkasnya berubah, dan hasil lama di sesi dibuang.
# ---------------------------------------------------------------------------
_AKAR = Path(__file__).resolve().parent
_MODUL_PROYEK = ("wiener", "editor_graf", "galeri_pohon", "tampilan")


def _jejak_kode() -> str:
    berkas = sorted(_AKAR.glob("wiener/*.py")) + [_AKAR / f"{m}.py" for m in _MODUL_PROYEK[1:]]
    return "|".join(f"{p.name}:{p.stat().st_mtime_ns}:{p.stat().st_size}" for p in berkas if p.exists())


_JEJAK = _jejak_kode()
if "wiener" in sys.modules and getattr(sys.modules["wiener"], "_jejak_kode", None) != _JEJAK:
    for _nama in [m for m in sys.modules if m.split(".")[0] in _MODUL_PROYEK]:
        del sys.modules[_nama]
    st.cache_data.clear()
if st.session_state.get("_jejak_kode") != _JEJAK:
    for _kunci in ("hasil_graf", "hasil_pola", "pdf_semua"):
        st.session_state.pop(_kunci, None)
    st.session_state["_jejak_kode"] = _JEJAK

import wiener  # noqa: E402

wiener._jejak_kode = _JEJAK

from editor_graf import CONTOH_POLA, editor_graf, graf_ke_gambar, muat_ke_editor, teks_sisi
from galeri_pohon import galeri_pohon
from tampilan import gaya, hero
from wiener.analisis import analisis_graf, format_angka
from wiener.enumerasi import ADA_NUMBA, info_numba
from wiener.graf import KELUARGA, graf_dari_gambar, graf_keluarga
from wiener.matriks_pohon import banyak_spanning_tree
from wiener.pola import CATATAN_BUKTI, KOLOM_POLA, analisis_pola, analisis_pola_fungsi
from wiener.pola_gambar import OPERASI, PESAN_TIDAK_BERATURAN, keluarga_operasi, tebak_semua
from wiener.simpan import BATAS_PDF_SEMUA_POHON, simpan_hasil_graf, simpan_hasil_pola, simpan_pdf_semua_pohon

st.set_page_config(page_title="Indeks Wiener & Spanning Tree", page_icon=":material/hub:", layout="wide")
gaya()
hero()

pilihan_keluarga = {f"{v.kode} — {v.nama_lengkap}": k for k, v in KELUARGA.items()}
LAJU_PERKIRAAN = 4_000_000 if ADA_NUMBA else 50_000     # pohon per detik (perkiraan kasar)
JENIS_GAMBAR = ["png", "jpg", "jpeg", "webp", "bmp"]
S_KELUARGA, S_GAMBAR = "Keluarga graf", "Gambar graf"
UJUNG = ["Otomatis", "Tertutup", "Terbuka"]

with st.sidebar:
    st.markdown("### :material/hub: Riset indeks Wiener")
    st.caption(info_numba())
    if not ADA_NUMBA:
        st.warning("Numba tidak terpasang: enumerasi memakai Python murni dan jauh lebih lambat.")
    st.markdown("**Cara pakai**")
    st.markdown("1. Pilih **keluarga graf**, atau **gambar** graf Anda sendiri (bisa juga unggah foto graf).\n"
                "2. Tekan **Hitung**.\n"
                "3. Lihat ringkasan, galeri & animasi spanning tree, lalu unduh Excel/PNG/LaTeX.\n\n"
                "Tab **Pola untuk rentang n** mencari rumus W, τ, dan W spanning tree untuk n = dari … sampai.")
    st.divider()
    st.caption("Rumus pola adalah dugaan hasil komputasi dan perlu dibuktikan secara matematis.")


# ---------------------------------------------------------------------------
# Bantuan umum
# ---------------------------------------------------------------------------

def durasi(detik: float) -> str:
    if detik < 1:
        return "< 1 detik"
    if detik < 60:
        return f"{detik:.0f} detik"
    if detik < 3600:
        return f"{detik / 60:.1f} menit"
    if detik < 86400:
        return f"{detik / 3600:.1f} jam"
    if detik < 86400 * 365:
        return f"{detik / 86400:.1f} hari"
    return "lebih dari setahun"


def pelacak_progres(bar, awalan: str = ""):
    mulai = time.perf_counter()

    def cb(selesai, total):
        lewat = time.perf_counter() - mulai
        teks = f"{awalan}{format_angka(selesai)} / {format_angka(total)} pohon"
        if 0 < selesai < total and lewat > 1:
            teks += f" · sisa ±{durasi((total - selesai) * lewat / selesai)}"
        bar.progress(min(1.0, selesai / max(total, 1)), text=teks)
    return cb


def tombol_unduh(berkas: dict[str, list[Path]], kunci: str):
    semua = [b for daftar in berkas.values() for b in daftar]
    with st.container(horizontal=True):
        for b in semua:
            if b.suffix == ".pdf" and b.with_suffix(".png") in semua:
                continue
            mime = {".xlsx": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                    ".tex": "text/x-tex", ".png": "image/png", ".pdf": "application/pdf"}.get(b.suffix)
            ikon = {".xlsx": ":material/table_chart:", ".tex": ":material/function:",
                    ".png": ":material/image:", ".pdf": ":material/picture_as_pdf:"}.get(b.suffix)
            st.download_button(b.name, b.read_bytes(), file_name=b.name, mime=mime, key=f"{kunci}-{b.name}",
                               icon=ikon)
    zbuf = io.BytesIO()
    with zipfile.ZipFile(zbuf, "w", zipfile.ZIP_DEFLATED) as z:
        for b in semua:
            z.write(b, b.name)
    st.download_button("Unduh semua (ZIP, termasuk PDF)", zbuf.getvalue(), file_name=f"{kunci}.zip",
                       mime="application/zip", key=f"{kunci}-zip", icon=":material/folder_zip:", type="primary")


def deteksi_unggahan(kunci_unggah: str, kunci_editor: str):
    """on_change uploader: deteksi graf dari gambar lalu muat ke kanvas."""
    from wiener.deteksi_gambar import deteksi_graf

    berkas = st.session_state.get(kunci_unggah)
    if berkas is None:
        return
    data = berkas.getvalue()
    st.session_state[f"asli_{kunci_editor}"] = data
    try:
        hasil = deteksi_graf(data)
    except (ValueError, RuntimeError) as e:
        st.session_state[f"pesan_{kunci_editor}"] = ("error", str(e))
        return
    muat_ke_editor(hasil.isi_editor(), key=kunci_editor)
    pesan = (f"Terdeteksi {len(hasil.titik)} titik dan {len(hasil.sisi)} sisi dan sudah dimuat ke kanvas. "
             "Periksa hasilnya: tambah, hapus, geser, atau ganti nama bila perlu.")
    if hasil.peringatan:
        pesan += " " + " ".join(hasil.peringatan)
    st.session_state[f"pesan_{kunci_editor}"] = ("success", pesan)


def kanvas_dengan_unggah(kunci_editor: str, kunci_unggah: str) -> dict:
    """Satu panel: kanvas gambar + unggah gambar (opsional) yang dideteksi ke kanvas yang sama."""
    pesan = st.session_state.get(f"pesan_{kunci_editor}")
    asli = st.session_state.get(f"asli_{kunci_editor}")
    with st.expander("Punya gambar graf? Unggah untuk dideteksi otomatis ke kanvas", icon=":material/photo_camera:",
                     expanded=asli is not None and pesan is not None and pesan[0] == "error"):
        c1, c2 = st.columns([3, 2])
        c1.file_uploader("Foto gambar tangan, pindaian, tangkapan layar, atau gambar dari makalah",
                         type=JENIS_GAMBAR, key=kunci_unggah, on_change=deteksi_unggahan,
                         args=(kunci_unggah, kunci_editor))
        c1.caption("Paling akurat bila titik berupa bulatan yang lebih tebal dari garis dan sisi berupa garis "
                   "lurus. Label huruf tidak dibaca; titik diberi nama v1, v2, … yang bisa diganti dengan mode Nama.")
        if asli is not None:
            c2.image(asli, caption="Gambar asli", width="stretch")
    if pesan is not None:
        (st.error if pesan[0] == "error" else st.success)(pesan[1], icon=":material/auto_awesome:")
    return editor_graf(key=kunci_editor)


def latex_syarat(pt) -> str:
    if pt.modulus == 1:
        return ""
    if pt.modulus == 2:
        return r"n\ \text{genap},\ " if pt.sisa == 0 else r"n\ \text{ganjil},\ "
    return rf"n \equiv {pt.sisa} \pmod{{{pt.modulus}}},\ "


@st.cache_data(max_entries=64, show_spinner=False)
def png_graf(kunci_json: str, n: int) -> bytes:
    from wiener.gambar import gambar_graf

    G = bangun(kunci_json)(n)
    folder = Path(tempfile.mkdtemp(prefix="wiener_pratinjau_"))
    return gambar_graf(G, folder / "p", judul=f"${G.nama_tex}$")[0].read_bytes()


def bangun(kunci_json: str):
    """Fungsi n -> Graf dari kunci JSON (keluarga bawaan atau keluarga dari gambar)."""
    k = json.loads(kunci_json)
    if "keluarga" in k:
        return lambda n: graf_keluarga(k["keluarga"], n)
    return keluarga_dari_kunci(kunci_json).buat


@st.cache_data(max_entries=64, show_spinner=False)
def daftar_tafsir(isi_json: str, ujung: str, nama: str) -> list[str]:
    """Label semua cara gambar ini bisa tumbuh (untuk dipilih pengguna)."""
    isi = json.loads(isi_json)
    try:
        semua = tebak_semua(isi["titik"], isi["sisi"], ujung.lower(), nama)
    except ValueError:
        return []
    return [f"{k.label} → gambar Anda = {k.nama}{_sub(k.n_gambar)}" if k.n_gambar else k.label for k in semua]


def _sub(n) -> str:
    return "".join("₀₁₂₃₄₅₆₇₈₉"[int(c)] for c in str(n))


def keluarga_dari_kunci(kunci_json: str):
    k = json.loads(kunci_json)
    isi = k["isi"]
    if k["cara"] == "indeks":
        semua = tebak_semua(isi["titik"], isi["sisi"], k["ujung"].lower(), k["nama"])
        if not semua:
            raise ValueError(PESAN_TIDAK_BERATURAN)
        return semua[min(int(k.get("tafsir", 0)), len(semua) - 1)]
    return keluarga_operasi(k["cara"], isi["titik"], isi["sisi"], k["nama"], a=k.get("a"), b=k.get("b"), s=k.get("s"))


@st.cache_data(max_entries=64, show_spinner=False)
def perkiraan(kunci_json: str, dari: int, sampai: int) -> pd.DataFrame:
    buat = bangun(kunci_json)
    baris = []
    for n in range(dari, sampai + 1):
        G = buat(n)
        tau = banyak_spanning_tree(G) if G.banyak_titik <= 400 else None
        baris.append({"n": n, "|V|": G.banyak_titik, "|E|": G.banyak_sisi,
                      "τ": format_angka(tau) if tau is not None else "?",
                      "Perkiraan enumerasi": durasi(tau / LAJU_PERKIRAAN) if tau else "-",
                      "_detik": tau / LAJU_PERKIRAAN if tau else 0})
    return pd.DataFrame(baris)


# ---------------------------------------------------------------------------
# Tab 1: analisis satu graf
# ---------------------------------------------------------------------------

def _keluarga_ke_editor():
    kode = pilihan_keluarga[st.session_state["kel-graf"]]
    G = graf_keluarga(kode, int(st.session_state["n-graf"]))
    muat_ke_editor(graf_ke_gambar(G), key="editor_graf")
    st.session_state["sumber"] = S_GAMBAR
    st.session_state["nama_gambar"] = f"{G.kode}_ubah"


def _buat_pdf_semua(h):
    st.session_state["pdf_semua"] = simpan_pdf_semua_pohon(h, akar=Path(tempfile.mkdtemp(prefix="wiener_pdf_")))


tab_graf, tab_pola = st.tabs([":material/hub: Analisis satu graf", ":material/functions: Pola untuk rentang n"])

with tab_graf:
    st.session_state.setdefault("sumber", S_KELUARGA)
    st.session_state.setdefault("nama_gambar", "graf_gambar")
    with st.container(border=True, key="panel-graf"):
        st.markdown("#### :material/looks_one: Pilih graf")
        sumber = st.segmented_control("Sumber graf", [S_KELUARGA, S_GAMBAR], key="sumber",
                                      label_visibility="collapsed") or S_KELUARGA
        if sumber == S_KELUARGA:
            kiri, kanan = st.columns([3, 2], vertical_alignment="center")
            with kiri:
                label = st.selectbox("Keluarga", list(pilihan_keluarga), key="kel-graf")
                kode = pilihan_keluarga[label]
                n = st.number_input("n", min_value=KELUARGA[kode].n_min, value=max(KELUARGA[kode].n_min, 4),
                                    step=1, key="n-graf")
                st.button("Ubah di kanvas gambar", icon=":material/edit:", on_click=_keluarga_ke_editor,
                          help="Muat graf ini ke kanvas, lalu tambah/hapus titik dan sisi sesuka Anda.")
            with kanan:
                st.image(png_graf(json.dumps({"keluarga": kode}), int(n)), width=300)
        else:
            isi_gambar = kanvas_dengan_unggah("editor_graf", "unggah-graf")
            c1, c2 = st.columns([2, 1], vertical_alignment="bottom")
            nama_gambar = c1.text_input("Nama graf (untuk nama folder dan berkas)", key="nama_gambar")
            c2.download_button("Simpan daftar sisi (.txt)", teks_sisi(isi_gambar) or "",
                               file_name=f"{nama_gambar or 'graf_gambar'}.txt", mime="text/plain",
                               icon=":material/download:", width="stretch")
        hitung = st.button("Hitung", type="primary", key="hitung-graf", icon=":material/play_arrow:",
                           width="stretch")

    if hitung:
        try:
            if sumber == S_KELUARGA:
                G = graf_keluarga(kode, int(n))
            else:
                G = graf_dari_gambar(nama_gambar.strip() or "graf_gambar", isi_gambar["titik"],
                                     isi_gambar["sisi"], isi_gambar.get("tata_letak", "bebas"))
        except ValueError as e:
            st.error(str(e), icon=":material/error:")
            st.stop()
        for p in G.peringatan:
            st.warning(p)
        tau0 = banyak_spanning_tree(G)
        if tau0 / LAJU_PERKIRAAN > 60:
            st.info(f"τ = {format_angka(tau0)} pohon; enumerasi diperkirakan ±{durasi(tau0 / LAJU_PERKIRAAN)}. "
                    "Tekan Stop di pojok kanan atas untuk menghentikannya.", icon=":material/schedule:")
        bar = st.progress(0.0, text="Menghitung…")
        h = analisis_graf(G, batas=None, progres=False, callback=pelacak_progres(bar, "Enumerasi: "))
        bar.progress(1.0, text="Selesai. Menyimpan keluaran…")
        st.session_state["hasil_graf"] = (h, simpan_hasil_graf(h, akar=Path(tempfile.mkdtemp(prefix="wiener_"))))
        st.session_state.pop("pdf_semua", None)
        bar.empty()
        st.toast(f"{G.nama} selesai: W = {h.distribusi.W}, τ = {format_angka(h.tau)}", icon=":material/check_circle:")

    if "hasil_graf" in st.session_state:
        h, berkas = st.session_state["hasil_graf"]
        G, d, e = h.graf, h.distribusi, h.enumerasi
        gambar = {b.stem: b for b in berkas.get("gambar", []) if b.suffix == ".png"}
        with st.container(key="hasil-graf"):
            st.markdown(f"### :material/insights: Hasil untuk {G.nama}")
            with st.container(horizontal=True):
                st.metric("Titik |V|", G.banyak_titik, border=True)
                st.metric("Sisi |E|", G.banyak_sisi, border=True)
                st.metric("Indeks Wiener W(G)", d.W if d.W is not None else "-", border=True)
                st.metric("Diameter", d.diameter if d.diameter is not None else "-", border=True)
                st.metric("Spanning tree τ(G)", format_angka(h.tau), border=True)

            t_ring, t_st, t_gal, t_det, t_unduh = st.tabs([
                ":material/dashboard: Ringkasan", ":material/account_tree: Spanning tree",
                ":material/animation: Galeri & animasi", ":material/list_alt: Detail", ":material/download: Unduh"])
            with t_ring:
                c1, c2 = st.columns([1, 1])
                with c1:
                    if f"{G.kode}_graf" in gambar:
                        st.image(str(gambar[f"{G.kode}_graf"]), caption=f"Graf {G.nama}")
                with c2:
                    st.markdown("**Distribusi jarak**")
                    st.dataframe(pd.DataFrame(d.baris_tabel(), columns=["t", "N_t", "t·N_t"]), hide_index=True)
                    cocok = d.total_pasangan == d.pasangan_seharusnya
                    st.caption(f"Σ N_t = {d.total_pasangan} {'=' if cocok else '≠'} C(|V|,2) = {d.pasangan_seharusnya}")
                    if e is not None:
                        st.markdown("**Sebaran W spanning tree**")
                        df = pd.DataFrame(list(e.sebaran.items()), columns=["W", "Banyak pohon"])
                        st.bar_chart(df, x="W", y="Banyak pohon", height=220)
            with t_st:
                if e is None:
                    st.info(h.catatan_enumerasi)
                else:
                    with st.container(horizontal=True):
                        st.metric("W minimum", e.w_min, border=True)
                        st.metric("Pohon minimum", format_angka(e.banyak_min), border=True)
                        st.metric("W maksimum", e.w_maks, border=True)
                        st.metric("Pohon maksimum", format_angka(e.banyak_maks), border=True)
                    st.caption(f"Enumerasi {format_angka(e.banyak)} pohon dalam {e.waktu:.2f} detik "
                               f"({'cocok' if e.banyak == h.tau else 'TIDAK cocok'} dengan τ Matriks-Pohon).")
                    c1, c2 = st.columns(2)
                    for kol, jenis, contoh in ((c1, "minimum", h.contoh_min), (c2, "maksimum", h.contoh_maks)):
                        with kol, st.container(border=True):
                            nama = f"{G.kode}_pohon_{jenis}"
                            if nama in gambar:
                                st.image(str(gambar[nama]), caption=f"Contoh pohon {jenis} (W = {contoh.W})")
                            st.dataframe(pd.DataFrame(contoh.distribusi.baris_tabel(),
                                                      columns=["t", "N_t", "t·N_t"]), hide_index=True)
                    st.markdown("**Sebaran W spanning tree**")
                    st.dataframe(pd.DataFrame(list(e.sebaran.items()), columns=["W", "Banyak pohon"]),
                                 hide_index=True)
            with t_gal:
                if e is None:
                    st.info(h.catatan_enumerasi)
                else:
                    if h.daftar is None:
                        st.info("Yang ditampilkan: contoh pohon minimum dan maksimum.", icon=":material/info:")
                    elif not h.daftar_lengkap:
                        st.info(f"τ = {format_angka(h.tau)} pohon, jadi galeri menampilkan "
                                f"**{format_angka(len(h.daftar))} pohon**: contoh minimum, contoh maksimum, dan "
                                "sampel acak seragam (setiap pohon berpeluang sama terpilih), diurutkan menurut W. "
                                "Banyak pohon per W pada saringan adalah hitungan di dalam sampel; sebaran W "
                                "untuk semua pohon ada di tab Spanning tree. Nomor sama dengan sheet Sampel di Excel.",
                                icon=":material/info:")
                    else:
                        st.caption("Semua spanning tree, nomor sama dengan daftar di Excel. Klik sebuah kartu untuk "
                                   "melihat animasinya, atau buka tab Animasi untuk memutar semua pohon.")
                    galeri_pohon(h, key="galeri")
                    if h.daftar is not None and len(h.daftar) > BATAS_PDF_SEMUA_POHON:
                        pdf = st.session_state.get("pdf_semua")
                        if pdf is None:
                            label = (f"Buat PDF semua {format_angka(h.tau)} pohon" if h.daftar_lengkap
                                     else f"Buat PDF {format_angka(len(h.daftar))} pohon sampel")
                            st.button(label, icon=":material/picture_as_pdf:", on_click=_buat_pdf_semua, args=(h,))
                        else:
                            st.download_button(pdf.name, pdf.read_bytes(), file_name=pdf.name, mime="application/pdf",
                                               icon=":material/picture_as_pdf:", type="primary")
            with t_det:
                c1, c2 = st.columns(2)
                with c1:
                    st.markdown("**Titik dan derajat**")
                    st.dataframe(pd.DataFrame({"Titik": G.titik, "Derajat": h.derajat}), hide_index=True)
                with c2:
                    st.markdown("**Himpunan**")
                    st.write("V(G) = {" + ", ".join(G.titik) + "}")
                    st.write("E(G) = {" + ", ".join(G.nama_sisi(s) for s in G.sisi) + "}")
                if d.pasangan is not None:
                    st.markdown("**Pasangan titik per jarak**")
                    st.dataframe(pd.DataFrame([[t, len(p), ", ".join(a + b for a, b in p)]
                                               for t, p in d.pasangan.items()],
                                              columns=["t", "Banyak", "Pasangan"]), hide_index=True)
                if h.daftar is not None:
                    st.markdown(f"**Daftar semua {format_angka(len(h.daftar))} spanning tree**" if h.daftar_lengkap else
                                f"**Sampel {format_angka(len(h.daftar))} dari {format_angka(h.tau)} spanning tree**")
                    D = max(max(t.distribusi.N) for t in h.daftar)
                    st.dataframe(pd.DataFrame(
                        [[t.nomor, ", ".join(G.nama_sisi(s) for s in t.sisi)]
                         + [t.distribusi.N.get(k, 0) for k in range(1, D + 1)] + [t.W] for t in h.daftar],
                        columns=["No", "Sisi"] + [f"N_{k}" for k in range(1, D + 1)] + ["W"]), hide_index=True)
            with t_unduh:
                tombol_unduh(berkas, G.kode)


# ---------------------------------------------------------------------------
# Tab 2: pola untuk rentang n
# ---------------------------------------------------------------------------

def _muat_contoh_pola():
    pilihan = st.session_state.get("contoh-pola")
    c = CONTOH_POLA.get(pilihan)
    if c is None:
        return
    isi = graf_ke_gambar(graf_keluarga(*c["keluarga"])) if "keluarga" in c else c["isi"]
    muat_ke_editor(isi, key="editor_pola")
    st.session_state["cara-pola"] = c["cara"]
    st.session_state["ujung-pola"] = c.get("ujung", "Otomatis")
    for p in ("a", "b", "s"):
        if p in c:
            st.session_state[f"param-{p}"] = c[p]
    st.session_state["sumber_pola"] = S_GAMBAR


with tab_pola:
    st.session_state.setdefault("sumber_pola", S_KELUARGA)
    st.session_state.setdefault("cara-pola", "indeks")
    st.session_state.setdefault("ujung-pola", "Otomatis")
    keluarga_g, kunci_kel, n_min = None, None, 3
    with st.container(border=True, key="panel-pola"):
        st.markdown("#### :material/looks_one: Pilih keluarga graf Gₙ")
        c1, c2 = st.columns([3, 2], vertical_alignment="center")
        sumber_p = c1.segmented_control("Sumber keluarga", [S_KELUARGA, S_GAMBAR], key="sumber_pola",
                                        label_visibility="collapsed") or S_KELUARGA
        c2.menu_button("Muat contoh keluarga dari gambar", list(CONTOH_POLA), key="contoh-pola",
                       on_click=_muat_contoh_pola, icon=":material/auto_awesome:", width="stretch")
        if sumber_p == S_KELUARGA:
            label = st.selectbox("Keluarga", list(pilihan_keluarga), key="kel-pola")
            kode_p = pilihan_keluarga[label]
            n_min = KELUARGA[kode_p].n_min
            kunci_kel = json.dumps({"keluarga": kode_p})
        else:
            st.caption("Gambar graf **apa pun**, lalu pilih cara membentuk Gₙ darinya. Untuk *Tebak dari nama "
                       "titik*, beri nama titik huruf+angka (x1, y1, x2, y2, … atau satu anggota utuh x1..x5); "
                       "untuk operasi lain, nama titik bebas.")
            isi_pola = kanvas_dengan_unggah("editor_pola", "unggah-pola")
            nama_titik = [t["nama"] for t in isi_pola["titik"]]
            c1, c2 = st.columns([3, 1])
            cara = c1.selectbox("Cara membentuk Gₙ dari gambar", list(OPERASI), key="cara-pola",
                                format_func=lambda k: OPERASI[k].label)
            nama_kel = c2.text_input("Nama keluarga", value="G", max_chars=6, key="nama-kel",
                                     help="Huruf saja; dipakai sebagai Gₙ pada tabel dan LaTeX.")
            op = OPERASI[cara]
            st.caption(op.keterangan)
            param = {}
            if cara == "indeks":
                st.segmented_control("Ujung rantai", UJUNG, key="ujung-pola",
                                     help="Otomatis: ditebak dari gambar. Dari dua salinan saja tidak terlihat "
                                          "apakah rantai tertutup, jadi pilih sendiri bila perlu.")
            elif op.parameter and nama_titik:
                kol = st.columns(len(op.parameter))
                label_p = {"a": "Titik a (salinan i)", "b": "Titik b (salinan i+1)", "s": "Titik bersama s"}
                for kk, p in zip(kol, op.parameter):
                    if st.session_state.get(f"param-{p}") not in nama_titik:
                        st.session_state[f"param-{p}"] = nama_titik[0]
                    param[p] = kk.selectbox(label_p[p], nama_titik, key=f"param-{p}")
            ujung = st.session_state["ujung-pola"] or "Otomatis"
            if cara == "indeks" and isi_pola["titik"]:
                pilihan_tafsir = daftar_tafsir(json.dumps(isi_pola, sort_keys=True), ujung, nama_kel)
                if len(pilihan_tafsir) > 1:
                    if st.session_state.get("tafsir-pola", 0) >= len(pilihan_tafsir):
                        st.session_state["tafsir-pola"] = 0
                    param["tafsir"] = st.radio(
                        "Gambar ini bisa bertambah besar dengan beberapa cara. Pilih yang Anda maksud:",
                        list(range(len(pilihan_tafsir))), format_func=lambda i: pilihan_tafsir[i], key="tafsir-pola")
            if isi_pola["titik"]:
                kunci_kel = json.dumps({"isi": isi_pola, "cara": cara, "ujung": ujung, "nama": nama_kel, **param},
                                       sort_keys=True)
                try:
                    keluarga_g = keluarga_dari_kunci(kunci_kel)
                except ValueError as e:
                    st.warning(str(e), icon=":material/warning:")
                    kunci_kel = None
            else:
                st.info("Kanvas masih kosong. Gambar graf, unggah gambar, atau pilih contoh.", icon=":material/draw:")
            if keluarga_g is not None:
                n_min = keluarga_g.n_min
                st.success(f"**{keluarga_g.nama}ₙ** — {keluarga_g.ringkasan()}.", icon=":material/check_circle:")
                for p in keluarga_g.peringatan:
                    st.warning(p, icon=":material/warning:")

        if kunci_kel is not None:
            with st.expander("Pratinjau anggota keluarga", icon=":material/visibility:", expanded=sumber_p == S_GAMBAR):
                n_lihat = st.slider("n untuk pratinjau", min_value=n_min, max_value=max(n_min + 9, 10),
                                    value=max(5, n_min), key=f"n-pratinjau-{sumber_p}")
                try:
                    st.image(png_graf(kunci_kel, n_lihat), width=460)
                except ValueError as e:
                    st.warning(str(e))

        st.markdown("#### :material/looks_two: Rentang n")
        c1, c2 = st.columns(2)
        dari = c1.number_input("dari n", min_value=n_min, value=max(3, n_min), key="dari-pola")
        sampai = c2.number_input("sampai n", min_value=int(dari), value=int(dari) + 7, key="sampai-pola")
        tambahan = 6     # n ekstra (tanpa enumerasi) untuk memverifikasi rumus |V|, |E|, W(G), τ
        if kunci_kel is not None:
            try:
                tabel = perkiraan(kunci_kel, int(dari), int(sampai))
                total = float(tabel["_detik"].sum())
                with st.expander(f"Perkiraan ukuran dan waktu: total ±{durasi(total)}", icon=":material/schedule:",
                                 expanded=total > 300):
                    st.dataframe(tabel.drop(columns="_detik"), hide_index=True)
                    if total > 300:
                        st.warning("Enumerasi akan lama. Perkecil 'sampai n' bila ingin hasil cepat.")
            except ValueError as e:
                st.warning(str(e))
        hitung_pola = st.button("Hitung pola", type="primary", disabled=kunci_kel is None,
                                icon=":material/play_arrow:", width="stretch")

    if hitung_pola and kunci_kel is not None:
        bar = st.progress(0.0, text="Menghitung…")
        bar_n = st.empty()

        def cbp(n, a, b):
            bar.progress((n - a + 1) / (b - a + 1), text=f"Selesai n = {n} dari {b}")

        pelacak: dict = {}

        def cb_pohon(n, selesai, total):
            if pelacak.get("n") != n:
                pelacak["n"] = n
                pelacak["cb"] = pelacak_progres(bar_n, f"n = {n}: ")
            pelacak["cb"](selesai, total)

        if sumber_p == S_KELUARGA:
            hp = analisis_pola(kode_p, int(dari), int(sampai), batas=None, tambahan=int(tambahan),
                               progres=False, callback=cbp, callback_pohon=cb_pohon)
        else:
            kg = keluarga_g
            hp = analisis_pola_fungsi(kg.nama, f"keluarga {kg.tex} dari gambar", kg.tex, kg.buat, kg.n_min,
                                      int(dari), int(sampai), batas=None, tambahan=int(tambahan),
                                      progres=False, callback=cbp, callback_pohon=cb_pohon)
        st.session_state["hasil_pola"] = (hp, simpan_hasil_pola(hp, akar=Path(tempfile.mkdtemp(prefix="wiener_pola_"))))
        bar.empty()
        bar_n.empty()
        jumlah = sum(r.ditemukan for r in hp.rumus)
        st.toast(f"Pola selesai: {jumlah} dari {len(hp.rumus)} kolom punya rumus", icon=":material/functions:")

    if "hasil_pola" in st.session_state:
        hp, berkas = st.session_state["hasil_pola"]
        with st.container(key="hasil-pola"):
            st.markdown(f"### :material/insights: Pola {hp.nama_lengkap}, n = {hp.dari}..{hp.sampai}")
            t_rumus, t_tabel, t_unduh = st.tabs([":material/function: Rumus", ":material/table: Tabel per n",
                                                 ":material/download: Unduh"])
            with t_rumus:
                for r in hp.rumus:
                    with st.container(border=True):
                        if not r.ditemukan:
                            st.markdown(f"**{r.kolom.judul}** :gray-badge[tidak ditemukan polinom berderajat ≤ 4]")
                            continue
                        st.markdown(f"**{r.kolom.judul}** :green-badge[rumus ditemukan]")
                        kiri = r.kolom.tex.format(g=hp.tex)
                        for pt in r.potongan:
                            faktor = f" = {pt.tex_faktor}" if pt.tex_faktor else ""
                            st.latex(rf"{kiri} = {pt.tex}{faktor} \qquad ({latex_syarat(pt)}n \geq {pt.n0})")
                        with st.expander("Tabel selisih berhingga"):
                            for pt in r.potongan:
                                st.caption(pt.label_kelas)
                                st.dataframe(pd.DataFrame([["n"] + pt.selisih_n] +
                                                          [["nilai" if i == 0 else f"selisih {i}"] + s
                                                           for i, s in enumerate(pt.selisih)]), hide_index=True)
                st.info(CATATAN_BUKTI, icon=":material/info:")
            with t_tabel:
                st.dataframe(pd.DataFrame([[r["n"]] + [r.get(k.kunci) for k in KOLOM_POLA] for r in hp.baris],
                                          columns=["n"] + [k.judul for k in KOLOM_POLA]), hide_index=True)
                for c in hp.catatan:
                    st.caption(c)
            with t_unduh:
                tombol_unduh(berkas, f"pola_{hp.kode}")
