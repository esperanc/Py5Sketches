"""
Demo de modos de "wrap" para coordenadas de textura.
"""
def setup():
    createCanvas(800,800, WEBGL)
    global pg
    pg = createGraphics (400,400)
    pg.fill('bisque')
    pg.strokeWeight(3)
    pg.stroke('brown')
    pg.rect(0,0,400,400)
    pg.fill("white")
    pg.triangle(100,100,300,300,300,100)
    textureMode(NORMAL)
    texture(pg)
    global wrap_u, wrap_v, wrap_dict
    wrap_dict = {"CLAMP":CLAMP, "REPEAT":REPEAT, "MIRROR":MIRROR}
    wrap_u = createSelect()
    wrap_u.position (10,10)
    wrap_v = createSelect()
    wrap_v.position (10,30)
    for key in wrap_dict.keys():
        wrap_u.option(key)
        wrap_v.option(key)

def draw():
    background(220)
    orbitControl()
    r,h,n = 200,200,20
    rotateX(PI/10)
    rotateY(radians(frameCount))
    textureWrap(wrap_dict[wrap_u.selected()],
       wrap_dict[wrap_v.selected()])
    beginShape(QUAD_STRIP)
    noStroke()
    for i in range(n+1):
        ang = TAU*i/n
        vertex(r*cos(ang),-h,r*sin(ang),8*i/n,0)
        vertex(r*cos(ang),h,r*sin(ang),8*i/n,4)
    endShape()
    