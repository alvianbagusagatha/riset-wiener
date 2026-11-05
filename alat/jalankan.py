"""Peluncur aplikasi Riset Indeks Wiener.

Dipanggil oleh "Buka Wiener.bat" (Windows) atau "Buka Wiener.command" (Mac/Linux).
Urutannya:
  1. cek versi terbaru di GitHub, unduh dan pasang kalau ada (dilewati bila offline
     atau bila folder ini repo git milik pengembang);
  2. pasang ulang library kalau requirements.txt berubah;
  3. jalankan Streamlit dan buka browser.

Pilihan:
  --tanpa-update    jangan cek GitHub
  --tanpa-browser   jangan buka browser otomatis
  --hanya-update    cek dan pasang update saja, tanpa menjalankan aplikasi
"""
from __future__ import annotations

import hashlib
import io
import json
import os
import shutil
import socket
import subprocess
import sys
import tempfile
import time
import urllib.request
import webbrowser
import zipfile
from pathlib import Path

AKAR = Path(__file__).resolve().parent.parent
PENGATURAN = AKAR / "alat" / "pembaruan.json"
BERKAS_VERSI = AKAR / ".versi"              # sha commit yang sedang terpasang
DAFTAR_BERKAS = AKAR / ".berkas_terpasang"  # berkas dari update terakhir
HASH_LIBRARY = AKAR / ".venv" / ".hash_requirements"

# Tidak pernah ditimpa atau dihapus oleh update.
DILINDUNGI = {".venv", "hasil", ".git", ".versi", ".berkas_terpasang", "__pycache__", ".pytest_cache"}

BATAS_WAKTU = 8  # detik, untuk cek versi
# Windows membatasi path 260 karakter; beberapa berkas library sudah ±150 karakter sendiri.
BATAS_PANJANG_FOLDER = 80


def tulis(pesan: str = "") -> None:
    print(pesan, flush=True)


# ---------------------------------------------------------------- update

def baca_pengaturan() -> dict:
    try:
        return json.loads(PENGATURAN.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}


def _unduh(url: str, accept: str | None = None) -> bytes:
    kepala = {"User-Agent": "riset-wiener-peluncur"}
    if accept:
        kepala["Accept"] = accept
    with urllib.request.urlopen(urllib.request.Request(url, headers=kepala), timeout=BATAS_WAKTU) as r:
        return r.read()


def versi_terbaru(repo: str, cabang: str) -> str:
    sha = _unduh(f"https://api.github.com/repos/{repo}/commits/{cabang}",
                 accept="application/vnd.github.sha").decode().strip()
    if len(sha) != 40:
        raise ValueError("jawaban GitHub tidak dikenal")
    return sha


def _dilindungi(relatif: Path) -> bool:
    return relatif.parts[0] in DILINDUNGI or "__pycache__" in relatif.parts


def pasang_zip(data: bytes) -> int:
    """Salin isi ZIP GitHub ke folder ini. Hanya berkas yang berubah ditulis."""
    berubah = 0
    with tempfile.TemporaryDirectory() as tmp:
        with zipfile.ZipFile(io.BytesIO(data)) as z:
            z.extractall(tmp)
        isi = [p for p in Path(tmp).iterdir() if p.is_dir()]
        if len(isi) != 1:
            raise ValueError("isi ZIP tidak dikenal")
        sumber = isi[0]
        baru: list[str] = []
        for asal in sorted(sumber.rglob("*")):
            if not asal.is_file():
                continue
            rel = asal.relative_to(sumber)
            if _dilindungi(rel):
                continue
            baru.append(rel.as_posix())
            tujuan = AKAR / rel
            data_baru = asal.read_bytes()
            if tujuan.exists() and tujuan.read_bytes() == data_baru:
                continue
            tujuan.parent.mkdir(parents=True, exist_ok=True)
            tujuan.write_bytes(data_baru)
            if os.name != "nt" and (asal.suffix in {".command", ".sh"}):
                tujuan.chmod(0o755)
            berubah += 1

    # hapus berkas yang dulu dipasang update tetapi sekarang sudah tidak ada di GitHub
    try:
        lama = DAFTAR_BERKAS.read_text(encoding="utf-8").splitlines()
    except OSError:
        lama = []
    for rel in set(lama) - set(baru):
        p = AKAR / rel
        if rel and not _dilindungi(Path(rel)) and p.is_file():
            p.unlink()
            berubah += 1
    DAFTAR_BERKAS.write_text("\n".join(baru), encoding="utf-8")
    return berubah


def cek_update() -> None:
    if (AKAR / ".git").exists():
        tulis("Folder ini repo git: update lewat 'git pull', bukan otomatis.")
        return
    atur = baca_pengaturan()
    repo, cabang = atur.get("repo"), atur.get("cabang", "main")
    if not repo:
        return
    tulis("Mengecek versi terbaru di GitHub ...")
    try:
        sha = versi_terbaru(repo, cabang)
    except Exception as e:  # offline, repo belum ada, batas API, dll.
        tulis(f"  Tidak bisa mengecek update ({e.__class__.__name__}). Memakai versi yang ada.")
        return
    try:
        sekarang = BERKAS_VERSI.read_text(encoding="utf-8").strip()
    except OSError:
        sekarang = ""
    if sha == sekarang:
        tulis(f"  Sudah versi terbaru ({sha[:7]}).")
        return
    tulis(f"  Ada versi baru ({sha[:7]}). Mengunduh ...")
    try:
        data = _unduh(f"https://codeload.github.com/{repo}/zip/{sha}")
        n = pasang_zip(data)
    except Exception as e:
        tulis(f"  Update gagal ({e}). Memakai versi yang ada.")
        return
    BERKAS_VERSI.write_text(sha, encoding="utf-8")
    tulis(f"  Update selesai: {n} berkas diperbarui.")


# ---------------------------------------------------------------- library

def cek_library() -> None:
    req = AKAR / "requirements.txt"
    h = hashlib.sha256(req.read_bytes()).hexdigest()
    try:
        if HASH_LIBRARY.read_text(encoding="utf-8").strip() == h:
            return
    except OSError:
        pass
    tulis("Memasang/memperbarui library (bisa beberapa menit) ...")
    hasil = subprocess.run([sys.executable, "-m", "pip", "install", "--disable-pip-version-check",
                            "-q", "-r", str(req)])
    if hasil.returncode != 0:
        tulis("  Pemasangan library gagal. Periksa koneksi internet lalu coba lagi.")
        if os.name == "nt" and len(str(AKAR)) > BATAS_PANJANG_FOLDER:
            tulis("  Lokasi folder ini juga sangat panjang, dan Windows membatasi panjang path.")
            tulis("  Pindahkan folder ke lokasi pendek, mis. C:\\riset-wiener, hapus folder .venv")
            tulis("  di dalamnya, lalu jalankan Pasang.bat lagi.")
        sys.exit(1)
    HASH_LIBRARY.parent.mkdir(parents=True, exist_ok=True)
    HASH_LIBRARY.write_text(h, encoding="utf-8")
    tulis("  Library siap.")


# ---------------------------------------------------------------- jalankan

def port_kosong(mulai: int = 8501) -> int:
    for port in range(mulai, mulai + 50):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            if s.connect_ex(("127.0.0.1", port)) != 0:
                return port
    raise RuntimeError("tidak ada port kosong")


def tunggu_siap(port: int, proses: subprocess.Popen, batas: float = 90) -> bool:
    akhir = time.time() + batas
    while time.time() < akhir:
        if proses.poll() is not None:
            return False
        try:
            with urllib.request.urlopen(f"http://127.0.0.1:{port}/_stcore/health", timeout=2):
                return True
        except Exception:
            time.sleep(0.5)
    return False


def jalankan(buka_browser: bool) -> int:
    port = port_kosong()
    alamat = f"http://localhost:{port}"
    tulis(f"Membuka aplikasi di {alamat} ...")
    proses = subprocess.Popen(
        [sys.executable, "-m", "streamlit", "run", str(AKAR / "app.py"),
         "--server.headless", "true", "--server.port", str(port),
         "--server.address", "localhost",  # hanya bisa dibuka dari komputer ini
         "--browser.gatherUsageStats", "false"],
        cwd=AKAR)
    try:
        if tunggu_siap(port, proses):
            if buka_browser:
                webbrowser.open(alamat)
            tulis("")
            tulis("Aplikasi berjalan. Biarkan jendela ini terbuka selama dipakai;")
            tulis("tutup jendela ini (atau tekan Ctrl+C) untuk berhenti.")
        return proses.wait()
    except KeyboardInterrupt:
        proses.terminate()
        return 0


def main() -> int:
    argumen = set(sys.argv[1:])
    os.chdir(AKAR)
    if "--tanpa-update" not in argumen:
        cek_update()
    cek_library()
    if "--hanya-update" in argumen:
        return 0
    return jalankan("--tanpa-browser" not in argumen)


if __name__ == "__main__":
    sys.exit(main())
