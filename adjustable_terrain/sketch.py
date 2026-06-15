"""
Malha 3D interativa — N×M vértices em WEBGL.

  Arrastar esfera (vértice)  →  mover para cima/baixo (eixo Y mundial)
  Arrastar área vazia        →  orbitar / zoom com orbitControl
  +  /  -                    →  aumentar / reduzir resolução (passo 2)
  R                          →  zerar todas as alturas
  S                          →  suavizar um passo (Laplaciano)
  W                          →  alternar sólido / arame
  F                          →  alternar normais suaves / planas
"""

# ── parâmetros ─────────────────────────────────────────────────────────────
N, M      = 8, 8
GRID_SIZE = 360       # extensão total da grade em unidades de mundo
HIT_R     = 18        # threshold de seleção em pixels de tela

wireframe = False
smooth    = True
verts     = []        # verts[i][j] = [x, y, z]  — floats Python
selected  = None      # (i, j) ou None
drag_vert = False
dirty     = True
cached_nrm = None     # lista Python [N][M][3]

# matrizes de câmera (16 floats, coluna-maior) capturadas em draw()
cam_proj  = None
cam_view  = None

hud_el    = None      # elemento HTML para legenda

# ── grade ──────────────────────────────────────────────────────────────────

def make_grid():
    global verts, dirty
    sp = float(GRID_SIZE) / max(max(N - 1, 1), max(M - 1, 1))
    verts = [
        [[(j - (M - 1) * 0.5) * sp,   0.0,   (i - (N - 1) * 0.5) * sp]
         for j in range(M)]
        for i in range(N)
    ]
    dirty = True

# ── normais por vértice ────────────────────────────────────────────────────

def compute_normals():
    nrm = [[[0.0, 0.0, 0.0] for _ in range(M)] for _ in range(N)]
    for i in range(N - 1):
        for j in range(M - 1):
            v00 = verts[i][j];     v10 = verts[i + 1][j]
            v11 = verts[i + 1][j + 1]; v01 = verts[i][j + 1]
            for (a, b, c), corners in [
                ((v00, v01, v11), [(i, j), (i, j + 1), (i + 1, j + 1)]),
                ((v00, v11, v10), [(i, j), (i + 1, j + 1), (i + 1, j)])
            ]:
                e1 = [b[k] - a[k] for k in range(3)]
                e2 = [c[k] - a[k] for k in range(3)]
                nx = e1[1]*e2[2] - e1[2]*e2[1]
                ny = e1[2]*e2[0] - e1[0]*e2[2]
                nz = e1[0]*e2[1] - e1[1]*e2[0]
                for ii, jj in corners:
                    nrm[ii][jj][0] += nx
                    nrm[ii][jj][1] += ny
                    nrm[ii][jj][2] += nz
    for i in range(N):
        for j in range(M):
            n = nrm[i][j]
            L = (n[0]**2 + n[1]**2 + n[2]**2)**0.5
            nrm[i][j] = [n[k] / L for k in range(3)] if L > 1e-9 else [0.0, 1.0, 0.0]
    return nrm

# ── projeção manual (substitui screenX/screenY ausente em Py5Script) ───────

def fetch_matrices():
    """Lê proj e view da câmera interna do p5.js."""
    try:
        cam = P5._renderer._curCamera
        p = [float(cam.projMatrix.mat4[k]) for k in range(16)]
        v = [float(cam.cameraMatrix.mat4[k]) for k in range(16)]
        return p, v
    except Exception:
        return None, None

def world_to_screen(x, y, z, proj, view):
    """Projeta ponto 3D → pixels de tela. Matrizes em coluna-maior (OpenGL)."""
    # View: ve = view * [x,y,z,1]
    vx = view[0]*x + view[4]*y + view[8]*z  + view[12]
    vy = view[1]*x + view[5]*y + view[9]*z  + view[13]
    vz = view[2]*x + view[6]*y + view[10]*z + view[14]
    vw = view[3]*x + view[7]*y + view[11]*z + view[15]
    # Projeção perspectiva: cl = proj * ve
    cx = proj[0]*vx + proj[4]*vy + proj[8]*vz  + proj[12]*vw
    cy = proj[1]*vx + proj[5]*vy + proj[9]*vz  + proj[13]*vw
    cw = proj[3]*vx + proj[7]*vy + proj[11]*vz + proj[15]*vw
    if abs(cw) < 1e-9:
        return None, None
    # NDC → pixels
    sx = (cx / cw + 1.0) * width  * 0.5
    sy = (1.0 - cy / cw) * height * 0.5
    return sx, sy

# ── setup / eventos ────────────────────────────────────────────────────────

def setup():
    global hud_el
    create_canvas(window_width, window_height, WEBGL)
    make_grid()
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
        sel_info = f'  ·  vértice ({i},{j})  y={verts[i][j][1]:.0f}'
    modo = 'arame' if wireframe else ('suave' if smooth else 'plano')
    hud_el.html(
        f'Malha {N}×{M}  |  {modo}{sel_info}<br>'
        f'+/- res  ·  R zerar  ·  S suavizar  ·  W arame  ·  F normais  '
        f'·  arrastar esfera: altura  ·  arrastar vazio: câmera'
    )

def mouse_pressed():
    global selected, drag_vert
    if cam_proj is None or cam_view is None:
        return
    best, best_d = None, HIT_R
    for i in range(N):
        for j in range(M):
            sx, sy = world_to_screen(verts[i][j][0], verts[i][j][1], verts[i][j][2],
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
    # Escalar delta de pixels → unidades de mundo no eixo Y
    # Derivação: 1 pixel ≈ cam_dist / (proj[5] * height/2) unidades de mundo
    scale = 1.0
    try:
        cam = P5._renderer._curCamera
        ex = float(cam.eyeX); ey = float(cam.eyeY); ez = float(cam.eyeZ)
        cam_dist = (ex*ex + ey*ey + ez*ez)**0.5
        if cam_proj and cam_proj[5] > 1e-9:
            scale = cam_dist / (cam_proj[5] * height * 0.5)
    except Exception:
        pass
    verts[selected[0]][selected[1]][1] += (mouse_y - pmouse_y) * scale
    dirty = True

def mouse_released():
    global selected, drag_vert
    selected  = None
    drag_vert = False

def key_pressed():
    global N, M, wireframe, smooth, dirty
    if key in ['+', '='] and N < 30:
        N = min(N + 2, 30);  M = min(M + 2, 30);  make_grid()
    elif key == '-' and N > 2:
        N = max(N - 2, 2);   M = max(M - 2, 2);   make_grid()
    elif key in ['R', 'r']:
        for row in verts:
            for v in row:
                v[1] = 0.0
        dirty = True
    elif key in ['W', 'w']:
        wireframe = not wireframe
    elif key in ['F', 'f']:
        smooth = not smooth;  dirty = True
    elif key in ['S', 's']:
        new_y = [[verts[i][j][1] for j in range(M)] for i in range(N)]
        for i in range(N):
            for j in range(M):
                nb = [(i + di, j + dj)
                      for di, dj in [(-1, 0), (1, 0), (0, -1), (0, 1)]
                      if 0 <= i + di < N and 0 <= j + dj < M]
                new_y[i][j] = sum(verts[a][b][1] for a, b in nb) / len(nb)
        for i in range(N):
            for j in range(M):
                verts[i][j][1] = new_y[i][j]
        dirty = True

# ── renderização ───────────────────────────────────────────────────────────

def vert_radius():
    return max(2.5, min(7.0, 48.0 / max(N, M)))

def draw():
    global cam_proj, cam_view, dirty, cached_nrm

    background(22, 28, 40)

    # orbitControl só quando não estamos arrastando um vértice
    if not drag_vert:
        orbit_control()

    # Capturar matrizes APÓS orbit_control() atualizar a câmera
    cam_proj, cam_view = fetch_matrices()

    # Iluminação
    ambient_light(50, 58, 75)
    directional_light(200, 218, 255, -0.4, -1.0, -0.5)
    directional_light(80,  105, 175,  0.5,  0.5,  0.7)

    # Recalcular normais somente quando necessário
    if dirty:
        cached_nrm = compute_normals() if smooth else None
        dirty = False

    r = vert_radius()

    # ── faces sólidas ──────────────────────────────────────────────────────
    if not wireframe:
        no_stroke()
        fill(200, 200, 200)
        for i in range(N - 1):
            for j in range(M - 1):
                v00 = verts[i][j];      v10 = verts[i + 1][j]
                v11 = verts[i + 1][j + 1]; v01 = verts[i][j + 1]
                begin_shape(QUADS)
                if smooth and cached_nrm:
                    for v, (ii, jj) in [
                        (v00, (i,     j    )), (v01, (i,     j + 1)),
                        (v11, (i + 1, j + 1)), (v10, (i + 1, j    ))
                    ]:
                        normal(cached_nrm[ii][jj][0],
                               cached_nrm[ii][jj][1],
                               cached_nrm[ii][jj][2])
                        vertex(float(v[0]), float(v[1]), float(v[2]))
                else:
                    # normal plana por face
                    e1 = [v01[k] - v00[k] for k in range(3)]
                    e2 = [v11[k] - v00[k] for k in range(3)]
                    nx = e1[1]*e2[2] - e1[2]*e2[1]
                    ny = e1[2]*e2[0] - e1[0]*e2[2]
                    nz = e1[0]*e2[1] - e1[1]*e2[0]
                    L  = (nx*nx + ny*ny + nz*nz)**0.5
                    if L > 1e-9:  nx, ny, nz = nx/L, ny/L, nz/L
                    normal(nx, ny, nz)
                    vertex(float(v00[0]), float(v00[1]), float(v00[2]))
                    vertex(float(v01[0]), float(v01[1]), float(v01[2]))
                    vertex(float(v11[0]), float(v11[1]), float(v11[2]))
                    vertex(float(v10[0]), float(v10[1]), float(v10[2]))
                end_shape()

    # ── arame ──────────────────────────────────────────────────────────────
    no_fill()
    stroke_weight(1)
    if wireframe:
        stroke(70, 110, 170)
    else:
        stroke(55, 90, 145, 55)
    for i in range(N - 1):
        for j in range(M - 1):
            begin_shape(QUADS)
            vertex(float(verts[i][j][0]),         float(verts[i][j][1]),         float(verts[i][j][2]))
            vertex(float(verts[i][j + 1][0]),     float(verts[i][j + 1][1]),     float(verts[i][j + 1][2]))
            vertex(float(verts[i + 1][j + 1][0]), float(verts[i + 1][j + 1][1]), float(verts[i + 1][j + 1][2]))
            vertex(float(verts[i + 1][j][0]),     float(verts[i + 1][j][1]),     float(verts[i + 1][j][2]))
            end_shape()

    # ── esferas nos vértices ───────────────────────────────────────────────
    no_stroke()
    for i in range(N):
        for j in range(M):
            push()
            translate(float(verts[i][j][0]),
                      float(verts[i][j][1]),
                      float(verts[i][j][2]))
            if (i, j) == selected:
                fill(255, 75, 75)
                emissive_material(255,0,0)
                sphere(r * 1.9)
                emissive_material(0,0,0)
            else:
                fill(175, 208, 245)
                sphere(r)
            pop()

    update_hud()