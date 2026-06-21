"""
Splines de Catmull-Rom interativas com parâmetro de tensão.
 
Clique em área vazia para adicionar um ponto.
Arraste pontos para movê-los.
Delete / X / D  : remover ponto selecionado
V               : alternar variante uniforme / centripetal
T / t           : aumentar / diminuir tensão global (passo 0.1)
"""
from gui import GuiBlock

def cr_segment(p0, p1, p2, p3, t, tension=0.0):
    """
    Catmull-Rom uniforme com tensão tau.
    tau=0 -> CR original; tau=1 -> segmentos de reta.
    Interpola entre p1 e p2.
    """
    s = (1.0 - tension) / 2.0
    t2 = t * t
    t3 = t2 * t
    # coeficientes de Hermite cubico
    h00 =  2*t3 - 3*t2 + 1
    h10 =    t3 - 2*t2 + t
    h01 = -2*t3 + 3*t2
    h11 =    t3 -   t2
    # tangentes escaladas por s
    m1 = [s * (p2[i] - p0[i]) for i in range(2)]
    m2 = [s * (p3[i] - p1[i]) for i in range(2)]
    return [
        h00*p1[i] + h10*m1[i] + h01*p2[i] + h11*m2[i]
        for i in range(2)
    ]
 
def lerp_pt(a, b, t):
    return [a[i] + t * (b[i] - a[i]) for i in range(2)]
 
def cr_centripetal_segment(p0, p1, p2, p3, t, tension=0.0):
    """Catmull-Rom centripetal com tensão."""
    def knot(a, b, t_prev):
        d = sqrt((b[0]-a[0])**2 + (b[1]-a[1])**2)
        return t_prev + (d**0.5 if d > 1e-8 else 1e-4)
    t0 = 0.0
    t1 = knot(p0, p1, t0)
    t2 = knot(p1, p2, t1)
    t3 = knot(p2, p3, t2)
    if abs(t2 - t1) < 1e-10:
        return p1[:]
    u = t1 + t * (t2 - t1)
    def lp(a, b, ta, tb, tc):
        if abs(tb - ta) < 1e-10:
            return a[:]
        f = (tc - ta) / (tb - ta)
        return lerp_pt(a, b, f)
    a1 = lp(p0, p1, t0, t1, u)
    a2 = lp(p1, p2, t1, t2, u)
    a3 = lp(p2, p3, t2, t3, u)
    b1 = lp(a1, a2, t0, t2, u)
    b2 = lp(a2, a3, t1, t3, u)
    base = lp(b1, b2, t1, t2, u)
    # aplicar tensão: interpolar entre base e lerp reto p1->p2
    if tension > 0.0:
        straight = lerp_pt(p1, p2, t)
        base = lerp_pt(base, straight, tension)
    return base
 
def setup():
    global pts, selected, centripetal, tension
    create_canvas(window_width, window_height)
    w, h = width, height
    pts = [
        [w*0.15, h*0.5],
        [w*0.30, h*0.2],
        [w*0.50, h*0.75],
        [w*0.70, h*0.2],
        [w*0.85, h*0.5],
    ]
    selected = None
    make_interface()
    centripetal = False
    tension = 0.0

def make_interface():
    global gui
    gui = GuiBlock()
    gui.addCheckbox("centripetal")
    gui.addCheckbox("closed")
    gui.addNumber("tension", -4,4,0,0.1)


def mouse_pressed():
    global selected, pts
    selected = None
    if mouse_button != LEFT:
        return
    for p in pts:
        if dist(p[0], p[1], mouse_x, mouse_y) < 10:
            selected = p
            return
    if not selected:
        j = -1
        min_d = 1e10
        p = [mouse_x, mouse_y]
        n = len(pts)
        k = n+1 if gui.closed else n
        for i in range (1,k):
            d = dist_segment (p, pts[i-1], pts[i%n])
            if d < min_d:
                min_d = d
                j = i
        pts = pts[:j] + [p] + pts[j:]
        selected = pts[j]
 
def mouse_dragged():
    if selected:
        selected[0] += mouse_x - pmouse_x
        selected[1] += mouse_y - pmouse_y
 
def key_pressed():
    global selected
    if key in ['D', 'd', 'X', 'x', 'Delete'] and selected and len(pts) > 2:
        pts.remove(selected)
        selected = None

def dist_segment (p, a, b):
    p = create_vector (*p)
    a = create_vector (*a)
    b = create_vector (*b)
    v = b.copy().sub(a)
    u = p.copy().sub(a)
    vlen = v.mag()
    vnorm = v.copy().normalize()
    proj_size = vnorm.dot(u)
    if proj_size > vlen: return p.dist(b)
    if proj_size < 0: return p.dist(a)
    return p.sub(a.lerp(b, proj_size / vlen)).mag()

def draw_curve():
    n = len(pts)
    if n < 2:
        return
    if gui.closed:
        ext = [pts[-1]]+pts+[pts[0],pts[1]]
        n += 1
    else:
        ext = [pts[0]] + pts + [pts[-1]]
    centripetal = gui.centripetal
    tension = gui.tension
    seg_fn = cr_centripetal_segment if centripetal else cr_segment
    stroke_weight(2.5)
    if gui.closed: fill('white') 
    else: no_fill()
    begin_shape()
    for s in range(1, n):
        p0, p1, p2, p3 = ext[s-1], ext[s], ext[s+1], ext[s+2]
        for i in range(40):
            pt = seg_fn(p0, p1, p2, p3, i / 39.0, tension)
            vertex(pt[0], pt[1])
    end_shape()
 
def draw():
    background(245)
 
    draw_curve()
    
    # Polígono de controle (tracejado)
    push()
    stroke(180)
    stroke_weight(1)
    no_fill()
    drawingContext.setLineDash([3, 6])
    begin_shape()
    for x, y in pts+([pts[0]] if gui.closed else []):
        vertex(x, y)
    end_shape()
    drawingContext.setLineDash([])
    pop()
 
    # Pontos de controle
    push()
    stroke_weight(1.5)
    stroke(50)
    for p in pts:
        fill(220, 60, 60) if p is selected else fill(255)
        circle(p[0], p[1], 12, 12)
    pop()
    
    

    