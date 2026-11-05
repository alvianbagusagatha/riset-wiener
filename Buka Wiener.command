#!/bin/bash
# Pembuka aplikasi untuk macOS dan Linux. Di Mac: klik dua kali.
cd "$(dirname "$0")" || exit 1
if [ ! -x .venv/bin/python ]; then
  echo "Aplikasi belum dipasang. Menjalankan Pasang.command terlebih dulu ..."
  exec bash ./Pasang.command
fi
exec .venv/bin/python alat/jalankan.py "$@"
