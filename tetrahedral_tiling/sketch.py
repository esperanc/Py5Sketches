"""
Decomposição do espaço em tetraedros — quatro alternativas.

Como dividir uma malha cúbica em tetraedros? O «select» da GUI alterna entre
quatro respostas clássicas, cada uma com o seu compromisso:

  6 tetraedros (Kuhn)   Divisão simples em torno de uma diagonal. Os 6 tets
                        são orthoschemes (arestas 1, √2, √3) — irregulares,
                        mas fáceis de gerar e consistentes entre cubos. É a
                        base da poligonização «marching tetrahedra».

  5 tetraedros          1 tet central regular (arestas √2, ótimo) + 4 de canto
                        irregulares. Para encaixar, cubos vizinhos têm de ser
                        espelhados → com «repetições = 2» vê-se o xadrez de
                        variantes A/B. O central regular aparece a dourado.

  24 — Lattice BCC      Adiciona-se um ponto no centro do cubo e liga-se aos
                        centros e arestas das 6 faces: 24 tets congruentes por
                        cubo, malha perfeitamente periódica. A escolha dominante
                        na prática (boa condição numérica em qualquer resolução).

  Sommerville           A joia teórica: um único tetraedro (disfenoide) que
                        preenche o espaço sozinho, sem espelhamento — só
                        rotações e translações. Emerge da decomposição BCC
                        (favo de Delaunay). Arestas s, s e quatro s·√3/2.

  faces / arestas       O que desenhar.
  opacidade             Transparência das faces — semitransparentes para ver
                        o interior.
  explodir              Vista explodida: afasta cada tet do centro, revelando
                        os detalhes internos da decomposição.
  repetições            1 ou 2 cubos por eixo (mostra a periodicidade / o
                        espelhamento).
  girar                 Rotação automática lenta (combina com arrastar/órbita).

  Arrastar              orbit_control (orbitar / zoom).
  s / S                 guarda PNG.
"""

import tetra as T
from gui import GuiBlock

# ── Estado global ────────────────────────────────────────────────────────────
gui       = None
hud_el    = None
_cam_init = False

S         = 130.0          # lado do cubo em unidades de mundo
prepared  = []             # [(verts, centroide, hue, destaque?), ...]
_key      = None           # (modo, repetições) — recalcula só quando muda
n_cubes   = 1

# Faces e arestas de um tetraedro (índices nos 4 vértices).
TRI = [(0, 1, 2), (0, 1, 3), (0, 2, 3), (1, 2, 3)]
EDG = [(0, 1), (0, 2), (0, 3), (1, 2), (1, 3), (2, 3)]

MODES = {
    "6 tetraedros":     "6",
    "5 tetraedros":     "5",
    "24 — Lattice BCC": "24",
    "Sommerville":      "somm",
}
MODE_NAMES = list(MODES.keys())


# ── Construção da geometria ──────────────────────────────────────────────────
def rebuild():
    """(Re)calcula a decomposição quando o modo ou as repetições mudam."""
    global prepared, _key, n_cubes

    mode = MODES[gui.decomposicao]
    n = int(gui.repeticoes)
    key = (mode, n)
    if key == _key:
        return
    _key = key
    n_cubes = n

    # Mantém a extensão total constante (~S) qualquer que seja o nº de cubos,
    # para o enquadramento da câmara não mudar entre repetições = 1 e 2.
    s_eff = S / n
    tets, highlights = T.build(mode, n, s_eff)
    prepared = []
    for idx, t in enumerate(tets):
        cx = (t[0][0] + t[1][0] + t[2][0] + t[3][0]) / 4.0
        cy = (t[0][1] + t[1][1] + t[2][1] + t[3][1]) / 4.0
        cz = (t[0][2] + t[1][2] + t[2][2] + t[3][2]) / 4.0
        hue = (idx * 37) % 360
        prepared.append((t, (cx, cy, cz), hue, idx in highlights))


# ── Setup / GUI ──────────────────────────────────────────────────────────────
def setup():
    global gui, hud_el

    create_canvas(window_width, window_height, WEBGL)

    GuiBlock.labelWidth = "7em"
    gui = GuiBlock()
    gui.addSelect("decomposicao", MODE_NAMES, "24 — Lattice BCC")
    gui.addCheckbox("faces", True)
    gui.addCheckbox("arestas", True)
    gui.addNumber("opacidade", 20, 200, 85, 5)
    gui.addNumber("explodir", 0.0, 1.5, 0.0, 0.05)
    gui.addNumber("repeticoes", 1, 2, 1, 1)
    gui.addCheckbox("girar", False)

    hud_el = create_div('')
    hud_el.position(10, window_height - 78)
    hud_el.style('color',          'rgba(190, 214, 244, 0.96)')
    hud_el.style('font-family',    'monospace')
    hud_el.style('font-size',      '13px')
    hud_el.style('line-height',    '1.55')
    hud_el.style('pointer-events', 'none')
    hud_el.style('text-shadow',    '0 1px 3px rgba(0,0,0,0.85)')
    hud_el.style('white-space',    'pre')


def key_pressed():
    if key in 'sS':
        save("tetrahedral_tiling.png")


# ── Desenho ──────────────────────────────────────────────────────────────────
def draw():
    global _cam_init

    color_mode(RGB, 255)
    background(18, 22, 32)

    if not _cam_init:
        camera(0, -250, 640, 0, 0, 0, 0, 1, 0)
        _cam_init = True

    orbit_control()
    rebuild()

    if gui.girar:
        rotate_y(frame_count * 0.005)
        rotate_x(frame_count * 0.0017)

    k = float(gui.explodir)
    opac = float(gui.opacidade)

    color_mode(HSB, 360, 100, 100, 255)

    if gui.faces:
        _draw_faces(k, opac)
    if gui.arestas:
        if gui.faces:
            _depth_prepass(k)        # popula o z-buffer com as faces
        _draw_edges(k)               # arestas ocludidas pelas faces

    update_hud()


# ── Transparência ────────────────────────────────────────────────────────────
# Faces translúcidas exigem cuidado com o z-buffer: se escrevem profundidade,
# ocluem-se umas às outras e o alpha-compositing fica errado. Por isso desativa-
# se a *escrita* de profundidade (depthMask false) e ordenam-se os tets de trás
# para frente (algoritmo do pintor); dentro de cada tet ordenam-se também os 4
# triângulos. No fim restaura-se depthMask(true) para o clear do próximo frame
# limpar o z-buffer corretamente.
#
# As arestas têm de respeitar a profundidade (não atravessar as faces). Como as
# faces de cor não escrevem profundidade, faz-se um *depth pre-pass*: redesenham-
# se as faces apenas para o z-buffer (cor desligada) e só então as arestas, com
# teste de profundidade LEQUAL (as arestas são coincidentes com as faces, logo
# precisam de passar no «igual»). Assim cada tet mostra o seu aramado da frente
# e esconde as arestas tapadas pelas faces — em vez do efeito raio-x.

_gl = None


def _gl_ctx():
    global _gl
    if _gl is None:
        _gl = P5._renderer.GL
    return _gl


def _mv_zrow():
    """Linha-z da matriz model-view (view · model) — dá a profundidade de olho
    z = a·x + b·y + c·z + d de qualquer ponto, para ordenar de trás para frente."""
    v = list(P5._renderer.uViewMatrix.mat4)      # column-major 4×4
    m = list(P5._renderer.uModelMatrix.mat4)
    vr = (v[2], v[6], v[10], v[14])              # linha 2 da view
    row = []
    for kk in range(4):
        b = kk * 4
        row.append(vr[0] * m[b] + vr[1] * m[b + 1]
                   + vr[2] * m[b + 2] + vr[3] * m[b + 3])
    return row


def _emit_tet(verts, ox, oy, oz, row):
    """Emite os 4 triângulos de um tet; se `row` dado, de trás para frente."""
    tris = TRI
    if row is not None:
        a, b, c, d = row

        def tdepth(tri):
            p0, p1, p2 = verts[tri[0]], verts[tri[1]], verts[tri[2]]
            sx = (p0[0] + p1[0] + p2[0]) / 3.0 + ox
            sy = (p0[1] + p1[1] + p2[1]) / 3.0 + oy
            sz = (p0[2] + p1[2] + p2[2]) / 3.0 + oz
            return a * sx + b * sy + c * sz + d
        tris = sorted(TRI, key=tdepth)
    begin_shape(TRIANGLES)
    for tri in tris:
        for vi in tri:
            p = verts[vi]
            vertex(p[0] + ox, p[1] + oy, p[2] + oz)
    end_shape()


def _draw_faces(k, opac):
    gl = _gl_ctx()
    no_stroke()

    # Compositing correto: ordena os tets pela profundidade do centróide
    # (já considerando a explosão, que afasta o centróide por um fator 1+k).
    row = _mv_zrow()
    a, b, c, d = row
    ex = 1.0 + k

    def cdepth(i):
        cen = prepared[i][1]
        return a * cen[0] * ex + b * cen[1] * ex + c * cen[2] * ex + d

    order = sorted(range(len(prepared)), key=cdepth)

    gl.depthMask(False)
    for i in order:
        verts, cen, hue, hi = prepared[i]
        ox, oy, oz = cen[0] * k, cen[1] * k, cen[2] * k
        if hi:
            fill(45, 80, 100, min(opac + 55, 255))
        else:
            fill(hue, 55, 95, opac)
        _emit_tet(verts, ox, oy, oz, row)
    gl.depthMask(True)


def _depth_prepass(k):
    """Redesenha as faces apenas para o z-buffer (cor desligada), para as
    arestas seguintes poderem ser ocludidas. A ordem é irrelevante: o teste
    LESS mantém a profundidade mais próxima."""
    gl = _gl_ctx()
    gl.colorMask(False, False, False, False)
    no_stroke()
    fill(0)                                  # cor mascarada; só preenche o depth
    for verts, c, hue, hi in prepared:
        ox, oy, oz = c[0] * k, c[1] * k, c[2] * k
        _emit_tet(verts, ox, oy, oz, None)
    gl.colorMask(True, True, True, True)


def _draw_edges(k):
    gl = _gl_ctx()
    gl.depthFunc(gl.LEQUAL)                   # arestas coincidem com as faces
    no_fill()
    for verts, c, hue, hi in prepared:
        ox, oy, oz = c[0] * k, c[1] * k, c[2] * k
        if hi:
            stroke(45, 90, 100, 255)
            stroke_weight(2.2)
        else:
            stroke(hue, 60, 75, 210)
            stroke_weight(1.2)
        begin_shape(LINES)
        for a, b in EDG:
            pa, pb = verts[a], verts[b]
            vertex(pa[0] + ox, pa[1] + oy, pa[2] + oz)
            vertex(pb[0] + ox, pb[1] + oy, pb[2] + oz)
        end_shape()
    gl.depthFunc(gl.LESS)                     # restaura para o próximo frame


# ── HUD ──────────────────────────────────────────────────────────────────────
_DESC = {
    "6":    "6 tets/cubo · orthoschemes (1, √2, √3) · base do marching tetrahedra",
    "5":    "5 tets/cubo · 1 central regular (dourado) + 4 de canto · vizinhos espelhados",
    "24":   "24 tets/cubo congruentes · centro + faces · malha periódica (BCC)",
    "somm": "disfenoide de Sommerville · preenche o espaço sozinho, sem espelhar",
}


def update_hud():
    if hud_el is None:
        return
    mode = MODES[gui.decomposicao]
    total = len(prepared)
    if mode == 'somm':
        cubos = f"favo {n_cubes}×{n_cubes}×{n_cubes}"
    else:
        nc = n_cubes ** 3
        cubos = f"{n_cubes}×{n_cubes}×{n_cubes} = {nc} cubo(s)"
    hud_el.html(
        f"{gui.decomposicao}\n"
        f"{_DESC[mode]}\n"
        f"{cubos}   ·   {total} tetraedros   ·   explodir = {float(gui.explodir):g}"
    )
