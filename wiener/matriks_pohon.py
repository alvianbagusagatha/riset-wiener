"""Teorema Matriks-Pohon (Kirchhoff) dengan aritmetika bilangan bulat eksak.

τ(G) = det(L₀), dengan L₀ minor Laplacian (baris & kolom titik pertama dihapus).
Determinan dihitung dengan algoritma Bareiss (bebas pecahan) memakai integer Python,
sehingga hasilnya tepat untuk graf sebesar apa pun.
"""

from __future__ import annotations

from .graf import Graf


def matriks_laplacian(G: Graf) -> list[list[int]]:
    n = G.banyak_titik
    L = [[0] * n for _ in range(n)]
    for a, b in G.sisi:
        L[a][a] += 1
        L[b][b] += 1
        L[a][b] -= 1
        L[b][a] -= 1
    return L


def determinan_bareiss(M: list[list[int]]) -> int:
    """Determinan matriks bilangan bulat secara eksak (algoritma Bareiss)."""
    n = len(M)
    if n == 0:
        return 1
    A = [list(map(int, baris)) for baris in M]
    tanda = 1
    sebelumnya = 1
    for k in range(n - 1):
        if A[k][k] == 0:
            tukar = next((i for i in range(k + 1, n) if A[i][k] != 0), None)
            if tukar is None:
                return 0
            A[k], A[tukar] = A[tukar], A[k]
            tanda = -tanda
        akk = A[k][k]
        for i in range(k + 1, n):
            aik = A[i][k]
            baris_i = A[i]
            baris_k = A[k]
            for j in range(k + 1, n):
                # pembagian ini selalu tepat (sifat Bareiss)
                baris_i[j] = (baris_i[j] * akk - aik * baris_k[j]) // sebelumnya
            baris_i[k] = 0
        sebelumnya = akk
    return tanda * A[n - 1][n - 1]


def banyak_spanning_tree(G: Graf) -> int:
    """τ(G) secara tepat. Graf tidak terhubung menghasilkan 0."""
    if G.banyak_titik <= 1:
        return 1
    L = matriks_laplacian(G)
    minor = [baris[1:] for baris in L[1:]]
    return abs(determinan_bareiss(minor))
