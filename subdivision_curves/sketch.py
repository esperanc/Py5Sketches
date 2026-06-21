"""
Demonstração de curvas de subdivisão: 4-point e Lane-Riesenfeld.

Arrastar pontos de controle para ajustar curva.
Clicar e arrastar para adicionar outro ponto de controle.
"""

from smooth_curves import lr, four_point
from gui import GuiBlock

def setup():
    createCanvas(windowWidth, windowHeight)
    global pts, subdivide, selected
    selected = None
    s = min(width,height)/4
    x = width/2
    y = height/2
    pts = [[x-s,y+s],[x-s,y-s], [x+s, y-s], [x+s, y+s]]
    make_interface()

def draw():
    background(240)
    global pts
    
    push()
    begin_shape()
    stroke_weight(2)
    fill('white')
    sub = pts
    if gui.algorithm=="Lane-Riesenfeld":
        subdivide = lr
        arg = gui.degree
    else:
        subdivide = four_point
        arg = gui.w
    for i in range(gui.recursions): sub = subdivide (sub, gui.closed, arg)
    for x,y in sub: vertex(x,y)
    end_shape(CLOSE if gui.closed else False)
    if gui.show_pts:
        for p in sub: circle(*p, 4)
    pop()
    
    push()
    stroke_weight(1)
    no_fill()
    drawingContext.setLineDash([2, 5]);
    begin_shape()
    for x,y in pts: vertex(x,y)
    end_shape(CLOSE if gui.closed else False)
    pop()
    
    
    
    for p in pts:
        fill('red' if p is selected else 'white')
        circle (*p, 10, 10)

def make_interface():
    global gui
    gui = GuiBlock()
    gui.addSelect("algorithm", ["Lane-Riesenfeld", "4-point"],"Lane-Riesenfeld")
    gui.addCheckbox("closed")
    gui.addCheckbox("show_pts")
    gui.addNumber("recursions", 0,6,4,1)
    gui.addNumber("degree",1,4,2,1)
    gui.addNumber("w",0.0,0.1,0.06,0.01)


def mouse_pressed():
    global selected, pts, moved
    selected = None
    if mouse_button != LEFT: return
    moved = False
    for p in pts:
        x, y = p
        if dist(x,y,mouse_x, mouse_y) < 10:
            selected = p
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


def key_pressed():
    global selected, pts
    if key in ["d","D","Delete"]:
        if selected and len(pts)>3:
            pts.remove(selected)
            
            
def mouse_dragged():
    global selected, moved
    if selected:
        moved = True
        p = selected
        p[0]+=mouse_x-pmouse_x
        p[1]+=mouse_y-pmouse_y

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
