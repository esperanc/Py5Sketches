"""
Algoritmos de subdivisão de malhas sobre a estrutura half-edge:

    * Catmull-Clark — produz quadriláteros; suaviza malhas de polígonos
      arbitrários (esquema aproximante, limite B-spline bicúbico).
    * Doo-Sabin     — esquema dual; cada passo gera faces-F (encolhidas),
      faces-E (uma por aresta) e faces-V (uma por vértice).
    * Loop          — só para triângulos (malhas não-triangulares são
      trianguladas em leque antes); esquema aproximante de Charles Loop.

Todos recebem um `half_edge.Mesh` e devolvem um novo `half_edge.Mesh`.
Os três suportam malhas abertas: as arestas/vértices de bordo recebem
regras especiais (curva B-spline cúbica no bordo) e o bordo é preservado.

Python puro (sem p5) — ver `_self_test()` no fim.
"""

import math
import half_edge
from half_edge import Mesh


# ── utilitários vetoriais ───────────────────────────────────────────────────
def _mid(a, b):
    return ((a[0] + b[0]) * 0.5, (a[1] + b[1]) * 0.5, (a[2] + b[2]) * 0.5)

def _lerp(a, b, t):
    """Interpola de `a` (base, sem deslocamento) para `b` (alvo suavizado).
    t=0 mantém a posição base; t=1 aplica a regra do algoritmo; t>1 exagera."""
    return (a[0] + (b[0] - a[0]) * t,
            a[1] + (b[1] - a[1]) * t,
            a[2] + (b[2] - a[2]) * t)

def _ekey(h):
    a = h.origin.id
    b = h.dest.id
    return (a, b) if a < b else (b, a)

def _boundary_neighbors(v):
    """(b1, b2): vértices vizinhos de `v` ao longo do bordo."""
    be = None
    for h in v.outgoing():
        if h.is_boundary:
            be = h
            break
    b1 = be.dest.pos          # be vai de v -> b1
    b2 = be.prev.origin.pos   # aresta de bordo que chega a v
    return b1, b2


# ── reorientação consistente (BFS) + ajuste para fora ───────────────────────
def _make_consistent(positions, faces):
    """Reorienta as faces para uma orientação global coerente (cada aresta
    interior percorrida em sentidos opostos pelas duas faces) e, no fim,
    vira tudo para fora caso a maioria das normais aponte para dentro.
    Indispensável: o construtor de Mesh rejeita orientações inconsistentes."""
    faces = [list(f) for f in faces]

    def dir_edges(f):
        k = len(f)
        return [(f[i], f[(i + 1) % k]) for i in range(k)]

    edge_faces = {}
    for fi, f in enumerate(faces):
        for (a, b) in dir_edges(f):
            key = (a, b) if a < b else (b, a)
            edge_faces.setdefault(key, []).append(fi)

    visited = [False] * len(faces)
    for start in range(len(faces)):
        if visited[start]:
            continue
        visited[start] = True
        stack = [start]
        while stack:
            fi = stack.pop()
            for (a, b) in dir_edges(faces[fi]):
                key = (a, b) if a < b else (b, a)
                for nb in edge_faces[key]:
                    if nb == fi or visited[nb]:
                        continue
                    if (a, b) in dir_edges(faces[nb]):
                        faces[nb].reverse()    # mesmo sentido → inverter
                    visited[nb] = True
                    stack.append(nb)

    # ── virar para fora (voto maioritário das normais) ──
    n = len(positions)
    cx = sum(p[0] for p in positions) / n
    cy = sum(p[1] for p in positions) / n
    cz = sum(p[2] for p in positions) / n
    vote = 0.0
    for f in faces:
        k = len(f)
        nx = ny = nz = 0.0
        fx = fy = fz = 0.0
        for i in range(k):
            p = positions[f[i]]
            q = positions[f[(i + 1) % k]]
            nx += (p[1] - q[1]) * (p[2] + q[2])
            ny += (p[2] - q[2]) * (p[0] + q[0])
            nz += (p[0] - q[0]) * (p[1] + q[1])
            fx += p[0]; fy += p[1]; fz += p[2]
        fx /= k; fy /= k; fz /= k
        vote += nx * (fx - cx) + ny * (fy - cy) + nz * (fz - cz)
    if vote < 0:
        for f in faces:
            f.reverse()
    return faces


def _finalize(positions, faces):
    faces = _make_consistent(positions, faces)
    return Mesh(positions, faces, orient=False, scale=1.0)


def triangulate(mesh):
    """Triangulação em leque de cada face (preserva a orientação)."""
    pos = [list(v.pos) for v in mesh.vertices]
    faces = []
    for f in mesh.faces:
        idx = [h.origin.id for h in f.circulate()]
        for i in range(1, len(idx) - 1):
            faces.append([idx[0], idx[i], idx[i + 1]])
    return Mesh(pos, faces, orient=False, scale=1.0)


# ── Catmull-Clark ───────────────────────────────────────────────────────────
def catmull_clark(mesh, t=1.0):
    m = mesh
    pos = []

    # pontos de face (centroides)
    fp = {}
    for f in m.faces:
        fp[f.id] = len(pos)
        pos.append(list(f.centroid))

    # pontos de aresta — base: ponto médio; alvo: média com as 2 faces
    ep = {}
    for h in m.halfedges:
        if h.is_boundary:
            continue
        k = _ekey(h)
        if k in ep:
            continue
        A = h.origin.pos
        B = h.dest.pos
        mid = _mid(A, B)
        if h.twin.is_boundary:
            e = mid
        else:
            c1 = pos[fp[h.face.id]]
            c2 = pos[fp[h.twin.face.id]]
            tgt = tuple((A[i] + B[i] + c1[i] + c2[i]) * 0.25 for i in range(3))
            e = _lerp(mid, tgt, t)
        ep[k] = len(pos)
        pos.append(list(e))

    # pontos de vértice — base: posição original P; alvo: regra de CC
    vp = {}
    for v in m.vertices:
        P = v.pos
        if v.is_boundary:
            b1, b2 = _boundary_neighbors(v)
            tgt = tuple((b1[i] + 6 * P[i] + b2[i]) / 8 for i in range(3))
        else:
            fa = [0.0, 0.0, 0.0]
            ra = [0.0, 0.0, 0.0]
            n = 0
            for h in v.outgoing():
                cf = pos[fp[h.face.id]]
                mid = _mid(h.origin.pos, h.dest.pos)
                for i in range(3):
                    fa[i] += cf[i]
                    ra[i] += mid[i]
                n += 1
            tgt = tuple((fa[i] / n + 2 * ra[i] / n + (n - 3) * P[i]) / n
                        for i in range(3))
        vp[v.id] = len(pos)
        pos.append(list(_lerp(P, tgt, t)))

    # faces (um quadrilátero por canto)
    faces = []
    for f in m.faces:
        for h in f.circulate():
            faces.append([vp[h.origin.id], ep[_ekey(h)],
                          fp[f.id], ep[_ekey(h.prev)]])
    return _finalize(pos, faces)


# ── Doo-Sabin ───────────────────────────────────────────────────────────────
def doo_sabin(mesh, t=1.0):
    m = mesh
    pos = []
    nv = {}   # id de half-edge interior -> índice do ponto-canto

    # base: vértice original P (cantos colapsam no vértice gerador);
    # alvo: média do vértice, das 2 arestas e do centroide da face.
    for f in m.faces:
        c = f.centroid
        for h in f.circulate():
            P = h.origin.pos
            m_next = _mid(h.origin.pos, h.dest.pos)            # aresta a sair
            m_prev = _mid(h.prev.origin.pos, h.prev.dest.pos)  # aresta a entrar
            tgt = tuple((P[i] + m_next[i] + m_prev[i] + c[i]) * 0.25
                        for i in range(3))
            nv[h.id] = len(pos)
            pos.append(list(_lerp(P, tgt, t)))

    faces = []
    # faces-F (uma por face, encolhida)
    for f in m.faces:
        faces.append([nv[h.id] for h in f.circulate()])
    # faces-E (uma por aresta interior)
    for h in m.halfedges:
        if h.is_boundary or h.twin.is_boundary:
            continue
        if h.id < h.twin.id:
            faces.append([nv[h.id], nv[h.twin.next.id],
                          nv[h.twin.id], nv[h.next.id]])
    # faces-V (uma por vértice interior)
    for v in m.vertices:
        ring = []
        interior = True
        for h in v.outgoing():
            if h.is_boundary:
                interior = False
                break
            ring.append(nv[h.id])
        if interior and len(ring) >= 3:
            faces.append(ring)

    return _finalize(pos, faces)


# ── Loop ────────────────────────────────────────────────────────────────────
def loop(mesh, t=1.0):
    m = triangulate(mesh)
    pos = []

    # vértices "pares" — base: posição original P; alvo: regra de Loop
    vp = {}
    for v in m.vertices:
        P = v.pos
        if v.is_boundary:
            b1, b2 = _boundary_neighbors(v)
            tgt = tuple(0.75 * P[i] + 0.125 * (b1[i] + b2[i]) for i in range(3))
        else:
            neigh = [h.dest.pos for h in v.outgoing()]
            n = len(neigh)
            beta = 3.0 / 16.0 if n == 3 else 3.0 / (8.0 * n)
            s = [sum(g[i] for g in neigh) for i in range(3)]
            tgt = tuple((1 - n * beta) * P[i] + beta * s[i] for i in range(3))
        vp[v.id] = len(pos)
        pos.append(list(_lerp(P, tgt, t)))

    # vértices "ímpares" — base: ponto médio; alvo: regra de Loop
    ep = {}
    for h in m.halfedges:
        if h.is_boundary:
            continue
        k = _ekey(h)
        if k in ep:
            continue
        A = h.origin.pos
        B = h.dest.pos
        mid = _mid(A, B)
        if h.twin.is_boundary:
            e = mid
        else:
            C = h.next.dest.pos          # vértice oposto neste triângulo
            D = h.twin.next.dest.pos     # vértice oposto no triângulo gêmeo
            tgt = tuple(0.375 * (A[i] + B[i]) + 0.125 * (C[i] + D[i])
                        for i in range(3))
            e = _lerp(mid, tgt, t)
        ep[k] = len(pos)
        pos.append(list(e))

    # cada triângulo -> 4 triângulos
    faces = []
    for f in m.faces:
        hs = list(f.circulate())
        v = [vp[h.origin.id] for h in hs]
        e = [ep[_ekey(h)] for h in hs]   # e[i] = aresta de v[i] a v[i+1]
        faces.append([v[0], e[0], e[2]])
        faces.append([v[1], e[1], e[0]])
        faces.append([v[2], e[2], e[1]])
        faces.append([e[0], e[1], e[2]])

    return _finalize(pos, faces)


ALGORITHMS = {
    "Catmull-Clark": catmull_clark,
    "Doo-Sabin":     doo_sabin,
    "Loop":          loop,
}
ALGO_NAMES = list(ALGORITHMS.keys())


def subdivide(mesh, algo, levels, t=1.0):
    fn = ALGORITHMS[algo]
    m = mesh
    for _ in range(levels):
        m = fn(m, t)
    return m


# ── auto-teste ──────────────────────────────────────────────────────────────
def _bbox_diag(mesh):
    xs = [v.x for v in mesh.vertices]
    ys = [v.y for v in mesh.vertices]
    zs = [v.z for v in mesh.vertices]
    return ((max(xs) - min(xs)) ** 2 + (max(ys) - min(ys)) ** 2
            + (max(zs) - min(zs)) ** 2) ** 0.5


def _self_test():
    for solid in half_edge.SOLID_NAMES:
        base = half_edge.build(solid)
        euler0 = base.euler()
        diag0 = _bbox_diag(base)
        for algo in ALGO_NAMES:
            m = base
            for lvl in range(1, 4):
                m = ALGORITHMS[algo](m)
                # Euler invariante: 2 (fechada) ou 1 (aberta, topologia de disco)
                assert m.euler() == euler0, \
                    f"{solid}/{algo} L{lvl}: Euler {m.euler()} != {euler0}"
                for h in m.halfedges:
                    assert h.twin is not None and h.twin.twin is h
                assert base.is_closed == m.is_closed

            # t=0 deve preservar a geometria (mesma caixa envolvente)
            m0 = ALGORITHMS[algo](base, 0.0)
            assert m0.euler() == euler0
            assert abs(_bbox_diag(m0) - diag0) < 1e-6, \
                f"{solid}/{algo} t=0 alterou a geometria"

            print(f"{solid:14s} {algo:13s} L3: "
                  f"V={m.n_vertices:5d} E={m.n_edges:5d} F={m.n_faces:5d} "
                  f"Euler={m.euler()} fechada={m.is_closed}  (t=0 ok)")
    print("OK — subdivisão consistente; t=0 preserva a geometria.")


if __name__ == "__main__":
    _self_test()
