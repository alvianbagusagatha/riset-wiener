# Riset Indeks Wiener pada Graf dan Spanning Tree

Program Python untuk menghitung indeks Wiener sebuah graf G dan semua spanning tree-nya,
serta mencari pola/rumus untuk keluarga graf berparameter n. Berjalan di Windows, macOS,
dan Linux.

Yang dihitung:

1. **Graf**: V(G), E(G), |V|, |E|, derajat titik.
2. **Distribusi jarak**: N_t, tabel t | N_t | t·N_t, Σ N_t (dicek = C(|V|,2)), W(G),
   diameter, dan daftar pasangan per jarak (untuk |V| ≤ 40).
3. **Spanning tree**:
   - τ(G) **tepat** dengan Teorema Matriks-Pohon (determinan Bareiss, integer Python).
   - Enumerasi semua spanning tree (tanpa batas) dengan W(T) = Σ n1(e)·n2(e);
     W minimum/maksimum, banyak pohonnya, dan sebaran W.
   - Contoh pohon minimum & maksimum (sisi, N_t, pasangan per jarak).
   - Daftar semua pohon jika τ ≤ 5000 (selebihnya sampel acak 5000 pohon), gambar kisi
     semua pohon jika τ ≤ 100.
4. **Pola n**: tabel per n dan pencarian rumus polinom otomatis (pecahan eksak, derajat ≤ 4;
   satu rumus → paritas n → n mod 4; pengecualian n kecil dilaporkan sebagai "n ≥ n0"),
   lengkap dengan tabel selisih berhingga. Keluarga graf bisa dipilih dari daftar bawaan
   atau **digambar sendiri**.
5. **Graf dari gambar**: gambar graf langsung di kanvas, atau unggah foto/gambar graf
   (mis. gambar tangan) yang dideteksi otomatis.

> Rumus hasil pencarian otomatis adalah **dugaan** hasil komputasi dan masih perlu
> dibuktikan secara matematis.

## Cara memakai

Ada dua cara, dan keduanya selalu memakai versi terbaru:

- **Online**: buka link aplikasi di Streamlit Cloud. Tidak perlu memasang apa pun, tetapi
  servernya kecil, jadi graf dengan τ sangat besar lebih baik dihitung di laptop sendiri.
- **Di laptop sendiri**: pasang sekali, lalu buka lewat pintasan di Desktop.

### Memasang di laptop (tanpa mengetik perintah)

1. Unduh folder ini: di halaman GitHub klik **Code → Download ZIP**, lalu ekstrak ZIP-nya ke
   folder mana saja (mis. `Documents\riset-wiener`).
2. **Windows**: klik dua kali **`Pasang.bat`**.
   **Mac**: klik kanan **`Pasang.command`** → Open (sekali saja, karena macOS menanyakan izin).
   **Linux**: jalankan `bash Pasang.command` di terminal.
3. Kalau Python belum ada, halaman unduhan Python akan terbuka. Pasang Python 3.13
   (Windows: centang **Add python.exe to PATH**), lalu jalankan `Pasang` lagi.
4. Tunggu pemasangan library selesai (beberapa menit, hanya sekali). Di Windows, pintasan
   **Riset Indeks Wiener** muncul di Desktop.

Setelah itu, buka aplikasi dengan pintasan Desktop atau **`Buka Wiener.bat`**
(Mac/Linux: **`Buka Wiener.command`**). Aplikasi terbuka di browser. Biarkan jendela hitam
terbuka selama aplikasi dipakai, dan tutup jendela itu untuk berhenti.

### Update

Tidak perlu melakukan apa-apa. Setiap kali dibuka, `Buka Wiener` mengecek GitHub:

- kalau ada versi baru, berkasnya diunduh dan diganti otomatis;
- kalau ada library baru, library itu dipasang otomatis;
- kalau sedang offline, aplikasi tetap terbuka dengan versi terakhir.

Folder `hasil/` dan `.venv/` tidak pernah disentuh oleh update. Alamat repo yang dicek ada di
`alat/pembaruan.json`.

### Untuk pengembang

Folder yang merupakan repo git (hasil `git clone`) **tidak** di-update otomatis; pakai
`git pull` seperti biasa. Untuk memasang manual (butuh Python 3.10 – 3.14):

```bash
python -m venv .venv
.venv\Scripts\activate              # macOS/Linux: source .venv/bin/activate
pip install -r requirements-dev.txt  # requirements.txt + pytest, networkx
streamlit run app.py
```

Numba bersifat opsional tetapi sangat disarankan. Tanpa Numba program tetap berjalan
(Python murni) dengan peringatan bahwa enumerasi akan jauh lebih lambat.

### Menerbitkan versi baru

1. Ubah kode, jalankan `python -m pytest`.
2. `git commit` lalu `git push` ke GitHub.

Selesai: Streamlit Cloud men-deploy ulang otomatis dalam 1–2 menit, dan semua pengguna laptop
mendapat versi baru saat membuka aplikasi berikutnya.

### Deploy pertama ke Streamlit Cloud (sekali saja)

1. Masuk ke [share.streamlit.io](https://share.streamlit.io) dengan akun GitHub.
2. **Create app** → pilih repo ini, cabang `main`, berkas utama `app.py`.
3. Di **Advanced settings** pilih Python 3.13, lalu **Deploy**.

## Pemakaian baris perintah

```bash
python wiener.py keluarga                              # daftar keluarga graf
python wiener.py graf --keluarga CL --n 7              # analisis CL_7
python wiener.py graf --keluarga M --n 6 --tanpa-gambar
python wiener.py graf --kustom sisi.txt                # graf dari berkas
python wiener.py graf --kustom "x1-x2, x2-x3, x3-x1, x1-y1"
python wiener.py pola --keluarga CL --dari 3 --sampai 12
```

Opsi penting:

| Opsi | Arti |
|---|---|
| `--batas N` | opsional: lewati enumerasi jika τ > N (bawaan: tanpa batas) |
| `--keluaran FOLDER` | folder akar keluaran (bawaan `hasil`) |
| `--tambahan K` | (pola) banyak n tambahan di atas rentang untuk memverifikasi rumus \|V\|, \|E\|, W(G), τ (bawaan 6) |
| `--tanpa-gambar`, `--tanpa-simpan`, `--tanpa-progres` | lewati gambar / penyimpanan / bilah progres |

Format berkas graf kustom: sisi dipisah koma, titik koma, atau baris baru, mis.
`x1-x2, x2-x3, x1-y1`. Baris yang diawali `#` adalah komentar. Sisi ganda dan gelung
diabaikan dengan peringatan; format yang salah menghasilkan pesan kesalahan yang jelas.

## Aplikasi klik (Streamlit)

```bash
streamlit run app.py
```

Tampilan memakai tema sendiri (`.streamlit/config.toml`, mode terang & gelap) dengan banner
animasi, kartu metrik, dan notifikasi saat perhitungan selesai.

**Tab "Analisis satu graf"** — pilih sumber graf:

- **Keluarga graf**: pilih keluarga dan n (ada pratinjau gambar). Tombol **Ubah di kanvas gambar**
  memuat graf itu ke kanvas untuk dimodifikasi.
- **Gambar graf**: gambar graf apa pun di kanvas. Di panel yang sama ada **unggah gambar**: foto
  gambar tangan, pindaian, atau tangkapan layar dideteksi otomatis lalu muncul di kanvas yang sama
  untuk diperiksa dan diperbaiki.

Tekan **Hitung**. Hasil ditampilkan dalam tab: Ringkasan, Spanning tree, **Galeri & animasi**,
Detail, dan Unduh. Enumerasi tidak dibatasi; untuk τ besar ada perkiraan waktu, bilah progres
dengan sisa waktu, dan tombol **Stop** di pojok kanan atas.

### Galeri & animasi spanning tree

- **Galeri**: SEMUA spanning tree (untuk τ ≤ 5.000) sebagai kartu bernomor (nomor sama dengan
  Excel), dengan halaman, saringan per nilai W, dan penanda pohon minimum/maksimum.
- **Animasi**: klik kartu atau buka tab Animasi; sisi pohon "tumbuh" satu per satu. Ada tombol
  putar/jeda, maju/mundur, penggeser, dan pilihan kecepatan untuk memutar semua pohon berurutan.
- Unduhan: `*_semua_pohon.png/.pdf` (τ ≤ 100) atau PDF berhalaman berisi semua pohon
  (48 per halaman; otomatis untuk τ ≤ 1.000, dengan tombol untuk τ ≤ 5.000).
- Untuk τ > 5.000 galeri menampilkan **5.000 pohon**: contoh minimum, contoh maksimum, dan
  sampel acak seragam (algoritma Wilson; setiap pohon berpeluang sama terpilih), diurutkan
  menurut W. Sampelnya sama setiap kali dihitung, dan juga ada di sheet Excel
  "Sampel spanning tree" serta PDF `*_sampel_pohon.pdf` (lewat tombol).

### Menggambar graf

| Mode | Cara |
|---|---|
| Gambar | klik area kosong = tambah titik; klik dua titik = tambah sisi (klik lagi = hapus sisi); klik titik yang sama = batal pilih; seret titik = pindahkan |
| Hapus | klik titik atau sisi untuk menghapusnya |
| Nama | klik titik untuk mengganti namanya |

- **Awalan titik baru**: awalan `x` menghasilkan x1, x2, … (digambar merah), awalan `y` menghasilkan y1, y2, …
- **Rapikan ke kisi**, **Urungkan**, dan **Kosongkan** tersedia di bilah atas kanvas.
- Posisi titik di kanvas dipakai pada gambar keluaran. Daftar sisi bisa disimpan sebagai .txt
  untuk CLI (`--kustom`).

### Unggah gambar graf

Agar deteksi akurat: titik berupa bulatan (penuh atau lingkaran) yang jelas lebih tebal dari
garis, sisi berupa garis (hampir) lurus, dan tidak ada judul/tulisan tebal di dekat graf. Label
huruf tidak dibaca; titik diberi nama v1, v2, … yang dapat diganti dengan mode **Nama**.

### Pola untuk graf apa pun

Di tab **Pola untuk rentang n**, pilih **Gambar graf** (kanvas + unggah gambar, sama seperti di
tab pertama), lalu pilih **cara membentuk Gₙ** dari gambar:

| Cara | Keterangan | Contoh |
|---|---|---|
| Tebak otomatis dari gambar | gambar dua salinan pertama (x1, y1, x2, y2) **atau satu anggota utuh** (x1..x5, y1..y5); aturan sisi dan ujung rantai (terbuka, tertutup, atau terpilin seperti Möbius) ditebak otomatis. Bila nama titik tidak berpola (v1, v2, … acak), bagian yang berulang ditebak dari **letak** titik (kolom, baris, atau sudut) | gambar M₅ utuh → Mₙ |
| G □ Pₙ | hasil kali Kartesius dengan lintasan | P₂ □ Pₙ = Lₙ |
| G □ Cₙ | hasil kali Kartesius dengan siklus | P₂ □ Cₙ = CLₙ |
| Rantai / cincin | n salinan G, salinan i dan i+1 dihubungkan sisi a→b (cincin: juga n→1) | rantai C₃ |
| Amalgamasi | n salinan G berbagi satu titik s | C₃ → graf persahabatan |
| Korona Cₙ ⊙ G | setiap titik Cₙ dihubungkan ke satu salinan G | Cₙ ⊙ K₁ = graf matahari |
| G ⊙ K̄ₙ | n titik anting di setiap titik G | |
| G + K̄ₙ | join G dengan n titik baru | K₁ + K̄ₙ = K₁,ₙ |

Pada "tebak otomatis", titik tanpa angka (mis. c) adalah titik pusat bersama, dan
banyak titik per jenis boleh berbeda sedikit (mis. ular segitiga v1..v4, u1..u3). Satu gambar
bisa tumbuh dengan lebih dari satu cara; misalnya grid 4×3 bisa berarti kolomnya yang
bertambah (grid 4×n) atau barisnya (grid 3×n). Dalam hal itu aplikasi menampilkan semua
**tafsiran** dan Anda memilih salah satunya. Graf yang sama sekali tidak punya bagian
berulang tetap bisa dibuat keluarganya lewat operasi graf di tabel atas. Tombol
**Muat contoh keluarga dari gambar** berisi contoh siap pakai. Sebelum menghitung, aplikasi
menampilkan pratinjau Gₙ dan tabel perkiraan ukuran serta waktu untuk setiap n.

### Graf apa saja yang didukung?

Semua graf sederhana tak berarah: tanpa arah, tanpa bobot, tanpa sisi ganda, dan tanpa gelung.
W(G) hanya terdefinisi bila graf terhubung; graf tidak terhubung dilaporkan dengan τ = 0.
Enumerasi spanning tree tidak dibatasi, tetapi waktunya sebanding dengan τ (±4 juta pohon per
detik dengan 12 utas): τ sampai ratusan juta selesai dalam hitungan menit, sedangkan τ yang jauh
lebih besar bisa butuh berjam-jam. τ sendiri selalu dihitung tepat dan seketika.

## Keluaran

Semua berkas disimpan di `hasil/<nama_graf>_n<n>/`, misalnya `hasil/CL_n7/`:

- `CL_n7.xlsx` — sheet: Graf, Distribusi jarak, Sebaran W spanning tree, Contoh minimum,
  Contoh maksimum, Daftar spanning tree (τ ≤ 5000) atau Sampel spanning tree (τ > 5000).
- `CL_n7_graf.png/.pdf`, `CL_n7_pohon_minimum.png/.pdf`, `CL_n7_pohon_maksimum.png/.pdf`,
  dan `CL_n7_semua_pohon.png/.pdf` (jika τ ≤ 100). PNG 300 dpi.
- `CL_n7.tex` — tabel distribusi jarak, sebaran W, dan persamaan (butuh `amsmath`).

Perintah `pola` menyimpan ke `hasil/pola_CL_n3-12/`: Excel (sheet Pola n, Rumus,
Selisih berhingga) dan `.tex` (tabel pola + rumus dalam lingkungan `equation`).

## Keluarga graf

| Kode | Graf | Titik |
|---|---|---|
| `CL` | circular ladder CL_n (n ≥ 3) | x1..xn (siklus dalam), y1..yn (siklus luar) |
| `L` | graf tangga L_n (n ≥ 2) | x1..xn, y1..yn |
| `M` | Möbius ladder M_n (n ≥ 3) | L_n + x_n y_1 + y_n x_1 |
| `C`, `P` | siklus C_n, lintasan P_n | v1..vn |
| `K1N` | bintang K_{1,n} | c, v1..vn |
| `W` | roda W_n = c + C_n (n ≥ 3) | c, v1..vn |
| `F` | kipas F_n = c + P_n | c, v1..vn |
| `K` | graf lengkap K_n | v1..vn |

### Menambah keluarga baru

Tambahkan satu fungsi di `wiener/graf.py`:

```python
@keluarga("S", n_min=3, nama_lengkap="Graf matahari S_n", tex="S_n")
def graf_matahari(n):
    v = [f"v{i}" for i in range(1, n + 1)]
    u = [f"u{i}" for i in range(1, n + 1)]
    sisi = [(v[i], v[(i + 1) % n]) for i in range(n)] + [(v[i], u[i]) for i in range(n)]
    return v + u, sisi, None, "bebas"     # posisi None = tata letak otomatis
```

Keluarga ini langsung tersedia di CLI (`--keluarga S`), di Streamlit, dan pada perintah `pola`.

## Struktur proyek

```
wiener/            modul inti
  graf.py          struktur graf, keluarga graf, pembaca graf kustom
  jarak.py         BFS, distribusi jarak N_t, W
  matriks_pohon.py Laplacian + determinan Bareiss (τ eksak)
  enumerasi.py     enumerasi spanning tree (Numba, paralel) + cadangan Python murni
  analisis.py      analisis lengkap satu graf
  pola.py          tabel pola n, interpolasi pecahan, pencarian rumus, selisih berhingga
  pola_gambar.py   keluarga G_n dari gambar: tebak pola nama titik + operasi graf
  deteksi_gambar.py deteksi titik dan sisi dari gambar unggahan (OpenCV)
  excel.py, gambar.py, latex.py, simpan.py   keluaran
wiener.py          CLI
editor_graf.py     kanvas gambar graf (komponen Streamlit)
galeri_pohon.py    galeri & animasi spanning tree (komponen Streamlit)
tampilan.py        banner animasi dan gaya tampilan
.streamlit/        tema aplikasi
app.py             aplikasi Streamlit
tests/             pengujian pytest
alat/              peluncur dengan update otomatis (jalankan.py), alamat repo, ikon
Pasang.bat, Buka Wiener.bat           pemasang & pembuka untuk Windows
Pasang.command, Buka Wiener.command   pemasang & pembuka untuk macOS/Linux
```

## Cara kerja enumerasi

Backtracking per sisi (sertakan/abaikan) dengan union-find tanpa path compression tetapi
dengan rollback (union by size). Sisi yang boleh diabaikan dibatasi |E| − (|V| − 1), jadi
cabang yang sisa sisinya tidak cukup langsung dipangkas. Keputusan untuk beberapa sisi
pertama dijadikan "awalan" yang dikerjakan paralel di semua inti CPU; karena τ sudah
diketahui dari Teorema Matriks-Pohon, bilah progres menampilkan pohon ditemukan / τ beserta
perkiraan waktu. Hasil enumerasi selalu dicek sama dengan τ.

Waktu acuan (12 utas, Numba): CL_10 (2.620.860 pohon) ±0,5 detik; CL_12 (43.804.800 pohon)
±10 detik. Kompilasi Numba pertama kali butuh beberapa detik tambahan (lalu disimpan di cache).

## Pengujian

```bash
pip install -r requirements-dev.txt
python -m pytest -v
```

Mencakup nilai acuan CL_3, CL_4, CL_7, τ dan W min/maks spanning tree CL_n untuk n = 3..12,
rumus pola CL_n, kesamaan τ Matriks-Pohon dengan hasil enumerasi, Σ N_t = C(|V|,2),
uji silang dengan networkx untuk semua keluarga, pembaca graf kustom, keluarga dari gambar
(tebak pola dari anggota utuh harus sama dengan CL_n, L_n, M_n, W_n, F_n, … bawaan; operasi
graf diuji terhadap rumus τ yang diketahui), PDF semua pohon, dan deteksi graf dari gambar (keluaran program
maupun gambar tangan tiruan).
