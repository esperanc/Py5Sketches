"""
Poligonização de um campo escalar por «marching tetrahedra».

Esta é a variante simplicial do marching cubes (o análogo 3D do marching
triangles): cada célula da grade é dividida em 6 tetraedros e cada tetraedro
é poligonizado de forma exata e SEM ambiguidade — ao contrário das 256
configurações do marching cubes clássico, um tetraedro só tem três topologias
possíveis (0, 1 ou 2 vértices no interior), pelo que não há buracos nem casos
ambíguos a tratar.

Fluxo:
  1. amostra-se o campo nos (n+1)^3 nós de uma grade regular em [-B, B]^3;
  2. para cada uma das n^3 células percorrem-se os seus 6 tetraedros;
  3. em cada aresta de tetraedro que cruza o nível faz-se interpolação linear;
  4. a normal de cada vértice vem do gradiente do campo (∇f aponta para fora).
"""


# Cantos do cubo unitário, índices 0..7
_CORNERS = [
    (0, 0, 0), (1, 0, 0), (1, 1, 0), (0, 1, 0),
    (0, 0, 1), (1, 0, 1), (1, 1, 1), (0, 1, 1),
]

# Decomposição do cubo em 6 tetraedros em leque à volta da diagonal 0–6.
# Os vértices 1,2,3,7,4,5 formam um ciclo hexagonal (a silhueta do cubo visto
# ao longo da diagonal); cada par consecutivo + {0,6} dá um tetraedro.
_TETS = [
    (0, 6, 1, 2), (0, 6, 2, 3), (0, 6, 3, 7),
    (0, 6, 7, 4), (0, 6, 4, 5), (0, 6, 5, 1),
]


def _interp(iso, p0, v0, p1, v1):
    d = v1 - v0
    t = 0.5 if abs(d) < 1e-12 else (iso - v0) / d
    if t < 0.0:
        t = 0.0
    elif t > 1.0:
        t = 1.0
    return (p0[0] + (p1[0] - p0[0]) * t,
            p0[1] + (p1[1] - p0[1]) * t,
            p0[2] + (p1[2] - p0[2]) * t)


def _march_tet(iso, pp, vv, out):
    """Poligoniza um tetraedro: pp/vv são as 4 posições/valores. Acrescenta
    vértices de triângulos (em grupos de 3) a `out`."""
    inside = (vv[0] < iso, vv[1] < iso, vv[2] < iso, vv[3] < iso)
    cnt = inside[0] + inside[1] + inside[2] + inside[3]
    if cnt == 0 or cnt == 4:
        return

    def E(m, o):
        return _interp(iso, pp[m], vv[m], pp[o], vv[o])

    if cnt == 1 or cnt == 3:
        # um vértice isolado (dentro se cnt==1, fora se cnt==3); as 3 arestas
        # que dele partem dão um triângulo.
        if cnt == 1:
            a = 0 if inside[0] else 1 if inside[1] else 2 if inside[2] else 3
        else:
            a = 0 if not inside[0] else 1 if not inside[1] else 2 if not inside[2] else 3
        others = [m for m in range(4) if m != a]
        out.append(E(a, others[0]))
        out.append(E(a, others[1]))
        out.append(E(a, others[2]))
    else:
        # dois dentro, dois fora → quadrilátero (2 triângulos). Ordem cíclica:
        # arestas consecutivas partilham um vértice do tetraedro, evitando o
        # «laço» (bowtie).
        ins = [m for m in range(4) if inside[m]]
        out_v = [m for m in range(4) if not inside[m]]
        a, b = ins
        c, d = out_v
        q0, q1, q2, q3 = E(a, c), E(a, d), E(b, d), E(b, c)
        out.append(q0); out.append(q1); out.append(q2)
        out.append(q0); out.append(q2); out.append(q3)


def _grad_normal(field, p, eps):
    x, y, z = p
    gx = field(x + eps, y, z) - field(x - eps, y, z)
    gy = field(x, y + eps, z) - field(x, y - eps, z)
    gz = field(x, y, z + eps) - field(x, y, z - eps)
    L = (gx * gx + gy * gy + gz * gz) ** 0.5
    if L < 1e-12:
        return (0.0, 1.0, 0.0)
    return (gx / L, gy / L, gz / L)   # ∇f aponta no sentido de f crescente (fora)


def polygonize(field, B, n, iso=0.0, grad_eps=None):
    """Devolve (verts, norms): duas listas paralelas de tuplos (x,y,z), onde
    cada 3 entradas consecutivas formam um triângulo da iso-superfície."""
    if grad_eps is None:
        grad_eps = B * 0.004
    n1 = n + 1
    coord = [(-B + 2.0 * B * i / n) for i in range(n1)]

    # 1) amostragem do campo nos nós da grade
    vals = [0.0] * (n1 * n1 * n1)
    idx = 0
    for i in range(n1):
        x = coord[i]
        for j in range(n1):
            y = coord[j]
            for k in range(n1):
                vals[idx] = field(x, y, coord[k])
                idx += 1

    def vidx(i, j, k):
        return (i * n1 + j) * n1 + k

    # 2) marchar pelas células
    raw = []
    cp = [None] * 8
    cv = [0.0] * 8
    pp = [None] * 4
    vv = [0.0] * 4
    for i in range(n):
        for j in range(n):
            for k in range(n):
                for c in range(8):
                    dx, dy, dz = _CORNERS[c]
                    ii, jj, kk = i + dx, j + dy, k + dz
                    cp[c] = (coord[ii], coord[jj], coord[kk])
                    cv[c] = vals[vidx(ii, jj, kk)]
                for (a, b, c, d) in _TETS:
                    pp[0], pp[1], pp[2], pp[3] = cp[a], cp[b], cp[c], cp[d]
                    vv[0], vv[1], vv[2], vv[3] = cv[a], cv[b], cv[c], cv[d]
                    _march_tet(iso, pp, vv, raw)

    # 3) normais por gradiente + 4) orientação coerente (normal da face alinhada
    #    com ∇f, isto é, virada para fora)
    verts = []
    norms = []
    for t in range(0, len(raw), 3):
        p0, p1, p2 = raw[t], raw[t + 1], raw[t + 2]
        n0 = _grad_normal(field, p0, grad_eps)
        n1n = _grad_normal(field, p1, grad_eps)
        n2 = _grad_normal(field, p2, grad_eps)
        ux, uy, uz = p1[0] - p0[0], p1[1] - p0[1], p1[2] - p0[2]
        wx, wy, wz = p2[0] - p0[0], p2[1] - p0[1], p2[2] - p0[2]
        fx = uy * wz - uz * wy
        fy = uz * wx - ux * wz
        fz = ux * wy - uy * wx
        avx = n0[0] + n1n[0] + n2[0]
        avy = n0[1] + n1n[1] + n2[1]
        avz = n0[2] + n1n[2] + n2[2]
        if fx * avx + fy * avy + fz * avz < 0.0:
            p1, p2 = p2, p1
            n1n, n2 = n2, n1n
        verts.append(p0); verts.append(p1); verts.append(p2)
        norms.append(n0); norms.append(n1n); norms.append(n2)
    return verts, norms


def edges_from_tris(verts):
    """Arestas únicas dos triângulos (para o aramado). Funde vértices por
    coordenada arredondada."""
    def key(p):
        return (round(p[0], 2), round(p[1], 2), round(p[2], 2))
    seen = set()
    out = []
    for t in range(0, len(verts), 3):
        tri = (verts[t], verts[t + 1], verts[t + 2])
        ks = (key(tri[0]), key(tri[1]), key(tri[2]))
        for a, b in ((0, 1), (1, 2), (2, 0)):
            ka, kb = ks[a], ks[b]
            ek = (ka, kb) if ka <= kb else (kb, ka)
            if ek in seen:
                continue
            seen.add(ek)
            pa, pb = tri[a], tri[b]
            out.append((pa[0], pa[1], pa[2], pb[0], pb[1], pb[2]))
    return out
