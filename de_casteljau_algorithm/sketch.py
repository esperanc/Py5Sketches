"""
Interactive demonstration of Bézier Curves drawn with the de Casteljau algorithm.

Drag control points to adjust curve.
Click and drag to add another control point (and increase curve degree).
Click on control point to remove it.
Use slider to adjust the t parameter.
"""

from math import comb, pow, hypot
from gui import GuiBlock

def de_casteljau (t, pts):
    global b
    b = [pts]
    n = len(pts)-1
    u = 1-t
    for k in range(1,n+1):
        b.append([])
        bp = b[k-1]
        for i in range (0,n-k+1):
            p = [u*bp[i][j]+t*bp[i+1][j] for j in [0,1]]
            b[k].append(p)
    return createVector(*b[n][0])

def dist_pt_seg(p, a, b):
    ab = b[0]-a[0],b[1]-a[1]
    ap = p[0]-a[0],p[1]-a[1]
    mag_ab_sq = hypot(*ab)
    if mag_ab_sq < 0.001: return hypot(*ap)
    t = max(0,min(1,(ab[0]*ap[0]+ab[1]*ap[1])/mag_ab_sq))
    q = [a[0]+ab[0]*t,a[1]+ab[1]*t]
    return hypot(q[0]-p[0],q[1]-p[1])

def flatness(pts):
    n = len(pts)
    a,b =pts[0],pts[n-1]
    d = [dist_pt_seg(p,a,b) for p in pts[1:-1]]
    return min(d)
    
def subdivide (pts, max_flatness = 1):
    result = []
    def sub (pts,include_first,max_level):
        fl = flatness(pts)
        if max_level<=0 or fl<= max_flatness: 
            result.extend(pts if include_first else pts[1:])
        else:
            n = len(pts)-1
            de_casteljau(0.5,pts)
            left = [b[i][0] for i in range (n+1)]
            right = [b[n-i][i] for i in range(n+1)]
            sub(left,True,max_level-1)
            sub(right,False,max_level-1)
    sub(pts, True, 10)
    return result
            
def bernstein(n,k,t):
    return comb(n,k)*pow(t,k)*pow(1-t,n-k)
    
def setup():
    global pts
    create_canvas(windowWidth, windowHeight)
    w,h = width,height
    pts = [[w*0.2,h*0.8],
           [w*0.4,h*0.2],
           [w*0.6,h*0.2],
           [w*0.8,h*0.8]]
    global gui
    gui = GuiBlock()
    gui.addNumber("t",0,1,0.5,0.01)
    gui.addNumber("max_error", 1,100,20,1)
    gui.addCheckbox("adaptive", True)
    gui.addCheckbox("construction", True)
    gui.addCheckbox("reparametrization")
    gui.addCheckbox("indices")
    

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
        #k = n+1 if gui.closed else n
        k = n
        for i in range (1,k):
            d = dist_segment (p, pts[i-1], pts[i%n])
            if d < min_d:
                min_d = d
                j = i
        pts = pts[:j] + [p] + pts[j:]
        selected = pts[j]

def mouse_released():
    global selected, pts
    if selected and not moved:
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
    
def draw():
    background(245)
    global pts
    
    push()
    stroke_weight(3)
    n = len(pts)-1
    begin_shape()
    if gui.adaptive:
        for x,y in subdivide(pts,gui.max_error):
            vertex(x,y)
    else:
        for i in range(100):
            t = i / 99
            p = de_casteljau(t, pts)
            vertex(p.x,p.y)
    end_shape()
    pop()
    
    for x,y in pts:
        circle (x, y, 15)
    
    push()
    colors = ['red','green','blue','orange','magenta','cyan']
    
    stroke_weight(2)
    de_casteljau(gui.t, pts)

    n = len(pts)-1
    
    if gui.reparametrization:
        no_stroke()
        fill (0,20)
        begin_shape()
        for i in range(n+1):
            x,y = b[i][0]
            vertex(x,y)
        end_shape()
        begin_shape()
        for i in range(n+1):
            x,y = b[n-i][i]
            vertex(x,y)
        end_shape()
    
    if gui.construction:
        for i in range(n+1):
            poly,c = b[i], colors[i%len(colors)]
            stroke(c)
            no_fill()
            begin_shape()
            for x,y in poly: vertex(x,y)
            end_shape()
            fill(c)
            for x,y in poly: circle(x,y,10)
            if gui.indices:
                fill('black')
                stroke(255)
                textSize(18)
                textAlign(CENTER)
                for j in range(len(poly)):
                    x,y = poly[j]
                    text(f"{j},{i}",x,y-12)
    pop()
        
    
    
    
