"""
Subdivisão cumulativa de malhas sobre a estrutura half-edge.

Aplica-se um passo de Catmull-Clark, Doo-Sabin ou Loop sobre a malha
corrente — incluindo o resultado de outro algoritmo — clicando no botão
respetivo. «Limpar» volta ao sólido base; «Desfazer» remove o último passo.

O slider «deslocamento» (t) calibra quanto os vértices são movidos no
próximo passo: t=0 só refina a topologia (geometria intacta), t=1 é a regra
padrão do algoritmo, t>1 exagera a suavização.

  Botões (esq.) → solido, deslocamento, passos, exibição
  Arrastar      → orbit_control (orbitar / zoom)
"""

import half_edge as he
import subdivision as sub
from gui import GuiBlock

# ── Estado global ───────────────────────────────────────────────────────────
RADIUS = 200.0

base_mesh = None      # sólido base (nível 0)
history   = []        # pilha de malhas; a corrente é history[-1]
ops       = []        # rótulos dos passos aplicados, ex.: ["CC", "Loop·0.5"]
gui       = None
hud_el    = None
_cam_init = False
_dirty    = True      # geometria de desenho precisa de recálculo
_geom_key = None

# dados-fonte das geometrias (lidos pelos callbacks de build_geometry)
tris      = []        # [(x,y,z,nx,ny,nz), ...] em grupos de 3
wire      = []        # segmentos da malha subdividida
base_wire = []        # segmentos da malha base

# objetos p5.Geometry retidos em buffers de GPU
face_geom = None
wire_geom = None
base_geom = None
_face_proxy = None
_wire_proxy = None
_base_proxy = None

ABBR = {"Catmull-Clark": "CC", "Doo-Sabin": "DS", "Loop": "Loop"}

COL_FACE = (200, 208, 222)
COL_WIRE = (40, 60, 95)
COL_BASE = (255, 205, 70)


def cur_mesh():
    return history[-1]


# ── Operações ───────────────────────────────────────────────────────────────
def set_base():
    global base_mesh, history, ops, base_wire, _dirty
    base_mesh = he.build(gui.solido, RADIUS)
    history = [base_mesh]
    ops = []
    base_wire = edges_of(base_mesh)
    _dirty = True

def apply_algo(name):
    global _dirty
    t = float(gui.deslocamento)
    new = sub.ALGORITHMS[name](cur_mesh(), t)
    history.append(new)
    label = ABBR[name] if abs(t - 1.0) < 1e-9 else f"{ABBR[name]}·{t:g}"
    ops.append(label)
    _dirty = True

def clear_all():
    global history, ops, _dirty
    history = [base_mesh]
    ops = []
    _dirty = True

def undo():
    global _dirty
    if len(history) > 1:
        history.pop()
        ops.pop()
        _dirty = True


# ── Geometria de desenho ────────────────────────────────────────────────────
def edges_of(mesh):
    out = []
    seen = set()
    for h in mesh.halfedges:
        if h.is_boundary:
            continue
        a, b = h.origin.id, h.dest.id
        k = (a, b) if a < b else (b, a)
        if k in seen:
            continue
        seen.add(k)
        p0, p1 = h.origin.pos, h.dest.pos
        out.append((p0[0], p0[1], p0[2], p1[0], p1[1], p1[2]))
    return out

def vertex_normals(mesh):
    acc = {v.id: [0.0, 0.0, 0.0] for v in mesh.vertices}
    for f in mesh.faces:
        nx, ny, nz = f.normal()
        for v in f.vertices():
            a = acc[v.id]
            a[0] += nx; a[1] += ny; a[2] += nz
    out = {}
    for vid, a in acc.items():
        L = (a[0] ** 2 + a[1] ** 2 + a[2] ** 2) ** 0.5
        out[vid] = (a[0] / L, a[1] / L, a[2] / L) if L > 1e-9 else (0.0, 1.0, 0.0)
    return out

# ── callbacks de build_geometry (leem os dados-fonte globais) ───────────────
def _face_cb(*_):
    begin_shape(TRIANGLES)
    for (x, y, z, nx, ny, nz) in tris:
        normal(nx, ny, nz)
        vertex(x, y, z)
    end_shape()

def _wire_cb(*_):
    begin_shape(LINES)
    for (x0, y0, z0, x1, y1, z1) in wire:
        vertex(x0, y0, z0)
        vertex(x1, y1, z1)
    end_shape()

def _base_cb(*_):
    begin_shape(LINES)
    for (x0, y0, z0, x1, y1, z1) in base_wire:
        vertex(x0, y0, z0)
        vertex(x1, y1, z1)
    end_shape()

def _free(geom):
    if geom is not None:
        try:
            free_geometry(geom)
        except Exception:
            pass

def rebuild_geometry():
    """Recalcula os dados-fonte e (re)constrói os p5.Geometry em GPU.
    Só corre quando a malha corrente ou o sombreamento mudam — a partir daí,
    cada frame apenas emite model(), sem reenviar vértices para a GPU."""
    global tris, wire, _dirty, _geom_key
    global face_geom, wire_geom, base_geom
    smooth = bool(gui.suave)
    key = (len(history), id(cur_mesh()), smooth)
    if not _dirty and key == _geom_key:
        return
    _geom_key = key
    _dirty = False

    m = cur_mesh()
    vn = vertex_normals(m) if smooth else None
    tris = []
    for f in m.faces:
        fn = f.normal()
        verts = list(f.vertices())
        for i in range(1, len(verts) - 1):
            for vtx in (verts[0], verts[i], verts[i + 1]):
                n = vn[vtx.id] if smooth else fn
                tris.append((vtx.x, vtx.y, vtx.z, n[0], n[1], n[2]))
    wire = edges_of(m)

    # libertar os buffers antigos e construir os novos
    _free(face_geom)
    _free(wire_geom)
    _free(base_geom)
    face_geom = build_geometry(_face_proxy)
    wire_geom = build_geometry(_wire_proxy)
    base_geom = build_geometry(_base_proxy)


# ── Setup / GUI ─────────────────────────────────────────────────────────────
def setup():
    global gui, hud_el, _face_proxy, _wire_proxy, _base_proxy

    create_canvas(window_width, window_height, WEBGL)

    _face_proxy = create_proxy(_face_cb)
    _wire_proxy = create_proxy(_wire_cb)
    _base_proxy = create_proxy(_base_cb)

    GuiBlock.labelWidth = "6em"
    gui = GuiBlock()
    gui.addSelect("solido", he.SOLID_NAMES, "Cubo")
    gui.addNumber("deslocamento", 0.0, 2.0, 1.0, 0.05)
    gui.addCheckbox("faces", True)
    gui.addCheckbox("arame", True)
    gui.addCheckbox("suave", True)
    gui.addCheckbox("base", True)
    gui.change(on_gui_change)

    add_button("Catmull-Clark", lambda e: apply_algo("Catmull-Clark"))
    add_button("Doo-Sabin",     lambda e: apply_algo("Doo-Sabin"))
    add_button("Loop",          lambda e: apply_algo("Loop"))
    add_button("Desfazer",      lambda e: undo())
    add_button("Limpar",        lambda e: clear_all())

    set_base()

    hud_el = create_div('')
    hud_el.position(10, window_height - 70)
    hud_el.style('color',          'rgba(180, 208, 240, 0.96)')
    hud_el.style('font-family',    'monospace')
    hud_el.style('font-size',      '13px')
    hud_el.style('line-height',    '1.55')
    hud_el.style('pointer-events', 'none')
    hud_el.style('text-shadow',    '0 1px 3px rgba(0,0,0,0.85)')
    hud_el.style('white-space',    'pre')

_prev_solid = ["Cubo"]
def on_gui_change():
    # mudar de sólido reinicia a pilha; outras mudanças (ex.: 'suave') só
    # marcam a geometria como suja.
    global _dirty
    if gui.solido != _prev_solid[0]:
        _prev_solid[0] = gui.solido
        set_base()
    else:
        _dirty = True

def add_button(label, fn):
    b = create_button(label)
    b.parent(gui.div)
    b.style("margin", "2px 4px 2px 0")
    b.style("font", GuiBlock.font)
    b.mousePressed(create_proxy(fn))
    return b


# ── Desenho ─────────────────────────────────────────────────────────────────
def draw():
    global _cam_init

    background(20, 26, 38)

    if not _cam_init:
        camera(0, -230, 560, 0, 0, 0, 0, 1, 0)
        _cam_init = True

    orbit_control()
    rebuild_geometry()

    ambient_light(55, 62, 78)
    directional_light(205, 220, 255, -0.4, 1.0, -0.5)
    directional_light(80, 105, 175, 0.5, -0.6, 0.7)

    if gui.faces and face_geom is not None:
        no_stroke()
        fill(COL_FACE[0], COL_FACE[1], COL_FACE[2])
        model(face_geom)

    if gui.arame and wire_geom is not None:
        no_fill()
        a = 150 if gui.faces else 220
        stroke(COL_WIRE[0], COL_WIRE[1], COL_WIRE[2], a)
        stroke_weight(1)
        model(wire_geom)

    if gui.base and base_geom is not None:
        no_fill()
        stroke(COL_BASE[0], COL_BASE[1], COL_BASE[2], 200)
        stroke_weight(2)
        model(base_geom)

    update_hud()


def update_hud():
    if hud_el is None or not history:
        return
    m = cur_mesh()
    seq = " → ".join(ops) if ops else "(sem subdivisão)"
    topo = "fechada" if m.is_closed else \
        f"aberta · {len(m.boundary)} arestas de bordo"
    hud_el.html(
        f"base: {gui.solido}   passos ({len(ops)}): {seq}\n"
        f"malha  V={m.n_vertices}  E={m.n_edges}  F={m.n_faces}"
        f"   Euler={m.euler()}   ({topo})\n"
        f"deslocamento do próximo passo: t={float(gui.deslocamento):g}"
    )
