"""
Superfície Bézier de produto tensorial — graus ajustáveis via GUI.
Renderização via subdivisão de de Casteljau.

  Arrastar esfera (ponto de controle) → mover no eixo Y
  Arrastar área vazia                 → orbitar / zoom (orbitControl)
  R                                   → zerar todas as alturas
"""

from math import comb, hypot
from gui import GuiBlock

# ── parâmetros globais ─────────────────────────────────────────────────────
EXTENT = 300        # extensão total da grade em unidades de mundo
HIT_R  = 18         # threshold de seleção em pixels de tela

du, dv   = 3, 2     # graus em u e v  →  (du+1)×(dv+1) pontos de controle
_sp  = float(EXTENT) / max(du, dv, 1)
ctrl = [
    [[(j - dv * 0.5) * _sp, 0.0, (i - du * 0.5) * _sp]
     for j in range(dv + 1)]
    for i in range(du + 1)
]

selected  = None    # (i, j) ou None
drag_vert = False
dirty     = True

surf_pts  = None    # malha avaliada da superfície Bézier
surf_nrm  = None    # normais por vértice da malha
res_last  = -1      # resolução usada no cache

cam_proj = None
cam_view = None
hud_el   = None
gui      = None

# Algoritmo de de Casteljau

def de_casteljau (t, pts):
    b = [pts]
    n = len(pts)-1
    d = len(pts[0])
    u = 1-t
    for k in range(1,n+1):
        b.append([])
        bp = b[k-1]
        for i in range (0,n-k+1):
            p = [u*bp[i][j]+t*bp[i+1][j] for j in range(d)]
            b[k].append(p)
    return b

def subdiv_grid (ctrl):
    grid = []
    n = len(ctrl[0])-1
    for row in ctrl:
        b = de_casteljau(0.5, row)
        left = [b[i][0] for i in range (n+1)]
        right = [b[n-i][i] for i in range(n+1)]
        grid.append(left+right[1:])
    return grid

def transpose_grid(grid):
    ni = len(grid)
    nj = len(grid[0])
    return [[grid[i][j] for i in range(ni)] for j in range(nj)]

# ── Avaliação da superfície ────────────────────────────────────────────────

def compute_surface():
    nsubdiv = gui.subdivisao
    grid = ctrl
    for i in range(nsubdiv):
        grid = subdiv_grid(grid)
        grid = transpose_grid(grid)
    if nsubdiv%2 == 1: 
        grid = transpose_grid(grid)
    return grid

def compute_face_normals(surf):
    Ri = len(surf)
    Rj = len(surf[0])
    nrm = [[[0.0, 0.0, 0.0] for _ in range(Rj)] for _ in range(Ri)]
    for i in range(Ri-1):
        for j in range(Rj-1):
            a = surf[i][j];       b = surf[i][j + 1]
            c = surf[i + 1][j + 1]; d = surf[i + 1][j]
            for (p, q, r), corners in [
                ((a, b, c), [(i, j), (i, j+1), (i+1, j+1)]),
                ((a, c, d), [(i, j), (i+1, j+1), (i+1, j)])
            ]:
                e1 = [q[k] - p[k] for k in range(3)]
                e2 = [r[k] - p[k] for k in range(3)]
                nx = e1[1]*e2[2] - e1[2]*e2[1]
                ny = e1[2]*e2[0] - e1[0]*e2[2]
                nz = e1[0]*e2[1] - e1[1]*e2[0]
            
                nrm[i][j][0] += nx
                nrm[i][j][1] += ny
                nrm[i][j][2] += nz
            
            n = nrm[i][j]
            L = (n[0]**2 + n[1]**2 + n[2]**2)**0.5
            nrm[i][j] = [n[k] / L for k in range(3)] if L > 1e-9 else [0.0, 1.0, 0.0]
    return nrm

def compute_normals(surf):
    Ri = len(surf)
    Rj = len(surf[0])
    nrm = [[[0.0, 0.0, 0.0] for _ in range(Rj)] for _ in range(Ri)]
    for i in range(Ri-1):
        for j in range(Rj-1):
            a = surf[i][j];       b = surf[i][j + 1]
            c = surf[i + 1][j + 1]; d = surf[i + 1][j]
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
    for i in range(Ri):
        for j in range(Rj):
            n = nrm[i][j]
            L = (n[0]**2 + n[1]**2 + n[2]**2)**0.5
            nrm[i][j] = [n[k] / L for k in range(3)] if L > 1e-9 else [0.0, 1.0, 0.0]
    return nrm

# ── Grade de controle ──────────────────────────────────────────────────────

def make_ctrl():
    global ctrl
    sp = float(EXTENT) / max(du, dv, 1)
    ctrl = [
        [[(j - dv * 0.5) * sp, 0.0, (i - du * 0.5) * sp]
         for j in range(dv + 1)]
        for i in range(du + 1)
    ]

def resize_ctrl(new_du, new_dv):
    """Redimensiona a grade preservando os valores Y existentes."""
    global ctrl, du, dv, dirty
    old, old_du, old_dv = ctrl, du, dv
    du, dv = new_du, new_dv
    sp = float(EXTENT) / max(du, dv, 1)
    ctrl = [
        [[(j - dv * 0.5) * sp, 0.0, (i - du * 0.5) * sp]
         for j in range(dv + 1)]
        for i in range(du + 1)
    ]
    for i in range(min(du + 1, old_du + 1)):
        for j in range(min(dv + 1, old_dv + 1)):
            ctrl[i][j][1] = old[i][j][1]
    dirty = True

# ── Projeção câmera ────────────────────────────────────────────────────────

def fetch_matrices():
    try:
        cam = P5._renderer._curCamera
        p = [float(cam.projMatrix.mat4[k]) for k in range(16)]
        v = [float(cam.cameraMatrix.mat4[k]) for k in range(16)]
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

def setup():
    global hud_el, gui
    create_canvas(window_width, window_height, WEBGL)
    # Câmera inicial: ligeiramente acima e à frente do plano XZ
    camera(0, -300, 500, 0, 0, 0, 0, 1, 0)
    make_ctrl()

    gui = GuiBlock()
    gui.addNumber("grau_u", 1, 7, du, 1)
    gui.addNumber("grau_v", 1, 7, dv, 1)
    gui.addNumber("subdivisao", 0, 10, 4, 1)
    gui.addSelect("normais", ["face","vertice","arame"], "face")

    def on_change():
        global dirty
        nu = int(gui.grau_u)
        nv = int(gui.grau_v)
        if nu != du or nv != dv:
            resize_ctrl(nu, nv)
        dirty = True

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
    if hud_el is None:
        return
    sel_info = ''
    if selected:
        i, j = selected
        sel_info = f'  ·  ponto ({i},{j})  y={ctrl[i][j][1]:.0f}'
    modo = gui.normais
    if modo != "arame": modo = "normais por "+modo
    hud_el.html(
        f'Bézier grau {du}×{dv}  ({du+1}×{dv+1} pontos)  |  {modo}{sel_info}<br>'
        f'R zerar alturas  ·  arrastar esfera: mover  ·  arrastar vazio: câmera'
    )

# ── Eventos ────────────────────────────────────────────────────────────────

def mouse_pressed():
    global selected, drag_vert
    if cam_proj is None or cam_view is None:
        return
    best, best_d = None, HIT_R
    for i in range(du + 1):
        for j in range(dv + 1):
            sx, sy = world_to_screen(ctrl[i][j][0], ctrl[i][j][1], ctrl[i][j][2],
                                     cam_proj, cam_view)
            if sx is None:
                continue
            d = ((sx - mouse_x)**2 + (sy - mouse_y)**2)**0.5
            if d < best_d:
                best_d = d
                best = (i, j)
    selected  = best
    drag_vert = best is not None

def mouse_dragged():
    global dirty
    if not (drag_vert and selected):
        return
    if cam_view is None or cam_proj is None:
        return
    i, j = selected
    px, py, pz = ctrl[i][j]
    # Reproduz exatamente o caminho de world_to_screen para obter cw correto
    vx = cam_view[0]*px + cam_view[4]*py + cam_view[8]*pz  + cam_view[12]
    vy = cam_view[1]*px + cam_view[5]*py + cam_view[9]*pz  + cam_view[13]
    vz = cam_view[2]*px + cam_view[6]*py + cam_view[10]*pz + cam_view[14]
    vw = cam_view[3]*px + cam_view[7]*py + cam_view[11]*pz + cam_view[15]
    # cw = denominador perspectivo (row 3 da proj matrix, col-major: [3],[7],[11],[15])
    cw = cam_proj[3]*vx + cam_proj[7]*vy + cam_proj[11]*vz + cam_proj[15]*vw
    # abs() em proj[5] neutraliza eventual sinal negativo (flip de Y do p5.js)
    fy = abs(cam_proj[5])
    scale = abs(cw) / (fy * height * 0.5) if fy > 1e-9 and abs(cw) > 1e-9 else 1.0
    dx = float(mouse_x - pmouse_x)
    dy = float(mouse_y - pmouse_y)
    # Mover no plano da tela: right = row0 da view (col-major: [0],[4],[8])
    #                         screen-down = row1 da view (col-major: [1],[5],[9])
    ctrl[i][j][0] += scale * (dx * cam_view[0] + dy * cam_view[1])
    ctrl[i][j][1] += scale * (dx * cam_view[4] + dy * cam_view[5])
    ctrl[i][j][2] += scale * (dx * cam_view[8] + dy * cam_view[9])
    dirty = True

def mouse_released():
    global selected, drag_vert
    selected  = None
    drag_vert = False

def key_pressed():
    global dirty
    if key in ['R', 'r']:
        for row in ctrl:
            for v in row:
                v[1] = 0.0
        dirty = True

# ── Renderização ───────────────────────────────────────────────────────────

def draw():
    global cam_proj, cam_view, dirty, surf_pts, surf_nrm, res_last

    background(22, 28, 40)

    if not drag_vert:
        orbit_control()

    cam_proj, cam_view = fetch_matrices()

    ambient_light(50, 58, 75)
    directional_light(200, 218, 255, -0.4,  1.0, -0.5)
    directional_light(80,  105, 175,  0.5,  -0.5,  0.7)

    normals = gui.normais
    wire = normals == "arame"

    if dirty:
        surf_pts = compute_surface()
        if normals == "face":
            surf_nrm = compute_face_normals(surf_pts)
        else:
            surf_nrm = compute_normals(surf_pts)
        dirty    = False

    Ri = len(surf_pts)
    Rj = len(surf_pts[0])
    
    # ── superfície sólida ──────────────────────────────────────────────────
    if not wire:
        no_stroke()
        fill(200, 200, 200)
        if normals == "face":
            for i in range(Ri-1):
                for j in range(Rj-1):
                    v00 = surf_pts[i][j];         v01 = surf_pts[i][j + 1]
                    v11 = surf_pts[i + 1][j + 1]; v10 = surf_pts[i + 1][j]
                    n = surf_nrm[i][j]
                    begin_shape(QUADS)
                    normal(*n)
                    vertex(float(v00[0]), float(v00[1]), float(v00[2]))
                    vertex(float(v01[0]), float(v01[1]), float(v01[2]))
                    vertex(float(v11[0]), float(v11[1]), float(v11[2]))
                    vertex(float(v10[0]), float(v10[1]), float(v10[2]))
                    end_shape()
        else:
            for i in range(Ri-1):
                for j in range(Rj-1):
                    v00 = surf_pts[i][j];         v01 = surf_pts[i][j + 1]
                    v11 = surf_pts[i + 1][j + 1]; v10 = surf_pts[i + 1][j]
                    n00 = surf_nrm[i][j];         n01 = surf_nrm[i][j + 1]
                    n11 = surf_nrm[i + 1][j + 1]; n10 = surf_nrm[i + 1][j]
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
    no_fill()
    stroke_weight(1)
    if wire:
        stroke(70, 110, 170)
    else:
        stroke(55, 90, 145, 55)
    for i in range(Ri-1):
        for j in range(Rj-1):
            begin_shape(QUADS)
            vertex(float(surf_pts[i][j][0]),         float(surf_pts[i][j][1]),         float(surf_pts[i][j][2]))
            vertex(float(surf_pts[i][j + 1][0]),     float(surf_pts[i][j + 1][1]),     float(surf_pts[i][j + 1][2]))
            vertex(float(surf_pts[i + 1][j + 1][0]), float(surf_pts[i + 1][j + 1][1]), float(surf_pts[i + 1][j + 1][2]))
            vertex(float(surf_pts[i + 1][j][0]),     float(surf_pts[i + 1][j][1]),     float(surf_pts[i + 1][j][2]))
            end_shape()

    # ── malha de controle (amarela) ────────────────────────────────────────
    stroke(255, 200, 50, 160)
    stroke_weight(1.5)
    no_fill()
    for i in range(du + 1):
        for j in range(dv):
            x0, y0, z0 = ctrl[i][j]
            x1, y1, z1 = ctrl[i][j + 1]
            line(float(x0), float(y0), float(z0), float(x1), float(y1), float(z1))
    for j in range(dv + 1):
        for i in range(du):
            x0, y0, z0 = ctrl[i][j]
            x1, y1, z1 = ctrl[i + 1][j]
            line(float(x0), float(y0), float(z0), float(x1), float(y1), float(z1))

    # ── esferas nos pontos de controle ─────────────────────────────────────
    r = max(3.0, min(8.0, 56.0 / max(du + 1, dv + 1)))
    no_stroke()
    for i in range(du + 1):
        for j in range(dv + 1):
            push()
            translate(float(ctrl[i][j][0]), float(ctrl[i][j][1]), float(ctrl[i][j][2]))
            if (i, j) == selected:
                emissive_material(255, 0, 0)
                fill(255, 75, 75)
                sphere(r * 1.2)
                emissive_material(0, 0, 0)
            else:
                fill(255, 210, 60)
                sphere(r)
            pop()

    update_hud()
