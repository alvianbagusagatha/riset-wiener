@echo off
cd /d "%~dp0"
title Riset Indeks Wiener
if not exist ".venv\Scripts\python.exe" (
  echo Aplikasi belum dipasang. Menjalankan Pasang.bat terlebih dulu ...
  call "%~dp0Pasang.bat"
  exit /b
)
rem Satu baris: berkas ini boleh ikut ter-update saat aplikasi berjalan.
(".venv\Scripts\python.exe" alat\jalankan.py %* || pause) & exit /b
