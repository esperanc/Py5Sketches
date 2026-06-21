"""
Interactive demonstration of Cubic Bézier splines.
Drag control points to adjust curve.
Click and drag to add another control point.
"""

from math import comb, pow, hypot
from gui import GuiBlock

            
def bernstein(n,k,t):
    return comb(n,k)*pow(t,k)*pow(1-t,n-k)
    
def bezier_point(pts,t,degree=3):
    sx,sy = 0,0
    for k in range(degree+1):
        j = min(k,len(pts)-1)
        x,y = pts[j]
        b = bernstein (degree,k,t)
        sx += x*b
        sy += y*b
    return [sx,sy]

def setup():
    global pts, selected, constrained
    create_canvas(windowWidth, windowHeight)
    constrained = []
    w,h = width,height
    pts = [[w*0.2,h*0.8],
           [w*0.4,h*0.2],
           [w*0.6,h*0.2],
           [w*0.8,h*0.8]]
    selected = None
    
def insert_point(pts, p):
    
    def dist_pt_seg(p, a, b):
        ab = b[0]-a[0],b[1]-a[1]
        ap = p[0]-a[0],p[1]-a[1]
        mag_ab_sq = ab[0]*ab[0]+ab[1]*ab[1]
        if mag_ab_sq < 0.001: return 0, hypot(*ap)
        t = max(0,min(1,(ab[0]*ap[0]+ab[1]*ap[1])/mag_ab_sq))
        q = [a[0]+ab[0]*t,a[1]+ab[1]*t]
        return t,hypot(q[0]-p[0],q[1]-p[1])
    
    min_d = 1e10
    closest = -1
    closest_t = 0
    for i in range(1, len(pts)):
        a = pts[i-1]
        b = pts[i]
        t,d = dist_pt_seg(p,a,b)
        if d < min_d:
            min_d = d
            closest,closest_t = i, t
    anchor = (closest-1) // 3 * 3 + 3
    A, B, C, D = pts[anchor-3:anchor+1]
    if closest == anchor:
        # between C and D
        t = (closest_t + 2) / 3
        Q1 = bezier_point([A,B,C,p,D],t+(1-t)*0.33,4)
        Q2 = bezier_point([A,B,C,p,D],t+(1-t)*0.66,4)
        pts[anchor-2:anchor] = [B, C, p, Q1, Q2]
    elif closest == anchor-1:
        # between B and C
        t = (closest_t + 1) / 3
        Q1 = bezier_point([A,B,p,C,D],0.33+(t-0.33)/2, 4)
        Q2 = bezier_point([A,B,p,C,D],0.66-(0.66-t)/2, 4)
        pts[anchor-2:anchor] = [B, Q1, p, Q2, C]
    else:
        assert(closest == anchor-2)
        t = closest_t / 3
        Q1 = bezier_point([A,p,B,C,D],t*0.33,4)
        Q2 = bezier_point([A,p,B,C,D],t*0.66,4)
        pts[anchor-2:anchor] = [Q1, Q2, p, B, C]
    constrain_point(pts,p)
    constrained.append(p)

def mouse_pressed():
    global selected, i_selected, pts, moved, new_point
    selected = None
    if mouse_button != LEFT: return
    moved = False
    new_point = False
    for i,p in enumerate(pts):
        x, y = p
        if dist(x,y,mouse_x, mouse_y) < 10:
            i_selected,selected = i,p
    if not selected:
        p = [mouse_x, mouse_y]
        insert_point (pts, p)
        i_selected = pts.index(p)
        selected = p
        new_point = True

def mouse_released():
    global selected, pts, new_point
    if selected and not moved and not new_point:
        if selected in constrained:
            constrained.remove(selected)
        else:
            i = pts.index(selected)
            if i%3 != 0 or i == 0 or i+1==len(pts): return
            constrain_point(pts,selected)
            constrained.append(selected)

def mouse_dragged():
    global selected, moved
    if selected:
        moved = True
        p = selected
        p[0]+=mouse_x-pmouse_x
        p[1]+=mouse_y-pmouse_y
        if p in constrained or i_selected%3==1 and pts[i_selected-1] in constrained\
            or i_selected%3==2 and pts[i_selected+1] in constrained:
            constrain_point (pts, p)

def key_pressed():
    if key in ["D","d", "X","x", "Delete"]:
        if selected and i_selected % 3 == 0:
            if selected in constrained: constrained.remove(selected)
            if len(pts [i_selected-1:i_selected+2]) == 3:
                pts [i_selected-1:i_selected+2] = []
        
def edge_neighbors(pts,i):
    idx = lambda i: max(0,min(len(pts)-1,i))
    if i % 3 == 0:
        # middle point
        a,b,c = pts[idx(i-1)],pts[i],pts[idx(i+1)]
    elif i % 3 == 1:
        # right point
        a,b,c = pts[idx(i-2)],pts[idx(i-1)],pts[i]
    else:
        # left point
        a,b,c = pts[i],pts[idx(i+1)],pts[idx(i+2)]
    return a,b,c

def constrain_point(pts,selected):
    i = pts.index(selected)
    a,b,c = edge_neighbors(pts,i)
    if i % 3 == 0:
        # middle point
        vx,vy = c[0]-a[0],c[1]-a[1]
        h = hypot(vx,vy)
        if h<0.01: return
        vx/=h
        vy/=h
        a[:] = [b[0]-vx*h/2,b[1]-vy*h/2]
        c[:] = [b[0]+vx*h/2,b[1]+vy*h/2]
    elif i % 3 == 1:
        # right point
        vx,vy = c[0]-b[0],c[1]-b[1]
        h = hypot(vx,vy)
        if h<0.01: return
        vx/=h
        vy/=h
        a[:] = [b[0]-vx*h,b[1]-vy*h]
    else:
        # left point
        vx,vy = b[0]-a[0],b[1]-a[1]
        h = hypot(vx,vy)
        if h<0.01: return
        vx/=h
        vy/=h
        c[:] = [b[0]+vx*h,b[1]+vy*h]
        
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
    
def draw_cubic(pts, i):
    for j in range(51):
        t = j / 50
        sx,sy = 0,0
        for k in range(4):
            j = min((i+k),len(pts)-1)
            x,y = pts[j]
            b = bernstein (3,k,t)
            sx += x*b
            sy += y*b
        vertex(sx,sy)
    
def draw():
    background(245)
    global pts
    
    push()
    stroke_weight(2)
    fill('white')
    begin_shape()
    for i in range(0,len(pts)-1,3):
        draw_cubic(pts,i)
    end_shape()
    pop()
    
    push()
    stroke_weight(1)
    no_fill()
    drawingContext.setLineDash([2, 5]);
    begin_shape()
    for x,y in pts: vertex(x,y)
    end_shape()
    pop()
    
    for i,p in enumerate(pts):
        sz = 12 if i%3 == 0 else 6
        if p in constrained: fill('red')
        else: fill('white')
        circle (*p, sz)
        
    
    
    
