"""
Superfícies de subdivisão de produto tensorial — extensões 3D dos esquemas
de curva Lane-Riesenfeld e 4-pontos (DLG) de smooth_curves.py.

Ideia central: aplicar o esquema de curva em cada LINHA da grade (direção
v), transpor, aplicar de novo (direção u), transpor de volta.  Um passo de
subdivisão de superfície = dois passes de subdivisão de curva.
"""

# ─────────────────────────────────────────────────────────────────────────────
# Auxiliares de curva 3D
# ─────────────────────────────────────────────────────────────────────────────

def _lr_curve(pts, closed, degree):
    """Um passo de Lane-Riesenfeld numa lista de pontos [x, y, z]."""
    v = []
    if not closed:
        for _ in range(degree - 1):   # clamping: duplica os extremos
            v.append(pts[0])
    for p in pts:
        v.append(p)
        v.append(p)                    # duplicação
    n = len(v)

    def nxt(i):
        return (i + 1) % n if closed else min(n - 1, i + 1)

    for _ in range(degree):            # d médias consecutivas
        u = []
        for i in range(n):
            p, q = v[i], v[nxt(i)]
            u.append([(p[k] + q[k]) * 0.5 for k in range(3)])
        v = u
    return v


def _fp_curve(pts, closed, w):
    """Um passo do esquema de 4-pontos (DLG) numa lista de pontos [x, y, z]."""
    n = len(pts)

    def nxt(i):  return (i + 1) % n      if closed else min(n - 1, i + 1)
    def nxt2(i): return (i + 2) % n      if closed else min(n - 1, i + 2)
    def prv(i):  return (i + n - 1) % n  if closed else max(0, i - 1)

    v = []
    for i in range(n):
        nb = [pts[prv(i)], pts[i], pts[nxt(i)], pts[nxt2(i)]]
        q  = [-w * nb[0][k] + (0.5 + w) * nb[1][k]
              + (0.5 + w) * nb[2][k] - w * nb[3][k]
              for k in range(3)]
        v.append(pts[i])
        v.append(q)
    if not closed:
        v.pop()
    return v


# ─────────────────────────────────────────────────────────────────────────────
# Produto tensorial
# ─────────────────────────────────────────────────────────────────────────────

def _rowwise(grid, fn, closed, arg):
    """Aplica fn a cada linha da grade."""
    return [fn(row, closed, arg) for row in grid]


def _transpose(grid):
    """Transpõe uma grade 2D (troca índices linha/coluna)."""
    return [[grid[r][c] for r in range(len(grid))] for c in range(len(grid[0]))]


def lr_surface(grid, closed_u=False, closed_v=False, degree=2):
    """Um passo de Lane-Riesenfeld de produto tensorial numa grade 3D.

    grid[i][j] = [x, y, z]; i é a direção u, j é a direção v.
    """
    s = _rowwise(grid, _lr_curve, closed_v, degree)   # subdivide ao longo de v
    s = _transpose(s)
    s = _rowwise(s,    _lr_curve, closed_u, degree)   # subdivide ao longo de u
    return _transpose(s)


def four_point_surface(grid, closed_u=False, closed_v=False, w=0.06):
    """Um passo de 4-pontos (DLG) de produto tensorial numa grade 3D."""
    s = _rowwise(grid, _fp_curve, closed_v, w)        # subdivide ao longo de v
    s = _transpose(s)
    s = _rowwise(s,    _fp_curve, closed_u, w)        # subdivide ao longo de u
    return _transpose(s)
