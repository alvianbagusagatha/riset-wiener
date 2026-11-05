@echo off
setlocal
cd /d "%~dp0"
title Pasang - Riset Indeks Wiener
echo ==================================================
echo    Pemasangan Riset Indeks Wiener
echo ==================================================
echo.

rem --- cari Python 3.10 - 3.14 --------------------------------------------
set "PY="
for %%V in (3.13 3.12 3.11 3.14 3.10) do (
  if not defined PY (
    py -%%V -c "import sys" >nul 2>&1 && set "PY=py -%%V"
  )
)
if not defined PY (
  python -c "import sys; sys.exit(0 if (3,10)<=sys.version_info[:2]<=(3,14) else 1)" >nul 2>&1 && set "PY=python"
)
if not defined PY (
  echo Python 3.10 - 3.14 belum terpasang di komputer ini.
  echo.
  echo 1. Halaman unduhan Python akan terbuka. Pasang Python 3.13,
  echo    dan CENTANG "Add python.exe to PATH" saat memasang.
  echo 2. Setelah selesai, jalankan Pasang.bat ini lagi.
  echo.
  start "" "https://www.python.org/downloads/"
  pause
  exit /b 1
)
echo Memakai Python: %PY%

rem --- Windows membatasi panjang path; folder yang terlalu dalam membuat pemasangan gagal
set "FOLDER=%~dp0"
set "SISA=%FOLDER:~80%"
if defined SISA (
  echo.
  echo PERHATIAN: lokasi folder ini sangat panjang.
  echo Kalau pemasangan gagal, pindahkan folder ke lokasi pendek, mis. C:\riset-wiener
  echo.
)

rem --- lingkungan Python khusus aplikasi (folder .venv) ---------------------
if not exist ".venv\Scripts\python.exe" (
  echo Membuat lingkungan Python di folder .venv ...
  %PY% -m venv .venv
  if errorlevel 1 goto gagal
)
".venv\Scripts\python.exe" -m pip install --disable-pip-version-check -q --upgrade pip
".venv\Scripts\python.exe" alat\jalankan.py --tanpa-update --hanya-update
if errorlevel 1 goto gagal

rem --- pintasan di Desktop -----------------------------------------------------
powershell -NoProfile -ExecutionPolicy Bypass -Command "$d=[Environment]::GetFolderPath('Desktop'); $s=(New-Object -ComObject WScript.Shell).CreateShortcut((Join-Path $d 'Riset Indeks Wiener.lnk')); $s.TargetPath='%~dp0Buka Wiener.bat'; $s.WorkingDirectory='%~dp0'; $s.IconLocation='%~dp0alat\ikon.ico'; $s.Description='Riset Indeks Wiener'; $s.Save()" >nul 2>&1
if errorlevel 1 (
  echo Pintasan Desktop tidak bisa dibuat. Buka aplikasi lewat "Buka Wiener.bat".
) else (
  echo Pintasan "Riset Indeks Wiener" dibuat di Desktop.
)

echo.
echo Pemasangan selesai.
choice /c YN /m "Buka aplikasi sekarang"
rem Baris terakhir sengaja satu blok: berkas ini boleh ikut ter-update saat berjalan.
if errorlevel 2 (".venv\Scripts\python.exe" alat\jalankan.py --hanya-update & pause & exit /b 0) else (".venv\Scripts\python.exe" alat\jalankan.py & exit /b)

:gagal
echo.
echo Pemasangan gagal. Baca pesan di atas, lalu jalankan Pasang.bat lagi.
pause
exit /b 1
