"""
Demo de como passar coordenadas de textura com 'vertex()'
"""
def setup():
    createCanvas(800,800, WEBGL)
    global pg
    pg = createGraphics (400,400)
    pg.background('bisque')
    pg.circle(200,200,150)
    textureMode(NORMAL)
    texture(pg)


def draw():
    background(220)
    orbitControl()
    r,h,n = 200,200,20
    rotateX(PI/10)
    rotateY(radians(frameCount))
    beginShape(QUAD_STRIP)
    for i in range(n+1):
        ang = TAU*i/n
        vertex(r*cos(ang),-h,r*sin(ang),i/n,0)
        vertex(r*cos(ang),h,r*sin(ang),i/n,1)
    endShape()
    