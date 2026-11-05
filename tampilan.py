"""Elemen tampilan aplikasi: banner animasi (komponen CCv2) dan sedikit CSS halaman."""

from __future__ import annotations

import math

import streamlit as st


def _svg_hero() -> str:
    """Tangga melingkar CL_6 dengan spanning tree yang 'tumbuh' berulang (animasi CSS murni)."""
    n, cx, cy = 6, 150, 150
    dalam, luar = {}, {}
    for i in range(n):
        s = -math.pi / 2 + 2 * math.pi * i / n
        dalam[i] = (cx + 58 * math.cos(s), cy + 58 * math.sin(s))
        luar[i] = (cx + 118 * math.cos(s), cy + 118 * math.sin(s))
    sisi = []
    for i in range(n):
        sisi += [(dalam[i], dalam[(i + 1) % n]), (luar[i], luar[(i + 1) % n]), (dalam[i], luar[i])]
    pohon = [(dalam[0], dalam[1]), (dalam[1], dalam[2]), (dalam[2], dalam[3]), (dalam[0], dalam[5]),
             (dalam[5], dalam[4]), (dalam[0], luar[0]), (dalam[2], luar[2]), (dalam[4], luar[4]),
             (luar[0], luar[1]), (luar[2], luar[3]), (luar[4], luar[5])]
    s = ""
    for (x1, y1), (x2, y2) in sisi:
        s += f'<line class="h-sisi" x1="{x1:.1f}" y1="{y1:.1f}" x2="{x2:.1f}" y2="{y2:.1f}"/>'
    for k, ((x1, y1), (x2, y2)) in enumerate(pohon):
        s += (f'<line class="h-pohon" pathLength="1" style="animation-delay:{k * 0.28:.2f}s" '
              f'x1="{x1:.1f}" y1="{y1:.1f}" x2="{x2:.1f}" y2="{y2:.1f}"/>')
    for k, (x, y) in enumerate(list(dalam.values()) + list(luar.values())):
        kelas = "h-titik merah" if k < n else "h-titik"
        s += f'<circle class="{kelas}" style="animation-delay:{k * 0.15:.2f}s" cx="{x:.1f}" cy="{y:.1f}" r="7"/>'
    return f'<svg class="h-svg" viewBox="0 0 300 300" aria-hidden="true">{s}</svg>'


_HTML_HERO = f"""
<div class="wh-hero">
  <div class="wh-teks">
    <h1>Indeks Wiener &amp; Spanning Tree</h1>
    <p>Hitung jarak, indeks Wiener, dan <b>semua</b> spanning tree sebuah graf, lalu temukan rumus
    polanya untuk rentang n. Pilih keluarga graf, gambar sendiri, atau unggah foto graf.</p>
    <div class="wh-cip"><span>τ eksak (Kirchhoff)</span><span>Enumerasi Numba paralel</span>
    <span>Rumus pola otomatis</span><span>Gambar &amp; unggah graf</span><span>Excel · PNG · LaTeX</span></div>
  </div>
  {_svg_hero()}
</div>
"""

_CSS_HERO = """
.wh-hero {
  position: relative; overflow: hidden; border-radius: 22px; padding: 28px 34px;
  background: linear-gradient(125deg, #312e81 0%, #4f46e5 45%, #7c3aed 75%, #c026d3 100%);
  background-size: 220% 220%; animation: wh-geser 14s ease infinite; color: #fff;
  display: flex; align-items: center; gap: 28px; box-shadow: 0 18px 40px -18px rgba(79,70,229,.65);
  font-family: var(--st-font);
}
@keyframes wh-geser { 0% { background-position: 0% 50%; } 50% { background-position: 100% 50%; }
  100% { background-position: 0% 50%; } }
.wh-hero::before { content: ""; position: absolute; inset: -40%; pointer-events: none;
  background: radial-gradient(circle at 30% 30%, rgba(255,255,255,.18), transparent 40%),
              radial-gradient(circle at 80% 70%, rgba(255,255,255,.10), transparent 35%);
  animation: wh-putar 30s linear infinite; }
@keyframes wh-putar { to { transform: rotate(360deg); } }
.wh-teks { position: relative; flex: 1 1 360px; min-width: 0; }
.wh-teks h1 { margin: 0 0 8px; font-size: clamp(1.7rem, 3.4vw, 2.5rem); line-height: 1.12; font-weight: 800;
  color: #fff; letter-spacing: -.02em; animation: wh-naik .7s ease both; }
.wh-teks p { margin: 0 0 16px; opacity: .92; font-size: 1.02rem; line-height: 1.55; max-width: 640px;
  animation: wh-naik .7s .12s ease both; }
.wh-cip { display: flex; flex-wrap: wrap; gap: 8px; animation: wh-naik .7s .24s ease both; }
.wh-cip span { background: rgba(255,255,255,.16); border: 1px solid rgba(255,255,255,.28);
  padding: 5px 12px; border-radius: 999px; font-size: .82rem; font-weight: 600; }
@keyframes wh-naik { from { opacity: 0; transform: translateY(12px); } to { opacity: 1; transform: none; } }
.h-svg { position: relative; width: 210px; height: 210px; flex: 0 0 auto; filter: drop-shadow(0 8px 18px rgba(0,0,0,.25)); }
.h-sisi { stroke: rgba(255,255,255,.3); stroke-width: 2.2; stroke-dasharray: 5 5; }
.h-pohon { stroke: #fff; stroke-width: 5; stroke-linecap: round; stroke-dasharray: 1; stroke-dashoffset: 1;
  animation: wh-tumbuh 6s ease-in-out infinite; }
@keyframes wh-tumbuh { 0% { stroke-dashoffset: 1; opacity: 1; } 12% { stroke-dashoffset: 0; }
  78% { stroke-dashoffset: 0; opacity: 1; } 92%, 100% { stroke-dashoffset: 0; opacity: 0; } }
.h-titik { fill: #fff; stroke: rgba(49,46,129,.6); stroke-width: 2; transform-box: fill-box; transform-origin: center;
  animation: wh-denyut 3s ease-in-out infinite; }
.h-titik.merah { fill: #fda4af; }
@keyframes wh-denyut { 0%, 100% { transform: scale(1); } 50% { transform: scale(1.25); } }
@media (max-width: 720px) { .h-svg { display: none; } .wh-hero { padding: 22px; } }
@media (prefers-reduced-motion: reduce) {
  .wh-hero, .wh-hero::before, .h-pohon, .h-titik, .wh-teks h1, .wh-teks p, .wh-cip { animation: none; }
  .h-pohon { stroke-dashoffset: 0; } }
"""

_HERO = st.components.v2.component("hero_wiener", html=_HTML_HERO, css=_CSS_HERO)

_CSS_APP = """
<style>
/* panel dan hasil muncul dengan animasi halus */
.st-key-hasil-graf, .st-key-hasil-pola, .st-key-panel-graf, .st-key-panel-pola {
  animation: wh-muncul .55s cubic-bezier(.2,.7,.2,1) both; }
@keyframes wh-muncul { from { opacity: 0; transform: translateY(14px); } to { opacity: 1; transform: none; } }
/* kartu metrik sedikit terangkat saat disorot */
[data-testid="stMetric"] { transition: transform .18s ease, box-shadow .18s ease; }
[data-testid="stMetric"]:hover { transform: translateY(-2px); box-shadow: 0 10px 24px -14px rgba(79,70,229,.6); }
@media (prefers-reduced-motion: reduce) { .st-key-hasil-graf, .st-key-hasil-pola, .st-key-panel-graf,
  .st-key-panel-pola, [data-testid="stMetric"] { animation: none; transition: none; } }
</style>
"""


def hero() -> None:
    _HERO(key="hero")


def gaya() -> None:
    st.html(_CSS_APP)
