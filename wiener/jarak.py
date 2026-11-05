"""Jarak antartitik, distribusi jarak N_t, dan indeks Wiener."""

from __future__ import annotations

from collections import deque
from dataclasses import dataclass
from math import comb

from .graf import Graf

BATAS_DAFTAR_PASANGAN = 40   # daftar pasangan per jarak hanya dibuat jika |V| ≤ 40


@dataclass
class DistribusiJarak:
    N: dict[int, int]                         # t -> banyak pasangan berjarak t
    total_pasangan: int                       # Σ N_t
    pasangan_seharusnya: int                  # C(|V|, 2)
    terhubung: bool
    W: int | None                             # Σ t·N_t (None jika tidak terhubung)
    diameter: int | None
    pasangan: dict[int, list[tuple[str, str]]] | None   # t -> daftar pasangan (|V| ≤ 40)

    def baris_tabel(self) -> list[tuple[int, int, int]]:
        return [(t, self.N[t], t * self.N[t]) for t in sorted(self.N)]


def jarak_dari(adj: list[list[int]], sumber: int) -> list[int]:
    jarak = [-1] * len(adj)
    jarak[sumber] = 0
    antre = deque([sumber])
    while antre:
        u = antre.popleft()
        for w in adj[u]:
            if jarak[w] < 0:
                jarak[w] = jarak[u] + 1
                antre.append(w)
    return jarak


def matriks_jarak(G: Graf) -> list[list[int]]:
    adj = G.tetangga()
    return [jarak_dari(adj, s) for s in range(G.banyak_titik)]


def distribusi_jarak(G: Graf, dengan_pasangan: bool | None = None) -> DistribusiJarak:
    nv = G.banyak_titik
    if dengan_pasangan is None:
        dengan_pasangan = nv <= BATAS_DAFTAR_PASANGAN
    D = matriks_jarak(G)
    N: dict[int, int] = {}
    pasangan: dict[int, list[tuple[str, str]]] | None = {} if dengan_pasangan else None
    terhubung = True
    for i in range(nv):
        for j in range(i + 1, nv):
            t = D[i][j]
            if t < 0:
                terhubung = False
                continue
            N[t] = N.get(t, 0) + 1
            if pasangan is not None:
                pasangan.setdefault(t, []).append((G.titik[i], G.titik[j]))
    total = sum(N.values())
    W = sum(t * c for t, c in N.items()) if terhubung else None
    diameter = (max(N) if N else 0) if terhubung else None
    N = dict(sorted(N.items()))
    if pasangan is not None:
        pasangan = dict(sorted(pasangan.items()))
    return DistribusiJarak(N=N, total_pasangan=total, pasangan_seharusnya=comb(nv, 2),
                           terhubung=terhubung, W=W, diameter=diameter, pasangan=pasangan)


def wiener_pohon_rumus_sisi(nv: int, sisi: list[tuple[int, int]]) -> int:
    """W(T) = Σ_{e∈T} n1(e)·n2(e), dengan n1, n2 banyak titik pada kedua sisi e."""
    adj: list[list[int]] = [[] for _ in range(nv)]
    for a, b in sisi:
        adj[a].append(b)
        adj[b].append(a)
    urutan = [0]
    induk = [-1] * nv
    induk[0] = 0
    for u in urutan:
        for w in adj[u]:
            if induk[w] < 0:
                induk[w] = u
                urutan.append(w)
    if len(urutan) != nv:
        raise ValueError("Himpunan sisi bukan pohon rentang (tidak terhubung).")
    ukuran = [1] * nv
    W = 0
    for u in reversed(urutan[1:]):
        ukuran[induk[u]] += ukuran[u]
        W += ukuran[u] * (nv - ukuran[u])
    return W
