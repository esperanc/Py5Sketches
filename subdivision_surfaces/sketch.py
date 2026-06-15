"""
Superfície de subdivisão de produto tensorial — Lane-Riesenfeld e 4-pontos.

  GUI (esq.)              → algoritmo, dimensões, recursões, parâmetros
  Arrastar esfera         → mover ponto de controlo no plano da tela
  Arrastar área vazia     → orbitar / zoom (orbitControl)
  R                       → zerar todas as alturas
"""

from smooth_surfaces import lr_surface, four_point_surface
from gui import GuiBlock

# ── Constantes ─────────────────────────────────────────────────────────────
EXTENT = 300
HIT_R  = 18

# ── Estado global — inicializado com valores padrão ────────────────────────
nu, nv = 4, 4

_sp  = float(EXTENT) / max(nu - 1, nv - 1, 1)
ctrl = [
    [[(j - (nv - 1) * 0.5) * _sp, 0.0, (i - (nu - 1) * 0.5) * _sp]
     for j in range(nv)]
    for i in range(nu)
]

selected  = None
drag_vert = False
dirty     = True

surf_pts  = None
surf_nrm  = None
_cam_init = False

cam_proj  = None
cam_view  = None
hud_el    = None
gui       = None

# ── Grade de controlo ──────────────────────────────────────────────────────

def make_ctrl():
    global ctrl
    sp = float(EXTENT) / max(nu - 1, nv - 1, 1)
    ctrl = [
        [[(j - (nv - 1) * 0.5) * sp, 0.0, (i - (nu - 1) * 0.5) * sp]
         for j in range(nv)]
        for i in range(nu)
    ]

def resize_ctrl():
    global ctrl, dirty
    old    = ctrl
    old_nu = len(old)
    old_nv = len(old[0]) if old else 0
    sp = float(EXTENT) / max(nu - 1, nv - 1, 1)
    ctrl = [
        [[(j - (nv - 1) * 0.5) * sp, 0.0, (i - (nu - 1) * 0.5) * sp]
         for j in range(nv)]
        for i in range(nu)
    ]
    for i in range(min(nu, old_nu)):
        for j in range(min(nv, old_nv)):
            ctrl[i][j][1] = old[i][j][1]
    dirty = True

# ── Subdivisão ─────────────────────────────────────────────────────────────

def do_subdivision(ctrl_g, alg, deg, w, cu, cv, recs):
    """Aplica `recs` passos de subdivisão à grade ctrl_g."""
    sub = ctrl_g
    for _ in range(recs):
        if alg == "Lane-Riesenfeld":
            sub = lr_surface(sub, cu, cv, deg)
        else:
            sub = four_point_surface(sub, cu, cv, w)
    return sub

def extend_for_closed(sub, closed_u, closed_v):
    """Duplica a primeira linha/coluna no fim para fechar a grade de renderização."""
    grid = sub
    if closed_v:
        grid = [row + [row[0]] for row in grid]
    if closed_u:
        grid = grid + [grid[0]]
    return grid

# ── Normais ────────────────────────────────────────────────────────────────

def compute_normals(grid):
    nrows = len(grid)
    ncols = len(grid[0])
    nrm = [[[0.0, 0.0, 0.0] for _ in range(ncols)] for _ in range(nrows)]
    for i in range(nrows - 1):
        for j in range(ncols - 1):
            a = grid[i][j];           b = grid[i][j + 1]
            c = grid[i + 1][j + 1];   d = grid[i + 1][j]
            for (p, q, r), corners in [
                ((a, b, c), [(i, j), (i, j+1), (i+1, j+1)]),
                ((a, c, d), [(i, j), (i+1, j+1), (i+1, j)])
            ]:
                e1 = [q[k] - p[k] for k in range(3)]
                e2 = [r[k] - p[k] for k in range(3)]
                nx = e1[1]*e2[2] - e1[2]*e2[1]
                ny = e1[2]*e2[0] - e1[0]*e2[2]
                nz = e1[0]*e2[1] - e1[1]*e2[0]
                for ii, jj in corners:
                    nrm[ii][jj][0] += nx
                    nrm[ii][jj][1] += ny
                    nrm[ii][jj][2] += nz
    for i in range(nrows):
        for j in range(ncols):
            n = nrm[i][j]
            L = (n[0]**2 + n[1]**2 + n[2]**2)**0.5
            nrm[i][j] = [n[k] / L for k in range(3)] if L > 1e-9 else [0.0, 1.0, 0.0]
    return nrm

# ── Projeção câmera ────────────────────────────────────────────────────────

def fetch_matrices():
    try:
        cam = P5._renderer._curCamera
        p   = [float(cam.projMatrix.mat4[k])   for k in range(16)]
        v   = [float(cam.cameraMatrix.mat4[k]) for k in range(16)]
        return p, v
    except Exception:
        return None, None

def world_to_screen(x, y, z, proj, view):
    vx = view[0]*x + view[4]*y + view[8]*z  + view[12]
    vy = view[1]*x + view[5]*y + view[9]*z  + view[13]
    vz = view[2]*x + view[6]*y + view[10]*z + view[14]
    vw = view[3]*x + view[7]*y + view[11]*z + view[15]
    cx = proj[0]*vx + proj[4]*vy + proj[8]*vz  + proj[12]*vw
    cy = proj[1]*vx + proj[5]*vy + proj[9]*vz  + proj[13]*vw
    cw = proj[3]*vx + proj[7]*vy + proj[11]*vz + proj[15]*vw
    if abs(cw) < 1e-9:
        return None, None
    return (cx / cw + 1.0) * width * 0.5, (1.0 - cy / cw) * height * 0.5

# ── Setup / GUI ────────────────────────────────────────────────────────────

def on_change():
    global nu, nv, dirty
    new_nu = int(gui.n_u)
    new_nv = int(gui.n_v)
    if new_nu != nu or new_nv != nv:
        nu, nv = new_nu, new_nv
        resize_ctrl()
    else:
        nu, nv = new_nu, new_nv
    dirty = True

def setup():
    global gui, hud_el

    create_canvas(window_width, window_height, WEBGL)
    make_ctrl()

    GuiBlock.labelWidth = "7em"
    gui = GuiBlock()
    gui.addSelect("algorithm",  ["Lane-Riesenfeld", "4-point"], "Lane-Riesenfeld")
    gui.addNumber("n_u",        2, 10, nu, 1)
    gui.addNumber("n_v",        2, 10, nv, 1)
    gui.addNumber("recursions", 0, 5,  3,  1)
    gui.addNumber("degree",     1, 4,  2,  1)
    gui.addNumber("w",          0.0, 0.12, 0.06, 0.01)
    gui.addCheckbox("closed_u")
    gui.addCheckbox("closed_v")
    gui.addCheckbox("arame")
    gui.change(on_change)

    hud_el = create_div('')
    hud_el.position(10, window_height - 40)
    hud_el.style('color',          'rgba(175, 205, 240, 0.95)')
    hud_el.style('font-family',    'monospace')
    hud_el.style('font-size',      '13px')
    hud_el.style('line-height',    '1.6')
    hud_el.style('pointer-events', 'none')
    hud_el.style('text-shadow',    '0 1px 3px rgba(0,0,0,0.8)')

def update_hud():
    if hud_el is None or gui is None:
        return
    sel_info = ''
    if selected is not None:
        i, j = selected
        sel_info = f'  ·  ponto ({i},{j})  y={ctrl[i][j][1]:.0f}'
    modo = 'arame' if gui.arame else 'sólido'
    grid_info = f'{nu}×{nv}'
    if surf_pts is not None:
        grid_info += f' → {len(surf_pts)}×{len(surf_pts[0])}'
    hud_el.html(
        f'Subdivisão {gui.algorithm}  |  {grid_info}  |  {modo}{sel_info}<br>'
        f'R zerar  ·  arrastar esfera: mover  ·  arrastar vazio: câmera'
    )

# ── Eventos ────────────────────────────────────────────────────────────────

def mouse_pressed():
    global selected, drag_vert
    if cam_proj is None or cam_view is None:
        drag_vert = False
        return
    best, best_d = None, HIT_R
    for i in range(nu):
        for j in range(nv):
            sx, sy = world_to_screen(ctrl[i][j][0], ctrl[i][j][1], ctrl[i][j][2],
                                     cam_proj, cam_view)
            if sx is None:
                continue
            d = ((sx - mouse_x)**2 + (sy - mouse_y)**2)**0.5
            if d < best_d:
                best_d = d
                best = (i, j)
    selected  = best
    drag_vert = (best is not None)

def mouse_dragged():
    global dirty
    if not (drag_vert and selected is not None):
        return
    if cam_view is None or cam_proj is None:
        return
    i, j = selected
    px, py, pz = ctrl[i][j]
    vx = cam_view[0]*px + cam_view[4]*py + cam_view[8]*pz  + cam_view[12]
    vy = cam_view[1]*px + cam_view[5]*py + cam_view[9]*pz  + cam_view[13]
    vz = cam_view[2]*px + cam_view[6]*py + cam_view[10]*pz + cam_view[14]
    vw = cam_view[3]*px + cam_view[7]*py + cam_view[11]*pz + cam_view[15]
    cw    = cam_proj[3]*vx + cam_proj[7]*vy + cam_proj[11]*vz + cam_proj[15]*vw
    fy    = abs(cam_proj[5])
    scale = abs(cw) / (fy * height * 0.5) if fy > 1e-9 and abs(cw) > 1e-9 else 1.0
    dx = float(mouse_x - pmouse_x)
    dy = float(mouse_y - pmouse_y)
    ctrl[i][j][0] += scale * (dx * cam_view[0] + dy * cam_view[1])
    ctrl[i][j][1] += scale * (dx * cam_view[4] + dy * cam_view[5])
    ctrl[i][j][2] += scale * (dx * cam_view[8] + dy * cam_view[9])
    dirty = True

def mouse_released():
    global drag_vert
    drag_vert = False

def key_pressed():
    global dirty
    if key in ['R', 'r']:
        for row in ctrl:
            for pt in row:
                pt[1] = 0.0
        dirty = True

# ── Renderização ───────────────────────────────────────────────────────────

def draw():
    global cam_proj, cam_view, dirty, surf_pts, surf_nrm, _cam_init

    background(22, 28, 40)

    if not _cam_init:
        camera(0, -300, 500, 0, 0, 0, 0, 1, 0)
        _cam_init = True

    if not drag_vert:
        orbit_control()

    cam_proj, cam_view = fetch_matrices()

    ambient_light(50, 58, 75)
    directional_light(200, 218, 255, -0.4,  1.0, -0.5)
    directional_light(80,  105, 175,  0.5, -0.5,  0.7)

    wire = bool(gui.arame)
    cu   = bool(gui.closed_u)
    cv   = bool(gui.closed_v)

    if dirty:
        raw      = do_subdivision(ctrl,
                                  gui.algorithm,
                                  int(gui.degree),
                                  float(gui.w),
                                  cu, cv,
                                  int(gui.recursions))
        grid     = extend_for_closed(raw, cu, cv)
        surf_pts = grid
        surf_nrm = compute_normals(grid)
        dirty    = False

    # ── superfície sólida ──────────────────────────────────────────────────
    if surf_pts is not None and not wire:
        nrows = len(surf_pts)
        ncols = len(surf_pts[0])
        no_stroke()
        fill(200, 200, 200)
        for i in range(nrows - 1):
            for j in range(ncols - 1):
                v00 = surf_pts[i][j];           v01 = surf_pts[i][j + 1]
                v11 = surf_pts[i + 1][j + 1];   v10 = surf_pts[i + 1][j]
                n00 = surf_nrm[i][j];           n01 = surf_nrm[i][j + 1]
                n11 = surf_nrm[i + 1][j + 1];   n10 = surf_nrm[i + 1][j]
                begin_shape(QUADS)
                normal(float(n00[0]), float(n00[1]), float(n00[2]))
                vertex(float(v00[0]), float(v00[1]), float(v00[2]))
                normal(float(n01[0]), float(n01[1]), float(n01[2]))
                vertex(float(v01[0]), float(v01[1]), float(v01[2]))
                normal(float(n11[0]), float(n11[1]), float(n11[2]))
                vertex(float(v11[0]), float(v11[1]), float(v11[2]))
                normal(float(n10[0]), float(n10[1]), float(n10[2]))
                vertex(float(v10[0]), float(v10[1]), float(v10[2]))
                end_shape()

    # ── arame da superfície ────────────────────────────────────────────────
    if surf_pts is not None:
        nrows = len(surf_pts)
        ncols = len(surf_pts[0])
        no_fill()
        stroke_weight(1)
        stroke(70, 110, 170) if wire else stroke(55, 90, 145, 55)
        for i in range(nrows - 1):
            for j in range(ncols - 1):
                begin_shape(QUADS)
                vertex(float(surf_pts[i][j][0]),         float(surf_pts[i][j][1]),         float(surf_pts[i][j][2]))
                vertex(float(surf_pts[i][j+1][0]),       float(surf_pts[i][j+1][1]),       float(surf_pts[i][j+1][2]))
                vertex(float(surf_pts[i+1][j+1][0]),     float(surf_pts[i+1][j+1][1]),     float(surf_pts[i+1][j+1][2]))
                vertex(float(surf_pts[i+1][j][0]),       float(surf_pts[i+1][j][1]),       float(surf_pts[i+1][j][2]))
                end_shape()

    # ── malha de controlo (amarela) ────────────────────────────────────────
    stroke(255, 200, 50, 160)
    stroke_weight(1.5)
    no_fill()
    for i in range(nu):
        for j in range(nv - 1):
            x0, y0, z0 = ctrl[i][j]
            x1, y1, z1 = ctrl[i][j + 1]
            line(float(x0), float(y0), float(z0), float(x1), float(y1), float(z1))
    for j in range(nv):
        for i in range(nu - 1):
            x0, y0, z0 = ctrl[i][j]
            x1, y1, z1 = ctrl[i + 1][j]
            line(float(x0), float(y0), float(z0), float(x1), float(y1), float(z1))
    # fechar malha quando closed
    if cu:
        for j in range(nv):
            x0, y0, z0 = ctrl[nu - 1][j]
            x1, y1, z1 = ctrl[0][j]
            line(float(x0), float(y0), float(z0), float(x1), float(y1), float(z1))
    if cv:
        for i in range(nu):
            x0, y0, z0 = ctrl[i][nv - 1]
            x1, y1, z1 = ctrl[i][0]
            line(float(x0), float(y0), float(z0), float(x1), float(y1), float(z1))

    # ── esferas nos pontos de controlo ─────────────────────────────────────
    r = max(3.0, min(8.0, 56.0 / max(nu, nv)))
    no_stroke()
    for i in range(nu):
        for j in range(nv):
            push()
            translate(float(ctrl[i][j][0]), float(ctrl[i][j][1]), float(ctrl[i][j][2]))
            if (i, j) == selected:
                emissive_material(255, 0, 0)
                fill(255, 75, 75)
                sphere(r * 1.3)
                emissive_material(0, 0, 0)
            else:
                fill(255, 210, 60)
                sphere(r)
            pop()

    update_hud()
