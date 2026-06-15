"""
Superfície NURBS de produto tensorial — graus, dimensões e nós ajustáveis via GUI.

  GUI esquerda (U / V)  → grau, nº de pontos de controle, vetor de nós
  Slider de peso (dir.) → peso w do ponto selecionado
  Arrastar esfera       → mover ponto de controle no plano da tela
  Arrastar área vazia   → orbitar / zoom (orbitControl)
  R                     → zerar alturas e repor pesos em 1
"""

from gui import GuiBlock

# ── Constantes ─────────────────────────────────────────────────────────────
EXTENT = 300        # extensão da grade em unidades de mundo
HIT_R  = 18         # raio de seleção em pixels de tela

# ── Estado global ───────────────────────────────────────────────────────────
nu, nv = 4, 4       # nº de pontos de controle em u e v
du, dv = 3, 3       # graus em u e v

# Inicialização de module-level com os valores padrão (nu=nv=4, du=dv=3)
# Garante que draw() pode calcular a superfície mesmo se setup() tiver
# um problema de escopo ao escrever globais via 'global ctrl / ku / kv'.
_sp  = float(EXTENT) / max(nu - 1, nv - 1, 1)
ctrl = [
    [[(j - (nv - 1) * 0.5) * _sp, 0.0, (i - (nu - 1) * 0.5) * _sp, 1.0]
     for j in range(nv)]
    for i in range(nu)
]
ku   = [0, 0, 0, 0, 1, 1, 1, 1]  # default clamped-uniform para nu=4, du=3
kv   = [0, 0, 0, 0, 1, 1, 1, 1]  # default clamped-uniform para nv=4, dv=3

selected  = None    # (i, j) ou None  — persiste após soltar o mouse
drag_vert = False
dirty     = True

surf_pts  = None
surf_nrm  = None
res_last  = -1
_cam_init = False   # câmera inicial definida no primeiro draw()

cam_proj = None
cam_view = None
hud_el   = None
u_gui    = None
v_gui    = None
w_gui    = None

# ── Cox-de Boor (recursivo) ────────────────────────────────────────────────

def cox_de_boor(i, d, t, knots, tmax=None):
    """N_{i,d}(t) via Cox-de Boor recursivo.

    tmax — limite superior fechado (por omissão: knots[-1]).
    Para t < tmax usa intervalos semi-abertos [lo, hi).
    Para t == tmax usa lo < tmax <= hi para identificar o último
    span ativo sem disparar o span seguinte que começa em tmax.
    """
    if tmax is None:
        tmax = knots[-1]

    def recurse(i, d):
        if d == 0:
            lo = knots[i]
            hi = knots[i + 1]
            if lo >= hi:                        # span degenerado
                return 0.0
            if t < tmax:
                return 1.0 if lo <= t < hi else 0.0
            else:                               # t == tmax: intervalo fechado
                return 1.0 if lo < tmax <= hi else 0.0

        denom1 = knots[i + d]     - knots[i]
        denom2 = knots[i + d + 1] - knots[i + 1]

        term1 = ((t - knots[i])         / denom1) * recurse(i,     d - 1) if denom1 else 0.0
        term2 = ((knots[i+d+1] - t)     / denom2) * recurse(i + 1, d - 1) if denom2 else 0.0

        return term1 + term2

    return recurse(i, d)
# ── Avaliação NURBS ────────────────────────────────────────────────────────

def compute_surface(res, ku_v, kv_v, nu_n, nv_n, du_n, dv_n, ctrl_g):
    """
    Avalia a superfície NURBS numa grade (res+1)×(res+1).
    Todos os parâmetros passados explicitamente — sem dependência de globais.
    """
    u0 = ku_v[du_n]
    u1 = ku_v[nu_n]
    v0 = kv_v[dv_n]
    v1 = kv_v[nv_n]

    us = [u0 + ii * (u1 - u0) / res for ii in range(res)] + [u1]
    vs = [v0 + jj * (v1 - v0) / res for jj in range(res)] + [v1]

    Bu = [[cox_de_boor(ci, du_n, u, ku_v, u1) for ci in range(nu_n)] for u in us]
    Bv = [[cox_de_boor(cj, dv_n, v, kv_v, v1) for cj in range(nv_n)] for v in vs]

    pts = []
    for bu_row in Bu:
        row = []
        for bv_row in Bv:
            nx = ny = nz = denom = 0.0
            for ci in range(nu_n):
                bu = bu_row[ci]
                if abs(bu) < 1e-12:
                    continue
                for cj in range(nv_n):
                    bv = bv_row[cj]
                    if abs(bv) < 1e-12:
                        continue
                    px, py, pz, pw = ctrl_g[ci][cj]
                    wbb   = bu * bv * pw
                    nx   += wbb * px
                    ny   += wbb * py
                    nz   += wbb * pz
                    denom += wbb
            if abs(denom) < 1e-12:
                row.append([0.0, 0.0, 0.0])
            else:
                row.append([nx / denom, ny / denom, nz / denom])
        pts.append(row)
    return pts

def compute_normals(surf, res):
    """Normais por vértice via médias de faces adjacentes."""
    R   = res + 1
    nrm = [[[0.0, 0.0, 0.0] for _ in range(R)] for _ in range(R)]
    for i in range(res):
        for j in range(res):
            a = surf[i][j];           b = surf[i][j + 1]
            c = surf[i + 1][j + 1];   d = surf[i + 1][j]
            for (p, q, r), corners in [
                ((a, b, c), [(i, j), (i, j + 1), (i + 1, j + 1)]),
                ((a, c, d), [(i, j), (i + 1, j + 1), (i + 1, j)])
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
    for i in range(R):
        for j in range(R):
            n = nrm[i][j]
            L = (n[0]**2 + n[1]**2 + n[2]**2)**0.5
            nrm[i][j] = [n[k] / L for k in range(3)] if L > 1e-9 else [0.0, 1.0, 0.0]
    return nrm

# ── Grade de controle ──────────────────────────────────────────────────────

def make_ctrl():
    """Cria grade plana de (nu × nv) pontos, centrada na origem."""
    global ctrl
    sp = float(EXTENT) / max(nu - 1, nv - 1, 1)
    ctrl = [
        [[(j - (nv - 1) * 0.5) * sp, 0.0, (i - (nu - 1) * 0.5) * sp, 1.0]
         for j in range(nv)]
        for i in range(nu)
    ]

def resize_ctrl():
    """Redimensiona a grade preservando alturas (y) e pesos (w) existentes."""
    global ctrl, dirty
    old    = ctrl
    old_nu = len(old)
    old_nv = len(old[0]) if old else 0
    sp = float(EXTENT) / max(nu - 1, nv - 1, 1)
    ctrl = [
        [[(j - (nv - 1) * 0.5) * sp, 0.0, (i - (nu - 1) * 0.5) * sp, 1.0]
         for j in range(nv)]
        for i in range(nu)
    ]
    for i in range(min(nu, old_nu)):
        for j in range(min(nv, old_nv)):
            ctrl[i][j][1] = old[i][j][1]   # preserva y
            ctrl[i][j][3] = old[i][j][3]   # preserva w
    dirty = True

# ── Vetores de nós ─────────────────────────────────────────────────────────

def default_knot_str(n, d):
    """Vetor de nós clamped uniforme para n pontos de controle de grau d."""
    end      = n - d                    # valor máximo do nó
    interior = list(range(1, end))      # nós interiores inteiros
    knots    = [0] * (d + 1) + interior + [end] * (d + 1)
    return ",".join(str(k) for k in knots)

def parse_knots(s, n, d):
    """Converte string CSV em lista de nós; completa automaticamente se curta."""
    try:
        ks = [float(x.strip()) for x in s.split(",") if x.strip()]
    except Exception:
        return None
    needed = n + d + 1
    while len(ks) < needed:
        inc = (ks[-1] - ks[-2]) if len(ks) > 1 else 1.0
        ks.append(ks[-1] + inc)
    return ks

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

# ── Callbacks dos GUI ──────────────────────────────────────────────────────

def on_change():
    """Disparado por qualquer alteração nos GuiBlocks U ou V."""
    global nu, nv, du, dv, ku, kv, dirty
    new_nu = int(u_gui.n_ctrl)
    new_nv = int(v_gui.n_ctrl)
    new_du = min(int(u_gui.grau), new_nu - 1)
    new_dv = min(int(v_gui.grau), new_nv - 1)

    # Actualiza sliders de grau se foram clamped
    if new_du != int(u_gui.grau):
        u_gui.setValue("grau", new_du)
    if new_dv != int(v_gui.grau):
        v_gui.setValue("grau", new_dv)

    # Quando muda o nº de pontos, gera novos nós padrão e redimensiona
    if new_nu != nu:
        u_gui.setValue("knots_u", default_knot_str(new_nu, new_du))
    if new_nv != nv:
        v_gui.setValue("knots_v", default_knot_str(new_nv, new_dv))

    changed_size = (new_nu != nu or new_nv != nv)
    nu, nv, du, dv = new_nu, new_nv, new_du, new_dv

    if changed_size:
        resize_ctrl()

    ku = parse_knots(u_gui.knots_u, nu, du) or ku
    kv = parse_knots(v_gui.knots_v, nv, dv) or kv
    dirty = True

def on_w_change():
    """Actualiza o peso do ponto de controle seleccionado."""
    global dirty
    if selected is not None:
        ctrl[selected[0]][selected[1]][3] = float(w_gui.w)
        dirty = True

# ── Setup ──────────────────────────────────────────────────────────────────

def setup():
    global u_gui, v_gui, w_gui, hud_el
    create_canvas(window_width, window_height, WEBGL)
    make_ctrl()

    ku_str = default_knot_str(nu, du)
    kv_str = default_knot_str(nv, dv)
    global ku, kv
    ku = parse_knots(ku_str, nu, du)
    kv = parse_knots(kv_str, nv, dv)

    # ── GuiBlock U ────────────────────────────────────────────────────────
    GuiBlock.labelWidth = "6em"
    u_gui = GuiBlock("U")
    u_gui.addNumber("grau",   1, 6, du, 1)
    u_gui.addNumber("n_ctrl", 2, 10, nu, 1)
    u_gui.addText("knots_u", ku_str)
    u_gui.change(on_change)

    # ── GuiBlock V (abaixo do U) ───────────────────────────────────────────
    v_gui = GuiBlock("V")
    v_gui.addNumber("grau",   1, 6, dv, 1)
    v_gui.addNumber("n_ctrl", 2, 10, nv, 1)
    v_gui.addText("knots_v", kv_str)
    v_gui.addNumber("resolucao", 4, 40, 20, 1)
    v_gui.addCheckbox("arame")
    v_gui.position(10, 135)
    v_gui.change(on_change)

    # ── GuiBlock de peso (topo direito) ───────────────────────────────────
    GuiBlock.labelWidth = "3em"
    w_gui = GuiBlock("peso")
    w_gui.addNumber("w", 0.1, 5.0, 1.0, 0.1)
    w_gui.position(window_width - 185, 10)
    w_gui.change(on_w_change)

    # ── HUD ───────────────────────────────────────────────────────────────
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
    if selected is not None:
        i, j = selected
        x, y, z, w = ctrl[i][j]
        sel_info = f'  ·  ponto ({i},{j})  y={y:.0f}  w={w:.2f}'
    modo     = 'arame' if v_gui.arame else 'sólido'
    surf_ok  = '' if surf_pts is not None else '  ⚠ superfície não calculada'
    hud_el.html(
        f'NURBS grau {du}×{dv}  ({nu}×{nv} pontos)  |  {modo}{sel_info}{surf_ok}<br>'
        f'R repor  ·  arrastar esfera: mover  ·  arrastar vazio: câmera'
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
    if selected is not None:
        w_gui.setValue("w", ctrl[selected[0]][selected[1]][3])

def mouse_dragged():
    global dirty
    if not (drag_vert and selected is not None):
        return
    if cam_view is None or cam_proj is None:
        return
    i, j = selected
    px, py, pz = ctrl[i][j][:3]
    # Denominador perspectivo — idêntico ao cálculo em world_to_screen
    vx = cam_view[0]*px + cam_view[4]*py + cam_view[8]*pz  + cam_view[12]
    vy = cam_view[1]*px + cam_view[5]*py + cam_view[9]*pz  + cam_view[13]
    vz = cam_view[2]*px + cam_view[6]*py + cam_view[10]*pz + cam_view[14]
    vw = cam_view[3]*px + cam_view[7]*py + cam_view[11]*pz + cam_view[15]
    cw = cam_proj[3]*vx + cam_proj[7]*vy + cam_proj[11]*vz + cam_proj[15]*vw
    fy    = abs(cam_proj[5])
    scale = abs(cw) / (fy * height * 0.5) if fy > 1e-9 and abs(cw) > 1e-9 else 1.0
    dx = float(mouse_x - pmouse_x)
    dy = float(mouse_y - pmouse_y)
    # Mover no plano da tela: right = row0; screen-down = row1 (col-major view)
    ctrl[i][j][0] += scale * (dx * cam_view[0] + dy * cam_view[1])
    ctrl[i][j][1] += scale * (dx * cam_view[4] + dy * cam_view[5])
    ctrl[i][j][2] += scale * (dx * cam_view[8] + dy * cam_view[9])
    dirty = True

def mouse_released():
    global drag_vert
    drag_vert = False   # seleção persiste; limpa apenas ao clicar no vazio

def key_pressed():
    global dirty
    if key in ['R', 'r']:
        for row in ctrl:
            for pt in row:
                pt[1] = 0.0   # zera altura
                pt[3] = 1.0   # repõe peso
        dirty = True
        if selected is not None:
            w_gui.setValue("w", 1.0)
    elif key in "Dd":
        print ("surf", surf_pts)
        print ("Bu", Bu)
        print ("Bv", Bv)

# ── Renderização ───────────────────────────────────────────────────────────

def _ctrl_color(w):
    """Cor do ponto de controle baseada no peso: amarelo=1, ciano>1, laranja<1."""
    if w >= 1.0:
        t = min(1.0, (w - 1.0) / 4.0)          # 0→1 para w de 1 a 5
        fill(int(255 * (1.0 - t)),
             int(210 + 45 * t),
             int(60  + 195 * t))                # amarelo → ciano
    else:
        t = min(1.0, (1.0 - w) / 0.9)           # 0→1 para w de 1 a 0.1
        fill(255,
             int(210 * (1.0 - t)),
             int(60  * (1.0 - t)))              # amarelo → laranja/vermelho

def draw():
    global cam_proj, cam_view, dirty, surf_pts, surf_nrm, res_last, _cam_init

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

    res  = int(v_gui.resolucao)
    wire = bool(v_gui.arame)

    if dirty or res != res_last:
        if ku and kv and ctrl:
            surf_pts = compute_surface(res, ku, kv, nu, nv, du, dv, ctrl)
            surf_nrm = compute_normals(surf_pts, res)
            res_last = res
            dirty    = False

    # ── superfície sólida ──────────────────────────────────────────────────
    if surf_pts is not None and not wire:
        no_stroke()
        fill(200, 200, 200)
        for i in range(res):
            for j in range(res):
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
        no_fill()
        stroke_weight(1)
        if wire:
            stroke(70, 110, 170)
        else:
            stroke(55, 90, 145, 55)
        for i in range(res):
            for j in range(res):
                begin_shape(QUADS)
                vertex(float(surf_pts[i][j][0]),             float(surf_pts[i][j][1]),             float(surf_pts[i][j][2]))
                vertex(float(surf_pts[i][j + 1][0]),         float(surf_pts[i][j + 1][1]),         float(surf_pts[i][j + 1][2]))
                vertex(float(surf_pts[i + 1][j + 1][0]),     float(surf_pts[i + 1][j + 1][1]),     float(surf_pts[i + 1][j + 1][2]))
                vertex(float(surf_pts[i + 1][j][0]),         float(surf_pts[i + 1][j][1]),         float(surf_pts[i + 1][j][2]))
                end_shape()

    # ── malha de controle (amarela) ────────────────────────────────────────
    stroke(255, 200, 50, 160)
    stroke_weight(1.5)
    no_fill()
    for i in range(nu):
        for j in range(nv - 1):
            x0, y0, z0 = ctrl[i][j][:3]
            x1, y1, z1 = ctrl[i][j + 1][:3]
            line(float(x0), float(y0), float(z0), float(x1), float(y1), float(z1))
    for j in range(nv):
        for i in range(nu - 1):
            x0, y0, z0 = ctrl[i][j][:3]
            x1, y1, z1 = ctrl[i + 1][j][:3]
            line(float(x0), float(y0), float(z0), float(x1), float(y1), float(z1))

    # ── esferas nos pontos de controle ─────────────────────────────────────
    r = max(3.0, min(8.0, 56.0 / max(nu, nv)))
    no_stroke()
    for i in range(nu):
        for j in range(nv):
            x, y, z, w = ctrl[i][j]
            push()
            translate(float(x), float(y), float(z))
            if (i, j) == selected:
                emissive_material(255, 0, 0)
                fill(255, 75, 75)
                sphere(r * 1.3)
                emissive_material(0, 0, 0)
            else:
                _ctrl_color(w)
                sphere(r)
            pop()

    update_hud()
