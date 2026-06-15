"""
Estrutura de dados half-edge (DCEL) — visualização interativa.

  GUI (esq.)        → sólido, circulador, e botões Next / Prev / Twin
  N / P / T         → operadores next / prev / twin sobre a half-edge corrente
  R                 → repõe a half-edge corrente
  Arrastar          → orbit_control (orbitar / zoom)

A half-edge corrente é desenhada como uma flecha vermelha. O circulador de
face mostra o anel da face (ciano); o de vértice mostra as half-edges que
partem do vértice (verde). Em malhas abertas as arestas de bordo são
destacadas a laranja e as half-edges de bordo aparecem tracejadas.
"""

import half_edge as he
from gui import GuiBlock

# ── Estado global ───────────────────────────────────────────────────────────
RADIUS = 200.0

mesh      = None
cur       = None          # half-edge corrente
gui       = None
hud_el    = None
_cam_init = False

COL_FACE   = (205, 212, 224)
COL_WIRE   = (90, 120, 165)
COL_BORDER = (255, 150, 40)
COL_CUR    = (240, 55, 55)
COL_RING   = (60, 210, 230)     # circulador de face
COL_FAN    = (90, 230, 120)     # circulador de vértice


# ── Helpers vetoriais (Python puro, sem p5) ─────────────────────────────────
def v_lerp(a, b, t):
    return (a[0] + (b[0] - a[0]) * t,
            a[1] + (b[1] - a[1]) * t,
            a[2] + (b[2] - a[2]) * t)

def v_sub(a, b):
    return (a[0] - b[0], a[1] - b[1], a[2] - b[2])

def v_add(a, b):
    return (a[0] + b[0], a[1] + b[1], a[2] + b[2])

def v_scale(a, s):
    return (a[0] * s, a[1] * s, a[2] * s)

def v_dot(a, b):
    return a[0] * b[0] + a[1] * b[1] + a[2] * b[2]

def v_len(a):
    return (a[0] * a[0] + a[1] * a[1] + a[2] * a[2]) ** 0.5

def v_unit(a):
    L = v_len(a)
    return (a[0] / L, a[1] / L, a[2] / L) if L > 1e-9 else (0.0, 0.0, 0.0)


# ── GUI / setup ─────────────────────────────────────────────────────────────
_solid_cache = [None]

def rebuild():
    global mesh, cur
    mesh = he.build(gui.solido, RADIUS)
    cur  = mesh.first_interior_halfedge()

def setup():
    global gui, hud_el

    create_canvas(window_width, window_height, WEBGL)

    GuiBlock.labelWidth = "6em"
    gui = GuiBlock()
    gui.addSelect("solido",     he.SOLID_NAMES, he.SOLID_NAMES[1])
    gui.addSelect("circulador", ["nenhum", "face", "vertice"], "face")
    gui.addCheckbox("faces", True)
    gui.addCheckbox("arame", True)
    gui.addCheckbox("bordas", True)
    gui.change(_handle_change)

    add_button("◀ prev (P)", lambda e: op_prev())
    add_button("twin (T)",   lambda e: op_twin())
    add_button("next (N) ▶", lambda e: op_next())

    rebuild()
    _solid_cache[0] = gui.solido

    hud_el = create_div('')
    hud_el.position(10, window_height - 92)
    hud_el.style('color',          'rgba(180, 208, 240, 0.96)')
    hud_el.style('font-family',    'monospace')
    hud_el.style('font-size',      '13px')
    hud_el.style('line-height',    '1.55')
    hud_el.style('pointer-events', 'none')
    hud_el.style('text-shadow',    '0 1px 3px rgba(0,0,0,0.85)')
    hud_el.style('white-space',    'pre')


def _handle_change():
    global cur
    if gui.solido != _solid_cache[0]:
        rebuild()
        _solid_cache[0] = gui.solido


def add_button(label, fn):
    b = create_button(label)
    b.parent(gui.div)
    b.style("margin", "2px 4px 2px 0")
    b.style("font", GuiBlock.font)
    b.mousePressed(create_proxy(fn))
    return b


# ── Operadores de navegação ─────────────────────────────────────────────────
def op_next():
    global cur
    if cur is not None:
        cur = cur.next

def op_prev():
    global cur
    if cur is not None:
        cur = cur.prev

def op_twin():
    global cur
    if cur is not None:
        cur = cur.twin

def key_pressed():
    global cur
    if key in ('n', 'N'):
        op_next()
    elif key in ('p', 'P'):
        op_prev()
    elif key in ('t', 'T'):
        op_twin()
    elif key in ('r', 'R'):
        cur = mesh.first_interior_halfedge()


# ── Desenho de uma half-edge como flecha ────────────────────────────────────
def he_endpoints(h, inset=0.16, lift=2.5):
    """Devolve (a0, a1, normal) da flecha — encolhida para o centro da face
    e elevada ao longo da normal para não brigar com a superfície."""
    p0 = h.origin.pos
    p1 = h.dest.pos
    face = h.face if h.face is not None else h.twin.face
    c = face.centroid
    n = face.normal()
    off = v_scale(n, lift)
    a0 = v_add(v_lerp(p0, c, inset), off)
    a1 = v_add(v_lerp(p1, c, inset), off)
    return a0, a1, n

def draw_arrow(h, col, weight, dashed=False):
    a0, a1, n = he_endpoints(h)
    d = v_sub(a1, a0)
    L = v_len(d)
    if L < 1e-6:
        return
    du = v_scale(d, 1.0 / L)

    stroke(col[0], col[1], col[2])
    stroke_weight(weight)
    no_fill()

    if dashed:
        seg = 9.0
        steps = max(1, int(L / seg))
        for i in range(0, steps, 2):
            s0 = v_add(a0, v_scale(du, i * seg))
            s1 = v_add(a0, v_scale(du, min((i + 1) * seg, L)))
            line(s0[0], s0[1], s0[2], s1[0], s1[1], s1[2])
    else:
        line(a0[0], a0[1], a0[2], a1[0], a1[1], a1[2])

    # cabeça da flecha — duas barbas no plano (du, perp) da face
    perp = v_unit((du[1] * n[2] - du[2] * n[1],
                   du[2] * n[0] - du[0] * n[2],
                   du[0] * n[1] - du[1] * n[0]))
    hl = min(22.0, L * 0.3)
    hw = hl * 0.55
    base = v_sub(a1, v_scale(du, hl))
    b1 = v_add(base, v_scale(perp, hw))
    b2 = v_sub(base, v_scale(perp, hw))
    line(a1[0], a1[1], a1[2], b1[0], b1[1], b1[2])
    line(a1[0], a1[1], a1[2], b2[0], b2[1], b2[2])

    # marca da cauda (origem)
    push()
    translate(a0[0], a0[1], a0[2])
    no_stroke()
    fill(col[0], col[1], col[2])
    sphere(weight * 1.6)
    pop()


# ── Desenho ─────────────────────────────────────────────────────────────────
def draw():
    global _cam_init

    background(20, 26, 38)

    if not _cam_init:
        camera(0, -240, 560, 0, 0, 0, 0, 1, 0)
        _cam_init = True

    orbit_control()

    ambient_light(55, 62, 78)
    directional_light(200, 215, 255, -0.4, 1.0, -0.5)
    directional_light(80, 105, 175, 0.5, -0.6, 0.7)

    if gui.faces:
        draw_faces()

    if gui.arame:
        draw_wireframe()

    if gui.bordas:
        draw_borders()

    # ── circulador (anel de face ou leque de vértice) ──
    # nota: a half-edge corrente é saltada aqui — será desenhada já a seguir
    # como flecha vermelha, evitando duas flechas sobrepostas (z-fighting).
    if gui.circulador == "face" and cur is not None:
        face = cur.face if cur.face is not None else cur.twin.face
        highlight_face(face)
        for h in face.circulate():
            if h is cur:
                continue
            draw_arrow(h, COL_RING, 4, dashed=h.is_boundary)
    elif gui.circulador == "vertice" and cur is not None:
        v = cur.origin
        highlight_vertex(v)
        for h in v.outgoing():
            if h is cur:
                continue
            draw_arrow(h, COL_FAN, 4, dashed=h.is_boundary)

    # ── half-edge corrente (vermelha, por cima) ──
    if cur is not None:
        draw_arrow(cur, COL_CUR, 6, dashed=cur.is_boundary)

    update_hud()


def draw_faces():
    no_stroke()
    fill(COL_FACE[0], COL_FACE[1], COL_FACE[2])
    for f in mesh.faces:
        n = f.normal()
        verts = list(f.vertices())
        begin_shape(TRIANGLES)
        normal(n[0], n[1], n[2])
        for i in range(1, len(verts) - 1):
            for vtx in (verts[0], verts[i], verts[i + 1]):
                vertex(vtx.x, vtx.y, vtx.z)
        end_shape()


def draw_wireframe():
    no_fill()
    stroke(COL_WIRE[0], COL_WIRE[1], COL_WIRE[2], 150)
    stroke_weight(1)
    seen = set()
    for h in mesh.halfedges:
        if h.is_boundary:
            continue
        a = h.origin.id
        b = h.dest.id
        key = (a, b) if a < b else (b, a)
        if key in seen:
            continue
        seen.add(key)
        p0 = h.origin.pos
        p1 = h.dest.pos
        line(p0[0], p0[1], p0[2], p1[0], p1[1], p1[2])


def draw_borders():
    if mesh.is_closed:
        return
    no_fill()
    stroke(COL_BORDER[0], COL_BORDER[1], COL_BORDER[2])
    stroke_weight(3.5)
    for be in mesh.boundary:
        p0 = be.origin.pos
        p1 = be.dest.pos
        line(p0[0], p0[1], p0[2], p1[0], p1[1], p1[2])


def highlight_face(face):
    n = face.normal()
    off = v_scale(n, 1.5)
    verts = [v_add(v.pos, off) for v in face.vertices()]
    no_stroke()
    fill(COL_RING[0], COL_RING[1], COL_RING[2], 70)
    begin_shape(TRIANGLES)
    normal(n[0], n[1], n[2])
    for i in range(1, len(verts) - 1):
        for vtx in (verts[0], verts[i], verts[i + 1]):
            vertex(vtx[0], vtx[1], vtx[2])
    end_shape()


def highlight_vertex(v):
    push()
    translate(v.x, v.y, v.z)
    no_stroke()
    emissive_material(0, 90, 40)
    fill(COL_FAN[0], COL_FAN[1], COL_FAN[2])
    sphere(9)
    emissive_material(0, 0, 0)
    pop()


# ── HUD ─────────────────────────────────────────────────────────────────────
def update_hud():
    if hud_el is None or mesh is None or cur is None:
        return
    face_lbl = "BORDA" if cur.is_boundary else f"f{cur.face.id}"
    twin = cur.twin
    twin_face = "BORDA" if twin.is_boundary else f"f{twin.face.id}"
    topo = "fechada" if mesh.is_closed else f"aberta · {len(mesh.boundary)} arestas de bordo"

    hud_el.html(
        f"{gui.solido}   V={mesh.n_vertices}  E={mesh.n_edges}  "
        f"F={mesh.n_faces}   Euler={mesh.euler()}   ({topo})\n"
        f"half-edge corrente  he{cur.id}:  v{cur.origin.id} → v{cur.dest.id}"
        f"   face={face_lbl}   twin=he{twin.id} (face={twin_face})\n"
        f"N next · P prev · T twin · R repor      "
        f"circulador: {gui.circulador}"
    )
