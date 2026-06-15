"""
Decomposições do espaço em tetraedros.

Cada função devolve uma lista de *tets*; cada tet é uma lista de 4 pontos
(x, y, z) já em coordenadas de mundo. O resultado é sempre recentrado na
origem para que a vista explodida irradie a partir do meio e a órbita fique
centrada.

Quatro alternativas (ver docstring de sketch.py):

  '6'    cubo  → 6 tetraedros   (divisão simples / Kuhn — orthoschemes)
  '5'    cubo  → 5 tetraedros   (1 central regular + 4 de canto irregulares)
  '24'   cubo  → 24 tetraedros  (lattice BCC: centro + centros de face)
  'somm' favo de disfenoides    (tetraedro de Sommerville, preenche o espaço
                                 sozinho, emergindo da decomposição BCC)
"""

# ── Cubo unitário ────────────────────────────────────────────────────────────
# Ordem canônica dos 8 cantos (índices usados nas tabelas de decomposição).
CUBE = [
    (0, 0, 0), (1, 0, 0), (1, 1, 0), (0, 1, 0),   # base  z = 0
    (0, 0, 1), (1, 0, 1), (1, 1, 1), (0, 1, 1),   # topo  z = 1
]

# As 6 faces como quadriláteros (usadas pela decomposição BCC de 24 tets).
FACES = [
    (0, 1, 2, 3),   # z = 0
    (4, 5, 6, 7),   # z = 1
    (0, 1, 5, 4),   # y = 0
    (3, 2, 6, 7),   # y = 1
    (0, 3, 7, 4),   # x = 0
    (1, 2, 6, 5),   # x = 1
]

# Divisão de Kuhn em 6 tets, todos partilhando a diagonal principal 0–6.
DECOMP_6 = [
    (0, 1, 2, 6), (0, 2, 3, 6), (0, 3, 7, 6),
    (0, 7, 4, 6), (0, 4, 5, 6), (0, 5, 1, 6),
]

# Divisão em 5 tets. O 1.º tet de cada lista é o central regular (arestas √2).
# Duas variantes espelhadas: cubos vizinhos têm de alternar entre A e B para
# que as faces internas casem — daí o «xadrez» quando há repetição.
DECOMP_5_A = [
    (0, 2, 5, 7),                                   # central regular
    (0, 1, 2, 5), (0, 2, 3, 7), (0, 4, 5, 7), (2, 5, 6, 7),
]
DECOMP_5_B = [
    (1, 3, 4, 6),                                   # central regular
    (0, 1, 3, 4), (1, 2, 3, 6), (1, 4, 5, 6), (3, 4, 6, 7),
]


# ── Utilidades ───────────────────────────────────────────────────────────────
def _avg(points):
    n = len(points)
    sx = sy = sz = 0.0
    for x, y, z in points:
        sx += x; sy += y; sz += z
    return (sx / n, sy / n, sz / n)


def _corners(i, j, k, s, origin):
    """Os 8 cantos do cubo da célula (i, j, k), lado s, deslocado por origin."""
    ox, oy, oz = origin
    return [(ox + (i + dx) * s, oy + (j + dy) * s, oz + (k + dz) * s)
            for dx, dy, dz in CUBE]


def _from_table(table, corners):
    """Materializa uma tabela de índices num conjunto de tets de pontos."""
    return [[corners[a] for a in tet] for tet in table]


def _bcc_24(corners):
    """24 tets congruentes: liga o centro do cubo ao centro e às arestas de
    cada face. Faces partilhadas entre cubos vizinhos são subdivididas de
    forma idêntica dos dois lados → malha periódica e conforme."""
    c = _avg(corners)
    tets = []
    for f in FACES:
        fc = _avg([corners[x] for x in f])
        for e in range(4):
            a = corners[f[e]]
            b = corners[f[(e + 1) % 4]]
            tets.append([c, fc, a, b])
    return tets


def _recenter(tets):
    """Subtrai o centróide médio dos vértices para centrar tudo na origem."""
    pts = [p for t in tets for p in t]
    cx, cy, cz = _avg(pts)
    return [[(x - cx, y - cy, z - cz) for x, y, z in t] for t in tets]


# ── Favo de Sommerville (disfenoides do BCC) ─────────────────────────────────
# A tetraedralização de Delaunay da rede BCC preenche o espaço com cópias
# congruentes de um único tetraedro (um disfenoide): nenhum espelhamento é
# necessário, apenas rotações e translações — é a propriedade que torna o
# tetraedro de Sommerville a «joia» entre os preenchedores do espaço.
#
# Cada disfenoide tem uma aresta cantos–cantos (comprimento s) ao longo de um
# eixo e a aresta oposta centros–centros (também s) perpendicular a ela; as
# quatro arestas laterais medem s·√3/2. Em torno de cada aresta do reticulado
# de cantos há 4 disfenoides (a bipirâmide/octaedro local), e cada disfenoide
# é gerado por exatamente uma dessas arestas, pelo que o favo não tem lacunas
# nem sobreposições.
_RING = [                      # pares de centros opostos (Δ unitário num eixo)
    ((+0.5, +0.5), (-0.5, +0.5)),
    ((+0.5, -0.5), (-0.5, -0.5)),
    ((+0.5, +0.5), (+0.5, -0.5)),
    ((-0.5, +0.5), (-0.5, -0.5)),
]


def _sommerville(n, s):
    tets = []

    def P(x, y, z):
        return (x * s, y * s, z * s)

    for i in range(n):
        for j in range(n):
            for k in range(n):
                # aresta no eixo x: (i,j,k) → (i+1,j,k); centros em (i+½, j±½, k±½)
                c0, c1 = P(i, j, k), P(i + 1, j, k)
                for (dy0, dz0), (dy1, dz1) in _RING:
                    tets.append([c0, c1,
                                 P(i + 0.5, j + dy0, k + dz0),
                                 P(i + 0.5, j + dy1, k + dz1)])
                # aresta no eixo y
                c0, c1 = P(i, j, k), P(i, j + 1, k)
                for (dx0, dz0), (dx1, dz1) in _RING:
                    tets.append([c0, c1,
                                 P(i + dx0, j + 0.5, k + dz0),
                                 P(i + dx1, j + 0.5, k + dz1)])
                # aresta no eixo z
                c0, c1 = P(i, j, k), P(i, j, k + 1)
                for (dx0, dy0), (dx1, dy1) in _RING:
                    tets.append([c0, c1,
                                 P(i + dx0, j + dy0, k + 0.5),
                                 P(i + dx1, j + dy1, k + 0.5)])
    return tets


# ── API ──────────────────────────────────────────────────────────────────────
def build(mode, n, s):
    """Constrói (tets, highlights) para o modo dado, num arranjo n×n×n, lado s.

    `highlights` é o conjunto de índices a destacar (tet central regular nos
    de 5; «joia» nos de Sommerville)."""
    if mode == 'somm':
        return _recenter(_sommerville(n, s)), {0}

    tets = []
    highlights = set()
    origin = (-n * s / 2.0, -n * s / 2.0, -n * s / 2.0)
    for i in range(n):
        for j in range(n):
            for k in range(n):
                corners = _corners(i, j, k, s, origin)
                if mode == '6':
                    group = _from_table(DECOMP_6, corners)
                elif mode == '5':
                    mirror = (i + j + k) % 2 == 1
                    table = DECOMP_5_B if mirror else DECOMP_5_A
                    group = _from_table(table, corners)
                    highlights.add(len(tets))      # central = 1.º do grupo
                elif mode == '24':
                    group = _bcc_24(corners)
                else:
                    group = []
                tets.extend(group)
    return _recenter(tets), highlights
