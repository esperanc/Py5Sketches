"""
Marching tetrahedra — extração de iso-superfícies de campos implícitos.

Escolhe-se um campo escalar f(x,y,z) num select e a iso-superfície f = nível
é poligonizada, dividindo cada célula da grade de amostragem em 6 tetraedros
(variante simplicial, sem ambiguidades, do marching cubes).

  GUI (esq.)
    campo       → função implícita a visualizar
    resolução   → nº de células da grade por eixo (custo ∝ resolução³)
    nível       → iso-valor; desloca a superfície para dentro/fora
    faces/arame/caixa/normais → o que desenhar
  Arrastar      → orbit_control (orbitar / zoom)

A geometria é calculada em Python e guardada em buffers de GPU (p5.Geometry,
via build_geometry); só é recalculada quando campo, resolução ou nível mudam.
"""

import fields as F
import marching as mc
from gui import GuiBlock

# ── Estado global ───────────────────────────────────────────────────────────
gui       = None
hud_el    = None
_cam_init = False
_dirty    = True
_geom_key = None

B         = 185.0     # meia-extensão da caixa do campo corrente
tris_v    = []        # vértices dos triângulos (grupos de 3)
tris_n    = []        # normais correspondentes
wire      = []        # segmentos do aramado

face_geom = None
wire_geom = None
box_geom  = None
_face_proxy = None
_wire_proxy = None
_box_proxy  = None

COL_FACE = (150, 196, 224)
COL_WIRE = (28, 44, 70)
COL_BOX  = (255, 205, 70)
COL_NORM = (120, 235, 170)


# ── callbacks de build_geometry (leem os dados-fonte globais) ───────────────
# Os vértices são emitidos em lotes: cada end_shape tesselado pelo p5 usa
# operações que rebentam a pilha de chamadas para arrays muito grandes, pelo
# que se fatiam as malhas densas em vários shapes (o build_geometry funde-os
# todos numa só geometria).
_CHUNK = 3000

def _face_cb(*_):
    no_stroke()   # sem stroke o p5 não gera as arestas (mais leve e seguro)
    vs, ns = tris_v, tris_n
    nverts = len(vs)
    i = 0
    while i < nverts:
        end = min(i + _CHUNK, nverts)
        end -= (end - i) % 3            # mantém triângulos completos
        begin_shape(TRIANGLES)
        for j in range(i, end):
            n = ns[j]
            p = vs[j]
            normal(n[0], n[1], n[2])
            vertex(p[0], p[1], p[2])
        end_shape()
        i = end

def _wire_cb(*_):
    nseg = len(wire)
    i = 0
    step = _CHUNK // 2
    while i < nseg:
        end = min(i + step, nseg)
        begin_shape(LINES)
        for j in range(i, end):
            x0, y0, z0, x1, y1, z1 = wire[j]
            vertex(x0, y0, z0)
            vertex(x1, y1, z1)
        end_shape()
        i = end

def _box_cb(*_):
    b = B
    c = [(-b, -b, -b), (b, -b, -b), (b, b, -b), (-b, b, -b),
         (-b, -b, b), (b, -b, b), (b, b, b), (-b, b, b)]
    e = [(0, 1), (1, 2), (2, 3), (3, 0),
         (4, 5), (5, 6), (6, 7), (7, 4),
         (0, 4), (1, 5), (2, 6), (3, 7)]
    begin_shape(LINES)
    for a, d in e:
        vertex(c[a][0], c[a][1], c[a][2])
        vertex(c[d][0], c[d][1], c[d][2])
    end_shape()

def _free(geom):
    if geom is not None:
        try:
            free_geometry(geom)
        except Exception:
            pass


def rebuild_geometry():
    """Recalcula a iso-superfície e (re)constrói os p5.Geometry em GPU. Só roda
    quando campo, resolução ou nível mudam."""
    global tris_v, tris_n, wire, B, _dirty, _geom_key
    global face_geom, wire_geom, box_geom

    name = gui.campo
    res = int(gui.resolucao)
    level = float(gui.nivel)
    want_wire = bool(gui.arame)
    key = (name, res, round(level, 4), want_wire)
    if not _dirty and key == _geom_key:
        return
    _geom_key = key
    _dirty = False

    func, B = F.FIELDS[name]
    tris_v, tris_n = mc.polygonize(func, B, res, iso=level)
    wire = mc.edges_from_tris(tris_v) if want_wire else []

    _free(face_geom)
    _free(wire_geom)
    _free(box_geom)
    face_geom = build_geometry(_face_proxy)
    wire_geom = build_geometry(_wire_proxy) if wire else None
    box_geom = build_geometry(_box_proxy)


# ── Setup / GUI ─────────────────────────────────────────────────────────────
def setup():
    global gui, hud_el, _face_proxy, _wire_proxy, _box_proxy

    create_canvas(window_width, window_height, WEBGL)

    _face_proxy = create_proxy(_face_cb)
    _wire_proxy = create_proxy(_wire_cb)
    _box_proxy = create_proxy(_box_cb)

    GuiBlock.labelWidth = "6em"
    gui = GuiBlock()
    gui.addSelect("campo", F.FIELD_NAMES, "Toro")
    gui.addNumber("resolucao", 8, 56, 28, 2)
    gui.addNumber("nivel", -0.9, 0.9, 0.0, 0.05)
    gui.addCheckbox("faces", True)
    gui.addCheckbox("arame", False)
    gui.addCheckbox("caixa", True)
    gui.addCheckbox("normais", False)
    gui.change(on_gui_change)
    
    hud_el = create_div('')
    hud_el.position(10, window_height - 70)
    hud_el.style('color',          'rgba(180, 208, 240, 0.96)')
    hud_el.style('font-family',    'monospace')
    hud_el.style('font-size',      '13px')
    hud_el.style('line-height',    '1.55')
    hud_el.style('pointer-events', 'none')
    hud_el.style('text-shadow',    '0 1px 3px rgba(0,0,0,0.85)')
    hud_el.style('white-space',    'pre')


def on_gui_change():
    global _dirty
    _dirty = True

# -- Teclado --------------
def key_pressed():
    if key in 'sS':
        save("marching.png")
        

# ── Desenho ─────────────────────────────────────────────────────────────────
def draw():
    global _cam_init

    background(20, 26, 38)

    if not _cam_init:
        camera(0, -240, 560, 0, 0, 0, 0, 1, 0)
        _cam_init = True

    orbit_control()
    rebuild_geometry()

    ambient_light(58, 64, 80)
    directional_light(205, 220, 255, -0.4, 1.0, -0.5)
    directional_light(80, 105, 175, 0.5, -0.6, 0.7)

    if gui.faces and face_geom is not None:
        push()
        no_stroke()
        ambient_material(COL_FACE[0], COL_FACE[1], COL_FACE[2])
        model(face_geom)
        pop()

    if gui.arame and wire_geom is not None:
        no_fill()
        a = 150 if gui.faces else 220
        stroke(COL_WIRE[0], COL_WIRE[1], COL_WIRE[2], a)
        stroke_weight(1)
        model(wire_geom)

    if gui.caixa and box_geom is not None:
        no_fill()
        stroke(COL_BOX[0], COL_BOX[1], COL_BOX[2], 150)
        stroke_weight(1.5)
        model(box_geom)

    if gui.normais:
        draw_normals()

    update_hud()


def draw_normals():
    no_fill()
    stroke(COL_NORM[0], COL_NORM[1], COL_NORM[2], 180)
    stroke_weight(1)
    L = 16.0
    vs, ns = tris_v, tris_n
    # uma normal por triângulo (no 1.º vértice) para não saturar a tela
    for i in range(0, len(vs), 3):
        p = vs[i]
        n = ns[i]
        line(p[0], p[1], p[2],
             p[0] + n[0] * L, p[1] + n[1] * L, p[2] + n[2] * L)


def update_hud():
    if hud_el is None:
        return
    res = int(gui.resolucao)
    ntri = len(tris_v) // 3
    cells = res * res * res
    hud_el.html(
        f"campo: {gui.campo}      nível f = {float(gui.nivel):g}\n"
        f"grade  {res}×{res}×{res} = {cells} células  ({cells * 6} tetraedros)"
        f"      caixa [-{B:g}, {B:g}]³\n"
        f"iso-superfície:  {ntri} triângulos   (marching tetrahedra)"
    )
