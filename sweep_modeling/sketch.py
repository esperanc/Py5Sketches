"""
Modelagem por varredura (sweep) sobre a estrutura half-edge.

Uma curva 2D — o *perfil* (vermelho) — é varrida ao longo de uma *trajetória*
(verde), gerando uma malha 3D:

  • Extrusão linear — perfil fechado deslocado ao longo de uma reta;
  • Revolução       — silhueta girada em torno do eixo y;
  • Lofting         — interpolação entre dois perfis ao longo da reta.

  GUI (esq.)
    tipo            → esquema de varredura
    perfil / alvo   → seção (extrusão) ou seções inicial→final (lofting)
    silhueta        → perfil da revolução
    seções          → discretização da varredura (mais = mais liso)
    torção          → giro acumulado ao longo da reta (extrusão / lofting)
    varredura       → extensão da varredura: % do comprimento ou do ângulo
    faces/arame/curvas/suave → exibição
  Arrastar          → orbit_control (orbitar / zoom)

A malha resultante é uma DCEL (half-edge); as faces e o aramado são lidos por
seus circuladores e enviados a buffers de GPU via build_geometry.
"""

import sweep
import profiles as pf
from gui import GuiBlock

# ── Estado global ───────────────────────────────────────────────────────────
gui       = None
hud_el    = None
_cam_init = False
_dirty    = True
_geom_key = None

mesh      = None
info      = None
tris      = []        # (x,y,z,nx,ny,nz) em grupos de 3
wire      = []        # segmentos do aramado
prof_pts  = []        # curva-perfil (vermelha)
traj_pts  = []        # curva-trajetória (verde)
prof_closed = True
traj_closed = False
show_axis = False

face_geom = None
wire_geom = None
_face_proxy = None
_wire_proxy = None

COL_FACE = (196, 204, 220)
COL_WIRE = (40, 58, 92)
COL_PROF = (240, 70, 70)
COL_TRAJ = (70, 220, 120)
COL_AXIS = (255, 205, 70)

_CHUNK = 3000


# ── Geometria de desenho ────────────────────────────────────────────────────
def edges_of(m):
    out = []
    seen = set()
    for h in m.halfedges:
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

def vertex_normals(m):
    acc = {v.id: [0.0, 0.0, 0.0] for v in m.vertices}
    for f in m.faces:
        nx, ny, nz = f.normal()
        for v in f.vertices():
            a = acc[v.id]
            a[0] += nx; a[1] += ny; a[2] += nz
    out = {}
    for vid, a in acc.items():
        L = (a[0] ** 2 + a[1] ** 2 + a[2] ** 2) ** 0.5
        out[vid] = (a[0] / L, a[1] / L, a[2] / L) if L > 1e-9 else (0.0, 1.0, 0.0)
    return out

def _triangulate(m, smooth):
    """Faces → triângulos com normais. Quads/triângulos: leque a partir de v0
    (convexos); n-gonos (tampas): leque a partir do centroide (estrela)."""
    vn = vertex_normals(m) if smooth else None
    out = []
    for f in m.faces:
        fn = f.normal()
        vs = list(f.vertices())
        k = len(vs)
        if k <= 4:
            for i in range(1, k - 1):
                for vtx in (vs[0], vs[i], vs[i + 1]):
                    n = vn[vtx.id] if smooth else fn
                    out.append((vtx.x, vtx.y, vtx.z, n[0], n[1], n[2]))
        else:
            cx = sum(v.x for v in vs) / k
            cy = sum(v.y for v in vs) / k
            cz = sum(v.z for v in vs) / k
            for i in range(k):
                a = vs[i]
                b = vs[(i + 1) % k]
                na = vn[a.id] if smooth else fn
                nb = vn[b.id] if smooth else fn
                out.append((cx, cy, cz, fn[0], fn[1], fn[2]))
                out.append((a.x, a.y, a.z, na[0], na[1], na[2]))
                out.append((b.x, b.y, b.z, nb[0], nb[1], nb[2]))
    return out


# ── callbacks de build_geometry ─────────────────────────────────────────────
def _face_cb(*_):
    no_stroke()
    n = len(tris)
    i = 0
    while i < n:
        end = min(i + _CHUNK, n)
        end -= (end - i) % 3
        begin_shape(TRIANGLES)
        for j in range(i, end):
            x, y, z, nx, ny, nz = tris[j]
            normal(nx, ny, nz)
            vertex(x, y, z)
        end_shape()
        i = end

def _wire_cb(*_):
    n = len(wire)
    i = 0
    step = _CHUNK // 2
    while i < n:
        end = min(i + step, n)
        begin_shape(LINES)
        for j in range(i, end):
            x0, y0, z0, x1, y1, z1 = wire[j]
            vertex(x0, y0, z0)
            vertex(x1, y1, z1)
        end_shape()
        i = end

def _free(g):
    if g is not None:
        try:
            free_geometry(g)
        except Exception:
            pass


def rebuild_geometry():
    global mesh, info, tris, wire, prof_pts, traj_pts
    global prof_closed, traj_closed, show_axis
    global _dirty, _geom_key, face_geom, wire_geom

    smooth = bool(gui.suave)
    key = (gui.tipo, gui.perfil, gui.alvo, gui.silhueta,
           int(gui.secoes), float(gui.torcao), float(gui.varredura), smooth)
    if not _dirty and key == _geom_key:
        return
    _geom_key = key
    _dirty = False

    info = sweep.build(gui.tipo, gui.perfil, gui.alvo, gui.silhueta,
                       gui.secoes, gui.torcao, gui.varredura)
    mesh = info["mesh"]
    prof_pts = info["prof"]
    traj_pts = info["traj"]
    prof_closed = info["prof_closed"]
    traj_closed = info["traj_closed"]
    show_axis = info["axis"]

    tris = _triangulate(mesh, smooth)
    wire = edges_of(mesh)

    _free(face_geom)
    _free(wire_geom)
    face_geom = build_geometry(_face_proxy)
    wire_geom = build_geometry(_wire_proxy)


# ── Setup / GUI ─────────────────────────────────────────────────────────────
def setup():
    global gui, hud_el, _face_proxy, _wire_proxy

    create_canvas(window_width, window_height, WEBGL)

    _face_proxy = create_proxy(_face_cb)
    _wire_proxy = create_proxy(_wire_cb)

    GuiBlock.labelWidth = "5.5em"
    gui = GuiBlock()
    gui.addSelect("tipo", sweep.TIPOS, "Revolução")
    gui.addSelect("perfil", pf.CROSS_NAMES, "Estrela")
    gui.addSelect("alvo", pf.CROSS_NAMES, "Círculo")
    gui.addSelect("silhueta", pf.SILH_NAMES, "Vaso")
    gui.addNumber("secoes", 3, 96, 40, 1)
    gui.addNumber("torcao", -360, 360, 0, 15)
    gui.addNumber("varredura", 5, 100, 100, 5)
    gui.addCheckbox("faces", True)
    gui.addCheckbox("arame", True)
    gui.addCheckbox("curvas", True)
    gui.addCheckbox("suave", False)
    gui.change(on_gui_change)

    hud_el = create_div('')
    hud_el.position(10, window_height - 72)
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
        save("sweeping.png")
        

# ── Desenho ─────────────────────────────────────────────────────────────────
def draw():
    global _cam_init

    background(20, 26, 38)

    if not _cam_init:
        camera(0, -250, 660, 0, 0, 0, 0, 1, 0)
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

    if gui.curvas:
        draw_curves()

    update_hud()


def _polyline(pts, closed, weight):
    n = len(pts)
    last = n if closed else n - 1
    for i in range(last):
        a = pts[i]
        b = pts[(i + 1) % n]
        line(a[0], a[1], a[2], b[0], b[1], b[2])

def draw_curves():
    # eixo de revolução
    if show_axis:
        stroke(COL_AXIS[0], COL_AXIS[1], COL_AXIS[2], 130)
        stroke_weight(1)
        line(0, -240, 0, 0, 240, 0)
    # trajetória (verde)
    no_fill()
    stroke(COL_TRAJ[0], COL_TRAJ[1], COL_TRAJ[2])
    stroke_weight(3)
    _polyline(traj_pts, traj_closed, 3)
    # perfil (vermelho), ligeiramente à frente
    stroke(COL_PROF[0], COL_PROF[1], COL_PROF[2])
    stroke_weight(4)
    _polyline(prof_pts, prof_closed, 4)


def update_hud():
    if hud_el is None or mesh is None:
        return
    m = mesh
    topo = "fechada" if m.is_closed else f"aberta · {len(m.boundary)} bordas"
    hud_el.html(
        f"varredura: {gui.tipo}      {info['active']}\n"
        f"malha  V={m.n_vertices}  E={m.n_edges}  F={m.n_faces}"
        f"   Euler={m.euler()}   ({topo})\n"
        f"seções={int(gui.secoes)}   varredura={float(gui.varredura):g}%"
        f"      perfil ▮vermelho   trajetória ▮verde"
    )
