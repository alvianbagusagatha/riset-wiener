#!/bin/bash
# Pemasangan untuk macOS dan Linux. Di Mac: klik dua kali. Di Linux: bash Pasang.command
cd "$(dirname "$0")" || exit 1
echo "=================================================="
echo "   Pemasangan Riset Indeks Wiener"
echo "=================================================="
echo

PY=""
for v in python3.13 python3.12 python3.11 python3.14 python3.10 python3; do
  if command -v "$v" >/dev/null 2>&1 && \
     "$v" -c 'import sys; sys.exit(0 if (3,10)<=sys.version_info[:2]<=(3,14) else 1)' 2>/dev/null; then
    PY="$v"; break
  fi
done
if [ -z "$PY" ]; then
  echo "Python 3.10 - 3.14 belum terpasang. Pasang Python 3.13 dari https://www.python.org/downloads/"
  echo "(Linux: sudo apt install python3 python3-venv), lalu jalankan Pasang.command lagi."
  (open "https://www.python.org/downloads/" || xdg-open "https://www.python.org/downloads/") >/dev/null 2>&1
  exit 1
fi
echo "Memakai Python: $PY"

if [ ! -x .venv/bin/python ]; then
  echo "Membuat lingkungan Python di folder .venv ..."
  "$PY" -m venv .venv || { echo "Gagal. Di Linux pasang dulu: sudo apt install python3-venv"; exit 1; }
fi
.venv/bin/python -m pip install --disable-pip-version-check -q --upgrade pip
.venv/bin/python alat/jalankan.py --tanpa-update --hanya-update || exit 1
chmod +x ./*.command

echo
echo "Pemasangan selesai. Selanjutnya buka aplikasi dengan 'Buka Wiener.command'."
read -r -p "Buka aplikasi sekarang? (y/n) " jawab
case "$jawab" in
  [yY]*) exec .venv/bin/python alat/jalankan.py ;;
  *)     exec .venv/bin/python alat/jalankan.py --hanya-update ;;
esac
