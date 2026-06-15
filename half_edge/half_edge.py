"""
Estrutura de dados *half-edge* (doubly-connected edge list) para malhas
poligonais, com circuladores de face e de vértice e suporte a malhas
abertas (arestas de borda marcadas).

Convenções
----------
* Cada aresta da malha é representada por duas *half-edges* gêmeas (twin),
  percorridas em sentidos opostos.
* Uma half-edge `h` parte de `h.origin` e aponta para `h.dest`
  (== `h.twin.origin`). A face que fica à *esquerda* de `h` é `h.face`.
* `h.next` / `h.prev` percorrem o anel da face no sentido em que ela foi
  orientada; girar `h.next` repetidamente fecha o circulador de face.
* Numa malha aberta, as half-edges de borda têm `face is None`
  (`h.is_boundary == True`) e ligam-se entre si formando o(s) anel(éis)
  do(s) buraco(s).

Este módulo é Python puro (sem dependências de p5) para poder ser testado
isoladamente — ver `_self_test()` no fim.
"""

import math

PHI = (1.0 + 5.0 ** 0.5) / 2.0


# ──────────────────────────────────────────────────────────────────────────
#  Primitivas da DCEL
# ──────────────────────────────────────────────────────────────────────────

class HalfEdge:
    __slots__ = ("origin", "twin", "next", "prev", "face", "id")

    def __init__(self):
        self.origin = None   # Vértice de origem
        self.twin = None     # Half-edge gêmea (sentido oposto)
        self.next = None     # Próxima no anel da face
        self.prev = None     # Anterior no anel da face
        self.face = None     # Face à esquerda, ou None se for borda
        self.id = -1

    @property
    def is_boundary(self):
        return self.face is None

    @property
    def dest(self):
        """Vértice de destino."""
        return self.twin.origin


class Vertex:
    __slots__ = ("x", "y", "z", "halfedge", "id")

    def __init__(self, x, y, z, i):
        self.x = float(x)
        self.y = float(y)
        self.z = float(z)
        self.halfedge = None   # uma half-edge que *parte* deste vértice
        self.id = i

    @property
    def pos(self):
        return (self.x, self.y, self.z)

    def outgoing(self):
        """Circulador de vértice: itera as half-edges que partem deste
        vértice, em ordem rotacional. Funciona tanto em vértices internos
        como de borda (nesse caso inclui a half-edge de borda)."""
        start = self.halfedge
        h = start
        while True:
            yield h
            h = h.twin.next      # rotação em torno do vértice
            if h is start:
                break

    def faces(self):
        """Faces incidentes (em ordem), ignorando o 'buraco' de borda."""
        for h in self.outgoing():
            if h.face is not None:
                yield h.face

    @property
    def is_boundary(self):
        for h in self.outgoing():
            if h.is_boundary:
                return True
        return False

    @property
    def degree(self):
        return sum(1 for _ in self.outgoing())


class Face:
    __slots__ = ("halfedge", "id")

    def __init__(self, i):
        self.halfedge = None   # uma half-edge do anel
        self.id = i

    def circulate(self):
        """Circulador de face: itera as half-edges do anel da face."""
        start = self.halfedge
        h = start
        while True:
            yield h
            h = h.next
            if h is start:
                break

    def vertices(self):
        for h in self.circulate():
            yield h.origin

    @property
    def centroid(self):
        sx = sy = sz = 0.0
        n = 0
        for v in self.vertices():
            sx += v.x; sy += v.y; sz += v.z; n += 1
        return (sx / n, sy / n, sz / n)

    @property
    def sides(self):
        return sum(1 for _ in self.circulate())

    def normal(self):
        """Normal (Newell) da face, normalizada."""
        nx = ny = nz = 0.0
        ring = list(self.vertices())
        k = len(ring)
        for i in range(k):
            p = ring[i]
            q = ring[(i + 1) % k]
            nx += (p.y - q.y) * (p.z + q.z)
            ny += (p.z - q.z) * (p.x + q.x)
            nz += (p.x - q.x) * (p.y + q.y)
        L = math.sqrt(nx * nx + ny * ny + nz * nz)
        if L < 1e-12:
            return (0.0, 1.0, 0.0)
        return (nx / L, ny / L, nz / L)


# ──────────────────────────────────────────────────────────────────────────
#  Malha
# ──────────────────────────────────────────────────────────────────────────

class Mesh:
    def __init__(self, positions, faces, orient=True, scale=1.0):
        if orient:
            faces = _orient_outward(positions, faces)

        self.vertices = [Vertex(x * scale, y * scale, z * scale, i)
                         for i, (x, y, z) in enumerate(positions)]
        self.faces = []
        self.halfedges = []

        edge_map = {}   # (a, b) -> half-edge com origin=a, dest=b

        for fi, ring in enumerate(faces):
            f = Face(fi)
            k = len(ring)
            hes = []
            for i in range(k):
                a = ring[i]
                he = HalfEdge()
                he.origin = self.vertices[a]
                he.face = f
                he.id = len(self.halfedges)
                self.halfedges.append(he)
                hes.append(he)
                if self.vertices[a].halfedge is None:
                    self.vertices[a].halfedge = he
            for i in range(k):
                hes[i].next = hes[(i + 1) % k]
                hes[i].prev = hes[(i - 1) % k]
            f.halfedge = hes[0]
            self.faces.append(f)
            for i in range(k):
                a = ring[i]
                b = ring[(i + 1) % k]
                if (a, b) in edge_map:
                    raise ValueError(
                        f"aresta dirigida repetida ({a},{b}); "
                        "malha não-manifold ou orientação inconsistente")
                edge_map[(a, b)] = hes[i]

        # ── emparelhar twins; criar half-edges de borda onde faltarem ──
        boundary = []
        for (a, b), he in list(edge_map.items()):
            if he.twin is not None:
                continue
            opp = edge_map.get((b, a))
            if opp is not None:
                he.twin = opp
                opp.twin = he
            else:
                be = HalfEdge()
                be.origin = self.vertices[b]   # borda anda de b -> a
                be.face = None
                be.id = len(self.halfedges)
                self.halfedges.append(be)
                be.twin = he
                he.twin = be
                edge_map[(b, a)] = be
                boundary.append(be)

        # ── ligar as half-edges de borda em anéis de buraco ──
        # cada vértice de borda tem exatamente uma half-edge de borda a sair
        out_boundary = {be.origin.id: be for be in boundary}
        for be in boundary:
            d = be.twin.origin.id          # destino de be
            nxt = out_boundary[d]
            be.next = nxt
            nxt.prev = be
        # vértices de borda passam a referenciar a half-edge de borda
        # (mantém o circulador de vértice canónico a começar na borda)
        for be in boundary:
            be.origin.halfedge = be

        self.boundary = boundary

    # ── consultas de conveniência ──────────────────────────────────────
    @property
    def n_vertices(self):
        return len(self.vertices)

    @property
    def n_faces(self):
        return len(self.faces)

    @property
    def n_edges(self):
        return len(self.halfedges) // 2

    @property
    def is_closed(self):
        return len(self.boundary) == 0

    def euler(self):
        return self.n_vertices - self.n_edges + self.n_faces

    def first_interior_halfedge(self):
        for he in self.halfedges:
            if not he.is_boundary:
                return he
        return self.halfedges[0]


# ──────────────────────────────────────────────────────────────────────────
#  Orientação consistente (para sólidos convexos: normal aponta para fora)
# ──────────────────────────────────────────────────────────────────────────

def _orient_outward(positions, faces):
    n = len(positions)
    cx = sum(p[0] for p in positions) / n
    cy = sum(p[1] for p in positions) / n
    cz = sum(p[2] for p in positions) / n
    out = []
    for ring in faces:
        k = len(ring)
        nx = ny = nz = 0.0
        for i in range(k):
            p = positions[ring[i]]
            q = positions[ring[(i + 1) % k]]
            nx += (p[1] - q[1]) * (p[2] + q[2])
            ny += (p[2] - q[2]) * (p[0] + q[0])
            nz += (p[0] - q[0]) * (p[1] + q[1])
        fx = sum(positions[i][0] for i in ring) / k
        fy = sum(positions[i][1] for i in ring) / k
        fz = sum(positions[i][2] for i in ring) / k
        dot = nx * (fx - cx) + ny * (fy - cy) + nz * (fz - cz)
        out.append(list(reversed(ring)) if dot < 0 else list(ring))
    return out


# ──────────────────────────────────────────────────────────────────────────
#  Sólidos platônicos e malhas de exemplo
# ──────────────────────────────────────────────────────────────────────────

def _tetrahedron():
    p = [(1, 1, 1), (-1, -1, 1), (-1, 1, -1), (1, -1, -1)]
    f = [[0, 1, 2], [0, 3, 1], [0, 2, 3], [1, 3, 2]]
    return p, f


def _cube():
    p = [(-1, -1, -1), (1, -1, -1), (1, 1, -1), (-1, 1, -1),
         (-1, -1, 1), (1, -1, 1), (1, 1, 1), (-1, 1, 1)]
    f = [[0, 1, 2, 3], [4, 5, 6, 7], [0, 1, 5, 4],
         [2, 3, 7, 6], [1, 2, 6, 5], [0, 3, 7, 4]]
    return p, f


def _octahedron():
    p = [(1, 0, 0), (-1, 0, 0), (0, 1, 0),
         (0, -1, 0), (0, 0, 1), (0, 0, -1)]
    f = [[0, 2, 4], [2, 1, 4], [1, 3, 4], [3, 0, 4],
         [2, 0, 5], [1, 2, 5], [3, 1, 5], [0, 3, 5]]
    return p, f


def _icosahedron():
    t = PHI
    p = [(-1, t, 0), (1, t, 0), (-1, -t, 0), (1, -t, 0),
         (0, -1, t), (0, 1, t), (0, -1, -t), (0, 1, -t),
         (t, 0, -1), (t, 0, 1), (-t, 0, -1), (-t, 0, 1)]
    f = [[0, 11, 5], [0, 5, 1], [0, 1, 7], [0, 7, 10], [0, 10, 11],
         [1, 5, 9], [5, 11, 4], [11, 10, 2], [10, 7, 6], [7, 1, 8],
         [3, 9, 4], [3, 4, 2], [3, 2, 6], [3, 6, 8], [3, 8, 9],
         [4, 9, 5], [2, 4, 11], [6, 2, 10], [8, 6, 7], [9, 8, 1]]
    return p, f


def _dodecahedron():
    """Dual do icosaedro, construído via circulador de vértice — cada
    pentágono é o anel ordenado de faces em torno de um vértice."""
    ico = Mesh(*_icosahedron(), orient=True)
    pos = []
    for f in ico.faces:
        cx, cy, cz = f.centroid
        L = math.sqrt(cx * cx + cy * cy + cz * cz)
        pos.append((cx / L, cy / L, cz / L))
    faces = []
    for v in ico.vertices:
        ring = [f.id for f in v.faces()]
        faces.append(ring)
    return pos, faces


def _open_box():
    """Cubo sem a face de cima — malha aberta com um buraco quadrado."""
    p, f = _cube()
    kept = [ring for ring in f
            if not all(p[i][1] > 0 for i in ring)]   # remove face y = +1
    return p, kept


def _grid(n=4, size=2.2):
    """Grade plana n×n no plano XZ — bordo retangular."""
    pos = []
    for i in range(n + 1):
        for j in range(n + 1):
            x = (j / n - 0.5) * size
            z = (i / n - 0.5) * size
            pos.append((x, 0.0, z))
    idx = lambda i, j: i * (n + 1) + j
    faces = []
    for i in range(n):
        for j in range(n):
            faces.append([idx(i, j), idx(i, j + 1),
                          idx(i + 1, j + 1), idx(i + 1, j)])
    return pos, faces


# Nome (PT) -> (gerador, orientar?, escala-base)
_SOLIDS = {
    "Tetraedro":    (_tetrahedron, True),
    "Cubo":         (_cube,        True),
    "Octaedro":     (_octahedron,  True),
    "Dodecaedro":   (_dodecahedron, True),
    "Icosaedro":    (_icosahedron, True),
    "Caixa aberta": (_open_box,    True),
    "Grade aberta": (_grid,        False),
}

SOLID_NAMES = list(_SOLIDS.keys())


def build(name, radius=200.0):
    """Constrói a malha pelo nome, normalizada para um 'raio' dado."""
    gen, orient = _SOLIDS[name]
    pos, faces = gen()
    # normaliza a maior distância à origem para `radius`
    rmax = max(math.sqrt(x * x + y * y + z * z) for (x, y, z) in pos) or 1.0
    scale = radius / rmax
    return Mesh(pos, faces, orient=orient, scale=scale)


# ──────────────────────────────────────────────────────────────────────────
#  Auto-teste (executar: python3 half_edge.py)
# ──────────────────────────────────────────────────────────────────────────

def _self_test():
    expect = {
        "Tetraedro":  (4, 6, 4, True),
        "Cubo":       (8, 12, 6, True),
        "Octaedro":   (6, 12, 8, True),
        "Dodecaedro": (20, 30, 12, True),
        "Icosaedro":  (12, 30, 20, True),
    }
    for name in SOLID_NAMES:
        m = build(name)
        V, E, F = m.n_vertices, m.n_edges, m.n_faces

        # 1) twins coerentes e anti-paralelos
        for he in m.halfedges:
            assert he.twin is not None and he.twin.twin is he
            assert he.origin is he.twin.dest
            assert he.dest is he.twin.origin
            assert he.next.prev is he and he.prev.next is he

        # 2) circulador de face fecha e dá o nº de lados certo
        for f in m.faces:
            ring = list(f.circulate())
            assert all(h.face is f for h in ring)
            assert ring[0] is f.halfedge

        # 3) circulador de vértice fecha e cobre o grau
        total_out = 0
        for v in m.vertices:
            outs = list(v.outgoing())
            total_out += len(outs)
            assert all(h.origin is v for h in outs)
        assert total_out == len(m.halfedges)   # cada he sai de 1 vértice

        # 4) borda forma anéis fechados
        for be in m.boundary:
            assert be.is_boundary
            assert be.next.is_boundary and be.prev.is_boundary
            assert be.next.prev is be

        closed = m.is_closed
        print(f"{name:14s} V={V:3d} E={E:3d} F={F:3d}  "
              f"Euler={m.euler():2d}  fechada={closed}  "
              f"bordas={len(m.boundary)}")

        if name in expect:
            eV, eE, eF, eClosed = expect[name]
            assert (V, E, F) == (eV, eE, eF), f"{name}: contagem errada"
            assert m.euler() == 2 and closed == eClosed

    # malhas abertas
    box = build("Caixa aberta")
    assert not box.is_closed and len(box.boundary) == 4
    grid = build("Grade aberta")
    assert not grid.is_closed
    # bordo da Grade 4x4 = 16 arestas
    assert len(grid.boundary) == 16, len(grid.boundary)
    # circulador de vértice de um vértice de borda inclui a half-edge de borda
    bv = next(v for v in grid.vertices if v.is_boundary)
    assert any(h.is_boundary for h in bv.outgoing())

    print("OK — todos os testes passaram.")


if __name__ == "__main__":
    _self_test()
