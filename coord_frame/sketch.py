"""
Interactive coordinate system demo.

Click and drag points / arrow heads.
Click coordinate frame to toggle coordinate systems.
"""

from frame import Frame

def setup():
    createCanvas(windowWidth, windowHeight)
    global P, Q, R, A, B, C, pt, v0, v1, currentFrame
    currentFrame = "PQR"
    P = createVector (100,100)
    Q = createVector (150,100)
    R = createVector (100,150)
    A = createVector (400,400)
    B = createVector (300,400)
    C = createVector (400,350)
    pt = createVector (200,150)
    v0 = createVector (200,200)
    v1 = createVector (250,250)
    
class Point:
    def __init__(self,p,label=""):
        self.p = p
        self.label=label
    
    def draw(self):
        circle (self.p.x, self.p.y, 8)
        push()
        strokeWeight(1)
        text (self.label, self.p.x, self.p.y-12)
        pop()
        
class Arrow:
    def __init__(self, p, q, name="X"):
        self.p = p
        self.q = q
        self.vec = q.copy().sub(p)
        self.v = self.vec.copy().normalize()
        self.name = name
    
    def draw(self):
        p,q,v = self.p, self.q, self.v
        line(p.x,p.y,q.x,q.y)
        u = v.copy().rotate(PI/2).setMag(5)
        r = q.copy().sub(v.copy().setMag(10))
        a = r.copy().add(u)
        b = r.copy().sub(u)
        triangle (a.x, a.y, q.x, q.y, b.x, b.y)
        s = q.copy().add(v.copy().setMag(12))
        push()
        strokeWeight(1)
        text (self.name, s.x, s.y)
        pop()
        
def mouse_pressed():
    global selected, currentFrame
    selected = None
    m = createVector (mouseX, mouseY)
    for p in (P,Q,R,A,B,C,pt, v0, v1):
        if m.dist(p) < 5:
            selected = p
    if selected in (A,B,C):
        currentFrame = "ABC"
    elif selected in (P,Q,R):
        currentFrame = "PQR"
        
def mouse_dragged():
    if not selected: return
    p = createVector(round(mouseX/5)*5, round(mouseY/5)*5)
    if selected.dist(p) >= 5:
        selected.set(p)

def mouse_released():
    global selected
    selected = None

def draw_parallel_lines(p, u, v):
    uNorm = u.copy().normalize()
    n = createVector(-uNorm.y, uNorm.x)
    
    corners = [
    0, 
    n.dot(createVector(width, 0)),
    n.dot(createVector(width, height)),
    n.dot(createVector(0, height))
    ]
    
    minC = min(*corners)
    maxC = max(*corners)
  
    baseProj = p.dot(n)
    stepProj = v.dot(n)
  
    if abs(stepProj) < 0.0001:
        if baseProj >= minC and baseProj <= maxC:
            draw_extended_line(p, uNorm)
        return
    
    i1 = (minC - baseProj) / stepProj
    i2 = (maxC - baseProj) / stepProj
    iStart = ceil(min(i1, i2))
    iEnd = floor(max(i1, i2));
  
    count = iEnd - iStart + 1
    
    if count > 1000:
        center = floor((iStart + iEnd) / 2)
        iStart = center - 500
        iEnd = center + 499

    for i in range(iStart, iEnd+1):
        p_i = p.copy().add(v.copy().mult(i))
        draw_extended_line(p_i, uNorm)

def draw_extended_line(origin, dir):
    canvasCenter = createVector(width / 2, height / 2)
    
    toCenter = canvasCenter.copy().sub(origin)

    distToCenterProj = toCenter.dot(dir)
    closestPoint = origin.copy().add(dir.copy().mult(distToCenterProj))
  
    diag = dist(0, 0, width, height);
    p1 = closestPoint.copy().sub(dir.copy().mult(diag))
    p2 = closestPoint.copy().add(dir.copy().mult(diag))
    line(p1.x, p1.y, p2.x, p2.y)

def drawGrid():
    drawingContext.setLineDash([2,2])
    if currentFrame == "PQR":
        p = P
        u = Q.copy().sub(P)
        v = R.copy().sub(P)
    else:
        p = A
        u = B.copy().sub(A)
        v = C.copy().sub(A)
    draw_parallel_lines(p,u,v)
    draw_parallel_lines(p,v,u)
    drawingContext.setLineDash([])

def draw():
    background(220)
    strokeWeight(1)
    stroke('gray')
    drawGrid()
    
    textSize(14)
    strokeWeight(2)
    textAlign(CENTER,CENTER)
    if currentFrame == "PQR":
        stroke('black')
        fill("black")
    else:
        stroke('gray')
        fill("gray")
    
    O = Point(P)
    u1 = Arrow (P,Q, "X")
    u2 = Arrow (P,R, "Y")
    
    u1.draw()
    u2.draw()
    O.draw()
    
    frame = None
    
    if currentFrame == "ABC":
        stroke('black')
        fill("black")
    else:
        stroke('gray')
        fill("gray")
        try:
            frame = Frame (P,u1.vec,u2.vec)
        except Exception:
            pass
    
    O = Point(A)
    u1 = Arrow (A,B, "U")
    u2 = Arrow (A,C, "V")
    
    u1.draw()
    u2.draw()
    O.draw()
    
    fill("black")
    if currentFrame == "ABC":
        try:
            frame = Frame (A,u1.vec,u2.vec)
        except Exception:
            pass
    
    if frame:
        coords = frame.to_frame_point(pt)
        labelPoint = f"{coords.x:.1f}, {coords.y:.1f}"
        coords = frame.to_frame_vector(v1.copy().sub(v0))
        labelVector = f"{coords.x:.1f}, {coords.y:.1f}"
    else:
        labelPoint = ""
        labelVector = ""
        
        
    stroke ('black')
    Point(pt,labelPoint).draw()
    Arrow(v0,v1,labelVector).draw()
