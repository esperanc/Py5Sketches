"""
Step-by-step transformation demo.
"""
transforms = [
    "P5.translate (1,-2)",
    "P5.rotate(P5.PI/4)",
    "P5.scale(0.5,1.5)"
    ]

def vec (x,y): return createVector(x,y)

def setup():
    createCanvas(600, 600)
    global tcount
    tcount = 0

def keyPressed():
    global tcount
    if key in "sS": 
        save(f"transform {tcount}.png")
    else:
        tcount = (tcount+1)%(len(transforms)+1)
    
def draw():
    background (200)
    fill(0)
    stroke(0)
    textSize(30)
    for i,trans in enumerate(transforms[:tcount]):
        t = trans.replace("P5.","")
        text(t,20,35*(i+1))
    text ("square(0,0,1)", 20, 35*(tcount+1))
    translate (width/2, height/2)
    scale (100)
    strokeWeight (2/100)
    fill(0)
    A,B,C = vec(0,0),vec(1,0),vec(0,1)
    Arrow(A, B,1/20).draw()
    Arrow(A, C,1/20).draw()
    strokeWeight(2/100)
    fill(255,128)
    scene()

def scene():
    for transf in transforms[:tcount]:
        eval(transf)
    A,B,C = vec(0,0),vec(1,0),vec(0,1)
    Arrow(A, B,1/20).draw()
    Arrow(A, C,1/20).draw()    
    noStroke()
    square (0,0,1)

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
    def __init__(self, p, q, s = 0.1):
        self.p = p
        self.q = q
        self.s = s
        self.vec = q.copy().sub(p)
        self.v = self.vec.copy().normalize()

    def draw(self):
        p,q,v,s = self.p, self.q, self.v,self.s
        line(p.x,p.y,q.x,q.y)
        u = v.copy().rotate(PI/2).setMag(s)
        r = q.copy().sub(v.copy().setMag(s*2))
        a = r.copy().add(u)
        b = r.copy().sub(u)
        triangle (a.x, a.y, q.x, q.y, b.x, b.y)
        # s = q.copy().add(v.copy().setMag(12))
        # push()
        # strokeWeight(1)
        # text (self.name, s.x, s.y)
        # pop()
