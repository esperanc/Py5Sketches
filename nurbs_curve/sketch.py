"""
Demo de curvas NURBS.
"""
from gui import GuiBlock

def cox_de_boor(i, d, t, knots):

    def recurse(i, d):
        if d == 0: 
            return 1.0 if knots[i] <= t < knots[i+1] else 0.0
        
        # Calculate denominators to handle potential division by zero
        # (Standard B-spline convention: 0 / 0 = 0)
        denom1 = knots[i+d] - knots[i]
        denom2 = knots[i+d+1] - knots[i+1]
        
        term1 = 0.0
        if denom1 != 0:
            term1 = ((t - knots[i]) / denom1) * recurse(i, d-1)
            
        term2 = 0.0
        if denom2 != 0:
            term2 = ((knots[i+d+1] - t) / denom2) * recurse(i+1, d-1)
            
        return term1 + term2

    return recurse(i, d)

# 
# Iterative version
#
def cox_de_boor(i, d, t, knots):
    
    global last_span
    try:
        last_span
    except:
        # Find the index of the last non-empty interval
        # (last j where knots[j] < knots[j+1])
        last_span = max(j for j in range(len(knots) - 1) if knots[j] < knots[j+1])

    def in_span(j):
        if j == last_span:
            return knots[j] <= t <= knots[j+1]   # closed on right at final span
        return knots[j] <= t < knots[j+1]

    N = [in_span(j) for j in range(i, i + d + 1)]

    for deg in range(1, d + 1):
        for j in range(d - deg + 1):
            ki = i + j
            denom1 = knots[ki + deg] - knots[ki]
            denom2 = knots[ki + deg + 1] - knots[ki + 1]
            term1 = ((t - knots[ki])       / denom1 * N[j])   if denom1 else 0.0
            term2 = ((knots[ki+deg+1] - t) / denom2 * N[j+1]) if denom2 else 0.0
            N[j] = term1 + term2

    return N[0]



def setup():
    global pts, selected
    createCanvas(windowWidth, windowHeight)
    s = min(width,height)/4
    x = width/2
    y = height/2
    pts = [[x-s,y+s,1],[x-s,y-s,1], [x+s, y-s,1], [x+s, y+s,1]]
    selected = None

    global gui
    GuiBlock.labelWidth = "7em"
    gui = GuiBlock()
    gui.addNumber("d",1,4,2,1)
    gui.addText("knots", "0,1,2,3,4,5")
    gui.addCheckbox("closed",False)
    gui.change(compute_knots)
    compute_knots()

    global wgui
    GuiBlock.labelWidth = "3em"
    wgui = GuiBlock()
    wgui.addNumber("w",0.1,5,1,0.1)
    wgui.position(width-230,10)
    wgui.change(w_changed)
    
def w_changed():
    global selected
    if selected:
        selected[2] = wgui.w
    
def compute_knots():
    global knots
    try:
        knots = list(map(lambda s:float(s), gui.knots.split(",")))
    except Exception:
        return
    d = gui.d
    m = len(pts)
    # Pad the knot vector.
    while len(knots)<m+d+d+1:
        increment = knots[-1]-knots[-2] if len(knots)>1 else 1
        knots.append(knots[-1]+increment)

def bspline_point(pts, t, d):
    q = createVector(0,0)
    for i,p in enumerate(pts):
        b = cox_de_boor(i,d,t,knots)
        q.x += b*p[0]*p[2]
        q.y += b*p[1]*p[2]
        q.z += b*p[2]
    return createVector(q.x/q.z,q.y/q.z)

def draw():
    background(240)
    
    push()
    stroke_weight(2)
    fill('white')
    d = gui.d
    if gui.closed:
        # Add trailing points to close the curve
        points = pts[-d:]+pts
    else:
        # Regular b-spline
        points = pts
    tmin = knots[d]
    tmax = knots[len(points)]
    begin_shape()
    
    for i in range(201):
        t = tmin+i*(tmax-tmin)/200.01 # Avoid the singularity at the last knot
        p = bspline_point(points,t,d)
        vertex(p.x,p.y)
    end_shape(CLOSE if gui.closed else None)
    pop()
    
    push()
    stroke_weight(1)
    no_fill()
    drawingContext.setLineDash([2, 5]);
    begin_shape()
    for x,y,w in pts: vertex(x,y)
    end_shape(CLOSE if gui.closed else False)
    pop()
    
    for p in pts:
        x,y,w = p
        fill('red' if p is selected else 'white')
        circle (x, y, 10, 10)

    
def mouse_pressed():
    global selected, pts, moved
    selected = None
    if mouse_button != LEFT: return
    moved = False
    for p in pts:
        x, y = p[:2]
        if dist(x,y,mouse_x, mouse_y) < 10:
            selected = p
    if not selected:
        j = -1
        min_d = 1e10
        p = [mouse_x, mouse_y,1]
        n = len(pts)
        k = n+1 if gui.closed else n
        for i in range (1,k):
            d = dist_segment (p, pts[i-1], pts[i%n])
            if d < min_d:
                min_d = d
                j = i
        pts = pts[:j] + [p] + pts[j:]
        selected = pts[j]
        compute_knots()
    if selected:
        wgui.setValue("w",selected[2])

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
    p = create_vector (*p[:2])
    a = create_vector (*a[:2])
    b = create_vector (*b[:2])
    v = b.copy().sub(a)
    u = p.copy().sub(a)
    vlen = v.mag()
    vnorm = v.copy().normalize()
    proj_size = vnorm.dot(u)
    if proj_size > vlen: return p.dist(b)
    if proj_size < 0: return p.dist(a)
    return p.sub(a.lerp(b, proj_size / vlen)).mag()